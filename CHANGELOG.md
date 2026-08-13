# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.12]

### Added

- **`memory-promotion` routine** (`core/routines/memory_promotion.py`, Sun 17:45,
  report-only). Native auto-memory is per-repository by design and the rig is
  cross-repo by design, with nothing carrying a rule between them: a "keep
  docstrings short" preference recorded in one project did not fire on another
  project's PR nine days later, while the same commit-message rule had been
  written out once per repo. The routine reports what is mechanical — a slug
  recorded in two or more live projects, and `type: feedback`/`user` memories —
  and `/weekly-retro` now reads that report and packages accepted promotions
  into a draft PR.
- `self-check` gained `delivery-paths-agree`: plugin-vs-checkout commit skew,
  Layer 1 serving uncommitted work, a hand-edited marketplace clone, and a
  statusline loading from a different checkout.

### Fixed

- `sync-rig.sh` pushed with plain `git push`, so the release tag it had just
  created stayed local while the remote's commits moved on. Now `--follow-tags`.

### Notes

- `memory-promotion` deliberately does **not** judge whether the rig already
  carries a rule. Three word-overlap attempts each produced confident nonsense —
  a mutation-testing memory cited to a PR-hygiene doc at 85%, then
  `user-working-style` rated fully covered on the words "working" and "style" —
  and tightening the threshold only moved which items were wrong. Semantic
  judgement lives in the skill that can read the files; the detector reports
  only what it can establish.
- Project-directory decoding is now filesystem-guided. The `/`-to-`-` encoding is
  ambiguous, and splitting on every hyphen silently dropped any project whose
  path contains one.

## [0.0.11]

### Added

- **`self-check` routine** (`core/routines/self_check.py`, Mon 08:30,
  report-only). Asserts the rig's *effects*, not its file layout, because every
  guarantee that broke this cycle broke while every structural check passed. It
  boots a real headless session and reads the `InstructionsLoaded` audit to
  confirm the Layer-1 import chain actually entered context; compares every file
  in the running plugin against the commit it claims; fires probes at the
  **installed** guardrail (with false-positive probes, since a blocklist that
  stops real work gets switched off); confirms declared timers exist and are
  enabled; and flags unpinned tool installs in CI. A `script` body on purpose —
  a verifier that depends on the model's judgement is not a verifier. A failing
  verdict leads the `/begin-work` brief rather than sitting in a report file.
- **`install/install-routine-timers.sh`** renders and installs the systemd units
  from the registry. Three routines had declared `enabled: true` with an
  `OnCalendar` and never run once, because nothing had ever rendered the
  templates. `draft-pr` routines are installed but left disabled without
  `--include-mutating`: arming one schedules an unattended push and PR, which
  `safety-rules.md` says needs explicit confirmation.
- **`install/sync-rig.sh`**, the one blessed propagation pass: refuses on a dirty
  tree, bumps the version when needed, publishes, resets a hand-edited
  marketplace clone (after backing the edits up), refreshes the plugin, then
  proves the result with `self-check`.
- `core/hooks/guardrail-probes.json` and first direct test coverage of the
  PreToolUse guardrail.

### Fixed

- **Timer-fired routines exited 127, silently, every night.** `systemd --user`
  supplies a minimal `PATH` containing neither `uv` nor `claude` (both in
  `~/.local/bin`), so a routine that ran perfectly in a login shell died under
  its own timer. `run-routine.sh` now repairs its own `PATH` — in the entrypoint
  rather than the unit file, so the cron and CI substrates inherit the fix.
- **CI lint changed verdict on unchanged code.** `uv tool install ruff` was
  unpinned: green in July, 159 errors in August against the same commit, after
  ruff shipped new default rules. Pinned to the version `.pre-commit-config.yaml`
  already used; `yamllint` pinned alongside it, and `self-check` now fails on any
  unpinned install so this cannot recur quietly.
- `core/authored-content-rules.md` contradicted Layer 1 on commit bodies.

### Changed

- `sync-rig.sh` bumps the version because **`claude plugin update` compares
  version strings, not commits**. With `plugin.json` unchanged it reports
  "already at the latest version" and leaves the plugin on its old commit however
  far the repo has moved — seven commits sat published-but-not-installed exactly
  this way. Any commit touching shipped content is undeliverable until the
  version moves.
