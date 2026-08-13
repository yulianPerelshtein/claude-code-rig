---
name: commit
description: Create a conventional commit with smart staging
disable-model-invocation: true
argument-hint: "[type]"
allowed-tools: Bash(git status *) Bash(git diff *) Bash(git add *) Bash(git commit *)
---

## Working tree

- Status: !`git status --short`
- Staged/unstaged stat: !`git diff --stat HEAD`

## Task

Create a conventional commit from the working tree above.

1. From the status/stat already shown, identify changed files relevant to the
   task (skip lock files, build artifacts).
2. Stage only relevant files with `git add <specific files>`.
3. Write a conventional commit message: `<type>(<scope>): <description>`.
   Types: feat, fix, refactor, test, docs, chore, perf. **One line only — never
   write a body.** If the change needs explaining, split it into smaller commits
   that each stand alone rather than adding prose. Rationale belongs in the PR
   description or a project note, where it can be revised; a commit body is
   frozen into `git log`. No agent-internals or "Generated with …" trailers (see
   `core/authored-content-rules.md`).
4. Run `git commit -m "..."` — do NOT use `--no-verify`.
5. Show the commit hash and summary.

`$ARGUMENTS` can override the commit type if provided.
