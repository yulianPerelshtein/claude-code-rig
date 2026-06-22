# Parallel-agent fan-out (breadth pass)

Workflow for analyzing many targets (repos, modules, docs) at once.

1. **Brief** each agent identically: target path + one-line context, the output
   file path, an exact markdown template, and "return a one-paragraph summary".
2. **Resilience clause** (mandatory): "write the output file after your first
   2–3 exploration steps, then append." This survives timeouts (sleep/network)
   — buffering to the end loses all work.
3. **Independence**: no cross-agent communication. The main session synthesizes
   after all return.
4. **Name the service file** in the prompt — agents otherwise miss the primary
   business-logic file, utils, test edge cases, and migrations.
5. **Sizing**: <~2000 files → single-agent pass; larger → hub-and-spoke
   (cartographer + API + data + patterns + testing agents).

Rule/fact: `domains/ai-assisted-coding/parallel-agent-orchestration.md`.
