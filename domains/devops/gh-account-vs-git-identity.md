# `gh`'s account is not git's identity

The `gh` CLI authenticates as **one active account**. Git authenticates
separately — typically per-directory, via an SSH host alias in `~/.ssh/config`:

```sshconfig
Host github-personal
  HostName github.com
  IdentityFile ~/.ssh/id_personal
```

```bash
git remote -v      # git@github-personal:me/private-repo.git  -> personal key
gh auth status     # Logged in to github.com account work-account  -> different
```

These can disagree, and usually should: one account is the default everywhere
while another covers a single tree.

## The symptom that looks like a bug

```console
$ gh repo view me/private-repo
GraphQL: Could not resolve to a Repository with the name 'me/private-repo'.
```

The repo exists and `git push` to it works. `gh` simply cannot see a private
repo owned by an account it is not authenticated as. **That is the expected
symptom of correct routing, not a fault** — verify with git rather than `gh`:

```bash
git ls-remote --heads origin        # resolves -> the repo is fine
git rev-list --count origin/main..HEAD   # and you can see its refs
```

## Do not "fix" it with `gh auth switch`

`gh auth switch` changes the active account **globally**, not for the current
directory. Running it to make one lookup succeed silently repoints every later
`gh` call — PR creation, review, issue lookup — at the wrong account, in every
repo. The failed lookup costs nothing; the switch costs correctness everywhere
until someone notices.

If a script genuinely needs `gh` against the other account, scope it to that
invocation (`GH_TOKEN=...`) rather than mutating global state. And when a plan
or runbook instructs an `auth switch` as a precondition, treat that as a bug in
the runbook: the check it is trying to satisfy can be done with git.
