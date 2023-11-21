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
'''

__version__ = '1.0.0'
__author__ = 'Andrew Musser'

# Python modules
import os.path
import json
import shutil
import subprocess
import sys
import re
import argparse
import logging
import ctypes
import time
import requests

# External Modules
from ASPython import ASTools

def main():

    # Extract the name. Probably could just hard-code this to 'LPM'. 
    prog_base = os.path.basename(sys.argv[0])
    prog_split = os.path.splitext(prog_base)
    prog_name = prog_split[0].upper()

    # Parse arguments from the command line 
    parser = argparse.ArgumentParser(description='A lightweight wrapper around NPM for Automation Studio dependency management', prog=prog_name)
    parser.add_argument('cmd', type=str, help='LPM command to execute (init, install, uninstall, list, etc)', default='')
    parser.add_argument('packages', type=str, nargs='*', help='the packages to be acted upon', default='') 
    parser.add_argument('-s', '--silent', action='store_true', help='Execute commands silently with default values and no operator prompts')
    parser.add_argument('-prj', '--asproject', action='store_true', help='Force LPM to treat current directory as AS project')
    parser.add_argument('-lib', '--aslibrary', action='store_true', help='Force LPM to treat current directory as AS library')
    parser.add_argument('-src', '--source', action='store_true', help='Use source code for libraries instead of binaries')
    parser.add_argument('-nc', '--nocolor', action='store_true', help='Dont color the output - to avoid dependency on termcolor')
    parser.add_argument('-t', '--token', type=str, help='Personal Access Token required for silent login')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s: ' + __version__)
    args = parser.parse_args()

    # Handle output coloring configuration. 
    if (not args.nocolor):
        from termcolor import colored, cprint
    else:
        # If the colors are skipped, then define dummy versions of termcolor functions. 
        def colored(text, color):
            return text
        def cprint(text, color):
            print(text)

    # Prepend the @loupeteam prefix to all package names, and split any @version suffixes off into separate struct.
    packages = []
    packageVersions = []
    if(args.packages):   
        for item in args.packages:
            # Force package name to lowercase, by convention
            item = item.lower()
            # If the @ character is present, it means there's a version specifier.
            if('@' in item):
                splitItem = item.split('@')
                packages.append('@loupeteam/' + splitItem[0])
                packageVersions.append(splitItem[1])
            # Othersie, version string is empty.
            else:
                packages.append('@loupeteam/' + item)
                packageVersions.append('')

    # Authenticate with a custom personal access token. 
    if(args.cmd == 'login'):
        if not args.silent:
            cprint('Please follow the prompts below to log in using valid Github credentials.', 'yellow')
            token = input(colored('? ', 'green') + 'Enter your personal access token: ')
            login(token)
        else:
            login(args.token)
        if isAuthenticated():
            print(colored(f'New credentials for {getAuthenticatedUser()} successfully stored.', 'green'))
        else:
            print(colored('Error: invalid credentials. Please try again.', 'red'))

    # Remove all local files related to LPM.
    elif(args.cmd == 'delete'):
        print('Removing LPM content from the local project...')
        deleteProject()
        print(colored('All done!', 'green'), 'Thanks for using LPM.')
        print(colored('Note: LPM-installed content within your AS project folder has not been removed.', 'yellow'))

    # Report on the overall status of LPM. 
    elif(args.cmd == 'status'):
        print('Retrieving status...')
        # Check to see if we're logged in globally. 
        if(isAuthenticated()):
            print('-> Logged in: ' + colored('Yes', 'green'))
            print('-> Current user: ' + colored(getAuthenticatedUser(), 'green'))
        else:
            print('-> Logged in: ' + colored('No', 'yellow'))
        # Check to see if we're initialized with a package.json file.
        if os.path.exists('package.json'):
            packageType = getPackageType('.')
            # Now print out status message based on packageType
            if(packageType == 'project'):
                print('-> Local directory status: ' + colored('Initialized with Automation Studio project', 'green'))
            elif(packageType == 'library'):
                print('-> Local directory status: ' + colored('Initialized with local library', 'green'))
            elif((packageType == 'program') | (packageType == 'package')):
                print('-> Local directory status: ' + colored('Initialized with local program', 'green'))
            else:
                print('-> Local directory status: ' + colored('Initialized as stand-alone package manager', 'green'))
        else:
            print('-> Local directory status: ' + colored('Not initialized for use with lpm', 'yellow'))

    # Check to see if the user is logged in. 
    elif(not isAuthenticated()):
        cprint('No credentials found. Please call lpm login before attempting other operations.', 'yellow')

    # Process commands that require authentication. 
    else:

        # Logout of the Github registry.
        if(args.cmd == 'logout'):
            print('Logging out...')
            logout()
            print(colored('Successfully logged out.', 'green'))

        # View information about a package. 
        elif(args.cmd == 'view') | (args.cmd == 'info'):
            if (len(args.packages) > 1):
                options = args.packages[1:]
                getInfo(packages[0], options)
            elif (len(args.packages) > 0):
                options = []
                getInfo(packages[0], options)
            else:
                print(colored('Please provide the name of one package.', 'yellow'))

        # View a list of all available packages. 
        elif(args.cmd == 'viewall'):
            printLoupePackageList()

        # Retrieve the type of a package (or directory). 
        elif(args.cmd == 'type'):
            if (len(packages) > 1):
                print(colored('This command is only supported with a single package.', 'yellow'))
            else:
                print(getPackageType(args.packages[0]))

        # Open up documentation page for the library.
        elif(args.cmd == 'docs'):
            if (len(packages) > 0):
                print('Opening up documentation for ' + ', '.join(packages) + '...')
                openDocumentation(packages)
                print(colored('Documentation is now up in your browser.', 'green'))
            else:
                print(colored('Please provide the name of at least one package.', 'yellow'))

        # Open up the project in Automation Studio. 
        elif(args.cmd == 'as'):
            project = ASTools.Project('.')
            cmd = []
            print('Opening Automation Studio...')
            asBin = os.path.join(ASTools.getASPath(project.ASVersion), 'pg.exe')
            if(not os.path.isfile(asBin)):
                cprint(f'Project was last opened with {project.ASVersion}, but that version is not installed. Trying to open with AS410 instead...', 'yellow')
                # If that version isn't installed, try something else. Just hard-coding 410 for now because it's what I have installed!
                asBin = os.path.join(ASTools.getASPath('AS410'), 'pg.exe')
            cmd.append(asBin)
            cmd.append('\"' + os.path.join(os.getcwd(), f'{project.name}.apj') + '\"')
            executeAndContinue(cmd)
            time.sleep(3)
            cprint('Wait for it...', 'yellow')
            time.sleep(3)
            cprint('Still working...', 'yellow')
            time.sleep(3)
            cprint('Almost done...', 'yellow')
            time.sleep(3)
            cprint('Good to go!', 'green')

        # Set up the local directory for package management.
        elif(args.cmd == 'init'):
            as_project = False
            as_library = False

            # Check to see if the current directory is an AS project.
            try:
                project = ASTools.Project('.')
                as_project = True      
            except:
                as_project = False

            # Check to see if the current directory is an AS library.
            try:
                library = ASTools.Library('.')
                as_library = True
            except:
                as_library = False
                
            # Handle AS project.
            if (as_project) or (args.asproject):
                print('Automation Studio project found, initializing package manager...')
                initializeProject()
                arg_folder = False
                if(not args.silent):
                    text = input(colored('? ', 'green') + colored('Would you like to initialize LPM with the existing Loupe libraries in your Automation Studio project?', 'yellow') + ' (y/N) ')
                    if (text.lower() == 'y') | (text.lower() == 'yes'):
                        arg_folder = importLibraries()
                configureProject(args)
                cprint('Your Automation Studio project is now ready to be used with LPM.', 'green')
                if (arg_folder):
                    cprint('Note that you will need to manually remove the _ARG folder to avoid library conflicts.', 'yellow')

            # Handle AS library. 
            elif (as_library) or (args.aslibrary):
                # Prepare a library for publication.   
                name = os.path.basename(os.getcwd())
                packageData = {}
                # Check for existing package.json, and extract important info. 
                if(os.path.exists('package.json')):
                    print('Found an existing package.json file, extracting its relevant contents...')
                    packageData = getPackageManifestField('package.json', ['lpm'])
                print('Creating package.json for the ' + colored(f'{name}', 'yellow') + ' library...')
                createLibraryManifest(name, packageData)
                print(colored('The package.json was successfully created.', 'green'))

            else:
                if(not args.silent):
                    text = input(colored('? ', 'green') + colored('No Automation Studio project found. Would you like to initialize this directory with a starter AS project?', 'yellow') + ' (Y/n) ')
                else:
                    text = 'n'
                if (text.lower() == 'n') | (text.lower() == 'no'):
                    initializeProject()
                    print(colored('This directory has been initialized as a stand-alone package manager.', 'green'))
                else:
                    initializeProject()
                    starterProject = ['@loupeteam/starterasproject49']
                    installPackages(starterProject, [''])
                    syncPackages(starterProject)
                    configureProject(args)
                    print(colored('Your local directory is now ready to be used with LPM.', 'green'))

        # Require that the init command be run before other commands are allowed. 
        elif(not os.path.exists('package.json')):
            cprint('Local directory not initialized. Please run lpm init before attempting other operations.', 'yellow')

        elif(args.cmd == 'configure'):
            configureProject(args)

        elif(args.cmd == 'debug'):
            libraries = readLoupeLibraryList()
            print(libraries)

        # Install one or more packages (and their dependencies).
        elif(args.cmd == 'install'):
            # Handle default scenario where sources are not requested (i.e. we're installing binary packages).
            if (not args.source):
                if (len(packages) > 0):
                    print('Installing ' + ', '.join(packages) + '...')
                    try:
                        installPackages(packages, packageVersions)
                    except:
                        cprint('Error while attempting to install package(s).', 'yellow')
                        return
                else:
                    print('Installing all dependencies...')
                    try:
                        installPackages(packages, packageVersions)
                    except:
                        cprint('Error while attempting to install package(s).', 'yellow')
                        return
                # Move packages from the node_modules folder into the project/main directory. 
                syncPackages(getAllDependencies(packages))
            else: # Handle request to install source code instead.
                if (len(packages) > 0):
                    print('Cloning ' + ', '.join(args.packages) + '...')
                    try:
                        # First check to see if there is an AS project locally.
                        project = ASTools.Project('.')
                        librariesPkg = ASTools.Package('./Logical/Libraries')
                        try:
                            # Check for existing Loupe folder.
                            loupePkg = ASTools.Package('./Logical/Libraries/Loupe')
                        except:
                            print('Loupe folder not found, creating it...')
                            # Add the Loupe package back in there.
                            loupePkg = librariesPkg.addEmptyPackage('Loupe') 
                        for package in args.packages:
                            # Extract version info if included (this would show up after the '@' character, i.e. 'mylib@3.0.4')
                            # TODO: this check is now redundant with a version check done at the top of this file, so this should get refactored...
                            if package.find('@') > -1:
                                splitPackage = package.split('@')
                                packageName = splitPackage[0]
                                packageVersion = splitPackage[1]
                                installSource(packageName, packageVersion, loupePkg)                               
                            else:
                                packageName = package
                                installSource(packageName, '', loupePkg)
                            # Next, install any dependencies of this source library.
                            sourceDependencies = getSourceDependencies(os.path.join('.', 'Logical', 'Libraries', 'Loupe', packageName))
                            if (len(sourceDependencies) > 0):
                                # TODO: add support for getting the correct version of these dependencies.
                                installPackages(sourceDependencies, [''] * len(sourceDependencies))
                                # Aaand sync those dependencies.
                                syncPackages(getAllDependencies(sourceDependencies))
                    except:
                        cprint('Error while attempting to install source code.', 'yellow')
                        cprint(sys.exc_info())
            # Deploy relevant objects to cpu.sw.
            # First check project-level settings to see if deployment is configured. 
            deploymentConfigs = getPackageManifestField('package.json', ['lpmConfig', 'deploymentConfigs'])
            if (deploymentConfigs is not None):
                print('Deploying ' + ', '.join(packages) + ' to the following configurations: ' + ', '.join(deploymentConfigs))
                for config in deploymentConfigs:
                    if(not args.source):
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
                if(os.path.exists(packageManifestPath)):
                    packageType = getPackageManifestField(packageManifestPath, ['lpm', 'type'])
                    if(packageType == 'project'):
                        return
            if (deploymentConfigs is None):
                cprint("Note that the installed packages have not been deployed.", "yellow")
                cprint("You will need to do this manually, or you can configure deployment targets with the 'lpm configure' command.", 'yellow')

        # Uninstall one or more packages.
        elif(args.cmd == 'uninstall'):
            if (len(packages) > 0):
                print('Uninstalling ' + ', '.join(packages) + '...')
                try:
                    uninstallPackages(packages)
                except:
                    cprint('Error while attempting to uninstall package(s).', 'yellow')
                    return
                syncPackages(getAllDependencies(packages))
                cprint('Operation completed successfully.', 'green')
            else:
                print(colored('Please provide the name of at least one package.', 'yellow'))

        # Open git client for a specific source library.
        elif(args.cmd == 'git'):
            # Retrieve configured Git client.
            gitClient = getPackageManifestField('package.json', ['lpmConfig', 'gitClient'])
            if(gitClient == ''):
                cprint("No Git client configured (please run lpm configure)", "yellow")
            else:
                print(f'Opening {gitClient} for these packages: ' + ', '.join(args.packages))
                for package in packages:
                    cmd = []
                    if(gitClient == 'GitExtensions'):
                        cmd.append('gitex.cmd')
                        cmd.append('openrepo')
                        cmd.append('\"' + os.path.join(os.getcwd(), 'Logical', 'Libraries', 'Loupe', os.path.split(package)[1]) + '\"')
                        executeAndContinue(cmd)
                    else:
                        cprint(f"We don't support {gitClient}, are you kidding?", "yellow")

        # Publish a binary library.
        elif(args.cmd == 'publish'):
            # Introspect the package.json to verify that the package name has the right scope prefix (i.e. @loupeteam). 
            data = getPackageManifestData('package.json')
            if data['name'].find('@loupeteam') != 0:
                cprint('Error: the package name must include the @loupeteam scope prefix.', 'yellow')
            else:
                try:
                    # Introspect the package.json to verify that the 'repository' field is present. 
                    repoUrl = data['repository']['url'] # This triggers an exception if it doesn't exist
                    if (args.silent):
                        text = 'y'
                    else:
                        text = input(colored('? ', 'green') + 'Are you sure you want to publish ' + colored(data['name'], 'yellow') + ' version ' + colored(data['version'], 'yellow') + '? (y/N) ')
                    if (text.lower() == 'y') | (text.lower() == 'yes'):
                        try: 
                            # Clean up the local directory before publishing.
                            # If there's a Jenkinsfile present, remove it.
                            if(os.path.isfile('./Jenkinsfile')):
                               os.remove('./Jenkinsfile') 
                            # Publish the package.
                            execute(['npm' ,'publish'], True)
                            cprint('Successfully published ' + data['name'] + ' version ' + data['version'] + '.', 'green')
                        except:
                            cprint("Error while publishing. Please check the detailed error message above.", 'yellow')                       
                except:
                    cprint('Error: the package.json file must include a repository parameter', 'yellow')
                    cprint('For example:', 'yellow')
                    print('"repository": {')
                    print('    "type": "git",')
                    print('    "url": "https://github.com/loupeteam/piper"')
                    print('}')  

        # Fetch the list of all dependencies for the root level, or one of its direct package dependencies. 
        elif((args.cmd == 'list') and (len(args.packages) == 0)):
            cmd = []
            cmd.append('npm list')
            cmd.append('-all')
            executeStandard(cmd)

        # In all other cases, just pass the command and list of packages straight through to NPM.
        else:
            runGenericNpmCmd(args.cmd, packages)
            cprint('Operation completed', 'green')

    return

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
    for library in loupePkg.objects:
        packages_to_import.append('@loupeteam/' + library.text)
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
    text.append('@loupeteam:registry=https://npm.pkg.github.com')
    text.append('//npm.pkg.github.com/:_authToken=' + token)
    f.write('\n'.join(text))
    f.close()

# Logout of the Github registry.  
def logout():
    # If there's a local .npmrc file, remove it.
    if(os.path.exists('./.npmrc')):
        os.remove('./.npmrc')
    # And perform the npm logout to globally logout as well.
    command = []
    command.append('npm logout') 
    command.append('--scope=@loupeteam')
    command.append('--registry=https://npm.pkg.github.com')
    executeStandard(command)

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
        print('Support for interactice prompts is disabled. Default values will be assigned to the package.json file.')
        print('All configurations in the project are being assigned as deployment targets: ' + ' '.join(project.buildConfigNames))
        setPackageManifestField('package.json', 'deploymentConfigs', project.buildConfigNames)
    else:
        from termcolor import colored, cprint
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

# Install source library by cloning into Logical / Libraries / Loupe folder. 
def installSource(package, version, loupePkg):
    # Package names are forced to lower case by convention
    package = package.lower()
    # The assumption here is that the repo has all of its assets at the root level.
    # Check to make sure this library isn't already in there.
    if (os.path.isdir(os.path.join('.', 'Logical', 'Libraries', 'Loupe', package))):
        raise Exception("Library folder already exists")
        return
    try:
        # Record the current directory.
        cwd = os.getcwd()
        # Grab the required credentials for inline cloning.
        username = getAuthenticatedUser()
        password = getLocalToken()
        # Clone the repo into the target directory.
        libraryPath = os.path.join('.', 'Logical', 'Libraries', 'Loupe', package)
        command1 = []
        command1.append('git clone')
        command1.append(f'https://{username}:{password}@github.com/loupeteam/{package}')
        command1.append(libraryPath)
        execute(command1, False)
        # And then checkout the correct commit if it's been specified.
        if (version != ''):
            os.chdir(os.path.join('.', libraryPath))
            command1b = []
            command1b.append('git checkout')
            command1b.append(version)
            execute(command1b, False)
            os.chdir(cwd)
        # Now add the new directory to the parent's .pkg.
        loupePkg._addPkgObject(libraryPath)

    except:
        raise Exception("Error cloning the repo")

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
            # Strip it of its @loupeteam prefix.
            splitPackage = os.path.split(package)[1]
            dependencyData = getSourceDependencies(os.path.join('.', 'Logical', 'Libraries', 'Loupe', splitPackage))
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

def getSourceDependencies(libraryPath):
    sourceLibrary = ASTools.Library(libraryPath)
    dependencyNames = []
    # Install binary dependencies for this library
    for dependency in sourceLibrary.dependencies:
        # First check to see if it's a custom Loupe lib (if not, ignore it)
        command = []
        command.append('npm view')
        command.append(f'@loupeteam/{dependency.name}')
        result = executeAndReturnCode(command)
        if result == 0:
            print('Dependency found: ' + f'@loupeteam/{dependency.name.lower()}')
            # Add this dependency to our list.
            dependencyNames.append(f'@loupeteam/{dependency.name}'.lower())
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
            packageDestination = getPackageManifestField(packageManifest, ['lpm', 'logical', 'destination'])
            # If an explicit destination exists, use that. Otherwise default to Logical root.
            if packageDestination != None:
                destination = os.path.join('Logical', packageDestination)
                # Now create the packages in this path that doesn't exist.
                createPackageTree(destination)
            else:
                destination = 'Logical'
            # Find the module(s) in node_modules, and sync it/them.
            for module in os.listdir(os.path.join('node_modules', '@loupeteam')):
                if (os.path.join('@loupeteam', module) == os.path.normpath(package)):
                    # Get a handle on the folder destination.
                    destinationPkg = ASTools.Package(destination)
                    # Create a list of filtered objects that don't get copied over.
                    filter = ['package.pkg', 'license', 'readme.md', 'package.json', 'changelog.md']
                    # Loop through all contents in the source directory and copy them over one by one. 
                    for item in os.listdir(os.path.join('node_modules', '@loupeteam', module)):
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
            # Find the module(s) in node_modules, and sync it/them.
            for module in os.listdir(os.path.join('node_modules', '@loupeteam')):
                if (os.path.join('@loupeteam', module) == os.path.normpath(package)):
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
                taskLocation = getPackageManifestField(packageManifest, ['lpm', 'logical', 'destination'])
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
            # Introspect the package.json for this package. Find its 'lpm' section.
            packageManifest = os.path.join('Logical', 'Libraries', 'Loupe', os.path.split(package)[1], 'package.json')
            libraryAttributes = getLibraryAttributes(packageManifest, config)
            libraryLocation = os.path.join('Libraries', 'Loupe')
            # Deploy the required library.
            deploymentTable.deployLibrary(os.path.join('Logical', libraryLocation), os.path.split(package)[1], libraryAttributes)

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
    # Create dependencies dictionary for this library
    dependency_dict = {}
    for dependency in library.dependencies:
        # First check to see if it's a custom Loupe lib (if not, ignore it)
        cmd = []
        cmd.append('npm view')
        cmd.append(f'@loupeteam/{dependency.name}')
        result = executeAndReturnCode(cmd)
        if result == 0:
            version = []
            if dependency.minVersion != '':
                version.append(f'>={library._formatVersionString(dependency.minVersion)}')
            if dependency.maxVersion != '':
                version.append(f'<={library._formatVersionString(dependency.maxVersion)}')
            if len(version) == 0:
                version.append('*')
            dependency_dict.update({f'@loupeteam/{dependency.name.lower()}':' '.join(version)})
    # Make sure there's a top level description available. 
    if (library.description == ''):
        description = f"Loupe's {package.lower()} library for Automation Runtime"
    else:
        description = library.description
    # Set the homepage to point to the styleguide
    homepage = f'https://loupeteam.github.io/LoupeDocs/libraries/{package.lower()}.html'
    # Ensure the lpmConfig has the proper type set.
    try:
        if lpmConfig['type'] != 'library':
            lpmConfig = { 'type': 'library' }
    except Exception:
        lpmConfig = { 'type': 'library' }
    # Create dictionary that will hold all values for the package.json file
    manifest_dict = {
                'name': f'@loupeteam/{package.lower()}', 
                'version': library._formatVersionString(library.version), 
                'description': description, 
                'homepage': homepage,
                'scripts': {},
                'keywords': [],
                'author': 'Loupe',
                'license': 'MIT',
                'repository': {
                    'type': 'git',
                    'url': 'https://github.com/loupeteam/' + package
                },
                'lpm': lpmConfig,
                'dependencies': dependency_dict
                }
    # Convert to JSON and create the file
    manifest_json = json.dumps(manifest_dict, indent=2)
    f = open('.\package.json', 'w')
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
    (error, data) = getLoupePackageListData()

    if not error:
        packages_sorted = sorted(data, key=lambda x: x["name"])
        for package in packages_sorted:
            if package['repository']['description'] is None:
                package['repository']['description'] = " "
        name_col_width = max(len(package["name"]) for package in packages_sorted) + 2 
        version_col_width = 12
        lastmod_col_width = 14
        description_col_width = max(len(package['repository']['description']) for package in packages_sorted)
        print(  "NAME".ljust(name_col_width) + 
                "VERSIONS".ljust(version_col_width) + 
                "LASTUPDATED".ljust(lastmod_col_width) + 
                "DESCRIPTION".ljust(description_col_width))
        print(  "----".ljust(name_col_width) + 
                "--------".ljust(version_col_width) + 
                "-----------".ljust(lastmod_col_width) + 
                "-----------".ljust(description_col_width))
        for package in packages_sorted:
            print(  package["name"].ljust(name_col_width) + 
                    str(package["version_count"]).ljust(version_col_width) + 
                    package["updated_at"][:10].ljust(lastmod_col_width) + 
                    package['repository']['description'].ljust(description_col_width))
    else:
        print(f"Unable to print package list: {error}")

# Fetches data using GitHub API (See https://docs.github.com/en/rest/packages?apiVersion=2022-11-28#list-packages-for-an-organization)
# Returns (error, data) tuple, where error is None if all OK and data is a list of package dictionaries (see GitHub's schema)
def getLoupePackageListData():
    token = getLocalToken()
    headers = { 'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28' }
    organization = 'loupeteam'
    page = 1
    per_page = 100
    all_packages_gathered = False
    all_packages = []

    while not all_packages_gathered:
        params = {  'package_type': 'npm',
                    'page': str(page),
                    'per_page': str(per_page) }
        r = requests.get(f'https://api.github.com/orgs/{organization}/packages', headers=headers, params=params, timeout=5)
        if r.status_code != 200:
            error = "Status code not OK. Code: " + r.status_code + "\n" + r.text 
            return (error, [])  # Early return
        retrieved_packages = json.loads(r.content)
        all_packages += retrieved_packages
        all_packages_gathered = len(retrieved_packages) < per_page    # All gathered once there are fewer results than full amount
        page += 1

    print(f"Retrieved {len(all_packages)} packages total. See below for detailed information.")
    return (None, all_packages)

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

if __name__ == "__main__":
    
    # Configure colored logger
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    main()