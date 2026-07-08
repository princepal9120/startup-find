"""SQLite storage for startup-find. Local-first, stdlib only."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

DEFAULT_DB = os.path.expanduser("~/.startup-find/yc.db")

SCHEMA = """CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY,
    source TEXT DEFAULT 'yc',
    source_id TEXT,
    name TEXT, slug TEXT, website TEXT,
    one_liner TEXT, long_description TEXT,
    team_size INTEGER, batch TEXT, status TEXT,
    industry TEXT, subindustry TEXT, all_locations TEXT,
    is_hiring INTEGER, top_company INTEGER, nonprofit INTEGER,
    stage TEXT, country TEXT,
    latitude REAL, longitude REAL,
    founders TEXT, year_founded INTEGER,
    funding_total_usd REAL, valuation_usd REAL,
    funded_date TEXT, source_url TEXT,
    updated_at TEXT
)"""


def get_conn(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def coerce(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["is_hiring"] = bool(d.get("is_hiring"))
    d["top_company"] = bool(d.get("top_company"))
    d["nonprofit"] = bool(d.get("nonprofit"))
    return d


def upsert(conn: sqlite3.Connection, c: dict) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO companies
           (id, source, source_id, name, slug, website, one_liner, long_description,
            team_size, batch, status, industry, subindustry, all_locations,
            is_hiring, top_company, nonprofit, stage, country,
            latitude, longitude, founders, year_founded,
            funding_total_usd, valuation_usd, funded_date, source_url, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            c.get("id"), c.get("source"), c.get("source_id"),
            c.get("name"), c.get("slug"), c.get("website"),
            c.get("one_liner"), c.get("long_description"),
            c.get("team_size"), c.get("batch"), c.get("status"),
            c.get("industry"), c.get("subindustry"), c.get("all_locations"),
            1 if c.get("is_hiring") else 0,
            1 if c.get("top_company") else 0,
            1 if c.get("nonprofit") else 0,
            c.get("stage"), c.get("country"),
            c.get("latitude"), c.get("longitude"),
            c.get("founders"), c.get("year_founded"),
            c.get("funding_total_usd"), c.get("valuation_usd"),
            c.get("funded_date"), c.get("source_url"),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


# ---- query helpers ----

def q_companies(db_path, limit, offset, batch, industry, country,
                is_hiring, top_company, search, source=None):
    conn = get_conn(db_path)
    where, params = [], []
    if source:
        where.append("source = ?"); params.append(source)
    if batch:
        where.append("batch = ?"); params.append(batch)
    if industry:
        where.append("industry LIKE ?"); params.append(f"%{industry}%")
    if country:
        where.append("country = ?"); params.append(country)
    if is_hiring is not None:
        where.append("is_hiring = ?"); params.append(1 if is_hiring else 0)
    if top_company is not None:
        where.append("top_company = ?"); params.append(1 if top_company else 0)
    if search:
        where.append("(name LIKE ? OR one_liner LIKE ? OR long_description LIKE ?)")
        params += [f"%{search}%"] * 3
    sql = "SELECT * FROM companies"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY batch DESC, name LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = [coerce(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def q_stats(db_path):
    conn = get_conn(db_path)
    total = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    hiring = conn.execute("SELECT COUNT(*) FROM companies WHERE is_hiring=1").fetchone()[0]
    by_source = dict(conn.execute(
        "SELECT source, COUNT(*) c FROM companies GROUP BY source").fetchall())
    by_batch = dict(conn.execute(
        "SELECT batch, COUNT(*) c FROM companies WHERE batch IS NOT NULL "
        "GROUP BY batch ORDER BY batch DESC").fetchall())
    by_industry = dict(conn.execute(
        "SELECT industry, COUNT(*) c FROM companies WHERE industry IS NOT NULL "
        "GROUP BY industry ORDER BY c DESC LIMIT 15").fetchall())
    conn.close()
    return {"total": total, "hiring": hiring, "by_source": by_source,
            "by_batch": by_batch, "by_industry_top15": by_industry}


def q_batches(db_path):
    conn = get_conn(db_path)
    rows = conn.execute(
        "SELECT DISTINCT batch FROM companies WHERE batch IS NOT NULL "
        "ORDER BY batch DESC").fetchall()
    conn.close()
    return [r["batch"] for r in rows]


def q_company(db_path, cid=None, slug=None):
    conn = get_conn(db_path)
    row = (conn.execute("SELECT * FROM companies WHERE slug = ?", (slug,)).fetchone()
           if slug else conn.execute("SELECT * FROM companies WHERE id = ?", (cid,)).fetchone())
    conn.close()
    return coerce(row) if row else None
