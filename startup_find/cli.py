"""startup-find CLI — local, agent-friendly YC + a16z startup data.

Converts the ExploreYC project (github.com/KonstantinMB/exploreyc) into a
self-contained CLI. Seeds Y Combinator's public Algolia dataset and the a16z
portfolio into a local SQLite DB (no API key, no rate limit) and serves fast
offline queries an AI coding agent can call.

Ergonomics modeled on jackwener/opencli: subcommands, --format
json|yaml|table|csv, --agent compact JSON, clean exit codes.

Exit codes: 0 success, 1 error, 66 empty result.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from .__version__ import __version__
from .db import (DEFAULT_DB, q_companies, q_stats, q_batches, q_company, coerce,
               ensure_seeded)
from . import yc, a16z, serve


def _emit(data, args):
    if args.format == "json" or args.agent:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif args.format == "csv":
        if isinstance(data, list) and data:
            cols = list(data[0].keys())
            print(",".join(cols))
            for r in data:
                print(",".join(str(r.get(c, "")) for c in cols))
        else:
            print(json.dumps(data, ensure_ascii=False))
    elif args.format == "yaml":
        try:
            import yaml
            print(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
        except ImportError:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:  # table
        if isinstance(data, list):
            for c in data:
                loc = c.get("all_locations") or c.get("country") or ""
                line = f"  - {c.get('name')} [{c.get('batch') or c.get('source')}] ({c.get('industry')})"
                if loc:
                    line += f" · {loc}"
                if c.get("is_hiring"):
                    line += " · hiring"
                print(line)
                if c.get("one_liner"):
                    print(f"      {c.get('one_liner')}")
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))


def _empty_exit():
    sys.stderr.write("no results\n")
    raise SystemExit(66)


def _common_args():
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--db", default=DEFAULT_DB, help=f"SQLite path (default {DEFAULT_DB})")
    parent.add_argument("--format", default="table", choices=["table", "json", "yaml", "csv"])
    parent.add_argument("--agent", action="store_true", help="compact JSON for AI agent tool use")
    return parent


# ---- commands ----

def cmd_seed(args):
    print(f"Seeding YC from public Algolia into {args.db} ...", file=sys.stderr)
    total = 0
    for done, page in yc.seed(args.db,
                              args.batch.split(",") if args.batch else None,
                              args.hits, args.max_pages):
        total = done
        print(f"  seeded {done} companies (page {page})", file=sys.stderr)
    print(f"DONE: {total} YC companies stored in {args.db}")


def cmd_seed_a16z(args):
    print(f"Seeding a16z portfolio into {args.db} ...", file=sys.stderr)
    n = a16z.seed(args.db, limit=args.limit)
    print(f"DONE: {n} a16z companies stored in {args.db}")


def cmd_companies(args):
    ensure_seeded(args.db)
    rows = q_companies(args.db, args.limit, args.offset, args.batch, args.industry,
                       args.country, args.is_hiring, args.top_company, args.search, args.source)
    if not rows:
        _empty_exit()
    _emit([coerce(r) for r in rows], args)


def cmd_search(args):
    ensure_seeded(args.db)
    rows = q_companies(args.db, args.limit, 0, None, None, None, None, None, args.q, args.source)
    if not rows:
        _empty_exit()
    _emit([coerce(r) for r in rows], args)


def cmd_stats(args):
    ensure_seeded(args.db)
    _emit(q_stats(args.db), args)


def cmd_batches(args):
    ensure_seeded(args.db)
    _emit(q_batches(args.db), args)


def cmd_company(args):
    ensure_seeded(args.db)
    row = q_company(args.db, args.id, args.slug)
    if not row:
        _empty_exit()
    _emit(coerce(row), args)


def cmd_digest(args):
    ensure_seeded(args.db)
    stats = q_stats(args.db)
    batches = q_batches(args.db)
    newest = batches[0] if batches else None
    hiring = (q_companies(args.db, args.limit, 0, newest, None, None, True, None, None, None)
              if newest else [])
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_companies": stats["total"],
        "hiring_now": stats["hiring"],
        "latest_batch": newest,
        "hiring_in_latest_batch": [coerce(c) for c in hiring],
    }
    _emit(out, args)


def cmd_serve(args):
    serve.serve(args.host, args.port)


def cmd_skill(args):
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SKILL.md"),
        os.path.expanduser("~/.hermes/skills/startup-find/SKILL.md"),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p) as f:
                sys.stdout.write(f.read())
            return
    sys.stderr.write("SKILL.md not found\n")
    raise SystemExit(1)


def build_parser():
    parent = _common_args()
    p = argparse.ArgumentParser(prog="startup-find", parents=[parent],
                                description="Local CLI for YC + a16z startup data (agent-friendly).")
    p.add_argument("--version", action="version", version=f"startup-find {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("seed", help="Pull YC companies into local SQLite", parents=[parent])
    s.add_argument("--batch", help="comma-separated batches e.g. 'Summer 2025,Winter 2025'")
    s.add_argument("--hits", type=int, default=1000)
    s.add_argument("--max-pages", type=int, default=10)
    s.set_defaults(func=cmd_seed)

    s = sub.add_parser("seed-a16z", help="Pull a16z portfolio into local SQLite", parents=[parent])
    s.add_argument("--limit", type=int, default=None, help="only first N (smoke test)")
    s.set_defaults(func=cmd_seed_a16z)

    s = sub.add_parser("companies", help="List/filter companies", parents=[parent])
    s.add_argument("--limit", type=int, default=50)
    s.add_argument("--offset", type=int, default=0)
    s.add_argument("--source", default=None, help="yc | a16z | (omit = all)")
    s.add_argument("--batch")
    s.add_argument("--industry")
    s.add_argument("--country")
    s.add_argument("--is-hiring", dest="is_hiring", type=lambda x: x.lower() == "true", default=None)
    s.add_argument("--top-company", dest="top_company", type=lambda x: x.lower() == "true", default=None)
    s.add_argument("--search")
    s.set_defaults(func=cmd_companies)

    s = sub.add_parser("search", help="Full-text search", parents=[parent])
    s.add_argument("q")
    s.add_argument("--limit", type=int, default=50)
    s.add_argument("--source", default=None)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("stats", help="Portfolio stats", parents=[parent])
    s.set_defaults(func=cmd_stats)

    s = sub.add_parser("batches", help="Distinct batches", parents=[parent])
    s.set_defaults(func=cmd_batches)

    s = sub.add_parser("company", help="One company by id or slug", parents=[parent])
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--id", type=int)
    g.add_argument("--slug")
    s.set_defaults(func=cmd_company)

    s = sub.add_parser("digest", help="Daily agent digest (offline)", parents=[parent])
    s.add_argument("--limit", type=int, default=15)
    s.set_defaults(func=cmd_digest)

    s = sub.add_parser("serve", help="Local HTTP API for non-Python agents", parents=[parent])
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8731)
    s.set_defaults(func=cmd_serve)

    s = sub.add_parser("skill", help="Print SKILL.md for AI agent discovery", parents=[parent])
    s.set_defaults(func=cmd_skill)

    return p


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"ERROR: {e}\n")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
