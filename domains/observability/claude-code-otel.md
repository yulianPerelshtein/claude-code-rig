# Claude Code native OpenTelemetry

Claude Code exports its own telemetry via OpenTelemetry (OTel): **metrics** as
time series, **events/logs**, and optionally **traces** (beta). This replaces any
bespoke usage parser — it's native, free, and standards-based. Adopted per
`SOTA_REFRESH.md §7` (item #24).

> Install-deferred: enable this on the machine/org you want to measure. The rig
> ships the config shape + this doc; turning it on is a user action.

## Enable (local console, zero backend)

The fastest way to see it working — metrics print to the console:

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=console
export OTEL_METRIC_EXPORT_INTERVAL=10000   # 10s while debugging (default 60s)
claude
```

## Enable (OTLP → a real backend)

Point it at a collector (Grafana/Prometheus/Honeycomb/etc.):

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
# auth if the collector needs it:
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <token>"
```

`OTEL_METRICS_EXPORTER` also accepts `prometheus` (scrape endpoint) and `none`.

### Persist it via settings (instead of shell exports)

Put the env block in `~/.claude/settings.json` so every session inherits it:

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
  }
}
```

## Metrics worth watching

| Metric | What it tells you |
|---|---|
| `claude_code.session.count` | Sessions started (`start_type`: fresh/resume/continue). |
| `claude_code.token.usage` | Tokens, split by `type` (input/output/cacheRead/cacheCreation) and `model`. The cache split is the headline efficiency signal. |
| `claude_code.cost.usage` | USD per request, by `model` / `query_source` (main/subagent/auxiliary). |
| `claude_code.lines_of_code.count` | Lines added/removed (`type`). |
| `claude_code.commit.count` / `claude_code.pull_request.count` | Commits / PRs created through the rig. |
| `claude_code.code_edit_tool.decision` | Edit/Write accept-vs-reject — a proxy for how often the model's edits land. |
| `claude_code.active_time.total` | Active (non-idle) seconds. |

Most metrics carry `session.id`, `model`, and (when authenticated) account
attributes; events add a `prompt.id` correlator.

## Privacy defaults (important)

Content logging is **off by default** and should usually stay off on a personal
rig:

- `OTEL_LOG_USER_PROMPTS` — logs prompt *text* (default off).
- `OTEL_LOG_TOOL_DETAILS` — logs Bash commands, tool input, MCP/skill names
  (default off).
- `OTEL_LOG_TOOL_CONTENT` / `OTEL_LOG_RAW_API_BODIES` — full tool I/O / full API
  bodies (default off; the latter includes the whole conversation).

Leave these off unless you own the backend and have a reason. Metrics +
counts give you the trends without shipping prompt content anywhere.

## Lightweight alternative: ccusage

For local cost/usage without standing up a collector, the community `ccusage`
CLI reads the on-disk transcripts:

```bash
npx ccusage@latest          # daily token/cost rollup from ~/.claude transcripts
```

Pair it with the rig's own `cost_tracker.py` Stop hook + the statusline for the
at-a-glance view; use OTel when you want history, dashboards, or org-wide
aggregation. In-session, `/cost` shows the current session's spend.

## See also

- `playbooks/observability/otel-insights-review.md` — the review cadence.
- `shareable/dashboard/` — the real-time statusline (rate_limits + cost).
- `core/hooks/stop/cost_tracker.py` — the per-session cost log this complements.
