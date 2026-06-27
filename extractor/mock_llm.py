# -*- coding: utf-8 -*-
"""
mock_llm.py  --  fake Claude tool response for testing the pipeline without an
API key. It shapes ground-truth values into the {raw,normalized,confidence,
source_page} structure the real model returns, then injects a few DELIBERATE
errors / low-confidence cells so the harness demonstrates miss-reporting and
the needs_review flag.

This is a PLUMBING test, not an accuracy measurement. Real accuracy requires
the live model (set ANTHROPIC_API_KEY and use extraction._call_claude).
"""
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GT_PATH = os.path.join(REPO_ROOT, "ground_truth.json")

GT = json.load(open(GT_PATH))
GT_BY_FILE = {c["filename"]: c["normalized"] for c in GT["contracts"]}

# Deliberate corruptions keyed by filename -> {field: (bad_value, confidence)}
# Chosen to mimic plausible model mistakes on the hard contracts.
CORRUPTIONS = {
    "04_initech_services_MESSY.pdf": {
        "termination_notice_days": (90, 0.4),     # wrong (truth 120), low conf
        "governing_law": ("Texas", 0.55),         # right value but low conf (buried in boilerplate)
    },
    "05_umbrella_supply_MESSY.docx": {
        "minimum_spend_period": ("annual", 0.5),  # wrong (truth monthly), low conf
        "payment_terms_days": (30, 0.45),         # wrong (truth 0 / upon receipt)
    },
    "03_globex_saas_MODERATE.docx": {
        "liability_cap_type": ("fixed_amount", 0.5),  # wrong (truth fees_paid_12mo)
    },
}


def make_mock_call(filename: str):
    """Return a call_fn(text)->tool_input that produces a realistic response
    for the given filename."""
    truth = GT_BY_FILE[filename]
    corrupt = CORRUPTIONS.get(filename, {})

    def call_fn(text: str) -> dict:
        out = {}
        from schema import FIELD_SPEC
        for f in FIELD_SPEC:
            name = f["name"]
            val = truth.get(name)
            conf = 0.95 if val is not None else 0.0
            if name in corrupt:
                val, conf = corrupt[name]
            out[name] = {
                "raw": (str(truth.get(name))[:40] if truth.get(name) is not None else None),
                "normalized": val,
                "confidence": conf,
                "source_page": 1,
            }
        return out

    return call_fn
