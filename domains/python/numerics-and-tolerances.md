# Numerics and tolerances

Never use `==` to compare or de-duplicate floats. Authoring/serialization
toolchains emit floating-point noise — a value meant to be `3000.0` may be
written as `2999.9999999` — and exact equality silently misses these.

```python
_EQUAL_TOLERANCE_M = 1e-3  # 1 mm — named, unit-meaningful, not 1e-9
if abs(a - b) < _EQUAL_TOLERANCE_M:
    ...  # treat as equal / duplicate
```

- Tie the tolerance to a **named, project-level unit-precision threshold**
  (e.g. the touch tolerance used elsewhere), not an arbitrary `1e-9`.
- The same applies to "is this zero / aligned / coincident" checks.

Case study: IFC storey-elevation de-duplication (float-equality traps in
geometry pipelines).
