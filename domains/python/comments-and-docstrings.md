# Comments and docstrings: volume, not just line length

`ruff-and-formatting.md` covers how *long* a line may be. This covers how much
prose to write at all — a file can pass every linter and still be buried in
commentary. The Layer-1 rule is the general one (comments fit on one line;
docstrings state the contract, not the algorithm); this is the Python mechanics.

## Module docstrings

Two lines. What the module is for, and the one constraint a reader would
otherwise get wrong. Not an essay, not a walkthrough of the pipeline, not a
list of the functions below — that list goes stale the first time someone adds
a function.

```python
# Prefer
"""Read events off the queue and hand them to the sink.

Events arrive unordered; the sink requires them grouped by stream id.
"""

# Avoid: a 25-line docstring restating the algorithm the code performs
"""This module implements the event ingestion pipeline.

The pipeline consists of the following stages:
  1. Read the raw events from the inbound queue ...
  2. Normalize each event by applying the transformations ...
  ... 20 more lines, now a second implementation to keep in sync ...
"""
```

## When a docstring is warranted at all

A docstring earns its place when it says something the signature cannot. Skip
it when the name and types already say everything:

```python
# No docstring needed — the signature is the whole contract
def is_expired(token: Token) -> bool:
    return token.expires_at < utcnow()
```

Write one when there is a precondition, a unit, a raise, a side effect, or a
non-obvious return convention. Those are facts; the step-by-step is not.

## NumPy Parameters/Returns sections

Use the NumPy sections only where the signature is **not** self-evident —
untyped or loosely typed parameters, a unit that the name doesn't carry, a
sentinel return. A `Parameters` block that restates `path: Path` as
"path : Path — the path" is pure cost.

```python
def backoff(attempt: int, *, ceiling: float = 30.0) -> float:
    """Delay before the next retry.

    Parameters
    ----------
    attempt : int
        Zero-based retry count — attempt 0 is the first *retry*, not the
        original call.
    ceiling : float
        Upper bound in seconds; the returned delay never exceeds it.

    Returns
    -------
    float
        Delay in seconds, jittered by up to 10%.
    """
```

Every entry carries a unit or a constraint the annotation cannot. That is the
bar. Delete any entry that would only restate the type.

## Inline comments

One line, and only for the *why*. If the comment needs a second line, first ask
whether a named variable or a small helper would carry the meaning instead.

```python
# Prefer
angle %= 360  # the solver returns cumulative rotation, not a bearing

# Avoid
# Here we take the modulo of the angle by 360 in order to normalize it into
# the range [0, 360), because the solver that produced this value returns a
# cumulative rotation rather than a compass bearing.
angle %= 360
```

Do not narrate the code (`# increment the counter`), and do not leave section
banners (`# ---- helpers ----`) in a file small enough to read at once.

When a comment genuinely needs a second line, break at a clause boundary — a
sentence end or a semicolon — not at the column limit. The break should fall
where a reader would pause anyway.

## What this rule does not cover

Brevity applies to *narration*, not to content. A table that encodes a spec — a
decision matrix, a status mapping, a unit-conversion reference — is data that
happens to live in a comment. Keep it whole; do not compress it into prose.
