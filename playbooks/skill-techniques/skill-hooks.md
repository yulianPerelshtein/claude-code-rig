# Skill-level hooks (`hooks:`)

Pre/post hooks declared **on a skill** that fire only when that skill runs —
distinct from the global `hooks.json` (`core/hooks/hooks.json`) that fires for
every matching event session-wide.

Reference: `core/skill-frontmatter-reference.md` (the `hooks` row).

## The shape

```yaml
---
name: review-pr
description: Review the current PR
hooks:
  pre:
    - git fetch origin
  post:
    - echo "review complete"
---
Review the PR …
```

The `pre` commands run before the skill body executes; `post` commands run after
it finishes. Use them for setup/teardown that the skill *always* needs and that
shouldn't be the model's job to remember.

## Skill hooks vs. global hooks

| | Skill `hooks:` | Global `hooks.json` |
|---|---|---|
| Scope | Only when this skill runs | Every matching tool/event |
| Lives in | The skill's frontmatter | `core/hooks/hooks.json` |
| Good for | Per-skill setup (`git fetch`, warm a cache) | Cross-cutting policy (guardrail, typecheck, cost tracking) |
| Cost | Paid only on invocation | Paid on every matching event |

Rule of thumb: if the step is **specific to one skill**, use a skill hook; if
it's a **policy that must hold regardless of which skill ran**, it belongs in
`hooks.json`.

## When it pays off

- A skill whose correctness depends on fresh state: `git fetch` before a PR
  review, a `docker compose up -d` before an integration-test skill.
- A skill that should always leave a breadcrumb (post-hook append to a log).

## Rules

1. Keep hook commands **fast and idempotent** — they run every invocation.
2. Don't duplicate a global hook as a skill hook; pick the right scope.
3. A failing pre-hook should fail loudly (the skill ran on stale state
   otherwise). Don't swallow its exit code.
4. Never put secret-bearing commands in a skill hook (same exposure as
   `!` injection).

## This rig

The rig's cross-cutting policy (guardrail, typecheck, ruff-fix, cost tracker,
injection scanner, dream loop) lives in `core/hooks/hooks.json` because it must
hold for **every** session, not one skill. Reach for skill `hooks:` only when a
setup step is genuinely local to a single skill — most rig skills don't need
one.

## See also

- `core/hooks/hooks.json` — the global event wiring.
- `playbooks/skill-techniques/dynamic-injection.md` — `!` injection covers many
  "fetch before running" needs without a hook.
