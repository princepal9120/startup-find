# startup-find

Local, agent-friendly CLI for **Y Combinator + a16z** startup data.

Seeds public datasets into a local **SQLite** database (no API key, no rate
limit) and serves fast offline queries that an AI coding agent (Claude Code,
Codex, Hermes, or any shell) can call.

Converted from the ExploreYC project
([github.com/KonstantinMB/exploreyc](https://github.com/KonstantinMB/exploreyc))
into a self-contained CLI. Ergonomics modeled on
[jackwener/opencli](https://github.com/jackwener/opencli).

## Why local-first?

Everything stays on **your** machine. `startup-find` never phones home, never
needs an account, and never sends your queries anywhere. The first time you run
a query on an empty database, it reminds you to seed:

```
Your local database is empty. Seed it first (data stays on YOUR machine):
  startup-find seed           # Y Combinator (public Algolia, no key)
  startup-find seed-a16z      # a16z portfolio
All data is stored locally in SQLite — nothing leaves your computer.
```

Seed once, then query forever offline. Perfect for personal research, building
your own tools on top of YC/a16z data, or letting an AI coding agent pull
startup facts without burning an API quota.

## Install

```bash
pip install startup-find
# or, editable from source:
git clone https://github.com/princepal9120/startup-find && cd startup-find
pip install -e .
```

Requires Python 3.9+. Zero runtime dependencies (stdlib only). `pyyaml` is
optional for `--format yaml`.

## Seed (one-time)

```bash
startup-find seed                 # all YC batches from public Algolia
startup-find seed --batch "Summer 2025" --hits 1000 --max-pages 10
startup-find seed-a16z            # a16z portfolio (inline JSON on a16z.com)
```

Data lands in `~/.startup-find/yc.db` by default (override with `--db`).

## Query (offline, unlimited)

```bash
startup-find stats
startup-find batches
startup-find companies --is-hiring true --batch "Summer 2025" --industry Fintech --limit 20
startup-find search "ai agent" --limit 10
startup-find company --slug stripe
startup-find digest
```

### Agent mode

```bash
startup-find companies --limit 5 --format json --agent
# --format: table | json | yaml | csv
# --agent : compact JSON on stdout for LLM tool use
# --db    : custom SQLite path
```

## HTTP API (for non-Python agents)

```bash
startup-find serve --port 8731
curl "http://127.0.0.1:8731/stats"
curl "http://127.0.0.1:8731/companies?is_hiring=true&batch=Summer%202025&limit=10"
curl "http://127.0.0.1:8731/search?q=ai%20agent"
curl "http://127.0.0.1:8731/company?slug=stripe"
```

Routes: `/health`, `/stats`, `/batches`, `/companies`, `/search`, `/company`.

## Daily use

Keyless and local, so it is safe for a daily cron/digest job:

```bash
startup-find digest --format json
```

## Exit codes

`0` success · `1` error · `66` empty result.

## License

MIT
