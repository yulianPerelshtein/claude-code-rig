# Prompt library

A small set of vetted prompt shapes for the rig's most common operations. Start
from one of these rather than from a blank file; they already pass the
`prompt-checklist.md`. These are *shapes*, not copy-paste finals — fill the
bracketed slots.

## Command-skill (slot-in verb, no model invocation)

```yaml
---
name: <verb>
description: <one line: what it does>
disable-model-invocation: true
argument-hint: "[<arg>]"
allowed-tools: Bash(<scoped *>)
---

## Context
- <label>: !`<bounded read command>`

## Task
<imperative, ordered steps>.
$ARGUMENTS <how the argument is used>.
```

When to use: a deterministic action you trigger with `/` (commit, deploy,
health). The `` !`cmd` `` block seeds it with live state.

## Model-invocable knowledge skill (auto-loads on description)

```yaml
---
name: <topic>
description: >-
  <what> — <when to use it, with trigger phrases>. Surfaces when <condition>.
paths:
  - "<glob the knowledge applies to>"
---

# <topic>
<the fact/rule, tight. Link a supporting file for depth.>
```

When to use: domain knowledge that should appear when touching matching files.
Omit `paths` for tool/reference topics that shouldn't reload on every edit.

## Read-only investigator (forked)

```yaml
---
name: <investigate-x>
description: <investigate X and report>
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob
---

Investigate $ARGUMENTS. Read the relevant files, trace the flow, and return a
tight summary: entry points, key files (path:line), control/data flow, and
surprises. Do NOT modify files.
```

When to use: investigation that would otherwise flood the main context. Returns
a summary; writes nothing. See `playbooks/skill-techniques/forked-investigation.md`.

## Subagent (delegated task with its own memory)

```yaml
---
name: <role>
description: Use when <condition>.
model: <haiku|sonnet|opus>
tools:
  - <minimal set>
memory: user        # only if cross-session pattern memory helps
---

You are a <role>. <constraints>. <ordered procedure>. Report: <pinned output shape>.
```

When to use: a reusable specialist (reviewer, test-writer, pr-writer) invoked via
the Task tool or a `context: fork` skill.

## Notes

- Keep bodies lean — every loaded line is a recurring token cost.
- Pin the **output shape** in any skill that produces output.
- Measure high-leverage changes (`ab-testing-skills.md`), don't eyeball them.

## See also

- `core/skill-frontmatter-reference.md`, `playbooks/prompt-optimization/prompt-checklist.md`.
