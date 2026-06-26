# -*- coding: utf-8 -*-
"""
extraction.py  --  contract text -> structured record via Claude tool use.

Pipeline:
    ingest_text(path)           PDF/DOCX -> plain text with [PAGE n] markers
    extract_contract(text, fn)  text -> validated, normalized record

The live Claude call is isolated in _call_claude so the rest is testable
without network/keys. Set ANTHROPIC_API_KEY in your environment to run it.
"""
import json
import os
import subprocess

from schema import (build_tool_schema, build_rules_text, validate_and_normalize)

MODEL = os.environ.get("EXTRACTOR_MODEL", "claude-sonnet-4-6")
# Sonnet is the cost/accuracy sweet spot for extraction. For the hardest
# contracts you can bump to claude-opus-4-8, or do a two-pass: Sonnet first,
# re-run only needs_review==True contracts on Opus.

SYSTEM_PROMPT = f"""You are a meticulous contract analyst extracting structured terms \
for a procurement comparison database.

Rules:
- Extract ONLY what the contract explicitly states. Never infer, guess, or \
fill in market-standard defaults.
- Read the ENTIRE document before deciding each field. Terms are sometimes \
granted in one section and restricted in another — report the NET EFFECT.
- For each field provide: raw (exact quote, UNDER 15 words, or null), \
normalized (per the rules below), confidence (0.0-1.0), and source_page.
- If a term is genuinely absent, set normalized to null and confidence to 0.
- Use confidence below 0.6 when wording is ambiguous, conflicting, or you had \
to interpret.

Normalization rules:
{build_rules_text()}

Call record_contract_terms exactly once with all fields."""


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
def ingest_text(path: str) -> str:
    """Extract plain text with [PAGE n] markers.

    PDFs: real per-page markers (pdftotext per page) -> enables source_page.
    DOCX: no reliable page boundaries from the XML, so the whole doc is [PAGE 1].
          (source_page will be approximate for DOCX — a known limitation.)
    """
    lower = path.lower()
    if lower.endswith(".pdf"):
        return _ingest_pdf(path)
    if lower.endswith(".docx"):
        text = subprocess.run(["pandoc", path, "-t", "plain"],
                              capture_output=True, text=True).stdout
        return "[PAGE 1]\n" + text.strip()
    # plain text fallback
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return "[PAGE 1]\n" + fh.read()


def _ingest_pdf(path: str) -> str:
    # number of pages
    info = subprocess.run(["pdfinfo", path], capture_output=True, text=True).stdout
    pages = 1
    for line in info.splitlines():
        if line.lower().startswith("pages:"):
            pages = int(line.split(":")[1].strip())
            break
    chunks = []
    for p in range(1, pages + 1):
        page_text = subprocess.run(
            ["pdftotext", "-layout", "-f", str(p), "-l", str(p), path, "-"],
            capture_output=True, text=True).stdout.strip()
        chunks.append(f"[PAGE {p}]\n{page_text}")
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Claude call (isolated)
# ---------------------------------------------------------------------------
def _call_claude(text: str) -> dict:
    """Return the raw tool_input dict from Claude. Requires ANTHROPIC_API_KEY."""
    import anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    tool = build_tool_schema()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_contract_terms"},
        messages=[{
            "role": "user",
            "content": f"<contract>\n{text}\n</contract>\n\n"
                       f"Extract the terms by calling record_contract_terms.",
        }],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "record_contract_terms":
            return block.input
    raise RuntimeError("Model did not return the expected tool_use block.")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def extract_contract(text: str, filename: str = "", call_fn=_call_claude) -> dict:
    """Full extraction for one contract's text. `call_fn` is injectable for tests.

    Returns the validate_and_normalize() record (fields/evidence/needs_review).
    """
    raw = call_fn(text)
    record = validate_and_normalize(raw, filename=filename)
    return record


def extract_file(path: str, call_fn=_call_claude) -> dict:
    text = ingest_text(path)
    return extract_contract(text, filename=os.path.basename(path), call_fn=call_fn)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python extraction.py <contract.pdf|docx>")
        sys.exit(1)
    rec = extract_file(sys.argv[1])
    print(json.dumps(rec, indent=2, ensure_ascii=False))
