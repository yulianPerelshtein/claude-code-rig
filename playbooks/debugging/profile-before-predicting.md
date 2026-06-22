# Profile before predicting a memory win

When a refactor is predicted to deliver a large memory reduction (>2×),
**profile first** to verify where the memory actually lives.

- The hypothesis ("concurrent loader references hold N GiB") is often wrong; the
  real peak may be irreducible **output working-set** data (e.g. decoded image
  arrays awaiting packaging) that the planned change cannot free.
- A streaming/structural refactor scoped against the wrong hypothesis can ship
  a few-percent win instead of the predicted multiple.
- Use a point-in-time snapshot (`domains/python/debugging-tracemalloc.md`) to
  attribute the peak to `file:line` before committing to the refactor. Gate the
  architectural follow-up behind a written plan.
