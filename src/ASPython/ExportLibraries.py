'''
 * File: ExportLibraries.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
"""
@title ExportLibraries
@description This file parses parameters from a file and uses them to 
export libraries from an AS project
"""

import ASTools
import logging
import os.path
import shutil
import json
import sys
import copy
import ctypes

from _version import __version__

# TODO: Better support command line arguments
# TODO: Add option to support user input

if __name__ == "__main__":
    default = {
        "projectPath": "", 
        "buildMode": "Rebuild", 
        "Configs": [], 
        "exportPath": "",
        "versionSubFolders": False,
        "ignoreLibraries": []
    }
    paramFileName = 'ExportLibrariesParam.json'
    # Set up logging and color-coding
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    # Write default params if none exist
    if not os.path.exists(paramFileName):
        logging.info('Parameter file: %s, not found. Creating file.', paramFileName)
        with open(paramFileName, 'x') as f:
            f.write(json.dumps(default, indent=2))
        input("Please modify %s with desired params. Press Enter to continue..." % paramFileName)

    try:
        data = copy.deepcopy(default) # Use deep copy instead of copy so that we don't modify default's non primitive values

        # Read parameters
        with open(paramFileName) as param:
            data.update(json.load(param))

        # Parse project
        project = ASTools.Project(data.get('projectPath'))

        if not data.get('Configs'):
            data['Configs'] = project.buildConfigNames
        
        # Update parameters with missing keys
        with open(paramFileName, 'w') as param:
            param.write(json.dumps(data, indent=2))

        # Build project
        if data.get('buildMode') != 'None':
            process = project.build(*data.get('Configs'), buildMode=data.get('buildMode'))
            logging.info('Project batch build complete, code %d', process.returncode)
            if process.returncode > ASTools.ASReturnCodes["Warnings"]:
                sys.exit(process.returncode)
        
        # Export 
        results = project.exportLibraries(data.get('exportPath'), overwrite=True, ignores=data.get('ignoreLibraries'), includeVersion=data.get('versionSubFolders'))
        for result in results.failed:
            logging.error('\033[31mFailed to export %s to %s because %s\033[0m', result.name, result.path, result.exception)
            # Remove libraries that failed exports 
            try:
                shutil.rmtree(result.path, onerror=ASTools.Library._rmtreeOnError)
            except FileNotFoundError as identifier:
                logging.debug('Failed to delete fail export lib, does not exist: %s', result.path)
            except:
                logging.exception('Failed to delete: %s, because  %s', result.path, sys.exc_info()[0])

        logging.info('Export Complete!')

    except:
        logging.exception('Error occurred: %s', sys.exc_info()[0])

    pass
    
    sys.exit(0)
    