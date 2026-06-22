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

Under `--routine-mode`, ask no interactive questions — just print the brief.
