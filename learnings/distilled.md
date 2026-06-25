# Distilled learnings

Cross-project operational patterns, sanitized. Each entry is a
`## YYYY-MM-DD CATEGORY` heading followed by a 1–3 line operational rule
(what/how only). In-depth write-ups live in the referenced `domains/` and
`playbooks/` docs; this file is the fast index.

Not auto-loaded on session start (see `core/context-architecture.md`). Pull
specific entries on demand or via a `load-learnings` skill.

---

## 2026-03-26 STATUSLINE-RATE-LIMITS-VIA-STDIN

Claude Code (v2.1.80+) passes `rate_limits.{five_hour,seven_day}.{used_percentage,resets_at}` on stdin to the statusline command. Use this instead of any OAuth usage beta endpoint. (Only present for Claude.ai Pro/Max/Team after the first API response.)

## 2026-03-26 BACKGROUND-TASK-POLLING

Do NOT chain sequential `sleep N && check` background tasks — it floods the notification queue. Use a single foreground sleep+check loop, or read the output file directly.

## 2026-03-26 BASH-HEREDOC-STDIN-PIPE-CONFLICT

`python3 - <<'EOF'` combined with a stdin pipe: the heredoc takes over stdin and the pipe is silently ignored. Fix: save the script to a `.py` file, then `echo "$INPUT" | python3 script.py`.

## 2026-03-26 STATUSLINE-MID-STREAM-TOKEN-SUPPRESSION

To avoid a flickering statusline during generation, keep a state file `{last_out, stable_out}`: if `current_out == last_out` generation stopped → advance `stable_out`; if different → still generating → keep `stable_out`. Always display `stable_out`. (Used by the statusline — `core/statusline/`.)

## 2026-03-19 POWERSHELL-LINE-CONTINUATION

Never use `^` or backtick continuation in PowerShell — a `--flag` at line start parses as a decrement. Use array splatting: `$a = @('--flag','val'); & exe @a`. See `playbooks/wsl/powershell-line-continuation.md`.

## 2026-04-05 WSL-HEREDOC-CRLF-PASTE

Do NOT hand a heredoc to the user as a paste-able WSL terminal command — clipboard CRLF causes `: command not found`. Write the content to a file and have the user run it. See `playbooks/wsl/paste-safety.md`.

## 2026-04-05 INVESTIGATE-BEFORE-FIX

Before writing a defensive fix, verify the issue reproduces across environments. If it's env-specific (e.g. dev-only data), confirm staging is clean first — the fix scope may change entirely. See `playbooks/investigation/investigate-before-fix.md`.

## 2026-04-07 ISOLATE-BEFORE-CONCLUDING

When a symptom has two plausible causes, isolate each independently before concluding. A combined test (A+B active) masks which one is responsible. See `playbooks/investigation/isolate-before-concluding.md`.

## 2026-04-07 DONT-ABANDON-WORKING-STATES

Commit and tag a working state before probing new features, so you can always return to a known-good baseline.

## 2026-04-09 COMMIT-BEFORE-PROBING

Commit the working state BEFORE starting a probe. The commit message must describe the known mechanism at commit time, not an inference made later.

## 2026-04-09 KEEPALIVE-MUST-RUN-AFTER-SUCCESS

In a long-running daemon, if the "ready" print + keep-alive read are in the error branch (`if not _wait_for_connected():`) instead of the `else:`, the process exits on success. Verify if/else structure when keep-alive must run after success.

## 2026-04-12 AWS-PROFILE-REQUIRED-FOR-BOTO3-AND-CLI

After `aws sso login --profile <profile>`, neither boto3 nor the AWS CLI picks up the profile automatically — set `AWS_PROFILE=<profile>` per shell or per command, else `UnrecognizedClientException` / invalid-token. See `domains/cloud-aws/sso-and-profiles.md`.

## 2026-04-12 RENAME-GREP-SCRIPTS-TOO

When renaming a symbol/field, grep ALL usages including shell scripts, not just source files. `scripts/` often hard-code names that tests won't catch. See `playbooks/refactoring/rename-grep-everything.md`.

## 2026-04-12 LINE-LENGTH-CHECK-NEW-STRINGS

Check max line length on any NEW strings — docstrings and comments are not exempt. CI catches what a local `--no-verify` bypasses. See `domains/python/ruff-and-formatting.md`.

## 2026-04-14 BRANCH-PREFLIGHT

