'''
 * File: lpm_core.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 *
 * This file is part of LPM, licensed under the MIT License.
'''
'''
LPM core functionality.

This module contains the underlying package-management, authentication, manifest
manipulation, and subprocess helpers used by the LPM CLI. The CLI lives in
LPM.py and is responsible for argument parsing and user-facing output;
everything else lives here so it can be reused and tested in isolation.
'''

import os
import os.path
import json
import shutil
import subprocess
import sys
import re
import requests
from urllib.parse import urlparse

from termcolor import colored, cprint

from ASPython import ASTools

import lpm_config


def isAuthenticated():
    command = []
    command.append('npm whoami')
    command.append('--registry=https://npm.pkg.github.com')
    result = executeAndReturnCode(command)
    if result > 0:
        return False
    else:
        return True

def getAuthenticatedUser():
    command = []
    command.append('npm whoami')
    command.append('--registry=https://npm.pkg.github.com')
    # Catch the special case where it's the loupe-devops-admin, as this should be converted to a different user name.
    user = executeAndReturnStdOut(command)
    if (user == 'loupe-devops-admin'):
        return 'default-user'
    else:
        return user

def getLocalToken():
    # Search in the local .npmrc file for this token.
    f = open(os.path.join(os.path.expanduser('~'), '.npmrc'), 'r')
    text = f.readlines()
    return re.search("_authToken=(.+)", "\n".join(text)).group(1)

# Bootstrap the project with required files.
def initializeProject():
    # Check to see if package.json already exists (and don't overwrite if it does).
    if os.path.exists('package.json'):
        print('Package.json already exists, skipping creation')
    else:
        # Set up the package.json file.
        execute(['npm' ,'init', '-y'], True)
        print('Created package.json file')

# Grab a list of existing libraries in the Loupe folder.
def importLibraries():
    arg_folder = False
    try:
        loupePkg = ASTools.Package('./Logical/Libraries/Loupe')
    except:
        err = sys.exc_info()
        print('Loupe folder not found, trying _ARG...')
        try:
            loupePkg = ASTools.Package('./Logical/Libraries/_ARG')
            arg_folder = True
        except:
            print('No existing Loupe libraries found.')
            return
    # Read the list of existing packages.
    packages_to_import = []
    package_versions_to_import = []
    default_scope = lpm_config.get_default_scope()
    for library in loupePkg.objects:
        packages_to_import.append(f'{default_scope}/' + library.text)
        package_versions_to_import.append(library.version)
    # Install them.
    try:
        print('Importing ' + ', '.join(packages_to_import) + '...')
        installPackages(packages_to_import, package_versions_to_import)
        syncPackages(packages_to_import)
    except:
        print(colored('An error occurred while importing the libraries.', 'yellow'))
        return
    return arg_folder
    # # Now delete the ARG folder if it was in there.
    # librariesPkg = ASTools.Package('./Logical/Libraries')
    # librariesPkg.removeObject('_ARG')

# Login silently by manually creating a the .npmrc file in the user directory.
def login(token):
    f = open(os.path.join(os.path.expanduser('~'), '.npmrc'), 'w')
    text = []
    # Write a registry mapping line for every configured scope. All scopes
    # currently share the GitHub Packages host, so a single auth token line
    # covers them. We deduplicate auth lines by host in case a user later
    # configures a non-GitHub registry.
    auth_hosts_written = set()
    for scope, info in lpm_config.get_scopes().items():
        text.append(f'{scope}:registry={info["registry"]}')
    for scope, info in lpm_config.get_scopes().items():
        # Use urlparse so registries with paths (e.g.
        # https://npm.pkg.github.com/some-path) or embedded credentials still
        # produce a clean host for the auth line.
        host = urlparse(info['registry']).netloc
        if not host:
            # Misconfigured registry URL; skip rather than write a broken
            # //<empty>/:_authToken= line.
            continue
        if host in auth_hosts_written:
            continue
        auth_hosts_written.add(host)
        text.append(f'//{host}/:_authToken=' + token)
    f.write('\n'.join(text))
    f.close()

# Logout of the Github registry.
def logout():
    # If there's a local .npmrc file, remove it.
    if(os.path.exists('./.npmrc')):
        os.remove('./.npmrc')
    # And perform the npm logout per configured scope to globally logout as well.
    failed = []
    for scope, info in lpm_config.get_scopes().items():
        command = []
        command.append('npm logout')
        command.append(f'--scope={scope}')
        command.append(f'--registry={info["registry"]}')
        try:
            executeStandard(command)
        except Exception as exc:
            # Don't let a failure on one scope abort the rest, but record
            # the failure so the user knows logout was incomplete.
            failed.append((scope, info['registry'], exc))
    if failed:
        for scope, registry, exc in failed:
            cprint(f"Warning: npm logout failed for {scope} ({registry}): {exc}", 'yellow')

