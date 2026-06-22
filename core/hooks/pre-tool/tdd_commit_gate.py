#!/usr/bin/env python3
"""
PreToolUse hook — MVP+TDD commit gate (opt-in).

Enforces test-first discipline: a `feat(<scope>):` commit must be immediately
preceded by a `test(<scope>):` commit for the SAME scope. If not, the commit is
blocked (exit 2) with guidance.

OPT-IN: a no-op unless the environment variable CC_TDD_GATE=1 is set. With it
unset (the default), this hook exits 0 immediately and never interferes.

Scope-less or non-feat commits always pass. If there is no prior commit (fresh
repo) the gate cannot determine order and allows the commit.
"""

import json
import os
import re
import subprocess
import sys

# git commit detection: `git`, then any run of leading global options
# (-C <path>, -c k=v, --flag[=val], -x), then the `commit` subcommand.
_GIT_COMMIT_RE = re.compile(
    r"(?:^|[;&|]|\s)git\s+"
    r"(?:(?:-C\s+\S+|-c\s+\S+|--[\w-]+(?:=\S+)?|-[A-Za-z])\s+)*"
    r"commit\b"
)
# A -C <path> anywhere in the command selects the repo for `git log`.
_DASH_C_RE = re.compile(r"-C\s+(\S+)")
# Message from -m / --message, with the value quoted; tolerates `-m"x"`,
# `-m 'x'`, `--message=x`, `--message "x"`.
_MSG_RE = re.compile(r"""(?:--message|-m)\s*=?\s*("([^"]*)"|'([^']*)')""")
_FEAT_RE = re.compile(r"^feat\(([^)]+)\)!?:")
_TEST_RE = re.compile(r"^test\(([^)]+)\)!?:")


def extract_message(command: str) -> str | None:
    m = _MSG_RE.search(command)
    if not m:
        return None
    raw = m.group(2) if m.group(2) is not None else (m.group(3) or "")
    return raw.split("\n", 1)[0]


def previous_subject(command: str) -> str | None:
    """Subject line of HEAD, honouring a `git -C <path>` in the command."""
    cwd = None
    cm = _DASH_C_RE.search(command)
    if cm:
        cwd = os.path.expanduser(cm.group(1))
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def main() -> None:
    if os.environ.get("CC_TDD_GATE") != "1":
        sys.exit(0)

    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if data.get("tool_name", "") != "Bash":
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "") or ""
    if not _GIT_COMMIT_RE.search(command):
        sys.exit(0)

    message = extract_message(command)
    if not message:
        sys.exit(0)  # nothing to validate (e.g. -F file, interactive)

    feat = _FEAT_RE.match(message)
    if not feat:
        sys.exit(0)  # only feat(<scope>) commits are gated
    scope = feat.group(1)

    prev = previous_subject(command)
    if prev is None:
        sys.exit(0)  # cannot determine order (fresh repo / not a git dir)

    prev_test = _TEST_RE.match(prev)
    if prev_test and prev_test.group(1) == scope:
        sys.exit(0)  # test-first satisfied

    print(
        "TDD GATE BLOCKED (CC_TDD_GATE=1): a `feat(" + scope + "):` commit must "
        "follow a `test(" + scope + "):` commit for the same scope.\n"
        f"Previous commit was: {prev or '(none)'}\n"
        "Write the failing test first and commit it as "
        f"`test({scope}): …`, or unset CC_TDD_GATE to disable this gate.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
