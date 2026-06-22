# A/B testing skills

Editing a prompt and *feeling* it improved is not evidence. For high-leverage
skills, measure the change. Claude Code ships the measurement loop natively via
the `skill-creator` plugin — use it instead of a hand-rolled harness.

## When to bother

A/B measurement has real overhead (tokens + time). Reserve it for:

- **High-frequency** skills (run many times a week).
- **High-leverage** skills where a wrong output is expensive (review, commit,
  eval-spec, the verification council).

For a one-off or rarely-used skill, a careful read against the checklist is
enough.

## The native loop (`skill-creator`)

Install once from the official marketplace:

```text
/plugin install skill-creator@claude-plugins-official
/reload-plugins
```

Then ask Claude to evaluate the skill (e.g. *"evaluate my review-pr skill with
skill-creator"*). It:

- Stores test cases (prompts, input files, expected behavior) in
  `evals/evals.json` inside the skill directory.
- Spawns a **subagent per test case** so each run starts from a clean context;
  records token count and duration.
- Grades each assertion (pass/fail with evidence) to `grading.json`.
- Aggregates with-skill vs without-skill pass rate, time, and tokens into
  `benchmark.json` — so you weigh the pass-rate gain against the overhead.
- Runs a **blind A/B between two versions** so you can confirm an edit is an
  improvement *before* committing it.
- Tunes the `description`: generates should-trigger / should-not-trigger
  prompts, measures hit rate, and proposes description edits when the skill
  fires on the wrong requests.

## Measure two things separately

1. **Triggering** — does the model invoke the skill on the prompts it should
   (and not on the ones it shouldn't)? This is a `description` problem.
2. **Output quality** — when it does run, does the output match the expectation?
   This is a body problem.

A skill can trigger perfectly and still produce poor output, or produce great
output but rarely trigger. Don't conflate them.

## Fresh-session discipline

Always compare in a **fresh session**. Leftover context from authoring the skill
masks gaps in the written instructions — the skill looks like it works because
*you* primed the context, not because the prompt carries the load.

## Rig-local fallback (no plugin)

If you can't install the plugin, approximate manually: pick 3–5 realistic
prompts, run each in a fresh session with the skill and again with it disabled
(`skillOverrides: {"<name>": "off"}` in `.claude/settings.local.json`), and
compare outputs by hand. Cruder, but still a baseline comparison rather than a
guess.

## See also

- `playbooks/prompt-optimization/prompt-checklist.md` — what to change.
- `core/skills/eval-spec/SKILL.md` — evaluation discipline for AI *features*
  (a different target than skill prompts, same evidence-over-vibes principle).