# Remove all LPM references from the project.
def deleteProject():
    if (os.path.isfile('./.npmrc')):
        os.remove('./.npmrc')
    if (os.path.isfile('./package.json')):
        os.remove('./package.json')
    if (os.path.isdir('./node_modules/')):
        shutil.rmtree('./node_modules/')
    if (os.path.isfile('./package-lock.json')):
        os.remove('./package-lock.json')

def configureProject(args):
    try:
        project = ASTools.Project('.')
    except:
        print('Configuration options are only supported at the root level of a project')
        return
    deploymentConfigs = getPackageManifestField('package.json', ['lpmConfig', 'deploymentConfigs'])
    if(deploymentConfigs == None): deploymentConfigs = []
    if (args.nocolor) or (args.silent):
        print('Support for interactive prompts is disabled. Default values will be assigned to the package.json file.')
        print('All configurations in the project are being assigned as deployment targets: ' + ' '.join(project.buildConfigNames))
        setPackageManifestField('package.json', 'deploymentConfigs', project.buildConfigNames)
    else:
        from InquirerPy import inquirer, get_style
        from InquirerPy.base.control import Choice

        # Config question #1: Deployment configurations.
        configOptions = []
        for config in project.buildConfigNames:
            configOptions.append(Choice(config, enabled=(config in deploymentConfigs)))
        print(colored("?", "green") + colored(" Which AS configuration(s) would you like future packages deployed to?", "yellow"))
        configs = inquirer.checkbox(
            message="(press 'space' to toggle one, 'a' to select all, 't' to toggle all)",
            style=get_style({"questionmark": "#00ff00", "pointer": "#ffff00"}),
            choices=configOptions,
            cycle=False,
            keybindings={
                "toggle-all-true": [{ "key": "a"}],
                "toggle-all-false": [{ "key": "t" }]
            }
        ).execute()
        setPackageManifestField('package.json', 'deploymentConfigs', configs)
        if (len(configs) > 0):
            cprint("The following configurations were successfully added to the deployment list: " + ", ".join(configs), "green")
        else:
            cprint("No configurations used for deployments", "green")

        # Config question #2: Configure a Git client.
        # Check to see if there already is a configuration, and if so display that.
        gitClient = getPackageManifestField('package.json', ['lpmConfig', 'gitClient'])
        if(gitClient == None): gitClient = ''
        availableClients = ['GitExtensions', 'GitKraken', 'SourceTree', ''] # Note that these are available but not all supported (=
        configOptions = []
        for client in availableClients:
            if(client == ''):
                configOptions.append(Choice(client, name='None', enabled=(client == gitClient)))
            else:
                configOptions.append(Choice(client, enabled=(client == gitClient)))
        print(colored("?", "green") + colored(" Which Git client would you like to use to introspect source libraries?", "yellow"))
        selectedClient = inquirer.select(
            message="(press 'enter' to select)",
            style=get_style({"questionmark": "#00ff00", "pointer": "#ffff00"}),
            choices=configOptions,
            cycle=False
        ).execute()
        setPackageManifestField('package.json', 'gitClient', selectedClient)
        if (selectedClient != ''):
            cprint(f"{selectedClient} has been configured as the preferred Git client", "green")
        else:
            cprint("No Git client selected", "green")

def getPackageType(path):
    packageType = None
    # Check to see if this directory has a package.json file.
    manifestFilePath = os.path.join(path, 'package.json')
    if os.path.exists(manifestFilePath):
        # First check for the lpm->type metadata.
        packageType = getPackageManifestField(manifestFilePath, ['lpm', 'type'])
    # If the field is not present, or the file is not present, then search manually for an indicative file extension.
    if (packageType == None):
        try:
            project = ASTools.Project(path)
            packageType = 'project'
        except:
            try:
                library = ASTools.Library(path)
                packageType = 'library'
            except:
                try:
                    package = ASTools.Package(path)
                    packageType = 'program'
                except:
                    # Getting here means no matches were found.
                    packageType = None
    if packageType == None:
        return 'undefined'
    else:
        return packageType

# Perform the NPM install.
def installPackages(packages, packageVersions):
    command = []
    command.append('npm install')
    # force packages names to lowercase
    packages = [package.lower() for package in packages]
    for (item, version) in zip(packages, packageVersions):
        if(version != ''):
            command.append(f'{item}@{version}')
        else:
            command.append(item)
    execute(command, False)

# Perform the NPM uninstall.
def uninstallPackages(packages):
    command = []
    command.append('npm uninstall')
    for item in packages:
        command.append(item)
    execute(command, False)

