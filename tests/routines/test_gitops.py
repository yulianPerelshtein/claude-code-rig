"""Policy-gated git helpers: default-branch detection, routine branch naming,
worktree creation, draft-PR open. Network-touching paths (push / gh) are not
exercised here — the e2e dry-run (Task 15) covers the no-write path."""

import subprocess

import pytest

from runner.gitops import (
    create_worktree,
    default_branch,
    routine_branch_name,
)
from runner.policy import PolicyError


def test_branch_name_is_namespaced():
    name = routine_branch_name("weekly-retro", "2026-06-21")
    assert name.startswith("routine/weekly-retro-")
    assert name.endswith("2026-06-21")


def test_default_branch_detected(git_repo):
    assert default_branch(git_repo) == "main"


def test_default_branch_ignores_current_feature_branch(git_repo):
    """With no origin/HEAD, default_branch must resolve to main — never the
    currently checked-out feature branch (which would block the routine push)."""
    subprocess.run(
        ["git", "-C", str(git_repo), "checkout", "-b", "routine/weekly-retro-x"],
        check=True,
        capture_output=True,
    )
    assert default_branch(git_repo) == "main"


def test_worktree_created_on_feature_branch(git_repo):
    branch = "routine/weekly-retro-2026-06-21"
    wt = create_worktree(git_repo, branch)
    try:
        assert wt.exists()
        head = subprocess.run(
            ["git", "-C", str(wt), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert head == branch
    finally:
        subprocess.run(
            ["git", "-C", str(git_repo), "worktree", "remove", "--force", str(wt)],
            capture_output=True,
        )


def test_worktree_refuses_default_branch(git_repo):
    with pytest.raises(PolicyError):
        create_worktree(git_repo, "main")
