# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.7]

### Fixed

- Routine `target_default` was validated but never applied: the CLI always
  defaulted `--target` to the caller's cwd and the `/routines` skill hardcoded
  `--target "$PWD"`, so a `rig`-targeted routine (weekly-retro, monthly-drift)
  run from any other directory would act on — and open a draft PR against — the
  wrong repo. The runner now resolves the target from `target_default` unless an
  explicit `--target` is passed.
- `install/backup.sh` archived nearly all of `~/.claude` (only six excludes),
  sweeping personal history, spend logs, clipboard cache, per-session data, org
  policy, workspace identity, and `settings.json` into a portable tgz. Excludes
  expanded to the full never-leave-machine set, plus a pre-write scan that
  refuses if a credential-shaped string is staged.

## [0.0.6]

### Fixed

- Hooks that emitted through channels Claude Code ignores, so they were silent
  no-ops, now use the documented output contracts:
  - `mcp_trimmer` read the wrong stdin key (`tool_output`), emitted the wrong
    rewrite field (`updatedMCPToolOutput`), and was registered with the matcher
    `mcp__` (an exact-string match that no real tool name satisfies) — three
    independent reasons it never trimmed anything. Now reads `tool_response`,
    emits `updatedToolOutput`, matches `mcp__.*`, and has test coverage.
  - `subagent_start` / `subagent_stop` injected context via plain stdout (not
    shown to the agent); rewritten to emit `hookSpecificOutput.additionalContext`.
    `subagent_start` keeps the no-full-`cat`-learnings token discipline.
  - `pre_compact` kept its working state backup but dropped the model-directed
    nudge that only reached the debug log.
  - `typecheck` reported type errors with exit 1 (first-line-only hook error);
    now exit 2, the code that surfaces stderr to Claude.
  - `SessionStart` fired only on `startup`; now also on `resume|clear|compact`.

### Removed

- The `TaskCompleted` hook. It pushed a `/wrap-up` reminder to Claude via stdout,
  which the model never sees — and `/wrap-up` is non-auto-invocable, so the
  reminder was addressed to the wrong actor twice over. The `/wrap-up` discipline
  lives in `default-workflows.md` (user-invoked).

## [0.0.5]

### Added

- Cost / rate-limit statusline (`core/statusline/`): a stdin-native status line
  (context usage, tokens, session cost, 5h / 7d rate-limit windows) with no API
  calls or network. Enable via a `statusLine` entry in your settings.json (a
  plugin can't register one).

### Removed

- The vestigial `shareable/` tarball subtree and its exporter
  (`tools/export-shareable.sh` + sanitize/verify helpers). The repo is public +
  MIT, so the whole repo is the shared artifact; the generic-hooks/commands
  mirrors had drifted behind `core/`. The one live, unique piece — the statusline
  — moved into `core/statusline/`.

### Changed

- Trimmed the always-loaded Layer-1 core (~4205 → ~1520 tokens): deleted
  `coding-style.md` (duplicated paths-scoped domains), dissolved
  `context-budget-policy.md`, demoted `context-architecture.md` and the
  authored-content rules out of always-loaded context, and fixed an output-style
  bug that stripped built-in coding instructions.

## [0.0.4]

### Added

- `domains/project-journal/` — paths-scoped domain for disciplined project
  working-notes: a stage-gated plan with a resumption protocol, a numbered
  decision log (rationale + alternatives + divergences), a revise-later parking
  lot, and per-project `AGENTS.md` conventions.
- `domains/methodology/living-docs-update-policy.md` — when a human-curated doc
  earns an update vs. stays put, plus the evidence-cite + confidence-label
  writing discipline; framed as a policy, not a parallel-KB automation.

### Changed

- `playbooks/ai-assisted-coding/parallel-agent-fan-out.md` — sharpened the
  incremental-write resilience clause to state the loss bound (a crash loses
  only the last un-written batch, not the whole run).

## [0.0.3]

### Changed

- Pinned the bundled MCP servers instead of tracking moving targets: `serena`
  to a specific commit (was git default-branch HEAD) and `@playwright/mcp` to a
  fixed version (was `@latest`), so a session no longer auto-pulls unreviewed
  upstream code.
- Secret-scan CI installs `trufflehog` from a pinned release tarball + verify
  instead of piping an unpinned `install.sh` from `main` to `sh` (now mirrors
  the gitleaks step; removes the `curl | sh` supply-chain pattern from CI).

## [0.0.2]

### Changed

- `/review-pr` is now review-only by default: it renders the review for the
  human and posts a PR comment only after an explicit per-invocation
  confirmation. `gh pr comment` is no longer pre-authorized in `allowed-tools`.
- `/review-pr` gained a remote-resolution preflight (step 0): if the PR cannot
  be resolved (e.g. a renamed/stale `origin`), it stops and asks rather than
  silently degrading or guessing a repository.
- `/review-pr` deduplicates findings across the 6 reviewers before scoring, so
  one defect is no longer scored and reported multiple times.

## [0.0.1]

### Changed

- Specialized BIM/IFC/USD geometry knowledge is no longer bundled in this repo;
  it is maintained in a separate private overlay. The `bim-geometry-usd`
  profile and the domain's references in `manifests/` and `playbooks/` were
  removed accordingly.

## [Unreleased]

### Added

- Safety scaffolding: `.gitignore`, `.gitattributes`, `.editorconfig`, `LICENSE`,
  `README.md`, `VERSION`, `.pre-commit-config.yaml`, `.markdownlint.json`,
  `.github/CODEOWNERS`, and CI workflows (`lint`, `secret-scan`,
  `plugin-validate`, `installer-dryrun`).
- Secret-scan CI with three gates: gitleaks, trufflehog, and a custom
  redaction-pattern blocklist (`.github/scripts/check-redactions.sh`), mirrored
  by a pre-commit hook for local pre-push validation.
- Skills-first `core/`: slash-command skills, agents, native `hooks.json`,
  output styles, and a context-architecture knowledge base.
- Path-scoped `domains/` knowledge bases and on-demand `playbooks/`.
- Plugin packaging (`.claude-plugin/`) plus a bespoke profile installer
  (`install/`, `manifests/`, `profiles/`) with dry-run / backup / rollback /
  uninstall.
- Continuous-improvement loop (session summaries → `dream-loop` consolidation →
  `/dream-report` → distilled learnings) and a session performance analyzer.
- Routines: a registry-driven runner with manual / scheduled (systemd) / event
  triggers and an enforced outcome policy.
- Cost / rate-limit statusline (`core/statusline/`): a stdin-native status line
  (context usage, tokens, session cost, 5h / 7d rate-limit windows) with no API
  calls or network.

[Unreleased]: https://github.com/yulianPerelshtein/claude-code-rig/commits/main
[0.0.4]: https://github.com/yulianPerelshtein/claude-code-rig/commits/main
[0.0.3]: https://github.com/yulianPerelshtein/claude-code-rig/commits/main
[0.0.2]: https://github.com/yulianPerelshtein/claude-code-rig/commits/main
[0.0.1]: https://github.com/yulianPerelshtein/claude-code-rig/commits/main
