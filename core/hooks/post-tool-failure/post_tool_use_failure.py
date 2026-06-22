#!/usr/bin/env python3
"""
PostToolUseFailure hook — logs failed tool calls and injects
guidance back into Claude's context via additionalContext.

Pattern-matches on error messages to provide actionable advice
that prevents blind retries and steers toward the right fix.
"""

import json
import sys
from pathlib import Path

# utils/ lives at the hooks root (core/hooks/), one level up from this
# event subdirectory (core/hooks/post-tool-failure/).
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.constants import ensure_session_log_dir


# ponytail: linear error->guidance dispatch; the many returns ARE the clearest
# form here. Convert to a {pattern: guidance} table only if this keeps growing.
def get_failure_guidance(  # noqa: C901, PLR0911
    tool_name: str, tool_input: dict, error: str
) -> str | None:
    """Return actionable guidance based on the failure pattern."""
    error_lower = error.lower() if error else ""

    if "hook" in error_lower and "denied" in error_lower:
        return (
            "This was blocked by a PreToolUse hook rule in "
            ".claude/hooks/blocked-commands.json. "
            "Do NOT retry the same command. Use a different "
            "approach or ask the user if they want to allow it."
        )

    if "permission" in error_lower and "denied" in error_lower:
        return (
            "The user denied this tool call. Do NOT retry "
            "the same action. Ask the user what they would "
            "like you to do instead."
        )

    if "sibling tool call" in error_lower:
        return (
            "This failed because a parallel sibling tool "
            "call errored. Retry this tool call individually."
        )

    if tool_name in ("Read", "Edit", "Write"):
        file_path = tool_input.get("file_path", "")
        # Edit-specific first: for Edit, "not found"/"not unique" means the
        # target STRING, not a missing file — route it to the right guidance
        # before the generic file-not-found check below can shadow it.
        if tool_name == "Edit" and (
            "not found" in error_lower or "not unique" in error_lower
        ):
            return (
                "The Edit target string was not found or not unique in the file. "
                "Read the file first to see its current contents, then retry "
                "with the exact string from the file."
            )
        if "not found" in error_lower or "no such file" in error_lower:
            return (
                f"File not found: {file_path}. "
                "Use Glob to search for the correct path before retrying."
            )
        if "read" in error_lower and "before" in error_lower:
            return (
                "You must Read the file before using Edit or Write. "
                "Read the file first, then retry."
            )

    if tool_name == "Bash":
        if "timeout" in error_lower or "timed out" in error_lower:
            return (
                "Command timed out. Consider: increasing the timeout parameter, "
                "using run_in_background: true, or breaking into smaller steps."
            )
        if error:
            return (
                "Bash command failed. Analyze the error output before retrying. "
                "Do NOT run the same command unchanged."
            )

    if tool_name.startswith("mcp__"):
        return (
            "MCP tool failed. Check that tool parameters are correct "
            "and the MCP server is running."
        )

    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)

        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        session_id = data.get("session_id", "unknown")
        error = data.get("tool_error", "")

        # Logging — append one JSON object per line (JSONL). Append-only keeps
        # this O(1) per failure instead of reading and rewriting the whole log.
        log_dir = ensure_session_log_dir(session_id)
        log_path = log_dir / "post_tool_use_failure.jsonl"

        entry: dict = {
            "tool_name": tool_name,
            "tool_use_id": data.get("tool_use_id", ""),
            "session_id": session_id,
            "hook_event_name": data.get("hook_event_name", "PostToolUseFailure"),
            "error": error,
        }
        if tool_name == "Bash":
            entry["command"] = tool_input.get("command", "")[:300]
        elif tool_name in ("Write", "Edit", "Read"):
            entry["file_path"] = tool_input.get("file_path", "")
        elif tool_name.startswith("mcp__"):
            parts = tool_name.split("__")
            if len(parts) >= 3:
                entry["mcp_server"] = parts[1]
                entry["mcp_tool_name"] = "__".join(parts[2:])
            entry["input_keys"] = list(tool_input.keys())[:10]

        with log_path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

        # Guidance injection
        guidance = get_failure_guidance(tool_name, tool_input, error)
        if guidance:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PostToolUseFailure",
                            "additionalContext": guidance,
                        }
                    }
                )
            )

    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
