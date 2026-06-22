# Git conventions

## Branch preflight

Before creating any branch:

```bash
git fetch origin
git log --oneline origin/main -10     # what's actually on main?
```

Spot-check key files against origin. Branching from a stale local `main` can
silently duplicate already-merged work — an entire phase can be redone before
you notice.

## Verify base before extracting a feature branch

Before proposing to extract a feature into its own branch, verify the target
branch's current HEAD and history (`git log origin/main`). Don't assume what's
"missing" — confirm it. Work you think is unshipped may already be on main via
another path.

## Staging discipline

- Never `git add .` / `git add -A` on a repo that contains a `.claude/` dir —
  stage explicit paths so agent-local files never enter a commit.
