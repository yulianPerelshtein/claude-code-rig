# Optional dependencies & platform-specific imports

Put OS-only or heavy-SDK imports **inside the functions that need them**, not at
module top. This keeps the module importable (and unit-testable) on a platform
or CI runner where the dependency isn't installed.

```python
def _handle_load(...):
    import some_native_sdk   # only imported when this path runs
    ...
```

For module-level names that tests must patch, declare them with a fallback:

```python
try:
    import some_native_sdk
except ImportError:
    some_native_sdk = None   # tests patch this name; import-clean on Linux/CI
```

Two distinct lessons live here:

1. **Importability / portability** — function-scoped imports for
   platform-/GPU-/native-only code paths; applies even with no tests.
2. **Test-patchability** — `try/except ImportError: name = None` so the symbol
   exists for `patch.object(...)` without the real dependency installed
   (cross-link: `domains/testing-tdd/pytest-mocking.md`).
