#!/usr/bin/env python3
"""SubagentStop hook — surface a review reminder to the PARENT agent.

Plain stdout on SubagentStop goes to the debug log only; to reach the parent's
context the note must be delivered via hookSpecificOutput.additionalContext on
exit 0, which appears at the end of the turn so the parent can act on it.
(Verified against the Claude Code hooks docs.)
"""

import json
import sys


def main() -> None:
    try:
        sys.stdin.read()  # drain stdin so the harness never blocks
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SubagentStop",
                        "additionalContext": (
                            "A sub-agent just finished. Review its output before "
                            "relying on it. If it surfaced a durable lesson, capture "
                            "it with /wrap-up."
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
