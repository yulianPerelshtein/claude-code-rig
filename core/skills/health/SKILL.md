---
name: health
description: Run a full environment health check
disable-model-invocation: true
allowed-tools: Bash(git status *) Bash(docker ps *) Bash(python3 *) Bash(uv *) Bash(ruff *) Bash(echo *)
---

## Environment probes

```!
git status --short
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "(docker not available)"
python3 --version
uv --version
ruff --version
```

## Task

From the probe output above, report a clean / warning / error status for each:

1. Working tree clean? (git status)
2. Which containers are running? (docker ps)
3. Python + uv present and a sane version?
4. ruff present?
5. Does `~/.claude/learnings.md` exist? Read it and note its line count.
6. Does `~/.claude/settings.json` exist and reference hooks? Check it.
7. Run `uv run ruff check .` now and report any **unfixable** lint errors (this
   one is run live, not pre-injected, because it can be slow).

Summarize with an overall PASS / WARN / FAIL.
