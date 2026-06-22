"""Orchestration tests for the runner CLI's execute() — the outcome dispatch,
error handling, run-state, and the draft-PR worktree flow — using injected
seams so no network / claude / gh is touched."""

import json
import subprocess
import types
from pathlib import Path

import pytest

from runner import cli
from runner.cli import execute
from runner.registry import Routine

REG = None  # registry_path is unused by the injected runner in these tests


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    """Point the runner's state + report dirs at the tmp tree."""
    state, reports = tmp_path / "state", tmp_path / "reports"
    monkeypatch.setattr(cli, "STATE_DIR", state)
    monkeypatch.setattr(cli, "REPORT_DIR", reports)
    return state, reports


def _routine(name, outcome, body_type="skill", script="", artifact_hint=""):
    return Routine(
        name=name,
        body=name,
        description="d",
        triggers=[{"type": "manual"}],
        target_default="cwd",
        outcome=outcome,
        body_type=body_type,
        script=script,
        artifact_hint=artifact_hint,
    )


def _ok(stdout=""):
    def runner(routine, cwd, registry_path):
        return types.SimpleNamespace(returncode=0, stdout=stdout)

    return runner


def _state(state_dir, routine):
    return json.loads((state_dir / "state.json").read_text())[routine]


def test_report_only_skill_writes_report_and_state(tmp_path, dirs):
    state, reports = dirs
    rc = execute(
        _routine("monthly-drift", "report-only"),
        tmp_path,
        REG,
        runner=_ok("drift report body\n"),
    )
    assert rc == 0
    report = next(reports.glob("*-monthly-drift.md"))
    assert "drift report body" in report.read_text()
    assert _state(state, "monthly-drift") == {
        "status": "ok",
        "date": _state(state, "monthly-drift")["date"],
        "artifact": str(report),
    }


def test_report_only_script_resolves_artifact_from_hint(tmp_path, dirs):
    """A script body's real report (written by the script, NOT printed to stdout)
    is resolved from the registry artifact_hint — the newest match this run."""
    state, reports = dirs
    out_dir = tmp_path / "dream-reports"
    out_dir.mkdir()
    (out_dir / "stale.md").write_text("old")  # pre-existing, must be ignored
    import os as _os

    _os.utime(out_dir / "stale.md", (1, 1))  # far in the past

    def writing_script(routine, cwd, registry_path):
        # the script writes its own report and prints NOTHING to stdout
        (out_dir / "20260621.md").write_text("# Dream report")
        return types.SimpleNamespace(returncode=0, stdout="")

    rc = execute(
        _routine(
            "dream-loop",
            "report-only",
            body_type="script",
            script="x.py",
            artifact_hint=str(out_dir / "*.md"),
        ),
        tmp_path,
        REG,
        runner=writing_script,
    )
    assert rc == 0
    artifact = _state(state, "dream-loop")["artifact"]
    assert artifact.endswith("20260621.md")  # the fresh report, not stale.md
    assert not reports.exists()  # runner did NOT re-write a report for a script body


def test_report_only_script_falls_back_to_stdout_path(tmp_path, dirs):
    """Without an artifact_hint, a script body's stdout last line is the artifact."""
    state, _ = dirs
    rc = execute(
        _routine("dream-loop", "report-only", body_type="script", script="x.py"),
        tmp_path,
        REG,
        runner=_ok("/tmp/some-report.md\n"),
    )
    assert rc == 0
    assert _state(state, "dream-loop")["artifact"] == "/tmp/some-report.md"


def test_draft_pr_opens_pr_only_when_changes_exist(git_repo, dirs):
    state, _ = dirs
    opened = {}

    def editing_runner(routine, cwd, registry_path):
        # modify a TRACKED file so the change is visible regardless of any
        # global gitignore (untracked names like learnings.md may be ignored).
        (cwd / "README.md").write_text("seed\nnew candidate\n")
        return types.SimpleNamespace(returncode=0, stdout="")

    def fake_pr(repo, branch, title, body):
        opened["branch"] = branch
        return f"https://example/pr/1 ({branch})"

    rc = execute(
        _routine("weekly-retro", "draft-pr"),
        git_repo,
        REG,
        runner=editing_runner,
        pr_opener=fake_pr,
    )
    assert rc == 0
    assert opened["branch"].startswith("routine/weekly-retro-")
    assert "example/pr" in _state(state, "weekly-retro")["artifact"]


def test_draft_pr_no_changes_opens_no_pr(git_repo, dirs):
    state, _ = dirs
    calls = []
    rc = execute(
        _routine("weekly-retro", "draft-pr"),
        git_repo,
        REG,
        runner=_ok(""),  # model made no edits
        pr_opener=lambda *a: calls.append(a) or "url",
    )
    assert rc == 0
    assert calls == []  # no PR opened
    assert "no changes" in _state(state, "weekly-retro")["artifact"]


def test_draft_pr_blocks_path_escape(git_repo, tmp_path, dirs):
    """A body that escapes the worktree via a symlink is blocked before commit;
    no PR is opened and the run is recorded as an error."""
    state, _ = dirs
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    calls = []

    def escaping_runner(routine, cwd, registry_path):
        (cwd / "evil").symlink_to(outside)
        return types.SimpleNamespace(returncode=0, stdout="")

    rc = execute(
        _routine("weekly-retro", "draft-pr"),
        git_repo,
        REG,
        runner=escaping_runner,
        pr_opener=lambda *a: calls.append(a) or "url",
    )
    assert rc == 1
    assert calls == []  # policy blocked it — no PR opened
    assert _state(state, "weekly-retro")["status"].startswith("error")


def test_body_failure_records_rc(tmp_path, dirs):
    state, _ = dirs

    def failing(routine, cwd, registry_path):
        return types.SimpleNamespace(returncode=7, stdout="")

    rc = execute(
        _routine("monthly-drift", "report-only"), tmp_path, REG, runner=failing
    )
    assert rc == 7
    assert _state(state, "monthly-drift")["status"] == "rc=7"


def test_exception_records_error_state(tmp_path, dirs):
    state, _ = dirs

    def boom(routine, cwd, registry_path):
        raise OSError("disk gone")

    rc = execute(_routine("monthly-drift", "report-only"), tmp_path, REG, runner=boom)
    assert rc == 1
    assert _state(state, "monthly-drift")["status"].startswith("error")
    # the run still recorded start + end + error in the log
    assert (state / "log.txt").read_text().count("\n") >= 2


def test_main_rejects_disabled_routine(tmp_path):
    """main() refuses a disabled routine (exit 3) without executing it."""
    import sys

    reg = tmp_path / "registry.yaml"
    reg.write_text(
        "version: 1\nroutines:\n  off-one:\n    body: off-one\n    description: d\n"
        "    triggers: [{type: manual}]\n    target_default: cwd\n"
        "    outcome: report-only\n    enabled: false\n"
    )
    runner_dir = Path(__file__).resolve().parents[2] / "core/routines"
    r = subprocess.run(
        [sys.executable, "-m", "runner.cli", "off-one", "--registry", str(reg)],
        capture_output=True,
        text=True,
        cwd=str(runner_dir),
    )
    assert r.returncode == 3
    assert "disabled" in r.stderr
