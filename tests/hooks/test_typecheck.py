"""Tests for core/hooks/post-tool/typecheck.py.

ruff and dmypy are replaced by a recorder (git stays real), so the tests pin the
hook's own decisions: where the daemon runs, where its status file lives, and
that a timeout never blocks.
"""

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "typecheck", REPO / "core" / "hooks" / "post-tool" / "typecheck.py"
)
assert SPEC is not None and SPEC.loader is not None
typecheck = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(typecheck)
REAL_RUN = subprocess.run


def ok(cmd, **kwargs):
    """A ruff or dmypy run that finds nothing."""
    return subprocess.CompletedProcess(cmd, 0, "", "")


@pytest.fixture(autouse=True)
def cache_home(tmp_path, monkeypatch):
    """Keep the hook's status files out of the real user cache."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return tmp_path / "cache"


def repo_with(path: Path, name: str) -> Path:
    """A fresh git repo at ``path`` holding one Python file; returns the file."""
    REAL_RUN(["git", "init", "-q", str(path)], check=True)
    source = path / "pkg" / name
    source.parent.mkdir(parents=True)
    source.write_text("x: int = 1\n")
    return source


def run_hook(monkeypatch, source: Path, tool_run=ok):
    """Run the hook on an Edit of ``source``; return its exit code and tool calls."""
    calls = []

    def fake_run(cmd, **kwargs):
        if cmd[0] == "git":
            return REAL_RUN(cmd, **kwargs)
        calls.append((cmd, kwargs))
        return tool_run(cmd, **kwargs)

    monkeypatch.setattr(typecheck.subprocess, "run", fake_run)
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(source)}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    with pytest.raises(SystemExit) as exit_:
        typecheck.main()
    return exit_.value.code, calls


def dmypy_call(calls):
    return next((cmd, kwargs) for cmd, kwargs in calls if "dmypy" in cmd)


def test_a_file_outside_any_repo_is_not_checked(tmp_path, monkeypatch):
    """Scratch probes get neither ruff nor dmypy."""
    probe = tmp_path / "probe.py"
    probe.write_text("x = 1\n")
    assert run_hook(monkeypatch, probe) == (0, [])


def test_the_daemon_runs_from_the_files_own_work_tree(
    tmp_path, monkeypatch, cache_home
):
    """One daemon per work tree, wherever the session stands; status in the cache."""
    first = repo_with(tmp_path / "main", "a.py")
    second = first.parent / "b.py"
    second.write_text("y: int = 2\n")
    other = repo_with(tmp_path / "worktree", "a.py")
    monkeypatch.chdir(other.parent)
    status = {}
    for source in (first, second, other):
        _, calls = run_hook(monkeypatch, source)
        cmd, kwargs = dmypy_call(calls)
        status[source] = Path(cmd[cmd.index("--status-file") + 1])
        assert Path(kwargs["cwd"]).resolve() == source.parents[1].resolve()
        assert status[source].parent == cache_home / "claude-code-rig" / "dmypy"
    assert status[first] == status[second] != status[other]


@pytest.mark.parametrize("slow", ["ruff", "dmypy"])
def test_a_timeout_skips_the_check_without_an_error(
    tmp_path, monkeypatch, capsys, slow
):
    """A step past its cap ends the hook quietly, not with a traceback."""
    source = repo_with(tmp_path / "repo", "a.py")

    def times_out(cmd, **kwargs):
        if slow in cmd:
            raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])
        return ok(cmd)

    code, _ = run_hook(monkeypatch, source, times_out)
    assert code == 0
    assert capsys.readouterr().err == ""
