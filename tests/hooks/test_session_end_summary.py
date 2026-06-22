#!/usr/bin/env python3
"""Tests for core/hooks/session/session_end.py — the session-summary writer."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "core" / "hooks" / "session" / "session_end.py"


def run_hook(payload: dict, home: Path) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home)}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def write_transcript(path: Path) -> None:
    lines = [
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "text", "text": "first prompt about widgets"}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "did the widget thing"}]}},
        {"type": "user", "message": {
            "role": "user", "content": "second plain-string prompt"}},
    ]
    path.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")


def summaries(home: Path) -> list[Path]:
    d = home / ".claude" / "data" / "session-summaries"
    return sorted(d.glob("*.md")) if d.is_dir() else []


def test_writes_summary_from_transcript(tmp_path):
    transcript = tmp_path / "t.jsonl"
    write_transcript(transcript)
    payload = {
        "session_id": "abc123",
        "reason": "clear",
        "hook_event_name": "SessionEnd",
        "cwd": "/proj",
        "transcript_path": str(transcript),
    }
    proc = run_hook(payload, tmp_path)
    assert proc.returncode == 0
    files = summaries(tmp_path)
    assert len(files) == 1
    text = files[0].read_text()
    assert "abc123" in text
    assert "first prompt about widgets" in text
    assert "second plain-string prompt" in text
    assert "did the widget thing" in text


def test_no_transcript_writes_no_summary_but_exits_zero(tmp_path):
    proc = run_hook({"session_id": "x", "reason": "other"}, tmp_path)
    assert proc.returncode == 0
    assert summaries(tmp_path) == []


def test_missing_transcript_file_is_tolerated(tmp_path):
    payload = {"session_id": "x", "transcript_path": str(tmp_path / "nope.jsonl")}
    proc = run_hook(payload, tmp_path)
    assert proc.returncode == 0
    assert summaries(tmp_path) == []


def test_legacy_event_log_still_written(tmp_path):
    proc = run_hook({"session_id": "x", "reason": "logout"}, tmp_path)
    assert proc.returncode == 0
    log = tmp_path / ".claude" / "data" / "logs" / "session_end.jsonl"
    assert log.is_file()
    last = log.read_text().splitlines()[-1]
    assert json.loads(last)["session_id"] == "x"


def test_summary_disabled_by_env(tmp_path):
    transcript = tmp_path / "t.jsonl"
    write_transcript(transcript)
    payload = {"session_id": "s", "transcript_path": str(transcript)}
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "CC_SESSION_SUMMARY": "0"}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0
    # Opt-out: no summary written, but the legacy event log still is.
    assert summaries(tmp_path) == []
    assert (tmp_path / ".claude" / "data" / "logs" / "session_end.jsonl").is_file()


def test_transcript_read_is_bounded(tmp_path):
    # A late assistant result placed beyond MAX_TRANSCRIPT_LINES must be excluded
    # from the summary (proves the read is bounded, not just that it works).
    transcript = tmp_path / "big.jsonl"
    lines = []
    for i in range(5200):
        lines.append(json.dumps({"type": "assistant", "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": f"filler {i}"}]}}))
    lines.append(json.dumps({"type": "assistant", "message": {
        "role": "assistant",
        "content": [{"type": "text", "text": "LATE_SENTINEL_RESULT"}]}}))
    transcript.write_text("\n".join(lines), encoding="utf-8")
    proc = run_hook({"session_id": "big", "transcript_path": str(transcript)}, tmp_path)
    assert proc.returncode == 0
    files = summaries(tmp_path)
    assert len(files) == 1
    assert "LATE_SENTINEL_RESULT" not in files[0].read_text()


def test_bad_stdin_exits_zero(tmp_path):
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not json",
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0
    assert summaries(tmp_path) == []


def test_malicious_session_id_is_sanitized(tmp_path):
    transcript = tmp_path / "t.jsonl"
    write_transcript(transcript)
    payload = {
        "session_id": "../../../etc/evil",
        "transcript_path": str(transcript),
    }
    proc = run_hook(payload, tmp_path)
    assert proc.returncode == 0
    files = summaries(tmp_path)
    # Exactly one summary, written safely inside the summaries dir as -unknown.md;
    # no traversal outside it.
    assert len(files) == 1
    assert files[0].name.endswith("-unknown.md")
    assert not (tmp_path / "etc" / "evil").exists()
