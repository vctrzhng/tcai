# -*- coding: utf-8 -*-
"""
schema.py  --  THE SINGLE SOURCE OF TRUTH for contract extraction.

Everything downstream is generated from FIELD_SPEC:
  - the Claude tool input_schema (build_tool_schema)
  - the extraction system prompt's normalization rules (build_rules_text)
  - validation + needs_review logic (validate_and_normalize)
  - the flat record stored in SQLite later

To add/change a field, edit FIELD_SPEC. Nothing else needs to change.
"""
from typing import Any

# ---------------------------------------------------------------------------
# FIELD SPEC
# Each field:
#   name      : key used everywhere (must match ground_truth.json)
#   type      : "str" | "int" | "float" | "bool" | "enum"
#   enum      : allowed values (enum type only); always include a catch-all
#   unit      : human description of the normalized unit (for the prompt)
#   rule      : normalization instruction shown to the model
#   tier      : 1 = comparison backbone, 2 = risk/legal, 3 = metadata
#   risk      : True -> always surfaced for human review (absence is meaningful)
# ---------------------------------------------------------------------------
FIELD_SPEC: list[dict[str, Any]] = [
    {"name": "vendor_name", "type": "str", "tier": 1, "risk": False,
     "unit": "company legal name",
     "rule": "The supplier/vendor/provider/contractor party name. Not the customer."},

    {"name": "counterparty_name", "type": "str", "tier": 3, "risk": False,
     "unit": "company legal name",
     "rule": "The buyer/customer/client party name."},

    {"name": "effective_date", "type": "str", "tier": 3, "risk": False,
     "unit": "ISO date YYYY-MM-DD",
     "rule": "Effective date of the agreement, normalized to YYYY-MM-DD."},

    {"name": "pricing_model", "type": "enum", "tier": 1, "risk": False,
     "enum": ["fixed", "tiered_volume", "usage_based", "subscription",
              "cost_plus", "hybrid", "unknown"],
     "unit": "enum",
     "rule": "Pick the single best-fit value. 'hybrid' if it clearly mixes "
             "two models (e.g. fixed base fee + usage). 'unknown' if unclear."},

    {"name": "payment_terms_days", "type": "int", "tier": 1, "risk": False,
     "unit": "integer days",
     "rule": "Days until payment is due. 'Net 30' -> 30. 'forty-five (45) "
             "days' -> 45. 'upon receipt' / 'due on receipt' -> 0."},

    {"name": "discount_pct", "type": "float", "tier": 1, "risk": False,
     "unit": "percent as a number",
     "rule": "Headline/volume discount percent as a number (5% -> 5.0). If "
             "both a volume discount and a separate prompt-pay discount exist, "
             "use the larger volume discount. null if no discount stated."},

    {"name": "minimum_spend", "type": "int", "tier": 1, "risk": False,
     "unit": "integer, contract currency, no symbols",
     "rule": "Minimum committed spend/volume as an integer (no $ or commas). "
             "0 if the contract explicitly states no minimum. null if silent."},

    {"name": "minimum_spend_period", "type": "enum", "tier": 1, "risk": False,
     "enum": ["annual", "monthly", "quarterly", "total_term", "none", "unknown"],
     "unit": "enum",
     "rule": "The period the minimum_spend applies to. 'none' if there is no "
             "minimum. 'unknown' if a minimum exists but period is unclear."},

    {"name": "term_length_months", "type": "int", "tier": 1, "risk": False,
     "unit": "integer months",
     "rule": "Initial term length in months. '2 years' -> 24."},

    {"name": "auto_renewal", "type": "bool", "tier": 2, "risk": True,
     "unit": "boolean",
     "rule": "true if it renews automatically unless cancelled; false if it "
             "expires / requires a new agreement to continue."},

    {"name": "renewal_notice_days", "type": "int", "tier": 2, "risk": True,
     "unit": "integer days",
     "rule": "Days of advance notice required to stop renewal. null if not "
             "applicable or not stated."},

    {"name": "termination_for_convenience", "type": "bool", "tier": 2, "risk": True,
     "unit": "boolean",
     "rule": "true ONLY if a party may terminate without cause. Read the WHOLE "
             "document: if one section grants it but another restricts/qualifies "
             "it, report the net effect (true if it is available at all, even if "
             "only after an initial lock-in period)."},

    {"name": "termination_notice_days", "type": "int", "tier": 2, "risk": True,
     "unit": "integer days",
     "rule": "Notice days for termination for convenience. null if convenience "
             "termination is not permitted at all."},

    {"name": "liability_cap", "type": "int", "tier": 2, "risk": True,
     "unit": "integer, contract currency, no symbols",
     "rule": "Liability cap as an integer amount IF stated as a fixed sum. If "
             "the cap is expressed as a formula (e.g. '12 months of fees') and "
             "no fixed number is given, set normalized to null and capture the "
             "formula in liability_cap_type."},

    {"name": "liability_cap_type", "type": "enum", "tier": 2, "risk": True,
     "enum": ["fixed_amount", "fees_paid_12mo", "fees_paid_total",
              "multiple_of_fees", "uncapped", "none", "unknown"],
     "unit": "enum",
     "rule": "How the cap is expressed. 'fixed_amount' if a dollar figure; "
             "'fees_paid_12mo' for trailing-12-months-fees style caps; 'none' "
             "if the contract is silent on any cap."},

    {"name": "governing_law", "type": "str", "tier": 2, "risk": False,
     "unit": "US state or jurisdiction name",
     "rule": "Governing-law jurisdiction (usually a US state). Check boilerplate/"
             "miscellaneous sections. null if not stated."},

    {"name": "indemnification", "type": "enum", "tier": 2, "risk": True,
     "enum": ["mutual", "vendor_only", "customer_only", "none", "unknown"],
     "unit": "enum",
     "rule": "Who indemnifies whom. 'vendor_only' = only the vendor/supplier "
             "indemnifies. 'customer_only' = only the buyer/customer indemnifies. "
             "'none' if no indemnity is created."},
]

