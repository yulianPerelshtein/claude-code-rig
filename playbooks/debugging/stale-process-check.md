# Check for a stale process before debugging an API

When an API response doesn't match the code on disk — a field is missing that
clearly exists in the source and the model — suspect a **stale server process**
before debugging the code.

```bash
ps aux | grep -i uvicorn      # or gunicorn / flask / node — the relevant server
```

A process started by a previous terminal session may be serving old code. Kill
it, restart, and re-verify **before** spending time on code-level debugging.
