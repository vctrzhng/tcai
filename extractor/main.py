from __future__ import annotations
# -*- coding: utf-8 -*-
"""
main.py  --  FastAPI backend for the Contract Intelligence MVP.

Run:
    cd extractor
    export ANTHROPIC_API_KEY=sk-ant-...
    uvicorn main:app --reload
    # docs at http://127.0.0.1:8000/docs

Set TCAI_MOCK=1 to use the mock extractor (no API key) for wiring up the UI.
"""
import os
import shutil
import tempfile

from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

import db
import analysis
import insights as insights_mod
from extraction import ingest_text, extract_contract, _call_claude

# Ensure the table exists as soon as this module is imported (covers TestClient,
# workers, and any entrypoint that doesn't trigger lifespan).
db.init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="TCAI — Contract Intelligence", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

USE_MOCK = os.environ.get("TCAI_MOCK") == "1"


def _extractor_for(filename: str):
    """Pick the real Claude call, or a mock keyed by filename for dev."""
    if not USE_MOCK:
        return _call_claude
    from mock_llm import make_mock_call, GT_BY_FILE
    if filename in GT_BY_FILE:
        return make_mock_call(filename)
    # unknown file in mock mode: return empty extraction
    return lambda text: {f["name"]: {"raw": None, "normalized": None,
                                     "confidence": 0.0, "source_page": None}
                         for f in __import__("schema").FIELD_SPEC}


# --------------------------------------------------------------- contracts
@app.post("/contracts/upload")
async def upload(files: list[UploadFile] = File(...)):
    results = []
    for uf in files:
        suffix = os.path.splitext(uf.filename)[1] or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(uf.file, tmp)
            tmp_path = tmp.name
        try:
            text = ingest_text(tmp_path)
            rec = extract_contract(text, filename=uf.filename,
                                   call_fn=_extractor_for(uf.filename))
            cid = db.insert_record(rec)
            results.append({"contract_id": cid, "filename": uf.filename,
                            "needs_review": rec["needs_review"],
                            "review_reasons": rec["review_reasons"],
                            "fields": rec["fields"]})
        except Exception as e:
            results.append({"filename": uf.filename, "error": str(e)})
        finally:
            os.unlink(tmp_path)
    return {"uploaded": results}


@app.get("/contracts")
def list_contracts():
    return {"contracts": db.list_contracts()}


@app.get("/contracts/{contract_id}")
def get_contract(contract_id: str):
    rec = db.get_contract(contract_id)
    if not rec:
        raise HTTPException(404, "Not found")
    return rec


@app.delete("/contracts/{contract_id}")
def delete_contract(contract_id: str):
    if not db.delete_contract(contract_id):
        raise HTTPException(404, "Not found")
    return {"deleted": contract_id}


# --------------------------------------------------------------- analysis
class CompareReq(BaseModel):
    contract_ids: Optional[List[str]] = None
    fields: Optional[List[str]] = None


@app.post("/analysis/compare")
def compare(req: CompareReq):
    return analysis.compare(req.contract_ids, req.fields)


@app.get("/analysis/best-pricing")
def best_pricing():
    return {"ranking": analysis.rank_pricing()}


@app.get("/analysis/unfavorable")
def unfavorable():
    return {"flags": analysis.unfavorable_terms()}


@app.get("/analysis/benchmark")
def benchmark():
    return analysis.benchmark()


class InsightReq(BaseModel):
    kind: str = "compare"               # compare | best_pricing | unfavorable | benchmark
    contract_ids: Optional[List[str]] = None
    voice: str = "buyer_advocate"       # buyer_advocate | neutral


@app.post("/analysis/insights")
def insights(req: InsightReq):
    if req.kind not in ("compare", "best_pricing", "unfavorable", "benchmark"):
        raise HTTPException(400, "kind must be one of: compare, best_pricing, "
                                 "unfavorable, benchmark")
    call_fn = insights_mod._mock_insights if USE_MOCK else insights_mod._call_claude_insights
    return insights_mod.generate_insights(req.kind, req.contract_ids, req.voice,
                                          call_fn=call_fn)


# --------------------------------------------------------------- frontend
# Serve the static UI at the root. Mounted LAST so /contracts and /analysis
# routes take priority. The frontend lives one level up from extractor/.
_FRONTEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "frontend")
if os.path.isdir(_FRONTEND):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")
