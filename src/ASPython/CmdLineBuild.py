'''
 * File: CmdLineBuild.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
"""
@title CmdLineExportBuild
@description This python script takes in command line arguments 
and build given configurations for an AS project

0.1.0 - Synchronize all script versions
0.0.3 - Improve failed build error message
0.0.2 - Slight changes to debug messages
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
    parser.add_argument('project', type=str, help='Path to AS project you want to build')
    parser.add_argument('-c','--configuration', nargs='+', type=str, help='AS configuration(s) you want to build')
    parser.add_argument('-bm','--buildMode', type=str, help='Type of build in AS', default='Build', choices=['Rebuild', 'Build','BuildAndTransfer', 'BuildAndCreateCompactFlash', 'None']) 
    parser.add_argument('-sim','--simulation', action='store_true', help='Should be built for simulation')
    parser.add_argument('-pip', action='store_true', help='Generate a PIP after the build completes')
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
    logging.debug('The project to be built is: %s', args.project)
    logging.debug('The project configuration(s) to be build is: %s', args.configuration)
    logging.debug('The project build mode is: %s', args.buildMode)
    logging.debug('The project will be built for simulation: %s', args.simulation)
    logging.debug('The log level will be: %s', args.logLevel)
    if args.pip:
        logging.debug('Pip will be created')


    # Build the project 
    project = ASTools.Project(os.path.abspath(args.project))

    for config in args.configuration:

        # if not args.simulation:
        #     # If there is a simulation parameter defined in the XML, set it to 0 (i.e. disable sim before the build)
        #     if project.getHardwareParameter(config, 'Simulation') != '':
        #         project.setHardwareParameter(config, 'Simulation', '0')

        buildStatus = project.build(config, buildMode=args.buildMode, simulation=args.simulation)

        if buildStatus.returncode > ASTools.ASReturnCodes['Warnings']:
            sys.exit('Build failed for config {config}')
        elif args.pip:
            # Determine target destination for the PIP (will be in the format <ASProjectPath>/Temp/PIP/<config>/)
            destination = f"{project.tempPath}/PIP/{config}"
            
            # Create Pip folder if it doesn't exist
            if not os.path.isdir(f"{project.tempPath}/PIP"):
                os.mkdir(f"{project.tempPath}/PIP")
            
            # Delete the entirety of the PIP Config folder so that old PIPs don't get used later. 
            if os.path.isdir(destination):
                shutil.rmtree(destination)
            
            # Recreate the PIP Config folder.
            os.mkdir(destination)
            
            # Create the PIP (will just be loose files at this point).
            project.createPIP(config, destination)
            
            # Zip up the PIP files into a .tar archive.
            os.chdir(destination)
            tf = tarfile.open('Installer.tar.gz', mode='w:gz', format=tarfile.USTAR_FORMAT)
            for item in os.listdir():
                tf.add(item)
            tf.close()
        else:
            logging.debug('Building of %s Complete!', config)

    
    sys.exit(0)

if __name__ == "__main__":
    
    # Configure colored logger
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    main()
