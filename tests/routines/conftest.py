"""Shared fixtures for the routines runner tests."""

import subprocess

import pytest


@pytest.fixture
def git_repo(tmp_path):
    """A throwaway git repo with one commit on `main`."""

    def run(*a):
        subprocess.run(a, cwd=tmp_path, check=True, capture_output=True)

    run("git", "init", "-b", "main")
    run("git", "config", "user.email", "t@t")
    run("git", "config", "user.name", "t")
    (tmp_path / "README.md").write_text("seed\n")
    run("git", "add", "-A")
    run("git", "commit", "-m", "seed")
    return tmp_path
