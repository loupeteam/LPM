'''
 * File: LPM.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 *
 * This file is part of LPM, licensed under the MIT License.
'''
'''
LPM
This is a lightweight wrapper around NPM that processes Loupe packages.

This file contains the command-line interface only. The underlying
functionality lives in lpm_core.py.
'''

import os.path
import json
import sys
import argparse
import logging
import ctypes
import time

version_file = os.path.normpath(os.path.join(os.path.dirname(__file__), 'version.json'))
with open(version_file, "r") as f:
    data = json.load(f)
    __version__ = data["version"]

__author__ = 'Andrew Musser'

from ASPython import ASTools

# Core LPM functionality. The CLI delegates to functions defined in lpm_core.
from lpm_core import *
import lpm_config

# Spellings of flags that are global (top-level) and must appear before the
# subcommand for argparse to recognise them.  Centralised here so that
# _hoist_global_flags(), the fallback parser, and any future code all stay
# in sync automatically.
_GLOBAL_FLAG_SPELLINGS = {'-s', '--silent', '-nc', '--nocolor'}


# ---------------------------------------------------------------------------
# Output coloring helpers.
# These are configured at the start of main() based on --nocolor, then used
# by all the cmd_* handlers below.
# ---------------------------------------------------------------------------

def _identity(text, color):
    return text

def _plain_print(text, color):
    print(text)

colored = _identity
cprint = _plain_print


# ---------------------------------------------------------------------------
# Helpers shared between subcommands.
# ---------------------------------------------------------------------------

# Commands that never require authentication.
_NO_AUTH = {'login', 'logout', 'delete', 'status'}

# Commands that may run before `lpm init` has been invoked (i.e. don't require
# a package.json in the current directory).
_NO_INIT_REQUIRED = {
    'login', 'logout', 'delete', 'status',
    'view', 'info', 'viewall', 'type', 'docs', 'as', 'init',
}


def _normalize_packages(raw_packages):
    """Prepend the configured default scope and split @version suffixes.

    If a user passes an already-scoped name like ``@acme/foo`` it is left
    intact so additional registries (configured via ``lpm_config``) work.
    """
    default_scope = lpm_config.get_default_scope()
    packages = []
    versions = []
    for item in raw_packages or []:
        item = item.lower()
        if item.startswith('@') and '/' in item:
            # Already-scoped name (e.g. "@acme/foo" or "@acme/foo@1.2.3").
            # Split on the last '@' if there's a version suffix.
            if item.count('@') >= 2:
                at_pos = item.rfind('@')
                packages.append(item[:at_pos])
                versions.append(item[at_pos+1:])
            else:
                packages.append(item)
                versions.append('')
        elif '@' in item:
            name, _, version = item.partition('@')
            packages.append(f'{default_scope}/' + name)
            versions.append(version)
        else:
            packages.append(f'{default_scope}/' + item)
            versions.append('')
    return packages, versions


# ---------------------------------------------------------------------------
# Subcommand handlers. Each takes the parsed args namespace.
# ---------------------------------------------------------------------------

def cmd_login(args):
    if args.silent:
        if not args.token:
            print(colored('Error: --token is required when using --silent.', 'red'))
            return
        login(args.token)
    elif args.token:
        login(args.token)
    else:
        cprint('Please follow the prompts below to log in using valid GitHub credentials.', 'yellow')
        token = input(colored('? ', 'green') + 'Enter your personal access token: ')
        login(token)
    if getattr(args, 'no_check', False):
        print('Credentials stored (authentication check skipped).')
    elif isAuthenticated():
        print(colored(f'New credentials for {getAuthenticatedUser()} successfully stored.', 'green'))
    else:
        print(colored('Error: invalid credentials. Please try again.', 'red'))


def cmd_logout(args):
    print('Logging out...')
    logout()
    print(colored('Successfully logged out.', 'green'))


def cmd_delete(args):
    print('Removing LPM content from the local project...')
    deleteProject()
    print(colored('All done!', 'green'), 'Thanks for using LPM.')
    print(colored('Note: LPM-installed content within your AS project folder has not been removed.', 'yellow'))


