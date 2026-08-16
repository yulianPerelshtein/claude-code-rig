# Verifying the test itself

A test you have not seen fail proves nothing. Both rules here are about the
test's own integrity, not the code's.

## Mutation-test a regression test

After writing a test meant to catch a specific defect, **apply that exact defect
and confirm precisely that test fails.** A test that passes with and without the
fix is worthless, and it is indistinguishable from a good one until something
breaks in production.

```bash
# 1. test passes against the fixed code
pytest tests/test_statusline.py -q          # 12 passed

# 2. reintroduce the exact defect the test targets
#    (here: put the $ segment back into the statusline)
pytest tests/test_statusline.py -q          # 1 failed  <- the test is real

# 3. restore, confirm green again
```

Check **which** test failed, not merely that something did. A mutation that
turns the whole suite red is usually a *broken mutation* — a missing import, a
syntax error — and that is a false signal, not a result. Fix the mutation until
it is a fair test of the one assertion, then read the failure.

`git stash push -- <source file>` is the cheapest way to apply and revert one:
stash the source, run the targeted test, expect a named failure, `git stash pop`.

This catches a whole class of self-deception. A check written against a parser
that only matched line-leading `@` once reported "all 2 Layer-1 files loaded"
for a five-file chain — it could not fail, so it passed, and the guarantee it
was supposed to protect was broken the whole time.

## Never mask a failing test

No `xfail`, no `skip`, no loosened assertion to get a green run. A failing test
is information; suppressing it destroys the information and keeps the defect.

- Fix the cause. If the cause is out of scope for the current change, that is a
  reason to open a separate PR for it — not a reason to silence the test.
- A quarantine marker is legitimate **only** when the test is failing for an
  environmental reason that is documented, and the quarantine is itself tracked.
  "It was already red" is not a reason.
- Deleting a test to make CI pass is the same act with better camouflage.

The corollary for tooling: a checker whose only failure mode is a false pass
belongs in the same category. Prefer one that can go red for a real reason over
one that is reassuring by construction.
