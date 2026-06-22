---
name: dream-report
description: Review the latest dream-loop consolidation and apply candidate learnings
disable-model-invocation: true
argument-hint: "[date]"
allowed-tools: Read, Glob
---

Review the latest dream-loop consolidation and turn its candidate themes into
learnings. The report was produced deterministically by `dream_loop.py` (it
surfaces recurring themes; it does **not** synthesize) — synthesis is your job.

Steps:

1. Locate the report. If `$ARGUMENTS` names a date (`YYYYMMDD`), read
   `~/.claude/data/dream-reports/$ARGUMENTS.md`. Otherwise Glob
   `~/.claude/data/dream-reports/*.md`, pick the most recent by filename, and
   Read it. If none exist, say so — dream reports are written at SessionEnd once
   session summaries exist — and stop.
2. For context, Read the **session summaries** it drew from
   (`~/.claude/data/session-summaries/`).
3. For each candidate theme, propose a **concrete, one-line operational rule**
   suitable for `~/.claude/learnings.md` — or mark it DISCARD if it is a one-off
   or already covered by CLAUDE.md / an existing learning.
4. Present each as `ACCEPT` / `DISCARD` / `MODIFY` with the proposed rule text.
   Ask the user to confirm before writing anything.
5. For each ACCEPTed item, append to `~/.claude/learnings.md` using the wrap-up
   entry format, followed by a provenance line: `# from dream-report <date>`.
6. Confirm: "Learnings updated: N new entries added from dream-report <date>."

Do not auto-apply — the user reviews every candidate. This skill is the
human-in-the-loop half of the continuous-improvement loop; see
`playbooks/continuous-improvement/sleep-dream-mode.md`.
