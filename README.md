# 🚀 startup-find

> **Local-first, agent-friendly CLI for YC + a16z startup data.**
> No API key. No rate limits. No data leaves your machine.

[![PyPI version](https://img.shields.io/pypi/v/startup-find?color=brightgreen&label=pip)](https://pypi.org/project/startup-find/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-success)](pyproject.toml)
[![Website](https://img.shields.io/badge/website-live-orange)](https://princepal9120.github.io/startup-find/)

---

## What is it?

`startup-find` seeds public **Y Combinator** and **a16z** startup datasets into a local **SQLite** database, then lets you query them instantly — offline, forever, from your terminal or any AI coding agent.

Think of it as a `grep`-able, JSON-ready, LLM-tool-friendly window into thousands of startups: names, batches, industries, hiring status, descriptions, and more.

```
$ startup-find search "ai agent" --limit 5 --format json
```

```json
[
  { "name": "AutoDev", "batch": "Summer 2024", "industry": "AI", "is_hiring": true },
  ...
]
```

---

## ✨ Features

- 🏠 **Local-first** — all data lives in `~/.startup-find/yc.db` (SQLite), nothing phones home
- ⚡ **Offline queries** — seed once, query forever with no internet needed
- 🤖 **Agent-ready** — `--format json` + `--agent` flag for clean LLM tool use
- 🌐 **HTTP server** — `startup-find serve` exposes a REST API for non-Python agents
- 🔍 **Full-text search** — fast FTS5-powered search across company names and descriptions
- 📊 **Rich filters** — batch, industry, hiring status, location, and more
- 🔄 **Daily digest** — safe for cron jobs; exit code `66` = empty (scriptable)
- 📦 **Zero runtime deps** — pure stdlib; `pyyaml` optional for YAML output

---

## 📦 Install

```bash
pip install startup-find
```

Or install from source (editable):

```bash
git clone https://github.com/princepal9120/startup-find && cd startup-find
pip install -e .
```

**Requirements:** Python 3.9+ · Zero runtime dependencies · Optional: `pip install startup-find[yaml]` for YAML output

---

## 🌱 Seed (one-time setup)

Pull data from public sources into your local SQLite database:

```bash
startup-find seed                              # All YC batches (public Algolia, no key needed)
startup-find seed --batch "Summer 2025"       # Specific batch only
startup-find seed --hits 1000 --max-pages 10  # Tune crawl size
startup-find seed-a16z                        # a16z portfolio
```

Data lands in `~/.startup-find/yc.db`. Override with `--db /path/to/custom.db`.

> **First-run reminder:** If you query on an empty database, you'll see:
> ```
> Your local database is empty. Seed it first (data stays on YOUR machine):
>   startup-find seed        # Y Combinator (public Algolia, no key)
>   startup-find seed-a16z   # a16z portfolio
> ```

---

## 🔍 Query (offline, unlimited)

### Stats & discovery

```bash
startup-find stats                # Row counts, last-seeded timestamps
startup-find batches              # List all YC batches in the DB
startup-find digest               # Today's snapshot digest
```

### Filter companies

```bash
startup-find companies \
  --is-hiring true \
  --batch "Summer 2025" \
  --industry Fintech \
  --limit 20
```

### Full-text search

```bash
startup-find search "ai agent" --limit 10
startup-find search "climate energy" --format csv
```

### Single company lookup

```bash
startup-find company --slug stripe
```

---

## 🤖 Agent / LLM Tool Use

Designed to be called by AI coding agents (Claude Code, Codex, GPT-4, shell scripts, etc.):

```bash
# Compact JSON on stdout — perfect for LLM tool calls
startup-find companies --limit 5 --format json --agent

# All output formats
# --format: table | json | yaml | csv
# --agent : strips ANSI, adds envelope metadata
# --db    : custom SQLite path
```

**Example agent system prompt snippet:**

```
Tool: startup-find
Usage: startup-find search "<query>" --format json --agent
       startup-find companies --industry AI --is-hiring true --format json --agent
Returns: JSON array of company objects with name, batch, industry, url, description, is_hiring.
```

---

## 🌐 HTTP API (for non-Python agents)

Spin up a lightweight local REST server for any language or tool:

```bash
startup-find serve --port 8731
```

| Endpoint | Description |
|---|---|
| `GET /health` | Health check |
| `GET /stats` | DB row counts & timestamps |
| `GET /batches` | All seeded batches |
| `GET /companies` | Filter: `batch`, `industry`, `is_hiring`, `limit` |
| `GET /search?q=<query>` | Full-text search |
| `GET /company?slug=<slug>` | Single company by slug |

```bash
curl "http://127.0.0.1:8731/companies?is_hiring=true&batch=Summer%202025&limit=10"
curl "http://127.0.0.1:8731/search?q=ai+agent"
curl "http://127.0.0.1:8731/company?slug=stripe"
```

---

## ⏰ Daily Cron / Digest

Safe for scheduled jobs — `startup-find` is keyless, rateless, and local:

```bash
# crontab example: run every morning at 8am
0 8 * * * startup-find digest --format json >> ~/startup-digest.json
```

---

## 🚦 Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error |
| `66` | Empty result (scriptable — treat as "no data") |

---

## 🗂️ Project Structure

```
startup-find/
├── startup_find/
│   ├── cli.py        # Entry point & argument parsing
│   ├── db.py         # SQLite schema, seeding, FTS5 queries
│   ├── yc.py         # YC Algolia scraper
│   ├── a16z.py       # a16z portfolio scraper
│   └── serve.py      # Lightweight HTTP server (stdlib only)
├── pyproject.toml
└── README.md
```

---

## 🤝 Contributing

Contributions welcome! This project is intentionally **dependency-free** — please keep it that way.

```bash
git clone https://github.com/princepal9120/startup-find
cd startup-find
pip install -e .
startup-find seed && startup-find stats
```

Open an issue or PR for:
- New data sources (other VC portfolios, accelerators)
- New filter flags or output formats
- Bug fixes or performance improvements

---

## 📜 Credits

- Data sourced from the public [YC Algolia API](https://www.ycombinator.com/) and [a16z.com](https://a16z.com/portfolio/)
- Converted from the [ExploreYC](https://github.com/KonstantinMB/exploreyc) project
- CLI ergonomics inspired by [jackwener/opencli](https://github.com/jackwener/opencli)

---

## 📄 License

[MIT](LICENSE) © [Prince Pal](https://github.com/princepal9120)
