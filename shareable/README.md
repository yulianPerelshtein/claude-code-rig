# shareable/

The only directory in this repo that may be packaged for distribution. Every
file here is vendor-neutral and passes the redaction + secret scans
unconditionally. The parent repo is all-rights-reserved; **this subtree is
MIT-licensed** (see [`LICENSE`](./LICENSE)).

## Bundles

| Directory | Bundle name | Contents |
|---|---|---|
| `dashboard/` | `dashboard` | Flagship: stdin-native statusline + cost-tracker + MCP-trimmer + budget + install/uninstall + tests. |
| `generic-hooks/` | `hooks` | `guardrail.py` + `blocked-commands.json` + `post_tool_use_failure.py` + `mcp_trimmer.py` + tests. |
| `generic-commands/` | `commands` | Skills (`disable-model-invocation`): `commit`, `health`, `save-state`, `walkthrough`, `wrap-up`. |
| `generic-playbooks/` | `playbooks` | Portable operational notes (WSL paste safety, ruff baseline, parallel agents, AI-as-judge, LLM SDK deferral, gh-PR-via-REST, AWS SSO). |

## Export

Build a sanitized, self-contained tarball with the repo's exporter:

```bash
tools/export-shareable.sh --bundle dashboard --output ~/exports/cc-dashboard.tgz
tools/export-shareable.sh --bundle everything --dry-run   # scans only
```

The exporter copies the selected bundle dirs into a temp stage, runs every
redaction + secret scan (any hit aborts), adds a top-level `LICENSE` /
`README.md` / `INSTALL.md`, and writes a reproducible tarball. Nothing outside
`shareable/` ever enters a bundle.
