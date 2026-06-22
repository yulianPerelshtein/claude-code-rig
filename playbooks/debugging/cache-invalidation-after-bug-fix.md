# Cache invalidation after a bug fix

Generated/cached files survive a fix to their producer. After fixing a bug in a
**file generator**, rotate the cache key or the stale output is silently reused
and your fix appears to have no effect.

- Rotate the **work-dir / job-id / version** after any generator change.
- Symptom: "I fixed the generation bug but the output is unchanged" → you're
  reading a cached artefact keyed the same as before.

Applies broadly: sidecar/manifest files, build artefacts, generated code,
fixture caches, archive (USDZ/zip) extracts, Docker layers.
