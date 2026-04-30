'''
 * File: lpm_config.py
 * Copyright (c) 2026 Loupe
 * https://loupe.team
 *
 * This file is part of LPM, licensed under the MIT License.
'''
'''
LPM scope/registry configuration.

LPM was originally hardcoded to the @loupeteam npm scope (backed by the
`loupeteam` GitHub organization on npm.pkg.github.com). This module generalizes
that so users can register additional scopes without modifying LPM source.

Configuration is layered (later overrides earlier):
  1. Built-in defaults (always include @loupeteam -> loupeteam org).
  2. User-global config: ~/.lpm/config.json (or $LPM_CONFIG_PATH if set).
  3. Per-project config: ./package.json -> "lpmConfig" with optional
     "scopes" and "defaultScope" keys.

Each scope entry has the shape:
    "@scope": { "org": "<github-org>", "registry": "<registry-url>" }

A user with no config files installed sees identical behavior to the
original loupeteam-only LPM.
'''

import os
import os.path
import json


DEFAULT_SCOPE = '@loupeteam'
DEFAULT_ORG = 'loupeteam'
DEFAULT_REGISTRY = 'https://npm.pkg.github.com'

_BUILTIN_SCOPES = {
    DEFAULT_SCOPE: {'org': DEFAULT_ORG, 'registry': DEFAULT_REGISTRY},
}

# Cached config for the lifetime of the process. The CLI is short-lived, so
# a single load per invocation is fine.
_cached_config = None


def _user_config_path():
    override = os.environ.get('LPM_CONFIG_PATH')
    if override:
        return override
    return os.path.join(os.path.expanduser('~'), '.lpm', 'config.json')


def _read_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return None


def _normalize_scope_key(scope):
    if not scope:
        return scope
    if not scope.startswith('@'):
        return '@' + scope
    return scope


def _normalize_scopes_dict(raw):
    """Coerce any user-provided scopes mapping to the canonical shape."""
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, value in raw.items():
        scope_key = _normalize_scope_key(key)
        if not isinstance(value, dict):
            continue
        org = value.get('org')
        if not org:
            continue
        registry = value.get('registry') or DEFAULT_REGISTRY
        out[scope_key] = {'org': org, 'registry': registry}
    return out


def load_config(force_reload=False):
    """Load and merge LPM configuration. Result shape:
        { 'defaultScope': '@scope',
          'scopes': { '@scope': {'org': str, 'registry': str}, ... } }
    """
    global _cached_config
    if _cached_config is not None and not force_reload:
        return _cached_config

    scopes = dict(_BUILTIN_SCOPES)
    default_scope = DEFAULT_SCOPE

    # Layer 2: user-global config.
    user_data = _read_json(_user_config_path())
    if isinstance(user_data, dict):
        scopes.update(_normalize_scopes_dict(user_data.get('scopes')))
        if user_data.get('defaultScope'):
            default_scope = _normalize_scope_key(user_data['defaultScope'])

    # Layer 3: per-project package.json -> lpmConfig.
    project_pkg = _read_json(os.path.join('.', 'package.json'))
    if isinstance(project_pkg, dict):
        lpm_config = project_pkg.get('lpmConfig')
        if isinstance(lpm_config, dict):
            scopes.update(_normalize_scopes_dict(lpm_config.get('scopes')))
            if lpm_config.get('defaultScope'):
                default_scope = _normalize_scope_key(lpm_config['defaultScope'])

    # Guarantee the default scope is resolvable. If a user removed @loupeteam
    # and pointed defaultScope somewhere unconfigured, fall back to @loupeteam.
    if default_scope not in scopes:
        default_scope = DEFAULT_SCOPE

    _cached_config = {'defaultScope': default_scope, 'scopes': scopes}
    return _cached_config


def reset_cache():
    """Test hook: drop the cached config so the next call re-reads files."""
    global _cached_config
    _cached_config = None


def get_default_scope():
    return load_config()['defaultScope']


def get_scopes():
    """Return a copy of the {scope: {org, registry}} mapping."""
    return dict(load_config()['scopes'])


def get_scope_info(scope):
    scope = _normalize_scope_key(scope)
    return load_config()['scopes'].get(scope)


def get_org_for_scope(scope):
    info = get_scope_info(scope)
    if info is None:
        # Unknown scope: fall back to the default org so we degrade rather than
        # crash. Callers that need strictness should check get_scope_info first.
        return load_config()['scopes'][get_default_scope()]['org']
    return info['org']


def get_registry_for_scope(scope):
    info = get_scope_info(scope)
    if info is None:
        return load_config()['scopes'][get_default_scope()]['registry']
    return info['registry']


def scope_for_package(package_name):
    """Extract the @scope prefix from a package name, or return the default."""
    if package_name and package_name.startswith('@') and '/' in package_name:
        return package_name.split('/', 1)[0]
    return get_default_scope()


def org_for_package(package_name):
    return get_org_for_scope(scope_for_package(package_name))


def strip_scope(package_name):
    """Return the bare package name (no @scope/ prefix)."""
    if package_name and package_name.startswith('@') and '/' in package_name:
        return package_name.split('/', 1)[1]
    return package_name


def apply_default_scope(package_name):
    """Prepend the default scope if `package_name` is not already scoped."""
    if package_name and package_name.startswith('@') and '/' in package_name:
        return package_name
    return f'{get_default_scope()}/{package_name}'
