---
name: weekly-retro
description: Package accepted learning candidates from the week into a DRAFT PR against distilled.md (clustering is /dream-report's job).
argument-hint: "--target <repo> [--routine-mode] [--outcome draft-pr]"
allowed-tools: Bash, Read, Grep, Edit
---

# /weekly-retro  (outcome: draft-pr)

Operate on `--target` (default = the rig repo). Turn **already-clustered**
learning candidates into a small, reviewable draft PR. The clustering /
synthesis of raw session signal is **`/dream-report`'s job** (fed by the
deterministic `dream_loop.py` consolidation) — this routine only *packages*
accepted candidates, so it does not duplicate that analysis.

1. Read the latest `~/.claude/data/dream-reports/*.md` (the consolidation
   scaffold) and the candidate learnings `/dream-report` has already promoted
   into `~/.claude/learnings.md`. If no dream report exists yet, run
   `/dream-report` first (or note that there is nothing to package and stop).
2. Select 1–5 accepted candidates and render them in the existing
   `learnings/distilled.md` format (`## YYYY-MM-DD CATEGORY-NAME` + 1–3 lines,
   operational rule only).
3. Apply edits **only** inside `<target>/learnings/distilled.md` (or the
   target's configured learnings path). Touch nothing else.
4. Under `--routine-mode`, write the proposed diff into the worktree and **stop**
   — do **not** push or open the PR yourself. The runner
   (`runner/cli` → `runner/gitops.open_draft_pr`) commits the worktree, creates
   `routine/weekly-retro-<date>`, and runs `gh pr create --draft`.

Never merge. Never push to a default branch. Draft PR only — the human reviewer
is the single gate on anything that mutates tracked knowledge. See
`playbooks/continuous-improvement/weekly-retrospective.md` for the cadence.
