"""Unit tests for pure helpers in lpm_core.py.

These tests use tmp_path fixtures and small mocks so they run without npm,
GitHub, or Automation Studio.
"""

import json
from unittest.mock import patch

import pytest

import lpm_core


class TestGetJsonData:
    def test_reads_existing_json(self, tmp_path):
        path = tmp_path / 'data.json'
        path.write_text(json.dumps({'foo': 'bar', 'n': 1}))
        assert lpm_core.getJsonData(str(path)) == {'foo': 'bar', 'n': 1}

    def test_creates_missing_file_and_returns_empty(self, tmp_path):
        path = tmp_path / 'new.json'
        assert not path.exists()
        assert lpm_core.getJsonData(str(path)) == {}
        # The file should now exist (created via 'x' mode).
        assert path.exists()

    def test_empty_file_returns_empty_dict(self, tmp_path):
        path = tmp_path / 'empty.json'
        path.write_text('')
        assert lpm_core.getJsonData(str(path)) == {}

    def test_invalid_json_returns_empty_dict(self, tmp_path):
        path = tmp_path / 'bad.json'
        path.write_text('{not valid json')
        assert lpm_core.getJsonData(str(path)) == {}


class TestSaveJsonData:
    def test_writes_indented_json(self, tmp_path):
        path = tmp_path / 'out.json'
        lpm_core.saveJsonData({'a': 1, 'b': [2, 3]}, str(path))
        assert json.loads(path.read_text()) == {'a': 1, 'b': [2, 3]}
        # Indented output should contain newlines.
        assert '\n' in path.read_text()

    def test_overwrites_existing_file(self, tmp_path):
        path = tmp_path / 'out.json'
        path.write_text('{"old": true}')
        lpm_core.saveJsonData({'new': True}, str(path))
        assert json.loads(path.read_text()) == {'new': True}

    def test_roundtrip_with_get(self, tmp_path):
        path = tmp_path / 'rt.json'
        original = {'x': {'y': [1, 2, {'z': 'q'}]}}
        lpm_core.saveJsonData(original, str(path))
        assert lpm_core.getJsonData(str(path)) == original


class TestGetPackageManifestField:
    @pytest.fixture
    def manifest(self, tmp_path):
        path = tmp_path / 'package.json'
        path.write_text(
            json.dumps(
                {
                    'name': '@loupeteam/foo',
                    'version': '1.2.3',
                    'lpm': {'type': 'library'},
                    'lpmConfig': {'deploymentConfigs': ['Intel', 'Arm'], 'gitClient': 'GitExtensions'},
                    'dependencies': {'@loupeteam/bar': '^0.1.0'},
                }
            )
        )
        return str(path)

    def test_top_level_field(self, manifest):
        assert lpm_core.getPackageManifestField(manifest, ['name']) == '@loupeteam/foo'

    def test_nested_field(self, manifest):
        assert lpm_core.getPackageManifestField(manifest, ['lpm', 'type']) == 'library'

    def test_returns_dict(self, manifest):
        assert lpm_core.getPackageManifestField(manifest, ['dependencies']) == {'@loupeteam/bar': '^0.1.0'}

    def test_returns_list(self, manifest):
        assert lpm_core.getPackageManifestField(manifest, ['lpmConfig', 'deploymentConfigs']) == ['Intel', 'Arm']

    def test_missing_top_level_returns_none(self, manifest):
        assert lpm_core.getPackageManifestField(manifest, ['nope']) is None

    def test_missing_nested_returns_none(self, manifest):
        assert lpm_core.getPackageManifestField(manifest, ['lpm', 'missing']) is None

    def test_descend_into_non_dict_returns_none(self, manifest):
        # 'name' resolves to a string; further path elements should fail safely.
        assert lpm_core.getPackageManifestField(manifest, ['name', 'extra']) is None


