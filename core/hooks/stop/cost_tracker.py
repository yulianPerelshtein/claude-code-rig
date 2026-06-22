#!/usr/bin/env python3
import sys
import json
import os
from datetime import datetime, timedelta


def get_week_start() -> datetime:
    """Week resets Sunday at 22:00."""
    now = datetime.now()
    days_since_sunday = (now.weekday() + 1) % 7
    last_sunday = now - timedelta(days=days_since_sunday)
    week_start = last_sunday.replace(hour=22, minute=0, second=0, microsecond=0)
    if now < week_start:
        week_start -= timedelta(weeks=1)
    return week_start


def get_month_start() -> datetime:
    return datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def read_session_cost(path: str, session_id: str) -> float:
    """Cost of the just-ended session, if last-session.json matches it."""
    try:
        with open(path) as f:
            last = json.load(f)
        if last.get("session_id") == session_id:
            return float(last.get("cost_usd", 0))
    except Exception:
        pass
    return 0.0


def read_recent_entries(log_path: str, cutoff: datetime) -> list[dict]:
    """Parsed log entries with timestamp >= cutoff; malformed lines skipped."""
    entries: list[dict] = []
    if not os.path.exists(log_path):
        return entries
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if datetime.fromisoformat(entry["timestamp"]) >= cutoff:
                    entries.append(entry)
            except Exception:
                continue
    return entries


def write_log(log_path: str, entries: list[dict]) -> None:
    with open(log_path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def spend_since(entries: list[dict], start: datetime) -> float:
    """Sum of the max cost per session for entries at/after start."""
    by_session: dict[str, float] = {}
    for entry in entries:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
        except Exception:
            continue
        if ts < start:
            continue
        sid = entry["session_id"]
        cost = float(entry.get("cost_usd", 0))
        if sid not in by_session or cost > by_session[sid]:
            by_session[sid] = cost
    return round(sum(by_session.values()), 4)


def main() -> None:
    try:
        hook_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    session_id = hook_data.get("session_id", "")
    if not session_id:
        sys.exit(0)

    last_session_path = os.path.expanduser("~/.claude/last-session.json")
    log_path = os.path.expanduser("~/.claude/cost-log.jsonl")
    budget_path = os.path.expanduser("~/.claude/budget.json")
    cache_path = os.path.expanduser("~/.claude/budget-cache.json")

    now = datetime.now()
    entry = {
        "session_id": session_id,
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "cost_usd": read_session_cost(last_session_path, session_id),
    }

    week_start = get_week_start()
    month_start = get_month_start()

    # Keep only entries still inside the longest window we aggregate over, add
    # the new one, and rewrite. This bounds the log (older entries never feed
    # an aggregate) instead of letting it grow without limit.
    entries = read_recent_entries(log_path, min(week_start, month_start))
    entries.append(entry)
    write_log(log_path, entries)

    if not os.path.exists(budget_path):
        sys.exit(0)
    try:
        with open(budget_path) as f:
            budget = json.load(f)
    except Exception:
        sys.exit(0)

    cache = {
        "week_spent": spend_since(entries, week_start),
        "month_spent": spend_since(entries, month_start),
        "week_budget": float(budget.get("weekly_usd", 0)),
        "month_budget": float(budget.get("monthly_usd", 0)),
        "week_reset": "Sunday 22:00",
        "updated": now.isoformat(),
    }
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)

    sys.exit(0)


if __name__ == "__main__":
    main()
