# Contract Extraction Module

The core extraction layer: contract file -> structured, normalized record.

## Files

| File | Role |
|------|------|
| `schema.py` | **Single source of truth.** `FIELD_SPEC` defines every field. Generates the Claude tool schema, the prompt rules, and the validation logic. **Edit fields here only.** |
| `extraction.py` | Ingestion (PDF/DOCX -> text with `[PAGE n]` markers) + the Claude tool-use call + orchestration. |
| `mock_llm.py` | Fake Claude response for testing without an API key. Plumbing test only. |
| `run_harness.py` | Runs the pipeline over all mock contracts and scores vs ground truth. |

## Run the plumbing test (no API key)

```bash
cd extractor
python run_harness.py --mock
```

Proves ingestion -> validation -> needs_review -> scoring all work. The
deliberate errors in `mock_llm.py` make it score ~96% so you can see the
miss-reporting and review flags in action.

## Run live (real extraction accuracy)

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...      # your key
cd extractor
python run_harness.py                     # scores real Claude extraction
```

Or extract a single file:

```bash
python extraction.py ../mock_contracts/04_initech_services_MESSY.pdf
```

Default model is `claude-sonnet-4-6` (good cost/accuracy for extraction).
Override with `export EXTRACTOR_MODEL=claude-opus-4-8` for harder docs.

## What a record looks like

```json
{
  "filename": "04_initech_services_MESSY.pdf",
  "fields": { "vendor_name": "Initech Services Group", "payment_terms_days": 60, ... },
  "evidence": { "payment_terms_days": {"raw": "sixty (60) days after ... receipt",
                                       "confidence": 0.95, "source_page": 1}, ... },
  "needs_review": true,
  "review_reasons": ["governing_law: low confidence (0.55)"]
}
```

`fields` -> goes into SQLite + drives comparison. `evidence` -> provenance for
the UI (clickable page + quote). `needs_review` -> route to human in the upload
review panel.

## Design notes

- **Full-contract pass**, not clause-by-clause: one call, whole document in
  context, so cross-section conflicts (e.g. termination granted in §5,
  restricted in §11) are resolved correctly.
- **Forced tool use** (`tool_choice` = the tool) guarantees schema-shaped
  output. Upgrade path: Anthropic's native structured outputs / `strict: true`
  for token-level schema guarantees — add `"strict": True` in `build_tool_schema`.
- **DOCX page numbers are approximate** (no reliable page breaks in the XML);
  PDFs get true per-page markers.
- **needs_review fires** when any field is low-confidence, any risk field is
  absent, or a value failed to normalize. This is how you ship at 80% honestly.
