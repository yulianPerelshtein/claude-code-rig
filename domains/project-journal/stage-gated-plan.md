# The stage-gated plan

A plan that survives a multi-day project has a fixed spine: a reader (including
future-you after a context clear) can open it cold and know what's done, what's
next, and what was already decided. It is the source of truth for resuming.

## Structure

```text
1. Context        — what this is, the deliverables, the constraints.
2. Scope          — files/areas in play; what's explicitly out of scope.
3. Stages         — each bounded by an explicit checkpoint (below).
4. Risk register  — known risks, severity, and the mitigation for each.
5. Resumption     — how to pick up cleanly after a context clear (below).
```

## Stages end at checkpoints, not at "done"

Each stage states its goal, its tasks, its deliverable, and a **checkpoint**: a
point where work pauses for review before the next stage starts. The checkpoint
is the unit of trust — it's where a human confirms direction before more code is
built on top of it. Build shared scaffolding *to a real caller*, not
speculatively — the YAGNI ladder and "duplication is cheaper than the wrong
abstraction" apply at stage boundaries too (`domains/software-design/clean-code.md`).

A risk register entry is one line: `<risk> | <severity> | <mitigation>`. Its
value is that a mitigation is decided *before* the risk fires, not improvised
under pressure. Mark entries resolved as stages close them.

## Resumption protocol

The plan's most important section, because context clears are routine. State the
exact steps to rebuild context:

```text
1. Read this plan end-to-end.
2. Read the running design notes (thought-process).
3. `git log --oneline` — the last commit identifies the current stage (this
   leans on a commit-per-task habit; if you batch commits, read the plan's task
   checkboxes instead).
4. Resume at the next un-committed task in that stage.
5. Do not silently re-decide anything in the decision log; surface it first.
```

Step 5 is what keeps a resumed session from quietly contradicting a locked
decision — the most common failure mode after a clear.

## Close with the synthesis-report shape

When the work ships, the plan and decision log distill into a report (or a PR
description). A repeatable shape:

```text
Approach → Decisions → Empirical findings → Alternatives considered → Limitations
```

The plan and decision log are the raw material; the report is the polished
synthesis. Keeping the journal well-formed during the work is what makes the
final writeup a distillation rather than an archaeology project.
