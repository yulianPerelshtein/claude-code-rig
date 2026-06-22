# Prompt checklist

The canonical review checklist behind the `/optimize-prompt` skill. Apply it to
any skill / agent / command prompt before considering it done. Pairs with
`core/skill-frontmatter-reference.md` (the field-level reference).

## Token budget

- The body is **lean** — once a skill loads, its content stays in context for
  the rest of the session, so every line is a recurring cost.
- Long reference material (API specs, tables, examples) lives in a **supporting
  file** the skill points to, not inline.
- No restating of CLAUDE.md or other always-loaded context.

## Trigger clarity (model-invocable skills)

- `description` leads with the **use case and trigger phrases** — the one line
  the model reads to decide whether to load it.
- `description` + `when_to_use` stay under the **1,536-character** listing cap.
- Slot-in verbs with side effects use `disable-model-invocation: true` so they
  never auto-fire.

## Instruction clarity

- Imperative and **ordered**; numbered steps for procedures.
- States *what to do*, not a narration of *why* — unless the rationale changes
  the behavior.
- No contradictions with `core/` standing rules or the agent's own constraints.

## Frontmatter fit

- Right invocation control (`disable-model-invocation` / `user-invocable`).
- `argument-hint` present whenever the body reads `$ARGUMENTS`.
- `allowed-tools` scoped to what the skill actually needs — and wide enough to
  cover any `` !`cmd` `` injection.
- `paths` only when the knowledge maps to a file type; omitted for
  tool/reference skills.
- `model` right-sized (cheap mechanical → `haiku`; deep judgment → `opus`).

## Output-format specificity

- When the skill produces output, the **shape is pinned**: required headers, a
  table schema, a final verdict line. Ambiguous output format is the most common
  cause of inconsistent skill behavior.
- For a skill returning **many uniform records**, consider the TOON tabular
  encoding (~40% vs JSON, *uniform tabular only*) —
  `domains/context-engineering/toon-output-format.md`. For flat tables CSV is
  smaller; for nested data keep JSON.

## Edge cases

- Empty / missing argument: defined default or an explicit ask.
- No match / empty injection / tool failure: the body still makes sense.
- Idempotency where the skill writes or commits.

## Measurement, not vibes

- For a high-frequency or high-leverage skill, **measure** the change — don't
  trust a read-through. Use the `skill-creator` eval loop
  (`playbooks/prompt-optimization/ab-testing-skills.md`): it runs the skill on a
  fixed prompt set with and without the edit and reports the pass-rate delta
  against the token/time overhead.

## See also

- `core/skill-frontmatter-reference.md` — every frontmatter field.
- `playbooks/prompt-optimization/prompt-library.md` — vetted templates to start from.
