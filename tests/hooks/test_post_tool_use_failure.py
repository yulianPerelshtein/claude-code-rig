#!/usr/bin/env python3
"""Tests for core/hooks/post-tool-failure/post_tool_use_failure.py.

Payloads come from a fixture captured off a live session (tests/hooks/fixtures/).
The hook once read a `tool_error` key the event never sends, so every logged
failure recorded an empty error and no text-matching guidance branch could fire.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "core" / "hooks" / "post-tool-failure" / "post_tool_use_failure.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture() -> dict:
    return json.loads((FIXTURES / "posttoolusefailure-read.json").read_text())


def run(payload: dict, project_dir: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)},
    )
    return proc.stdout.strip()


def test_failure_fixture_carries_error_at_top_level():
    payload = load_fixture()
    assert isinstance(payload["error"], str) and payload["error"]
    assert "tool_error" not in payload


def test_missing_file_read_gets_file_not_found_guidance(tmp_path):
    out = json.loads(run(load_fixture(), tmp_path))
    context = out["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("File not found: /work/sample/missing.txt.")


def test_log_records_the_error_text(tmp_path):
    payload = load_fixture()
    run(payload, tmp_path)
    log = tmp_path / ".claude" / "data" / "logs" / payload["session_id"]
    lines = (log / "post_tool_use_failure.jsonl").read_text().splitlines()
    entry = json.loads(lines[0])
    assert entry["error"] == payload["error"]
