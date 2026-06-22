#!/usr/bin/env python3
"""Tests for the installer vocabulary in install/lib/installer.py:
`extends:` profile chaining, `- enhancement: <id>` parsing, and the
`conflicts_with` / unknown-id / cycle guards.

installer.py imports pyyaml, which the installer always runs under
(`uv run --with pyyaml`). Run this suite the same way:
    uv run --with pyyaml pytest tests/install/
Under a plain `uv run pytest` (no pyyaml) the module is skipped, not failed.
"""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("yaml")  # installer.py imports yaml at module load

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER = REPO_ROOT / "install" / "lib" / "installer.py"

MARKETPLACE = """
enhancements:
  - id: headroom
    install_method: pipx
    install: 'pipx install headroom-ai'
    smoke_test: enhancements/headroom/smoke-test.sh
  - id: scrapling
    install_method: pipx
    install: 'pipx install scrapling'
    conflicts_with: obscura
  - id: obscura
    install_method: rust
    install: 'cargo install obscura'
    conflicts_with: scrapling
"""


def load_installer(repo: Path):
    spec = importlib.util.spec_from_file_location("installer_mod", INSTALLER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REPO = repo
    mod.MARKETPLACE = repo / "manifests" / "marketplace.yaml"
    return mod


def make_repo(tmp_path: Path, profiles: dict[str, str], marketplace: str = "") -> Path:
    (tmp_path / "profiles").mkdir()
    for name, body in profiles.items():
        (tmp_path / "profiles" / f"{name}.yaml").write_text(body)
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "marketplace.yaml").write_text(marketplace)
    return tmp_path


def test_extends_unions_parent_modules(tmp_path):
    make_repo(tmp_path, {
        "base": "profile: base\nmodules:\n  - core\n  - all-domains\n",
        "child": "profile: child\nextends: base\nmodules:\n  - all-templates\n",
    })
    mod = load_installer(tmp_path)
    assert mod.profile_modules("child") == ["core", "all-domains", "all-templates"]


def test_extends_dedupes(tmp_path):
    make_repo(tmp_path, {
        "base": "profile: base\nmodules:\n  - core\n",
        "child": "profile: child\nextends: base\nmodules:\n  - core\n  - extra\n",
    })
    mod = load_installer(tmp_path)
    assert mod.profile_modules("child") == ["core", "extra"]


def test_enhancement_entries_parsed(tmp_path):
    make_repo(tmp_path, {
        "t2": (
            "profile: t2\nextends: base\nmodules:\n"
            "  - enhancement: headroom\n  - enhancement: scrapling\n"
        ),
        "base": "profile: base\nmodules:\n  - core\n",
    }, MARKETPLACE)
    mod = load_installer(tmp_path)
    assert mod.profile_enhancements("t2") == ["headroom", "scrapling"]
    # Enhancement dicts are not treated as string modules.
    assert mod.profile_modules("t2") == ["core"]


def test_handle_enhancements_reports_without_running(tmp_path, capsys):
    make_repo(tmp_path, {
        "t2": "profile: t2\nmodules:\n  - enhancement: headroom\n",
    }, MARKETPLACE)
    mod = load_installer(tmp_path)
    mod.handle_enhancements("t2")  # must not raise / not run installs
    out = capsys.readouterr().out
    assert "headroom" in out
    assert "DEFERRED" in out


def test_unknown_enhancement_exits(tmp_path):
    make_repo(tmp_path, {
        "t2": "profile: t2\nmodules:\n  - enhancement: nope\n",
    }, MARKETPLACE)
    mod = load_installer(tmp_path)
    with pytest.raises(SystemExit):
        mod.handle_enhancements("t2")


def test_conflicts_with_exits(tmp_path):
    make_repo(tmp_path, {
        "t2": (
            "profile: t2\nmodules:\n"
            "  - enhancement: scrapling\n  - enhancement: obscura\n"
        ),
    }, MARKETPLACE)
    mod = load_installer(tmp_path)
    with pytest.raises(SystemExit):
        mod.handle_enhancements("t2")


def test_extends_cycle_exits(tmp_path):
    make_repo(tmp_path, {
        "a": "profile: a\nextends: b\nmodules: []\n",
        "b": "profile: b\nextends: a\nmodules: []\n",
    })
    mod = load_installer(tmp_path)
    with pytest.raises(SystemExit):
        mod.profile_modules("a")


def test_missing_profile_exits(tmp_path):
    make_repo(tmp_path, {"a": "profile: a\nextends: ghost\nmodules: []\n"})
    mod = load_installer(tmp_path)
    with pytest.raises(SystemExit):
        mod.profile_modules("a")


def test_real_enhanced_tier2_enhancements_resolve():
    """Guard the real profile against a typo'd / missing enhancement id: every
    enhancement listed in profiles/enhanced-tier2.yaml must exist in the real
    marketplace.yaml#enhancements catalog, and handle_enhancements must not exit."""
    mod = load_installer(REPO_ROOT)
    catalog = mod.load_enhancement_catalog()
    enh = mod.profile_enhancements("enhanced-tier2")
    assert "claude-context" in enh
    assert [e for e in enh if e not in catalog] == []
    mod.handle_enhancements("enhanced-tier2")  # validates + reports; must not exit
