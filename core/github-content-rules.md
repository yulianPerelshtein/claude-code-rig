# GitHub content rules

Content authored for GitHub is for human reviewers and the audit trail.
Nothing about *how* a change was produced belongs there.

- PR / issue / comment bodies must NEVER reference the AI assistant, agents,
  skills, plan files, `.claude/` artifacts, internal session notes, or any
  other agent-internal artifact.
- PR bodies stay minimal:
  - `## Summary` — the user-facing intent.
  - `## Changes` — the concrete delta.
  - Do NOT add `## Why now`, `## Test plan`, `## Plan reference`,
    `## Background`, `## Notes`, etc. Reviewers read the diff for the rest.
- No emojis, no marketing tone, no "Generated with …" trailers.
- Prefer the REST API over the CLI when editing an existing PR/issue body, to
  avoid quoting/escaping corruption.
