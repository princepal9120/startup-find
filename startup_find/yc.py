"""YC seeder — pulls Y Combinator's public Algolia dataset into SQLite.

The Algolia APP_ID / API_KEY below are public constants shipped in the
ExploreYC open-source backend (backend/scraper_service.py). They are not
secrets and require no account.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

from .db import get_conn, upsert

ALGOLIA_URL = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"
ALGOLIA_APP_ID = "45BWZJ1SGC"
ALGOLIA_API_KEY = (
    "NzllNTY5MzJiZGM2OTY2ZTQwMDEzOTNhYWZiZGRjODlhYzVkNjBmOGRjNzJiMWM4"
    "ZTU0ZDlhYTZjOTJiMjlhMWFuYWx5dGljc1RhZ3M9eWNkYyZyZXN0cmljdEluZGlj"
    "ZXM9WUNDb21wYW55X3Byb2R1Y3Rpb24lMkNZQ0NvbXBhbnlfQnlfTGF1bmNoX0Rh"
    "dGVfcHJvZHVjdGlvbiZ0YWdGaWx0ZXJzPSU1QiUyMnljZGNfcHVibGljJTIyJTVE"
)


def _algolia_post(payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    url = (
        f"{ALGOLIA_URL}?x-algolia-agent=Algolia%20for%20JavaScript%20(3.35.1)"
        f"&x-algolia-application-id={ALGOLIA_APP_ID}&x-algolia-api-key={ALGOLIA_API_KEY}"
    )
    req = urllib.request.Request(
        url, data=body, headers={
            "Content-Type": "application/json",
            "Origin": "https://www.ycombinator.com",
            "Referer": "https://www.ycombinator.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def seed(db_path: str, batches: list[str] | None, hits_per_page: int, max_pages: int):
    conn = get_conn(db_path)
    facet_filters = []
    if batches:
        facet_filters.append([f"batch:{b}" for b in batches])
    total = 0
    page = 0
    while page < max_pages:
        params = {
            "facetFilters": json.dumps(facet_filters) if facet_filters else "",
            "facets": json.dumps(["batch", "industries", "regions", "isHiring", "top_company"]),
            "hitsPerPage": hits_per_page,
            "maxValuesPerFacet": 1000,
            "page": page,
            "query": "",
            "restrictIndices": "YCCompany_production,YCCompany_By_Launch_Date_production",
            "tagFilters": '["ycdc_public"]',
        }
        body = {"requests": [{"indexName": "YCCompany_production", "params": urlencode(params)}]}
        try:
            data = _algolia_post(body)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Algolia HTTP error: {e.code}") from e
        results = (data.get("results") or [{}])[0]
        hits = results.get("hits", [])
        if not hits:
            break
        for c in hits:
            def _str(v):
                if isinstance(v, list):
                    return ", ".join(str(x) for x in v)
                return v
            upsert(conn, {
                "id": c.get("id"), "source": "yc", "source_id": str(c.get("id")),
                "name": c.get("name"), "slug": c.get("slug"), "website": c.get("website"),
                "one_liner": c.get("one_liner"), "long_description": c.get("long_description"),
                "team_size": c.get("team_size"), "batch": c.get("batch"), "status": c.get("status"),
                "industry": _str(c.get("industries")), "subindustry": _str(c.get("subindustry")),
                "all_locations": c.get("all_locations"),
                "is_hiring": bool(c.get("isHiring")), "top_company": bool(c.get("topCompany")),
                "nonprofit": bool(c.get("nonprofit")), "stage": c.get("stage"),
                "country": c.get("country"), "latitude": c.get("latitude"),
                "longitude": c.get("longitude"), "founders": c.get("founders"),
                "year_founded": c.get("yearFounded"),
                "funding_total_usd": c.get("fundingTotalUsd"),
                "valuation_usd": c.get("valuationUsd"),
                "funded_date": c.get("fundedDate"), "source_url": c.get("url"),
            })
            total += 1
        conn.commit()
        yield total, page + 1
        if len(hits) < hits_per_page:
            break
        page += 1
        time.sleep(0.5)
    conn.close()
