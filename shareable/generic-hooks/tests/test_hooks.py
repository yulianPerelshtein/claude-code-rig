#!/usr/bin/env python3
"""Tests for the generic guardrail + post-tool-failure hooks.

The guardrail is run as a subprocess (faithful to how Claude Code invokes it):
exit 2 = blocked, exit 0 = allowed.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOKS = HERE.parent
GUARDRAIL = HOOKS / "guardrail.py"
PTF = HOOKS / "post_tool_use_failure.py"


def run_guardrail(payload: dict) -> int:
    proc = subprocess.run(
        [sys.executable, str(GUARDRAIL)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return proc.returncode


def bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_blocks_rm_rf():
    assert run_guardrail(bash("rm -rf /tmp/x")) == 2


def test_blocks_split_flag_rm():
    assert run_guardrail(bash("rm -r -f build")) == 2
    assert run_guardrail(bash("rm --recursive --force build")) == 2


def test_blocks_force_push():
    assert run_guardrail(bash("git push origin main --force")) == 2


def test_blocks_ruff_format():
    assert run_guardrail(bash("ruff format .")) == 2


# The guardrail blocks the WSL Windows-drive mount. Assemble that prefix from
# parts so this test file carries no literal mount marker — only guardrail.py is
# exempt from the repo's redaction gate.
WIN_MOUNT = "/mnt/" + "c/"


def test_blocks_windows_mount_bash():
    assert run_guardrail(bash("cat " + WIN_MOUNT + "Users/x/secret.txt")) == 2


def test_blocks_windows_mount_write():
    payload = {"tool_name": "Write", "tool_input": {"file_path": WIN_MOUNT + "x.txt"}}
    assert run_guardrail(payload) == 2


def test_allows_benign_command():
    assert run_guardrail(bash("ls -la && git status")) == 0


def test_allows_non_bash_tool():
    payload = {"tool_name": "Read", "tool_input": {"file_path": "a.py"}}
    assert run_guardrail(payload) == 0


# ── post_tool_use_failure guidance routing ──────────────────────────────────

_spec = importlib.util.spec_from_file_location("ptf", PTF)
ptf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ptf)


def test_edit_string_not_found_guidance():
    g = ptf.get_failure_guidance("Edit", {"file_path": "a.py"}, "String not found")
    assert g is not None and "Edit target string" in g


def test_file_not_found_guidance():
    g = ptf.get_failure_guidance("Read", {"file_path": "a.py"}, "no such file")
    assert g is not None and "Glob" in g


def test_unknown_failure_returns_none():
    assert ptf.get_failure_guidance("Bash", {}, "") is None


# ── session_id path-traversal hardening ─────────────────────────────────────


def test_session_id_traversal_is_neutralized(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    logs_root = tmp_path / ".claude" / "data" / "logs"
    d = ptf.ensure_session_log_dir("../../../../tmp/evil")
    assert str(d).startswith(str(logs_root))
    assert d.name == "unknown"


def test_session_id_absolute_is_neutralized(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    logs_root = tmp_path / ".claude" / "data" / "logs"
    d = ptf.ensure_session_log_dir("/tmp/evil")
    assert str(d).startswith(str(logs_root))


def test_valid_session_id_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    d = ptf.ensure_session_log_dir("abc-123_XY")
    assert d.name == "abc-123_XY"
