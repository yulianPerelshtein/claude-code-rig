# Test economy

Every test costs reading time, run time and upkeep. Add one only when it catches
a defect that no other test catches. In the review these rules come from, a plan
asked for fourteen new test cases; six survived, and no coverage was lost.

## Before writing: the "catches what?" list

List each planned test with the defect only it catches. Drop the ones whose
answer is "nothing new":

- a type check (`isinstance(handler, X)`) beside a behaviour test that already
  goes through the same lookup;
- a test that only shows library or database behaviour (for example, Postgres
  treating NULLs as distinct in a unique key);
- a copy of an existing test with one constant changed.

Proposed tests from a reviewer, a critic agent or a plan are candidates. They go
through the same list; a proposal is not a requirement.

## Extend before you copy

In order of preference:

1. Add a case to an existing table (a `CASES` list, `@pytest.mark.parametrize`,
   `it.each`).
2. Parametrize an existing test over the old and the new value, and rename it to
   the general behaviour.
3. Write a new test, only for behaviour that no existing test exercises.

A parametrized test keeps one body. A copy drifts from its original.

Parametrize only cases of the same check. Two checks that merely share the
function under test stay in separate tests; following the file's existing
one-test-per-check layout is not a new pattern.

## Keep a named case where a loop cannot see

A test that loops over a registry or a set ("every listed member is
non-blocking") cannot notice a member that is missing from it. Membership needs
a named case. That case is not redundant.

## No new pattern inside a feature PR

A new kind of test (running migrations inside the suite, parsing SQL, a new
fixture style) or a guard for the whole repo (one migration head, enum parity
between code and schema) is its own PR, so the team can accept or refuse the
pattern. File it in the backlog with its code.

## One-off proof stays out of the suite

When the proof needs a real system (a migration on a real database, a deploy
step), run it once (a throwaway container is enough) and quote the result in the
PR body. Do not commit a test whose only job was to convince the author once.

## Then verify what you keep

Mutation-check each kept test (`verifying-the-test.md`): break the change and
see that exactly that test fails.
