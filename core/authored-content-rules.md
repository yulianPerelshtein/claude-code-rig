# Authored-content rules

Covers anything written for human reviewers and the audit trail: PR/issue
bodies, commit messages, and review comments. Not always-loaded — the authoring
skills (`pr-writer`, `commit`, `review-pr`) cite this for the shared principle
and carry their own format inline.

## The principle (applies to all of them)

The diff is the source of truth. Authored content points at *intent* — the why
a reviewer can't reconstruct from the code — and stays out of the way otherwise.

- NEVER reference the AI assistant, agents, skills, plan files, `.claude/`
  artifacts, or internal session notes. None of that is part of the change.
  This includes plan/audit section labels (e.g. `D2`, `F2`, "phase N") — name
  what changed, not its tracking ID. Git history must stand on its own to a
  reader with no access to the plan.
- No "Generated with …" trailers, no emojis, no marketing tone.
- Write like a person on a small team talking to peers, not like a form.
  Concise and specific beats complete.

## PR / issue bodies

Lead with a `## Summary` — a sentence or two, in your own voice, on what this
does and *why* (the intent, a constraint, the reason now). That's usually the
whole body; experienced reviewers read the diff for the rest.

Add a `## Notes` section only when there's a real callout — a rejected
alternative, a deferred follow-up, a migration step, a breaking change. Omit it
otherwise. Don't add `## Changes`/`## Test plan`/`## Background` sections that
just re-narrate the diff.

When editing an existing PR/issue body, prefer the REST API over the CLI to
avoid quoting/escaping corruption.

## Commit messages

Conventional commit (`<type>(<scope>): <description>`). Subject says what
changed and why in one line; a body is for the non-obvious *why* only. Same
no-agent-internals rule as above.

## Review comments (on others' work)

Specific, actionable, and tied to the line. No preamble, no "great work but…"
padding. Suggest rather than mandate on style; reserve blocking asks for
correctness. (A fuller reviewing-others skill is planned.)
