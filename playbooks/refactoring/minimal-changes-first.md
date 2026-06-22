# Minimal changes first

When porting code between branches or implementing a scoped plan, avoid renames
or refactors beyond what the plan explicitly requires.

- An incidental rename (e.g. `camera_name_to_filesystem_safe` →
  `camera_name_to_safe`) can cascade into conflicts across several files and
  have to be fully reverted.
- If an existing name is in production and not targeted by the plan, **leave
  it**.
- Keep the diff to the lines the change actually needs (see
  `domains/devops/pr-cleanliness.md`).

Opportunistic cleanups go in a separate, clearly-labelled commit — never mixed
into a functional change.
