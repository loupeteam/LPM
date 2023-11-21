'''
 * File: CmdLineGetVersion.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
"""
@title CmdLineGetVersion
@description This python script takes in command line arguments 
and retrieves the current build version of an AS project

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
    parser = argparse.ArgumentParser(description='Retrieve the versionId for an AS project.')
    parser.add_argument('project', type=str, help='Path to AS project')
    parser.add_argument('-bi','--buildInfo', type=str, help='Location of the buildInfo .var file')
    parser.add_argument('--semver', dest='semVer', action='store_true', help='Request the version back in Semantic Version format')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=_version.__version__))
    args = parser.parse_args()
    
    project = ASTools.Project(args.project)

    versionId = project.getConstantValue(args.buildInfo, 'versionId')

    if (args.semVer):
        # The version needs to be in the format w.x.y.z. So we try to extract that from the versionId string. 
        # Expecting the output of 'git describe --tags --all', which looks like this: v0.1.2-685-gad6e288
        try:
            match = re.search('(\d+\.\d+\.\d+).*-(\d+)-.*', versionId)
            versionId = match.group(1)
            if (match.group(2) != ''):
                versionId = versionId + '.' + match.group(2)
            else:
                versionId = versionId + '.0'
        except:
            versionId = '0.0.0.0'

    sys.stdout.write(versionId)

    sys.exit(0)


if __name__ == "__main__":

    main()
