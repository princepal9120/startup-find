# Plan: Fix global `--db` flag parsing

## Problem

`startup-find --db /tmp/x.db stats` ignores the custom path and uses `~/.startup-find/yc.db`.
Root cause: argparse `parents=[parent]` on both root and subparsers — subparser defaults overwrite root-parsed values.

## Scope

- Fix `--db`, `--format`, `--agent` for global-before-subcommand and subcommand-after forms
- Add pytest coverage for argparse resolution
- Add GitHub Actions CI (install + pytest)
- Wire `serve` to respect `--db` CLI flag

Out of scope: PyPI publish, schema migration, `--agent` compact JSON.

## Approach

Use `argparse.SUPPRESS` defaults on subparser parent args so subparsers only override when explicitly passed after the subcommand. Root parser keeps normal defaults.

## Files

| File | Change |
|------|--------|
| `startup_find/cli.py` | `_common_args(suppress_defaults=...)`, subparsers use suppress parent |
| `startup_find/serve.py` | Accept `db` param; `cmd_serve` passes `args.db` |
| `tests/test_cli.py` | Argparse position tests |
| `.github/workflows/ci.yml` | pytest on push/PR |
| `pyproject.toml` | `[project.optional-dependencies] dev = ["pytest"]` |

## Test scenarios

1. `--db /tmp/a.db stats` → `args.db == /tmp/a.db`
2. `stats --db /tmp/a.db` → `args.db == /tmp/a.db`
3. `stats` (no flag) → `args.db == DEFAULT_DB`
4. Same for `--format json` before/after subcommand
5. `serve --db /tmp/a.db` passes db to server (smoke via parse only)

## Verification

```bash
pytest tests/ -q
startup-find --db /tmp/test.db stats --format json  # total 0 on fresh db
```