# Native context & memory levers

Zero-dependency, native Claude Code settings/hooks/frontmatter that shape what
enters context and what persists across sessions (item #27). All confirmed
against the official docs (settings / hooks / sub-agents / memory). Prefer these
before any third-party token-economy tool — they cost nothing and don't egress.

The rig ships a starting `core/settings.template.json`; **merge** its keys into
your own `~/.claude/settings.json` (don't blind-overwrite a settings file you've
customised). The bespoke installer drops it as `~/.claude/settings.template.json`
(never your live settings.json) for you to splice; on the marketplace install you
merge it yourself.

## 1. `ENABLE_TOOL_SEARCH` — defer MCP tool schemas

MCP servers (serena, Playwright) otherwise load every tool's full JSON schema
into context at session start. Tool Search defers the **schemas** — only tool
names + server instructions load up front, and Claude fetches a schema on demand
when it first needs that tool. This is the headline trim for a multi-MCP rig.

| Value | Behaviour |
|---|---|
| *unset* (default) | **Deferred** — tool search is on by default; schemas load on demand. |
| `"true"` | Same as default, pinned explicitly (what the template sets). |
| `"auto"` | **Threshold mode** — load schemas up front *only if* they fit within ~10% of context, else defer. |
| `"auto:N"` | Threshold mode with a custom percentage (e.g. `"auto:5"`). |
| `"false"` | Load all MCP schemas up front (no deferral). |

> **Correction to earlier rig notes:** deferral is the **default**, and `auto` is
> *threshold* mode (it may load small toolsets up front) — it is **not** "always
> defer". For maximum deferral the template pins `"true"`. Goes in the `env`
> block, as a string. Auto-falls back to up-front loading on Vertex AI or a
> non-first-party `ANTHROPIC_BASE_URL`.

## 2. `claudeMdExcludes` — skip noisy CLAUDE.md files at load

Glob patterns or absolute paths of `CLAUDE.md` files to skip when loading memory;
patterns match the absolute path. Keeps vendored / dependency instruction files
out of context. Applies to user/project/local memory only — managed policy files
cannot be excluded. The template excludes `vendor/` and `node_modules/` trees.

## 3. Auto-memory: `autoMemoryEnabled` / `autoMemoryDirectory`

Claude maintains a per-project memory store (a `MEMORY.md` entrypoint plus
optional topic files like `debugging.md`, read on demand) at
`~/.claude/projects/<project>/memory/` — already inside the `SECURITY_REVIEW.md
§6` exclude set, so it never reaches git or the redaction surface.

- `autoMemoryEnabled` (default `true`) — the template pins it on; set `false`
  (or `/memory` in-session, or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`) to turn it
  off. This is the single place to disable on-disk memory capture.
- `autoMemoryDirectory` — relocate the store (absolute or `~/`-prefixed). Left at
  the default here; set it only if you want memory outside `~/.claude`.

## 4. Per-subagent `memory:` frontmatter — scoped persistent memory

A subagent can carry its **own** `MEMORY.md`, isolated from the main session and
from other subagents, surviving across conversations. Add `memory: <scope>` to an
agent's frontmatter:

| Scope | Store |
|---|---|
| `user` | `~/.claude/agent-memory/<agent-name>/` |
| `project` | `.claude/agent-memory/<agent-name>/` |
| `local` | `.claude/agent-memory-local/<agent-name>/` |

When set, the agent's prompt is injected with the first 200 lines / 25 KB of its
`MEMORY.md` and Read/Write/Edit are auto-enabled for that store. Give it to the
**analysis/research** agents that benefit from remembering conventions across
runs — the rig sets `memory: user` on `code-reviewer`, `test-writer`,
`eval-planner`, and `eval-auditor`. Leave it off ephemeral agents (`refactor`
runs worktree-isolated; `pr-writer` is stateless).

## 5. `InstructionsLoaded` hook — observe what loaded

Fires when a `CLAUDE.md` or `.claude/rules/*.md` file enters context — at session
start and on lazy loads — with `file_path`, `memory_type`
(`User`/`Project`/`Local`/`Managed`), and `load_reason` (`session_start`,
`nested_traversal`, `path_glob_match`, `include`, `compact`). It has no decision
control (observability only); the rig wires it to append a JSONL audit line so
you can debug *which* instruction files actually loaded and why (path-glob rules,
nested `CLAUDE.md`, includes). See `core/hooks/instructions-loaded/`.

## 6. Compaction & memory lifecycle — what survives, what to rely on

Prefer native token reduction before any third-party tool: prompt caching,
context editing, auto-compaction, and skills lazy-loading. Evaluate any
token-economy tool against these first.

- **Auto-compaction is native.** On compaction, Claude Code re-attaches the most
  recent invocation of each skill (capped ~5,000 tokens per skill, ~25,000
  combined, oldest dropped first). Skill *descriptions* are NOT re-injected after
  compaction — only skills you actually invoked are preserved.
- **`/context`** shows live capacity with a per-category breakdown.
  **`PreCompact`/`PostCompact`** hooks fire around a compaction (both support
  `manual`/`auto` matchers; `PreCompact` can block, `PostCompact` cannot).
  Proactive save-state belongs on `PreCompact`. Hook stdin does NOT expose
  remaining context budget — only the statusline payload carries
  `context_window.*` (`used_percentage`, `remaining_percentage`, …). Do not build
  a PostToolUse "N% remaining" monitor.
- **`MEMORY.md`** is native, machine-local, zero-egress, and survives `/compact`
  (re-injected from disk). It is the cross-session memory backbone alongside
  `CLAUDE.md` (also re-read from disk post-compaction).

## See also

- `core/settings.template.json` — the starting settings these keys live in.
- `core/context-architecture.md` — the rig's layer/tier loading + precedence model.
- `domains/memory/serena.md` — the MCP whose schemas `ENABLE_TOOL_SEARCH` defers.
- `playbooks/observability/otel-insights-review.md` — pairs context cost with the
  cache-ratio metric to see deferral working.
