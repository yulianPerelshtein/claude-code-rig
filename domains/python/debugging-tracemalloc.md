# Point-in-time peak-memory profiling with tracemalloc

To snapshot memory at a **specific point** in a long-running process (not start
or end):

1. `tracemalloc.start(25)` **before** any heavy imports.
2. Monkey-patch the existing logging/checkpoint function to dump a snapshot
   when the target phase fires:
   - top allocation sites by `file:line` (`snapshot.statistics('lineno')`),
   - top live object types by `sys.getsizeof`,
   - `RSS − traced_total` ≈ the C-side (numpy / native / image-buffer) estimate.
3. Write structured output to a file so a timeout doesn't lose it.

Caveats:

- tracemalloc adds ~250–500 MiB and ~2× wall-clock overhead — worth it for the
  diagnostic, but measure clean separately.
- `sys.getsizeof` does **not** include externally-owned bytes (numpy / native /
  image C-side buffers) — pair it with the `file:line` allocation sites to see
  the real picture.

Companion playbook: `playbooks/debugging/tracemalloc-checkpoint.md`. Profile
*before* predicting a memory win: `playbooks/debugging/profile-before-predicting.md`.
