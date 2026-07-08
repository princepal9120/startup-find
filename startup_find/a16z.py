"""a16z portfolio seeder.

Faithfully ported from ExploreYC's backend/a16z_scraper_service.py
(github.com/KonstantinMB/exploreyc). The a16z portfolio page ships its full
dataset inline as a JS global; we fetch + parse it (no API key, no browser).

Differences from upstream: stdlib urllib instead of `requests`; a16z ids are
offset into a reserved block (1_000_000+) so they never collide with YC ids.
"""
from __future__ import annotations

import html
import json
import re
import urllib.request
from typing import Optional

from .db import get_conn, upsert

PORTFOLIO_URL = "https://a16z.com/portfolio/"
SOURCE = "a16z"
A16Z_ID_OFFSET = 1_000_000  # reserved block so a16z ids never collide with YC ids
_EXIT_STAGES = {"IPO", "M&A", "SPAC", "DPO", "EXIT"}


def _slugify(value: str) -> str:
    value = html.unescape(value or "").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value


def _first_nonempty(*vals) -> Optional[str]:
    for v in vals:
        if v not in (None, "", []):
            return v
    return None


def fetch_html() -> str:
    req = urllib.request.Request(
        PORTFOLIO_URL, headers={
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
            "Accept": "text/html,application/xhtml+xml",
        })
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_entries(html_text: str) -> list[dict]:
    m = re.search(r"window\.a16z_portfolio_companies\s*=\s*(\[.*?\])\s*;",
                  html_text, re.DOTALL)
    if not m:
        raise ValueError("window.a16z_portfolio_companies not found — a16z page layout may have changed")
    entries = json.loads(m.group(1))

    # Richer per-company attributes (exits ticker), keyed by native id.
    dom_by_id: dict[str, dict] = {}
    for raw in re.findall(r"data-company='(\\{.*?\\})'", html_text, re.DOTALL):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            try:
                obj = json.loads(html.unescape(raw))
            except json.JSONDecodeError:
                continue
        if obj.get("id") is not None:
            dom_by_id[str(obj["id"])] = obj
    for e in entries:
        extra = dom_by_id.get(str(e.get("id")))
        if extra:
            e["_dom"] = extra
    return entries


def _derive_exit(entry: dict, dom: dict):
    stages = set(entry.get("stages") or [])
    acquirer = entry.get("acquirer")
    ticker = entry.get("ticker_symbol")
    if acquirer or "M&A" in stages:
        return "M&A", "Acquired"
    if ticker or "IPO" in stages:
        return "IPO", "Public"
    if "SPAC" in stages:
        return "SPAC", "Public"
    if entry.get("exit_date") or (stages & _EXIT_STAGES):
        return "Exit", "Exited"
    return None, "Active"


def _map_entry(entry: dict, seen_slugs: set) -> dict:
    dom = entry.get("_dom") or {}
    native_id = str(entry.get("id"))
    name = (_first_nonempty(dom.get("name"), entry.get("title"),
             dom.get("display_name"), dom.get("post_title")) or f"a16z-{native_id}")

    slug = None
    permalink = dom.get("permalink")
    if permalink:
        mslug = re.search(r"/companies/([^/]+)/?", permalink)
        if mslug:
            slug = mslug.group(1)
    slug = slug or _slugify(name) or f"a16z-{native_id}"
    if slug in seen_slugs:
        slug = f"{slug}-{native_id}"
    seen_slugs.add(slug)

    verticals_raw = dom.get("verticals") or ""
    verticals = [v.strip() for v in re.split(r"[;,]", verticals_raw) if v.strip()]
    focus_areas = dom.get("focus_areas") or []
    industries = list(dict.fromkeys([*focus_areas, *verticals]))
    industry = industries[0] if industries else None

    year = entry.get("year_founded")
    try:
        year_founded = int(year) if year not in (None, "") else None
    except (ValueError, TypeError):
        year_founded = None

    jobs = dom.get("jobs")
    if jobs in (None, ""):
        try:
            jobs = int(dom.get("number_of_jobs") or 0)
        except (ValueError, TypeError):
            jobs = 0

    exit_type, status = _derive_exit(entry, dom)
    overview = entry.get("overview") or ""
    website_description = dom.get("website_description") or ""
    one_liner = _first_nonempty(
        website_description,
        overview.split(". ")[0] + "." if overview else None,
        (entry.get("announcement") or {}).get("excerpt"),
    )

    return {
        "id": A16Z_ID_OFFSET + int(native_id) if str(native_id).isdigit() else slug,
        "source": SOURCE,
        "source_id": native_id,
        "name": name,
        "slug": slug,
        "website": _first_nonempty(entry.get("web"), dom.get("external_url"),
                                   dom.get("company_url"), dom.get("url")),
        "one_liner": one_liner,
        "long_description": _first_nonempty(overview, website_description),
        "stage": ", ".join(entry.get("stages") or []) or None,
        "industry": industry,
        "founders": _first_nonempty(entry.get("founders"), dom.get("founders_list")),
        "year_founded": year_founded,
        "funded_date": _first_nonempty(dom.get("initial_a16z_date_funded"),
                                       entry.get("invest_date"), dom.get("investment_date")),
        "ticker_symbol": entry.get("ticker_symbol") or None,
        "acquirer": entry.get("acquirer") or None,
        "exit_type": exit_type,
        "status": status,
        "source_url": permalink,
        "is_hiring": bool(jobs and int(jobs) > 0),
        "batch": None, "team_size": None, "all_locations": None,
        "top_company": False, "nonprofit": False, "subindustry": None,
    }


def map_all(entries: list[dict], limit: Optional[int] = None) -> list[dict]:
    seen_slugs: set = set()
    mapped = []
    for e in entries:
        if e.get("id") is None:
            continue
        mapped.append(_map_entry(e, seen_slugs))
        if limit and len(mapped) >= limit:
            break
    return mapped


def seed(db_path: str, limit: Optional[int] = None):
    html_text = fetch_html()
    entries = parse_entries(html_text)
    mapped = map_all(entries, limit=limit)
    conn = get_conn(db_path)
    for c in mapped:
        upsert(conn, c)
    conn.commit()
    conn.close()
    return len(mapped)
