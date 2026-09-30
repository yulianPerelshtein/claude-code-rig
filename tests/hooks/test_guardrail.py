#!/usr/bin/env python3
"""Tests for core/hooks/pre-tool/guardrail.py (PreToolUse blocklist + prompts).

The Co-Authored-By cases are the load-bearing ones: the Claude Code system
prompt instructs adding that trailer and the rig forbids it, so prose alone
cannot settle the conflict. Exit 2 is the hard block that does.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "core" / "hooks" / "pre-tool" / "guardrail.py"

TRAILER = "Co-Authored-By: Someone <s@example.com>"


def guard(command: str, tool: str = "Bash") -> tuple[int, str]:
    """Run the hook on one command; return (exit code, stdout)."""
    payload = {"tool_name": tool, "tool_input": {"command": command}}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,  # a blocked command exits 2; that is the assertion, not an error
    )
    return proc.returncode, proc.stdout


@pytest.mark.parametrize(
    "command",
    [
        f'git commit -m "feat: x\n\n{TRAILER}"',
        f'git commit --trailer "{TRAILER}" -m "feat: x"',
        'git commit -m "fix: y" -m "co-authored-by: a <a@b.c>"',  # case-insensitive
        f'git add -A && git commit -m "feat: x\n\n{TRAILER}"',
    ],
)
def test_blocks_co_authored_by_trailer(command):
    assert guard(command)[0] == 2


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "feat(rig): wire layer 1"',
        "git log --format=%b | grep Co-Authored-By",  # reading is not authoring
        "git commit --amend --no-edit",
        # Naming the trailer is not adding one — the colon is what makes it a
        # trailer, so a subject that merely mentions it must still commit.
        'git commit -m "feat(guardrail): block Co-Authored-By trailers"',
    ],
)
def test_allows_commits_without_the_trailer(command):
    assert guard(command)[0] == 0


def test_blocks_destructive_command():
    assert guard("rm -rf build")[0] == 2


def test_prompts_rather_than_blocks_on_windows_mount():
    code, out = guard("ls /mnt/c/Users")
    # A confirmation prompt is exit 0 plus a JSON decision, not exit 2.
    assert code == 0
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "ask"

# --- git global options ------------------------------------------------------
# Git accepts global options BETWEEN `git` and the subcommand, so `git -C <path>
# push` never matched a rule anchored on `git push`. That is the rig's own idiom
# (gitops.py, cli.py), so every git rule was bypassable by the most natural
# spelling. Fragments are split to keep a blocked sequence off any single line.

FORCE_PUSH = "push --force"
SHORT_FORCE = "push origin main -f"
HARD_RESET = "reset --hard"
CLEAN_FORCE = "clean -fd"
WORKDIR = "/tmp/somerepo"


@pytest.mark.parametrize(
    "command",
    [
        f"git {FORCE_PUSH}",
        f"git -C {WORKDIR} {FORCE_PUSH}",
        f"git -C {WORKDIR} {SHORT_FORCE}",
        f"git --git-dir={WORKDIR}/.git {FORCE_PUSH}",
        f"git -c user.name=x {FORCE_PUSH}",
        f"git -C {WORKDIR} -c k=v {FORCE_PUSH}",
        f"git --no-pager {FORCE_PUSH}",
        f"git -C {WORKDIR} {HARD_RESET}",
        f"git --work-tree {WORKDIR} {HARD_RESET}",
        f"git -C {WORKDIR} {CLEAN_FORCE}",
    ],
)
def test_blocks_destructive_git_behind_global_options(command):
    assert guard(command)[0] == 2


@pytest.mark.parametrize(
    "command",
    [
        f"git -C {WORKDIR} status",
        f"git -C {WORKDIR} log --oneline",
        f"git -C {WORKDIR} diff --stat",
        "git push origin main",
        'git commit -m "ordinary message"',
    ],
)
def test_allows_ordinary_git_behind_global_options(command):
    assert guard(command)[0] == 0


# --- fail closed -------------------------------------------------------------
# A missing or corrupt blocklist used to yield an empty rule set, so the hook
# approved everything and printed nothing. A partial sync silently disarmed it.


def _isolated_hook(tmp_path, blocklist_text=None):
    """Copy the hook where neither blocklist candidate path can resolve."""
    hooks = tmp_path / "hooks" / "pre-tool"
    hooks.mkdir(parents=True)
    (tmp_path / "home").mkdir()
    if blocklist_text is not None:
        (tmp_path / "hooks" / "blocked-commands.json").write_text(blocklist_text)
    copy = hooks / "guardrail.py"
    copy.write_text(HOOK.read_text())
    return copy


def _run_isolated(hook_copy, tmp_path, command):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    proc = subprocess.run(
        [sys.executable, str(hook_copy)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(tmp_path / "home")},
    )
    return proc.returncode, proc.stdout


@pytest.mark.parametrize("blocklist_text", [None, "{not json", '{"patterns": [}'])
def test_unreadable_blocklist_prompts_instead_of_allowing(tmp_path, blocklist_text):
    hook = _isolated_hook(tmp_path, blocklist_text)
    code, out = _run_isolated(hook, tmp_path, f"git {FORCE_PUSH}")
    assert code == 0
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "ask"
    assert "GUARDRAIL NOT LOADED" in decision["permissionDecisionReason"]


def test_valid_but_empty_blocklist_is_a_deliberate_policy(tmp_path):
    """An empty pattern list parses fine and must NOT be treated as breakage."""
    hook = _isolated_hook(tmp_path, '{"patterns": []}')
    code, out = _run_isolated(hook, tmp_path, f"git {FORCE_PUSH}")
    assert (code, out.strip()) == (0, "")


# --- force-push exception for feature branches -------------------------------
# Rewriting a branch only you are on is routine, and the blanket block made it
# impossible to tidy a PR before review. The exception is narrow on purpose:
# --force-with-lease only, one named unprotected branch only, and every case the
# hook cannot read from the command text keeps the block.

LEASE = "push --force-with-lease"


def decide(command: str) -> str:
    """'block' (exit 2), 'ask' (exit 0 with a decision), or 'allow' (exit 0, silent)."""
    code, out = guard(command)
    if code == 2:
        return "block"
    if not out.strip():
        return "allow"
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


@pytest.mark.parametrize(
    "command",
    [
        f"git {LEASE} origin my-branch",
        f"git {LEASE} origin feature/thing",
        f"git -C {WORKDIR} {LEASE} origin my-branch",
        f"git {LEASE} origin HEAD:my-branch",
        f"git {LEASE}=origin/my-branch origin my-branch",
        f"cd {WORKDIR} && git {LEASE} origin my-branch",
        "git push origin my-branch --force-with-lease",
    ],
)
def test_asks_for_lease_push_to_a_feature_branch(command):
    assert decide(command) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        f"git {LEASE} origin main",
        f"git {LEASE} origin Staging",
        f"git {LEASE} origin HEAD:master",
        f"git {LEASE}",
        f"git {LEASE} origin",
        f"git {LEASE} --force origin my-branch",
        "git push -f --force-with-lease origin my-branch",
    ],
)
def test_still_blocks_every_other_force_push(command):
    assert decide(command) == "block"


def test_exception_does_not_pardon_another_rule_in_the_same_command():
    """The exception skips the force-push rule, not the rest of the blocklist."""
    assert decide(f"git {LEASE} origin my-branch && git {HARD_RESET} HEAD~1") == "block"


# --- the Read tool -----------------------------------------------------------
# The credential and Windows-mount prompts covered `cat .env` but not the Read
# tool, so the same file was one tool choice away from the transcript.


def read_decision(file_path: str) -> str:
    """'ask' or 'allow' for a Read of `file_path`."""
    payload = {"tool_name": "Read", "tool_input": {"file_path": file_path}}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    if not proc.stdout.strip():
        return "allow"
    return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]


@pytest.mark.parametrize(
    "file_path",
    [
        "/home/dev/proj/.env",
        "/home/dev/proj/.env.local",
        "/home/dev/.ssh/id_rsa",
        "/home/dev/.aws/credentials",
        "/home/dev/.claude/.credentials.json",
        "/home/dev/proj/certs/server.pem",
        "/mnt/c/Users/dev/notes.txt",
    ],
)
def test_read_of_a_credential_or_windows_path_asks(file_path):
    assert read_decision(file_path) == "ask"


@pytest.mark.parametrize(
    "file_path",
    [
        "/home/dev/proj/README.md",
        "/home/dev/proj/.venv/lib/python3.12/site.py",
        "/home/dev/proj/src/keyboard.py",
        "/home/dev/proj/environment.yml",
    ],
)
def test_read_of_an_ordinary_file_is_silent(file_path):
    assert read_decision(file_path) == "allow"


# --- stacked-PR commands -----------------------------------------------------
# gh stack wraps pushes and merges the git rules cannot see: push and sync
# force-push every layer with a lease, submit opens PRs, merge merges them.

STACK = "gh " + "stack"
MERGE = "mer" + "ge"


@pytest.mark.parametrize(
    "command",
    [
        f"{STACK} {MERGE}",
        f"{STACK} {MERGE} 42 --yes",
        f"gh pr {MERGE} 12 --squash",
        f"cd {WORKDIR} && gh pr {MERGE} 12",
    ],
)
def test_blocks_merging_pull_requests(command):
    assert decide(command) == "block"


@pytest.mark.parametrize(
    "command", [f"{STACK} push", f"{STACK} sync --prune", f"{STACK} submit --auto"]
)
def test_asks_before_stack_pushes(command):
    assert decide(command) == "ask"


@pytest.mark.parametrize(
    "command",
    [f"{STACK} view", f"{STACK} rebase", "gh pr view 12", "gh pr list --base main"],
)
def test_allows_local_and_read_only_stack_commands(command):
    assert decide(command) == "allow"


def test_confirm_list_does_not_pardon_a_blocked_command():
    assert decide(f"{STACK} push && git {HARD_RESET} HEAD~1") == "block"
