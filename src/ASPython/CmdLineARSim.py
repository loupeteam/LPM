'''
 * File: CmdLineARSim.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
"""
@title CmdLineARSim
@description This python script takes in command line arguments 
and creates an ARSIm package for a given AS project

0.1.0 - Synchronize all script versions
0.0.4 - Improve failed build error message
0.0.3 - Add support for multiple configurations
0.0.2 - Fix ARSim structure not created if buildMode is None
0.0.1 - Initial release
"""

# Python Modules
import argparse
import ctypes
import logging
import sys
import os
import shutil
import tarfile

# External Modules
import ASTools  
import _version

def main():

    buildStatus = None

    # Parse arguments from the command line 
    parser = argparse.ArgumentParser(description='Build and start ARSim an AS project via command line.')
    parser.add_argument('project', type=str, help='AS project you want to build')
    parser.add_argument('-c','--configuration', nargs='+', type=str,  help='AS configuration you want to build')
    parser.add_argument('-bm', '--buildMode', type=str, help='AS build mode you want executed', default='None', choices=['Rebuild', 'Build','BuildAndTransfer', 'BuildAndCreateCompactFlash', 'None'])
    parser.add_argument('-ss', '--startSim', action='store_true', help='Option to have ARSim start after ARSim creation')
    parser.add_argument('-uf', '--userFiles', type=str, help='Path to the folder containing user files to get included with simulator')
    parser.add_argument('-hf', '--hmiFiles', type=str, help='Path to the folder containing HMI files to get included with simulator')
    parser.add_argument('-l', '--logLevel', type=str.upper, help='Log level', choices=['DEBUG','INFO','WARNING', 'ERROR'], default='')
    parser.add_argument('-v','--version', action='version', version='%(prog)s {version}'.format(version=_version.__version__))
    args = parser.parse_args()

    # Allow setting log level via command line
    if(args.logLevel):
        lognum = getattr(logging, args.logLevel)
        if not isinstance(lognum, int):
            raise ValueError('Invalid log level: %s' % args.logLevel)
        logging.getLogger().setLevel(level=lognum)

    # Save parsed information in to variables. eARSim.
    logging.debug('%s', args)
    logging.debug('The project to be built is: %s', args.project)
    logging.debug('The configuration(s) to be built is: %s', args.configuration)
    logging.debug('Build mode:  %s', args.buildMode) 
    logging.debug('Start simulation when creation is complete:  %s', args.startSim)

    project = ASTools.Project(args.project)

    if args.buildMode != 'None':
        for config in args.configuration:
            buildStatus = project.build(config, buildMode=args.buildMode, simulation=True)

            if buildStatus.returncode > ASTools.ASReturnCodes['Warnings']:
                sys.exit('Build failed for config {config}')
            else:
                logging.debug('Building of %s Complete!', config)

    for config in args.configuration:
        # Determine target destination for the PIP (will be in the format <ASProjectPath>/Temp/PIP/<config>/)
        destination = os.path.join(project.tempPath, 'SIM', config)
        
        # Create SIM folder if it doesn't exist
        if not os.path.isdir(os.path.join(project.tempPath, 'SIM')):
            os.mkdir(os.path.join(project.tempPath, 'SIM'))
        
        # Delete the entirety of the SIM Config folder so that old PIPs don't get used later. 
        if os.path.isdir(destination):
            shutil.rmtree(destination)
        
        # Recreate the SIM Config folder.
        os.mkdir(destination)
        
        # Create the SIM (will just be loose files at this point).
        project.createSim(config, destination=destination, startSim=args.startSim)

        # Add custom directory with user partition data if configured. 
        if args.userFiles != '':
            userPath = os.path.join(destination, 'ARSimUser')
            shutil.copytree(args.userFiles, userPath)

        # Add custom directory with HMI data if configured. 
        if args.userFiles != '':
            hmiPath = os.path.join(destination, 'HMI')
            shutil.copytree(args.hmiFiles, hmiPath, ignore=shutil.ignore_patterns('node_modules'))
     
        # Zip up the PIP files into a .tar archive.
        os.chdir(destination)
        tf = tarfile.open('Simulator.tar.gz', mode='w:gz', format=tarfile.PAX_FORMAT)
        for item in os.listdir():
            tf.add(item)
        tf.close()
    
    sys.exit(0)
        
if __name__ == "__main__":
    
    # Configure colored logger
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    main()
