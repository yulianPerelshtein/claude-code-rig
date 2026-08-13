#!/usr/bin/env python3
"""Regression tests for run-routine.sh's environment repair.

`systemd --user` starts services with a minimal PATH that contains neither `uv`
nor `claude` (both under ~/.local/bin). Every timer-fired routine therefore
exited 127 while the identical command succeeded in a login shell — a failure
mode invisible to any check that only asserts files exist. The entrypoint now
repairs its own PATH, and these tests pin that.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RUN_ROUTINE = REPO / "core" / "routines" / "run-routine.sh"

# The repair resolves real tools from the real HOME; without them there is
# nothing to find and the test would assert on the wrong thing.
needs_tools = pytest.mark.skipif(
    not (shutil.which("uv") and shutil.which("claude")),
    reason="requires uv and claude on the developer PATH",
)

MINIMAL_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def run_with_path(
    path_value: str, tmp_path: Path, home: str | None = None
) -> subprocess.CompletedProcess:
    # /bin/bash by absolute path: the point is to constrain the script's PATH,
    # not to make the interpreter itself unfindable.
    argv = ["/bin/bash", str(RUN_ROUTINE), "dream-loop"]
    argv += ["--target", str(tmp_path), "--dry-run"]
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        env={"HOME": home or os.path.expanduser("~"), "PATH": path_value},
    )


@needs_tools
def test_dry_run_survives_the_systemd_user_path(tmp_path):
    """The exact PATH `systemctl --user show-environment` reports."""
    proc = run_with_path(MINIMAL_PATH, tmp_path)
    assert proc.returncode == 0, f"exit {proc.returncode}\nstderr:\n{proc.stderr}"
    assert "[dry-run]" in proc.stdout


def test_reports_the_missing_tool_instead_of_exiting_127_blind(tmp_path):
    """A HOME with no ~/.local/bin leaves the tools genuinely unreachable. The
    failure must name what is missing — a bare 127 is what made this silent."""
    empty_home = tmp_path / "home"
    empty_home.mkdir()
    proc = run_with_path("/usr/bin:/bin", tmp_path, home=str(empty_home))
    assert proc.returncode == 127
    assert "not found on PATH" in proc.stderr


def test_entrypoint_is_executable_and_parses():
    assert os.access(RUN_ROUTINE, os.X_OK), "run-routine.sh must stay executable"
    syntax = subprocess.run(
        ["bash", "-n", str(RUN_ROUTINE)], capture_output=True, text=True, check=False
    )
    assert syntax.returncode == 0, syntax.stderr
