#!/usr/bin/env python3
import sys
import json
import re
import os
import shlex
from pathlib import Path


# Reading a credential file can leak secrets into the transcript, but is often
# legitimate on a dev box — so prompt, don't hard-block. Read verbs only; stops
# at the first pipe/;/& so it never binds across commands. Destructive ops still
# hard-block first (rm -rf .env is denied, not asked).
CRED_READ = re.compile(
    r"\b(cat|tac|less|more|head|tail|bat|nl|xxd|od|strings|hexdump|grep|rg|awk|sed|cut|tee)\b"
    r"[^|;&]*"
    r"(\.(env|secret|secrets|pem|key|p12|pfx)\b|credentials\b|id_rsa\b|id_ed25519\b)",
    re.IGNORECASE,
)


# Force-push is blocked outright, with one exception: rewriting a branch nobody
# else is on, with --force-with-lease, which git refuses if the remote moved.
# The exception has to be provable from the command text -- a bare --force, a
# protected branch, or a destination this cannot read all keep the block.
FORCE_PUSH_ID = "git-force-push"
DEFAULT_PROTECTED_BRANCHES = ("main", "master", "develop", "dev", "staging", "production", "release")
SHELL_SEPARATORS = re.compile(r"\|\||&&|[;&|\n]")
BARE_FORCE_FLAG = re.compile(r"-[A-Za-z]*f[A-Za-z]*")


def load_policy() -> dict | None:
    """Load the blocked patterns and the protected-branch list from JSON config.

    Resolves the config relative to this file first (it ships at
    ``core/hooks/blocked-commands.json`` next to the hook tree, which works in
    the plugin cache dir via ``${CLAUDE_PLUGIN_ROOT}``), then falls back to the
    legacy deployed path ``~/.claude/hooks/blocked-commands.json``.

    Returns ``None`` when no candidate could be read or parsed. That is a broken
    install, NOT an empty policy, and the caller must fail closed: this used to
    return ``[]``, so a partial sync silently disabled every rule and the hook
    approved a force-push without printing anything at all. A file that parses
    but declares no patterns is a deliberate empty policy and still returns [].

    Returns
    -------
    dict or None
        ``patterns`` as (id, regex, reason) triples, ``id`` being "" when the
        pattern declares none, and ``protected_branches`` as a lowercased set.
    """
    candidates = [
        Path(__file__).resolve().parent.parent / "blocked-commands.json",
        Path(os.path.expanduser("~/.claude/hooks/blocked-commands.json")),
    ]
    for config_path in candidates:
        try:
            with open(config_path) as f:
                data = json.load(f)
            patterns = [
                (p.get("id", ""), p["regex"], p["reason"]) for p in data.get("patterns", [])
            ]
        except Exception:
            continue
        declared = data.get("protectedBranches") or DEFAULT_PROTECTED_BRANCHES
        return {"patterns": patterns, "protected_branches": {b.lower() for b in declared}}
    return None


def force_push_exception(command: str, protected: set[str]) -> str | None:
    """The branch a force-push may rewrite, or None to keep the block.

    Parameters
    ----------
    command : str
        The whole Bash command line, which may chain several commands.
    protected : set[str]
        Lowercased branch names the exception never applies to.

    Returns
    -------
    str or None
        The branch name when the command pushes with ``--force-with-lease`` to
        one explicitly named, unprotected branch. None otherwise, including
        every case this cannot read: no lease, a bare ``--force`` beside it, an
        unnamed destination, or a segment shlex refuses to split.
    """
    for segment in SHELL_SEPARATORS.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue
        if "push" not in tokens:
            continue
        push_at = tokens.index("push")
        if "git" not in tokens[:push_at]:
            continue
        if not any(t.split("=", 1)[0] == "--force-with-lease" for t in tokens):
            continue
        # A bare force beside the lease wins in git, so it wins here too.
        if any(t == "--force" or BARE_FORCE_FLAG.fullmatch(t) for t in tokens):
            return None
        operands = [t for t in tokens[push_at + 1 :] if not t.startswith("-")]
        # Exactly a remote and a refspec. Anything else and the destination is
        # the upstream of whatever branch is checked out, which is not readable
        # from the command text.
        if len(operands) != 2:
            return None
        branch = operands[1].lstrip("+").split(":")[-1]
        if branch.startswith("refs/heads/"):
            branch = branch[len("refs/heads/") :]
        if not branch or branch.lower() in protected:
            return None
        return branch
    return None


