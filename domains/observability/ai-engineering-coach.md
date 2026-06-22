# AI-Engineering-Coach — Tier 2, opt-in

[AI-Engineering-Coach](https://github.com/microsoft/ai-engineering-coach) is a
read-only VS Code extension that observes Claude Code session logs locally, runs
them through ~45 anti-pattern rules across 5 categories (prompt quality, session
hygiene, **code review**, tool mastery, context management), and renders a
forensic dashboard. It also has a Skill Finder (mines repeated prompts to suggest
skill candidates) and instruction-file audits. MIT, ~2.2k★, no telemetry.

It is the **retrospective/forensic** complement to the rig's real-time statusline
dashboard — they don't overlap. Downgraded from Tier 1 to **opt-in** per
`SOTA_REFRESH.md §4.4` for the reasons below.

> Disclaimer (from its own README): *"an open-source community effort by
> Microsoft employees. It is not an official Microsoft product."* No SLA; could
> be archived without notice.

## Why it's opt-in, not adopted

1. **No prebuilt VSIX.** As of evaluation, `gh api .../releases` returns `[]` —
   GitHub Releases is empty. The README's "Path 1 — Prebuilt VSIX" is currently
   **non-functional**. You must build from source (Dev Container, or local
   Node.js + npm + esbuild + `vsce package`).
2. **WSL2 log-path compatibility unconfirmed.** It claims "any harness, one
   dashboard," but Claude Code log parsing on WSL2 is implementation-specific and
   unverified. Budget +1–2 days for VSIX build / WSL2 path debugging.
3. **Community support model.** No vendor SLA.

## Adoption path (deferred user action)

1. Build the `.vsix` from source on the laptop (Path 2 Dev Container or Path 3
   local Node). Install it in VS Code.
2. Verify the dashboard actually renders your Claude Code sessions on WSL2.
3. Capture which of the ~45 rules are most actionable for your workflow (the
   `code review` category is the most directly useful for a coding rig).
4. Adopt the weekly ritual: `playbooks/observability/weekly-coach-review.md`.

The quantitative side (cost/token/cache trends) is already covered by native
OTel + ccusage (`domains/observability/claude-code-otel.md`); the Coach adds the
*qualitative* forensic + skill-finder layer on top.

## See also

- `playbooks/observability/weekly-coach-review.md` — the retrospective ritual.
- `domains/observability/claude-code-otel.md` — the quantitative half (adopted).
- `profiles/enhanced-tier2.yaml` — the opt-in profile.
