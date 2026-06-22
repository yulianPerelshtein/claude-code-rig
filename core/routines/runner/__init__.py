"""Runner package for the rig's routines capability.

The safety-critical logic (outcome-policy enforcement, git/worktree/draft-PR
plumbing, report/log/state) lives here and is unit-tested with pytest. A thin
``run-routine.sh`` and systemd user units invoke it headlessly.
"""
