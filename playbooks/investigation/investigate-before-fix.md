# Investigate before fixing

Before writing a defensive fix:

1. **Reproduce** the issue. Confirm it actually occurs.
2. **Check environment specificity.** If it only reproduces with certain data
   (e.g. dev-only records), confirm staging/prod data is clean first — the fix
   scope may change entirely (or the fix may be unnecessary).
3. **Grep prior dead-ends.** In a deeply-investigated area, search any
   "confirmed dead ends" / findings doc before re-attempting something already
   ruled out.
4. Only then write the fix, scoped to the real cause.

Pairs with: `isolate-before-concluding.md`, `probe-first.md`,
`scope-mismatch-ask.md`.
