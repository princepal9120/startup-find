"""Fit-profile scoring, founder email lookup, and outreach drafting.

Implements the Nikhil Sheoran "relevant fit" model:
  - Score startups by relevance to YOUR specific experience axes
  - Find founder emails for direct outreach (bypass job portals)
  - Generate short founder emails using his proven formula

Stdlib only. No external deps.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.request

# ---------------------------------------------------------------------------
# Fit-profile scoring
# ---------------------------------------------------------------------------

# Default fit axes for Prince's profile (AI Platform Engineer)
DEFAULT_FIT_AXES = [
    "ai agent", "agentic", "langchain", "langgraph", "llm",
    "browser automation", "computer use", "playwright", "puppeteer",
    "cloudflare", "workers", "edge computing",
    "ecommerce", "marketing automation", "retention",
    "python", "typescript", "fastapi", "backend",
    "mcp", "model context protocol", "rag", "embeddings",
    "observability", "eval", "infra", "platform",
]

# Weight multipliers: title/one_liner matches count more than long_desc
WEIGHT_ONE_LINER = 3
WEIGHT_NAME = 4
WEIGHT_DESC = 1
WEIGHT_INDUSTRY = 2


def score_fit(row: dict, axes: list[str]) -> dict:
    """Score a company row against fit axes. Returns {score, matches[]}."""
    name = (row.get("name") or "").lower()
    one_liner = (row.get("one_liner") or "").lower()
    long_desc = (row.get("long_description") or "").lower()
    industry = (row.get("industry") or "").lower()
    subindustry = (row.get("subindustry") or "").lower()

    score = 0
    matches = []
    for axis in axes:
        axis_lower = axis.lower().strip()
        if not axis_lower:
            continue
        hit = False
        if axis_lower in name:
            score += WEIGHT_NAME
            hit = True
        if axis_lower in one_liner:
            score += WEIGHT_ONE_LINER
            hit = True
        if axis_lower in industry or axis_lower in subindustry:
            score += WEIGHT_INDUSTRY
            hit = True
        if axis_lower in long_desc:
            score += WEIGHT_DESC
            hit = True
        if hit:
            matches.append(axis)

    return {"score": score, "matches": matches}


def rank_by_fit(rows: list[dict], axes: list[str]) -> list[dict]:
    """Attach fit_score + fit_matches to each row, sorted desc."""
    scored = []
    for row in rows:
        result = score_fit(row, axes)
        row["fit_score"] = result["score"]
        row["fit_matches"] = result["matches"]
        scored.append(row)
    scored.sort(key=lambda r: (-r["fit_score"], r.get("name") or ""))
    return scored


# ---------------------------------------------------------------------------
# Founder email lookup (agent-reach web pattern)
# ---------------------------------------------------------------------------

def _jina_fetch(url: str, timeout: int = 15) -> str:
    """Fetch a page via Jina reader (agent-reach web.md pattern)."""
    try:
        req = urllib.request.Request(
            f"https://r.jina.ai/{url}",
            headers={"User-Agent": "startup-find/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_emails(text: str) -> list[str]:
    """Extract unique emails from text."""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    seen = set()
    emails = []
    for m in re.findall(pattern, text):
        m = m.lower().strip()
        if m not in seen and not m.endswith((".png", ".jpg", ".svg")):
            seen.add(m)
            emails.append(m)
    return emails


def find_founder_email(row: dict) -> dict:
    """Look up founder/team emails for a company.

    Strategy:
    1. Fetch company website /about, /team, /contact pages
    2. Extract emails via regex
    3. Return {emails: [...], source_url: ...}
    """
    website = row.get("website") or ""
    slug = row.get("slug") or ""
    if not website:
        return {"emails": [], "source_url": "", "note": "no website in DB"}

    # Ensure protocol
    if not website.startswith("http"):
        website = f"https://{website}"

    emails = []
    source_url = ""

    # Try common team/about pages
    for path in ["", "/about", "/team", "/contact", "/about-us", "/careers"]:
        url = f"{website}{path}"
        text = _jina_fetch(url)
        if text:
            found = _extract_emails(text)
            if found:
                emails.extend(found)
                source_url = url
                break

    # Also try the homepage if nothing found
    if not emails:
        text = _jina_fetch(website)
        if text:
            emails = _extract_emails(text)
            source_url = website

    # Fallback: Exa search for founder email
    if not emails:
        try:
            company_name = row.get("name") or ""
            query = ("exa.web_search_exa(query: "
                     f"\"founder email {company_name} {slug}\", numResults: 3)")
            result = subprocess.run(
                ["mcporter", "call", query],
                capture_output=True, text=True, timeout=20,
            )
            if result.returncode == 0:
                # Extract emails from search results
                emails = _extract_emails(result.stdout)
                source_url = "exa search"
        except Exception:
            pass

    # Filter out obvious non-founder emails
    ignore_patterns = [
        "noreply@", "no-reply@", "support@", "help@", "info@",
        "hello@", "contact@", "sales@", "press@", "media@",
        "security@", "abuse@", "postmaster@", "webmaster@",
        "example.com", "sentry.io", "github.com", "wix.com",
        "squarespace.com", "wordpress.com", "webflow.io",
    ]
    filtered = [
        e for e in emails
        if not any(p in e for p in ignore_patterns)
    ]

    return {
        "emails": filtered[:10],
        "source_url": source_url,
        "note": "verify before sending" if filtered else "no emails found on public pages",
    }


# ---------------------------------------------------------------------------
# Outreach draft generator
# ---------------------------------------------------------------------------

RESUME_FACTS_DEFAULT = """
- Senior SWE with 3+ years in AI/ML product development
- Built AI agents with LangGraph, FastAPI, TypeScript/Python/Go
- Deployed on Cloudflare Workers, edge computing
- Experience: ecommerce AI (BIK.ai), marketing agent platform (AICMOHQ)
- Built browser automation and computer-use agent integrations
- Strong eval, observability, and reliability engineering background
- Open source contributor, MIT/Apache licensing
""".strip()


def draft_outreach(row: dict, resume_facts: str | None = None) -> str:
    """Generate a short founder outreach email using Nikhil's formula.

    Formula: what you built -> why this company -> 15-min chat ask.
    """
    name = row.get("name") or "your company"
    one_liner = row.get("one_liner") or ""
    website = row.get("website") or ""
    fit_matches = row.get("fit_matches") or []

    facts = resume_facts or RESUME_FACTS_DEFAULT

    # Build relevance sentence from fit matches
    if fit_matches:
        relevance = f"My experience directly overlaps with what {name} is building: {', '.join(fit_matches[:3])}."
    else:
        relevance = f"I've been following {name} and the work in {one_liner[:80] if one_liner else 'this space'}."

    draft = f"""Subject: Quick question about {name}

