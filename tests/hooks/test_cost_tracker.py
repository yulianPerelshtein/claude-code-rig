#!/usr/bin/env python3
"""Tests for core/hooks/stop/cost_tracker.py — plan usage sampled per turn.

Runs the hook as a subprocess with HOME pointed at a tmp dir, as Claude Code
would, so the real ~/.claude is never touched.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "core" / "hooks" / "stop" / "cost_tracker.py"


def run_hook(home: Path, session_id: str) -> None:
    subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"session_id": session_id, "hook_event_name": "Stop"}),
        capture_output=True,
        text=True,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
        check=True,
    )


def log_rows(home: Path) -> list[dict]:
    log = home / ".claude" / "cost-log.jsonl"
    if not log.is_file():
        return []
    return [json.loads(ln) for ln in log.read_text().splitlines() if ln.strip()]


def test_logs_the_plan_snapshot_per_turn_and_nothing_without_one(tmp_path):
    run_hook(tmp_path, "sess-a")  # no statusline has run yet
    assert log_rows(tmp_path) == []
    snapshot = tmp_path / ".claude" / "data" / "plan-usage.json"
    snapshot.parent.mkdir(parents=True)
    plan = {
        "five_hour": {"used_percentage": 12.0, "resets_at": 1762300000},
        "seven_day": {"used_percentage": 34.0, "resets_at": 1762400000},
    }
    stamp = "2026-11-04T10:00:00+00:00"
    snapshot.write_text(json.dumps({"updated": stamp, "plan": plan}))
    run_hook(tmp_path, "sess-a")
    run_hook(tmp_path, "sess-b")
    rows = log_rows(tmp_path)
    assert [r["session_id"] for r in rows] == ["sess-a", "sess-b"]
    assert rows[0]["plan_week_pct"] == 34.0
    assert rows[0]["plan_week_resets_at"] == 1762400000
    assert rows[0]["plan_5h_pct"] == 12.0
    assert "cost_usd" not in rows[0]
