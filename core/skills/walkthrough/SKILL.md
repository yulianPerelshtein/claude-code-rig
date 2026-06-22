---
name: walkthrough
description: Interactive section-by-section code walkthrough for learning sessions
disable-model-invocation: true
argument-hint: "[file]"
---

Walk through the file specified in the argument (or the file currently under discussion) as an interactive learning session.

Follow these steps precisely:

1. Read the target file if not already in context.

2. **Orientation** — Write a 3-sentence summary:
   - What this file does
   - Where it fits in the broader system
   - What the key challenge or interesting problem it solves

3. **Map** — List all logical sections of the file with their line ranges (e.g. imports, public functions, private helpers). Number them. Tell the user: "We'll go through each in order. Say 'next' to advance, or ask a question at any point."

4. **Section loop** — For the current section:
   - State the section name and line range as a header
   - Explain line by line (or group logically related lines), always referencing line numbers like `L10` or `L22–28`
   - On first use of any library-specific API or non-obvious concept, give a one-line definition in plain language
   - At the end of the section, note how it connects to other sections (e.g. "This result is consumed by the function at L89")
   - End with: "Ready for the next section, or want to go deeper on anything here?"

5. On each user response:
   - If they say "next" / "continue" / similar → advance to the next section and repeat step 4
   - If they ask a question → answer it with line references, then ask if they want to continue or dig further
   - If they ask to go deeper on a specific line or concept → zoom in, explain in full detail, then offer to continue
   - If all sections are done → write a 2-sentence closing summary tying everything together

Rules:

- Never dump more than one section per response
- Always cite line numbers (use `L<n>` or `L<n>–<m>` format inline in prose)
- Explain *why* a pattern was chosen, not just *what* it does, when that context is available from the code or docstrings
- Keep language plain — define jargon on first use
- Do not offer to refactor or improve the code; this is a read-only learning session
