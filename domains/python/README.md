# domains/python — README

Generic Python engineering knowledge, distilled from cross-project experience.
Activates as a `paths:`-scoped skill (see `SKILL.md`) when Python files are in
context. No project/company/vendor specifics.

| File | Lesson |
|---|---|
| `ruff-and-formatting.md` | lint vs format; magic trailing comma; on-save-formatter hazards; line length. |
| `optional-dependencies-and-platform-imports.md` | function-scoped imports for OS-only / heavy SDKs; test-patchable module names. |
| `numerics-and-tolerances.md` | never `==` on floats; named, unit-meaningful tolerances. |
| `defensive-vs-revealing-code.md` | sign multipliers over `abs()`; let invariant violations surface. |
| `import-time-side-effects.md` | module-import-time file checks fail silently. |
| `debugging-tracemalloc.md` | point-in-time peak-memory profiling. |