def cmd_status(args):
    print('Retrieving status...')
    if isAuthenticated():
        print('-> Logged in: ' + colored('Yes', 'green'))
        print('-> Current user: ' + colored(getAuthenticatedUser(), 'green'))
    else:
        print('-> Logged in: ' + colored('No', 'yellow'))
    if os.path.exists('package.json'):
        packageType = getPackageType('.')
        if packageType == 'project':
            print('-> Local directory status: ' + colored('Initialized with Automation Studio project', 'green'))
        elif packageType == 'library':
            print('-> Local directory status: ' + colored('Initialized with local library', 'green'))
        elif packageType in ('program', 'package'):
            print('-> Local directory status: ' + colored('Initialized with local program', 'green'))
        else:
            print('-> Local directory status: ' + colored('Initialized as stand-alone package manager', 'green'))
    else:
        print('-> Local directory status: ' + colored('Not initialized for use with lpm', 'yellow'))


def cmd_view(args):
    packages, _ = _normalize_packages(args.packages)
    if len(args.packages) > 1:
        getInfo(packages[0], args.packages[1:])
    elif len(args.packages) == 1:
        getInfo(packages[0], [])
    else:
        print(colored('Please provide the name of one package.', 'yellow'))


def cmd_viewall(args):
    printLoupePackageList()


def cmd_type(args):
    if len(args.packages) > 1:
        print(colored('This command is only supported with a single package.', 'yellow'))
    elif len(args.packages) == 1:
        print(getPackageType(args.packages[0]))
    else:
        print(colored('Please provide the name of one package.', 'yellow'))


def cmd_docs(args):
    packages, _ = _normalize_packages(args.packages)
    if packages:
        print('Opening up documentation for ' + ', '.join(packages) + '...')
        openDocumentation(packages)
        print(colored('Documentation is now up in your browser.', 'green'))
    else:
        print(colored('Please provide the name of at least one package.', 'yellow'))


def cmd_as(args):
    project = ASTools.Project('.')
    print('Opening Automation Studio...')
    asBin = os.path.join(ASTools.getASPath(project.ASVersion), 'pg.exe')
    if not os.path.isfile(asBin):
        cprint(f'Project was last opened with {project.ASVersion}, but that version is not installed. Trying to open with AS410 instead...', 'yellow')
        # If that version isn't installed, try something else. Just hard-coding 410 for now because it's what I have installed!
        asBin = os.path.join(ASTools.getASPath('AS410'), 'pg.exe')
    cmd = [asBin, '\"' + os.path.join(os.getcwd(), f'{project.name}.apj') + '\"']
    executeAndContinue(cmd)
    time.sleep(3)
    cprint('Wait for it...', 'yellow')
    time.sleep(3)
    cprint('Still working...', 'yellow')
    time.sleep(3)
    cprint('Almost done...', 'yellow')
    time.sleep(3)
    cprint('Good to go!', 'green')


def cmd_init(args):
    as_project = False
    as_library = False
    try:
        ASTools.Project('.')
        as_project = True
    except:
        as_project = False
    try:
        ASTools.Library('.')
        as_library = True
    except:
        as_library = False

    if as_project or args.asproject:
        print('Automation Studio project found, initializing package manager...')
        initializeProject()
        arg_folder = False
        if not args.silent:
            text = input(colored('? ', 'green') + colored('Would you like to initialize LPM with the existing Loupe libraries in your Automation Studio project?', 'yellow') + ' (y/N) ')
            if text.lower() in ('y', 'yes'):
                arg_folder = importLibraries()
        configureProject(args)
        cprint('Your Automation Studio project is now ready to be used with LPM.', 'green')
        if arg_folder:
            cprint('Note that you will need to manually remove the _ARG folder to avoid library conflicts.', 'yellow')

    elif as_library or args.aslibrary:
        name = os.path.basename(os.getcwd())
        packageData = {}
        if os.path.exists('package.json'):
            print('Found an existing package.json file, extracting its relevant contents...')
            packageData = getPackageManifestField('package.json', ['lpm'])
        print('Creating package.json for the ' + colored(f'{name}', 'yellow') + ' library...')
        createLibraryManifest(name, packageData)
        print(colored('The package.json was successfully created.', 'green'))

    else:
        if not args.silent:
            text = input(colored('? ', 'green') + colored('No Automation Studio project found. Would you like to initialize this directory with a starter AS project?', 'yellow') + ' (Y/n) ')
        else:
            text = 'n'
        if text.lower() in ('n', 'no'):
            initializeProject()
            print(colored('This directory has been initialized as a stand-alone package manager.', 'green'))
        else:
            initializeProject()
            # TODO: support per-scope starter projects. For now we always
            # bootstrap from the default scope (which is @loupeteam unless the
            # user has overridden it in their lpm config).
            starterProject = [f'{lpm_config.get_default_scope()}/starterasproject49']
            installPackages(starterProject, [''])
            syncPackages(starterProject)
            configureProject(args)
            print(colored('Your local directory is now ready to be used with LPM.', 'green'))