# Install lpm package source by cloning package's repo folder
def installSource(package, version, sourceDependencies=None):
    if sourceDependencies is None:
        sourceDependencies = []
    # Package names are forced to lower case by convention
    package = package.lower()
    repoName = getRepoName(package)
    repoPath = os.path.join('.', 'TempObjects', repoName)
    try:
        if not os.path.isdir(repoPath):
            # Grab the required credentials for inline cloning.
            username = getAuthenticatedUser()
            password = getLocalToken()
            # Clone the repo into the target directory.
            # Resolve the org from the package's scope. We require the scope
            # to be configured rather than silently falling back to the
            # default org -- a typo (e.g. @looupeteam/foo) must not result in
            # a clone from the wrong organization.
            scope = lpm_config.scope_for_package(package)
            if lpm_config.get_scope_info(scope) is None:
                raise Exception(
                    f"Cannot install source for {package}: scope {scope} is not "
                    "configured. Add it to ~/.lpm/config.json or your project's "
                    "lpmConfig.scopes before installing as source."
                )
            org = lpm_config.get_org_for_scope(scope)
            command1 = []
            command1.append('git clone')
            command1.append(f'https://{username}:{password}@github.com/{org}/{repoName}')
            command1.append(repoPath)
            execute(command1, False)
        else:
            # Folder exists already.
            if '.git' in os.listdir(repoPath):
                print(f"Repository for package {package} already exists. Cloning skipped.")
            else:
                raise Exception(f"{package} repository folder \"{repoName}\" exists, but does not contain expected structure.")

        # And then checkout the correct commit if it's been specified.
        if (version != ''):
            command1b = []
            command1b.append(f'git -C {repoPath} checkout')
            command1b.append(version)
            execute(command1b, False)

        # Retrieve package source location via repo's Jenkinsfile
        packageSourcePath = getPackageSourcePathFromRepoPackage(repoPath, package)

        # Get lpm package type from package.json data
        packageType = getPackageType(packageSourcePath)

        # Install according to specifics of package type
        if packageType in ['library']:
            packageDestination = './Logical/Libraries/Loupe'
            createPackageTree(packageDestination)
        elif packageType in ['program', 'package']:
            # Get AS package for destination
            packageManifest = os.path.join(packageSourcePath, 'package.json')
            packageDestination = getPackageDestination(packageManifest)
        else:
            raise Exception("Unsupported LPM package type. Cannot install as source.")

        # Add the new directory to the parent's .pkg as a reference.
        targetAsPackage = ASTools.Package(packageDestination)
        targetAsPackage._addPkgObject(packageSourcePath, reference=True)

        if packageType in ['library']:
            packageSourceDependencies = getLibrarySourceDependencies(packageSourcePath)
        elif packageType in ['program', 'package']:
            packageSourceDependencies = getProgramSourceDependencies(packageSourcePath)

        if (len(packageSourceDependencies) > 0):
            # TODO: add support for getting the correct version of these dependencies.
            installPackages(packageSourceDependencies, [''] * len(packageSourceDependencies))
            # Aaand sync those dependencies.
            syncPackages(getAllDependencies(packageSourceDependencies))

        # add to source dependencies list and remove duplicates
        sourceDependencies += getAllDependencies(packageSourceDependencies)
        sourceDependencies = list(set(sourceDependencies))

        # save sourceInfo in json
        sourceInfoFilePath = os.path.join(".", "TempObjects", "sourceInfo.json")
        sourceInfo = getJsonData(sourceInfoFilePath)
        sourceInfo[package] = {}
        sourceInfo[package]["repoPath"] = repoPath
        sourceInfo[package]["packageSourcePath"] = packageSourcePath
        sourceInfo[package]['logicalPath'] = os.path.join(packageDestination, os.path.normpath(packageSourcePath).split(os.sep)[-1])
        saveJsonData(sourceInfo, sourceInfoFilePath)
    except Exception as e:
        raise Exception(f"Error installing source for '{package}': {e}") from e

# Get destination of LPM package using manifest, defaulting if unspecified
def getPackageDestination(packageManifestPath):
    manifestPackageDestination = getPackageManifestField(packageManifestPath, ['lpm', 'logical', 'destination'])
    # If an explicit destination exists, use that. Otherwise default to Logical root.
    if manifestPackageDestination != None:
        packageDestination = os.path.join('Logical', manifestPackageDestination)
    else:
        packageDestination = 'Logical'
    createPackageTree(packageDestination)
    return packageDestination

# Get package source paths from Jenkinsfile
def getPackageSourcePaths(repoPath):
    jenkinsfilePath = os.path.join(repoPath, 'Jenkinsfile')
    if os.path.exists(jenkinsfilePath):
        with open(jenkinsfilePath) as j:
            rePackagesToPublishArrayContents = r"packagesToPublish\s*:\s*\[(.*)\]"
            for line in j:
                match = re.search(rePackagesToPublishArrayContents, line)
                if match:
                    arrayContents = match.group(1)
                    reArrayElement = r"\b[\w\\\/]+\b"
                    matches = re.findall(reArrayElement, arrayContents)
                    packageSourcePaths = []
                    for match in matches:
                        packageSourcePaths.append(os.path.join(repoPath, os.path.normpath(match)))
                    return packageSourcePaths

        # default, return empty array
        return []
    else:
        return []

