---
name: observability
description: >-
  Quantitative observability for Claude Code itself — native OpenTelemetry
  metrics/logs, the in-session /cost view, and the ccusage CLI. Use when setting
  up telemetry, reviewing usage/cost trends, or wiring a metrics backend.
---

# observability

How to see what the rig is actually doing — tokens, cost, sessions, tool
activity — quantitatively, over time. Read `claude-code-otel.md` for the native
OpenTelemetry setup and `playbooks/observability/otel-insights-review.md` for the
review cadence.

This is the **quantitative** half of the continuous-improvement loop (the
qualitative half is the dream loop + `/wrap-up`). It is install-deferred: enable
telemetry on the machine you want to measure; the rig ships the config + docs.
