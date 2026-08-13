#!/usr/bin/env bash
# Thin entrypoint for routines: systemd timers and the /routines skill call this;
# all logic lives in the python runner (core/routines/runner/). Kept thin so the
# safety-critical code stays unit-tested in Python.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# systemd --user hands us a minimal PATH with neither uv nor claude (both live in
# ~/.local/bin), so every timer-fired routine exited 127 while the identical
# command worked in a login shell — silently, nightly. Fixed here rather than in
# the unit file so the cron and CI substrates inherit it too. Node is added only
# when claude turns out to need it (a native install does not).
# Plain conditionals, not `[[ … ]] && …`: under `set -e` that idiom aborts the
# script the moment a directory is absent, which is exactly the case on a host
# without ~/.local/bin.
for d in "${HOME}/.local/bin" "${HOME}/bin"; do
    if [[ -d "${d}" ]]; then
        case ":${PATH}:" in
            *":${d}:"*) ;;
            *) PATH="${d}:${PATH}" ;;
        esac
    fi
done
if ! command -v node >/dev/null 2>&1; then
    nvm_bin="$(ls -d "${NVM_DIR:-${HOME}/.nvm}"/versions/node/*/bin 2>/dev/null | sort -V | tail -n1 || true)"
    if [[ -n "${nvm_bin}" ]]; then
        PATH="${nvm_bin}:${PATH}"
    fi
fi
export PATH

for tool in uv claude; do
    command -v "${tool}" >/dev/null 2>&1 || {
        echo "run-routine.sh: '${tool}' not found on PATH=${PATH}" >&2
        exit 127
    }
done
# Put the runner package on PYTHONPATH WITHOUT changing the working directory,
# so the CLI's `--target` default (the caller's cwd) stays correct. --with
# pyyaml supplies the registry loader's dep (the rig declares no [project] deps).
export PYTHONPATH="${HERE}${PYTHONPATH:+:${PYTHONPATH}}"
exec uv run --with pyyaml python -m runner.cli "$@"
