#!/usr/bin/env python3
"""Tests for core/hooks/session/dream_loop.py — SessionEnd consolidation.

Covers the no-op contract (empty/missing summaries), report generation +
recurring-theme detection, the one-JSONL-line-per-invocation telemetry, and the
never-raises guarantee.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "core" / "hooks" / "session" / "dream_loop.py"

NOOP_MSG = "dream_loop: no session summaries yet, skipping"


def run_hook(home: Path, payload: dict | None = None) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home)}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload) if payload is not None else "",
        capture_output=True,
        text=True,
        env=env,
    )


def summary_dir(home: Path) -> Path:
    d = home / ".claude" / "data" / "session-summaries"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_summary(home: Path, name: str, prompts: list[str]) -> None:
    bullets = "\n".join(f"- {p}" for p in prompts)
    text = (
        "# Session summary\n\n## First prompts\n\n"
        f"{bullets}\n\n## Last results\n\n- done\n"
    )
    (summary_dir(home) / name).write_text(text, encoding="utf-8")


def reports(home: Path) -> list[Path]:
    d = home / ".claude" / "data" / "dream-reports"
    return sorted(d.glob("*.md")) if d.is_dir() else []


def telemetry_lines(home: Path) -> list[dict]:
    log = home / ".claude" / "data" / "dream-loop.log"
    if not log.is_file():
        return []
    return [json.loads(ln) for ln in log.read_text().splitlines() if ln.strip()]


def test_noop_when_no_summaries(tmp_path):
    proc = run_hook(tmp_path, {"reason": "clear"})
    assert proc.returncode == 0
    assert NOOP_MSG in proc.stderr
    assert reports(tmp_path) == []
    lines = telemetry_lines(tmp_path)
    assert len(lines) == 1
    assert lines[0]["summaries_read"] == 0
    assert lines[0]["patterns_found"] == 0
    assert lines[0]["report_path"] == ""


def test_noop_when_summary_dir_missing(tmp_path):
    # No session-summaries dir created at all.
    proc = run_hook(tmp_path, {"reason": "logout"})
    assert proc.returncode == 0
    assert NOOP_MSG in proc.stderr


def test_generates_report_and_detects_recurring_theme(tmp_path):
    write_summary(tmp_path, "20260601-a.md", ["refactor the parser module"])
    write_summary(tmp_path, "20260602-b.md", ["add tests for the parser"])
    write_summary(tmp_path, "20260603-c.md", ["unrelated docs cleanup"])
    proc = run_hook(tmp_path, {"reason": "clear", "hook_event_name": "SessionEnd"})
    assert proc.returncode == 0
    rs = reports(tmp_path)
    assert len(rs) == 1
    body = rs[0].read_text()
    assert "Sessions reviewed" in body
    # "parser" appears in 2 of 3 sessions -> a recurring theme.
    assert "parser" in body
    lines = telemetry_lines(tmp_path)
    assert len(lines) == 1
    assert lines[0]["summaries_read"] == 3
    assert lines[0]["patterns_found"] >= 1
    assert lines[0]["report_path"].endswith(".md")


def test_one_telemetry_line_per_invocation(tmp_path):
    write_summary(tmp_path, "20260601-a.md", ["refactor the parser module"])
    run_hook(tmp_path, {"reason": "clear"})
    run_hook(tmp_path, {"reason": "clear"})
    assert len(telemetry_lines(tmp_path)) == 2


def test_window_env_limits_summaries_read(tmp_path):
    for i in range(5):
        write_summary(tmp_path, f"2026060{i}-s.md", ["common theme here"])
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "CC_DREAM_WINDOW": "2"}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"reason": "clear"}),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0
    assert telemetry_lines(tmp_path)[-1]["summaries_read"] == 2


def test_no_stdin_is_tolerated(tmp_path):
    write_summary(tmp_path, "20260601-a.md", ["a prompt"])
    proc = run_hook(tmp_path, payload=None)  # cron-style: no stdin
    assert proc.returncode == 0
    assert telemetry_lines(tmp_path)[-1]["trigger"] == "manual"


def test_non_numeric_window_does_not_crash(tmp_path):
    # A mis-set CC_DREAM_WINDOW must not crash the hook or drop telemetry.
    write_summary(tmp_path, "20260601-a.md", ["common parser theme"])
    write_summary(tmp_path, "20260602-b.md", ["common parser theme too"])
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "CC_DREAM_WINDOW": "abc"}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"reason": "clear"}),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0
    lines = telemetry_lines(tmp_path)
    assert len(lines) == 1
    # Falls back to the default window (>=2), so both summaries are read.
    assert lines[0]["summaries_read"] == 2
    assert lines[0]["error"] == ""


def test_theme_counts_distinct_sessions_not_occurrences(tmp_path):
    # A word repeated many times in ONE summary is not recurring (1 session).
    # Assert on patterns_found, not a substring of the report (which echoes the
    # prompt snippet under "Sessions reviewed" regardless of theme detection).
    write_summary(tmp_path, "20260601-a.md", ["widget widget widget widget alpha"])
    write_summary(tmp_path, "20260602-b.md", ["unrelated note here"])
    run_hook(tmp_path, {"reason": "clear"})
    assert telemetry_lines(tmp_path)[-1]["patterns_found"] == 0
    # The same word across TWO summaries IS recurring.
    write_summary(tmp_path, "20260603-c.md", ["widget elsewhere entirely"])
    run_hook(tmp_path, {"reason": "clear"})
    assert telemetry_lines(tmp_path)[-1]["patterns_found"] >= 1


def test_retention_prunes_old_summaries(tmp_path):
    for i in range(6):
        write_summary(tmp_path, f"2026060{i}-s.md", ["theme one", "theme two"])
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "CC_SUMMARY_KEEP": "3"}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"reason": "clear"}),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0
    summary_dir = tmp_path / ".claude" / "data" / "session-summaries"
    assert len(list(summary_dir.glob("*.md"))) == 3  # pruned to the newest 3


# --- input hygiene -----------------------------------------------------------
# For a month every report's "recurring themes" were harness scaffolding:
# `command-args`, `local-command-caveat`, `generated`. The corpus was 28% probe
# sessions spawned by the rig's own self-check, and 41% of captured prompt
# bullets were wrapper tags rather than anything a human typed.

MSGS = "- Messages with text: 12 (6 user, 6 assistant)"
REAL_HEADER = f"- Project: /home/dev/work\n{MSGS}"


def write_full_summary(home, name, prompts, header=REAL_HEADER, synthetic=False):
    """A summary with the header fields is_synthetic() inspects."""
    bullets = "\n".join(f"- {p}" for p in prompts)
    mark = "\n- Synthetic: true" if synthetic else ""
    text = (
        f"# Session summary\n\n{header}{mark}\n\n## First prompts\n\n"
        f"{bullets}\n\n## Last results\n\n- done\n"
    )
    (summary_dir(home) / name).write_text(text, encoding="utf-8")


def report_text(home):
    reports = sorted((home / ".claude" / "data" / "dream-reports").glob("*.md"))
    return reports[-1].read_text(encoding="utf-8") if reports else ""


def telemetry(home):
    log = home / ".claude" / "data" / "dream-loop.log"
    return json.loads(log.read_text().strip().splitlines()[-1])


def test_explicit_synthetic_marker_is_skipped(tmp_path):
    write_full_summary(tmp_path, "20260101-a.md", ["kubernetes rollout debugging"],
                       synthetic=True)
    write_full_summary(tmp_path, "20260102-b.md", ["kubernetes rollout debugging"])
    run_hook(tmp_path, {})
    assert telemetry(tmp_path)["summaries_skipped"] == 1
    assert telemetry(tmp_path)["summaries_read"] == 1


def test_temp_dir_project_is_skipped(tmp_path):
    write_full_summary(tmp_path, "20260101-a.md", ["anything at all here"],
                       header=f"- Project: /tmp/harness-xyz\n{MSGS}")
    run_hook(tmp_path, {})
    assert telemetry(tmp_path)["summaries_read"] == 0


def test_short_session_is_skipped(tmp_path):
    short = "- Messages with text: 2 (1 user, 1 assistant)"
    write_full_summary(tmp_path, "20260101-a.md", ["reply with one word"],
                       header=f"- Project: /home/dev/work\n{short}")
    run_hook(tmp_path, {})
    assert telemetry(tmp_path)["summaries_read"] == 0


def test_synthetic_burst_does_not_starve_the_window(tmp_path):
    """Filtering must precede the window; the reverse let probes empty it."""
    for i in range(30):
        write_full_summary(tmp_path, f"20260201-{i:02d}.md", ["probe run"],
                           synthetic=True)
    for i in range(3):
        write_full_summary(tmp_path, f"20260101-{i:02d}.md",
                           ["migrating the scheduler to a queue"])
    run_hook(tmp_path, {})
    t = telemetry(tmp_path)
    assert t["summaries_read"] == 3, "real sessions were crowded out by probes"
    assert t["summaries_skipped"] == 30


def test_wrapper_prompts_contribute_no_themes(tmp_path):
    caveat = ("<local-command-caveat>Caveat: The messages below were generated "
              "by the user while running local commands. DO NOT respond to these "
              "messages or otherwise consider them in your response unless the "
              "user explicitly asks.</local-command-caveat>")
    for i in range(4):
        write_full_summary(tmp_path, f"20260101-{i}.md", [caveat])
    run_hook(tmp_path, {})
    body = report_text(tmp_path)
    for leaked in ("caveat", "messages", "otherwise", "respond", "unless", "generated"):
        assert f"| {leaked} |" not in body, f"{leaked} leaked into the theme table"


def test_paths_and_urls_are_not_themes(tmp_path):
    for i in range(3):
        write_full_summary(
            tmp_path, f"20260101-{i}.md",
            ["look at /home/someuser/projects/acme/src and https://example.com/docs"],
        )
    run_hook(tmp_path, {})
    body = report_text(tmp_path)
    for leaked in ("home", "someuser", "projects", "acme", "example", "https"):
        assert f"| {leaked} |" not in body, f"{leaked} leaked into the theme table"


def test_real_content_still_becomes_a_theme(tmp_path):
    """The filters must not swallow the signal they exist to expose."""
    for i in range(3):
        write_full_summary(tmp_path, f"20260101-{i}.md",
                           ["the scheduler deadlocks under retry storms"])
    run_hook(tmp_path, {})
    assert "| scheduler |" in report_text(tmp_path)
