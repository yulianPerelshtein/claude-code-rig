#!/usr/bin/env python3
"""Tests for core/hooks/session/session_perf.py — Layer-1 deterministic scorer.

Covers the no-op contract (no data), flagging by each signal (cost outlier,
cost/turn, failure density, correction density, near-duplicate prompts), the
one-JSONL-line-per-invocation telemetry, the window filter, optional OTel
enrichment, retention pruning, and the never-raises guarantee. All fixtures land
in a throwaway HOME; the real ~/.claude is never touched.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "core" / "hooks" / "session" / "session_perf.py"

NOOP_MSG = "session_perf: no session data yet, skipping"


def run_hook(
    home: Path, payload: dict | None = None, extra_env: dict | None = None
) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home)}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload) if payload is not None else "",
        capture_output=True,
        text=True,
        env=env,
    )


# --- fixture writers -------------------------------------------------------


def logs_dir(home: Path) -> Path:
    d = home / ".claude" / "data" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_prompts(home: Path, session_id: str, prompts: list[str]) -> None:
    """Append prompt JSONL records (recent timestamps)."""
    path = logs_dir(home) / "user_prompt_submit.jsonl"
    now = datetime.now()
    with path.open("a", encoding="utf-8") as fh:
        for i, text in enumerate(prompts, start=1):
            fh.write(
                json.dumps(
                    {
                        "session_id": session_id,
                        "hook_event_name": "UserPromptSubmit",
                        "turn": i,
                        "ts": (now - timedelta(minutes=len(prompts) - i)).isoformat(),
                        "prompt_length": len(text),
                        "prompt_preview": text[:120],
                    }
                )
                + "\n"
            )


def write_cost(home: Path, session_id: str, cost: float) -> None:
    path = home / ".claude" / "cost-log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "cost_usd": cost,
                }
            )
            + "\n"
        )


def write_failures(home: Path, session_id: str, n: int) -> None:
    sdir = logs_dir(home) / session_id
    sdir.mkdir(parents=True, exist_ok=True)
    with (sdir / "post_tool_use_failure.jsonl").open("a", encoding="utf-8") as fh:
        for _ in range(n):
            fh.write(json.dumps({"tool_name": "Bash", "error": "boom"}) + "\n")


def report_text(home: Path) -> str:
    d = home / ".claude" / "data" / "session-perf"
    reports = sorted(d.glob("*.md")) if d.is_dir() else []
    return reports[-1].read_text() if reports else ""


def telemetry(home: Path) -> list[dict]:
    log = home / ".claude" / "data" / "session-perf.log"
    if not log.is_file():
        return []
    return [json.loads(ln) for ln in log.read_text().splitlines() if ln.strip()]


# --- contract --------------------------------------------------------------


def test_noop_when_no_data(tmp_path):
    proc = run_hook(tmp_path, {"reason": "clear"})
    assert proc.returncode == 0
    assert NOOP_MSG in proc.stderr
    assert report_text(tmp_path) == ""
    lines = telemetry(tmp_path)
    assert len(lines) == 1
    assert lines[0]["sessions_scored"] == 0
    assert lines[0]["sessions_flagged"] == 0
    assert lines[0]["report_path"] == ""


def test_one_telemetry_line_per_invocation(tmp_path):
    write_prompts(tmp_path, "sess-1", ["do a thing"])
    run_hook(tmp_path, {"reason": "clear"})
    run_hook(tmp_path, {"reason": "clear"})
    assert len(telemetry(tmp_path)) == 2


def test_no_stdin_tolerated(tmp_path):
    write_prompts(tmp_path, "sess-1", ["do a thing"])
    proc = run_hook(tmp_path, payload=None)
    assert proc.returncode == 0
    assert telemetry(tmp_path)[-1]["trigger"] == "manual"


# --- flagging by signal ----------------------------------------------------


def test_clean_sessions_not_flagged(tmp_path):
    for s in ("a", "b", "c"):
        write_prompts(tmp_path, s, ["implement the feature cleanly", "add tests"])
        write_cost(tmp_path, s, 0.10)
    run_hook(tmp_path, {"reason": "clear"})
    assert telemetry(tmp_path)[-1]["sessions_flagged"] == 0
    assert "No inefficient sessions flagged" in report_text(tmp_path)


def test_flags_correction_density(tmp_path):
    write_prompts(
        tmp_path,
        "sloppy",
        ["build the parser", "no", "wait that's wrong", "fix it", "still broken"],
    )
    write_cost(tmp_path, "sloppy", 0.10)
    run_hook(tmp_path, {"reason": "clear"})
    body = report_text(tmp_path)
    assert telemetry(tmp_path)[-1]["sessions_flagged"] == 1
    assert "sloppy" in body
    assert "correction density" in body
    assert "/optimize-prompt" in body


def test_flags_failure_density(tmp_path):
    write_prompts(tmp_path, "broken", ["run the build", "try again"])
    write_failures(tmp_path, "broken", 4)
    run_hook(tmp_path, {"reason": "clear"})
    body = report_text(tmp_path)
    assert telemetry(tmp_path)[-1]["sessions_flagged"] == 1
    assert "tool-failure density" in body
    assert "~/.claude/learnings.md" in body


def test_flags_cost_outlier(tmp_path):
    # cohort of cheap sessions + one expensive -> the expensive one is flagged.
    for s in ("cheap1", "cheap2", "cheap3"):
        write_prompts(tmp_path, s, ["normal work here please"])
        write_cost(tmp_path, s, 0.05)
    write_prompts(tmp_path, "pricey", ["normal work here please"])
    write_cost(tmp_path, "pricey", 5.00)
    run_hook(tmp_path, {"reason": "clear"})
    body = report_text(tmp_path)
    assert "pricey" in body
    assert "cost outlier" in body


def test_flags_near_duplicate_prompts(tmp_path):
    # Two substantive prompts repeated verbatim across two sessions -> each
    # session has dup_prompts >= MIN_DUP (2) and is flagged as a skill candidate.
    dup1 = "set up the database migration script"
    dup2 = "configure the staging deployment pipeline"
    write_prompts(tmp_path, "sess-x", [dup1, dup2])
    write_prompts(tmp_path, "sess-y", [dup1, dup2])
    run_hook(tmp_path, {"reason": "clear"})
    body = report_text(tmp_path)
    assert "near-duplicate" in body
    assert telemetry(tmp_path)[-1]["sessions_flagged"] == 2


def test_otel_enrichment_optional_file(tmp_path):
    write_prompts(tmp_path, "sess-otel", ["work work work here now"])
    otel = tmp_path / "otel.jsonl"
    otel.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "metric": "claude_code.token.usage",
                        "session_id": "sess-otel",
                        "type": "input",
                        "value": 90,
                    }
                ),
                json.dumps(
                    {
                        "metric": "claude_code.token.usage",
                        "session_id": "sess-otel",
                        "type": "cacheRead",
                        "value": 10,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    run_hook(
        tmp_path, {"reason": "clear"}, extra_env={"CC_OTEL_METRICS_FILE": str(otel)}
    )
    body = report_text(tmp_path)
    # cache ratio 10/100 = 0.1 < 0.5 -> low-cache flag.
    assert "low cache-hit ratio" in body


# --- window + retention ----------------------------------------------------


def test_window_excludes_old_sessions(tmp_path):
    # An old prompt (timestamp 30 days ago) is outside the default 7-day window.
    path = logs_dir(tmp_path) / "user_prompt_submit.jsonl"
    old = (datetime.now() - timedelta(days=30)).isoformat()
    path.write_text(
        json.dumps(
            {
                "session_id": "ancient",
                "turn": 1,
                "ts": old,
                "prompt_length": 5,
                "prompt_preview": "no",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    run_hook(tmp_path, {"reason": "clear"})
    assert telemetry(tmp_path)[-1]["sessions_scored"] == 0


def test_retention_prunes_old_reports(tmp_path):
    perf_dir = tmp_path / ".claude" / "data" / "session-perf"
    perf_dir.mkdir(parents=True, exist_ok=True)
    for i in range(5):
        (perf_dir / f"2026010{i}.md").write_text("stale", encoding="utf-8")
    write_prompts(tmp_path, "sess-1", ["build the parser", "no", "fix it"])
    run_hook(tmp_path, {"reason": "clear"}, extra_env={"CC_PERF_KEEP": "2"})
    remaining = list(perf_dir.glob("*.md"))
    assert len(remaining) == 2


def test_bad_window_env_does_not_crash(tmp_path):
    write_prompts(tmp_path, "sess-1", ["build the parser", "no", "fix it"])
    proc = run_hook(tmp_path, {"reason": "clear"}, extra_env={"CC_PERF_WINDOW": "abc"})
    assert proc.returncode == 0
    assert telemetry(tmp_path)[-1]["error"] == ""


def test_unknown_session_ignored(tmp_path):
    write_prompts(tmp_path, "unknown", ["no", "fix it", "wrong again"])
    run_hook(tmp_path, {"reason": "clear"})
    assert telemetry(tmp_path)[-1]["sessions_scored"] == 0


def test_cost_only_foreign_session_not_scored(tmp_path):
    # A session present ONLY in the home-global cost log (another project) must
    # not enter this project's cohort — only prompt/failure-keyed sessions do.
    write_prompts(tmp_path, "local", ["do the local work here please"])
    write_cost(tmp_path, "local", 0.10)
    write_cost(tmp_path, "foreign", 9.99)  # no prompts/failures for "foreign"
    run_hook(tmp_path, {"reason": "clear"})
    assert telemetry(tmp_path)[-1]["sessions_scored"] == 1
    assert "foreign" not in report_text(tmp_path)


def test_failure_only_session_not_flagged_on_cost_per_turn(tmp_path):
    # A failure-only (zero-turn) session with cost must NOT trip the cost/turn
    # rule with a nonsensical "over 0 turn(s)" reason.
    write_failures(tmp_path, "failonly", 1)  # below MIN_FAILURES, so no fail flag
    write_cost(tmp_path, "failonly", 1.00)  # cost/turn would be 1.0 if turns=0->1
    run_hook(tmp_path, {"reason": "clear"})
    assert telemetry(tmp_path)[-1]["sessions_scored"] == 1
    assert telemetry(tmp_path)[-1]["sessions_flagged"] == 0
    assert "over 0 turn" not in report_text(tmp_path)


def test_otel_bad_metric_does_not_crash_scan(tmp_path):
    # A non-string "metric" must be skipped by read_otel, not abort the whole
    # scan (the readers-never-propagate contract).
    write_prompts(tmp_path, "sess-1", ["work work work here now"])
    otel = tmp_path / "otel.jsonl"
    otel.write_text(
        json.dumps({"metric": 123, "session_id": "sess-1", "value": 5}) + "\n",
        encoding="utf-8",
    )
    proc = run_hook(
        tmp_path, {"reason": "clear"}, extra_env={"CC_OTEL_METRICS_FILE": str(otel)}
    )
    assert proc.returncode == 0
    line = telemetry(tmp_path)[-1]
    assert line["error"] == ""
    assert line["sessions_scored"] == 1