# Given a repo and a package name, find the package source paths and return the one that either
#   contains a package.json file with the right "name" value
#   OR the last folder matches the name and the folder contains a .lby file
# This function helps resolve the path in the case that a repo has multiple packages (e.g a library and a prog)
def getPackageSourcePathFromRepoPackage(repoPath, packageName: str):
    packageSourcePaths = getPackageSourcePaths(repoPath)
    for path in packageSourcePaths:
        packageJson = os.path.join(path, 'package.json')
        if os.path.exists(packageJson):
            with open(packageJson) as p:
                data = json.load(p)
                if packageName.lower() == data.get("name", "").lower():
                    return path
        else:
            splitPath = os.path.normpath(path).split(os.sep)
            basePackageName = os.path.split(packageName)[1]
            if splitPath[-1].lower() == basePackageName:
                for file in os.listdir(path):
                    (root, ext) = os.path.splitext(file)
                    if ext == '.lby':
                        return path

    # Fallback: no Jenkinsfile or no match found — search the repo root then
    # walk through 'src' and 'source' directories for a subdirectory that
    # contains a matching package.json or a .lby file.
    basePackageName = os.path.split(packageName)[1].lower()

    def _find_in_tree(search_root):
        for dirpath, dirnames, filenames in os.walk(search_root):
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
            packageJsonPath = os.path.join(dirpath, 'package.json')
            if os.path.exists(packageJsonPath):
                with open(packageJsonPath) as p:
                    try:
                        data = json.load(p)
                        if packageName.lower() == data.get('name', '').lower():
                            return dirpath
                    except json.JSONDecodeError:
                        pass
            if os.path.basename(dirpath).lower() == basePackageName:
                if any(os.path.splitext(f)[1] == '.lby' for f in filenames):
                    return dirpath
        return None

    # Check repo root itself first, then recurse into src/source only.
    search_dirs = [repoPath] + [
        os.path.join(repoPath, d) for d in ('src', 'source')
        if os.path.isdir(os.path.join(repoPath, d))
    ]
    for search_dir in search_dirs:
        result = _find_in_tree(search_dir)
        if result is not None:
            return result

    raise ValueError(
        f"Could not find source path for package '{packageName}' in repo '{repoPath}'. "
        "No Jenkinsfile packagesToPublish entry and no matching directory found."
    )

def getJsonData(jsonFilePath):
    # Create file only if it doesn't already exist
    try:
        with open(jsonFilePath, 'x'):
            pass
    except FileExistsError:
        pass

    with open(jsonFilePath, 'r+') as fp:
        # Load to dictionary
        try:
            data = json.load(fp)
        except:
            data = {}

    return data

def saveJsonData(data: dict, jsonFilePath):
    with open(jsonFilePath, 'w') as fp:
        json.dump(data, fp, indent=2)

def openDocumentation(packages):
    command = []
    command.append('npm docs')
    for item in packages:
        command.append(item)
    execute(command, False)

def getInfo(package, options):
    command = []
    command.append('npm view')
    command.append(package)
    for item in options:
        command.append(item)
    execute(command, False)

# Create a list of Loupe libraries that are currently in the AS project.
def readLoupeLibraryList():
    libraryList = []
    try:
        loupePkg = ASTools.Package(os.path.join('.', 'Logical', 'Libraries', 'Loupe'))
        for element in loupePkg.objects:
            libraryName = element.text
            lib = ASTools.Library(os.path.join('.', 'Logical', 'Libraries', 'Loupe', libraryName))
            libraryList.append(lib.name + '@' + lib.version)
    except:
        # No Loupe folder, so the list should be null.
        return
    return libraryList

# Retrieves repo name of a package by fetching data from GitHub
def getRepoName(package):
    (error, data) = getPackageData(package)
    if error is None:
        fullUrl = data.get('repository', {}).get('html_url', None)
        if fullUrl is None:
            print("Unable to process package data")
            return None
        # Return final folder of URL
        repoName = fullUrl.split('/')[-1]
        return repoName
    else:
        print(error)
        return None

# Retrieve a deep list of all dependencies of the specified packages.
# This is recursive logic that hurts my brain, but seems to work.
def getAllDependencies(packages):
    dependencies = []
    for package in packages:
        # Introspect the package.json for this file. Find its 'lpm/type' field.
        packageManifest = os.path.join('node_modules', package, 'package.json')
        packageType = getPackageManifestField(packageManifest, ['lpm', 'type'])
        # When dealing with an HMI project, don't parse through its dependencies recursively! That gets deep real fast.
        if(packageType == 'hmi-project'):
            return packages
        dependencies.append(package)
        # If package.json exists, get dependencies from there.
        if(os.path.exists(os.path.join('node_modules', package, 'package.json'))):
            dependencyData = getPackageManifestField(os.path.join('node_modules', package, 'package.json'), ['dependencies'])
            if(dependencyData == None):
                dependencyData = []
        # If there is no package.json for this package, assume it's a source library, and that it's already sync'd
        # to the Logical View under Libraries / Loupe.
        else:
            # Strip it of its @<scope> prefix.
            splitPackage = os.path.split(package)[1]
            dependencyData = getLibrarySourceDependencies(os.path.join('.', 'Logical', 'Libraries', 'Loupe', splitPackage))
            print('Source dependencies: ')
            print(dependencyData)
        localDependencies = []
        for item in dependencyData:
            localDependencies.append(item)
        nestedDependencies = getAllDependencies(localDependencies)
        for item in nestedDependencies:
            dependencies.append(item)
    # Before returning the list, sanitize it by removing duplicates.
    sanitizedDependencies = []
    for dep in dependencies:
        lowerdep = dep.lower()
        if lowerdep not in sanitizedDependencies:
            sanitizedDependencies.append( lowerdep )
    return sanitizedDependencies

