#!/usr/bin/env bash
# Thin entrypoint for routines: systemd timers and the /routines skill call this;
# all logic lives in the python runner (core/routines/runner/). Kept thin so the
# safety-critical code stays unit-tested in Python.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Put the runner package on PYTHONPATH WITHOUT changing the working directory,
# so the CLI's `--target` default (the caller's cwd) stays correct. --with
# pyyaml supplies the registry loader's dep (the rig declares no [project] deps).
export PYTHONPATH="${HERE}${PYTHONPATH:+:${PYTHONPATH}}"
exec uv run --with pyyaml python -m runner.cli "$@"
