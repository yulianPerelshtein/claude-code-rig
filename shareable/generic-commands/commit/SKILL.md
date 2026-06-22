---
name: commit
description: Create a conventional commit with smart staging
disable-model-invocation: true
argument-hint: "[type]"
---

1. Run `git status` and `git diff --stat`
2. Identify changed files relevant to the task (skip lock files, build artifacts)
3. Stage only relevant files with `git add <specific files>`
4. Write a conventional commit message: `<type>(<scope>): <description>`
   Types: feat, fix, refactor, test, docs, chore, perf
5. Run `git commit -m "..."` — do NOT use --no-verify
6. Show the commit hash and summary

$ARGUMENTS can override the commit type if provided.
