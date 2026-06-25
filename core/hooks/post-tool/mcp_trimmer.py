#!/usr/bin/env python3
"""
PostToolUse hook — trims oversized MCP tool outputs to prevent context bloat.

Large MCP responses (Context7, Playwright, etc.) can silently flood the
context window. Any output over MCP_TRIM_THRESHOLD chars is truncated and
a note is injected so Claude knows to use more targeted queries.
"""

import json
import sys

MCP_TRIM_THRESHOLD = 15_000  # chars


def main() -> None:
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "")

        if not tool_name.startswith("mcp__"):
            sys.exit(0)

        tool_output = data.get("tool_response", "")
        raw = tool_output if isinstance(tool_output, str) else json.dumps(tool_output)

        if len(raw) <= MCP_TRIM_THRESHOLD:
            sys.exit(0)

        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "updatedToolOutput": (
                            raw[:MCP_TRIM_THRESHOLD]
                            + f"\n\n[OUTPUT TRIMMED: {len(raw)} chars exceeded "
                            f"{MCP_TRIM_THRESHOLD} threshold. "
                            "Use more targeted queries to reduce output.]"
                        ),
                    }
                }
            )
        )

    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