FIELD_BY_NAME = {f["name"]: f for f in FIELD_SPEC}
SCORED_FIELDS = [f["name"] for f in FIELD_SPEC]
RISK_FIELDS = [f["name"] for f in FIELD_SPEC if f["risk"]]

LOW_CONFIDENCE = 0.6  # below this -> needs_review


# ---------------------------------------------------------------------------
# Tool schema generation
# ---------------------------------------------------------------------------
def _normalized_schema(f: dict) -> dict:
    """JSON-schema fragment for a field's normalized value (nullable)."""
    if f["type"] == "enum":
        return {"type": ["string", "null"], "enum": f["enum"] + [None],
                "description": f"One of: {', '.join(f['enum'])}. {f['rule']}"}
    base = {"str": "string", "int": "integer", "float": "number", "bool": "boolean"}[f["type"]]
    return {"type": [base, "null"],
            "description": f"Normalized value ({f['unit']}). {f['rule']}"}


def build_tool_schema() -> dict:
    """Generate the Anthropic tool definition from FIELD_SPEC.

    Each field is an object {raw, normalized, confidence, source_page} so we
    capture provenance and confidence alongside the comparable value.
    """
    properties = {}
    for f in FIELD_SPEC:
        properties[f["name"]] = {
            "type": "object",
            "properties": {
                "raw": {"type": ["string", "null"],
                        "description": "Exact quoted text from the contract supporting "
                                       "this value, UNDER 15 WORDS. null if the field is absent."},
                "normalized": _normalized_schema(f),
                "confidence": {"type": "number",
                               "description": "0.0-1.0 confidence in the normalized value. "
                                              "Use < 0.6 when the text is ambiguous or conflicting."},
                "source_page": {"type": ["integer", "null"],
                                "description": "1-based page number where found (from [PAGE n] "
                                               "markers), or null if unknown."},
            },
            "required": ["raw", "normalized", "confidence", "source_page"],
            "additionalProperties": False,
        }
    return {
        "name": "record_contract_terms",
        "description": "Record the structured terms extracted from a procurement contract. "
                       "Provide every field; use null normalized + confidence 0 when a term "
                       "is genuinely absent.",
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": [f["name"] for f in FIELD_SPEC],
            "additionalProperties": False,
        },
        # When you upgrade to native structured outputs / strict tools, add: "strict": True
    }


def build_rules_text() -> str:
    """Human-readable normalization rules block for the system prompt."""
    lines = []
    for f in FIELD_SPEC:
        enum = f" Allowed: [{', '.join(f['enum'])}]." if f["type"] == "enum" else ""
        lines.append(f"- {f['name']} ({f['unit']}): {f['rule']}{enum}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation + normalization of the model's tool output
# ---------------------------------------------------------------------------
def _coerce(f: dict, value: Any):
    """Coerce/validate a normalized value to its declared type.
    Returns (coerced_value, ok). On failure returns (None, False)."""
    if value is None:
        return None, True
    t = f["type"]
    try:
        if t == "enum":
            return (value, True) if value in f["enum"] else ("unknown" if "unknown" in f["enum"] else None, False)
        if t == "int":
            return int(round(float(value))), True
        if t == "float":
            return float(value), True
        if t == "bool":
            if isinstance(value, bool):
                return value, True
            s = str(value).strip().lower()
            if s in ("true", "yes", "1"):
                return True, True
            if s in ("false", "no", "0"):
                return False, True
            return None, False
        if t == "str":
            return str(value).strip(), True
    except (ValueError, TypeError):
        return None, False
    return value, True


def validate_and_normalize(tool_input: dict, filename: str = "") -> dict:
    """Turn raw tool output into a clean record.

    Returns:
      {
        "filename": ...,
        "fields": {name: normalized_value, ...},     # flat, for SQL + harness
        "evidence": {name: {raw, confidence, source_page}, ...},
        "needs_review": bool,
        "review_reasons": [str, ...],
      }
    """
    fields, evidence, reasons = {}, {}, []
    for f in FIELD_SPEC:
        name = f["name"]
        cell = tool_input.get(name) or {}
        raw_norm = cell.get("normalized")
        conf = cell.get("confidence", 0.0)
        try:
            conf = max(0.0, min(1.0, float(conf)))
        except (ValueError, TypeError):
            conf = 0.0

        norm, ok = _coerce(f, raw_norm)
        if not ok:
            reasons.append(f"{name}: could not normalize value {raw_norm!r}")
            conf = min(conf, 0.3)

        fields[name] = norm
        evidence[name] = {"raw": cell.get("raw"), "confidence": conf,
                          "source_page": cell.get("source_page")}

        if conf < LOW_CONFIDENCE and norm is not None:
            reasons.append(f"{name}: low confidence ({conf:.2f})")
        if f["risk"] and norm is None:
            reasons.append(f"{name}: risk field is absent — confirm manually")

    return {
        "filename": filename,
        "fields": fields,
        "evidence": evidence,
        "needs_review": len(reasons) > 0,
        "review_reasons": reasons,
    }
