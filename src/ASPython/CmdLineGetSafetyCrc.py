'''
 * File: CmdLineGetSafetyCrc.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
"""
@title CmdLineGetVersion
@description This python script takes in command line arguments 
and retrieves the CRC of the specified safe application

0.1.0 - Synchronize all script versions
0.0.1 - Initial release
"""

# Python Modules
import argparse
import os.path
import shutil
import sys
import re
from typing import Dict, Tuple, Sequence, Union, List, Optional

# External Modules
import ASTools
import _version

def main():

    # Parse arguments from the command line 
    parser = argparse.ArgumentParser(description='Retrieve the CRC for an SafeApplication.')
    parser.add_argument('project', type=str, help='Path to AS project')
    parser.add_argument('-c','--configuration', nargs='+', type=str, help='AS configuration(s)')
    parser.add_argument('-sa','--safeApp', type=str, help='Location of the safe application binaries')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=_version.__version__))
    args = parser.parse_args()
    
    project = ASTools.Project(args.project)

    # Find the name of the PLC folder (the one that's right under the configuration name folder).
    configurationDirectory = os.path.join(project.dirPath, 'Physical', args.configuration[0])
    plcDirectory = [name for name in os.listdir(configurationDirectory) if os.path.isdir(os.path.join(configurationDirectory, name))]

    # Truncate extension off of SfApp. 
    splitSafetyApp = args.safeApp.split('.')

    # Create the full relative path to the obscure file. 
    relativePath = os.path.join('Physical', args.configuration[0], plcDirectory[0], 'MappSafety', splitSafetyApp[0], 'C', 'PLC', 'R', 'CPU', 'CPU.ini')

    # And retrieve the CRC value. 
    safetyCrc = project.getIniValue(relativePath, 'CRC', 'PROJECT')

    sys.stdout.write(safetyCrc)

    sys.exit(0)


if __name__ == "__main__":

    main()
