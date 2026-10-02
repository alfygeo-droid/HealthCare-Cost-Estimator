from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import Flask, current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS tariffs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cghs_code TEXT NOT NULL,
  procedure_name TEXT NOT NULL,
  non_nabh_rate REAL,
  nabh_rate REAL,
  super_speciality_rate REAL,
  speciality TEXT,
  city_tier TEXT NOT NULL,
  source TEXT,
  source_date TEXT,
  UNIQUE(cghs_code, city_tier)
);
CREATE INDEX IF NOT EXISTS idx_tariffs_name ON tariffs(procedure_name);
CREATE INDEX IF NOT EXISTS idx_tariffs_code ON tariffs(cghs_code);

CREATE TABLE IF NOT EXISTS hospitals (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  city TEXT,
  city_tier TEXT,
  accreditation TEXT,
  room_general REAL,
  room_sharing REAL,
  room_private REAL,
  room_icu REAL,
  markup REAL DEFAULT 1.0,
  is_synthetic INTEGER DEFAULT 1,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS policies (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  policy_type TEXT,
  sum_insured REAL,
  deductible REAL,
  copay_percent REAL,
  room_limit REAL,
  pre_hospitalization_days INTEGER,
  post_hospitalization_days INTEGER,
  non_payable_percent REAL,
  is_synthetic INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS demo_bills (
  bill_id TEXT PRIMARY KEY,
  scenario_id TEXT,
  patient_id TEXT,
  hospital_id TEXT,
  procedure_code TEXT,
  admission_date TEXT,
  discharge_date TEXT,
  invoice_number TEXT,
  is_synthetic INTEGER DEFAULT 1,
  payload_json TEXT
);

CREATE TABLE IF NOT EXISTS demo_claims (
  claim_id TEXT PRIMARY KEY,
  scenario_id TEXT,
  patient_id TEXT,
  policy_id TEXT,
  hospital_id TEXT,
  bill_id TEXT,
  procedure_code TEXT,
  invoice_number TEXT,
  claim_date TEXT,
  claimed_amount REAL,
  approved_amount REAL,
  status TEXT,
  is_synthetic INTEGER DEFAULT 1,
  payload_json TEXT
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


def _sqlite_path(url: str) -> Path:
    if url.startswith("sqlite:///"):
        raw = url.replace("sqlite:///", "", 1)
        p = Path(raw)
        if not p.is_absolute():
            p = Path(__file__).resolve().parents[1] / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    raise RuntimeError(f"Unsupported DATABASE_URL for local engine: {url}")


def get_conn() -> sqlite3.Connection:
    if "db" not in g:
        path = _sqlite_path(current_app.config["DATABASE_URL"])
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@contextmanager
def db_session():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db(app: Flask) -> None:
    path = _sqlite_path(app.config["DATABASE_URL"])
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

    @app.teardown_appcontext
    def close_db(_exc=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def get_meta(key: str, default: str | None = None) -> str | None:
    conn = get_conn()
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(key: str, value: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
