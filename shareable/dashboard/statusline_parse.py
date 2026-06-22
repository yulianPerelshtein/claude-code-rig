#!/usr/bin/env python3
"""Parse Claude Code's statusline stdin JSON into a pipe-delimited line.

Rate limits are read straight from stdin: Claude Code v2.1.80+ passes
``rate_limits.{five_hour,seven_day}.{used_percentage,resets_at}`` (epoch
seconds) on the statusline JSON. No OAuth call, no cache, no network, no
credential file. The fields are absent on Bedrock / Vertex / Foundry — those
render empty session/weekly segments, which is the correct behaviour there.

Output (single line, ``|``-delimited, consumed by statusline.sh):

    used%|bar|in_tok|out_tok|cost|session|weekly|model|agent|worktree
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Mid-stream output-token suppression state (see get_stable_out).
STATE_FILE = Path.home() / ".claude" / "statusline-state.json"


# ── Helpers ───────────────────────────────────────────────────────────────────


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1_000}k"
    return str(n)


def fmt_time_remaining(resets_at: float | int | None) -> str:
    """Return e.g. ' 1h5m' for short windows, ' Mon' for multi-day windows.

    ``resets_at`` is a Unix epoch in seconds, as passed in ``rate_limits`` on
    stdin (not an ISO-8601 string).
    """
    if not resets_at:
        return ""
    try:
        reset = datetime.fromtimestamp(float(resets_at), tz=timezone.utc)
        diff = (reset - datetime.now(timezone.utc)).total_seconds()
        if diff <= 0:
            return ""
        mins = int(diff // 60)
        hours = mins // 60
        days = hours // 24
        if days >= 1:
            return " " + reset.strftime("%a")
        if hours >= 1:
            return f" {hours}h{mins % 60}m"
        return f" {mins}m"
    except Exception:
        return ""


def get_stable_out(out_raw: int) -> int:
    """Suppress mid-stream output tokens; only advance when count stabilises."""
    result = 0
    try:
        state = json.loads(STATE_FILE.read_text())
        last_out = state.get("last_out", -1)
        result = state.get("stable_out", 0)
        if out_raw == last_out:
            result = out_raw
    except Exception:
        result = 0
    try:
        STATE_FILE.write_text(json.dumps({"last_out": out_raw, "stable_out": result}))
    except Exception:
        pass
    return result


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    try:
        d = json.load(sys.stdin)
    except Exception:
        # Full 10-field contract (used|bar|in|out|cost|session|weekly|model|agent|wt).
        print("0|" + "░" * 20 + "|0|0|0.00|||?||")
        return

    cw = d.get("context_window", {})
    cu = cw.get("current_usage") or {}
    cost = d.get("cost") or {}
    model = d.get("model") or {}
    agent = d.get("agent") or {}
    wt = d.get("worktree") or {}

    used = int(cw.get("used_percentage") or 0)
    inp = cu.get("input_tokens", 0)
    out_raw = cu.get("output_tokens", 0)
    cache_r = cu.get("cache_read_input_tokens", 0)
    total_in = inp + cache_r
    usd = cost.get("total_cost_usd") or 0
    model_str = (model.get("display_name") or "?").lower()
    agent_nm = agent.get("name") or ""
    wt_branch = wt.get("branch") or ""

    filled = min(used * 20 // 100, 20)
    bar = "█" * filled + "░" * (20 - filled)

    out_tok = get_stable_out(out_raw)

    # Rate limits — straight from stdin (no OAuth, no cache, no network).
    session_str = ""
    weekly_str = ""
    rl = d.get("rate_limits") or {}
    fh = rl.get("five_hour") or {}
    sd = rl.get("seven_day") or {}
    if fh:
        pct = round(fh.get("used_percentage", 0))
        session_str = f"{pct}%{fmt_time_remaining(fh.get('resets_at'))}"
    if sd:
        pct = round(sd.get("used_percentage", 0))
        weekly_str = f"{pct}%{fmt_time_remaining(sd.get('resets_at'))}"

    print(
        f"{used}|{bar}|{fmt_tokens(total_in)}|{fmt_tokens(out_tok)}"
        f"|{usd:.2f}|{session_str}|{weekly_str}|{model_str}|{agent_nm}|{wt_branch}"
    )


if __name__ == "__main__":
    main()
