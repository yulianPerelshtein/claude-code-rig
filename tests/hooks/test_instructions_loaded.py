#!/usr/bin/env python3
"""Tests for core/hooks/instructions-loaded/instructions_loaded.py (#27).

Covers append-only JSONL audit of loaded instruction files, the required +
optional fields per the InstructionsLoaded schema, session_id sanitization,
malformed-stdin tolerance, and the never-raises / exit-0 contract.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "core" / "hooks" / "instructions-loaded" / "instructions_loaded.py"


def run_hook(home: Path, payload: object) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home)}
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )


def run_hook_env(
    home: Path, payload: object, extra_env: dict
) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home)}
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def log_lines(home: Path) -> list[dict]:
    log = home / ".claude" / "data" / "logs" / "instructions_loaded.jsonl"
    if not log.is_file():
        return []
    return [json.loads(ln) for ln in log.read_text().splitlines() if ln.strip()]


def test_logs_required_fields(tmp_path):
    proc = run_hook(
        tmp_path,
        {
            "session_id": "sess-1",
            "hook_event_name": "InstructionsLoaded",
            "file_path": "/home/u/project/CLAUDE.md",
            "memory_type": "Project",
            "load_reason": "session_start",
        },
    )
    assert proc.returncode == 0
    lines = log_lines(tmp_path)
    assert len(lines) == 1
    e = lines[0]
    assert e["session_id"] == "sess-1"
    assert e["file_path"] == "/home/u/project/CLAUDE.md"
    assert e["memory_type"] == "Project"
    assert e["load_reason"] == "session_start"
    assert "ts" in e and e["ts"]
    # Optional fields omitted when absent.
    assert "globs" not in e and "trigger_file_path" not in e


def test_includes_optional_fields_when_present(tmp_path):
    run_hook(
        tmp_path,
        {
            "session_id": "sess-1",
            "file_path": "/p/.claude/rules/python.md",
            "memory_type": "Project",
            "load_reason": "path_glob_match",
            "globs": ["**/*.py"],
            "trigger_file_path": "/p/src/app.py",
        },
    )
    e = log_lines(tmp_path)[0]
    assert e["globs"] == ["**/*.py"]
    assert e["trigger_file_path"] == "/p/src/app.py"


def test_appends_across_invocations(tmp_path):
    for r in ("session_start", "nested_traversal", "compact"):
        run_hook(tmp_path, {"session_id": "s", "file_path": "/x", "load_reason": r})
    reasons = [e["load_reason"] for e in log_lines(tmp_path)]
    assert reasons == ["session_start", "nested_traversal", "compact"]


def test_unsafe_session_id_sanitized(tmp_path):
    run_hook(tmp_path, {"session_id": "../../etc", "file_path": "/x"})
    assert log_lines(tmp_path)[0]["session_id"] == "unknown"


def test_malformed_stdin_never_raises(tmp_path):
    proc = run_hook(tmp_path, "not json")
    assert proc.returncode == 0
    assert log_lines(tmp_path) == []


def test_empty_payload_tolerated(tmp_path):
    proc = run_hook(tmp_path, {})
    assert proc.returncode == 0
    e = log_lines(tmp_path)[0]
    assert e["file_path"] == ""
    assert e["load_reason"] == ""


def test_off_switch_logs_nothing(tmp_path):
    proc = run_hook_env(
        tmp_path,
        {"session_id": "s", "file_path": "/x", "load_reason": "session_start"},
        {"CC_INSTRUCTIONS_LOG": "0"},
    )
    assert proc.returncode == 0
    assert log_lines(tmp_path) == []