def getLibrarySourceDependencies(libraryPath):
    sourceLibrary = ASTools.Library(libraryPath)
    dependencyNames = []
    # TODO: probe every configured scope rather than only the default scope.
    # Today this only resolves dependencies that live under the default scope's
    # registry; cross-scope dependencies need to be encoded explicitly upstream.
    default_scope = lpm_config.get_default_scope()
    # Install binary dependencies for this library
    for dependency in sourceLibrary.dependencies:
        # First check to see if it's a known package in the default scope (if not, ignore it).
        command = []
        command.append('npm view')
        command.append(f'{default_scope}/{dependency.name}')
        result = executeAndReturnCode(command)
        if result == 0:
            print('Dependency found: ' + f'{default_scope}/{dependency.name.lower()}')
            # Add this dependency to our list.
            dependencyNames.append(f'{default_scope}/{dependency.name}'.lower())
    return dependencyNames

def getProgramSourceDependencies(programSourcePath):
    dependencyData = getPackageManifestField(os.path.join(programSourcePath, 'package.json'), ['dependencies'])
    dependencyNames = []
    for key, value in dependencyData.items():
        print('Dependency found: ' + str(key))
        dependencyNames.append(key)
    return dependencyNames

# Synchronize a package from the node_modules folder into the appropriate directory.
def syncPackages(packages):
    try:
        # First check to see if we're in an AS project root directory.
        project = ASTools.Project('.')
    except:
        project = None
    for package in packages:
        # Introspect the package.json for this file. Find its 'lpm' section.
        packageManifest = os.path.join('node_modules', package, 'package.json')
        packageType = getPackageManifestField(packageManifest, ['lpm', 'type'])
        # Do something different based on package type.
        if(packageType == 'project'):
            # Copy starter project into root directory.
            shutil.copytree(os.path.join('node_modules', package), '.', dirs_exist_ok=True, ignore=shutil.ignore_patterns('package.json'))

        if(packageType == 'hmi-project'):
            # Copy starter project into root directory.
            shutil.copytree(os.path.join('node_modules', package), '.', dirs_exist_ok=True)

        elif(project == None):
            # Skip sync'ing of other types (packages or libraries) if we're not in a project.
            pass

        elif((packageType == 'program') | (packageType == 'package')):
            destination = getPackageDestination(packageManifest)
            # Find the module(s) in node_modules across every configured scope, and sync it/them.
            for scope in lpm_config.get_scopes().keys():
                scopeDir = os.path.join('node_modules', scope)
                if not os.path.isdir(scopeDir):
                    continue
                for module in os.listdir(scopeDir):
                    if (os.path.join(scope, module) == os.path.normpath(package)):
                        # Get a handle on the folder destination.
                        destinationPkg = ASTools.Package(destination)
                        # Create a list of filtered objects that don't get copied over.
                        filter = ['package.pkg', 'license', 'readme.md', 'package.json', 'changelog.md']
                        # Loop through all contents in the source directory and copy them over one by one.
                        for item in os.listdir(os.path.join(scopeDir, module)):
                            if (item.lower() not in filter):
                                # If the item already exists, delete it.
                                destinationItem = os.path.join(destination, item)
                                if os.path.exists(destinationItem):
                                    destinationPkg.removeObject(item)
                                destinationPkg.addObject(os.path.join('node_modules', package, item))

        elif(packageType == 'library') or (packageType == None):
            packageDestination = getPackageManifestField(packageManifest, ['lpm', 'logical', 'destination'])
            # If an explicit destination exists, use that. Otherwise default to Logical root.
            if packageDestination != None:
                destination = os.path.join('Logical', packageDestination)
            else:
                destination = os.path.join('Logical', 'Libraries', 'Loupe')
            # Now create the packages in this path that doesn't exist.
            createPackageTree(destination)
            # Find the module(s) in node_modules across every configured scope, and sync it/them.
            for scope in lpm_config.get_scopes().keys():
                scopeDir = os.path.join('node_modules', scope)
                if not os.path.isdir(scopeDir):
                    continue
                for module in os.listdir(scopeDir):
                    if (os.path.join(scope, module) == os.path.normpath(package)):
                        # Get a handle on the library's parent folder.
                        parentPkg = ASTools.Package(destination)
                        # If the library already exists, delete it.
                        libraryPath = os.path.join(destination, module)
                        if os.path.isdir(libraryPath):
                            parentPkg.removeObject(module)
                        parentPkg.addObject(os.path.join('node_modules', package))

