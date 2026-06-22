# Python tooling conventions (flake8, 79-char)

Drop-in conventions for a project that lints with flake8 at the classic 79-char
limit.

## Rules

- **Line length 79** applies to *everything*, including docstrings and comments
  — they are not exempt. Check new strings before committing; CI catches what a
  local `--no-verify` bypasses.
- Run the linter after every edit; fix warnings as you go, don't batch them.
- Keep imports at module top unless an optional/platform dependency requires a
  function-scoped import (then add `# noqa` only where justified — e.g. `E402`
  after a required `load_dotenv()`).

## pyproject / setup.cfg starting point

```ini
[flake8]
max-line-length = 79
extend-ignore = E203, W503   # black/ruff-compatible defaults
```

For projects on `ruff`, mirror with `line-length = 79` and prefer
`ruff check --fix` (never `ruff format` mid-task — see
`domains/python/ruff-and-formatting.md`).
