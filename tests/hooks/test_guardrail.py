#!/usr/bin/env python3
"""Tests for core/hooks/pre-tool/guardrail.py (PreToolUse blocklist + prompts).

The Co-Authored-By cases are the load-bearing ones: the Claude Code system
prompt instructs adding that trailer and the rig forbids it, so prose alone
cannot settle the conflict. Exit 2 is the hard block that does.
"""

import json
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
