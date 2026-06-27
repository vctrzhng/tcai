# TCAI — Contract Intelligence Platform

Upload procurement contracts → automatically extract key terms into a consistent
schema → store them as a growing dataset → compare vendors, benchmark terms, and
surface unfavorable clauses.

The value is **cross-contract intelligence** (comparison, benchmarking,
decision support), not "chat with a contract."

## Layout

```
tcai/
├── ground_truth.json        Answer key: expected normalized values per mock contract
├── mock_contracts/          6 sample contracts (PDF + DOCX), easy → hard
├── generators/              Scripts that regenerate the mock contracts (optional)
│   ├── contract_content.py  Source text for the mocks
│   ├── make_pdfs.py         Regenerate PDFs + export DOCX content
│   └── make_docx.js         Regenerate DOCX (run after make_pdfs.py)
└── extractor/               The application
    ├── schema.py            SINGLE SOURCE OF TRUTH (FIELD_SPEC drives everything)
    ├── extraction.py        Ingestion (PDF/DOCX → text) + Claude tool-use call
    ├── db.py                SQLite storage (table generated from FIELD_SPEC)
    ├── analysis.py          Deterministic compare / rank / flag / benchmark
    ├── main.py              FastAPI app (upload, list, detail, delete, analysis)
    ├── mock_llm.py          Offline test stub (no API key needed)
    ├── run_harness.py       Run the pipeline over mocks, score vs ground truth
    ├── README.md            Extraction module docs
    └── BACKEND_README.md    Storage + API docs
```

## Quick start

```bash
# 1. system deps (text extraction): poppler-utils + pandoc
#    macOS:  brew install poppler pandoc
#    Ubuntu: sudo apt install poppler-utils pandoc

# 2. python deps
pip install -r requirements.txt

# 3a. prove the pipeline works WITHOUT an API key (uses the mock extractor)
cd extractor
python run_harness.py --mock

# 3b. run for real
export ANTHROPIC_API_KEY=sk-ant-...
python run_harness.py                 # scores real Claude extraction vs ground truth

# 4. run the API
uvicorn main:app --reload             # docs at http://127.0.0.1:8000/docs
#   or, no key, mock extraction keyed to the 6 sample files:
TCAI_MOCK=1 uvicorn main:app --reload
```

## How it fits together

1. **schema.py** defines every field once (`FIELD_SPEC`). It generates the Claude
   tool schema, the prompt's normalization rules, the validation logic, and the
   SQLite columns — so nothing can drift out of sync.
2. **extraction.py** turns a contract file into a record of
   `{normalized value, raw quote, confidence, source page}` per field, flagging
   low-confidence and absent-risk fields for human review.
3. **db.py** stores typed columns (fast to query) plus the full evidence blob
   (provenance).
4. **analysis.py** runs deterministic comparison/benchmark/flagging over the
   dataset. The numbers come from here, never from an LLM.
5. **main.py** exposes it all over HTTP.

## The web UI

A no-build single-page app in `frontend/` (plain HTML/CSS/JS), styled to match
the personal-site design system. FastAPI serves it automatically:

```bash
cd extractor
TCAI_MOCK=1 uvicorn main:app --reload      # no API key needed to click around
# open http://127.0.0.1:8000
```

Four tabs: Upload (drag-drop → extract → review with flagged fields), Library
(the growing dataset table), Compare (side-by-side with best/worst highlights),
and Insights (pick a lens + voice → grounded insights + recommendation).

## Status

Built and tested end to end: mock data + ground truth, extraction, storage,
analysis, insight narrator with grounding verification, REST API, and the web UI.
