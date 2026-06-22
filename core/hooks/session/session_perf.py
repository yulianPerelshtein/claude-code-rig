#!/usr/bin/env python3
"""SessionEnd (or cron) Layer-1 deterministic session performance scorer (#30).

The *diagnostic* layer of Cluster B (ENHANCEMENTS_BACKLOG §2.10). It computes
per-session inefficiency signals from data the rig ALREADY emits — never calling
a model — ranks the worst sessions, and writes a routing scaffold to
~/.claude/data/session-perf/<date>.md. The qualitative "what-failed-where"
diagnosis is the on-demand /analyze-session skill (Layer 2); this hook only flags
*which* sessions are worth that look, and *why*, with the raw numbers.

Inputs (all already bounded by their writers):
  - prompt JSONL   (LOG_DIR/user_prompt_submit.jsonl)  -> turns, corrections, near-dups
  - cost log       (~/.claude/cost-log.jsonl)          -> cost/session (max), cost/turn
  - failure JSONL  (LOG_DIR/<sid>/post_tool_use_failure.jsonl) -> tool-failure density
  - OTel metrics   (optional, $CC_OTEL_METRICS_FILE)   -> cache ratio, edit reject rate

Contract (mirrors dream_loop.py):
  - No data at all -> exit 0 with the single stderr line
    `session_perf: no session data yet, skipping`.
  - Never raises.
  - Exactly one JSONL telemetry line per invocation to ~/.claude/data/session-perf.log:
    {ts, trigger, sessions_scored, sessions_flagged, report_path, latency_ms, error}.
  - Retention-bounded: prunes reports beyond CC_PERF_KEEP and caps the log.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.constants import (  # noqa: E402
    COST_LOG,
    LOG_DIR,
    SESSION_PERF_DIR,
    SESSION_PERF_LOG,
)
from utils.hooklib import append_jsonl, int_env, read_payload  # noqa: E402

DEFAULT_WINDOW_DAYS = 7
DEFAULT_TOP = 5
DEFAULT_KEEP = 90  # retention: max session-perf reports to keep on disk
PERF_LOG_MAX_LINES = 2000

# Correction = a short prompt that opens with a corrective marker (the model
# missed and the user is steering it back). Needs the prompt preview; when
# CC_PROMPT_LOG=0 strips previews, correction density degrades to 0 (documented).
CORRECTION_MAX_LEN = 80
CORRECTION_RE = re.compile(
    r"^\s*(no|nope|wait|stop|actually|undo|revert|fix|not\b|that'?s? (wrong|not)"
    r"|still|instead|try again|redo|again|wrong)\b",
    re.IGNORECASE,
)
MIN_DUP_LEN = 12  # ignore trivial repeats ("yes", "ok") in near-dup detection
WS_RE = re.compile(r"\s+")

# Flag thresholds + weights (transparent, deterministic). A session is flagged
# when score > 0. Weights only order the report; the raw numbers are shown too.
COST_SIGMA = 1.5  # cost outlier = mean + 1.5*std across the cohort
COST_PER_TURN_HIGH = 0.50  # USD/turn (absolute)
FAIL_DENSITY_HIGH = 0.5
MIN_FAILURES = 3
CORR_DENSITY_HIGH = 0.34
MIN_CORRECTIONS = 2
MIN_DUP = 2
CACHE_LOW = 0.5  # OTel only
EDIT_REJECT_HIGH = 0.4  # OTel only
W_COST = 3
W_COST_PER_TURN = 2
W_FAIL = 3
W_CORR = 2
W_DUP = 2
W_CACHE = 1
W_EDIT = 1

# Routing targets (the point of #30 — close the loop, not just a dashboard).
R_COST = "review context budget (context-budget-policy / otel-insights-review)"
R_COST_TURN = "tighten prompts / trim context (/optimize-prompt)"
R_FAIL = "recurring-failure rule -> ~/.claude/learnings.md via /dream-report"
R_CORR = "/optimize-prompt on the driving skill/agent; maybe a skill candidate"
R_DUP = "repeated prompt -> skill candidate (/optimize-prompt, dream-report)"
R_CACHE = "stabilise early context (otel-insights-review, context-budget-policy)"
R_EDIT = "/optimize-prompt — prompts are producing rejected edits"


# --- input readers (each guarded; a bad file never propagates) -------------


def iter_jsonl(path: Path):
    """Yield parsed objects from a JSONL file; skip blank/bad lines; tolerate a
    missing file."""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
    except OSError:
        return


def parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    # The writer emits naive local timestamps; drop any tzinfo on hand-crafted
    # input so naive-vs-aware comparisons in the window filter can't raise.
    return dt.replace(tzinfo=None)


def normalize(text: str) -> str:
    return WS_RE.sub(" ", text).strip().lower().rstrip(" .!?")


def read_prompts() -> dict[str, list[dict]]:
    """session_id -> list of prompt records from the prompt JSONL."""
    by_session: dict[str, list[dict]] = {}
    for rec in iter_jsonl(LOG_DIR / "user_prompt_submit.jsonl"):
        if not isinstance(rec, dict):
            continue
        sid = rec.get("session_id") or "unknown"
        by_session.setdefault(sid, []).append(rec)
    return by_session


def read_costs() -> dict[str, float]:
    """session_id -> max cost_usd (mirrors cost_tracker's per-session aggregation)."""
    costs: dict[str, float] = {}
    for rec in iter_jsonl(COST_LOG):
        if not isinstance(rec, dict):
            continue
        sid = rec.get("session_id")
        if not sid:
            continue
        try:
            cost = float(rec.get("cost_usd", 0))
        except (TypeError, ValueError):
            continue
        if sid not in costs or cost > costs[sid]:
            costs[sid] = cost
    return costs


def read_failures(cutoff: datetime) -> dict[str, int]:
    """session_id -> failed-tool-call count from per-session failure JSONLs.

    Only logs modified at/after `cutoff` are read, so the per-SessionEnd scan
    stays bounded by the window even as a long-lived project accumulates session
    subdirs (stale failure logs are neither read nor scored)."""
    failures: dict[str, int] = {}
    try:
        failure_logs = list(LOG_DIR.glob("*/post_tool_use_failure.jsonl"))
    except OSError:
        return failures
    for log in failure_logs:
        try:
            if datetime.fromtimestamp(log.stat().st_mtime) < cutoff:
                continue
        except OSError:
            continue
        failures[log.parent.name] = sum(1 for _ in iter_jsonl(log))
    return failures


def read_otel() -> dict[str, dict]:
    """Optional enrichment. If $CC_OTEL_METRICS_FILE points at a JSONL of OTel
    metric records, derive per-session cache ratio + edit reject rate. Absent or
    unreadable -> {} (the scorer's deterministic backbone runs without OTel,
    which is an install-deferred user action). Expected per-line shapes:
      {"metric":"claude_code.token.usage","session_id":..,"type":"input|cacheRead","value":N}
      {"metric":"claude_code.code_edit_tool.decision","session_id":..,"decision":"accept|reject","value":N}
    """
    path = os.environ.get("CC_OTEL_METRICS_FILE")
    if not path:
        return {}
    acc: dict[str, dict[str, float]] = {}
    for rec in iter_jsonl(Path(path).expanduser()):
        if not isinstance(rec, dict):
            continue
        sid = rec.get("session_id") or rec.get("session.id")
        if not sid:
            continue
        try:
            value = float(rec.get("value", 0))
        except (TypeError, ValueError):
            continue
        slot = acc.setdefault(sid, {})
        metric = rec.get("metric", "")
        if not isinstance(metric, str):
            continue
        if metric.endswith("token.usage") and rec.get("type") in ("input", "cacheRead"):
            slot[rec["type"]] = slot.get(rec["type"], 0.0) + value
        elif metric.endswith("code_edit_tool.decision") and rec.get("decision") in (
            "accept",
            "reject",
        ):
            slot[rec["decision"]] = slot.get(rec["decision"], 0.0) + value
    return {sid: _otel_ratios(slot) for sid, slot in acc.items()}


def _otel_ratios(slot: dict[str, float]) -> dict:
    out: dict = {}
    cache_total = slot.get("input", 0.0) + slot.get("cacheRead", 0.0)
    if cache_total > 0:
        out["cache_ratio"] = round(slot.get("cacheRead", 0.0) / cache_total, 3)
    edit_total = slot.get("accept", 0.0) + slot.get("reject", 0.0)
    if edit_total > 0:
        out["edit_reject_rate"] = round(slot.get("reject", 0.0) / edit_total, 3)
    return out


# --- scoring ---------------------------------------------------------------


def duplicate_index(prompts: dict[str, list[dict]]) -> dict[str, set[str]]:
    """normalized prompt text -> set of session_ids it appears in (len-gated)."""
    index: dict[str, set[str]] = {}
    for sid, recs in prompts.items():
        for rec in recs:
            preview = rec.get("prompt_preview") or ""
            norm = normalize(preview)
            if len(norm) >= MIN_DUP_LEN:
                index.setdefault(norm, set()).add(sid)
    return index


def session_signals(
    sid: str,
    prompts: list[dict],
    cost: float,
    failures: int,
    dup_index: dict[str, set[str]],
    otel: dict,
) -> dict:
    turns = len(prompts)
    corrections = sum(
        1
        for rec in prompts
        if rec.get("prompt_length", 9999) <= CORRECTION_MAX_LEN
        and CORRECTION_RE.match(rec.get("prompt_preview") or "")
    )
    dups = sum(
        1
        for rec in prompts
        if len(dup_index.get(normalize(rec.get("prompt_preview") or ""), set())) > 1
    )
    denom = max(turns, 1)
    sig = {
        "session_id": sid,
        "turns": turns,
        "cost_usd": round(cost, 4),
        "cost_per_turn": round(cost / denom, 4),
        "corrections": corrections,
        "correction_density": round(corrections / denom, 3),
        "failures": failures,
        "failure_density": round(failures / denom, 3),
        "dup_prompts": dups,
    }
    sig.update(otel)
    return sig


def cost_outlier_threshold(costs: list[float]) -> float:
    """Cohort mean + COST_SIGMA*std over the positive costs; inf if too few."""
    positive = [c for c in costs if c > 0]
    if len(positive) < 2:
        return float("inf")
    mean = sum(positive) / len(positive)
    var = sum((c - mean) ** 2 for c in positive) / len(positive)
    return mean + COST_SIGMA * (var**0.5)


# Reason builders for the rule table (kept small to stay under the line limit).
def _reason_cost(s: dict, c: float) -> str:
    return f"cost outlier: ${s['cost_usd']} (cohort cutoff ${round(c, 4)})"


def _reason_cost_turn(s: dict, _c: float) -> str:
    return f"high cost/turn: ${s['cost_per_turn']} over {s['turns']} turn(s)"


def _reason_fail(s: dict, _c: float) -> str:
    return (
        f"tool-failure density {s['failure_density']} "
        f"({s['failures']} failures / {s['turns']} turns)"
    )


def _reason_corr(s: dict, _c: float) -> str:
    return (
        f"correction density {s['correction_density']} "
        f"({s['corrections']}/{s['turns']} prompts steering back)"
    )


def _reason_dup(s: dict, _c: float) -> str:
    return f"{s['dup_prompts']} near-duplicate prompt(s) across sessions"


def _reason_cache(s: dict, _c: float) -> str:
    return f"low cache-hit ratio {s['cache_ratio']} (cache-busting waste)"


def _reason_edit(s: dict, _c: float) -> str:
    return f"high edit reject rate {s['edit_reject_rate']} (unwanted edits)"


# Transparent rule table: (predicate, weight, reason builder, routing target).
_RULES = [
    (
        lambda s, c: s["cost_usd"] > 0 and s["cost_usd"] > c,
        W_COST,
        _reason_cost,
        R_COST,
    ),
    (
        lambda s, _c: s["turns"] >= 1 and s["cost_per_turn"] >= COST_PER_TURN_HIGH,
        W_COST_PER_TURN,
        _reason_cost_turn,
        R_COST_TURN,
    ),
    (
        lambda s, _c: s["failures"] >= MIN_FAILURES
        and s["failure_density"] >= FAIL_DENSITY_HIGH,
        W_FAIL,
        _reason_fail,
        R_FAIL,
    ),
    (
        lambda s, _c: s["corrections"] >= MIN_CORRECTIONS
        and s["correction_density"] >= CORR_DENSITY_HIGH,
        W_CORR,
        _reason_corr,
        R_CORR,
    ),
    (
        lambda s, _c: s["dup_prompts"] >= MIN_DUP,
        W_DUP,
        _reason_dup,
        R_DUP,
    ),
    (
        lambda s, _c: "cache_ratio" in s and s["cache_ratio"] < CACHE_LOW,
        W_CACHE,
        _reason_cache,
        R_CACHE,
    ),
    (
        lambda s, _c: "edit_reject_rate" in s
        and s["edit_reject_rate"] >= EDIT_REJECT_HIGH,
        W_EDIT,
        _reason_edit,
        R_EDIT,
    ),
]


def evaluate(sig: dict, cost_cut: float) -> tuple[int, list[tuple[str, str]]]:
    """Return (score, [(reason, routing)]) by running the transparent rule table.
    A session is flagged when score > 0; the raw numbers are surfaced too."""
    flags: list[tuple[str, str]] = []
    score = 0
    for applies, weight, reason, route in _RULES:
        if applies(sig, cost_cut):
            score += weight
            flags.append((reason(sig, cost_cut), route))
    return score, flags

# --- gather + window -------------------------------------------------------


def last_activity(sid: str, prompts: dict[str, list[dict]]) -> datetime | None:
    stamps = [parse_ts(r.get("ts")) for r in prompts.get(sid, [])]
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else None


def gather(window_days: int, otel: dict) -> dict[str, dict]:
    """Build per-session signals for project-local sessions active in the window.

    The universe is the sessions seen in the project-scoped prompt/failure logs
    (LOG_DIR). The cost log is home-global (keyed by session_id), so we look up
    cost for those sessions but do NOT pull in sessions that appear only in the
    cost log — those belong to other projects and would otherwise enter the
    cohort context-less and bypass the window."""
    cutoff = datetime.now() - timedelta(days=window_days)
    prompts = read_prompts()
    costs = read_costs()
    failures = read_failures(cutoff)
    if not prompts and not failures:
        return {}
    dup_index = duplicate_index(prompts)
    sessions: dict[str, dict] = {}
    for sid in set(prompts) | set(failures):
        if sid == "unknown":
            continue
        seen = last_activity(sid, prompts)
        # Sessions with prompts are window-checked by their newest prompt ts;
        # failure-only sessions have no ts but read_failures already dropped any
        # whose log predates the cutoff, so they are in-window by construction.
        if seen is not None and seen < cutoff:
            continue
        sessions[sid] = session_signals(
            sid,
            prompts.get(sid, []),
            costs.get(sid, 0.0),
            failures.get(sid, 0),
            dup_index,
            otel.get(sid, {}),
        )
    return sessions


# --- rendering -------------------------------------------------------------


def render_report(
    flagged: list[tuple[dict, int, list[tuple[str, str]]]],
    scored: int,
    window_days: int,
    top: int,
    otel_on: bool,
) -> str:
    otel_note = "OTel metrics" if otel_on else "OTel absent (deferred)"
    lines = [
        f"# Session performance — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Deterministic inefficiency scan over {scored} session(s) active in the "
        f"last {window_days} day(s), from the rig's own logs (cost-log.jsonl, "
        f"post_tool_use_failure.jsonl, the prompt JSONL; {otel_note}). **No LLM "
        "ran.** Run `/analyze-session <session-id>` for a qualitative "
        "what-failed-where diagnosis of any flagged session below.",
        "",
    ]
    if not flagged:
        lines += [
            "## No inefficient sessions flagged",
            "",
            "Every scanned session was below the inefficiency thresholds. Nothing "
            "to route this cycle.",
            "",
        ]
        return "\n".join(lines)
    lines += [
        "## Flagged sessions (worst first)",
        "",
        "| Session | Score | Cost $ | Turns | $/turn | Corr. | Fail | Dup |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for sig, score, _ in flagged:
        lines.append(
            f"| `{sig['session_id']}` | {score} | {sig['cost_usd']} | "
            f"{sig['turns']} | {sig['cost_per_turn']} | {sig['corrections']} | "
            f"{sig['failures']} | {sig['dup_prompts']} |"
        )
    lines += ["", f"## Why + where to route (top {min(top, len(flagged))})", ""]
    for sig, score, reasons in flagged[:top]:
        lines.append(f"### `{sig['session_id']}` (score {score})")
        lines += [f"- {reason} → {route}" for reason, route in reasons]
        lines.append(f"- → `/analyze-session {sig['session_id']}` for diagnosis")
        lines.append("")
    return "\n".join(lines)


# --- telemetry + retention -------------------------------------------------


def log_telemetry(record: dict) -> None:
    try:
        append_jsonl(SESSION_PERF_LOG, record, PERF_LOG_MAX_LINES)
    except OSError:
        pass


def prune_reports(keep: int) -> None:
    """Delete session-perf reports beyond the newest `keep`. Guarded."""
    try:
        reports = sorted(
            SESSION_PERF_DIR.glob("*.md"),
            key=lambda p: (p.stat().st_mtime, p.name),
            reverse=True,
        )
    except OSError:
        return
    for path in reports[keep:]:
        try:
            path.unlink()
        except OSError:
            continue


# --- main ------------------------------------------------------------------


def main() -> None:
    start = time.monotonic()
    payload = read_payload()
    trigger = payload.get("reason") or payload.get("hook_event_name") or "manual"
    window_days = int_env("CC_PERF_WINDOW", DEFAULT_WINDOW_DAYS)
    top = int_env("CC_PERF_TOP", DEFAULT_TOP)
    report_path = ""
    sessions_scored = 0
    sessions_flagged = 0
    error = ""
    try:
        otel = read_otel()  # parsed once; reused for scoring + the report header
        sessions = gather(window_days, otel)
        sessions_scored = len(sessions)
        if not sessions:
            print("session_perf: no session data yet, skipping", file=sys.stderr)
        else:
            costs = [s["cost_usd"] for s in sessions.values()]
            cost_cut = cost_outlier_threshold(costs)
            evaluated = []
            for sig in sessions.values():
                score, reasons = evaluate(sig, cost_cut)
                if score > 0:
                    evaluated.append((sig, score, reasons))
            evaluated.sort(key=lambda t: (-t[1], t[0]["session_id"]))
            sessions_flagged = len(evaluated)
            SESSION_PERF_DIR.mkdir(parents=True, exist_ok=True)
            out = SESSION_PERF_DIR / f"{datetime.now().strftime('%Y%m%d')}.md"
            out.write_text(
                render_report(
                    evaluated, sessions_scored, window_days, top, bool(otel)
                ),
                encoding="utf-8",
            )
            report_path = str(out)
            prune_reports(int_env("CC_PERF_KEEP", DEFAULT_KEEP))
    except Exception as exc:  # never raise from a hook
        error = f"{type(exc).__name__}: {exc}"[:200]
    log_telemetry(
        {
            "ts": datetime.now().isoformat(),
            "trigger": trigger,
            "sessions_scored": sessions_scored,
            "sessions_flagged": sessions_flagged,
            "report_path": report_path,
            "latency_ms": round((time.monotonic() - start) * 1000, 1),
            "error": error,
        }
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
