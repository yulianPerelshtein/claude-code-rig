# Validators

Standalone, CLI-invoked validators for plan/spec documents. They are **not**
wired into `hooks.json` — they are meant to be called explicitly by
plan-execution and spec-authoring skills/commands (e.g. a "validate the plan"
step that runs `uv run python ...` and gates on the exit code), and they read
the hook payload (notably `cwd`) from stdin.

These are standalone CLIs; the skills/commands that invoke them are wired
by later skills; they are intentionally standalone, not dead code.

## Tools

- **`validate_file_contains.py`** — fails (exit 2) if the most recently modified
  `--extension` file in `--directory` is missing any required `--contains`
  string. Exit 0 when all present.
- **`validate_no_placeholders.py`** — fails (exit 2) if that file still contains
  placeholder/skeleton patterns (`--not-contains`, or a sensible default set:
  `[To be detailed`, `TBD`, `[INSERT`, …). Exit 0 when clean.
- **`validate_tdd_tasks.py`** — fails (exit 2) if the file has no TDD/testing
  task, or if the first TDD task appears *after* the first implementation task
  (`--contains-before TDD_PATTERN IMPL_PATTERN`). Enforces tests-first ordering.

All three exit 0 (non-blocking) when the target directory or file does not
exist, so they are safe to call speculatively.

## Example

```bash
uv run python core/hooks/validators/validate_file_contains.py \
    --directory specs --extension .md \
    --contains '## Task Description' --contains '## Objective'
```
