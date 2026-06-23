# The revise-later parking lot

A deferred-learning log: when something you don't fully understand surfaces
mid-task, you write it down and keep moving instead of either (a) stalling the
task to research it now, or (b) losing the question entirely. It protects
momentum without sacrificing rigor.

## What goes in it

Anything you used but couldn't yet explain, or a decision you made on intuition
and want to verify later: an unfamiliar library's actual behaviour, why a
default works, a packaging concept you leaned on, a perf claim you assumed. The
discipline is to capture the *question* with enough context to answer it later —
not to answer it now.

## Each entry: context + question, answer added inline later

```text
### <topic>
Context: <where it came up, why it mattered to the task>
Question: <what you want to understand>

(later, when researched, the answer is written in directly underneath)
```

Answering inline (rather than in a separate doc) means the log doubles as a
study record: the context that triggered the question sits right next to its
resolution. Entries you've answered can move to a "Resolved" section; the open
ones are your reading list.

## Why this beats the alternatives

- **vs. researching immediately:** a deep dive mid-implementation blows the
  task's focus and often the context window. The parking lot defers the cost to
  a time you choose.
- **vs. a mental note:** questions you don't write down are gone by the next
  context clear. The log is durable across sessions.
- **vs. a TODO comment in code:** these are *learning* questions, not work
  items; they don't belong in tracked source, and they carry more context than a
  one-line comment holds.

Keep it gitignored alongside the other working notes — it records what you
didn't know, which is private by nature. See `project-conventions.md`.
