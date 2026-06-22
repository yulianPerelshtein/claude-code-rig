# TOON output format

A compact tabular encoding for structured data a skill returns: one header row +
positional tuples, instead of repeating JSON keys on every record. Pattern only —
borrowed from the Coralogix CLI write-up; **skip the CLI** (commercial, paywalled
backend). See `ENHANCEMENTS_BACKLOG.md §4.5` (#14, Tier 3).

## The corrected number (read this first)

The source claims **~90%** token reduction over JSON. That is **overstated**
(`SOTA_REFRESH.md §5.6 / §7`). The real benefit is **~40%, and only on uniform
tabular arrays** — many records with identical keys. For other shapes it loses:

- **Flat tables:** plain **CSV is smaller** than TOON — use CSV.
- **Nested / irregular data:** **compact JSON wins** — use JSON.
- **Uniform array of flat objects, many rows:** TOON's ~40% applies.

So TOON is a **narrow** tool, not a default. Don't reformat everything into it.

## Shape

```text
# JSON (keys repeat every row):
[{"id":1,"name":"a","ok":true},{"id":2,"name":"b","ok":false}]

# TOON (header once, then tuples):
id,name,ok
1,a,true
2,b,false
```

The win comes purely from not repeating keys; it grows with row count and
shrinks to nothing (or negative) for few rows or nested values.

## When to use it (and not)

| Data | Use |
|---|---|
| Many rows, identical flat keys, returned to the model | **TOON** (~40%) |
| Flat table, few/simple columns | **CSV** (smaller than TOON) |
| Nested, optional, or irregular fields | **compact JSON** |
| A handful of records | don't bother — overhead > savings |

Use it for a **skill's own large structured output** (e.g. a report of N findings
with uniform fields), implemented standalone — never depend on Coralogix.

## See also

- `core/skill-frontmatter-reference.md` — output-format design (this is one tip).
- `core/context-budget-policy.md` — native token reduction first.
- `domains/context-engineering/headroom.md` — the input-side compression lever (opt-in).
