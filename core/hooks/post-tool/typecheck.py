#!/usr/bin/env python3
import sys
import json
import subprocess
import os


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

    # Lint-fix this file immediately after Claude writes it.
    # ruff check --fix: removes unused imports, fixes quote style, etc.
    # Does NOT reformat whitespace or collapse multi-line expressions —
    # that is ruff format's job, which we never run automatically.
    subprocess.run(
        ['uv', 'run', 'ruff', 'check', '--fix', path],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Type-check via the mypy daemon (dmypy): the daemon persists across edits,
    # so repeated checks are fast instead of paying mypy's cold start every time.
    # Only return code 1 means "type errors found"; 2 means a tooling/daemon
    # problem, which we skip silently rather than emit a false TYPE ERRORS warning.
    result = subprocess.run(
        ['uv', 'run', 'dmypy', 'run', '--', path,
         '--ignore-missing-imports', '--no-error-summary'],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode == 1:
        print(f'TYPE ERRORS in {path}:\n{result.stdout.strip()}', file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