Hi [Founder Name],

I came across {name}{f' ({website})' if website else ''} and was immediately interested.

{relevance}

A bit about me:
{facts}

Would you be open to a 15-minute chat about how I could contribute to the team?

Thanks,
[Your Name]
[Your Email]
[Your Phone]
[LinkedIn] | [GitHub]
"""
    return draft.strip()


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def cmd_fit_score(args, q_companies_func, ensure_seeded_func, coerce_func):
    """Rank companies by fit-profile relevance."""
    ensure_seeded_func(args.db)
    axes = []
    if args.profile:
        axes = [a.strip() for a in args.profile.split(",") if a.strip()]
    if not axes:
        axes = DEFAULT_FIT_AXES

    # Fetch a wide pool, rank, then truncate (ranking must see all candidates)
    pool = q_companies_func(
        args.db, max(args.limit * 20, 500), 0, args.batch, args.industry,
        args.country, args.is_hiring, None, args.search, args.source,
    )
    if not pool:
        return None

    ranked = rank_by_fit(pool, axes)  # q_companies already returns coerced dicts
    return ranked[: args.limit]


def cmd_signals(args, q_companies_func, ensure_seeded_func, coerce_func):
    """Filter companies by hiring signals (funded, recent batch, etc.)."""
    ensure_seeded_func(args.db)

    rows = q_companies_func(
        args.db, args.limit, 0, args.batch, args.industry,
        args.country, True, None, args.search, args.source,
    )
    if not rows:
        return None

    results = []
    for row in rows:  # q_companies already returns coerced dicts
        signals = []
        if row.get("funding_total_usd"):
            signals.append(f"funded: ${row['funding_total_usd']:,.0f}")
        if row.get("funded_date"):
            signals.append(f"funded: {row['funded_date']}")
        if args.recent_batch and row.get("batch") == args.recent_batch:
            signals.append(f"recent batch: {row['batch']}")
        if row.get("top_company"):
            signals.append("YC top company")
        if row.get("team_size") and isinstance(row["team_size"], int):
            if row["team_size"] <= 20:
                signals.append(f"early stage: {row['team_size']} people")
            elif row["team_size"] <= 100:
                signals.append(f"growing: {row['team_size']} people")
        if row.get("is_hiring"):
            signals.append("actively hiring")
        row["signals"] = signals
        results.append(row)

    return results


def cmd_founder_email(args, q_company_func, ensure_seeded_func, coerce_func):
    """Look up founder email for a company."""
    ensure_seeded_func(args.db)
    row = q_company_func(args.db, None, args.slug)
    if not row:
        return None
    axes = [a.strip() for a in (args.profile or "").split(",") if a.strip()] or DEFAULT_FIT_AXES
    fit_result = score_fit(row, axes)
    row["fit_matches"] = fit_result["matches"]
    result = find_founder_email(row)  # q_company already returns coerced dict
    return {"company": row.get("name"), "slug": row.get("slug"), **result}


def cmd_outreach_draft(args, q_company_func, ensure_seeded_func, coerce_func):
    """Generate a short founder outreach email."""
    ensure_seeded_func(args.db)
    row = q_company_func(args.db, None, args.slug)
    if not row:
        return None
    resume_facts = None
    if args.resume_file:
        try:
            with open(args.resume_file) as f:
                resume_facts = f.read().strip()
        except OSError:
            pass

    axes = [a.strip() for a in (args.profile or "").split(",") if a.strip()] or DEFAULT_FIT_AXES
    fit_result = score_fit(row, axes)
    row["fit_matches"] = fit_result["matches"]
    draft = draft_outreach(row, resume_facts)
    return {
        "company": row.get("name"),
        "slug": row.get("slug"),
        "fit_matches": row["fit_matches"],
        "draft": draft,
    }
