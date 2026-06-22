---
name: optimize-prompt
description: Review and tighten a skill / agent / command prompt against the rig's checklist
disable-model-invocation: true
argument-hint: "[file]"
allowed-tools: Read, Edit, Glob
---

Optimize the prompt file named in `$ARGUMENTS` (a `SKILL.md`, an agent `.md`, or
a command). If no argument is given, ask which file. Reference:
`playbooks/prompt-optimization/prompt-checklist.md`.

Steps:

1. Read the target file. Identify its type (model-invocable skill, slash-only
   command, subagent, or domain knowledge) — the bar differs per type.
2. Score it against the checklist, calling out concrete issues:
   - **Token budget** — is the body lean? Every line is a recurring cost once
     loaded. Move long reference material to a supporting file.
   - **Trigger clarity** (`description`) — for a model-invocable skill, does the
     first sentence state *when* to use it with real trigger phrases? (Cap:
     1,536 chars across `description` + `when_to_use`.)
   - **Instruction clarity** — imperative, ordered, unambiguous; no narration of
     why/how where a directive will do.
   - **Frontmatter fit** — right `disable-model-invocation` / `argument-hint` /
     `allowed-tools` / `paths` / `model` for the job (see
     `core/skill-frontmatter-reference.md`).
   - **Output-format specificity** — when the skill produces output, is the
     shape pinned (headers, table, verdict line)?
   - **Edge cases** — empty arg, no match, tool failure: are they handled?
3. Present findings as a short list: `issue → suggested rewrite`. Group by
   severity (must-fix / nice).
4. If the user approves, apply the edits with the Edit tool. Do **not** rewrite
   wholesale — preserve working structure; change only what the checklist flags.
5. For a high-leverage skill, recommend measuring the change with the
   `skill-creator` eval loop rather than eyeballing it
   (`playbooks/prompt-optimization/ab-testing-skills.md`).

Keep the prompt's intent intact. This is optimization, not a redesign.
