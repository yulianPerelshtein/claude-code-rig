# Secret-scanning patterns for legacy / integration repos

When reviewing third-party desktop-app integration repos (vendor-tool add-ins,
C# desktop SDKs, legacy service repos that predate secrets management), grep for
hard-coded credentials in these common spots:

- `Constants/*ApiKeys*`, `Constants/Api*.cs`, any `.cs` with `const string`
  containing key-shaped values.
- `requirements.txt` lines like `git+https://<PAT>@github.com/...` (PAT embedded
  for a private package).
- `config.yaml` / `appsettings.json` SaaS tokens (error/monitoring,
  feature-flag, analytics providers).

These appear because the repos predate proper secrets management. Flag and route
to rotation; never copy the values anywhere.
