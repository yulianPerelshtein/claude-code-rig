# Wrap Claude Code with headroom

The workflow for evaluating and (if it proves out) running the **opt-in**
headroom compression layer. Read `domains/context-engineering/headroom.md` for
the caveats first — especially the undetermined data-egress posture and the
realistic ~47% (not 60–95%) on codebase work.

> This is a **deferred user action** on the personal laptop, not something the
> installer turns on.

## Three integration modes (least → most invasive)

| Mode | Command | When |
|---|---|---|
| **wrap** | `headroom wrap claude` | First test. One command, fully reversible. |
| **MCP** | `headroom mcp install` | After wrap proves savings; exposes compress/retrieve as tools to any skill. |
| **proxy** | OpenAI-compatible HTTP proxy | Only if you need language-agnostic interception. Deferred. |

Start at **wrap**. Don't jump to proxy.

## A/B methodology

You can't trust a vibe — measure. Run the *same* representative task twice:

1. **Baseline:** plain `claude`, a scripted codebase-exploration session (open N
   files, ask the same M questions). Record tokens via `/cost` (or
   `npx ccusage@latest` afterwards) and wall-clock.
2. **Wrapped:** `headroom wrap claude`, identical session. Record the same.
3. **Compare:** compute the token delta. Accept only if **≥30% reduction on this
   codebase workload** AND output quality is unchanged (no lost context, no
   wrong answers from dropped content).
4. **Repeat across ≥1 week** of real work before trusting it daily — a single
   session is noise.

## Safety checklist before daily use

- [ ] Verified no phone-home (prompts / compressed summaries not sent upstream);
      `Kompress-v2-base` fetched once; offline flag set if available.
- [ ] Measured local compressor CPU/RAM; acceptable on the laptop.
- [ ] Confirmed no data-loss on a code task (diff the wrapped vs unwrapped answer
      on something you can verify).
- [ ] Installed via `pipx` (isolated env), not bare `pip`.
- [ ] `headroom learn` left **disabled** (don't let it compete with
      `learnings/distilled.md`).

## Rolling back

`unalias claude` (or close the wrap) + `pipx uninstall headroom-ai`. The rig's
own hooks/skills are unaffected — headroom is purely an interception layer.

## See also

- `domains/context-engineering/headroom.md` — evaluation summary + caveats.
- `domains/context-engineering/native-context-levers.md` — native reduction to try before any wrapper.
- `playbooks/observability/otel-insights-review.md` — measure the cache/cost
  impact over time.