Before creating a branch: `git fetch origin` → check `git log --oneline origin/main -10` → spot-check key files vs origin. Branching from a stale local main can duplicate already-merged work. See `domains/devops/git-conventions.md`.

## 2026-04-14 MINIMAL-CHANGES-POLICY

When porting code between branches, avoid renames/refactors beyond what the plan requires — incidental renames cascade into multi-file conflicts. If a name is in production and not targeted by the plan, leave it. See `playbooks/refactoring/minimal-changes-first.md`.

## 2026-04-14 NO-AGENT-FILES-IN-COMMITS

Never stage `.claude/` files (plans, memory, settings). Use explicit paths when staging — never `git add .` / `git add -A` on a repo with `.claude/` present. See `core/safety-rules.md`.

## 2026-04-14 OPTIONAL-DEPENDENCY-AND-PLATFORM-IMPORTS

Put OS-only or heavy-SDK imports inside the functions that need them (not module top). For module-level names that tests patch, use `try/except ImportError: name = None`. Makes the module importable (and testable) without the dependency installed. See `domains/python/optional-dependencies-and-platform-imports.md`.

## 2026-04-14 OS-MAKEDIRS-BREAKS-UNDER-PATCHED-EXISTS

`patch('os.path.exists', return_value=True)` breaks `os.makedirs` (it uses `exists` internally). Always `patch('os.makedirs')` alongside it. See `domains/testing-tdd/pytest-mocking.md`.

## 2026-04-14 MOCKOBJECT-IDENTITY-IN-ASSERTIONS

`assert_called_once_with(MagicMock(), ...)` always fails on the object arg — each `MagicMock()` is a distinct object. Capture the mock first, or assert specific positional args via `call_args[0][N]`.

## 2026-04-14 MOCK-AS-CONTEXT-MANAGER

A `MagicMock()` used as a context manager returns `__enter__.return_value` (a new mock), not itself. For `with urlopen(...) as resp:`, set `resp.__enter__ = MagicMock(return_value=resp)`.

## 2026-04-15 BRANCH-EXTRACTION-VERIFY-BASE-FIRST

Before extracting a feature branch, verify the target branch's HEAD and history — don't assume what's "missing". Check `git log origin/main` first.

## 2026-04-15 SCOPE-MISMATCH-ASK-NOT-ASSUME

When told "get X through", don't assume X is what you're currently on. Clarify: foundational work (already done, needs merging) vs new work. See `playbooks/investigation/scope-mismatch-ask.md`.

## 2026-04-16 PR-CLEANLINESS

Keep every commit formatting-clean as written. Before committing, verify `git diff main -- <file>` shows zero blank-line whitespace noise. Never mix trailing-whitespace removal with logic changes. See `domains/devops/pr-cleanliness.md`.

## 2026-04-16 FORMATTER-COLLAPSES-MULTILINE

An auto-formatter run on save will collapse any multi-line expression that fits the line-length limit and rewrite chained `with a, b:` to a newer-syntax form (can break older-Python CI). Preserve multi-line style with magic trailing commas, or bypass the on-save formatter. See `domains/python/ruff-and-formatting.md`.

## 2026-04-16 TRAILING-WHITESPACE-RESTORE-TECHNIQUE

To strip blank-line noise from a PR without a rebase: `git show main:<file> > /tmp/baseline`, apply only semantic changes (from `git diff -w main..HEAD`) via a script, write back. Result: main's formatting + only real changes. See `domains/devops/pr-cleanliness.md`.

## 2026-04-26 CHECK-SCRIPTS-DIR-FIRST

Before creating a new local conversion/run script, check the project's `scripts/` for the canonical entry — it usually already exists.

## 2026-04-28 BLANK-LINE-NOISE-IS-BIDIRECTIONAL

Trailing-whitespace blank lines create diff noise in both directions (stripping shows a removed-blank line; restoring shows an added-blank line). The fix is the baseline technique, not ad-hoc edits. See `domains/devops/pr-cleanliness.md`.

## 2026-04-28 CHERRY-PICK-LAYERED-PRS

When rebasing layered PRs onto a main that already has earlier PRs, resolve conflicts by combining both sides (cherry-picked intent + fixes already landed). Never blindly take one side — ask what the correct final state is given all landed changes. See `playbooks/refactoring/cherry-pick-layered-prs.md`.

## 2026-05-03 STALE-PROCESS-BEFORE-DEBUGGING-API

