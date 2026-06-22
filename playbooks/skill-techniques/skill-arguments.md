# Skill arguments + `argument-hint`

Make a skill take input cleanly: declare what it expects so the `/` UI shows a
hint, and read the value from `$ARGUMENTS` in the body.

Reference: `core/skill-frontmatter-reference.md` (the `argument-hint` +
`arguments` rows).

## The shape

```yaml
---
name: walkthrough
description: Interactive section-by-section code walkthrough
disable-model-invocation: true
argument-hint: "[file]"
---
Walk through the file specified in $ARGUMENTS (or the file currently under
discussion) as an interactive learning session …
```

- `argument-hint` is the placeholder shown in the `/` menu — `[file]`,
  `<pr-number>`, `[type]`. It is **UX only**; it does not validate.
- `$ARGUMENTS` in the body is the raw string the user typed after the command.
- For richer inputs some CLI versions support a structured `arguments:` block;
  for a single positional value, `argument-hint` + `$ARGUMENTS` is enough.

## Conventions

- **Brackets convey arity:** `[optional]` vs `<required>`. Use `[...]` when the
  skill has a sensible default with no arg, `<...>` when it's mandatory.
- **Always handle the empty case.** Because `argument-hint` doesn't validate,
  the body must define what happens with no argument — default, infer from
  context, or ask. State it explicitly: *"…(or the file currently under
  discussion)"*.
- **Feed `$ARGUMENTS` into `` !`cmd` `` injection** when relevant:
  `` !`gh pr diff $ARGUMENTS` `` turns `/pr-summary 123` into a pre-injected diff
  (see `dynamic-injection.md`). For multiple positional args use `$0`, `$1`, or
  declared `$name` placeholders.

## When it pays off

- Any command-skill that operates on a target the user names: a file, a PR
  number, a commit type, a mode.
- Improves both invocation UX (the hint) and the body's ability to branch on
  input.

## Retrofit candidates in this rig

- `core/skills/commit/SKILL.md` — `argument-hint: "[type]"`; `$ARGUMENTS`
  overrides the inferred conventional-commit type. (Already wired.)
- `core/skills/walkthrough/SKILL.md` — `argument-hint: "[file]"`. (Already
  wired.)
- `core/skills/eval-spec/SKILL.md` — `argument-hint: "[plan|audit]"` selects the
  mode. (Already wired.)
- New skills (`optimize-prompt`, `dream-report`) declare their hints from day
  one rather than being retrofitted.

## See also

- `playbooks/skill-techniques/dynamic-injection.md` — combine `$ARGUMENTS` with
  `` !`cmd` `` to pre-fetch argument-scoped context.
