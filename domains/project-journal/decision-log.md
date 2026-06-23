# The decision log

A numbered, append-only log of every non-obvious choice. Numbers are stable
handles you can cite from commit messages, the final report, and later
decisions ("supersedes D14"). The log is the project's memory of *why*, which
the diff never records.

## Each decision carries three things

```text
D14. <statement — what was decided, in one line>
     Rationale: <why this over the obvious default>
     Alternatives rejected: <what else was on the table, and why not>
```

Statement-only entries rot: six weeks later you can't tell whether a choice was
deliberate or accidental. The alternatives line is what makes the log defensible
in review — "considered X and Y, chose Z because…" reads very differently from a
bare assertion.

## Record divergences at the moment of discovery

The highest-value entries are the ones written *when reality breaks the plan* —
not reconstructed afterward. Capture the pivot inline, with the trigger:

```text
D14 (revised). Dropped the planned mesh-distance library — not on the package
     index for our toolchain; would force off the project's dependency manager.
     Pivoted to a 2D-footprint decomposition that needs no new dependency.
D20 (calibrated). Real input data carried float noise the synthetic fixtures
     never produced; equality tolerance moved from exact to a 1mm unit threshold.
```

These are the decisions a reader most needs and least often finds, because the
instinct is to quietly fix and move on. Write them down as they happen.

## Structured Finding Format

For a non-obvious *discovery* (as opposed to a decision), use a consistent unit
so findings stay greppable and reviewable:

```text
**Finding:** <what was found>
**Evidence:** <file path(s), symbol, line range>
**Confidence:** High | Medium | Low
**Open question:** <what needs confirmation, or "none">
```

The evidence line is the discipline: a claim with no file-path backing is a
vibe, not a finding. The confidence label tells a later reader (or red-team
pass) where to spend scrutiny. Findings whose open question is unresolved
belong in `revise-later.md`, not buried in prose.
