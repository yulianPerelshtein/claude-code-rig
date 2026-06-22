---
name: security
description: >-
  Self-audit of the rig's OWN configuration — skills, hooks, permissions, and MCP
  servers — for prompt-injection risk and over-broad tool access. Use when
  reviewing or editing Claude Code config (settings, permissions, hooks, .mcp.json)
  or doing a periodic config-security pass.
paths:
  - "**/.claude/settings*.json"
  - "**/.mcp.json"
  - "**/hooks.json"
  - "**/.claude/**"
---

# security

Auditing the agent's *own* configuration as an attack surface. See
`config-audit-pattern.md` for the self-audit design (rescoped from the ECC
"AgentShield" idea; #20, Tier 3). For project-code security review use the
`review-pr` skill and native `/security-review`; for secret-leak prevention see
`playbooks/security/secret-scanning-patterns.md`.
