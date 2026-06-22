# Incremental refactoring

Refactoring is continuous, not a scheduled phase. Fowler (*Opportunistic
Refactoring*) argues you refactor whenever you touch code — in small steps,
woven into feature and bugfix work — rather than booking a big "refactoring
sprint" that never comes.

## The camp-site rule

Leave the code a little better than you found it:

- **Preparatory refactoring** — before adding a feature, reshape the
  surrounding code so the feature drops in cleanly ("make the change easy, then
  make the easy change").
- **Clean up your own mess** — remove duplication or awkwardness you introduce
  as you go, while the context is fresh.
- Keep each cleanup small and behavior-preserving; large rewrites are a separate
  decision, not a camp-site cleanup.

## Only refactor on green

Never refactor against red or absent tests — without a green baseline you can't
tell a refactor from a regression. If the code you're about to change isn't
covered, **add one or two characterization tests first** that pin the current
behavior, get them green, and only then refactor.

## The green loop

Mirror `core/agents/refactor.md`:

1. Tests **green before you start**.
2. Read all affected files first.
3. Make ONE small behavior-preserving change.
4. Run the tests. If green, **commit that step**; if red, fix or revert.
5. Repeat. Never break a public API without documenting the break.

Committing per green step keeps every increment revertible and keeps the diff
honest.

## Know when to stop

Refactoring has diminishing returns — avoid the rabbit hole. "Better, not
perfect" is the goal; **another visit is fine**. When you spot cleanup that's
out of scope for the current change, don't chase it now — leave a `ponytail:`
marker naming the upgrade path and move on:

```python
# ponytail: this dispatch is getting long; extract a handler table next visit
```

## Two modes

- **Opportunistic (in-flow).** Small refactors woven into the change you're
  already making. No worktree.
- **Isolated (worktree).** Large, self-contained refactors run in a git
  worktree (the `refactor` agent's `isolation: worktree`) to keep the working
  change clean.

Fowler's caution: routing *everyday* refactoring through branch/worktree
isolation discourages it — the friction makes people skip the small cleanups
that matter most. Reserve isolation for genuinely large refactors; do the small
ones in-flow.

## See also

- `playbooks/refactoring/minimal-changes-first.md` — keep the diff to the lines
  the change actually needs.
- `playbooks/refactoring/cherry-pick-layered-prs.md` — split a refactor out from
  the feature it enables into separate, clearly-labelled commits/PRs.
