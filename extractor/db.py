# -*- coding: utf-8 -*-
"""
db.py  --  SQLite storage for contract records.

The table is GENERATED from FIELD_SPEC so storage can never drift from
extraction. Typed columns for every field (fast filter/sort/aggregate) PLUS
a raw_json blob holding the full evidence (raw quotes, confidence, page) so
nothing is lost.
"""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from schema import FIELD_SPEC

DB_PATH = os.environ.get("TCAI_DB", os.path.join(os.path.dirname(__file__), "contracts.db"))

# Map FIELD_SPEC types -> SQLite column types
_SQL_TYPE = {"str": "TEXT", "enum": "TEXT", "int": "INTEGER",
             "float": "REAL", "bool": "INTEGER"}  # bool stored as 0/1


def _columns_sql() -> str:
    cols = [f'"{f["name"]}" {_SQL_TYPE[f["type"]]}' for f in FIELD_SPEC]
    return ",\n  ".join(cols)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    conn.executescript(f"""
    CREATE TABLE IF NOT EXISTS contracts (
      contract_id   TEXT PRIMARY KEY,
      filename      TEXT,
      uploaded_at   TEXT,
      needs_review  INTEGER,
      review_reasons TEXT,        -- json list
      raw_json      TEXT,         -- full evidence blob
      {_columns_sql()}
    );
    """)
    conn.commit()
    conn.close()


def insert_record(record: dict) -> str:
    """Store a validate_and_normalize() record. Returns contract_id."""
    cid = str(uuid.uuid4())
    fields = record["fields"]
    base = {
        "contract_id": cid,
        "filename": record.get("filename"),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "needs_review": 1 if record.get("needs_review") else 0,
        "review_reasons": json.dumps(record.get("review_reasons", [])),
        "raw_json": json.dumps(record.get("evidence", {}), ensure_ascii=False),
    }
    # add typed field columns, coercing bool -> 0/1
    for f in FIELD_SPEC:
        v = fields.get(f["name"])
        if f["type"] == "bool" and v is not None:
            v = 1 if v else 0
        base[f["name"]] = v

    cols = ", ".join(f'"{k}"' for k in base)
    ph = ", ".join("?" for _ in base)
    conn = connect()
    conn.execute(f"INSERT INTO contracts ({cols}) VALUES ({ph})", list(base.values()))
    conn.commit()
    conn.close()
    return cid


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # decode bool columns back to true/false/None
    for f in FIELD_SPEC:
        if f["type"] == "bool" and d.get(f["name"]) is not None:
            d[f["name"]] = bool(d[f["name"]])
    d["needs_review"] = bool(d.get("needs_review"))
    if d.get("review_reasons"):
        d["review_reasons"] = json.loads(d["review_reasons"])
    return d


def list_contracts() -> list[dict]:
    conn = connect()
    rows = conn.execute("SELECT * FROM contracts ORDER BY uploaded_at DESC").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_contract(contract_id: str) -> dict | None:
    conn = connect()
    row = conn.execute("SELECT * FROM contracts WHERE contract_id = ?",
                       (contract_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = _row_to_dict(row)
    if d.get("raw_json"):
        d["evidence"] = json.loads(d["raw_json"])
    return d


def delete_contract(contract_id: str) -> bool:
    conn = connect()
    cur = conn.execute("DELETE FROM contracts WHERE contract_id = ?", (contract_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def fetch_for_analysis(contract_ids: list[str] | None = None) -> list[dict]:
    """Rows as plain dicts for the analysis layer (typed fields, no blob)."""
    conn = connect()
    if contract_ids:
        ph = ", ".join("?" for _ in contract_ids)
        rows = conn.execute(
            f"SELECT * FROM contracts WHERE contract_id IN ({ph})", contract_ids
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM contracts").fetchall()
    conn.close()
    out = []
    for r in rows:
        d = _row_to_dict(r)
        d.pop("raw_json", None)
        out.append(d)
    return out


if __name__ == "__main__":
    init_db()
    print("Initialized DB at", DB_PATH)
