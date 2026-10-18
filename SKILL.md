---
name: startup-find
description: >
  MUST USE when the user (or an AI coding agent) wants Y Combinator / a16z
  startup data locally — company search, hiring boards, batch/industry/country
  filters, or a daily digest — without an API key or rate limit.
  startup-find seeds YC's public dataset and the a16z portfolio into local
  SQLite and serves fast offline queries. Use it for "find YC companies",
  "who's hiring in batch X", "YC startups in <industry>", or agent-driven
  daily digests.

  Also use when the user mentions "startup-find", "ExploreYC CLI", or wants a
  local-first startup database their coding agent can query.
metadata:
  openclaw:
    homepage: https://github.com/princepal9120/startup-find
---

# startup-find — local, agent-friendly YC/a16z data CLI

Converts the ExploreYC project into a self-contained CLI. Seeds Y Combinator's
public Algolia dataset and the a16z portfolio into a local SQLite DB (no API
key, no rate limit) and serves offline queries an AI coding agent can call.

Install: `pip install startup-find` (or `pip install -e .` from source).
Binary: `startup-find`. Requires Python 3.9+, zero deps (stdlib only).

## Setup (one-time)
```bash
startup-find seed            # pulls YC companies into ~/.startup-find/yc.db
startup-find seed-a16z       # pulls a16z portfolio
# or a slice:
startup-find seed --batch "Summer 2025" --hits 1000 --max-pages 10
```

## Query (offline, unlimited)
```bash
startup-find stats
startup-find batches
startup-find companies --is-hiring true --batch "Summer 2025" --industry Fintech --limit 20
startup-find search "ai agent" --limit 10
startup-find company --slug stripe
startup-find digest
```

## Agent mode (Claude Code / Codex)
```bash
startup-find companies --limit 5 --format json --agent
# --format: table | json | yaml | csv
# --agent:  compact JSON on stdout for tool use
# --db:     custom SQLite path (default ~/.startup-find/yc.db)
# --source: yc | a16z   (omit = all sources)
```

## HTTP API (non-Python agents)
```bash
startup-find serve --port 8731
# GET /stats /batches /companies?is_hiring=true&batch=... /search?q=... /company?slug=...
```

## Exit codes
0 success, 1 error, 66 empty result.

## Agent-reach integration (live web + social)

startup-find is the LOCAL discovery layer. Pair it with agent-reach for live
verification, founder emails, and social research. agent-reach router docs:
`~/.hermes/skills/agent-reach/SKILL.md` (references/ has per-platform commands).

```bash
# Live web page read (founder-email uses this internally via r.jina.ai)
curl -s "https://r.jina.ai/https://<company-website>/about"

# Exa web search (fit-score / founder-email fallback)
mcporter call 'exa.web_search_exa(query: "founder email <company>", numResults: 5)'

# Twitter/X research: find founder tweets, hiring posts, launch announcements
rtk twitter search "<company> hiring" -n 10
rtk twitter user <founder-handle>            # recent posts

# Reddit research: team sentiment, hiring, product discussion
rtk opencli reddit search "<company>" -f yaml
# or: rtk rdt search "<company>" --limit 10

# Verify a shortlist end-to-end (Nikhil Sheoran playbook):
startup-find fit-score --is-hiring true --limit 20 --format json --agent   # rank by YOUR fit
startup-find signals --recent-batch "Summer 2026" --format json --agent     # hiring signals
startup-find founder-email --slug <slug> --format json                     # direct founder email
startup-find outreach-draft --slug <slug> --format json                    # 3-line founder email
rtk twitter search "<company> founder" -n 5                                # cross-check founder
```

## Fit-profile commands (Nikhil Sheoran "relevant fit" model)

```bash
# Rank startups by relevance to your experience axes (not just keywords)
startup-find fit-score --is-hiring true --limit 20
startup-find fit-score --profile "ai agent, langgraph, cloudflare, ecommerce" --is-hiring true

# Hiring signals: funded, recent batch, team size, top company
startup-find signals --recent-batch "Summer 2026" --limit 30

# Founder email lookup: Jina reader on /about /team /contact + Exa search fallback
startup-find founder-email --slug manufact

# Short founder email (his formula: what you built -> why THIS company -> 15-min chat)
startup-find outreach-draft --slug manufact --resume-file ~/resume-facts.txt

# Daily digest, fit-ranked (safe for cron)
startup-find digest --profile "ai agent, mcp, platform" --format json
```

## Daily use
Keyless + local, safe for a daily cron/digest job: `startup-find digest --format json`.
