# -*- coding: utf-8 -*-
"""
analysis.py  --  deterministic cross-contract analysis over typed rows.

These functions are the product's point of view. The numbers always come from
here (SQL/Python), never from an LLM. An LLM may later narrate the resulting
tables into insights, but it never invents the data.
"""
from statistics import median, mean

from db import fetch_for_analysis

# Default fields shown in a comparison table (the Tier-1 backbone + key risk).
DEFAULT_COMPARE_FIELDS = [
    "vendor_name", "pricing_model", "payment_terms_days", "discount_pct",
    "minimum_spend", "minimum_spend_period", "term_length_months",
    "auto_renewal", "termination_for_convenience", "liability_cap",
    "governing_law",
]


def compare(contract_ids=None, fields=None) -> dict:
    """Side-by-side comparison table. Returns {columns, rows, highlights}."""
    fields = fields or DEFAULT_COMPARE_FIELDS
    rows = fetch_for_analysis(contract_ids)
    table = [{f: r.get(f) for f in fields} | {"contract_id": r["contract_id"]} for r in rows]
    highlights = _best_worst(table, fields)
    return {"columns": fields, "rows": table, "highlights": highlights}


# Which direction is "better for the buyer" per field, for highlighting.
# +1 = higher is better, -1 = lower is better, 0 = not ranked.
_BUYER_DIRECTION = {
    "payment_terms_days": +1,     # longer to pay = better for buyer
    "discount_pct": +1,           # bigger discount = better
    "minimum_spend": -1,          # lower commitment = better
    "liability_cap": +1,          # higher cap = better protection for buyer
    "term_length_months": -1,     # shorter lock-in = more flexible
    "renewal_notice_days": -1,    # shorter notice to exit = better
    "termination_notice_days": -1,
}


def _best_worst(table, fields) -> dict:
    """For each numeric ranked field, mark which contract_id is best/worst."""
    hl = {}
    for f in fields:
        direction = _BUYER_DIRECTION.get(f, 0)
        if direction == 0:
            continue
        vals = [(r["contract_id"], r.get(f)) for r in table if isinstance(r.get(f), (int, float))]
        if len(vals) < 2:
            continue
        best = (max if direction > 0 else min)(vals, key=lambda x: x[1])
        worst = (min if direction > 0 else max)(vals, key=lambda x: x[1])
        hl[f] = {"best": best[0], "worst": worst[0]}
    return hl


def score_pricing(r: dict) -> float:
    """Composite buyer-favorability score for pricing. Explicit + tunable.
    Higher = better deal for the buyer. Returns a 0-ish centered score."""
    s = 0.0
    if r.get("payment_terms_days") is not None:
        s += r["payment_terms_days"] / 30.0           # +1 per 30 days to pay
    if r.get("discount_pct") is not None:
        s += r["discount_pct"] / 2.0                  # +0.5 per 1% discount
    ms = r.get("minimum_spend")
    if ms:                                            # any committed minimum is a cost
        s -= min(ms / 100000.0, 5.0)                  # capped penalty
    if r.get("termination_for_convenience"):
        s += 1.0                                      # exit flexibility is valuable
    return round(s, 2)


def rank_pricing(contract_ids=None) -> list[dict]:
    rows = fetch_for_analysis(contract_ids)
    for r in rows:
        r["pricing_score"] = score_pricing(r)
    rows.sort(key=lambda r: r["pricing_score"], reverse=True)
    return [{"vendor_name": r.get("vendor_name"), "contract_id": r["contract_id"],
             "pricing_score": r["pricing_score"],
             "payment_terms_days": r.get("payment_terms_days"),
             "discount_pct": r.get("discount_pct"),
             "minimum_spend": r.get("minimum_spend"),
             "termination_for_convenience": r.get("termination_for_convenience")}
            for r in rows]


def unfavorable_terms(contract_ids=None) -> list[dict]:
    """Rule-based flags for buyer-unfavorable terms. Each flag is auditable."""
    rows = fetch_for_analysis(contract_ids)
    flags = []
    for r in rows:
        v = r.get("vendor_name") or r.get("filename")
        cid = r["contract_id"]

        cap, ms = r.get("liability_cap"), r.get("minimum_spend")
        if cap is not None and ms and cap < ms:
            flags.append({"contract_id": cid, "vendor_name": v,
                          "severity": "high",
                          "flag": f"Liability cap (${cap:,}) is below committed spend (${ms:,})"})
        if r.get("liability_cap") is None and r.get("liability_cap_type") in (None, "none"):
            flags.append({"contract_id": cid, "vendor_name": v, "severity": "medium",
                          "flag": "No liability cap stated"})
        if r.get("termination_for_convenience") is False:
            flags.append({"contract_id": cid, "vendor_name": v, "severity": "high",
                          "flag": "No termination for convenience"})
        if r.get("auto_renewal") and (r.get("renewal_notice_days") or 0) > 60:
            flags.append({"contract_id": cid, "vendor_name": v, "severity": "medium",
                          "flag": f"Auto-renews with long notice window "
                                  f"({r.get('renewal_notice_days')} days)"})
        if r.get("payment_terms_days") is not None and r["payment_terms_days"] < 30:
            flags.append({"contract_id": cid, "vendor_name": v, "severity": "low",
                          "flag": f"Short payment terms ({r['payment_terms_days']} days)"})
        if r.get("indemnification") == "customer_only":
            flags.append({"contract_id": cid, "vendor_name": v, "severity": "high",
                          "flag": "One-sided indemnification (customer only)"})
    return flags


def benchmark(contract_ids=None) -> dict:
    """Dataset-wide stats per numeric field + distributions for categoricals."""
    rows = fetch_for_analysis(contract_ids)
    n = len(rows)
    numeric = ["payment_terms_days", "discount_pct", "minimum_spend",
               "term_length_months", "liability_cap"]
    out = {"n_contracts": n, "numeric": {}, "categorical": {}}
    for f in numeric:
        vals = [r[f] for r in rows if isinstance(r.get(f), (int, float))]
        if vals:
            out["numeric"][f] = {"min": min(vals), "max": max(vals),
                                 "mean": round(mean(vals), 1),
                                 "median": median(vals), "count": len(vals)}
    for f in ["pricing_model", "indemnification", "governing_law"]:
        dist = {}
        for r in rows:
            k = r.get(f) or "unknown"
            dist[k] = dist.get(k, 0) + 1
        out["categorical"][f] = dist
    return out
