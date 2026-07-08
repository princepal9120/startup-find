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

## Daily use
Keyless + local, safe for a daily cron/digest job: `startup-find digest --format json`.
