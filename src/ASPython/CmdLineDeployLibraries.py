'''
 * File: CmdLineDeployLibraries.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
"""
@title CmdLineDeployLibraries
@description This python script deploys Loupe libraries
to a specified cpu.sw file. 

0.1.0 - Synchronize all script versions
0.0.1 - Initial release
"""

# Python Modules
import argparse
import logging
import sys
import ctypes
import os
import tarfile
import shutil

# External Modules
import ASTools
import _version

def main():
    # Parse arguments from the command line 
    parser = argparse.ArgumentParser(description='Build an AS project with command line arguments.')
    parser.add_argument('-d', '--deploymentFile', type=str, help='Path to the cpu.sw file')
    parser.add_argument('-lf', '--libraryFolder', type=str, help='Path to the folder that holds the libraries')
    parser.add_argument('-lib', '--libraries', nargs='+', type=str, help='Libraries to deploy')
    parser.add_argument('-l', '--logLevel', type=str.upper, help='Log level', choices=['DEBUG','INFO','WARNING', 'ERROR'], default='')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=_version.__version__))   
    args = parser.parse_args()


    # Allow setting log level via command line
    if(args.logLevel):
        lognum = getattr(logging, args.logLevel)
        if not isinstance(lognum, int):
            raise ValueError('Invalid log level: %s' % args.logLevel)
        logging.getLogger().setLevel(level=lognum)

    # Save parsed information in to variables. 
    logging.debug('The file to be updated is: %s', args.deploymentFile)
    logging.debug('The libraries to be deployed are: %s', args.libraries)
    logging.debug('The log level will be: %s', args.logLevel)

    # Retrieve the deployment table.
    deploymentTable = ASTools.SwDeploymentTable(args.deploymentFile)
    # Deploy the required libraries. If no libraries are specified, this means deploy everything in the library folder.
    if (not args.libraries):
        for library in os.listdir(args.libraryFolder):
            # Wait! Don't deploy the Package.pkg as a library, that would make no sense!
            if (library != 'Package.pkg'):
                deploymentTable.deployLibrary(args.libraryFolder, library)
    else:
        for library in args.libraries:
            deploymentTable.deployLibrary(args.libraryFolder, library)
    
    sys.exit(0)

if __name__ == "__main__":
    
    # Configure colored logger
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    main()
