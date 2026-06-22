# tracemalloc checkpoint hook

To capture a peak-memory snapshot at a **specific point** in a long-running
process:

1. `tracemalloc.start(25)` **before** any heavy imports (top of entry script).
2. Monkey-patch the existing checkpoint/log function to, when the target phase
   name fires, take `tracemalloc.take_snapshot()` and dump:
   - top allocation sites by `file:line` (`snapshot.statistics('lineno')`),
   - top live object types by `sys.getsizeof`,
   - `RSS − traced_total` ≈ C-side (native/numpy/image) estimate.
3. Write the report to a file (so a timeout/sleep doesn't lose it).

Run the profiled pass separately from timing runs (tracemalloc adds ~250–500
MiB and ~2× wall-clock). Rule/fact: `domains/python/debugging-tracemalloc.md`.
