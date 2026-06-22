"""Report-file, append-only log (bounded), and run-state writers.

Runner-written reports land under ~/.claude/routine-reports/; run-state + the
human-readable log live in ~/.local/share/cc-rig-routines/ (mirrors the F.5
reminders pattern)."""

import json

from runner.report import append_log, write_report, write_state


def test_write_report_creates_dated_file(tmp_path):
    p = write_report(tmp_path, "monthly-drift", "no drift\n", date="2026-06-21")
    assert p.exists()
    assert "monthly-drift" in p.name
    assert "2026-06-21" in p.name
    assert "no drift" in p.read_text()


def test_state_roundtrip(tmp_path):
    write_state(
        tmp_path, "weekly-retro", status="ok", date="2026-06-21", artifact="PR#1"
    )
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["weekly-retro"]["status"] == "ok"
    assert state["weekly-retro"]["artifact"] == "PR#1"
    assert state["weekly-retro"]["date"] == "2026-06-21"


def test_state_preserves_other_routines(tmp_path):
    write_state(tmp_path, "weekly-retro", status="ok")
    write_state(tmp_path, "monthly-drift", status="ok")
    state = json.loads((tmp_path / "state.json").read_text())
    assert {"weekly-retro", "monthly-drift"} <= set(state)


def test_append_log_is_additive(tmp_path):
    append_log(tmp_path, "run a")
    append_log(tmp_path, "run b")
    text = (tmp_path / "log.txt").read_text()
    assert text.count("\n") == 2
    assert "run a" in text and "run b" in text


def test_default_date_used_when_omitted(tmp_path):
    import datetime

    p = write_report(tmp_path, "x", "body")
    assert datetime.date.today().isoformat() in p.name


def test_append_log_is_bounded(tmp_path, monkeypatch):
    """log.txt must not grow unbounded — it trims to the last N lines once it
    crosses the byte threshold (mirrors hooklib's rotate contract)."""
    from runner import report

    monkeypatch.setattr(report, "LOG_MAX_BYTES", 200)
    monkeypatch.setattr(report, "LOG_KEEP_LINES", 5)
    for i in range(200):
        append_log(tmp_path, f"line {i}")
    lines = (tmp_path / "log.txt").read_text().splitlines()
    assert len(lines) <= 6  # keep_lines (+ the final append before next rotate)
    assert "line 199" in lines[-1]
