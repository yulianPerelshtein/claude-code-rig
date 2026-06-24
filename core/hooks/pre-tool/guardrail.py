#!/usr/bin/env python3
import sys
import json
import re
import os
from pathlib import Path


def load_blocklist() -> list[tuple[str, str]]:
    """Load blocked patterns from JSON config. Falls back to empty list on error.

    Resolves the blocklist relative to this file first (it ships at
    ``core/hooks/blocked-commands.json`` next to the hook tree, which works in
    the plugin cache dir via ``${CLAUDE_PLUGIN_ROOT}``), then falls back to the
    legacy deployed path ``~/.claude/hooks/blocked-commands.json``.
    """
    candidates = [
        Path(__file__).resolve().parent.parent / "blocked-commands.json",
        Path(os.path.expanduser("~/.claude/hooks/blocked-commands.json")),
    ]
    for config_path in candidates:
        try:
            with open(config_path) as f:
                data = json.load(f)
            return [(p["regex"], p["reason"]) for p in data.get("patterns", [])]
        except Exception:
            continue
    return []


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
        blocklist = load_blocklist()
        for pattern, reason in blocklist:
            if re.search(pattern, command, re.IGNORECASE):
                print(
                    f"GUARDRAIL BLOCKED: {reason}\nCommand was: {command[:200]}",
                    file=sys.stderr,
                )
                sys.exit(2)
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