def deployPackages(config, packages):
    # Figure out where the deployment table is for this configuration.
    configPath = os.path.join('Physical', config)
    cpuFolderName = [x for x in os.listdir(configPath) if os.path.isdir(os.path.join(configPath, x))]
    deploymentTable = ASTools.SwDeploymentTable(os.path.join('Physical', config, cpuFolderName[0], 'cpu.sw'))
    configPackage = ASTools.CpuConfig(os.path.join('Physical', config, cpuFolderName[0], 'cpu.pkg'))
    for package in packages:
        # Check if the package.json exists in node_modules - if it doesn't, then assume that it is a source library.
        if(os.path.exists(os.path.join('node_modules', package, 'package.json'))):
            # Introspect the package.json for this package. Find its 'lpm' section.
            packageManifest = os.path.join('node_modules', package, 'package.json')
            packageType = getPackageManifestField(packageManifest, ['lpm', 'type'])

            # Do something different based on package type.
            if(packageType == 'library') or (packageType == None):
                libraryLocation = getPackageManifestField(packageManifest, ['lpm', 'logical', 'destination'])
                if (libraryLocation == None):
                    libraryLocation = os.path.join('Libraries', 'Loupe')
                libraryAttributes = getLibraryAttributes(packageManifest, config)
                # Deploy the required library.
                deploymentTable.deployLibrary(os.path.join('Logical', libraryLocation), os.path.split(package)[1], libraryAttributes)

            elif((packageType == 'program') | (packageType == 'package')):
                cpuDeployment = getPackageManifestField(packageManifest, ['lpm', 'physical', 'cpu'])
                taskLocation = getPackageDestination(packageManifest)
                # First deploy all configured tasks.
                if cpuDeployment != None:
                    for item in cpuDeployment:
                        deploymentTable.deployTask(taskLocation, item['source'], item['destination'])
                # Next perform additional configuration changes.
                # Set the pre-build step if it exists.
                preBuildCommand = getPackageManifestField(packageManifest, ['lpm', 'physical', 'configuration', 'preBuildStep'])
                if (preBuildCommand != None):
                    configPackage.setPreBuildStep(preBuildCommand)

        # No package.json is present in node_modules - so it's a source library.
        else:
            sourceInfoFilePath = os.path.join(".", "TempObjects", "sourceInfo.json")
            sourceInfo = getJsonData(sourceInfoFilePath)
            packageSourceInfo = sourceInfo[package]
            packageManifest = os.path.join(packageSourceInfo['packageSourcePath'], 'package.json')
            packageType = getPackageType(packageSourceInfo['packageSourcePath'])
            if packageType in ['library']:
                libraryLocation = os.path.join('Libraries', 'Loupe')
                libraryAttributes = getLibraryAttributes(packageManifest, config)

                # Special case logic: convert AdditionalLibraryDirectories attribute path from logical to actual
                if "AdditionalLibraryDirectories" in libraryAttributes:
                    libraryAttributes["AdditionalLibraryDirectories"] = ASTools.getActualPathFromLogicalPath(libraryAttributes["AdditionalLibraryDirectories"])

                # Deploy the required library.
                deploymentTable.deployLibrary(os.path.join('Logical', libraryLocation), os.path.split(package)[1], libraryAttributes)
            elif packageType in ['program', 'package']:
                sourceInfoFilePath = os.path.join(".", "TempObjects", "sourceInfo.json")
                sourceInfo = getJsonData(sourceInfoFilePath)
                packageSourceInfo = sourceInfo[package]
                cpuDeployment = getPackageManifestField(packageManifest, ['lpm', 'physical', 'cpu'])

                logicalPackagePath = os.path.normpath(packageSourceInfo['logicalPath'])

                if cpuDeployment != None:
                    for item in cpuDeployment:
                        deploymentTable.deployTask(logicalPackagePath, item['source'], item['destination'])

def getLibraryAttributes(packageManifest, config):
    libraryCpus = getPackageManifestField(packageManifest, ['lpm', 'physical', 'cpu'])
    try:
        if (type(libraryCpus) == list):
            for cpu in libraryCpus:
                try:
                    if(cpu['config'].lower() == config.lower()):
                        return cpu['attributes']
                except Exception as e:
                    return cpu['attributes']
        else:
            try:
                return libraryCpus['attributes']
            except Exception as e:
                return {}
    except Exception as e:
        return {}
    return {}

def createPackageTree(packages: list):
    # Retrieve this as a list of folders for creation.
    normalizedDestination = os.path.normpath(packages)
    packageList = normalizedDestination.split(os.sep)
    for i in range(len(packageList)):
        try:
            # Check for package existence.
            pkg = ASTools.Package(os.path.join(*packageList[:i+1]))
        except:
            # Package does not exist, so create it.
            # First retrieve handle of its parent package.
            parentPkg = ASTools.Package(os.path.join(*packageList[:i]))
            pkg = parentPkg.addEmptyPackage(packageList[i])

