#!/usr/bin/env python3
"""Stop hook: log the subscription plan usage at the end of every turn.

On a Claude subscription the cost of work is the share of the 5-hour and weekly
limits it uses, not dollars. Hooks never receive those percentages; the statusline
does, and keeps the latest values in PLAN_SNAPSHOT. This hook samples that file
into COST_LOG once per turn, tagged with the session that just finished a turn, so
the log is a time series of plan usage per session (the session scorer reports
weekly peaks from it). No snapshot (no statusline, or not a subscription) means
nothing is logged. API-equivalent dollars per session come from the transcripts
instead (utils/transcript_usage.py), because reading a transcript every turn is
too slow for a Stop hook.

Never raises; one JSONL line per logged turn, the log rotated to COST_LOG_LINES.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.constants import COST_LOG, PLAN_SNAPSHOT  # noqa: E402
from utils.hooklib import append_jsonl, read_payload  # noqa: E402

# About 1.3k turns a month: 20k rows keep more than a year of plan history.
COST_LOG_LINES = 20_000
COST_LOG_BYTES = 8_000_000


def plan_row(session_id: str, snapshot: dict) -> dict | None:
    """The log row for one turn, or None when the snapshot holds no plan."""
    plan = snapshot.get("plan")
    if not isinstance(plan, dict):
        return None
    week = plan.get("seven_day") or {}
    hours = plan.get("five_hour") or {}
    now = datetime.now()
    return {
        "session_id": session_id,
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "plan_week_pct": week.get("used_percentage"),
        "plan_week_resets_at": week.get("resets_at"),
        "plan_5h_pct": hours.get("used_percentage"),
        "plan_5h_resets_at": hours.get("resets_at"),
        "plan_updated": snapshot.get("updated"),
    }


def main() -> None:
    payload = read_payload()
    session_id = payload.get("session_id", "")
    if not session_id:
        sys.exit(0)
    try:
        row = plan_row(session_id, json.loads(PLAN_SNAPSHOT.read_text()))
        if row is not None:
            append_jsonl(COST_LOG, row, COST_LOG_LINES, COST_LOG_BYTES)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
