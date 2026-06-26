# TCAI Backend (storage + API + analysis)

Turns extraction records into a queryable, growing dataset and serves the
comparison/benchmark logic.

## Files

| File | Role |
|------|------|
| `db.py` | SQLite layer. The `contracts` table is **generated from `FIELD_SPEC`** (typed columns) + a `raw_json` evidence blob. Store / list / get / delete / fetch-for-analysis. |
| `analysis.py` | Deterministic cross-contract logic: `compare`, `rank_pricing`, `unfavorable_terms`, `benchmark`. The product's point of view lives here. |
| `main.py` | FastAPI app. Upload→extract→store + list/detail/delete + analysis endpoints. |

(Depends on `schema.py` and `extraction.py` from the extraction module.)

## Run

```bash
cd extractor
pip install fastapi "uvicorn[standard]" python-multipart anthropic

# real extraction:
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn main:app --reload          # http://127.0.0.1:8000/docs

# OR wire up the UI without a key (mock extractor keyed to the 6 mock files):
TCAI_MOCK=1 uvicorn main:app --reload
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/contracts/upload` | multipart `files=`; extracts + stores each; returns fields + `needs_review` |
| GET | `/contracts` | dataset list (typed fields) |
| GET | `/contracts/{id}` | full record incl. `evidence` (raw quote, confidence, page) |
| DELETE | `/contracts/{id}` | remove one |
| POST | `/analysis/compare` | body `{contract_ids?, fields?}` → table + best/worst highlights |
| GET | `/analysis/best-pricing` | buyer-favorability ranking (see `score_pricing`) |
| GET | `/analysis/unfavorable` | rule-based risk flags with severity |
| GET | `/analysis/benchmark` | dataset-wide numeric stats + categorical distributions |

## Design notes

- **SQLite, no vector DB.** Your queries are structured aggregations, which is
  exactly SQL's job. A vector DB would not help "which contract has the best
  payment terms."
- **`score_pricing` and the unfavorable rules are explicit and tunable** — edit
  the heuristic in `analysis.py`. That heuristic is your differentiation; don't
  hide it in an LLM.
- **`raw_json` keeps full provenance** so the UI can show the source quote +
  page for every extracted value (audit trail legal users will demand).
- **Numbers come from this layer, never an LLM.** When you add the insight
  narrator later, feed it these computed tables and forbid it from introducing
  data not present in them.
