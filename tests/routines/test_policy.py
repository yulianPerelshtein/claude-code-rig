"""Outcome-policy hard invariants for the routine runner.

These are the runner-side backstop that the model is never trusted to obey: no
push to a default branch, no merge, no writes outside the target, no writes to
deployed ~/.claude source originals, and no destructive commands. The
destructive-command base is loaded from the SAME core/hooks/blocked-commands.json
the PreToolUse guardrail uses, so the two never drift; the runner appends the
routine-specific invariants the interactive guardrail does not carry (merge / PR
merge / skip-permissions).
"""

import json
import re
from pathlib import Path

import pytest

from runner.policy import (
    PolicyError,
    assert_command_allowed,
    assert_path_in_target,
    assert_push_allowed,
    load_blocked_patterns,
)


def test_blocks_push_to_main():
    with pytest.raises(PolicyError, match="default branch"):
        assert_push_allowed(branch="main", default_branch="main")


def test_blocks_push_to_master_even_if_not_default():
    with pytest.raises(PolicyError, match="default branch"):
        assert_push_allowed(branch="master", default_branch="develop")


def test_allows_feature_branch_push():
    assert_push_allowed(
        branch="routine/weekly-retro-2026-06-21", default_branch="main"
    )


def test_blocks_write_outside_target(tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    with pytest.raises(PolicyError, match="outside target"):
        assert_path_in_target(tmp_path / "other" / "f.md", target)


def test_allows_write_inside_target(tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    assert_path_in_target(target / "learnings" / "distilled.md", target)


def test_blocks_deployed_home_claude(tmp_path):
    """The REAL ~/.claude is protected regardless of target (precise to $HOME)."""
    target = tmp_path / "proj"
    target.mkdir()
    deployed = Path.home() / ".claude" / "CLAUDE.md"
    with pytest.raises(PolicyError, match="deployed"):
        assert_path_in_target(deployed, target)


def test_allows_target_local_claude_dir(tmp_path):
    """A target's OWN project-local .claude/ is writable (not the deployed one)."""
    target = tmp_path / "proj"
    (target / ".claude").mkdir(parents=True)
    assert_path_in_target(target / ".claude" / "plans" / "today.md", target)


@pytest.mark.parametrize(
    "cmd",
    [
        "git push --force origin main",
        "git push -f origin feature",
        "rm -rf /",
        "rm -r -f build",
        "git merge develop",
        "gh pr merge 1",
        "git reset --hard HEAD~1",
        "claude -p '/x' --dangerously-skip-permissions",
    ],
)
def test_blocks_destructive_and_merge(cmd):
    with pytest.raises(PolicyError):
        assert_command_allowed(cmd)


@pytest.mark.parametrize(
    "cmd",
    [
        "gh pr create --draft --title x --body y",
        "git push -u origin routine/weekly-retro-2026-06-21",
        "git fetch --quiet",
        "git status --porcelain",
    ],
)
def test_allows_safe_commands(cmd):
    assert_command_allowed(cmd)


def test_blocklist_loaded_from_shipped_json():
    """The destructive base is the SAME guardrail blocklist (no drift)."""
    repo = Path(__file__).resolve().parents[2]
    shipped = json.loads((repo / "core/hooks/blocked-commands.json").read_text())
    shipped_regexes = {p["regex"] for p in shipped["patterns"]}
    loaded = {pat.pattern for pat in load_blocked_patterns()}
    # every shipped pattern is present in the runner's compiled set
    assert shipped_regexes <= loaded


def test_falls_back_when_blocklist_missing(tmp_path):
    """A missing JSON must not disable the routine-specific invariants."""
    missing = tmp_path / "nope.json"
    pats = load_blocked_patterns(missing)
    assert pats  # non-empty fallback
    blob = " ".join(p.pattern for p in pats)
    assert "merge" in blob and "force" in blob


def test_extras_present_even_with_real_json():
    """merge / pr merge / skip-permissions are runner-added, not in the guardrail."""
    blob = " ".join(p.pattern for p in load_blocked_patterns())
    assert re.search(r"merge", blob)
    assert "dangerously-skip-permissions" in blob
