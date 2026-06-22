# Routines

A **routine** is a named, repeatable procedure (deterministic steps + tools)
bound to one or more triggers (manual / scheduled / event), with a target and an
enforced **outcome policy**, tracked in a registry. Routines apply to any repo,
not just this rig — every body takes `--target <repo>` (default = cwd).

See `ROUTINES_DESIGN.md` (staging) for the full design rationale.

## Anatomy

1. **Body** — the procedure. Either a skills-first `SKILL.md` (slash command,
   e.g. `core/skills/weekly-retro/` ⇒ `/weekly-retro`) or, for `dream-loop`, the
   shipped deterministic script `core/hooks/session/dream_loop.py` (no LLM).
2. **Trigger** — `manual` (slash), `event` (a hook), or `scheduled` (a systemd
   user timer; opt-in CI cron).
3. **Target** — the repo the routine operates on (`--target`, default cwd).
4. **Outcome policy** — enforced by the runner, never trusted to the model.

## Registry (`registry.yaml`)

Single source of truth binding name → body → triggers → target → outcome. Keys:

| Key | Meaning |
|---|---|
| `body` | skill folder name, or (with `body_type: script`) the routine label |
| `body_type` | `skill` (default; `claude -p /<body>`) or `script` (run `script` directly) |
| `script` | path (relative to the rig root) for `body_type: script` |
| `description` | one-line summary |
| `triggers` | list of `{type: manual / event / scheduled, ...}` |
| `target_default` | `rig` or `cwd` |
| `outcome` | `report-only` \| `draft-pr` \| `local-write-allowlist` |
| `enabled` | bool |

### The five v1 routines

| Routine | Body | Trigger(s) | Outcome |
|---|---|---|---|
| `begin-work` | new skill | manual + SessionStart **nudge** | report-only |
| `wrap-up` | **existing** `/wrap-up` | manual + SessionEnd | local-write-allowlist |
| `weekly-retro` | new skill | scheduled (Sun 18:00) + manual | draft-pr |
| `monthly-drift` | new skill | scheduled (monthly) + manual | report-only |
| `dream-loop` | **existing** `dream_loop.py` (script) | scheduled (nightly) + manual | report-only |

`wrap-up` and `dream-loop` reuse already-shipped capabilities; only
`begin-work` / `weekly-retro` / `monthly-drift` + the `/routines` dispatcher are
new. There is intentionally **no `/dream-loop` skill** — the routine schedules
the deterministic `dream_loop.py`, and `/dream-report` remains the human
synthesis step.

## Outcome policies (enforced by the runner)

The body produces content; the **runner** (`runner/cli` → `policy`/`gitops`)
decides what is written or pushed:

- **report-only** — the runner writes the body's output to a dated report under
  `~/.claude/routine-reports/`; no repo changes, no commits, no pushes. (The
  `dream-loop` script writes its own consolidation under
  `~/.claude/data/dream-reports/`.)
- **draft-pr** — the body edits files **inside an isolated git worktree**; the
  runner — never the model — commits, pushes `routine/<name>-<date>`, and runs
  `gh pr create --draft`. Never merged, never on a default branch.
- **local-write-allowlist** — the body writes machine-local native stores
  (session summaries / MEMORY) directly. No commits, no pushes.

## Safety invariants

The runner performs the git operations for `draft-pr` (the model only edits in
the worktree), and `runner/policy.py` is the gate on what the runner does:

- **never push to a default branch** (`main`/`master`) — `assert_push_allowed`,
  wired into `create_worktree` + `open_draft_pr`;
- **never run a destructive command** — `open_draft_pr` self-checks the
  structural command it builds via `assert_command_allowed`, whose blocklist is
  loaded from the SAME `core/hooks/blocked-commands.json` the guardrail uses (no
  drift) plus routine extras (no `git merge`, no `gh pr merge`, no
  `--dangerously-skip-permissions`);
- **never commit an edit outside the worktree** — before committing,
  `_run_draft_pr` resolves every changed path and asserts it is inside the
  worktree (`assert_path_in_target`), catching an absolute-path / symlink escape;
- draft PRs only, never merged.

The **model's own** actions during a headless run are constrained separately by
the PreToolUse guardrail hook + the permission profile installed in the target's
`~/.claude` — not by the runner (which never executes model-emitted commands).
The deployed `~/.claude` originals are never written (guarded against the real
`$HOME/.claude`).

> The **opt-in CI substrate** runs the body via `claude-code-action` directly,
> so the runner's invariants are **not** enforced there — only the workflow
> permissions + skill prose apply. Prefer the local systemd substrate for
> mutating routines (see the GitHub-Actions template's caveat).

`run-routine.sh ... --dry-run` writes nothing and prints the planned argv.

## Running

```bash
# preview (writes nothing)
core/routines/run-routine.sh weekly-retro --target "$PWD" --dry-run
# via the dispatcher skill
/routines list | status | run <name> | enable <name> | disable <name>
```

## Scheduling (systemd user timers — local default)

A shared templated service backs every routine; one concrete timer per scheduled
routine carries its own `OnCalendar`. Render the templates in
`templates/systemd/`, replacing:

| Token | Meaning |
|---|---|
| `__RIG_ROOT__` | absolute path to the rig checkout |
| `__TARGET__` | repo the routine operates on (default: the rig root) |
| `__NAME__` | routine name (a registry key + the service instance) |
| `__ON_CALENDAR__` | systemd `OnCalendar` expression |

Install rendered units under `~/.config/systemd/user/`, then
`systemctl --user enable --now cc-routine-<name>.timer`. `Persistent=true`
catches up runs missed while the machine was off (chosen over cron/atd because
WSLg timers proved unreliable). Run-state + log live in
`~/.local/share/cc-rig-routines/`.

## Scheduling (opt-in CI — escalation)

`templates/github-actions-routine.yml.tmpl` renders a per-repo workflow using
`anthropics/claude-code-action`. **It BILLS the Anthropic API account per token**
(not subscription-free in CI). It no-ops without `ANTHROPIC_API_KEY`, bounds
turns + wall-clock, and opens draft PRs only. Tier-2, never enabled by default.
