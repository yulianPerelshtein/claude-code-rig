# Rename: grep everything, not just source

When renaming a symbol, dataclass field, function, or config key, grep **all**
usages — not just the language source files.

- `scripts/` (shell, makefiles, CI YAML) often hard-code names that Python/unit
  tests won't catch.
- Search docs, fixtures, and generated-file templates too.
- A missed shell-script reference fails only at runtime, often in CI or prod.

`rg -n '<old-name>'` across the whole repo before declaring a rename complete.
