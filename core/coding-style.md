# Coding style — Python

## Linting (run after every edit)

```bash
ruff check --fix <file>   # lint autofixes only — safe to run always
```

## Formatting — NEVER run automatically

- NEVER run `ruff format` on an existing file during a task.
- `ruff format` rewrites whitespace style (collapses multi-line expressions,
  strips trailing whitespace from blank lines) and creates PR noise.
- `ruff format` is ONLY used as an explicit one-time `style:` normalization
  commit, agreed with the user, separate from any functional change.
- The Bash guardrail (`hooks/blocked-commands.json`) blocks `ruff format`
  automatically — it will be rejected if attempted via Bash.

## Writing new multi-line code

Always add a **magic trailing comma** after the last element of any multi-line
dict / list / function call that must stay multi-line — ruff will then never
collapse it:

```python
# Good — stays multi-line because of the trailing comma
config = {
    item['name']: item
    for item in items
    if isinstance(item, dict) and 'name' in item  # no trailing comma in comprehensions
}

records.append(RecordSpec(
    name=name,
    width=0,
    height=0,   # <- magic trailing comma
))
```

Comprehensions (list/dict/generator) cannot have trailing commas; keep them
multi-line by writing them that way and never running `ruff format`.

## Editing existing files — baseline technique

Before editing any existing file, check for pre-existing formatting noise:

```bash
git diff main -- <file> | grep '^[-+][[:space:]]*$' | wc -l   # blank-line noise count
```

If noise exists (> 0), use the **baseline technique** instead of a line editor:

1. `git show main:<file> > /tmp/baseline.py`
2. Apply ONLY the semantic changes via string replacement in a script.
3. Write back preserving newlines: `open('<file>', 'w', newline='').write(content)`
4. Commit as a separate `fix: restore formatting baseline` commit BEFORE any
   functional change.

Rationale: editors that auto-run a formatter on save will rewrite every
trailing-whitespace blank line, turning a 3-line change into a 200-line diff.
The PostToolUse `ruff check --fix` (lint only, not format) is safe after edits.

## PR cleanliness

- A diff should contain only the lines the change actually needs.
- Watch for bidirectional blank-line noise (adding *or* removing trailing
  whitespace on blank lines) — it inflates diffs and obscures intent.

## Design principles

Write code a tired teammate can read at 3am — the sound core, applied with
judgment, not dogma.

- **One responsibility per unit.** A function/class/module does one thing.
- **Intention-revealing names.** Verbs for actions, nouns for things.
- **Command/query separation.** A function either *does* something or *answers*
  something, not both.
- **No hidden side effects.** Don't mutate state a caller can't see.
- **Dependency injection over hard-coded deps.** Pass collaborators in.
- **DRY with judgment.** A little duplication beats the wrong abstraction
  (Metz); extract only when the shared concept is real.
- **Deep modules (Ousterhout).** Prefer a simple interface over a wide one;
  complexity = dependencies + obscurity — minimize both.

### The YAGNI ladder

Before writing code, stop at the first rung that holds:

1. Does this need to exist at all? (speculative → skip it, and say so)
2. Does the standard library do it?
3. Does a native platform feature cover it?
4. Does an already-installed dependency solve it? (never add one for a few lines)
5. Can it be one line?
6. Only then: the minimum code that works.

The ladder is a reflex, not a research project.

### Marking deliberate shortcuts

When you take a deliberate shortcut, mark it and name the upgrade path:

```python
# ponytail: in-memory dict cache; swap for Redis if this goes multi-process
```

Greppable (`rg 'ponytail:'`), reads as intent not ignorance, and feeds the
refactoring backlog.

### Not dogma

Do NOT mandate 2–4 line functions, zero-argument functions, extraction of
single-use helpers, or comment removal. Readability and correctness beat
metric-chasing. Mechanical limits (length, args, branches, complexity) are
enforced by Ruff/CI (see `pyproject.toml`), not by hand.

### Never simplify away

Input validation at trust boundaries, error handling that prevents data loss,
security, accessibility, and anything explicitly requested are never cut for
brevity.
