# Global Architecture & Workflow Context (base)

This is the always-loaded Layer-1 core: universal rules only. Domain knowledge
activates on demand via `paths:`-scoped skills (see `context-budget-policy.md`).

Sibling core files (imported so each stays single-purpose and auditable):

- @safety-rules.md — destructive-command and filesystem guardrails.
- @default-workflows.md — how tasks are executed; TodoWrite usage.
- @github-content-rules.md — PR/issue body discipline.
- @reasoning-preferences.md — effort-aware tone and output preferences.
- @context-budget-policy.md — what loads when; native context management.
- @context-architecture.md — the 7-layer hierarchy + drift monitor.

## System Environment: WSL2 Ubuntu

- ALL commands run in native Linux/Ubuntu.
- NEVER read or write the Windows filesystem mount (the `/mnt/<drive>/` path).
  Keep all work on the Linux filesystem.

## Multi-checkout WSL ↔ Windows sync

When the same repository is checked out on both WSL and Windows:

- NEVER manually copy files between the two checkouts.
- Treat them as two independent git checkouts of the same remote.
- Always push from one side, then `git fetch && git checkout <branch>` on the
  other.
- If the other working tree is dirty (manually-copied files sitting as
  untracked/modified), clean it properly before switching branches:

  ```powershell
  git stash                                  # save modified tracked files
  git clean -fd -e "*.<asset-ext>" -e "<local-config>"  # remove conflicting untracked
  git checkout <branch>
  git lfs pull                               # restore LFS assets if needed
  ```

## Execution

- Check distilled learnings (and native `MEMORY.md`) before retrying any
  failed operation.

## Agent behaviour

- Be concise. No compliments or filler (see @reasoning-preferences.md).
- NEVER add `Co-Authored-By:` trailers to commit messages.
- NEVER add authorship or copyright headers to new files (no "Created by …",
  no `Copyright (c) … <COMPANY>`, no date stamps). Follow the existing project
  convention or omit entirely.

## Worktrees

- Complex refactors run in an isolated worktree (the `refactor` agent).
- Worktree location: `~/.claude-worktrees/<project>/<branch>`.

## Plans

- Save plans at `<project-root>/.claude/plans/<kebab-case-name>.md` (gitignored).
- When entering plan mode, set the plan file path immediately.
