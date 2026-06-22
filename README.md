# claude-code-rig

> A personal Claude Code rig: skills-first core, path-scoped domain knowledge,
> native hooks, agents, output styles, and scheduled routines. WSL-first,
> manifest-driven, profile-based incremental install.

## What it is

A batteries-included Claude Code setup, packaged as a plugin (with a bespoke
installer for locked-down machines). It adds:

- a **safety guardrail** that blocks destructive commands (`rm -rf`, force-push,
  `curl | sh`, credential reads, …) plus an advisory prompt-injection scanner on
  fetched content;
- a **skills-first `core/`** — slash-command skills (`/commit`, `/review-pr`,
  `/walkthrough`, `/wrap-up`, `/health`, `/save-state`, …), agents
  (`code-reviewer`, `refactor`, `test-writer`, `pr-writer`, eval helpers), and
  output styles;
- **path-scoped `domains/`** — knowledge that auto-activates by file type
  (python, testing-tdd, software-design, cloud-aws, devops, ai-assisted-coding,
  context-engineering, observability, memory, methodology, scraping, security);
- a **continuous-improvement loop** — per-session summaries → deterministic
  consolidation (`dream-loop`) → `/dream-report` → distilled learnings;
- **routines** — named, repeatable procedures (`begin-work`, `wrap-up`,
  `weekly-retro`, `monthly-drift`, `dream-loop`) bound to manual / scheduled
  (systemd user timers) / event triggers, with an enforced outcome policy
  (report-only · draft-PR · local-write-allowlist);
- a **cost / rate-limit statusline** dashboard.

## Layout

| Path | What |
|---|---|
| `core/` | always-loaded skills, agents, hooks, output styles, routines, knowledge base |
| `domains/` | path-scoped domain knowledge (auto-activates by file type) |
| `playbooks/` | on-demand multi-step workflows |
| `templates/` | per-project starter files |
| `learnings/` | distilled cross-project lessons |
| `manifests/` | YAML-driven install + module + marketplace state |
| `install/` | WSL bootstrap, profile installer, dry-run, backup, rollback, validate, uninstall |
| `profiles/` | install profiles (see below) |
| `tools/` | CLI helpers, shareable-bundle exporter, sanitizer |
| `shareable/` | sanitized exportable subset (dashboard + generic hooks/commands/playbooks), MIT |

## Install

**Plugin (recommended):**

```bash
claude plugin marketplace add https://github.com/yulianPerelshtein/claude-code-rig
claude plugin install claude-code-rig@claude-code-rig
claude plugin list   # confirm it's enabled
```

**Bespoke profile installer** (for machines where the marketplace isn't an
option): clone, then run `install/bootstrap-wsl.sh`, or
`install/install-profile.sh <profile> [--dry-run]`. It supports dry-run, backup,
rollback, and uninstall; the source→target file map lives in `manifests/`.

Profiles: `minimal-core`, `personal-full`, `backend`, `bim-geometry-usd`,
`cloud-aws`, `ai-assisted-coding`, `claude-dashboard`, `shareable-dashboard`,
`enhanced-tier2`, `future-work-laptop`.

Optional cost/usage statusline: `bash shareable/dashboard/install.sh`.

## Shareable bundle

`tools/export-shareable.sh` produces a sanitized, **MIT-licensed** bundle from
`shareable/` — the statusline dashboard plus generic hooks/commands/playbooks —
safe to use or share on its own.

## Safety

The PreToolUse guardrail (`core/hooks/`) blocks destructive commands from a
shared blocklist; routines never push to a default branch and never merge (draft
PRs only, gated by the runner). Everything runs locally and zero-egress by
default.

## Versioning

`VERSION` is the canonical release; `git rev-parse HEAD` is the deployed commit.
Both are recorded in `~/.claude/.installed-from-rig.json` after each
`install-profile.sh` run.

## License

MIT — see `LICENSE`.
