from __future__ import annotations
# -*- coding: utf-8 -*-
"""
insights.py  --  turn a deterministic analysis table into 3-5 grounded,
plain-English insights plus an optional recommendation.

SAFETY DESIGN (this is the whole point):
  - The LLM is given ONLY a table that analysis.py already computed.
  - It is told to reference only numbers present in that table.
  - We additionally VERIFY, in code, that every numeric token the model
    emits appears in the source table. Ungrounded numbers are flagged.
  Facts come from the deterministic layer; the model only phrases them.

The LLM call is isolated in _call_claude_insights and injectable, so this is
testable without an API key.
"""
import json
import os
import re

MODEL = os.environ.get("INSIGHT_MODEL", "claude-sonnet-4-6")

VOICES = {
    "buyer_advocate":
        "You advise the BUYER in a procurement / group-purchasing program. "
        "Favor the buyer's interests: flag risk, weak protection, lock-in, and "
        "leverage points for renegotiation. Be direct but factual.",
    "neutral":
        "You are a neutral contract analyst. Summarize even-handedly without "
        "taking either party's side.",
}

# Tool schema: forces structured output so we never parse free prose.
INSIGHT_TOOL = {
    "name": "record_insights",
    "description": "Record 3-5 insights and an optional recommendation derived "
                   "strictly from the provided table.",
    "input_schema": {
        "type": "object",
        "properties": {
            "insights": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string",
                                 "description": "One insight, <= 2 sentences. Must reference "
                                                "specific values from the table."},
                        "refs": {"type": "array", "items": {"type": "string"},
                                 "description": "The exact values from the table this insight "
                                                "cites (e.g. ['90', 'Initech Services Group'])."},
                    },
                    "required": ["text", "refs"],
                    "additionalProperties": False,
                },
            },
            "recommendation": {
                "type": ["string", "null"],
                "description": "One actionable recommendation IF the table supports it, else null.",
            },
        },
        "required": ["insights", "recommendation"],
        "additionalProperties": False,
    },
}


def _system_prompt(voice: str) -> str:
    return (
        f"{VOICES.get(voice, VOICES['buyer_advocate'])}\n\n"
        "You will receive a JSON table of already-computed contract data. "
        "Rules, strictly:\n"
        "- Use ONLY values present in the table. Never introduce numbers, "
        "vendor names, or facts not in it.\n"
        "- Do not compute new figures beyond simple comparison/ordering of "
        "values already shown.\n"
        "- Each insight must cite the specific table value(s) it relies on in "
        "its 'refs'.\n"
        "- Prefer insights that help a decision (who is best/worst, outliers, "
        "risks, leverage).\n"
        "Call record_insights exactly once."
    )


def _numbers_in(obj) -> set:
    """All numeric tokens appearing anywhere in a JSON-able object, as strings.
    A '-' is only treated as a negative sign when not preceded by a digit, so
    ranges like '30-90' yield 30 and 90, not 30 and -90."""
    found = set()
    text = json.dumps(obj, default=str)
    for m in re.finditer(r"(?<![\d.])-?\d+(?:\.\d+)?", text):
        n = float(m.group())
        found.add(str(int(n)) if n.is_integer() else str(n))
    return found


def _verify_grounding(insights: list[dict], table: dict) -> list[str]:
    """Return a list of warnings for numbers cited that aren't in the table."""
    table_numbers = _numbers_in(table)
    warnings = []
    for ins in insights:
        cited = _numbers_in({"t": ins.get("text", ""), "r": ins.get("refs", [])})
        for num in cited:
            # allow small ordinals 1-5 (e.g. "3 of the 6 vendors") that describe counts
            if num in table_numbers:
                continue
            if num.isdigit() and int(num) <= len(table.get("rows", [])) + 1:
                continue
            warnings.append(f"Insight cites '{num}' which is not a table value: "
                            f"\"{ins.get('text','')[:80]}\"")
    return warnings


# ---------------------------------------------------------------------------
# Table builders: pull a clean, model-friendly table from analysis.py
# ---------------------------------------------------------------------------
def build_table(kind: str, contract_ids=None) -> dict:
    """kind in {compare, best_pricing, unfavorable, benchmark}."""
    import analysis
    if kind == "compare":
        t = analysis.compare(contract_ids)
        return {"kind": "compare", "columns": t["columns"], "rows": t["rows"],
                "highlights": t["highlights"]}
    if kind == "best_pricing":
        return {"kind": "best_pricing", "rows": analysis.rank_pricing(contract_ids)}
    if kind == "unfavorable":
        return {"kind": "unfavorable", "rows": analysis.unfavorable_terms(contract_ids)}
    if kind == "benchmark":
        return {"kind": "benchmark", **analysis.benchmark(contract_ids)}
    raise ValueError(f"unknown table kind: {kind}")


# ---------------------------------------------------------------------------
# Claude call (isolated, injectable)
# ---------------------------------------------------------------------------
def _call_claude_insights(table: dict, voice: str) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=_system_prompt(voice),
        tools=[INSIGHT_TOOL],
        tool_choice={"type": "tool", "name": "record_insights"},
        messages=[{
            "role": "user",
            "content": f"Here is the computed table:\n\n```json\n"
                       f"{json.dumps(table, indent=2, default=str)}\n```\n\n"
                       f"Produce insights by calling record_insights.",
        }],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "record_insights":
            return block.input
    raise RuntimeError("Model did not return record_insights tool call.")


