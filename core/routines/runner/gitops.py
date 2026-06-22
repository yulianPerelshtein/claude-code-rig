"""Policy-gated git operations for routines: worktree, branch, draft-PR.

Every mutating helper passes through the policy guards first, so a routine can
never push to a default branch, merge, or run a destructive command — even if
the model body asks it to. Auth (e.g. `gh auth switch`) is the operator's /
systemd unit's responsibility; the runner stays account-agnostic so routines
work against any repo (ROUTINES_DESIGN.md §7).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .policy import assert_command_allowed, assert_push_allowed


def _git(
    repo, *args: str, check: bool = True
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def default_branch(repo) -> str:
    """The branch a routine must never push to: the remote default if known,
    else whichever of main/master exists. Never falls back to the *current*
    branch (that would block the routine's own feature-branch push)."""
    remote = _git(
        repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False
    )
    if remote.returncode == 0 and remote.stdout.strip():
        return remote.stdout.strip().rsplit("/", 1)[-1]
    for candidate in ("main", "master"):
        found = _git(repo, "rev-parse", "--verify", "--quiet", candidate, check=False)
        if found.returncode == 0:
            return candidate
    return "main"


def routine_branch_name(routine: str, date: str) -> str:
    return f"routine/{routine}-{date}"


def create_worktree(repo, branch: str) -> Path:
    """Create an isolated worktree on a NEW feature branch (policy-gated).
    Cleans up the temp dir if the worktree add fails (e.g. branch exists)."""
    assert_push_allowed(branch=branch, default_branch=default_branch(repo))
    worktree = Path(tempfile.mkdtemp(prefix="cc-routine-wt-"))
    try:
        _git(repo, "worktree", "add", "-b", branch, str(worktree))
    except subprocess.CalledProcessError:
        shutil.rmtree(worktree, ignore_errors=True)
        raise
    return worktree


def remove_worktree(repo, worktree) -> None:
    """Best-effort cleanup of a worktree created by ``create_worktree``."""
    _git(repo, "worktree", "remove", "--force", str(worktree), check=False)


def open_draft_pr(repo, branch: str, title: str, body: str) -> str:
    """Push a feature branch and open a DRAFT PR (policy-gated). Never merges.

    The title/body are passed to ``gh`` as argv (list form, never shell-
    interpreted), so they are NOT scanned by the command blocklist — a learning
    whose text legitimately mentions ``rm -rf`` / ``git push --force`` must not
    abort the PR."""
    assert_push_allowed(branch=branch, default_branch=default_branch(repo))
    # runner self-check: prove the structural command we built is never one the
    # shared guardrail blocklist forbids (exercises load_blocked_patterns on the
    # real run path; the title/body are passed as argv, never scanned).
    assert_command_allowed(f"git push -u origin {branch}")
    _git(repo, "push", "-u", "origin", branch)
    created = subprocess.run(
        [
            "gh", "pr", "create", "--draft",
            "--title", title, "--body", body, "--head", branch,
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return created.stdout.strip()
