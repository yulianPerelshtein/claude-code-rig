# A rule that fires for exactly one case is suspect

When a rule has an edge-case path (e.g. "elements outside the visible band →
unassigned/flagged") and that path fires for **~1 legitimate real-world case**
across the entire corpus, the rule is probably too strict.

- Test rules on **real data** before declaring them correct.
- Prefer a **symmetric catch-all + a flag** over an "unassigned" bucket: it
  preserves the operator-facing diagnostic value without dropping the
  assignment.
- A single legitimate case in the edge path (rooftop slab, deep foundation) is
  a signal to broaden the rule, not to special-case the one element.
