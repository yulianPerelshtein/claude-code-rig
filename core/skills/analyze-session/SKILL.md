---
name: analyze-session
description: Diagnose a flagged session against the 5-category rubric and route each fix (Layer 2 of #30). Use on demand for a session the deterministic scorer flagged, or one you know went badly.
disable-model-invocation: true
argument-hint: "[session-id]"
allowed-tools: Read, Glob, Bash
---

Diagnose **one** session's inefficiency and route every finding to a concrete
fix. This is Layer 2 of the session performance analyzer (item #30): the
deterministic Layer-1 scorer (`core/hooks/session/session_perf.py`) already
flagged *which* sessions and *which signals* tripped; your job is the
qualitative **what-failed-where + fix**, evidence-gated and human-in-the-loop.

This is **sampled and on-demand** — never run it over every session. LLM-as-judge
on one's own transcripts is biased, noisy, and token-costly; run it on a flagged
or known-bad session, then act on the routing.

## Steps

1. **Pick the session.**
   - If `$ARGUMENTS` names a session id, use it.
   - Otherwise Glob `~/.claude/data/session-perf/*.md`, Read the most recent
     report, and take the worst-scored flagged session. If no report exists, say
     so (it is written at SessionEnd once there is session data) and stop.
2. **Load the Layer-1 evidence** for that session from the report: its score and
   the specific signals that tripped (cost, cost/turn, failure density,
   correction density, near-duplicates, and — if present — cache ratio / edit
   reject rate). These are the numeric anchors; do not re-derive them by hand.
3. **Gather the qualitative record** (read-only):
   - the prompt stream — `~/.claude/data/logs/user_prompt_submit.jsonl`, filtered
     to this `session_id` (turn / ts / preview);
   - the failures — `~/.claude/data/logs/<session-id>/post_tool_use_failure.jsonl`;
   - the transcript if you can locate it (`~/.claude/projects/**` or the session
     summary under `~/.claude/data/session-summaries/`). Keep reads bounded.
4. **Diagnose against the 5-category rubric** (borrowed from the AI-Engineering
   Coach taxonomy — the rubric, not its GUI). For each category, give a one-line
   verdict + the **evidence** (a turn number, a failure, a number from Layer 1).
   Skip a category honestly if there is no evidence either way.

   | Category | What you are looking for |
   |---|---|
   | **Prompt quality** | Vague/under-specified asks; missing acceptance criteria; the correction cluster that followed a weak prompt. |
   | **Session hygiene** | Scope creep, no checkpoint/`/save-state`, marathon sessions that should have been split, stale context carried forward. |
   | **Code-review effectiveness** | Edits landed without review/tests; rejected edits (high edit-reject rate); review caught nothing because none ran. |
   | **Tool mastery** | Failure/retry density: blind retries, wrong tool for the job, Edit-string misses, Bash that timed out. |
   | **Context management** | Cache-busting (low cache ratio), bloated context, cost/turn outliers, re-reading the same files. |

5. **Route each finding** (the point — close the loop, not write a report):
   - prompt-quality issue → `/optimize-prompt` on the offending skill / agent /
     command that drove the session;
   - a prompt you keep re-issuing (near-duplicate signal) → **skill candidate**:
     draft it (`core/skill-frontmatter-reference.md`) or note it for `/dream-report`;
   - a **recurring failure category** → propose a one-line operational rule for
     `~/.claude/learnings.md`, applied via the `/dream-report` human-in-the-loop
     path (do not append silently); it is later curated into the repo's
     `learnings/distilled.md`.
   - cache / cost finding → `domains/context-engineering/native-context-levers.md` +
     `playbooks/observability/otel-insights-review.md`.
6. **Present, then ask.** Output the rubric verdicts + the routed actions as a
   short checklist. Apply nothing without confirmation; this skill diagnoses and
   proposes — the user decides what to fix.

## Output shape

```text
## Session <id> — diagnosis (Layer-1 score N)

| Category | Verdict | Evidence |
|---|---|---|
| Prompt quality | ... | turn 4–7 corrections after a vague ask |
| ... | ... | ... |

## Routed actions
- [ ] /optimize-prompt <file> — <why>
- [ ] skill candidate: <name> — <the repeated prompt>
- [ ] ~/.claude/learnings.md (via /dream-report): <one-line rule>
```

See `playbooks/continuous-improvement/session-performance-review.md` for the
weekly cadence this fits into, and `core/hooks/session/session_perf.py` for how
the Layer-1 signals are computed.
