#!/usr/bin/env python3
"""Tests for the credential gate in install/backup.sh.

The gate is a grep -E pattern, so it is tested the way the script runs it:
the KEY_RE line is read from backup.sh and fed to `grep -aE` on a temp file.
Fake keys are assembled at runtime so no key-shaped literal sits in the repo.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP = REPO_ROOT / "install" / "backup.sh"

pytestmark = pytest.mark.skipif(shutil.which("grep") is None, reason="needs grep")


def key_re() -> str:
    match = re.search(r"^KEY_RE='(.+)'$", BACKUP.read_text(), re.MULTILINE)
    assert match, "KEY_RE line not found in install/backup.sh"
    return match.group(1)


def gate_flags(tmp_path: Path, text: str) -> bool:
    sample = tmp_path / "settings.json"
    sample.write_text(text)
    result = subprocess.run(
        ["grep", "-aEl", key_re(), str(sample)],
        env={"LC_ALL": "C"},
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


@pytest.mark.parametrize(
    "prefix",
    ["sk-" + "ant-api03-", "sk-" + "ant-oat01-", "sk-" + "proj-", "sk-"],
)
def test_gate_flags_hyphenated_and_plain_sk_keys(tmp_path: Path, prefix: str) -> None:
    assert gate_flags(tmp_path, '{"apiKey": "' + prefix + "a1B2" * 6 + '"}')


def test_gate_ignores_words_that_merely_contain_sk(tmp_path: Path) -> None:
    text = '{"note": "run the task-runner and the disk-check"}'
    assert not gate_flags(tmp_path, text)
