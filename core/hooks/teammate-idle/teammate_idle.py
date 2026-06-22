#!/usr/bin/env python3
"""
TeammateIdle hook — quality gate for premature idling.

Prevents teammates from going idle when they have assigned tasks
still in_progress. Exit 0 = warn only. Change to exit 2 to block.
"""

import json
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
        agent_name = data.get("agent_name", "unknown")
        sys.stderr.write(
            f"Teammate '{agent_name}' is going idle. "
            "If you have assigned tasks still in_progress, "
            "complete them before going idle.\n"
        )
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
