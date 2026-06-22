#!/usr/bin/env python3
"""Tests for core/hooks/pre-tool/tdd_commit_gate.py (opt-in PreToolUse gate)."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "core" / "hooks" / "pre-tool" / "tdd_commit_gate.py"


def init_repo(path: Path, last_subject: str | None) -> None:
    def run(*a):
        return subprocess.run(a, cwd=path, check=True, capture_output=True)

    run("git", "init", "-q")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    if last_subject is not None:
        (path / "f.txt").write_text("x")
        run("git", "add", "f.txt")
        run("git", "commit", "-q", "-m", last_subject)


def gate(command: str, cwd: Path, enabled: bool) -> int:
    env = {"PATH": "/usr/bin:/bin"}
    if enabled:
        env["CC_TDD_GATE"] = "1"
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
    )
    return proc.returncode


def test_disabled_by_default(tmp_path):
    init_repo(tmp_path, "chore: setup")
    # Even a TDD-violating feat passes when the gate is not enabled.
    assert gate('git commit -m "feat(api): add endpoint"', tmp_path, enabled=False) == 0


def test_blocks_feat_without_preceding_test(tmp_path):
    init_repo(tmp_path, "chore: setup")
    assert gate('git commit -m "feat(api): add endpoint"', tmp_path, enabled=True) == 2


def test_allows_feat_after_matching_test(tmp_path):
    init_repo(tmp_path, "test(api): failing endpoint test")
    assert gate('git commit -m "feat(api): add endpoint"', tmp_path, enabled=True) == 0


def test_allows_feat_after_test_different_scope_blocked(tmp_path):
    init_repo(tmp_path, "test(ui): something else")
    assert gate('git commit -m "feat(api): add endpoint"', tmp_path, enabled=True) == 2


def test_non_feat_passes(tmp_path):
    init_repo(tmp_path, "chore: setup")
    assert gate('git commit -m "fix(api): patch"', tmp_path, enabled=True) == 0


def test_scopeless_feat_passes(tmp_path):
    init_repo(tmp_path, "chore: setup")
    assert gate('git commit -m "feat: broad change"', tmp_path, enabled=True) == 0


def test_non_commit_command_passes(tmp_path):
    init_repo(tmp_path, "chore: setup")
    assert gate("ls -la", tmp_path, enabled=True) == 0


def test_fresh_repo_allows(tmp_path):
    init_repo(tmp_path, None)  # no commits yet
    assert gate('git commit -m "feat(api): first"', tmp_path, enabled=True) == 0


def test_blocks_with_leading_global_option(tmp_path):
    init_repo(tmp_path, "chore: setup")
    cmd = 'git -c user.email=x commit -m "feat(api): y"'
    assert gate(cmd, tmp_path, enabled=True) == 2


def test_blocks_with_no_pager_option(tmp_path):
    init_repo(tmp_path, "chore: setup")
    assert gate('git --no-pager commit -m "feat(api): y"', tmp_path, enabled=True) == 2


def test_blocks_message_no_space(tmp_path):
    init_repo(tmp_path, "chore: setup")
    assert gate('git commit -m"feat(api): y"', tmp_path, enabled=True) == 2


def test_blocks_long_message_equals(tmp_path):
    init_repo(tmp_path, "chore: setup")
    assert gate('git commit --message="feat(api): y"', tmp_path, enabled=True) == 2


def test_commit_graph_subcommand_not_blocked(tmp_path):
    init_repo(tmp_path, "chore: setup")
    # `git commit-graph write` is not a commit; no -m, must pass.
    assert gate("git commit-graph write", tmp_path, enabled=True) == 0
