# Fargate ephemeral-volume asset cache

Design notes for an asset-download cache in a Fargate task (e.g. a converter
that pulls assets from S3):

- **Always-on for remote assets**; default the cache dir to a mounted path
  (e.g. `/cache/<name>`). Expose `cache_dir=None` to disable it (useful in
  unit tests).
- Back `/cache` with a **named ephemeral volume** mounted only in the task that
  needs it (CFN `Volumes` + `MountPoints`). Don't mount it in unrelated tasks.
- **Path-traversal guard**: before joining cached metadata's filename with the
  entry dir, assert it's a plain basename — `os.path.basename(v) == v` — so
  tampered metadata can't escape the cache dir.
- **try/except scope**: wrap only the cache lookup (etag check + lookup) in
  try/except. Keep the actual asset copy (the real S3 GET) **outside** it, so a
  genuine download failure propagates instead of being masked as a "cache
  lookup failed" warning.
- **Local testing**: point the cache dir at a temp path via config override;
  restore to the default before committing.
