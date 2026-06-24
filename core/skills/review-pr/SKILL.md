---
name: review-pr
description: Code review a pull request, focused on the diff only
disable-model-invocation: true
allowed-tools: Bash(gh issue view:*), Bash(gh search:*), Bash(gh issue list:*), Bash(gh pr diff:*), Bash(gh pr view:*), Bash(gh pr list:*), Bash(gh repo set-default:*), Bash(git log:*), Bash(git blame:*)
---

Review the PR diff only — do not flag issues outside changed lines.

**Review-only by default.** This skill renders the review for the human to read.
It never posts to GitHub on its own — posting requires an explicit per-invocation
confirmation (step 9). `gh pr comment` is intentionally NOT pre-authorized in
`allowed-tools`, so any post triggers a normal permission prompt as a backstop.

## Changed files in the current PR

!`gh pr diff --name-only 2>/dev/null`

The list above (when non-empty) scopes every reviewer agent to the changed
files. If it is empty, the branch has no associated PR; rely on step 3's
`gh pr view` instead.

0. Remote-resolution preflight: confirm the PR actually resolves before doing
   any work. Run `gh repo set-default --view 2>/dev/null` (or `gh pr view --json number -q .number 2>/dev/null`). If it errors or returns empty, STOP and tell the user the PR could not be resolved — most likely a renamed/stale `origin` remote — and ask them to run `gh repo set-default` or pass an explicit `--repo owner/name`. Do NOT guess a repository.

1. Haiku agent — eligibility check: (a) closed, (b) draft, (c) trivially simple/automated, (d) already reviewed by you. If any true, stop.

2. Haiku agent — locate CLAUDE.md files: root + any in directories with modified files.

3. Haiku agent — view PR, return concise summary.

4. Launch 6 parallel Sonnet agents. Each returns: file:line, issue description, reason flagged:

   **Agent 1 — CLAUDE.md compliance**: Verify diff adheres to explicit CLAUDE.md rules (type hints, no trailing whitespace, PEP-8, no Windows-filesystem paths under the WSL `/mnt` drive mounts). Only flag direct violations — not general style opinions. Also flag design-principles violations from domains/software-design/clean-code.md: single-responsibility breaches, mixed abstraction levels, the wrong abstraction, and missing dependency injection. Do NOT flag mechanical limits (length/args/complexity) — CI's Ruff gate owns those.

   **Agent 2 — Bug scan**: Shallow scan changed lines only. Flag: logic errors, null/undefined handling, off-by-one, boolean logic, broken control flow, missing return values, API misuse, needless complexity / over-engineering a YAGNI ladder would have avoided (judgment, not the mechanical Ruff limits). Ignore pre-existing issues and nitpicks a senior engineer would not raise.

   **Agent 3 — Historical context**: Read git blame and recent log for modified files. Flag bugs only apparent from history (e.g. revert reintroducing known bug, change breaking prior contract).

   **Agent 4 — Repeat patterns from past PRs**: Read past PRs touching same files. Check if prior review comments apply to current diff.

   **Agent 5 — In-code guidance compliance**: Read comments/docstrings in modified files. Flag changes violating in-code guidance (e.g. "do not call from async context", "must be called after X").

   **Agent 6 — Security and stack-specific patterns**: Only flag issues visible in the diff:

   *Security:*
   - Hard-coded credentials, tokens, secrets, or API keys
   - Missing auth checks on protected endpoints
   - SQL string concatenation (not parameterized)
   - Missing input validation on user-provided data
   - Sensitive data (passwords, tokens) in logs or error messages
   - Overly permissive or missing CORS on new endpoints

   *Python / FastAPI:*
   - Bare `except:` or `except Exception:` without re-raise
   - Blocking calls (`requests`, `time.sleep`) inside `async def` — use `asyncio.to_thread`
   - Missing Pydantic validation on user-input request fields
   - DB sessions not closed or missing context manager
   - Missing try/except + rollback around DB write transactions

   *React / TypeScript:*
   - `useEffect` with missing/incorrect dependency array
   - `innerHTML` assignment without sanitization (XSS)
   - Missing error boundary around data-fetching components

   *General performance:*
   - N+1 query patterns (loop issuing DB query per iteration)
   - Unbounded in-memory accumulation inside loops

5. Haiku agent — deduplicate across the 6 reviewers BEFORE scoring. The agents have overlapping mandates (e.g. Agents 1, 2 and 6 can each flag the same line), so the same defect often surfaces 2–3×. Group findings by (file, nearest line, root cause). For each cluster, keep ONE canonical finding, union the distinct "reason flagged" tags, and carry forward the highest-severity framing. Emit the deduplicated set to scoring.

6. For each deduplicated issue, parallel Haiku agents score 0–100 (give rubric verbatim to agents):
   - **0**: False positive or pre-existing issue not introduced by this diff
   - **25**: Unverified or stylistic (not explicitly in CLAUDE.md)
   - **50**: Real but minor — unlikely to be hit in practice
   - **75**: Verified real, will be hit, directly impacts functionality or explicitly in CLAUDE.md
   - **100**: Confirmed, will happen frequently, direct evidence

7. Discard issues with confidence < 80. If nothing remains, do not proceed.

8. Haiku agent — re-run eligibility check from step 1.

9. Render the review to the USER as text (do NOT post). Use this format exactly:

   ```text
   ### Code review

   Found N issues:

   1. <brief description> (<reason: CLAUDE.md rule / security / bug / historical context>)

   <https://github.com/owner/repo/blob/FULL_SHA/path/to/file#L10-L14>

   2. ...

   <sub>If this review was useful, react 👍. Otherwise react 👎.</sub>
   ```

   Or if no issues passed the confidence threshold:

   ```text
   ### Code review

   No issues found. Checked for bugs, CLAUDE.md compliance, security red flags, and stack-specific patterns.
   ```

10. Confirmation gate before any post. After rendering the review, ask the user exactly: **"Post this as a PR comment via `gh pr comment`? (yes/no)"**. Only on an explicit affirmative reply, run `gh pr comment` with the rendered body (this will prompt for permission, since `gh pr comment` is not pre-authorized — that is intended). On anything other than an explicit yes, stop without posting; the rendered review above is the deliverable.

**False positives — do not flag:**

- Pre-existing issues not touched by the diff
- CI-catchable issues (linter, type checker) — assume CI runs
- Lint-suppressed lines (`# noqa`, `// eslint-disable`)
- Nitpicks; coverage/docs gaps (unless CLAUDE.md requires); intentional changes within PR scope

**Notes:**

- Use `gh` for all GitHub interactions; never web fetch for GitHub URLs
- Links: full git SHA only, not HEAD/branch. Format: `https://github.com/owner/repo/blob/SHA/path#L5-L9`
