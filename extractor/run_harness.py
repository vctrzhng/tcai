# -*- coding: utf-8 -*-
"""
run_harness.py  --  run the extraction pipeline over all mock contracts and
score against ground truth.

MODES:
  python run_harness.py            # LIVE: uses Claude (needs ANTHROPIC_API_KEY)
  python run_harness.py --mock     # PLUMBING: uses mock_llm (no key needed)

The --mock run proves ingestion -> validation -> needs_review -> scoring all
work. Swap to live to measure real extraction accuracy.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import SCORED_FIELDS
from extraction import ingest_text, extract_contract, _call_claude

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GT_PATH = os.path.join(REPO_ROOT, "ground_truth.json")
CONTRACT_DIR = os.path.join(REPO_ROOT, "mock_contracts")

GT = json.load(open(GT_PATH))


def values_match(field, got, want):
    if want is None:
        return got is None
    if isinstance(want, str) and isinstance(got, str):
        g, w = got.strip().lower(), want.strip().lower()
        return g == w or w in g or g in w
    if isinstance(want, float) or isinstance(got, float):
        try:
            return abs(float(got) - float(want)) < 1e-6
        except (TypeError, ValueError):
            return False
    return got == want


def run(mock=False):
    field_hits = {f: [0, 0] for f in SCORED_FIELDS}
    overall_c = overall_t = 0
    review_count = 0
    print(f"{'CONTRACT':<34}{'CORRECT':>8}{'TOTAL':>7}{'ACC':>6}{'REVIEW':>8}")
    print("-" * 63)

    for c in GT["contracts"]:
        fn = c["filename"]
        want_all = c["normalized"]
        path = os.path.join(CONTRACT_DIR, fn)
        text = ingest_text(path)

        if mock:
            from mock_llm import make_mock_call
            call_fn = make_mock_call(fn)
        else:
            call_fn = _call_claude

        rec = extract_contract(text, filename=fn, call_fn=call_fn)
        got_all = rec["fields"]
        if rec["needs_review"]:
            review_count += 1

        correct = total = 0
        misses = []
        for f in SCORED_FIELDS:
            if f not in want_all:
                continue
            total += 1
            field_hits[f][1] += 1
            if values_match(f, got_all.get(f), want_all[f]):
                correct += 1
                field_hits[f][0] += 1
            else:
                misses.append(f"{f}: got {got_all.get(f)!r} want {want_all[f]!r}")
        overall_c += correct
        overall_t += total
        flag = "REVIEW" if rec["needs_review"] else "ok"
        print(f"{fn:<34}{correct:>8}{total:>7}{correct/total:>5.0%}{flag:>8}")
        for m in misses:
            print(f"    MISS  {m}")
        for r in rec["review_reasons"]:
            print(f"    flag  {r}")

    print("-" * 63)
    print(f"{'OVERALL':<34}{overall_c:>8}{overall_t:>7}{overall_c/overall_t:>5.0%}"
          f"{review_count:>6} flagged")
    print("\nPER-FIELD ACCURACY:")
    for f in SCORED_FIELDS:
        c_, t_ = field_hits[f]
        if t_:
            print(f"  {f:<30}{c_}/{t_}  {c_/t_:>4.0%}")


if __name__ == "__main__":
    run(mock="--mock" in sys.argv)
