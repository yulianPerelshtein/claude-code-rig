---
name: health
description: Run a full environment health check
disable-model-invocation: true
---

Run these checks and report a clean/warning/error status for each:

1. `git status` — working tree clean?
2. `docker ps` — which containers are running?
3. `python3 --version` and `uv --version`
4. `ruff --version`
5. Does `~/.claude/learnings.md` exist? Show line count.
6. Does `~/.claude/settings.json` exist and contain hooks?
7. `uv run ruff check .` — any unfixable lint errors?