def createLibraryManifest(package, lpmConfig):
    library = ASTools.Library('.')
    default_scope = lpm_config.get_default_scope()
    default_org = lpm_config.get_org_for_scope(default_scope)
    # Create dependencies dictionary for this library
    dependency_dict = {}
    for dependency in library.dependencies:
        # First check to see if it's a known package in the default scope (if not, ignore it).
        cmd = []
        cmd.append('npm view')
        cmd.append(f'{default_scope}/{dependency.name}')
        result = executeAndReturnCode(cmd)
        if result == 0:
            version = []
            if dependency.minVersion != '':
                version.append(f'>={library._formatVersionString(dependency.minVersion)}')
            if dependency.maxVersion != '':
                version.append(f'<={library._formatVersionString(dependency.maxVersion)}')
            if len(version) == 0:
                version.append('*')
            dependency_dict.update({f'{default_scope}/{dependency.name.lower()}':' '.join(version)})
    # Make sure there's a top level description available.
    if (library.description == ''):
        description = f"{package.lower()} library for Automation Runtime"
    else:
        description = library.description
    # Set the homepage. Only emit the LoupeDocs URL when publishing under the
    # @loupeteam scope; other scopes can override later via a future
    # `docsUrlTemplate` config option.
    if default_scope == lpm_config.DEFAULT_SCOPE:
        homepage = f'https://loupeteam.github.io/LoupeDocs/libraries/{package.lower()}.html'
    else:
        homepage = ''
    # Ensure the lpmConfig has the proper type set.
    try:
        if lpmConfig['type'] != 'library':
            lpmConfig = { 'type': 'library' }
    except Exception:
        lpmConfig = { 'type': 'library' }
    # Create dictionary that will hold all values for the package.json file
    manifest_dict = {
                'name': f'{default_scope}/{package.lower()}',
                'version': library._formatVersionString(library.version),
                'description': description,
                'homepage': homepage,
                'scripts': {},
                'keywords': [],
                'author': default_org,
                'license': 'MIT',
                'repository': {
                    'type': 'git',
                    'url': f'https://github.com/{default_org}/' + package
                },
                'lpm': lpmConfig,
                'dependencies': dependency_dict
                }
    # Convert to JSON and create the file
    manifest_json = json.dumps(manifest_dict, indent=2)
    f = open('.\\package.json', 'w')
    f.write(manifest_json)
    f.close()
    return

def getPackageManifestData(manifest):
    f = open(manifest, 'r+', encoding='utf-8')
    data = json.load(f)
    f.close()
    return data

def getPackageManifestField(manifest, fieldPath: list):
    data = getPackageManifestData(manifest)
    try:
        for item in fieldPath:
            data = data[item]
        return data
    except:
        return None

def setPackageManifestField(manifest, fieldName, fieldData):
    readFile = open(manifest, 'r+')
    data = json.load(readFile)
    readFile.close()
    # If the lpmConfig key isn't in there yet, add it first.
    if(not "lpmConfig" in data):
        data["lpmConfig"] = {}
    data["lpmConfig"][fieldName] = fieldData
    jsonData = json.dumps(data, indent=2)
    writeFile = open(manifest, 'w')
    writeFile.write(jsonData)
    writeFile.close()

def printLoupePackageList():
    print("Retrieving package data...")
    (error, data) = getPackageListData()

    if error:
        print(f"Unable to print package list: {error}")
        return

    if not data:
        print("No packages found.")
        return

    packages_sorted = sorted(data, key=lambda x: x["name"])

    # Pre-process package descriptions; these are handled separately, as they can be None.
    package_descriptions = []
    for package in packages_sorted:
        try:
            if package['repository']['description'] is not None:
                package_descriptions.append(package['repository']['description'])
            else:
                package_descriptions.append(" ")
        except:
            package_descriptions.append(" ")

    # Determine column widths.
    name_col_width = max(len(package["name"]) for package in packages_sorted) + 2
    scope_col_width = max((len(package.get("_lpm_scope", "")) for package in packages_sorted), default=6) + 2
    scope_col_width = max(scope_col_width, len("SCOPE") + 2)
    version_col_width = 12
    lastmod_col_width = 14
    description_col_width = max((len(description) for description in package_descriptions), default=len("DESCRIPTION"))

    # Print the header.
    print(  "NAME".ljust(name_col_width) +
            "SCOPE".ljust(scope_col_width) +
            "VERSIONS".ljust(version_col_width) +
            "LASTUPDATED".ljust(lastmod_col_width) +
            "DESCRIPTION".ljust(description_col_width))
    print(  "----".ljust(name_col_width) +
            "-----".ljust(scope_col_width) +
            "--------".ljust(version_col_width) +
            "-----------".ljust(lastmod_col_width) +
            "-----------".ljust(description_col_width))

    for idx, package in enumerate(packages_sorted):
        print(  package["name"].ljust(name_col_width) +
                package.get("_lpm_scope", "").ljust(scope_col_width) +
                str(package["version_count"]).ljust(version_col_width) +
                package["updated_at"][:10].ljust(lastmod_col_width) +
                package_descriptions[idx].ljust(description_col_width))

