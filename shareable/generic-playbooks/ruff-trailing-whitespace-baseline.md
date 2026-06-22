# Ruff trailing-whitespace baseline

Keep every commit formatting-clean **as written**. Mixing whitespace churn with
logic changes produces noisy, hard-to-review diffs and merge conflicts.

## Rules

- Before committing, verify `git diff <base> -- <file>` shows **zero**
  blank-line whitespace noise. Never mix trailing-whitespace removal with a
  logic change.
- Trailing-whitespace blank lines create diff noise in **both** directions:
  stripping shows a removed-blank line; restoring shows an added-blank line.
  The fix is the baseline technique below, not ad-hoc edits.
- An auto-formatter on save will collapse any multi-line expression that fits
  the line-length limit and may rewrite `with a, b:` to a newer-syntax form
  (which can break older-Python CI). Preserve intentional multi-line style with
  **magic trailing commas**, or disable format-on-save for the file.

## Baseline technique (strip noise without a rebase)

When a file already carries trailing-whitespace blank lines and you only want to
land a semantic change cleanly:

1. `git show <base>:<file> > /tmp/baseline` — start from the clean upstream copy.
2. Apply only the semantic delta (from `git diff -w <base>..HEAD`) to the
   baseline via a small script or targeted edits.
3. Write it back.

Result: upstream's formatting plus only your real changes — no whitespace noise.

## Lint, don't reformat

Use `ruff check --fix` (autofixes only) during a task. Avoid `ruff format` on an
existing file mid-change — it rewrites whitespace style and creates PR noise.
Reserve any whole-file reformat for a separate, explicit `style:` commit.