When an API response doesn't match the code on disk, check for a stale server process before debugging code (`ps aux | grep uvicorn`). A previous session may be serving old code. See `playbooks/debugging/stale-process-check.md`.

## 2026-05-06 GH-PR-EDIT-BODY-USE-REST-NOT-CLI

`gh pr edit --body` can silently fail to update a PR body on some org configs (exits 0 with a deprecation message). Use the REST API first: `gh api -X PATCH repos/<owner>/<repo>/pulls/<n> --input p.json`. Verify via `--jq`, never trust exit code alone. See `domains/devops/github-cli.md`.

## 2026-05-06 AI-REVIEW-SKEPTICISM

Apply critical thinking to AI/Copilot PR comments — many are stale-description nits needing zero code change. Verify each against the codebase and runtime behaviour before applying. See `playbooks/code-review/ai-review-skepticism.md`.

## 2026-05-06 MULTI-AGENT-PARALLEL-REPO-ANALYSIS

Spawning many independent sub-agents for breadth-pass analysis works reliably: each reads one target, writes its output file incrementally, returns a one-paragraph summary; no cross-agent chatter; main session synthesizes. See `playbooks/ai-assisted-coding/parallel-agent-fan-out.md`.

## 2026-05-06 AGENT-INCREMENTAL-WRITE-RESILIENCE

Agent timeouts (sleep/network) lose all work if findings are buffered to the end. Every agent prompt must say: "write the output file after your first 2–3 steps, then append." Not a tool-call cap — the real issue is end-buffering.

## 2026-05-06 SHALLOW-AGENT-ANALYSIS-BLIND-SPOTS

Analysis agents reliably read README/routes/models/manifests but miss the primary service/business-logic file, utility modules, test edge cases, and migration history. Name the service file explicitly in the prompt.

## 2026-05-06 SECRET-SCAN-DESKTOP-ADDIN-REPOS

When reviewing C# desktop-app integration / vendor-tool add-in repos, grep for keys in `Constants/*ApiKeys*`, `requirements.txt` `git+https://<PAT>@`, and `config.yaml` SaaS tokens — these predate secrets management. See `playbooks/security/secret-scanning-patterns.md`.

## 2026-05-06 KB-BUILDER-AGENT-PROMPT-STRUCTURE

Effective repo-KB agent prompt: path+branch+1-line domain → "write after first 2–3 steps" → numbered exploration with an explicit early write → output path → exact markdown template → index-append → "return one-paragraph summary". Omitting the template yields inconsistent output. See `playbooks/ai-assisted-coding/kb-builder.md`.

## 2026-05-12 LAZY-LLM-SDK-IMPORT

When the LLM provider is still in flux, import the SDK inside the function (not module top) and return a 503 if the key/SDK is missing. Module loads cleanly without the dep; CI without the dep still passes. See `domains/ai-assisted-coding/llm-sdk-deferral.md`.

## 2026-05-12 GROK-VIA-OPENAI-COMPATIBLE-CLIENT

xAI/Grok exposes an OpenAI-compatible API at `https://api.x.ai/v1`. Use the `openai` package with `base_url` override (env `XAI_API_KEY`), not a bespoke SDK. Keep `LLM_BASE_URL`/`LLM_MODEL` overridable for portability. See `domains/ai-assisted-coding/grok-via-openai-shape.md`.

## 2026-05-12 CI-LLM-KEY-EMPTY-STRING-DEFENSE

Beyond per-test `monkeypatch.delenv`, set the key to `""` in the CI job's `env:` block — defends against a future test forgetting to mock, a dropped monkeypatch, or CI depending on a live third-party service. See `domains/devops/ci-llm-key-defense.md`.

## 2026-05-12 LLM-AS-JUDGE-PARSER-CALLER-SPLIT

Split the JSON parsing from the LLM call: a pure `_parse_*(raw) -> ...` (testable against canned outputs, all fail-open cases) and a `grade_*()` that does env/SDK/request then calls the parser. Live-LLM eval belongs in a separate harness, not unit tests. See `domains/testing-tdd/ai-judge-parser-caller-split.md`.

## 2026-05-12 LOAD-DOTENV-BEFORE-MODULE-IMPORTS

`load_dotenv()` must run BEFORE importing app modules that read env vars at import time. Order: `from dotenv import load_dotenv; load_dotenv()` then the app imports with `# noqa: E402`. No-op in prod (env injected directly). See `domains/ai-assisted-coding/load-dotenv-ordering.md`.

## 2026-05-24 RULE-FIRES-FOR-ONE-IS-SUSPECT

