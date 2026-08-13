---
name: begin-work
description: Daily startup brief — fetch, branch status, today's plan, light drift, yesterday's loose ends (report-only).
argument-hint: "--target <repo>"
allowed-tools: Bash, Read, Grep
---

# /begin-work  (outcome: report-only — never writes)

Operate on `--target` (default = current working directory). Print a concise
startup brief. **Report only: make no commits, no writes, no pushes.**

1. `git -C <target> fetch --quiet`, then show the current branch and
   ahead/behind vs its upstream (`git -C <target> status -sb`).
2. Surface today's plan + open TODOs: read `<target>/.claude/plans/*.md` (if
   present), `~/.claude/MEMORY.md` (if present), and the "loose ends" / "Last
   results" section of the most recent
   `~/.claude/data/session-summaries/*.md`.
3. Light drift check (summary only): note whether
   `git -C <target> status --porcelain` is dirty, and how many commits the
   branch is ahead/behind.
4. List yesterday's loose ends as a short checklist.
5. **Rig health.** Read `~/.claude/data/self-check/latest.json`. If `ok` is
   false, lead the brief with the failing check names and point at the dated
   report beside it; if the file is missing or its `date` is more than 10 days
   old, say the self-check has not run rather than reporting health. Say nothing
   when it is green — a passing check is not news.

Under `--routine-mode`, ask no interactive questions — just print the brief.

> Step 5 is the feedback loop, not decoration. Every failure the `self-check`
> routine exists to catch was a guarantee that broke *silently*; a report only
> written to disk would repeat that. This is the point where it reaches a human.
