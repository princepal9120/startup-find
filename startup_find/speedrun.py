"""Speedrun Talent Network live source for startup-find.

Read-only, no auth. Fetches portfolio companies from:
https://speedrun-talent-network.com/api/v1/companies
and upserts them into local SQLite with source='speedrun'.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
import urllib.parse

from .db import get_conn, upsert

BASE = "https://speedrun-talent-network.com/api/v1"


def _get(path: str, params: dict | None = None) -> dict:
    url = BASE + path
    if params:
        url += "?" + "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"speedrun API error {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"speedrun API unreachable: {e.reason}") from e


def _map_company(c: dict) -> dict:
    location = c.get("location") or ""
    industries = c.get("industries") or []
    return {
        "source": "speedrun",
        "source_id": c.get("slug"),
        "name": c.get("name"),
        "slug": c.get("slug"),
        "website": c.get("url"),
        "one_liner": c.get("blurb"),
        "long_description": c.get("blurb"),
        "team_size": None,
        "batch": None,
        "status": "Active",
        "industry": ", ".join(industries) if industries else None,
        "subindustry": None,
        "all_locations": location,
        "is_hiring": c.get("open_roles", 0) > 0,
        "top_company": 0,
        "nonprofit": 0,
        "stage": None,
        "country": None,
        "latitude": None,
        "longitude": None,
        "founders": None,
        "year_founded": None,
        "funding_total_usd": None,
        "valuation_usd": None,
        "funded_date": None,
        "source_url": c.get("url"),
        "updated_at": None,
    }


def seed(db: str, limit: int | None = None) -> int:
    data = _get("/companies", {"limit": limit or 500})
    items = data.get("companies", [])
    if not items:
        return 0
    conn = get_conn(db)
    for c in items:
        upsert(conn, _map_company(c))
    conn.commit()
    conn.close()
    return len(items)
