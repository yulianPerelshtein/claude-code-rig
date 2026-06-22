# dotenv load ordering

`load_dotenv()` must run **before** importing app modules that read env vars at
import time (config constants, module-level settings).

```python
from dotenv import load_dotenv
load_dotenv()
from app.config import ASSETS_DIR   # noqa: E402
from app.analysis import router      # noqa: E402
```

- Use `# noqa: E402` because the linter will otherwise flag the non-top imports.
- No-op in production (Render/Fly/containers inject env vars directly), so this
  keeps dev ergonomic without changing prod behaviour.
