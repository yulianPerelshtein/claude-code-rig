# Weekly retrospective

A light, every-Sunday loop that turns the week's sessions into next week's
improvements. The runtime half (auto-consolidation) is `dream_loop.py`; this
playbook is the human review cadence around it.

## Cadence

Run once a week (Sunday works well). Budget ~15 minutes.

## Checklist

1. **Health snapshot** — run the `/health` skill; confirm the environment is
   clean (tree, containers, tooling, no unfixable lint).
2. **Consolidate** — run `/dream-report`. It reads the week's session summaries
   (`~/.claude/data/session-summaries/`) and the latest dream report, and
   proposes candidate learnings. ACCEPT / DISCARD / MODIFY each; ACCEPTed
   entries land in `~/.claude/learnings.md` with a `# from dream-report <date>`
   provenance line.
3. **Prune** — if `wc -l ~/.claude/learnings.md` > 120, strip verbose
   `**Context:**`/`**Reason:**` annotations (per `core/context-architecture.md`
   Drift Monitor).
4. **Review flagged sessions** — read the latest session-perf scan
   (`~/.claude/data/session-perf/<date>.md`) and run `/analyze-session` on the
   worst 1–2, applying the routed fixes. Full steps:
   `playbooks/continuous-improvement/session-performance-review.md`.
5. **Spot a skill candidate** — if you pasted the same multi-step instruction
   3+ times this week, it's a skill. Draft it (`core/skill-frontmatter-reference.md`).

## Outputs

- Updated `~/.claude/learnings.md` (a few high-signal entries, not a dump).
- A mental note of any skill/playbook to author.

## See also

- `playbooks/continuous-improvement/session-performance-review.md` — the
  diagnostic pass (`/analyze-session`) that step 4 above runs.
- `playbooks/continuous-improvement/sleep-dream-mode.md` — the dream-loop config
  and how the summaries it reads are produced.
- `playbooks/continuous-improvement/monthly-drift-check.md` — the heavier
  monthly pass.
