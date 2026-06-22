# PR cleanliness

A diff should contain only the lines the change actually needs. The dominant
source of noise is **trailing-whitespace blank lines** in existing files.

## The problem is bidirectional

- A formatter strips a trailing-whitespace blank → the PR shows a removed blank
  line (looks like a deletion).
- Restoring from baseline adds it back → the PR shows an added blank line
  (looks like an addition).

Either way it obscures the real change.

## Baseline technique (fix without a rebase)

```bash
git show main:<file> > /tmp/baseline           # main's exact formatting
# identify real changes with: git diff -w main..HEAD -- <file>
# apply ONLY those semantic changes to the baseline via a script:
#   content = open('/tmp/baseline').read(); content = content.replace(old, new)
#   open('<file>', 'w', newline='').write(content)
```

The file then has main's original blank-line formatting plus only the real
changes — the PR diff shows zero blank-line noise.

## Rules

- Verify before committing: `git diff main -- <file>` shows no `^[-+][[:space:]]*$`.
- Never mix trailing-whitespace removal with logic changes in one commit — put
  whitespace normalization in a dedicated `style:` commit or avoid it entirely.
- `patch --ignore-whitespace` still carries multi-line→single-line collapses
  through (different line counts read as semantic) — check for collapsed
  expressions after any patch-based restore.
