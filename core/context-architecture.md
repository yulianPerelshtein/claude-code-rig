# Context Architecture — Canonical Reference

The rig's loading + precedence model. This is on-demand reference (not
always-loaded): pull it with `@core/context-architecture.md` when editing the
rig's structure. Two orthogonal axes — **where** a rule lives (layers) and
**when** content loads (tiers).

> Skills-first note (2026-06): upstream Claude Code merged commands into
> skills, so Layer 3 is now **skills** (a "command" is a skill with
> `disable-model-invocation: true`). Layer 7 is complemented by native
> `MEMORY.md`. The hierarchy is otherwise unchanged.

## Layer Hierarchy (where a rule lives + precedence)

```text
Layer 1: ~/.claude/CLAUDE.md          ← global, always loaded, universal rules only
Layer 2: <project>/.claude/CLAUDE.md  ← project-specific overrides and architecture
Layer 3: ~/.claude/skills/*/SKILL.md  ← skills (incl. commands = disable-model-invocation)
Layer 4: ~/.claude/agents/*.md        ← specialized subagents, invoked by name
Layer 5: ~/.claude/styles/*.md        ← output modes, invoked by /style
Layer 6: project memory files         ← persistent findings, loaded contextually
Layer 7: learnings/distilled.md + native MEMORY.md  ← cross-project operational patterns
```

**Placement rule**: a rule belongs at the HIGHEST layer where it is universally
true. Never duplicate a rule across layers.

## The two delivery paths

One source of truth (this repo) reaches a running Claude Code by two routes, and
the split is a **constraint, not a choice**:

| Route | Carries | Serves |
|---|---|---|
| plugin cache (`${CLAUDE_PLUGIN_ROOT}`) | skills, agents, hooks, MCP/LSP servers | the last **published commit** |
| the checkout, read directly | Layer 1 (`~/.claude/CLAUDE.md` import) + statusline | the **working tree**, instantly |

Neither of the second route's two components can move to the first. Per the
plugin reference: "A `CLAUDE.md` file at the plugin root is not loaded as project
context", and a plugin's `settings.json` honours "only the `agent` and
`subagentStatusLine` keys" — not the top-level `statusLine`.

The hazard is that the routes serve **different commits**: an uncommitted edit to
`CLAUDE.base.md` reaches every session immediately, while the hooks meant to
enforce it stay on the last published commit. That is not hypothetical — the
plugin sat 7 commits behind the checkout while both were "working".

`install/sync-rig.sh` is the one blessed pass that realigns them (refuses on a
dirty tree, publishes, refreshes the plugin, then proves it with `self-check`).
`self-check`'s `delivery-paths-agree` reports whenever they are apart, including
hand-edits to the marketplace clone — a third real git checkout whose local
edits are invisible to the rig and discarded on the next update.

**How Layer 1 is deployed**: a plugin ships skills, agents, hooks, and MCP
servers — it CANNOT ship an always-loaded `CLAUDE.md`. So `bootstrap-wsl.sh`
writes `~/.claude/CLAUDE.md` as a stub holding one line, `@<rig>/core/CLAUDE.base.md`.
An import rather than a copy: the rig stays the single source of truth, and the
`@sibling` imports inside `CLAUDE.base.md` resolve against ITS directory, so
`safety-rules` / `default-workflows` / `reasoning-preferences` come with it
(max import depth is four hops; this chain is two). Without that stub nothing
in `core/` reaches a session — a silent failure, since every file still looks
correctly wired. `install/validate.sh` checks both the stub and that its import
target resolves; `/context` lists what actually loaded, and the
`InstructionsLoaded` hook logs it per session.

## Loading triggers (when content enters context)

Keep the always-loaded core minimal; let everything else load only when
relevant, and lean on native context management rather than hand-built hooks
(see `domains/context-engineering/native-context-levers.md`).

