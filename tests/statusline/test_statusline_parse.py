#!/usr/bin/env python3
"""Tests for core/statusline/statusline_parse.py (the stdin-native statusline parser).

Runs the parser as a subprocess (most faithful to how Claude Code invokes it)
with HOME pointed at a tmp dir so the mid-stream state file never touches the
real ~/.claude. Pure helpers are imported directly.
"""

import ast
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PARSER = REPO / "core" / "statusline" / "statusline_parse.py"
RENDERER = REPO / "core" / "statusline" / "statusline.sh"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Import the module for pure-helper unit tests.
_spec = importlib.util.spec_from_file_location("statusline_parse", PARSER)
slp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(slp)


def run(fixture_name: str, tmp_home: Path) -> list[str]:
    """Pipe a fixture through the parser; return the 9 output fields."""
    payload = (FIXTURES / fixture_name).read_text()
    proc = subprocess.run(
        [sys.executable, str(PARSER)],
        input=payload,
        capture_output=True,
        text=True,
        env={"HOME": str(tmp_home), "PATH": "/usr/bin:/bin"},
        check=True,
    )
    line = proc.stdout.strip()
    return line.split("|")


def test_team_renders_session_and_weekly(tmp_path):
    fields = run("stdin-claude-ai-team.json", tmp_path)
    assert len(fields) == 9
    assert fields[0] == "42"  # used_percentage
    assert fields[4].startswith("36%")  # five_hour session
    assert fields[5].startswith("15%")  # seven_day weekly
    assert fields[6] == "sonnet"  # model, lowercased


def test_bedrock_renders_empty_rate_limit_segments(tmp_path):
    fields = run("stdin-bedrock-no-rate-limits.json", tmp_path)
    assert len(fields) == 9
    assert fields[4] == ""  # no five_hour -> empty session
    assert fields[5] == ""  # no seven_day -> empty weekly
    assert fields[8] == "feature/x"  # worktree branch still rendered


def test_mid_stream_only_five_hour(tmp_path):
    fields = run("stdin-mid-stream.json", tmp_path)
    assert fields[4].startswith("4%")  # five_hour present
    assert fields[5] == ""  # seven_day absent


def test_empty_stdin_falls_back(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(PARSER)],
        input="",
        capture_output=True,
        text=True,
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
        check=True,
    )
    assert proc.stdout.startswith("0|")
    # The fallback must honour the full 9-field contract.
    assert len(proc.stdout.strip().split("|")) == 9


def test_parser_never_reads_the_cost_field():
    """``cost.total_cost_usd`` is an API-equivalent estimate; a subscription
    plan bills nothing by it. The docstring may explain that — the code must
    not read it, so check the AST body with the docstring dropped.
    """
    body = ast.parse(PARSER.read_text()).body
    if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    code = "\n".join(ast.unparse(node) for node in body)
    assert "total_cost_usd" not in code


def test_rendered_statusline_has_no_dollar_segment(tmp_path):
    """End-to-end through statusline.sh: no fixture may render a $ amount."""
    for fixture in sorted(FIXTURES.glob("*.json")):
        rendered = subprocess.run(
            ["bash", str(RENDERER)],
            input=fixture.read_text(),
            capture_output=True,
            text=True,
            env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
            check=True,
        ).stdout
        assert "$" not in rendered, f"{fixture.name} rendered a $ segment: {rendered!r}"


def test_fmt_time_remaining_future_epoch():
    future = time.time() + 3 * 3600 + 5 * 60  # ~3h5m out
    out = slp.fmt_time_remaining(future)
    assert out.strip() in {"3h5m", "3h4m", "3h6m"}  # allow clock drift


def test_fmt_time_remaining_past_epoch_is_empty():
    assert slp.fmt_time_remaining(time.time() - 10) == ""


def test_fmt_time_remaining_none_is_empty():
    assert slp.fmt_time_remaining(None) == ""


def test_fmt_tokens_scaling():
    assert slp.fmt_tokens(950) == "950"
    assert slp.fmt_tokens(12_300) == "12k"
    assert slp.fmt_tokens(2_400_000) == "2.4M"


def test_no_network_imports():
    """The rewrite must not call the network or read a credential file."""
    src = PARSER.read_text()
    assert "import urllib" not in src
    assert "urllib.request" not in src
    assert "api.anthropic.com" not in src
    assert ".credentials.json" not in src


def test_fixtures_are_valid_json():
    for f in FIXTURES.glob("*.json"):
        json.loads(f.read_text())