- `context-architecture.md` documents the two delivery paths and why one path is
  impossible: a plugin cannot ship an always-loaded `CLAUDE.md` ("A `CLAUDE.md`
  file at the plugin root is not loaded as project context") and its
  `settings.json` honours only `agent` and `subagentStatusLine`, not the
  top-level `statusLine`.
- `validate.sh` resolves the statusline and `cc-extensions` set from the actual
  configuration instead of hardcoded paths, and verifies `CLAUDE.md`'s imports
  resolve rather than only that the file exists.

## [0.0.10]

### Fixed

- **Layer 1 never loaded.** `core/CLAUDE.base.md` calls itself "the always-loaded
  Layer-1 core" and `core/context-architecture.md` defines Layer 1 as
  `~/.claude/CLAUDE.md` — but only the bespoke manifest installer ever created
  that file. The marketplace path could not: a plugin ships skills, agents,
  hooks and MCP/LSP servers, never an always-loaded `CLAUDE.md`. So on a plugin
  install none of the core prose rules reached any session, silently, while
  every file still looked correctly wired. `bootstrap-wsl.sh` now writes
  `~/.claude/CLAUDE.md` as a one-line `@`-import of the rig's core — an import
  rather than a copy, so there is one source of truth and the nested `@sibling`
  imports still resolve against `CLAUDE.base.md`'s own directory. It is
  idempotent and never overwrites an existing hand-written `CLAUDE.md`.
- `install/validate.sh` passed on a `CLAUDE.md` whose import target no longer
  existed; it now resolves line-leading `@`-imports. Its statusline check
  hardcoded the bespoke install path (so it warned on a working plugin install)
  and its `cc-extensions` check hardcoded two of the five extensions — both now
  read from the actual configuration.
- Hooks ran as `uv run python …`, which resolves against whatever project
  environment the session happened to be in; now `uv run --no-project`.

### Added

- `## Authoring code` in Layer 1: comments fit on one line unless the meaning
  genuinely needs a second, and docstrings state the contract rather than
  restating the algorithm. The rig previously constrained comment *line length*
  only, never volume.
- `domains/python/comments-and-docstrings.md` — the Python mechanics of the
  above: two-line module docstrings, when a docstring is warranted at all, when
  NumPy `Parameters`/`Returns` earn their place, clause-boundary line breaks,
  and the carve-out for spec tables (content, not narration).
- `tests/hooks/test_guardrail.py` — first direct coverage of the PreToolUse
  guardrail.

### Changed

- The `Co-Authored-By` rule is now enforced, not just stated. The Claude Code
  system prompt instructs adding the trailer and the rig forbids it; a CLAUDE.md
  is context rather than configuration, so prose alone could not settle it.
  Layer 1 now says explicitly that the rule overrides the system prompt, and the
  guardrail blocklist hard-blocks any `git commit` carrying the trailer.
- `core/authored-content-rules.md` said a commit body "is for the non-obvious
  *why* only", contradicting Layer 1 and the `commit` skill, which both require
  a one-line subject with no body. Aligned on no body.
- Credential-file reads prompt for confirmation instead of being hard-blocked —
  legitimate on a dev box, and the `cat`-only blocklist patterns missed every
  other read verb anyway.
- The statusline no longer renders a `$` amount. `cost.total_cost_usd` is an
  API-equivalent estimate that bills nothing on a subscription plan; the
  rate-limit percentages are the real budget signal. The parser's output
  contract drops from ten fields to nine.

## [0.0.9]

### Added

- Quick-note capture (`qn`): `tools/cli-helpers/qn.sh` plus a slash-only `qn`
  skill. Appends a timestamped bullet under `## Log` in today's Obsidian daily
  note, scaffolding that note from the vault's own `_templates/daily.md` when it
  is missing — so a day first touched by `qn` matches what Obsidian would create
  instead of a stunted `## Log`-only file. The vault resolves from
  `$RIG_VAULT_DIR` (default `~/notes`), so nothing is pinned to one machine's
  layout. The script is the single source of truth: an interactive shell
  function and a personal `/qn` command call it rather than each carrying its
  own copy of the logic.

## [0.0.8]

### Fixed

- The statusline context bar rendered its fill inverted. The bar glyphs
  (`█` filled / `░` empty) were drawn under reverse video (`\033[7;3Xm`), which
  swaps foreground and background: the filled `█` run came out in the terminal's
  background colour (a grey sliver at the left edge) while the *empty* `░` track
  showed the status colour. Dropped the reverse-video attribute and now colour
  the two runs separately — filled in green/yellow/red by threshold, empty track
  in dim grey — so it reads as an ordinary progress bar.

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
