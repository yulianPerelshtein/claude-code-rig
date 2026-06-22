# Windows-filesystem isolation (WSL)

- All work stays on the Linux filesystem. Never read or write the Windows
  drive mount (the `/mnt/<drive>/` path) from WSL.
- Never use Windows-style paths in WSL commands.
- When the same repo is checked out on both WSL and Windows, treat them as two
  independent clones of the same remote: push from one, `git fetch && git
  checkout` on the other. Never hand-copy files between them.
- Combine with the baseline technique (`domains/devops/pr-cleanliness.md`) when
  a cross-checkout edit risks introducing blank-line/whitespace noise.