def cmd_configure(args):
    configureProject(args)


def cmd_debug(args):
    libraries = readLoupeLibraryList()
    print(libraries)


def cmd_install(args):
    packages, packageVersions = _normalize_packages(args.packages)

    if not args.source:
        if packages:
            print('Installing ' + ', '.join(packages) + '...')
        else:
            print('Installing all dependencies...')
        try:
            installPackages(packages, packageVersions)
        except:
            cprint('Error while attempting to install package(s).', 'yellow')
            return
        # If no explicit packages were given, resolve the full list from the
        # local package.json so that sync and deploy still run.
        if not packages:
            deps = getPackageManifestField('package.json', ['dependencies']) or {}
            packages = list(deps.keys())
        # Move packages from the node_modules folder into the project/main directory.
        syncPackages(getAllDependencies(packages))
        sourceDependencies = []
    else:
        if packages:
            print('Attempting to install source for ' + ', '.join(args.packages) + '...')
        sourceDependencies = []
        for (package, packageVersion) in zip(packages, packageVersions):
            installSource(package, packageVersion, sourceDependencies)

    # Deploy relevant objects to cpu.sw.
    deploymentConfigs = getPackageManifestField('package.json', ['lpmConfig', 'deploymentConfigs'])
    if deploymentConfigs is not None:
        print('Deploying ' + ', '.join(packages) + ' to the following configurations: ' + ', '.join(deploymentConfigs))
        for config in deploymentConfigs:
            if not args.source:
                deployPackages(config, getAllDependencies(packages))
            else:
                # TODO: this split below may not be necessary, TBD.
                # For case of source, deploy the source first.
                deployPackages(config, packages)
                # Then deploy all of its dependencies.
                deployPackages(config, sourceDependencies)
    cprint('Operation completed successfully.', 'green')
    for package in packages:
        packageManifestPath = os.path.join('node_modules', package, 'package.json')
        if os.path.exists(packageManifestPath):
            packageType = getPackageManifestField(packageManifestPath, ['lpm', 'type'])
            if packageType == 'project':
                return
    if deploymentConfigs is None:
        cprint("Note that the installed packages have not been deployed.", "yellow")
        cprint("You will need to do this manually, or you can configure deployment targets with the 'lpm configure' command.", 'yellow')


def cmd_uninstall(args):
    packages, _ = _normalize_packages(args.packages)
    if not packages:
        print(colored('Please provide the name of at least one package.', 'yellow'))
        return
    print('Uninstalling ' + ', '.join(packages) + '...')
    try:
        uninstallPackages(packages)
    except:
        cprint('Error while attempting to uninstall package(s).', 'yellow')
        return
    syncPackages(getAllDependencies(packages))
    cprint('Operation completed successfully.', 'green')


def cmd_git(args):
    packages, _ = _normalize_packages(args.packages)
    gitClient = getPackageManifestField('package.json', ['lpmConfig', 'gitClient'])
    if gitClient == '':
        cprint("No Git client configured (please run lpm configure)", "yellow")
        return
    if gitClient != 'GitExtensions':
        cprint(f"We don't support {gitClient}, are you kidding?", "yellow")
        return
    sourceInfoFilePath = os.path.join(".", "TempObjects", "sourceInfo.json")
    sourceInfo = getJsonData(sourceInfoFilePath)
    print(f'Opening {gitClient} for these packages: ' + ', '.join(args.packages))
    for package in packages:
        repoPath = sourceInfo.get(package, {}).get("repoPath", None)
        if repoPath is not None:
            cmd = ['gitex.cmd', 'openrepo', '\"' + os.path.join(os.getcwd(), repoPath) + '\"']
            executeAndContinue(cmd)
        else:
            cprint(f"Could not find repo location for {package}. Verify that it is installed as source.", "yellow")


