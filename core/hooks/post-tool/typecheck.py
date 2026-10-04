#!/usr/bin/env python3
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# A per-edit hook blocks the agent loop: short caps, and a timeout skips the check.
RUFF_TIMEOUT_S = 10
DMYPY_TIMEOUT_S = 15


def _git_root(path: str) -> str | None:
    """Return the root of the work tree holding ``path``; None outside any repo."""
    try:
        result = subprocess.run(
            ['git', '-C', os.path.dirname(path), 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    root = result.stdout.strip()
    return root if result.returncode == 0 and root else None


def _status_file(root: str) -> str:
    """Return the dmypy status file for work tree ``root``, kept in the user cache."""
    cache = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    directory = cache / 'claude-code-rig' / 'dmypy'
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory / f'{hashlib.sha256(root.encode()).hexdigest()[:16]}.json')


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool = data.get('tool_name', '')
    if tool not in ('Write', 'Edit'):
        sys.exit(0)

    path = (
        data.get('tool_input', {}).get('path')
        or data.get('tool_input', {}).get('file_path')
        or ''
    )

    if not path.endswith('.py') or not os.path.exists(path):
        sys.exit(0)

    # Scratch files outside any repo (probes in /tmp) are not project code.
    path = os.path.abspath(path)
    root = _git_root(path)
    if root is None:
        sys.exit(0)

    try:
        # Lint-fix this file immediately after Claude writes it.
        # ruff check --fix: removes unused imports, fixes quote style, etc.
        # Does NOT reformat whitespace or collapse multi-line expressions —
        # that is ruff format's job, which we never run automatically.
        subprocess.run(
            ['uv', 'run', '--no-project', 'ruff', 'check', '--fix', path],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=RUFF_TIMEOUT_S,
        )

        # Type-check via the mypy daemon (dmypy): the daemon persists across edits,
        # so repeated checks are fast instead of paying mypy's cold start every time.
        # One daemon per work tree, run from its root: a daemon started in another
        # checkout re-analyses on every switch and stalls on duplicate module names.
        # Only return code 1 means "type errors found"; 2 means a tooling/daemon
        # problem, which we skip silently rather than emit a false TYPE ERRORS warning.
        result = subprocess.run(
            ['uv', 'run', '--no-project', 'dmypy', '--status-file', _status_file(root),
             'run', '--', path, '--ignore-missing-imports', '--no-error-summary'],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=DMYPY_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        sys.exit(0)

    if result.returncode == 1:
        # Exit 2 is the only PostToolUse code that surfaces stderr to Claude
        # (the tool already ran, so this cannot block — it is advisory feedback).
        # Exit 1 would only show a first-line "hook error" notice to the user.
        print(f'TYPE ERRORS in {path}:\n{result.stdout.strip()}', file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
