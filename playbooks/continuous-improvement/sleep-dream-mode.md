# Sleep / dream mode

The runtime half of the continuous-improvement loop (items #3 + #12). It
consolidates recent sessions into a review-ready report **without spending
tokens during normal work** — all the model-side synthesis happens later, when
you run `/dream-report`.

## The two pieces

1. **`core/hooks/session/session_end.py`** — on every SessionEnd, writes a
   per-session summary (metrics + first prompts + last results) to
   `~/.claude/data/session-summaries/<date>-<session-id>.md`.
2. **`core/hooks/session/dream_loop.py`** — runs right after (also wired on
   SessionEnd; can also be a cron/systemd job). Reads the recent summaries,
   surfaces recurring themes deterministically, and writes
   `~/.claude/data/dream-reports/<date>.md`. It does **no** model inference.

The model-side synthesis is the `/dream-report` skill, run weekly.

## Configuration

| Env var | Default | Effect |
|---|---|---|
| `CC_SESSION_SUMMARY` | `1` (on) | Set `0`/`false`/`off` to **disable** writing per-session summaries. The loop then has nothing to consolidate — use this to opt out of on-disk prompt/result capture entirely. |
| `CC_DREAM_WINDOW` | `7` | How many recent session summaries to consolidate per report. |
| `CC_SUMMARY_KEEP` | `500` | Retention cap — after each report, summary files beyond the newest N are pruned (bounds disk + the per-SessionEnd scan). |

Both data dirs live under `~/.claude/data/` so they inherit the
`SECURITY_REVIEW.md §6` exclusion (never packaged, never committed). The summary
files hold the first prompts + last results of each session as plain text; they
never leave the machine, but if you don't want that captured at all, set
`CC_SESSION_SUMMARY=0`.

## Contract (why it's safe to wire globally)

- **No-op on a clean machine.** If `~/.claude/data/session-summaries/` is missing
  or empty, `dream_loop.py` exits 0 with the single stderr line
  `dream_loop: no session summaries yet, skipping`. The `installer-dryrun`
  workflow asserts this.
- **Never raises.** Any error is caught, recorded in the telemetry line, and the
  hook still exits 0 — a broken dream loop can never block a session from ending.
- **Observable.** Every invocation appends one JSONL line to
  `~/.claude/data/dream-loop.log`:
  `{ts, trigger, summaries_read, patterns_found, report_path, latency_ms, error}`.

## Review cadence

Weekly. Run `/dream-report`, triage each candidate theme (ACCEPT / DISCARD /
MODIFY), and let ACCEPTed entries flow into `~/.claude/learnings.md` with a
`# from dream-report <date>` provenance line. See
`playbooks/continuous-improvement/weekly-retrospective.md`.

## What it does NOT do

- No real-time interruption — it never "wakes up" mid-conversation.
- No auto-apply — you review every candidate before anything is written to
  `learnings.md`.
- No in-session token cost — it runs from the SessionEnd event (or cron), not
  during a conversation.