class TestSetPackageManifestField:
    @pytest.fixture
    def manifest(self, tmp_path):
        path = tmp_path / 'package.json'
        path.write_text(json.dumps({'name': '@loupeteam/foo', 'version': '1.0.0'}))
        return str(path)

    def test_creates_lpmconfig_when_missing(self, manifest):
        lpm_core.setPackageManifestField(manifest, 'gitClient', 'GitExtensions')
        with open(manifest) as f:
            data = json.load(f)
        assert data['lpmConfig'] == {'gitClient': 'GitExtensions'}
        # Untouched fields preserved.
        assert data['name'] == '@loupeteam/foo'
        assert data['version'] == '1.0.0'

    def test_updates_existing_lpmconfig(self, tmp_path):
        path = tmp_path / 'package.json'
        path.write_text(json.dumps({'name': 'x', 'lpmConfig': {'deploymentConfigs': ['Intel'], 'gitClient': 'old'}}))
        lpm_core.setPackageManifestField(str(path), 'gitClient', 'GitExtensions')
        with open(path) as f:
            data = json.load(f)
        assert data['lpmConfig']['gitClient'] == 'GitExtensions'
        # Other lpmConfig keys should remain.
        assert data['lpmConfig']['deploymentConfigs'] == ['Intel']

    def test_writes_list_field(self, manifest):
        lpm_core.setPackageManifestField(manifest, 'deploymentConfigs', ['Intel', 'Arm'])
        with open(manifest) as f:
            data = json.load(f)
        assert data['lpmConfig']['deploymentConfigs'] == ['Intel', 'Arm']


class TestGetPackageType:
    """Covers the manifest-based path. The ASTools-based fallback is exercised
    by the integration tests."""

    def test_reads_lpm_type_from_manifest(self, tmp_path):
        (tmp_path / 'package.json').write_text(json.dumps({'lpm': {'type': 'library'}}))
        assert lpm_core.getPackageType(str(tmp_path)) == 'library'

    def test_program_type(self, tmp_path):
        (tmp_path / 'package.json').write_text(json.dumps({'lpm': {'type': 'program'}}))
        assert lpm_core.getPackageType(str(tmp_path)) == 'program'

    def test_project_type(self, tmp_path):
        (tmp_path / 'package.json').write_text(json.dumps({'lpm': {'type': 'project'}}))
        assert lpm_core.getPackageType(str(tmp_path)) == 'project'


class TestGetRepoName:
    def test_extracts_repo_name_from_html_url(self):
        fake_data = {'repository': {'html_url': 'https://github.com/loupeteam/atn'}}
        with patch.object(lpm_core, 'getLoupePackageData', return_value=(None, fake_data)):
            assert lpm_core.getRepoName('@loupeteam/atn') == 'atn'

    def test_returns_none_when_html_url_missing(self):
        fake_data = {'repository': {}}
        with patch.object(lpm_core, 'getLoupePackageData', return_value=(None, fake_data)):
            assert lpm_core.getRepoName('@loupeteam/atn') is None

    def test_returns_none_when_repository_missing(self):
        with patch.object(lpm_core, 'getLoupePackageData', return_value=(None, {})):
            assert lpm_core.getRepoName('@loupeteam/atn') is None

    def test_returns_none_on_error(self):
        with patch.object(lpm_core, 'getLoupePackageData', return_value=('boom', None)):
            assert lpm_core.getRepoName('@loupeteam/atn') is None


