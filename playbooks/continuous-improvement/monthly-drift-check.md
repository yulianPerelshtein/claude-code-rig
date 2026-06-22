# Monthly drift check

Once a month, run the `core/context-architecture.md` Drift Monitor end-to-end so
instruction layers stay single-sourced and `learnings.md` stays lean.

## Cadence

Monthly, ~20 minutes. Heavier than the weekly retrospective.

## Procedure

1. **Run `/drift-check`.** It greps for directives duplicated across the user
   (`~/.claude/CLAUDE.md`) and project (`<workspace>/*/.claude/CLAUDE.md`)
   layers and reports any phrase appearing in 2+ files. A duplicated rule
   belongs in the **user** layer only — remove it from the project layer(s).
2. **Walk the Drift Monitor triggers** (`core/context-architecture.md`):
   - `wc -l ~/.claude/learnings.md` — if > 120, compress (strip
     `**Context:**`/`**Reason:**` preambles).
   - New `settings.json` hook/skill since last check → audit Layer 1 for
     redundancy.
   - Any project `CLAUDE.md` > 45 lines → push universal rules up to Layer 1.
3. **Re-scan sanitization** — if you've added rig content this month, re-run the
   redaction gate (`.github/scripts/check-redactions.sh`) so nothing
   company/secret-shaped crept in.
4. **Resolve contradictions manually.** `/drift-check` is advisory and never
   edits files; apply the single-home recommendation yourself and commit.

## Outputs

- One source of truth per directive (user vs project layer).
- `learnings.md` ≤ 120 lines.
- A clean redaction scan.

## See also

- `core/context-architecture.md` — the Drift Monitor triggers and the 7-layer model.
- `playbooks/continuous-improvement/quarterly-hooks-profile.md` — the quarterly
  performance pass.
