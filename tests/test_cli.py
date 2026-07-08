"""CLI argparse tests — global flags before/after subcommands."""
from __future__ import annotations

import pytest

from startup_find.cli import build_parser
from startup_find.db import DEFAULT_DB


@pytest.fixture
def parser():
    return build_parser()


@pytest.mark.parametrize(
    "argv,expected_db",
    [
        (["--db", "/tmp/custom.db", "stats"], "/tmp/custom.db"),
        (["stats", "--db", "/tmp/custom.db"], "/tmp/custom.db"),
        (["stats"], DEFAULT_DB),
        (["--db", "/tmp/seed.db", "seed", "--max-pages", "1"], "/tmp/seed.db"),
        (["seed", "--db", "/tmp/seed.db"], "/tmp/seed.db"),
    ],
)
def test_db_flag_positions(parser, argv, expected_db):
    args = parser.parse_args(argv)
    assert args.db == expected_db


@pytest.mark.parametrize(
    "argv,expected_format",
    [
        (["--format", "json", "stats"], "json"),
        (["stats", "--format", "json"], "json"),
        (["stats"], "table"),
    ],
)
def test_format_flag_positions(parser, argv, expected_format):
    args = parser.parse_args(argv)
    assert args.format == expected_format


def test_agent_flag_before_subcommand(parser):
    args = parser.parse_args(["--agent", "stats", "--format", "json"])
    assert args.agent is True
    assert args.format == "json"


def test_serve_receives_db(parser):
    args = parser.parse_args(["--db", "/tmp/api.db", "serve", "--port", "9999"])
    assert args.db == "/tmp/api.db"
    assert args.port == 9999