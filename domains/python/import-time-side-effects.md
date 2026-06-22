# Import-time side effects fail silently

Module-import-time file-existence checks are a silent-failure trap:

```python
# At import time: if the asset is missing, the constant becomes "" and every
# downstream consumer silently omits it — wrong output, no error.
_DEFAULT_ASSET = _find_asset() or ""
```

A missing asset (HDRI, texture, data file, model) becomes an empty default and
the program produces wrong output with **no error**.

- Don't rely on repo-relative file existence checked at import time.
- Resolve assets via an **env var** or an **explicit validation step** that
  fails loudly when a required input is absent.
- Keep import side-effect-free where possible; do I/O in functions, not at
  module scope.

BIM/asset-pipeline instance: USD-scene validation that must run on demand,
not as an import-time side effect.
