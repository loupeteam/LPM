'''
 * File: CmdLineCreateInstaller.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
"""
@title CmdLineCreateInstaller
@description This python script takes in command line arguments 
and generates an ISS-based installer

0.1.0 - Synchronize all script versions
0.0.1 - Initial release
"""

# Python Modules
import argparse
import logging
import sys
import subprocess
import uuid
from typing import Dict, Tuple, Sequence, Union, List, Optional

import _version

# TODO: Error handling when required pars aren't passed in. 

def main():

    # Parse arguments from the command line 
    parser = argparse.ArgumentParser(description='Generate an Inno installer')
    # High-level application information. 
    parser.add_argument('script', type=str, help='Name of the iss script to compile')
    parser.add_argument('-o', '--output', type=str, help='Destination folder where the installer is placed')
    parser.add_argument('-an', '--appName', type=str, help='Name of the app to create')
    parser.add_argument('-av', '--appVersion', type=str, help='Version of the app to create', default='1.0.0')
    parser.add_argument('-ap', '--appPublisher', type=str, help='Name of the app publisher', default='Loupe')
    parser.add_argument('-au', '--appUrl', type=str, help='URL of the app publisher', default='https://loupe.team')
    # Simulation assets.
    parser.add_argument('-sd', '--simDir', type=str, help='Directory where Simulation assets are located')
    # User Partition assets.
    parser.add_argument('-ud', '--userDir', type=str, help='Directory where User Partition assets are located')
    parser.add_argument('-jb', '--junctionBatch', type=str, help='Name of the Junction Batch file', default='ConnectFileDevice.bat')
    # HMI assets. 
    parser.add_argument('-hd', '--hmiDir', type=str, help='Directory where HMI assets are located')
    parser.add_argument('-he', '--hmiExe', type=str, help='Name of the HMI EXE file')
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

    # Generate the unique GUID that Inno expects for each app build. 
    GUID = generateGUID()

    # Compile the app, which produces the installer. 
    compileInstaller(args, GUID)

    sys.exit(0)

def generateGUID():
    GUID = uuid.uuid4()
    return '{{' + str(GUID) + '}'

def compileInstaller(args, GUID):

    command = []

    # Add the call to the iscc executable (this compiles the .iss script).
    command.append("C:\Program Files (x86)\Inno Setup 6\iscc")

    # Add the name of the script to compile. 
    command.append(args.script)

    # Pass in general app parameters.
    command.append(f"/O{args.output}")
    command.append(f"/dAppName={args.appName}")
    command.append(f"/dAppVersion={args.appVersion}")
    command.append(f"/dAppPublisher={args.appPublisher}")
    command.append(f"/dAppUrl={args.appUrl}")
    command.append(f"/dAppGUID={GUID}")

    # Pass in parameters related to simulation if it's required.
    if args.simDir:
        command.append("/dIncludeSimulator=yes")
        command.append(f"/dSimulationDirectory={args.simDir}")
    else:
        command.append("/dIncludeSimulator=no")

    # Pass in parameters related to User Partition if it's required. 
    if args.userDir:
        command.append("/dIncludeUserPartition=yes")
        command.append(f"/dUserPartitionDirectory={args.userDir}")
        command.append(f"/dJunctionBatchFilename={args.junctionBatch}")
    else:
        command.append("/dIncludeUserPartition=no")

    # Pass in parameters related to HMI.
    if args.hmiDir: 
        command.append("/dIncludeHmi=yes")
        command.append(f"/dHmiDirectory={args.hmiDir}")
        command.append(f"/dHmiExeName={args.hmiExe}")
    else:
        command.append("/dIncludeHmi=no")

    # Force quiet compilation if debug isn't set. 
    if args.logLevel != 'DEBUG':
        command.append("/Qp")

    # Execute the process, and retrieve the process object for further processing.
    logging.debug(command)
    process = subprocess.run(command, encoding="utf-8", errors='replace', shell=True)

    return

if __name__ == "__main__":

    main()
