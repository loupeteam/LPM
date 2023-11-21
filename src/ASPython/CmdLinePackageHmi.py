'''
 * File: CmdLinePackageHmi.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
"""
@title CmdLinePackageHmi
@description This python script takes in command line arguments 
and packages a webHMI-based HMI

0.1.0 - Synchronize all script versions
0.0.1 - Initial release
"""

# Python Modules
import argparse
import logging
import sys
import subprocess
import uuid
import os
import json
import re
from typing import Dict, Tuple, Sequence, Union, List, Optional

import _version

# TODO: add capabilities for zipping up HMI. 
# TODO: error check the parameters. 

def main():

    # Parse arguments from the command line 
    parser = argparse.ArgumentParser(description='Package up a webHMI-based HMI')
    # High-level application information. 
    parser.add_argument('-s', '--source', type=str, help='Source folder where the HMI files are located (i.e. where main package.json is located)', default='C:/Projects/Publisher/Project/HMIApp/Electron')
    parser.add_argument('-o', '--output', type=str, help='Destination folder where packaged files are placed')
    parser.add_argument('-an', '--appName', type=str, help='Name of the app to package')
    parser.add_argument('-av', '--appVersion', type=str, help='Version of the app to create', default='1.0.0')
    parser.add_argument('-ap', '--appPublisher', type=str, help='Name of the app publisher', default='Loupe')
    parser.add_argument('--installElectronPackager', dest='installElectronPackager', action='store_true', help='Install electron-packager before attempting to package HMI')
     # General script utilities.
    parser.add_argument('-l', '--logLevel', type=str.upper, help='Log level', choices=['DEBUG','INFO','WARNING', 'ERROR'], default='')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=_version.__version__))
    args = parser.parse_args()

    # Allow setting log level via command line
    if(args.logLevel):
        lognum = getattr(logging, args.logLevel)
        if not isinstance(lognum, int):
            raise ValueError('Invalid log level: %s' % args.logLevel)
        logging.getLogger().setLevel(level=lognum)

    # Install all npm dependencies from source folder and source/public folder.      
    installDependencies(args.source)
    try:
        installDependencies(args.source + '/public')
    except: 
        logging.info('No public sub-folder found, skipping its dependency installation')

    # Install electron-packager if specified. 
    if (args.installElectronPackager):
        installElectronPackager()

    # Update the version in the package.json.
    appSemanticVersion = updateAppVersion(args.source, args.appVersion)

    # Call electron-packager to package up the HMI.
    packageHMI(args.source, args.appName, args.output, args.appPublisher, appSemanticVersion)

    # Zip up the packaged artifacts. 
    #zipHMI(args)

    sys.exit(0)

def installDependencies(source):
    # cd into the right folder. 
    os.chdir(source)
    # Check to see if this folder has a package.json in it.
    if not 'package.json' in os.listdir('.'):
        logging.info('The source directory does not contain a package.json, skipping install')
    else:
        # Install all local npm dependencies.
        subprocess.run('npm install', encoding='utf-8', errors='replace', shell=True)
    return

def installElectronPackager():
    # Install the electron-packager module globally. 
    subprocess.run('npm install electron-packager -g', encoding='utf-8', errors='replace', shell=True)
    return

def updateAppVersion(source, version):
    with open(source + '/package.json', 'r+') as f:
        data = json.load(f)
        data['version'] = version
        f.seek(0)        # <--- should reset file position to the beginning.
        json.dump(data, f, indent=4)
        f.truncate()     # remove remaining part
    return version

def packageHMI(source, appName, output, appPublisher, appVersion):
    command = []
    command.append('electron-packager')
    command.append(source)
    command.append(appName)
    command.append('--platform=win32')
    command.append('--arch=x64')
    command.append(f'--out={output}')
    command.append('--overwrite')
    command.append(f'--win32metadata.CompanyName="{appPublisher}"')
    command.append(f'--win32metadata.FileDescription="Build #{appVersion}"')
    logging.info(command)
    subprocess.run(command, encoding='utf-8', shell=True)

if __name__ == "__main__":

    main()
