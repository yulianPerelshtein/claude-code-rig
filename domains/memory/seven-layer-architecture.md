# Seven-layer memory architecture — the Ground Truth Hierarchy lesson

Pattern-borrowed from memory-os (the Hermes 7-layer memory stack — *not* a Claude
Code component; heavy infra: SQLite + Qdrant + Redis + ARQ + an auto-curated
wiki). We adopt **none of the stack** — only the one insight that generalizes to
any RAG / context-injection system, including this rig's `learnings/distilled.md`
and native `MEMORY.md`. See `ENHANCEMENTS_BACKLOG.md §4.1` (#1, Tier 3, docs-only).

## The Layer 7 thesis: declare which memory is authoritative

> Injecting context is not enough. If you don't explicitly tell the agent that
> the injected memory is **authoritative**, it treats it as one more suggestion
> and quietly ignores it in favor of its own priors.

memory-os calls its identity/authority layer the **"Ground Truth Hierarchy."**
The practical rule for this rig: when you inject standing context (CLAUDE.md
rules, distilled learnings, a loaded `MEMORY.md`), state its **precedence** — what
overrides what — rather than just dumping it. Anthropic's memory docs make the
same point: memory you write is only useful if the agent is told to treat it as
ground truth over its assumptions.

Apply it concretely:

- `core/context-architecture.md` already defines Layers 1–7 with precedence —
  keep that precedence *explicit in the text the model reads*, not just implied
  by load order.
- When `/dream-report` or `/wrap-up` append a learning, phrase it as a directive
  ("Always …", "Never …"), not a musing — a rule the model must follow, not a
  note it may consider.
- A retrieved snippet pasted into context should say *why* it's authoritative
  ("this is the project's verified convention"), or the model may discount it.

## Other reusable patterns (lessons, not infra)

- **4-level retrieval fallback chain:** hybrid → dense-vector → lexical → SQLite.
  The lesson: always have a deterministic last resort (exact/lexical/structured)
  when semantic retrieval misses — don't let a vector miss become a silent gap.
  (The rig's analog: serena/grep/Read as the deterministic floor under any
  semantic tool — `domains/memory/serena.md`.)
- **Dedup threshold:** cosine **> 0.92** to treat two memories as duplicates.
  A concrete starting point if the rig ever scores learning similarity.
- **Anti-padding filters:** per-session dedup + a "social-closer" filter (drop
  "thanks!", "sounds good") before anything enters long-term memory — keep the
  store dense with signal, not chatter. The dream loop's STOPWORDS + theme
  aggregation is the rig's version.

## What we deliberately do NOT adopt

The Hermes stack itself (Qdrant/Redis/ARQ/wiki) is out of scope — native
`MEMORY.md` + `CLAUDE.md` + `learnings/distilled.md` cover cross-session memory
zero-egress. If Hermes is ever adopted, the full install goes in
`playbooks/hermes/memory-os.md` (not created until then).

## See also

- `core/context-architecture.md` — the rig's 7-layer precedence model.
- `domains/memory/serena.md` — the retrieval/navigation layer.
- `core/context-budget-policy.md` — native `MEMORY.md` as the memory backbone.
