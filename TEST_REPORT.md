# startup-find — Test Report (2026-07-08)

Built from ExploreYC (KonstantinMB/exploreyc), ergonomics modeled on jackwener/opencli.
Local source: /Users/princepal/dev/startup-find  (pip -e installed into .venv)
Launcher: /Users/princepal/bin/startup-find -> .venv/bin/startup-find
GitHub: https://github.com/princepal9120/startup-find

## RESULTS: PASS (after 2 fixes)

### Bugs found + fixed
1. STALE DB: a leftover ~/.startup-find/yc.db from an earlier build had an
   old schema (no source_id column). `CREATE TABLE IF NOT EXISTS` won't migrate.
   Symptom: "table companies has no column named source_id".
   Fix: rm the stale DB so the current schema applies. CLI code was correct.
   LESSON: if schema changes, the on-disk DB must be dropped. Consider a
   schema_version check + auto-migrate/drop in a future version.
2. BATCHES CRASH: `batches` returns a list of strings, but _emit's table branch
   assumed dicts -> 'str' object has no attribute 'get'.
   Fix: _emit now handles plain-string lists. Committed + pushed (00cda0a).

### Commands tested (all PASS)
- seed --max-pages 1  -> 1000 YC companies from public Algolia, no key. OK
- seed-a16z --limit 5 -> 5 a16z companies. OK (coexists with YC, total 1005)
- stats               -> total/hiring/by_source/by_batch/by_industry. OK
- batches             -> now lists batches (was crashing). OK
- companies --is-hiring --industry Fintech --limit 5 -> real rows. OK
- search "ai agent"   -> full-text match. OK
- company --slug stripe -> Stripe record with full fields. OK
- digest --limit 3    -> JSON digest. OK
- --format json/yaml/csv -> all emit correctly (yaml needs pyyaml). OK
- --agent (compact json) -> OK for agent tool use
- serve --port 8731   -> /health /stats /companies /search /company all 200. OK

### Data sanity
- 1005 companies total (1000 YC + 5 a16z test)
- 279 hiring
- Latest batch Winter 2027 present
- Real companies verifiable (Stripe, Abridge, 11x, etc.)

## HOW TO USE (for Prince)
  startup-find seed            # one-time, ~1k YC companies
  startup-find seed-a16z       # a16z portfolio
  startup-find companies --is-hiring true --industry Fintech --limit 20
  startup-find search "ai agent"
  startup-find serve --port 8731   # HTTP API for non-Python agents

## NOTES / FUTURE
- Full seed (all batches) = 9 pages of 1000. Could take a few minutes. Tested 1 page.
- No schema migration on DB change; dropping ~/.startup-find/yc.db is the reset path.
- pip install on PyPI not done (only -e from source). Could publish for "anyone".
