# Progressive skill activation

Pattern-borrowed from deer-flow (Bytedance's LangGraph super-agent harness — a
heavyweight *competing* harness, ~16 GB RAM, out of scope). We adopt **none of
the harness** — only its activation discipline, which happens to match how Claude
Code already works. See `ENHANCEMENTS_BACKLOG.md §4.2` (#15, Tier 3, docs-only).

## The lesson

> Load a skill's full content only when it is **activated by name**, not all
> skills at session start.

deer-flow loads skills on `/skill-name` activation rather than front-loading
them. This is the right default — and **Claude Code already does it natively**:

- A skill's `description` is in context so the model knows it exists, but the
  **full body loads only when the skill is invoked** (auto or `/name`).
- `disable-model-invocation: true` removes even the description from context
  until you invoke it — maximal laziness for slot-in command-skills.
- `paths:`-scoped domain skills surface only when matching files are in play.

So the rig's structure is already aligned. The actionable takeaway is a
**review discipline**, not a new mechanism:

- Don't defeat native lazy-loading by stuffing reference material into
  always-loaded `core/` files — push it into `domains/`/`playbooks/` that load on
  demand (`core/context-architecture.md`).
- If session-start context feels heavy, audit what's actually front-loaded
  (`/context`), and compare the rig's activation footprint against
  `cc-extensions/superpowers/` — if ours loads more eagerly than necessary,
  move content behind a `description`/`paths:` gate.
- Every always-loaded line is a recurring token cost; prefer activation-gated
  content.

## What we do NOT adopt

deer-flow itself (the harness, its Doubao/DeepSeek/Kimi defaults, BytePlus
services) — it duplicates Claude Code's role. Lesson only.

## See also

- `core/skill-frontmatter-reference.md` — `disable-model-invocation` / `paths:` / `description`.
- `core/context-architecture.md` — tiered, activation-gated loading.
- `playbooks/skill-techniques/` — the native frontmatter techniques in practice.
