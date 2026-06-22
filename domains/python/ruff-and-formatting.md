# ruff: lint vs format, and on-save hazards

## Run lint, not format, during a task

```bash
ruff check --fix <file>   # autofixes only — safe to run anytime
```

- NEVER run `ruff format` on an existing file mid-task. It rewrites whitespace
  style and creates PR noise. Use it only as an explicit one-time `style:`
  normalization commit, agreed with the user, separate from logic changes.

## An on-save formatter will fight you

If an editor/hook runs a formatter after every write, it will:

1. **Collapse** any multi-line expression that fits the line-length limit.
2. **Strip** trailing whitespace from blank lines (PR noise; see
   `domains/devops/pr-cleanliness.md`).
3. **Rewrite** chained `with a, b, c:` into the parenthesized form — which is
   newer-Python syntax and can break older-Python CI (`SyntaxError` on collect).
4. **Remove** an import added in one edit before the edit that uses it lands
   (F401). Add the *usage* first, then the import — or write the whole file at
   once.

## Defenses

- **Magic trailing comma** after the last element keeps a multi-line
  dict/list/call multi-line permanently.
- For files that must stay older-Python-compatible, keep chained `with`
  comma-form and grep for the parenthesized form before committing.
- Pin `target-version` in `pyproject.toml` if it isn't gitignored.

## Line length

Check line length on **new** strings too — docstrings and comments are not
exempt. CI catches an over-length docstring that a local `--no-verify` bypasses.