def cmd_publish(args):
    data = getPackageManifestData('package.json')
    # Publishing is currently restricted to the @loupeteam scope. The
    # multi-scope refactor wires everything else through lpm_config, but the
    # publish flow has not been validated end-to-end against user-added
    # scopes/registries yet.
    # TODO: replace this guard with `lpm_config.get_scope_info(scope)` once the
    # publish flow is verified for user-added scopes. The check would become:
    #     scope = lpm_config.scope_for_package(data['name'])
    #     if lpm_config.get_scope_info(scope) is None: ...
    if not data['name'].startswith('@loupeteam/'):
        cprint('Error: the package name must include the @loupeteam scope prefix.', 'yellow')
        return
    try:
        repoUrl = data['repository']['url']  # triggers an exception if missing
    except:
        cprint('Error: the package.json file must include a repository parameter', 'yellow')
        cprint('For example:', 'yellow')
        print('"repository": {')
        print('    "type": "git",')
        print('    "url": "https://github.com/loupeteam/piper"')
        print('}')
        return
    if args.silent:
        text = 'y'
    else:
        text = input(colored('? ', 'green') + 'Are you sure you want to publish ' + colored(data['name'], 'yellow') + ' version ' + colored(data['version'], 'yellow') + '? (y/N) ')
    if text.lower() not in ('y', 'yes'):
        return
    try:
        # Clean up the local directory before publishing.
        if os.path.isfile('./Jenkinsfile'):
            os.remove('./Jenkinsfile')
        execute(['npm', 'publish'], True)
        cprint('Successfully published ' + data['name'] + ' version ' + data['version'] + '.', 'green')
    except:
        cprint("Error while publishing. Please check the detailed error message above.", 'yellow')


def cmd_list(args):
    if args.packages:
        # Defer to npm with normalized package names for consistency with
        # other commands and scoped Loupe package handling.
        packages, _ = _normalize_packages(args.packages)
        runGenericNpmCmd('list', packages)
        cprint('Operation completed', 'green')
        return
    executeStandard(['npm list', '-all'])


def cmd_npm_passthrough(args):
    """Fallback for any command not recognized as an LPM subcommand."""
    packages, _ = _normalize_packages(args.packages)
    runGenericNpmCmd(args.cmd, packages)
    cprint('Operation completed', 'green')


# ---------------------------------------------------------------------------
# Argument parser construction.
# ---------------------------------------------------------------------------

def _build_parser(prog_name):
    parser = argparse.ArgumentParser(
        description='A lightweight wrapper around NPM for Automation Studio dependency management',
        prog=prog_name,
    )
    # Global flags (apply to all subcommands).
    parser.add_argument('-s', '--silent', action='store_true',
                        help='Execute commands silently with default values and no operator prompts')
    parser.add_argument('-nc', '--nocolor', action='store_true',
                        help="Don't color the output - to avoid dependency on termcolor")
    parser.add_argument('-v', '--version', action='version', version='%(prog)s: ' + __version__)

    sub = parser.add_subparsers(dest='cmd', metavar='command')

    # login
    p = sub.add_parser('login', help='Authenticate with the GitHub package registry')
    p.add_argument('-t', '--token', type=str, help='Personal Access Token required for silent login')
    p.add_argument('--no-check', action='store_true', dest='no_check',
                   help='Skip the post-login authentication check (useful for CI machine tokens)')
    p.set_defaults(func=cmd_login)

    # logout
    p = sub.add_parser('logout', help='Log out of the GitHub package registry')
    p.set_defaults(func=cmd_logout)

    # delete
    p = sub.add_parser('delete', help='Remove all local LPM files (package.json, .npmrc, node_modules)')
    p.set_defaults(func=cmd_delete)

    # status
    p = sub.add_parser('status', help='Show authentication and initialization status')
    p.set_defaults(func=cmd_status)

    # view / info
    for name in ('view', 'info'):
        p = sub.add_parser(name, help='View information about a package')
        p.add_argument('packages', nargs='*', help='Package and optional npm view fields')
        p.set_defaults(func=cmd_view)

    # viewall
    p = sub.add_parser('viewall', help='List all available Loupe packages')
    p.set_defaults(func=cmd_viewall)

    # type
    p = sub.add_parser('type', help='Print the LPM type of a package or directory')
    p.add_argument('packages', nargs='*')
    p.set_defaults(func=cmd_type)

    # docs
    p = sub.add_parser('docs', help='Open the documentation page for one or more packages')
    p.add_argument('packages', nargs='*')
    p.set_defaults(func=cmd_docs)

    # as
    p = sub.add_parser('as', help='Open the project in Automation Studio')
    p.set_defaults(func=cmd_as)

    # init
    p = sub.add_parser('init', help='Initialize the current directory for use with LPM')
    p.add_argument('-prj', '--asproject', action='store_true',
                   help='Force LPM to treat current directory as AS project')
    p.add_argument('-lib', '--aslibrary', action='store_true',
                   help='Force LPM to treat current directory as AS library')
    p.set_defaults(func=cmd_init)

    # configure
    p = sub.add_parser('configure', help='Configure deployment targets and Git client')
    p.set_defaults(func=cmd_configure)

    # debug
    p = sub.add_parser('debug', help='Print the list of installed Loupe libraries')
    p.set_defaults(func=cmd_debug)

    # install
    p = sub.add_parser('install', help='Install one or more packages')
    p.add_argument('packages', nargs='*')
    p.add_argument('-src', '--source', action='store_true',
                   help='Use source code for libraries instead of binaries')
    p.set_defaults(func=cmd_install)

    # uninstall
    p = sub.add_parser('uninstall', help='Uninstall one or more packages')
    p.add_argument('packages', nargs='*')
    p.set_defaults(func=cmd_uninstall)

    # git
    p = sub.add_parser('git', help='Open the configured Git client for source-installed packages')
    p.add_argument('packages', nargs='*')
    p.set_defaults(func=cmd_git)

    # publish
    p = sub.add_parser('publish', help='Publish a binary library to the GitHub package registry')
    p.set_defaults(func=cmd_publish)

    # list
    p = sub.add_parser('list', help='List installed dependencies')
    p.add_argument('packages', nargs='*')
    p.set_defaults(func=cmd_list)

    return parser, sub


