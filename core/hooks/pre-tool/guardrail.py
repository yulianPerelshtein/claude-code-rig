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


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool = data.get("tool_name", "")

    if tool == "Bash":
        command = data.get("tool_input", {}).get("command", "")
        # WSL OS-isolation: the Windows mount is off-limits for read AND write,
        # including via Bash (echo >, cp, tee, cat, ...). The Write/Edit branch
        # below only covers tool-level writes, so enforce it for Bash here too.
        if "/mnt/c/" in command:
            print(
                "GUARDRAIL BLOCKED: WSL OS-isolation — do not read from or "
                "write to the Windows mount (/mnt/c/).\n"
                f"Command was: {command[:200]}",
                file=sys.stderr,
            )
            sys.exit(2)
        blocklist = load_blocklist()
        for pattern, reason in blocklist:
            if re.search(pattern, command, re.IGNORECASE):
                print(
                    f"GUARDRAIL BLOCKED: {reason}\nCommand was: {command[:200]}",
                    file=sys.stderr,
                )
                sys.exit(2)

    elif tool in ("Write", "Edit"):
        path = (
            data.get("tool_input", {}).get("path", "")
            or data.get("tool_input", {}).get("file_path", "")
        )
        # Enforce WSL OS-isolation: never write to the Windows filesystem mount.
        if "/mnt/c/" in path:
            print(
                f"BLOCKED: Writing to Windows filesystem ({path}) "
                "violates OS isolation.",
                file=sys.stderr,
            )
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