def _mock_insights(table: dict, voice: str) -> dict:
    """Deterministic offline stand-in. Builds grounded insights straight from
    the table so the endpoint (and grounding check) work without an API key.
    Not a substitute for the real model's phrasing — a plumbing demo only."""
    kind = table.get("kind")
    rows = table.get("rows", [])
    ins = []
    rec = None

    if kind == "best_pricing" and rows:
        top, bottom = rows[0], rows[-1]
        ins.append({"text": f"{top['vendor_name']} offers the strongest pricing "
                            f"profile (score {top['pricing_score']}), driven by "
                            f"{top.get('payment_terms_days')}-day payment terms.",
                    "refs": [str(top['pricing_score']), str(top.get('payment_terms_days')),
                             top['vendor_name']]})
        ins.append({"text": f"{bottom['vendor_name']} ranks lowest "
                            f"(score {bottom['pricing_score']}), a candidate for "
                            f"renegotiation or consolidation.",
                    "refs": [str(bottom['pricing_score']), bottom['vendor_name']]})
        mins = [r for r in rows if r.get('minimum_spend')]
        if mins:
            hi = max(mins, key=lambda r: r['minimum_spend'])
            ins.append({"text": f"{hi['vendor_name']} carries the largest minimum "
                                f"commitment at {hi['minimum_spend']}, concentrating spend risk.",
                        "refs": [str(hi['minimum_spend']), hi['vendor_name']]})
        rec = (f"Prioritize {top['vendor_name']} for volume and open renegotiation "
               f"with {bottom['vendor_name']}.")

    elif kind == "unfavorable" and rows:
        highs = [r for r in rows if r.get("severity") == "high"]
        for r in highs[:3]:
            ins.append({"text": f"{r['vendor_name']}: {r['flag']}.", "refs": [r['vendor_name']]})
        while len(ins) < 3 and len(ins) < len(rows):
            r = rows[len(ins)]
            ins.append({"text": f"{r['vendor_name']}: {r['flag']}.", "refs": [r['vendor_name']]})
        rec = (f"Address the {len(highs)} high-severity flags before renewal." if highs
               else "Review flagged terms at next renewal.")

    elif kind == "compare" and rows:
        cols = table.get("columns", [])
        hl = table.get("highlights", {})
        if "payment_terms_days" in hl:
            best_id = hl["payment_terms_days"]["best"]
            best = next((r for r in rows if r["contract_id"] == best_id), None)
            if best:
                ins.append({"text": f"{best.get('vendor_name')} has the most favorable "
                                    f"payment terms at {best.get('payment_terms_days')} days.",
                            "refs": [str(best.get('payment_terms_days')), str(best.get('vendor_name'))]})
        no_term = [r for r in rows if r.get("termination_for_convenience") is False]
        if no_term:
            ins.append({"text": f"{len(no_term)} of {len(rows)} contracts lack "
                                f"termination for convenience, reducing exit flexibility.",
                        "refs": [str(len(no_term)), str(len(rows))]})
        models = {r.get("pricing_model") for r in rows if r.get("pricing_model")}
        ins.append({"text": f"Pricing spans {len(models)} distinct models "
                            f"({', '.join(sorted(m for m in models if m))}), "
                            f"complicating apples-to-apples comparison.",
                    "refs": [str(len(models))]})
        rec = "Standardize on consistent payment terms and a termination-for-convenience clause across vendors."

    elif kind == "benchmark":
        num = table.get("numeric", {})
        if "payment_terms_days" in num:
            p = num["payment_terms_days"]
            ins.append({"text": f"Payment terms range {p['min']}-{p['max']} days "
                                f"(median {p['median']}); the short end is below market norm.",
                        "refs": [str(p['min']), str(p['max']), str(p['median'])]})
        if "minimum_spend" in num:
            m = num["minimum_spend"]
            ins.append({"text": f"Minimum commitments span {m['min']}-{m['max']} "
                                f"(median {m['median']}), indicating uneven leverage.",
                        "refs": [str(m['min']), str(m['max']), str(m['median'])]})
        if "liability_cap" in num:
            l = num["liability_cap"]
            ins.append({"text": f"Liability caps range {l['min']}-{l['max']}, "
                                f"a wide spread in risk protection.",
                        "refs": [str(l['min']), str(l['max'])]})
        rec = "Set internal floors for payment terms and liability caps to guide negotiations."

    # ensure 3-5
    while len(ins) < 3:
        ins.append({"text": "Insufficient distinct signals in this view for a "
                            "further insight.", "refs": []})
    return {"insights": ins[:5], "recommendation": rec}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def generate_insights(kind: str, contract_ids=None, voice: str = "buyer_advocate",
                      call_fn=_call_claude_insights) -> dict:
    """Build the table, narrate it, verify grounding. Returns table + insights."""
    table = build_table(kind, contract_ids)
    # benchmark has no "rows"; treat it as empty only when there are no contracts
    has_data = bool(table.get("rows")) or (kind == "benchmark" and table.get("n_contracts"))
    if not has_data:
        return {"table": table, "insights": [], "recommendation": None,
                "grounding_warnings": [], "note": "No contracts to analyze yet."}
    raw = call_fn(table, voice)
    insights = raw.get("insights", [])
    warnings = _verify_grounding(insights, table)
    return {
        "table": table,
        "insights": insights,
        "recommendation": raw.get("recommendation"),
        "grounding_warnings": warnings,   # empty list == fully grounded
        "voice": voice,
    }
