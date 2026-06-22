# Parallel-agent orchestration (breadth pass)

Workflow for analyzing many targets (repos, modules, docs) at once with a fleet
of independent sub-agents.

1. **Brief** each agent identically: target path + one-line context, the output
   file path, an exact markdown template, and "return a one-paragraph summary".
2. **Resilience clause** (mandatory): "write the output file after your first
   2–3 exploration steps, then append." This survives timeouts (sleep/network)
   — buffering to the end loses all work.
3. **Independence**: no cross-agent communication. The main session synthesizes
   after all return.
4. **Name the key file** in the prompt — agents otherwise miss the primary
   business-logic file, utility modules, test edge cases, and migrations.
5. **Sizing**: under ~2000 files → single-agent pass; larger → hub-and-spoke
   (a cartographer agent plus API / data / patterns / testing agents).

The two failure modes that actually bite: end-buffering (fixed by the early-write
clause) and shallow reads (fixed by naming the service file explicitly).
