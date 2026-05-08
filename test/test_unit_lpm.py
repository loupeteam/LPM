"""Unit tests for pure helpers in LPM.py.

These tests don't hit the network, npm, or Automation Studio — they exercise
argv munging and package-name normalization in isolation. (Importing `LPM`
does read `src/version.json` at module load time, but that's the only
filesystem touch and it's incidental to the tests themselves.)
"""

import pytest

import LPM


class TestNormalizePackages:
    def test_empty_input(self):
        packages, versions = LPM._normalize_packages([])
        assert packages == []
        assert versions == []

    def test_none_input(self):
        packages, versions = LPM._normalize_packages(None)
        assert packages == []
        assert versions == []

    def test_single_bare_name(self):
        packages, versions = LPM._normalize_packages(['atn'])
        assert packages == ['@loupeteam/atn']
        assert versions == ['']

    def test_uppercase_is_lowercased(self):
        packages, versions = LPM._normalize_packages(['ATN'])
        assert packages == ['@loupeteam/atn']
        assert versions == ['']

    def test_with_version_suffix(self):
        packages, versions = LPM._normalize_packages(['atn@1.2.3'])
        assert packages == ['@loupeteam/atn']
        assert versions == ['1.2.3']

    def test_multiple_packages_mixed(self):
        packages, versions = LPM._normalize_packages(['atn', 'vartools@0.11.3', 'StringExt'])
        assert packages == ['@loupeteam/atn', '@loupeteam/vartools', '@loupeteam/stringext']
        assert versions == ['', '0.11.3', '']

    def test_version_with_prerelease_tag(self):
        packages, versions = LPM._normalize_packages(['atn@1.2.3-beta.1'])
        assert packages == ['@loupeteam/atn']
        assert versions == ['1.2.3-beta.1']

    def test_returned_lists_are_aligned(self):
        packages, versions = LPM._normalize_packages(['a', 'b@1', 'c@2'])
        assert len(packages) == len(versions) == 3


class TestHoistGlobalFlags:
    def test_empty(self):
        assert LPM._hoist_global_flags([]) == []

    def test_already_in_front(self):
        assert LPM._hoist_global_flags(['--silent', 'install', 'pkg']) == ['--silent', 'install', 'pkg']

    def test_silent_short_after_subcommand(self):
        assert LPM._hoist_global_flags(['install', '-s']) == ['-s', 'install']

    def test_silent_long_after_subcommand(self):
        assert LPM._hoist_global_flags(['install', '--silent']) == ['--silent', 'install']

    def test_silent_after_packages(self):
        assert LPM._hoist_global_flags(['install', 'pkg', '--silent']) == ['--silent', 'install', 'pkg']

    def test_nocolor_short(self):
        assert LPM._hoist_global_flags(['install', 'pkg', '-nc']) == ['-nc', 'install', 'pkg']

    def test_nocolor_long(self):
        assert LPM._hoist_global_flags(['install', 'pkg', '--nocolor']) == ['--nocolor', 'install', 'pkg']

    def test_two_global_flags_after(self):
        result = LPM._hoist_global_flags(['install', 'pkg', '--silent', '--nocolor'])
        # Both flags should land before the subcommand; their relative order is
        # implementation-defined but both must precede 'install'.
        assert result.index('--silent') < result.index('install')
        assert result.index('--nocolor') < result.index('install')
        assert 'pkg' in result and result.index('pkg') > result.index('install')

    def test_unknown_flag_passes_through(self):
        # Subcommand-specific flags like --source must not be hoisted.
        assert LPM._hoist_global_flags(['install', 'pkg', '--source']) == ['install', 'pkg', '--source']

    def test_no_subcommand(self):
        # If no positional ever appears, flags are returned unchanged.
        assert LPM._hoist_global_flags(['--silent']) == ['--silent']


class TestIsKnownCommand:
    @pytest.fixture
    def parser_and_sub(self):
        return LPM._build_parser('LPM')

    @pytest.mark.parametrize(
        'cmd',
        ['install', 'uninstall', 'login', 'logout', 'status', 'init', 'view', 'info', 'list'],
    )
    def test_known_subcommands(self, parser_and_sub, cmd):
        parser, sub = parser_and_sub
        assert LPM._is_known_command(parser, sub, [cmd]) is True

    def test_unknown_command_returns_false(self, parser_and_sub):
        parser, sub = parser_and_sub
        assert LPM._is_known_command(parser, sub, ['ci']) is False

    def test_help_short(self, parser_and_sub):
        parser, sub = parser_and_sub
        assert LPM._is_known_command(parser, sub, ['-h']) is True

    def test_help_long(self, parser_and_sub):
        parser, sub = parser_and_sub
        assert LPM._is_known_command(parser, sub, ['--help']) is True

    def test_version(self, parser_and_sub):
        parser, sub = parser_and_sub
        assert LPM._is_known_command(parser, sub, ['-v']) is True

    def test_global_flag_then_known_command(self, parser_and_sub):
        parser, sub = parser_and_sub
        assert LPM._is_known_command(parser, sub, ['--silent', 'install']) is True

    def test_global_flag_then_unknown_command(self, parser_and_sub):
        parser, sub = parser_and_sub
        assert LPM._is_known_command(parser, sub, ['--silent', 'ci']) is False

    def test_empty_argv(self, parser_and_sub):
        parser, sub = parser_and_sub
        assert LPM._is_known_command(parser, sub, []) is False