| Tier | What loads | When |
|---|---|---|
| 0 — Always | `CLAUDE.base.md` + its imported core files | Every session start |
| 1 — Domain | A domain's `SKILL.md` | Auto-activates when its `paths:` globs match files in context |
| 2 — Project | Project `CLAUDE.md` / `AGENTS.md` | When a session opens inside that project tree |
| 3 — Task | A specific `domains/<d>/<topic>.md`, a `playbooks/<area>/<name>.md`, or specific distilled-learning entries | On demand via `@filename` |
| 4 — Reference | `archive/`, deep references | Never auto-loaded |

### Domains activate two different ways

Not every domain is file-shaped, and forcing `paths:` onto one that isn't makes
it fire constantly on files it has nothing to say about.

| Kind | Activation | Domains |
|---|---|---|
| **File-shaped** — applies whenever you touch a file type | `paths:` globs | `python`, `testing-tdd`, `software-design`, `devops`, `security`, `project-journal` |
| **Task-shaped** — applies to a *kind of work*, any file type | description match (no `paths:`) | `ai-assisted-coding`, `cloud-aws`, `context-engineering`, `memory`, `methodology`, `observability`, `scraping` |

For a task-shaped domain the **description is the only activation route**, so it
must carry an explicit "Use when …" trigger. Measured against the real working
repos (3358 files), `ai-assisted-coding` was matching **1906** of them on
`**/*.py` while its content is LLM-SDK integration — irrelevant to nearly all of
them. `cloud-aws` was the mirror image: **0** matches, because its globs targeted
Terraform and CloudFormation while the actual AWS surface here is boto3. Both are
now task-shaped. Re-measure before adding `paths:` to a domain; a glob that
matches most of the corpus is a smell, and one that matches nothing is a bug.

Distilled learnings are likewise NOT auto-`cat`'d at session start —
`session_start.sh` prints only a short cue; targeted entries come on demand
(`/load-learnings`, or `@learnings/distilled.md`).

## Standard Project CLAUDE.md Template

```markdown
# <project-name>

<one-line description + distinct role vs other projects>

## Active Work  [omit if no active branch/plan]
Branch: `<branch>` — <status>. Plan: `<path>`

## Architecture
- `<file>` — <one-line role>
[list only non-obvious files]

## Style Overrides  [omit if identical to global]
- [only rules that DIFFER from global CLAUDE.md]

## Do Not
- [project-specific prohibitions only]
```

## distilled.md Entry Format

```markdown
## YYYY-MM-DD CATEGORY-NAME
[Operational rule — what/how only. No Context/Reason labels.]
```

- One entry per distinct pattern; date when confirmed; ALL-CAPS-WITH-DASHES category.
- 1–3 lines max; include exact commands, API paths, function names.

## Drift Monitor

Operationalized by the `/drift-check` skill (the duplication grep) and the
monthly `playbooks/continuous-improvement/monthly-drift-check.md` cadence.

**Triggers (check in order):**

1. `wc -l learnings/distilled.md` — if >200: compress (strip verbose preambles).
2. Run `/drift-check`, which **discovers** the instruction files that exist rather than assuming a repo home — a hardcoded `<workspace>/*/.claude/CLAUDE.md` glob matched nothing here and reported "no drift" every run. Any phrase in 2+ files → remove from the project layer.
3. New `settings.json` hook or skill added → audit Layer 1 for redundancy.
4. Before major branch handoff → verify project `CLAUDE.md` is current.

**Re-optimize (10 min):**

- distilled.md >200 lines → strip `**Context:**`/`**Reason:**` annotations.
- Duplicates found → keep in global, remove from project layer.
- Project CLAUDE.md >45 lines → push universal rules up to Layer 1.

> Native equivalents already cover what earlier drafts proposed as bespoke
> agents: the `InstructionsLoaded` hook
> (`domains/context-engineering/native-context-levers.md §5`) observes which
> instruction files actually load and why; `/drift-check` reports cross-layer
> duplicates. No Context-Validator / Session-Counter agent exists or is needed.
