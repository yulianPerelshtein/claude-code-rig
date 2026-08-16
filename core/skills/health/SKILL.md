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

**Scope.** This covers the *working environment* of the repo you are in. It does
not check the rig's own health — that is `self-check` (Layer 1 loads, the
deployed guardrail blocks, timers exist, CI pins) and `install/validate.sh`
(install integrity). Don't duplicate either; point at them instead.

From the probe output above, report a clean / warning / error status for each:

1. Working tree clean? (git status)
2. Which containers are running? (docker ps)
3. Python + uv present and a sane version?
4. ruff present?
5. Run `uv run ruff check .` now and report any **unfixable** lint errors (this
   one is run live, not pre-injected, because it can be slow). If the repo has
   no Python, say so rather than reporting a clean pass.
6. Rig health, by reading the verdict rather than re-deriving it: print
   `ok` and `failed` from `~/.claude/data/self-check/latest.json`. If the file is
   missing or older than ~10 days, report that the self-check has not run — do
   not report healthy.

Summarize with an overall PASS / WARN / FAIL.

> Removed from this checklist: "does `~/.claude/settings.json` reference hooks?"
> On a plugin install it never does — hooks ship from the plugin cache via
> `${CLAUDE_PLUGIN_ROOT}`, and `settings.json` carries no `hooks` block. The
> probe reported a permanent false warning. Also removed: the
> `~/.claude/learnings.md` line count — that machine-local store was retired
> entirely; its entries now live in `learnings/distilled.md`.
