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

# Python modules
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

# External Modules
from ASPython import ASTools

# Core LPM functionality. The CLI in this file delegates to functions defined
# in lpm_core. Importing * preserves the existing call sites in main() that
# reference these names directly.
from lpm_core import *

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
                    print('Attempting to install source for ' + ', '.join(args.packages) + '...')

                sourceDependencies = []
                for (package, packageVersion) in zip(packages, packageVersions):
                    installSource(package, packageVersion, sourceDependencies)
                
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
            elif gitClient != 'GitExtensions':
                cprint(f"We don't support {gitClient}, are you kidding?", "yellow")
            else:
                # GitExtensions is configured git client                
                sourceInfoFilePath = os.path.join(".", "TempObjects", "sourceInfo.json")
                sourceInfo = getJsonData(sourceInfoFilePath)
                print(f'Opening {gitClient} for these packages: ' + ', '.join(args.packages))
                for package in packages:
                    repoPath = sourceInfo.get(package, {}).get("repoPath", None)
                    if repoPath is not None:
                        cmd = []
                        cmd.append('gitex.cmd')
                        cmd.append('openrepo')
                        cmd.append('\"' + os.path.join(os.getcwd(), repoPath) + '\"')
                        executeAndContinue(cmd)
                    else:
                        cprint(f"Could not find repo location for {package}. Verify that it is installed as source.", "yellow")

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


if __name__ == "__main__":
    
    # Configure colored logger
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    main()
