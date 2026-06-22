# Skill frontmatter reference

The canonical reference for every skill/command frontmatter field this rig uses.
A skill is a `SKILL.md` file: a YAML frontmatter block between `---` markers,
then a Markdown body that becomes the prompt. For the *how-to* of the advanced
techniques, see
`playbooks/skill-techniques/{dynamic-injection,forked-investigation,skill-hooks,skill-arguments}.md`.

> Canonical source: `docs.claude.com/en/docs/claude-code/skills` (frontmatter
> reference). All fields are optional; only `description` is recommended so the
> model knows when to use the skill. Confirm anything load-bearing against your
> installed CLI version.

## Identity

| Field | What it does | When to use | Gotcha |
|---|---|---|---|
| `name` | Display name in skill listings; **defaults to the directory name**. | Optional. | For a `<dir>/SKILL.md` the *command* you type comes from the directory name, not `name` — `name` only sets the command for a plugin-root `SKILL.md`. |
| `description` | The one line the model reads to decide whether to auto-invoke. Falls back to the first body paragraph if omitted. | Always. | `description` + `when_to_use` are truncated at **1,536 chars** in the listing — put the key use case first. |
| `when_to_use` | Extra triggering guidance (trigger phrases, example requests); appended to `description`. | When triggers are subtle. | Counts toward the same 1,536-char cap; don't pad it. |

```yaml
---
name: commit
description: Create a conventional commit with smart staging
---
```

## Invocation control

| Field | What it does | When to use | Gotcha |
|---|---|---|---|
| `disable-model-invocation` | `true` = only the user's `/name` runs it; the model can't auto-load it. Also blocks preloading into subagents. | Slash-only verbs with side effects (`/commit`, `/deploy`). | When `true`, the **description is not in context** — the model won't even know it exists; that's the point for action skills. |
| `user-invocable` | `false` = hide from the `/` menu; model-only background knowledge. | Reference skills that aren't a meaningful user command. | Controls *menu visibility only*, not Skill-tool access — use `disable-model-invocation` to block programmatic invocation. |
| `argument-hint` | Autocomplete placeholder for expected args (`[type]`, `[issue-number]`, `[filename] [format]`). | Every command that reads `$ARGUMENTS`. | Cosmetic — it does **not** validate; the body still must handle a missing/garbage arg. |
| `arguments` | Named positional args for `$name` substitution; space-separated string or YAML list, mapped by position. | Multi-arg skills wanting readable `$name` placeholders. | For a single positional value, `$ARGUMENTS` + `argument-hint` is simpler. |

## Execution context

| Field | What it does | When to use | Gotcha |
|---|---|---|---|
| `allowed-tools` | Pre-approves the listed tools (no per-use prompt) while the skill is active. Space- or comma-separated, scoped (`Bash(git status *)`). | Skills that should run their tools without prompting — **required** so the `` !`cmd` `` injections are permitted. | It *grants*, it does not *restrict*: every tool stays callable, governed by your permission settings. Project skills need workspace-trust acceptance first. |
| `disallowed-tools` | Removes tools from the pool while the skill is active (clears on your next message). | Autonomous/background skills that must never call e.g. `AskUserQuestion`. | Temporary — resets after one turn; for a permanent block use permission deny rules. |
| `model` | Pin the model while the skill is active (same values as `/model`, or `inherit`). | Cheap mechanical skills → `haiku`; deep review → `opus`. | Override lasts only for the current turn; the session model resumes next prompt. |
| `effort` | Reasoning-effort level while active (`low`/`medium`/`high`/`xhigh`/`max`). | Heavy-reasoning skills worth the latency. | Available levels depend on the model; higher = slower + more tokens. |
| `context` | `fork` runs the skill in a forked subagent; the body becomes that subagent's prompt. | Read-only investigation that should not pollute the main context. | The fork **has no conversation history** and only makes sense for skills with explicit task instructions — not for "guidelines" skills. See `forked-investigation.md`. |
| `agent` | Which subagent type executes a `context: fork` skill (`Explore`, `Plan`, `general-purpose`, or a custom agent). Defaults to `general-purpose`. | Pair with `context: fork`. | `Explore`/`Plan` skip CLAUDE.md + git status to stay small; pick them for lean investigation. The named agent must exist. |

## Dynamic content

| Field / syntax | What it does | When to use | Gotcha |
|---|---|---|---|
| `` !`<command>` `` (body) | **Preprocessing**: runs the command and replaces the placeholder with its stdout *before* the model sees the body. | Pull live context (`` !`git diff HEAD` ``, `` !`gh pr view` ``) so the model starts from facts. | Recognized only when `!` is at line start or after whitespace (`KEY=!` is literal). Substitution runs **once** (output isn't re-scanned). The command must be permitted by `allowed-tools`; keep output bounded; never inject secrets. Disabled by `disableSkillShellExecution`. |
| ` ```! ` fenced block | Multi-line form of the above for several commands. | When you need a few probes injected together. | Same rules as the inline form. |
| `shell` | Shell for `` !`cmd` `` execution: `bash` (default) or `powershell`. | Windows PowerShell injections. | `powershell` needs `CLAUDE_CODE_USE_POWERSHELL_TOOL=1`; rarely needed on WSL/Linux. |
| `hooks` | Pre/post hooks scoped to this skill's lifecycle only. | A skill that always needs setup/teardown (e.g. `git fetch` first). | Distinct from global `core/hooks/hooks.json` — these fire only for this skill. See `skill-hooks.md`. |

Useful substitutions in the body: `$ARGUMENTS`, `$ARGUMENTS[N]` / `$N`, declared
`$name`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, and `${CLAUDE_SKILL_DIR}`
(the skill's own directory — use it to reference bundled scripts).

## Auto-loading

| Field | What it does | When to use | Gotcha |
|---|---|---|---|
| `paths` | Glob list; the skill loads automatically only when the session touches a matching file. Comma-separated string or YAML list. | `domains/*` knowledge scoped to file types (`**/*.py`, `**/.github/**`). | Too-broad a glob auto-loads constantly (token cost). **Omit `paths` entirely** for tool/reference skills that should load on description match, not on every edit. |

```yaml
---
name: python
description: Generic Python engineering practices …
paths:
  - "**/*.py"
  - "**/pyproject.toml"
---
```

## This rig's conventions

- **Command-skills** (`core/skills/*`): `disable-model-invocation: true` +
  `argument-hint` when they read `$ARGUMENTS`. They are slash-only verbs. Seed
  them with `` !`cmd` `` injection (and a matching `allowed-tools` scope) when
  their first action is a deterministic read (`git status`, `gh pr diff`).
- **Domain skills** (`domains/*/SKILL.md`): `paths:`-scoped when the knowledge
  maps to a file type; **description-triggered (no `paths:`)** for tool/reference
  domains (serena, Playwright, OTel) that shouldn't reload on every source edit.
- **Agents** (`core/agents/*`): agents do **not** take `context`/`!`-injection
  (those are skill fields). Right-size cost with `model:`, give cross-session
  memory with `memory: user` (#27), and isolate writes with
  `isolation: worktree`. To run an agent in a forked context, invoke it from a
  skill with `context: fork` + `agent: <name>`.
- **`!` dynamic injection** requires a matching `allowed-tools` scope; keep the
  injected output bounded and never inject credentials.