def _hoist_global_flags(argv):
    """Move -s/--silent and -nc/--nocolor before the subcommand if they appear after it.

    This allows both ``lpm --silent install`` and ``lpm install --silent``.
    """
    global_flags = _GLOBAL_FLAG_SPELLINGS
    prefix = []   # tokens up to and including the subcommand
    suffix = []   # tokens after the subcommand
    cmd_found = False
    for token in argv:
        if not cmd_found:
            prefix.append(token)
            if not token.startswith('-'):
                cmd_found = True
        else:
            if token in global_flags:
                # Insert before the subcommand (last item in prefix).
                prefix.insert(len(prefix) - 1, token)
            else:
                suffix.append(token)
    return prefix + suffix


def _is_known_command(parser, sub, argv):
    """Return True if argv contains a recognized subcommand.

    Walks past leading global flags to find the first positional, then checks
    it against the registered subparsers. This lets us preserve the legacy
    behavior where unknown commands are passed through to npm.
    """
    known = set(sub.choices.keys())
    # Flags that take a value at the top level. Currently none do (--silent
    # and --nocolor are store_true), but keep the structure in case that
    # changes.
    value_flags = set()
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in ('-h', '--help', '-v', '--version'):
            return True  # let argparse handle it
        if token in value_flags:
            i += 2
            continue
        if token.startswith('-'):
            i += 1
            continue
        return token in known
    return False  # no command at all → let argparse error


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------

def main():
    global colored, cprint

    prog_base = os.path.basename(sys.argv[0])
    prog_name = os.path.splitext(prog_base)[0].upper()

    parser, sub = _build_parser(prog_name)

    raw_args = _hoist_global_flags(sys.argv[1:])

    # Legacy behavior: any unrecognized first command is forwarded to npm.
    if raw_args and not _is_known_command(parser, sub, raw_args):
        fallback = argparse.ArgumentParser(add_help=False)
        # Keep these in sync with _GLOBAL_FLAG_SPELLINGS.
        fallback.add_argument('-s', '--silent', action='store_true')
        fallback.add_argument('-nc', '--nocolor', action='store_true')
        ns, leftover = fallback.parse_known_args(raw_args)
        ns.cmd = leftover[0] if leftover else ''
        ns.packages = leftover[1:]
        ns.func = cmd_npm_passthrough  # type: ignore[attr-defined]
    else:
        ns = parser.parse_args(raw_args)

    # Configure output coloring now that --nocolor is known.
    if not ns.nocolor:
        from termcolor import colored as _colored, cprint as _cprint
        colored = _colored
        cprint = _cprint
    else:
        colored = _identity
        cprint = _plain_print

    # If no command was given, show help and exit.
    if not getattr(ns, 'cmd', None):
        parser.print_help()
        return

    # Auth gate.
    if ns.cmd not in _NO_AUTH and not isAuthenticated():
        cprint('No credentials found. Please call lpm login before attempting other operations.', 'yellow')
        return

    # Init gate (commands beyond this point operate on a configured directory).
    if ns.cmd not in _NO_INIT_REQUIRED and not os.path.exists('package.json'):
        cprint('Local directory not initialized. Please run lpm init before attempting other operations.', 'yellow')
        return

    ns.func(ns)


if __name__ == "__main__":
    # Configure colored logger
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    main()
