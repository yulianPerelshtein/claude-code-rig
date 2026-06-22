#!/usr/bin/env python3
"""Tests for core/hooks/user-prompt-submit/user_prompt_submit.py.

Covers the JSONL migration (OPTIMIZATION_AUDIT §2.10): append-only writes, the
richer fields (turn index, ts, session_id), the per-session monotonic turn
counter, the CC_PROMPT_LOG privacy off-switch, malformed-stdin tolerance, and the
never-raises contract.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "core" / "hooks" / "user-prompt-submit" / "user_prompt_submit.py"


def run_hook(
    home: Path, payload: object, extra_env: dict | None = None
) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home)}
    if extra_env:
        env.update(extra_env)
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )


def prompt_log(home: Path) -> Path:
    return home / ".claude" / "data" / "logs" / "user_prompt_submit.jsonl"


def read_lines(home: Path) -> list[dict]:
    log = prompt_log(home)
    if not log.is_file():
        return []
    return [json.loads(ln) for ln in log.read_text().splitlines() if ln.strip()]


def test_appends_jsonl_with_richer_fields(tmp_path):
    proc = run_hook(
        tmp_path,
        {"session_id": "sess-1", "prompt": "refactor the parser module"},
    )
    assert proc.returncode == 0
    lines = read_lines(tmp_path)
    assert len(lines) == 1
    entry = lines[0]
    assert entry["session_id"] == "sess-1"
    assert entry["hook_event_name"] == "UserPromptSubmit"
    assert entry["turn"] == 1
    assert entry["prompt_length"] == len("refactor the parser module")
    assert entry["prompt_preview"] == "refactor the parser module"
    assert "ts" in entry and entry["ts"]


def test_appends_not_rewrites_and_turn_increments(tmp_path):
    run_hook(tmp_path, {"session_id": "sess-1", "prompt": "first"})
    run_hook(tmp_path, {"session_id": "sess-1", "prompt": "second"})
    run_hook(tmp_path, {"session_id": "sess-1", "prompt": "third"})
    lines = read_lines(tmp_path)
    assert len(lines) == 3
    assert [e["turn"] for e in lines] == [1, 2, 3]
    assert [e["prompt_preview"] for e in lines] == ["first", "second", "third"]


def test_turn_counter_is_per_session(tmp_path):
    run_hook(tmp_path, {"session_id": "sess-a", "prompt": "a1"})
    run_hook(tmp_path, {"session_id": "sess-b", "prompt": "b1"})
    run_hook(tmp_path, {"session_id": "sess-a", "prompt": "a2"})
    lines = read_lines(tmp_path)
    by_session = {(e["session_id"], e["turn"]) for e in lines}
    assert ("sess-a", 1) in by_session
    assert ("sess-a", 2) in by_session
    assert ("sess-b", 1) in by_session


def test_preview_off_switch_logs_metadata_only(tmp_path):
    proc = run_hook(
        tmp_path,
        {"session_id": "sess-1", "prompt": "secret prompt text"},
        extra_env={"CC_PROMPT_LOG": "0"},
    )
    assert proc.returncode == 0
    entry = read_lines(tmp_path)[0]
    assert entry["prompt_preview"] == ""
    # length is still recorded so correction-density analysis keeps working.
    assert entry["prompt_length"] == len("secret prompt text")


def test_long_prompt_preview_is_capped(tmp_path):
    run_hook(tmp_path, {"session_id": "sess-1", "prompt": "x" * 500})
    entry = read_lines(tmp_path)[0]
    assert len(entry["prompt_preview"]) == 120
    assert entry["prompt_length"] == 500


def test_unsafe_session_id_is_sanitized(tmp_path):
    run_hook(tmp_path, {"session_id": "../../etc/passwd", "prompt": "p"})
    entry = read_lines(tmp_path)[0]
    assert entry["session_id"] == "unknown"


def test_malformed_stdin_never_raises(tmp_path):
    proc = run_hook(tmp_path, "not json at all")
    assert proc.returncode == 0
    # Nothing written for malformed input, and no crash.
    assert read_lines(tmp_path) == []


def test_missing_prompt_field_tolerated(tmp_path):
    proc = run_hook(tmp_path, {"session_id": "sess-1"})
    assert proc.returncode == 0
    entry = read_lines(tmp_path)[0]
    assert entry["prompt_length"] == 0
    assert entry["prompt_preview"] == ""
