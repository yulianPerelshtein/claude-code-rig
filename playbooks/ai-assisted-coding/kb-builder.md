# KB-builder agent workflow

To build a per-repo knowledge-base file with an agent, give it (in order):

1. Repo path + branch + commit + a one-sentence domain context.
2. "Write the output file after your first 2–3 exploration steps, then append."
3. A numbered exploration sequence with an explicit "write initial file now" at
   step 3–4.
4. The exact output file path.
5. The exact markdown **template** (section headers) to follow — this is the
   highest-leverage part; omitting it yields inconsistent output.
6. Index-append instructions (api-index / event-index).
7. "Return a one-paragraph summary when done."

Rule/fact: `domains/ai-assisted-coding/kb-builder-prompts.md`. For multi-repo
breadth passes, combine with `parallel-agent-fan-out.md`.
