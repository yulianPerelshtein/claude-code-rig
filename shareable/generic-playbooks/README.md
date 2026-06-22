# Generic playbooks

A portable subset of cross-project operational patterns. Each is a short,
vendor-neutral rule you can drop into any Claude Code setup or read as a
standalone note.

| Playbook | Gist |
|---|---|
| `wsl-paste-safety.md` | Never hand a heredoc to a WSL terminal — write a file and run it. |
| `ruff-trailing-whitespace-baseline.md` | Keep commits formatting-clean; the baseline technique for stripping whitespace noise; lint don't reformat. |
| `parallel-agent-orchestration.md` | Fan out independent sub-agents for breadth analysis; early-write + name the key file. |
| `ai-as-judge-testing.md` | Split the parser from the LLM call so judging logic is unit-testable. |
| `llm-sdk-deferral.md` | Lazy-import the LLM SDK; empty-string the key in CI; `load_dotenv` ordering. |
| `gh-pr-edit-via-rest.md` | `gh pr edit --body` can silently no-op; PATCH via REST and verify. |
| `aws-profile-sso.md` | After `aws sso login`, set `AWS_PROFILE` or boto3/CLI won't see it. |

MIT-licensed (see the bundle's top-level `LICENSE`).