def ask(reason: str) -> None:
    """Prompt the user to confirm the tool call (PreToolUse 'ask' decision).

    Unlike the legacy exit-2 deny path, the JSON decision contract is read only
    on exit 0, so this must print and exit 0.
    """
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool = data.get("tool_name", "")

    if tool == "Bash":
        command = data.get("tool_input", {}).get("command", "")
        # Destructive patterns are a hard block FIRST — even on /mnt paths,
        # `rm -rf /mnt/c/...` must be denied, not merely confirmed.
        policy = load_policy()
        if policy is None:
            ask(
                "GUARDRAIL NOT LOADED: blocked-commands.json could not be read, "
                "so NO destructive-command rule is in force right now. This is "
                "usually a partial sync — run install/sync-rig.sh. Confirm only "
                f"if you have checked this command yourself.\nCommand: {command[:200]}"
            )
        exempt_branch = force_push_exception(command, policy["protected_branches"])
        for pattern_id, pattern, reason in policy["patterns"]:
            # The exception qualifies the force-push rules only. Every other rule
            # still hard-blocks, so a force-push chained with a recursive delete
            # is denied, not merely confirmed.
            if pattern_id == FORCE_PUSH_ID and exempt_branch:
                continue
            if re.search(pattern, command, re.IGNORECASE):
                print(
                    f"GUARDRAIL BLOCKED: {reason}\nCommand was: {command[:200]}",
                    file=sys.stderr,
                )
                sys.exit(2)
        # Rewriting an unshared branch is legitimate; rewriting the wrong one is
        # not recoverable. Confirm rather than allow silently.
        if exempt_branch:
            ask(
                f"Force-push rewrites the history of '{exempt_branch}' on the remote. "
                "--force-with-lease makes git refuse if anyone else pushed, and the "
                "branch is not protected, so this is allowed with your confirmation. "
                f"Confirm only if the branch is yours.\nCommand: {command[:200]}"
            )
        # Credential-file read: prompt (see CRED_READ note above).
        if CRED_READ.search(command):
            ask(
                "This reads a credential file (.env/secret/key/...), which can "
                "expose secrets in the transcript. Prefer loading via app "
                f"config; confirm only if intended.\nCommand: {command[:200]}"
            )
        # WSL OS-isolation: the Windows mount is cross-OS and slow (9p). Working
        # there is almost always a mistake, but a deliberate artifact handoff to
        # a Windows-native tool is legitimate — so PROMPT for confirmation rather
        # than hard-blocking.
        if "/mnt/c/" in command:
            ask(
                "WSL OS-isolation: this touches the Windows mount (/mnt/c/), "
                "which is slow (9p) and outside the Linux filesystem. Confirm "
                "only if this is a deliberate artifact handoff to a "
                f"Windows-native tool.\nCommand: {command[:200]}"
            )

    elif tool in ("Write", "Edit"):
        path = (
            data.get("tool_input", {}).get("path", "")
            or data.get("tool_input", {}).get("file_path", "")
        )
        # WSL OS-isolation: prompt (don't hard-block) on writes to the Windows
        # mount — a finished-artifact handoff is the legitimate case.
        if "/mnt/c/" in path:
            ask(
                f"WSL OS-isolation: writing to the Windows mount ({path}). "
                "Confirm only if this is a deliberate artifact handoff to a "
                "Windows-native tool."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
