# Session performance review

The diagnostic half of the continuous-improvement loop. Where `/dream-report`
surfaces recurring *themes* across sessions, this cadence finds the *inefficient
or failed* sessions and routes the fix. It pairs the deterministic Layer-1
scorer (`core/hooks/session/session_perf.py`, item #30) with the on-demand
`/analyze-session` skill.

## Cadence

Fold into the Sunday `weekly-retrospective.md` pass — budget ~10 extra minutes.
Run it more often only if a week was unusually rough.

## Checklist

1. **Read the scan.** The Layer-1 scorer runs at SessionEnd and writes
   `~/.claude/data/session-perf/<date>.md` — flagged sessions ranked worst-first
   with the signals that tripped (cost, cost/turn, tool-failure density,
   correction density, near-duplicate prompts; cache/edit-reject when OTel is
   on). No LLM ran to produce it. If nothing is flagged, you are done.
2. **Diagnose the worst 1–2.** Run `/analyze-session <session-id>` on the top
   flagged session(s) — not all of them. It reads the Layer-1 signals plus the
   session's prompt stream / failures / transcript and grades the session against
   the 5-category rubric (prompt quality · session hygiene · code-review
   effectiveness · tool mastery · context management), with evidence per verdict.
3. **Act on the routing.** `/analyze-session` proposes a routed action per
   finding; apply the ones you agree with:
   - prompt-quality → `/optimize-prompt` on the driving skill/agent/command;
   - repeated prompt → a **skill candidate** (draft now or note for `/dream-report`);
   - recurring failure category → a one-line rule into `~/.claude/learnings.md`
     via the `/dream-report` path (never appended silently; later curated into
     the repo's `learnings/distilled.md`);
   - cache/cost → `domains/context-engineering/native-context-levers.md` +
     `playbooks/observability/otel-insights-review.md`.
4. **Close the loop.** Nothing is auto-applied — you confirm each fix. The payoff
   compounds: each cycle removes a recurring inefficiency rather than just
   measuring it.

## Tuning (environment knobs)

All optional; sane defaults mean you normally set none of these. The Layer-1
scorer (`session_perf.py`) reads them at SessionEnd:

| Env var | Default | Effect |
|---|---|---|
| `CC_PERF_WINDOW` | `7` | Days of history scored (older sessions are skipped). |
| `CC_PERF_TOP` | `5` | Flagged sessions that get the detailed "why + route" section (the table lists all). |
| `CC_PERF_KEEP` | `90` | Session-perf reports retained before the oldest are pruned. |
| `CC_OTEL_METRICS_FILE` | *(unset)* | Path to a JSONL of native OTel metric records; when set, adds cache-hit-ratio + edit-reject-rate signals. OTel is otherwise an install-deferred user action. |
| `CC_PROMPT_LOG` | `1` | `0` logs prompt metadata only (no preview text). Correction density still works from length, but near-duplicate detection degrades. |

## Why this is sampled, not always-on

LLM-as-judge over your own transcripts is biased, noisy, and token-costly. Layer 1
is cheap and deterministic, so it runs every session; Layer 2 (the model
diagnosis) is reserved for the handful of sessions Layer 1 flags. This is the
rig-native, local version of the SOTA eval pattern (deterministic evaluators +
sampled LLM-as-judge + failure-category tracking) — **not** a deployed eval
server, and **not** the AI-Engineering-Coach GUI (whose 5-category taxonomy we
borrowed, not its code).

## See also

- `core/hooks/session/session_perf.py` — the Layer-1 scorer (signals + scoring).
- `core/skills/analyze-session/SKILL.md` — the Layer-2 `/analyze-session` skill.
- `playbooks/continuous-improvement/weekly-retrospective.md` — the cadence this
  folds into.
- `playbooks/observability/otel-insights-review.md` — the quantitative companion
  (OTel trends); pairs with this qualitative pass.
- `playbooks/continuous-improvement/sleep-dream-mode.md` — the *themes* half
  (`/dream-report`), complementary to this *inefficiency* half.