A rule whose edge-case path fires for ~1 legitimate real-world element across the whole corpus is probably too strict — prefer a symmetric catch-all + a flag over an "unassigned" bucket. Test on real data before declaring a rule correct. See `playbooks/investigation/rule-fires-for-one-is-suspect.md`.

## 2026-05-24 BRIEF-CONSTRAINTS-OVER-METRIC-IMPROVEMENT

When the brief forbids using source X for an output, don't loosen the constraint to improve an internal metric. Ship the brief-faithful pipeline + a diagnostic that surfaces the divergence; explain the trade-off. See `playbooks/investigation/brief-constraints-over-metrics.md`.

## 2026-05-24 SKIP-EMPTY-BY-DESIGN-DIAGNOSTICS

If you know the data can't support a diagnostic (denominator is always empty), don't implement it — document it under "alternatives considered". Empty diagnostics are noise. See `playbooks/investigation/skip-empty-diagnostics.md`.

## 2026-05-24 FLOAT-EQUALITY-FOR-DUPLICATE-DETECTION-IS-A-BUG

Never use `==` to detect duplicate floats — authoring tools emit noise like `2999.9999999` for `3000.0`. Use `abs(a-b) < tolerance` with a named, unit-meaningful threshold (e.g. 1mm), not `1e-9`. See `domains/python/numerics-and-tolerances.md`.

## 2026-05-24 SIGNED-DIRECTION-OVER-ABS-FOR-INVARIANTS

When a value has an invariant sign given its caller, encode direction as a `±1` multiplier, not `abs()`. `abs()` masks a future caller-side wrong-sign bug; a sign multiplier surfaces it as a negative output. See `domains/python/defensive-vs-revealing-code.md`.

## 2026-05-24 SAME-FALLBACK-FORMULA-IN-PARALLEL-PIPELINES

When two independent traversals render the same logical entity, both must use the IDENTICAL fallback for missing values, else the same entity gets different labels → spurious cross-pipeline disagreements. Applies to display, comparison, JSON, log lines. See `playbooks/data-engineering/cross-pipeline-fallback-consistency.md`.

## 2026-04-15 CACHE-INVALIDATION-AFTER-BUG-FIX

Generated/cached files survive a fix to their producer — rotate the cache key (work-dir / job-id / version) after fixing a generator bug, or the stale output is silently reused. Applies to sidecars, build artefacts, generated code, fixture caches, archive extracts, Docker layers. See `playbooks/debugging/cache-invalidation-after-bug-fix.md`.

## 2026-04-15 IMPORT-TIME-SIDE-EFFECTS-FAIL-SILENTLY

Module-import-time file-existence checks fail silently (a missing asset becomes an empty default, producing wrong output with no error). Use an env var or explicit validation; repo-relative asset paths are fragile. See `domains/python/import-time-side-effects.md`.

## 2026-06-09 EVENTBRIDGE-VALIDATE-PATTERN-BEFORE-DEPLOY

Validate a non-trivial EventBridge `EventPattern` offline before deploy: `aws events test-event-pattern` with one positive (→true) and one negative (→false) event. Catches filter typos before the CI cycle. See `domains/cloud-aws/eventbridge-patterns.md`.

## 2026-06-09 CFN-RULE-NEEDS-EXPLICIT-DEPENDSON-LOGS-POLICY

A CFN `Events::Rule` does NOT implicitly depend on a sibling `Logs::ResourcePolicy` (dependency inference only follows Ref/GetAtt/Sub). On first deploy they create in parallel; events in the gap get AccessDenied and drop. Add explicit `DependsOn`. See `domains/cloud-aws/cloudformation.md`.

## 2026-06-10 PROFILE-BEFORE-PREDICTING-MEMORY-WINS

Before a refactor predicted to deliver a large memory reduction (>2×), profile FIRST to find where memory actually lives — the working set may be irreducible output data, not the thing you planned to stream. See `playbooks/debugging/profile-before-predicting.md`.

## 2026-06-10 TRACEMALLOC-CHECKPOINT-PATTERN

For peak-memory profiling at a specific execution point: `tracemalloc.start(25)` before heavy imports, monkey-patch the existing checkpoint/log fn to dump a snapshot at the target phase (top sites by file:line, top live types, RSS minus traced = C-side estimate). `sys.getsizeof` excludes C-side buffers — pair with allocation sites. See `domains/python/debugging-tracemalloc.md`.