class TestGetAllDependencies:
    """getAllDependencies walks a project's node_modules to build a flat list
    of lpm-managed packages to sync. These tests build a fake node_modules
    layout under tmp_path and chdir into it so we exercise the real
    file-reading code paths.
    """

    @staticmethod
    def _writeManifest(root, packageName, manifest):
        # packageName may include a scope ('@scope/name') or be bare ('name').
        manifestPath = root / 'node_modules' / packageName / 'package.json'
        manifestPath.parent.mkdir(parents=True, exist_ok=True)
        manifestPath.write_text(json.dumps(manifest))

    def test_single_lpm_package_with_no_deps_returns_itself(self, tmp_path, monkeypatch):
        self._writeManifest(tmp_path, '@a/x', {'lpm': {'type': 'library'}})
        monkeypatch.chdir(tmp_path)
        assert lpm_core.getAllDependencies(['@a/x']) == ['@a/x']

    def test_walks_lpm_managed_transitive_deps(self, tmp_path, monkeypatch):
        # @a/x is lpm-managed and depends on @a/y, which is also lpm-managed.
        self._writeManifest(tmp_path, '@a/x', {'lpm': {'type': 'library'}, 'dependencies': {'@a/y': '*'}})
        self._writeManifest(tmp_path, '@a/y', {'lpm': {'type': 'library'}})
        monkeypatch.chdir(tmp_path)
        result = lpm_core.getAllDependencies(['@a/x'])
        assert result == ['@a/x', '@a/y']

    def test_non_lpm_package_is_a_leaf(self, tmp_path, monkeypatch):
        # Regression for the opcua-proxy hang: a package with no `lpm` field
        # must NOT have its (potentially huge) npm dep tree walked. We create
        # real manifests for the npm deps so an unfixed walker would happily
        # recurse into them; the assertion is that only the requested package
        # comes back.
        self._writeManifest(
            tmp_path,
            '@a/x',
            {'dependencies': {'express': '*', 'node-opcua': '*'}},
        )
        self._writeManifest(tmp_path, 'express', {'dependencies': {'body-parser': '*'}})
        self._writeManifest(tmp_path, 'body-parser', {})
        self._writeManifest(tmp_path, 'node-opcua', {})
        monkeypatch.chdir(tmp_path)
        result = lpm_core.getAllDependencies(['@a/x'])
        # Only @a/x — none of the plain npm packages, transitive or otherwise,
        # should appear in the lpm sync list.
        assert result == ['@a/x']

    def test_skips_packages_with_missing_manifest(self, tmp_path, monkeypatch):
        # Regression for #83: a transitive dep that npm hoisted to a nested
        # location is not at node_modules/<name>/package.json. Must skip it
        # rather than crashing.
        self._writeManifest(tmp_path, '@a/x', {'lpm': {'type': 'library'}, 'dependencies': {'@a/missing': '*'}})
        monkeypatch.chdir(tmp_path)
        # Should return @a/x and silently skip @a/missing.
        assert lpm_core.getAllDependencies(['@a/x']) == ['@a/x']

    def test_handles_dependency_cycles(self, tmp_path, monkeypatch):
        # A -> B -> A. Memoization must terminate the walk.
        self._writeManifest(tmp_path, '@a/x', {'lpm': {'type': 'library'}, 'dependencies': {'@a/y': '*'}})
        self._writeManifest(tmp_path, '@a/y', {'lpm': {'type': 'library'}, 'dependencies': {'@a/x': '*'}})
        monkeypatch.chdir(tmp_path)
        result = lpm_core.getAllDependencies(['@a/x'])
        assert sorted(result) == ['@a/x', '@a/y']

    def test_dedupes_diamond_dependencies(self, tmp_path, monkeypatch):
        # A -> B, A -> C, B -> D, C -> D. D appears once in result.
        self._writeManifest(
            tmp_path, '@a/a', {'lpm': {'type': 'library'}, 'dependencies': {'@a/b': '*', '@a/c': '*'}}
        )
        self._writeManifest(tmp_path, '@a/b', {'lpm': {'type': 'library'}, 'dependencies': {'@a/d': '*'}})
        self._writeManifest(tmp_path, '@a/c', {'lpm': {'type': 'library'}, 'dependencies': {'@a/d': '*'}})
        self._writeManifest(tmp_path, '@a/d', {'lpm': {'type': 'library'}})
        monkeypatch.chdir(tmp_path)
        result = lpm_core.getAllDependencies(['@a/a'])
        assert sorted(result) == ['@a/a', '@a/b', '@a/c', '@a/d']
        assert result.count('@a/d') == 1

    def test_hmi_project_short_circuits_recursion(self, tmp_path, monkeypatch):
        # hmi-project deps are deliberately not walked recursively (they're
        # entire applications, not libraries). Existing behavior preserved.
        self._writeManifest(
            tmp_path,
            '@a/hmi',
            {'lpm': {'type': 'hmi-project'}, 'dependencies': {'@a/should-not-walk': '*'}},
        )
        self._writeManifest(tmp_path, '@a/should-not-walk', {'lpm': {'type': 'library'}})
        monkeypatch.chdir(tmp_path)
        result = lpm_core.getAllDependencies(['@a/hmi'])
        # Returns the original input untouched, not the walked tree.
        assert result == ['@a/hmi']
