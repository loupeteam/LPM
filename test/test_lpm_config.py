"""Unit tests for the multi-scope configuration layer.

These tests do not exercise npm or GitHub; they only validate the loading,
merging, and helper logic in `lpm_config`, plus how the CLI's
`_normalize_packages` honors the configured default scope.
"""

import json
import os
import sys
import importlib

import pytest

sys.path.insert(0, "./src")
sys.path.insert(0, "./src/ASPython")

import lpm_config  # noqa: E402
import LPM  # noqa: E402


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Point lpm_config at a throwaway config file and reset its cache."""
    cfg_path = tmp_path / "config.json"
    monkeypatch.setenv("LPM_CONFIG_PATH", str(cfg_path))
    # Run from a directory with no project package.json so per-project layer is
    # a no-op for these tests.
    monkeypatch.chdir(tmp_path)
    lpm_config.reset_cache()
    yield cfg_path
    lpm_config.reset_cache()


def _write_config(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    lpm_config.reset_cache()


def test_default_config_when_no_file(isolated_config):
    cfg = lpm_config.load_config()
    assert cfg["defaultScope"] == "@loupeteam"
    assert "@loupeteam" in cfg["scopes"]
    assert cfg["scopes"]["@loupeteam"]["org"] == "loupeteam"


def test_user_config_adds_extra_scope(isolated_config):
    _write_config(isolated_config, {
        "scopes": {
            "@acme": {"org": "acme-corp", "registry": "https://npm.pkg.github.com"}
        }
    })
    cfg = lpm_config.load_config()
    # Built-in default scope is preserved alongside the user-added one.
    assert "@loupeteam" in cfg["scopes"]
    assert cfg["scopes"]["@acme"]["org"] == "acme-corp"
    assert lpm_config.get_default_scope() == "@loupeteam"


def test_user_config_overrides_default_scope(isolated_config):
    _write_config(isolated_config, {
        "defaultScope": "@acme",
        "scopes": {
            "@acme": {"org": "acme-corp", "registry": "https://npm.pkg.github.com"}
        }
    })
    assert lpm_config.get_default_scope() == "@acme"


def test_unknown_default_scope_falls_back(isolated_config):
    _write_config(isolated_config, {"defaultScope": "@nonexistent"})
    # Falls back to @loupeteam rather than crashing.
    assert lpm_config.get_default_scope() == "@loupeteam"


def test_scope_for_package_extracts_or_defaults(isolated_config):
    _write_config(isolated_config, {
        "scopes": {
            "@acme": {"org": "acme-corp", "registry": "https://npm.pkg.github.com"}
        }
    })
    assert lpm_config.scope_for_package("@acme/foo") == "@acme"
    assert lpm_config.scope_for_package("foo") == "@loupeteam"
    assert lpm_config.org_for_package("@acme/foo") == "acme-corp"
    assert lpm_config.org_for_package("foo") == "loupeteam"


def test_strip_scope(isolated_config):
    assert lpm_config.strip_scope("@acme/foo") == "foo"
    assert lpm_config.strip_scope("foo") == "foo"


def test_normalize_packages_uses_default_scope(isolated_config):
    # Bare names get the loupeteam prefix; existing scopes are preserved.
    pkgs, versions = LPM._normalize_packages(["foo", "@acme/bar", "baz@1.2.3", "@acme/qux@2.0.0"])
    assert pkgs == ["@loupeteam/foo", "@acme/bar", "@loupeteam/baz", "@acme/qux"]
    assert versions == ["", "", "1.2.3", "2.0.0"]


def test_normalize_packages_honors_overridden_default(isolated_config):
    _write_config(isolated_config, {
        "defaultScope": "@acme",
        "scopes": {
            "@acme": {"org": "acme-corp", "registry": "https://npm.pkg.github.com"}
        }
    })
    pkgs, _ = LPM._normalize_packages(["foo"])
    assert pkgs == ["@acme/foo"]


def test_login_writes_registry_line_per_scope(isolated_config, monkeypatch, tmp_path):
    # Stage a fake HOME so login() writes to a sandbox.
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))  # Windows
    _write_config(isolated_config, {
        "scopes": {
            "@acme": {"org": "acme-corp", "registry": "https://npm.pkg.github.com"}
        }
    })

    import lpm_core
    importlib.reload(lpm_core)  # rebind os.path.expanduser('~') usage at call time
    lpm_config.reset_cache()
    # Re-apply the env after reload (reload re-imports os).
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setenv("LPM_CONFIG_PATH", str(isolated_config))

    lpm_core.login("dummy-token-xyz")

    npmrc = (fake_home / ".npmrc").read_text(encoding="utf-8")
    assert "@loupeteam:registry=https://npm.pkg.github.com" in npmrc
    assert "@acme:registry=https://npm.pkg.github.com" in npmrc
    assert "//npm.pkg.github.com/:_authToken=dummy-token-xyz" in npmrc
    # Auth token should appear exactly once (deduped by host).
    assert npmrc.count("_authToken=") == 1
