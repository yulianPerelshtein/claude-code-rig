"""Tests for tools/cli-helpers/git_hunks.py against a throwaway git repository."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "cli-helpers"))
import git_hunks  # noqa: E402

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}


def git(*args: str, cwd: Path) -> str:
    """Run git in `cwd` with a fixed identity and no user config."""
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def three_hunks(tmp_path, monkeypatch):
    """A repo whose one file has three unstaged changes far enough apart to be three hunks."""
    git("init", "-q", cwd=tmp_path)
    lines = [f"line {n}\n" for n in range(1, 31)]
    (tmp_path / "f.txt").write_text("".join(lines))
    git("add", "f.txt", cwd=tmp_path)
    git("commit", "-qm", "base", cwd=tmp_path)
    for n in (2, 15, 28):
        lines[n - 1] = f"changed {n}\n"
    (tmp_path / "f.txt").write_text("".join(lines))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", {**os.environ, **GIT_ENV})
    return tmp_path


def test_stage_puts_only_the_chosen_hunks_in_the_index(three_hunks):
    assert len(git_hunks.list_hunks(["f.txt"])) == 3
    git_hunks.stage("f.txt", [1, 3])
    staged = git("diff", "--cached", cwd=three_hunks)
    unstaged = git("diff", cwd=three_hunks)
    assert "+changed 2" in staged and "+changed 28" in staged and "changed 15" not in staged
    assert "+changed 15" in unstaged and "changed 2" not in unstaged


def test_an_unknown_hunk_number_stages_nothing(three_hunks):
    with pytest.raises(SystemExit, match="has 3 hunk"):
        git_hunks.stage("f.txt", [1, 4])
    assert git("diff", "--cached", cwd=three_hunks) == ""
