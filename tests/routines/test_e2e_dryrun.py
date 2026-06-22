"""End-to-end dry-run: the runner CLI works against an ARBITRARY (non-rig)
target and writes nothing (success criteria #5 reusability + #7 no-write)."""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO / "core/routines"


def _run(name, target, *extra):
    env = {**os.environ, "PYTHONPATH": str(RUNNER_PATH)}
    return subprocess.run(
        [sys.executable, "-m", "runner.cli", name, "--target", str(target), *extra],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        env=env,
    )


def test_dryrun_runs_against_arbitrary_target(tmp_path):
    r = _run("weekly-retro", tmp_path, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "dry-run" in r.stdout
    assert "weekly-retro" in r.stdout
    assert str(tmp_path) in r.stdout
    # proves the dry-run wrote nothing under the arbitrary target
    assert list(tmp_path.iterdir()) == []


def test_dryrun_script_body_shows_shipped_script(tmp_path):
    r = _run("dream-loop", tmp_path, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "body_type=script" in r.stdout
    assert "dream_loop.py" in r.stdout
    assert list(tmp_path.iterdir()) == []


def test_unknown_routine_exits_2(tmp_path):
    r = _run("does-not-exist", tmp_path, "--dry-run")
    assert r.returncode == 2
    assert "unknown routine" in r.stderr
