# Clean code — the sound core, not the dogma

This rig writes clean code by following a **sound core** of principles applied
with judgment — and explicitly **skipping the dogma**. Robert Martin's *Clean
Code* mixes timeless advice (good names, single responsibility, no hidden side
effects) with dated, dogmatic advice (mandatory tiny functions, comment-phobia)
that often makes code *worse* when followed literally (see qntm, "It's probably
time to stop recommending Clean Code", 2020). Where the two conflict, this rig
follows the more balanced references: **John Ousterhout, *A Philosophy of
Software Design*** and **Sandi Metz**.

## The sound core

- **One responsibility per unit.** A unit with one reason to change is easier to
  name, test, and reuse.
- **Intention-revealing names.** The name should answer "what" and "why" so the
  body only has to show "how"; verbs for actions, nouns for things.
- **Command/query separation.** A function either *does* something or *answers*
  something — mixing the two hides side effects from callers.
- **No hidden side effects.** Mutating state a caller can't see is the most
  common source of "spooky action at a distance" bugs.
- **Dependency injection over hard-coded deps.** Passing collaborators in makes
  a unit testable and decouples it from a concrete implementation.
- **DRY with judgment.** Deduplicate real shared *concepts*, not coincidental
  similarity — premature deduplication couples things that should move apart.
- **Deep modules.** Prefer a simple interface over a wide one; a small surface
  hiding real work is the highest-leverage design move there is.

## Deep modules (Ousterhout)

Ousterhout reframes design around **complexity = dependencies + obscurity**, and
asks you to minimize both. The key tool is the **deep module**: a simple
interface over a substantial implementation. A function with three parameters
that does a lot of useful work is *deep*; a wrapper that adds an extra layer for
every internal call is *shallow* and just adds dependencies and surface area.
Prefer **fewer, deeper modules** over many shallow ones. This directly opposes
the "extract every few lines into its own function" reflex — a swarm of tiny
shallow functions raises total complexity even though each one looks simple.

## Duplication vs the wrong abstraction

Metz's rule: **"duplication is far cheaper than the wrong abstraction."** A
premature abstraction couples unrelated call sites; later, each new requirement
warps the shared code with flags and special cases until it is harder to follow
than the duplication it replaced. The discipline:

- Tolerate a little duplication while the right shape is still unclear.
- Extract a shared abstraction when the **concept is real** — a useful heuristic
  is the *third* genuine occurrence, not the second coincidence.
- If an existing abstraction is fighting you, **inline it back to duplication
  first**, then re-extract along the seam the requirements actually revealed.

## The YAGNI ladder

Before writing code, stop at the first rung that holds:

1. Does this need to exist at all? (speculative → skip it, and say so)
2. Does the standard library do it?
3. Does a native platform feature cover it?
4. Does an already-installed dependency solve it? (never add one for a few lines)
5. Can it be one line?
6. Only then: the minimum code that works.

Worked example — "we need a date picker":

```html
<!-- Rung 3: the platform already has one. No component, no dependency. -->
<input type="date" name="due" />
```

The reflex answer "pull in a date-picker library and build a `<DatePicker>`
wrapper" jumps straight past rungs 2–3 to a maintained dependency and a shallow
module. The ladder is a reflex, not a research project — spend seconds on it,
not an afternoon.

## What we explicitly reject

The metric-chasing dogma is **not** rig policy:

- No mandatory 2–4 line functions.
- No zero-argument-function requirement.
- No extraction of single-use helpers purely to shrink a function.
- No comment-phobia ("the code should explain itself" → delete comments).

qntm's critique shows the cost concretely: *Clean Code*'s own refactored sample
(the prime-generator) ends up **worse** — its logic shredded across many tiny
functions sharing mutable instance state, so you must reassemble the whole class
in your head to follow one path. Following the extreme rules made the code less
readable, not more. Readability and correctness beat metric-chasing.

## Mechanical vs judgment

There are two halves to "clean", and they live in different places:

- **Mechanical limits** (line length, argument count, branches, returns,
  cyclomatic complexity) are **objective** → enforced by Ruff/CI in
  `pyproject.toml` (`C901`, `PLR0911/0912/0913/0915`, `E501`). No human or LLM
  re-checks them. Genuinely justified exceptions use `# noqa` paired with a
  `# ponytail:` note explaining the ceiling.
- **Design judgment** (single responsibility, abstraction levels, the wrong
  abstraction, dependency injection, needless complexity) is **subjective** →
  this doc and the review agents own it. Reviewers do *not* re-flag the
  mechanical limits CI already gates.

## References

- John Ousterhout, *A Philosophy of Software Design* — deep modules; complexity
  = dependencies + obscurity.
- Martin Fowler, *Refactoring* and *Opportunistic Refactoring* — camp-site rule;
  refactor only on green; knowing when to stop.
- Sandi Metz, *99 Bottles of OOP* and "The Wrong Abstraction" — duplication is
  cheaper than the wrong abstraction.
- qntm, "It's probably time to stop recommending Clean Code" (2020) — the
  anti-dogma critique, with the worked prime-generator example.