# Fetches data using GitHub API (See https://docs.github.com/en/rest/packages?apiVersion=2022-11-28#list-packages-for-an-organization)
# When `scope` is None, queries every configured scope's org and concatenates the
# results, tagging each entry with its originating scope under `_lpm_scope`.
# Returns (error, data) tuple.
def getPackageListData(scope=None):
    token = getLocalToken()
    headers = { 'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28' }

    if scope is None:
        scopes_to_query = list(lpm_config.get_scopes().items())
    else:
        info = lpm_config.get_scope_info(scope)
        if info is None:
            return (f"Unknown scope: {scope}", [])
        scopes_to_query = [(scope, info)]

    all_packages = []
    errors = []
    for scope_name, info in scopes_to_query:
        organization = info['org']
        page = 1
        per_page = 100
        all_packages_gathered = False
        while not all_packages_gathered:
            params = {  'package_type': 'npm',
                        'page': str(page),
                        'per_page': str(per_page) }
            try:
                r = requests.get(f'https://api.github.com/orgs/{organization}/packages', headers=headers, params=params, timeout=5)
            except requests.RequestException as exc:
                errors.append(f"{scope_name} ({organization}): {exc}")
                break
            if r.status_code != 200:
                errors.append(f"{scope_name} ({organization}): status {r.status_code} - {r.text}")
                break
            retrieved_packages = json.loads(r.content)
            for pkg in retrieved_packages:
                pkg['_lpm_scope'] = scope_name
            all_packages += retrieved_packages
            all_packages_gathered = len(retrieved_packages) < per_page
            page += 1

    if not all_packages and errors:
        return ("; ".join(errors), [])
    if errors:
        # Surface partial failures via stderr-ish print but still return data.
        print("Warning: some scopes failed to query: " + "; ".join(errors))
    print(f"Retrieved {len(all_packages)} packages total. See below for detailed information.")
    return (None, all_packages)

# Backward-compatible alias for callers that still expect the old name.
def getLoupePackageListData():
    return getPackageListData()

# Fetches data using GitHub API for a single package; resolves the org from the
# package's @scope prefix.
# Returns (error, data) tuple.
def getPackageData(packageName: str):
    token = getLocalToken()
    headers = { 'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28' }
    organization = lpm_config.org_for_package(packageName)

    packageNameStripped = lpm_config.strip_scope(packageName)
    r = requests.get(f'https://api.github.com/orgs/{organization}/packages/npm/{packageNameStripped}', headers=headers, timeout=5)
    if r.status_code != 200:
        error = "Status code not OK. Code: " + str(r.status_code) + "\n" + r.text
        return (error, [])  # Early return
    packageData = json.loads(r.content)
    return (None, packageData)

# Backward-compatible alias.
def getLoupePackageData(packageName: str):
    return getPackageData(packageName)

# Run a generic NPM command on the specified packages.
def runGenericNpmCmd(cmd, packages):
    command = []
    command.append('npm')
    command.append(cmd)
    for item in packages:
        command.append(item)
    execute(command, False)

# Execute a generic batch script command.
def execute(cmd, quiet):
    #process = subprocess.Popen(' '.join(cmd), encoding="utf-8", errors='replace', shell=True)
    process = subprocess.Popen(' '.join(cmd), stdout=subprocess.PIPE, encoding="utf-8", errors='replace', shell=True)
    while process.returncode == None:
        rawStdOut = process.stdout.readline()
        #rawStdErr = process.stderr.readline()
        strippedStdOut = rawStdOut.rstrip()
        #strippedStdErr = rawStdErr#.rstrip()
        if (not quiet):
            if (strippedStdOut != ''):
                print(strippedStdOut)
            # if (strippedStdErr != ''):
            #     cprint(strippedStdErr, 'red')
        process.poll()
    if (process.returncode != 0):
        raise Exception('Error during process execution')

def executeStandard(cmd):
    process = subprocess.Popen(' '.join(cmd), encoding="utf-8", errors='replace', shell=True)
    while process.returncode == None:
        process.poll()
    if (process.returncode != 0):
        raise Exception('Error during process execution')

def executeAndContinue(cmd):
    process = subprocess.Popen(' '.join(cmd), encoding="utf-8", errors='replace', shell=True)
    return

def executeAndReturnCode(cmd):
    process = subprocess.Popen(' '.join(cmd), encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE, errors='replace', shell=True)
    while process.returncode == None:
        process.poll()
    return process.returncode

def executeAndReturnStdOut(cmd):
    process = subprocess.Popen(' '.join(cmd), stdout=subprocess.PIPE, encoding="utf-8", errors='replace', shell=True)
    std_out = ''
    while process.returncode == None:
        rawStdOut = process.stdout.readline()
        strippedStdOut = rawStdOut.rstrip()
        std_out = std_out + strippedStdOut
        process.poll()
    return std_out
