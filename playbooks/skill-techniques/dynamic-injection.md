# Dynamic context injection (`` !`command` ``)

Inject a shell command's **output** into a skill body before the model sees it,
so the skill starts with live facts instead of spending a turn fetching them.

Reference: `core/skill-frontmatter-reference.md` (the `` !`<command>` `` row +
`allowed-tools`).

## The shape

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---
## Pull request context

- Changed files: !`gh pr diff --name-only`
- Diff stat: !`gh pr diff --stat`
- PR title/body: !`gh pr view`

## Your task

Summarize this pull request for a reviewer …
```

Each `` !`<command>` `` line is executed and replaced with its stdout **before**
the model reads the body. The model then reasons over real diff/log/status text,
not an instruction to go and run it. This is preprocessing — the model only sees
the final, rendered prompt. (Note the bounded forms — `--name-only`, `--stat` —
per Rule 3 below; inject the full `gh pr diff` only when the diff is small.)

For several commands at once, use the fenced form opened with ` ```! `:

````markdown
## Environment
```!
python3 --version
uv --version
git status --short
```
````

## When it pays off

- The skill's first action would otherwise be a deterministic fetch
  (`git status`, `git diff --stat`, `gh pr view`).
- The fetched context is small and bounded.
- You want the model to *reason*, not to *orchestrate tool calls*.

## Rules

1. **`allowed-tools` must permit the command.** `` !`gh pr diff` `` needs
   `allowed-tools: Bash(gh *)` (or broader). A too-tight scope blocks it.
2. **Syntax is exact.** `!` is recognized only at the **start of a line or after
   whitespace** — `` KEY=!`cmd` `` is left literal. Substitution runs **once**;
   injected output is not re-scanned for further placeholders.
3. **Bound the output.** Use `--stat`, `-n 5`, `--name-only` — injected text is
   verbatim and counts against context. A 10k-line diff injected raw is a
   self-inflicted token bomb.
4. **Never inject secrets.** No `` !`cat .env` ``, no
   `` !`aws sts get-session-token` ``. The output lands in the prompt.
5. **Assume it can fail.** If the command errors (not a repo, no PR), the body
   still has to make sense — write the task so an empty/failed injection
   degrades gracefully.
6. Policy can disable it: `disableSkillShellExecution: true` replaces each
   command with `[shell command execution disabled by policy]`.

## Retrofit candidates in this rig

- `core/skills/commit/SKILL.md` — inject `` !`git status --short` `` +
  `` !`git diff --stat` `` so staging analysis starts from the real working
  tree. (Applied.)
- `core/skills/health/SKILL.md` — inject the status/branch/version probes via a
  ` ```! ` block. (Applied.)
- `core/skills/review-pr/SKILL.md` — inject `` !`gh pr diff --name-only` `` so
  every reviewer agent starts from the changed-files list. (Applied.)

## See also

- `playbooks/skill-techniques/forked-investigation.md` — pair `` !`cmd` ``
  injection with `context: fork` for read-only summarizers.
- `playbooks/skill-techniques/skill-arguments.md` — feed `$ARGUMENTS` into the
  injected command (e.g. `` !`gh pr diff $ARGUMENTS` ``).
