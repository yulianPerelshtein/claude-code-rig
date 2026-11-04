---
name: dream-report
description: Review the latest dream-loop consolidation and apply candidate learnings
disable-model-invocation: true
argument-hint: "[date]"
allowed-tools: Read, Glob
---

Review the latest dream-loop consolidation and turn its recurring facts into
learnings. The report was produced deterministically by `dream_loop.py`: it lists
the facts that recur across sessions, read from their transcripts (tool-failure
classes, files edited, skills and subagents used). It does **not** synthesize —
synthesis is your job.

Steps:

1. Locate the report. If `$ARGUMENTS` names a date (`YYYYMMDD`), read
   `~/.claude/data/dream-reports/$ARGUMENTS.md`. Otherwise Glob
   `~/.claude/data/dream-reports/*.md`, pick the most recent by filename, and
   Read it. If none exist, say so — dream reports are written at SessionEnd once
   session summaries exist — and stop.
2. For context, Read the **session summaries** it drew from
   (`~/.claude/data/session-summaries/`).
3. For each recurring fact, propose a **concrete, one-line operational rule**
   suitable for `learnings/distilled.md` — or mark it DISCARD if it is expected
   (a generic `Exit code 1`), a one-off, or already covered by CLAUDE.md / an
   existing learning. What each kind usually points to:
   - a tool failure: a habit to change (read before Edit) or a guardrail the
     model keeps walking into;
   - a file edited in many sessions: a note or tool worth a manifest, a skill,
     or a split;
   - a skill or subagent used in many sessions: check its cost in the
     session-performance report before adding a sibling.
4. Present each as `ACCEPT` / `DISCARD` / `MODIFY` with the proposed rule text.
   Ask the user to confirm before writing anything.
5. For each ACCEPTed item, append an `## Accepted for distilled.md` section to
   **the dream report you just read** (`~/.claude/data/dream-reports/<date>.md`),
   one entry per item in the format from `core/context-architecture.md`. Do NOT
   write a separate learnings store: `/weekly-retro` already globs these reports
   and is the gate that promotes them into `learnings/distilled.md` by draft PR.
   A machine-local staging file used to sit between the two and silently went
   three weeks unmentioned, holding seven learnings that never reached the repo.
6. Confirm: "N entries queued for /weekly-retro in dream-report <date>."

Do not auto-apply — the user reviews every candidate. This skill is the
human-in-the-loop half of the continuous-improvement loop; see
`playbooks/continuous-improvement/sleep-dream-mode.md`.
