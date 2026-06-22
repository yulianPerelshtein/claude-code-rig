# Config audit pattern (self-audit of the rig's own surface)

The valuable idea extracted from ECC's "AgentShield" concept — **without**
adopting ECC (a star-inflated polyglot mega-repo, ~217k★ vs ~1.1k watchers, heavy
collision risk with `cc-extensions/superpowers/`, monetization gravity toward a
paid tier; do **not** install it). See `ENHANCEMENTS_BACKLOG.md §4.3` (#20, Tier
3). This is a design note for a future standalone implementation, rescoped to a
**config** audit.

## The idea

Your agent's own configuration is an attack surface. A `/config-audit` pass
reviews the rig's **skills, hooks, permissions, and MCP servers** for:

- **Prompt-injection exposure** — skills/hooks that ingest untrusted content
  (Read/WebFetch/MCP output) and act on it without the advisory scan. (The rig
  already has `read_injection_scanner.py` on `Read|WebFetch`; the audit confirms
  coverage and flags new ingest paths.)
- **Over-broad tool permissions** — `allowed-tools` / permission rules wider than
  a skill needs (e.g. `Bash(*)` where `Bash(git *)` suffices); a skill granting
  itself broad access.
- **Unpinned / untrusted MCP servers** — `.mcp.json` entries from unknown
  sources, or servers whose tool output isn't trimmed (`mcp_trimmer.py`).
- **Secret exposure in config/injection** — any `!`-injection or hook that could
  surface a credential; cross-check `check-redactions.sh`.

## Why standalone, not ECC, and not a duplicate of native tools

- Native `/security-review` reviews **project code**; `/permissions` manages the
  permission set. Neither audits the rig's *own* skill/hook/MCP config as a
  threat surface — that's the gap this fills.
- Implement it Anthropic-aligned (a read-only skill over the rig's config files),
  not by importing ECC's bundle.

## Sketch (if/when built)

- `skills/custom/config-audit/SKILL.md` — read-only (`Read`, `Grep`, `Glob`);
  enumerate `core/hooks/hooks.json`, every `SKILL.md` `allowed-tools`, `.mcp.json`,
  and settings permissions; report findings by severity with the offending
  file:line; suggest the narrowest fix. Never edits config.
- Pairs with the verification council for consequential config changes, and with
  the periodic drift/security pass (`playbooks/continuous-improvement/monthly-drift-check.md`).

This is a **candidate**, not a shipped capability — captured so the AgentShield
idea isn't lost. Build it standalone if/when the config surface grows enough to
warrant it.

## See also

- `core/hooks/post-tool/read_injection_scanner.py` — the ingest-time injection scan.
- `playbooks/security/secret-scanning-patterns.md` — secret-leak prevention.
- `core/skills/review-pr/SKILL.md` + native `/security-review` — project-code review.
