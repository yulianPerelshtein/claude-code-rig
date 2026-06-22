# KB-builder agent prompt structure

An effective prompt for an agent that builds a per-repo knowledge-base file:

1. Repo path + branch + commit + a one-sentence domain context.
2. **Critical instruction**: "write the output file after your first 2–3
   exploration steps; then append" (resilience — see
   `parallel-agent-orchestration.md`).
3. A numbered exploration sequence with an explicit "write initial file now" at
   step 3–4.
4. The exact output file path.
5. The exact markdown template (section headers) the file must follow.
6. Index-append instructions (e.g. append to an api-index / event-index).
7. "Return a one-paragraph summary when done."

Agents that omit the template (step 5) produce inconsistent output that needs
post-processing. The template is the single highest-leverage part of the prompt.
