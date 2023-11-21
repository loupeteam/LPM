"""
@title CmdLineExportLib
@description This python script takes in command line arguments 
and export libraries from an AS project to a specified destination

0.0.4 - Improve error handling of failed builds
0.0.3 - Slight changes to debug messages
0.0.2 - ???
0.0.1 - Initial release
"""

# Python Modules
import argparse
import ctypes
import logging
import os.path
import shutil
import sys
import subprocess
from typing import Dict, Tuple, Sequence, Union, List, Optional

# External Modules
import ASTools
import _version

def main():

    buildStatus = None
    libBuildConfig:List[ASTools.Project.buildConfigs] = []

    # Parse arguments from the command line 
    parser = argparse.ArgumentParser(description='Export libraries from an AS project with command line arguments.')
    parser.add_argument('project', type=str, help='Path to AS project')
    parser.add_argument('-dest','--destination', type=str, help='Destination path for exported libraries')
    parser.add_argument('-c','--configuration', nargs='+', type=str, help='AS configuration')
    parser.add_argument('-wl', '--whitelist', type=str, nargs='+', help='Desired libraries (trumps the blacklist)', default='')
    parser.add_argument('-bl', '--blacklist', type=str, nargs='+', help='Ignored libraries (use glob style pattern: *myLibName*)', default='')
    parser.add_argument('-o', '--overwrite', action='store_true', help='Option to have previously exported libraries overwritten')         
    parser.add_argument('-source','--sourceFile', action='store_true', help='Option to have libraries exported as source') 
    parser.add_argument('-bm','--buildMode', type=str, help='Type of build in AS', default='None', choices=['Rebuild', 'Build','BuildAndTransfer', 'BuildAndCreateCompactFlash', 'None']) 
    parser.add_argument('-l', '--logLevel', type=str.upper, help='Log level input is case insensitive', choices=['DEBUG','INFO','WARNING', 'ERROR'], default='')
    parser.add_argument('-iv', '--includeVersion', action='store_true', help='Option to have version number included in the folder structure')     
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=_version.__version__))
    args = parser.parse_args()

    # Allow setting log level via command line
    if(args.logLevel):
        lognum = getattr(logging, args.logLevel)
        if not isinstance(lognum, int):
            raise ValueError('Invalid log level: %s' % args.logLevel)
        logging.getLogger().setLevel(level=lognum)

    # Log arguments for debug  
    logging.debug('The project to be built is: %s', args.project)
    logging.debug('The project configuration(s) to be build is: %s', args.configuration)
    logging.debug('Overwrite? %s', args.overwrite)
    logging.debug('Source? %s', args.sourceFile)
    logging.debug('Version Included? %s', args.includeVersion)     
    logging.debug('Built before exporting?  %s', args.buildMode)      
    logging.debug('Libraries whitelist: %s', args.whitelist)
    logging.debug('Libraries blacklist: %s', args.blacklist)
    
    if args.destination == None: 
        args.destination = os.path.join(os.path.dirname(args.project), '..', 'Exports')
    
    logging.debug('Export destination: %s', args.destination)
    
    project = ASTools.Project(args.project)

    # TODO: This section of config names to BuildConfig list can probably be improved (next ~85 lines)
    #       Using something like for each config name project.getConfigByName
    for buildConfig in project.buildConfigs:
        if args.configuration != None:
            if buildConfig.name in args.configuration:
                libBuildConfig.append(buildConfig)

    if not len(libBuildConfig):
        logging.error('\033[31mNot a configration in specified project: %s\033[0m', str(args.configuration))
        sys.exit('Configuration passed in is not part of AS project')

    libBuildConfigNames:List[str] = [config.name for config in libBuildConfig]

    for name in args.configuration:
        if name not in libBuildConfigNames:
            logging.error('Configuration name does not exist in project: %s', name)
    
    if args.buildMode != 'None':
        for config in args.configuration:
            buildStatus = project.build(config, buildMode=args.buildMode, simulation=False)
            
            if buildStatus.returncode > ASTools.ASReturnCodes['Warnings']:
                sys.exit('Build failed for config {config}')
            else:
                logging.debug('Building of %s Complete!', config)

    if args.buildMode == 'None' or buildStatus.returncode <= ASTools.ASReturnCodes['Errors']:
        results = project.exportLibraries(args.destination, overwrite=args.overwrite, buildConfigs=libBuildConfig, blacklist=args.blacklist, whitelist=args.whitelist, binary= not args.sourceFile, includeVersion= args.includeVersion )
        
        # TODO: This handling needs to be improved but first requires improvements in the return info of exportLibraries
        for result in results.failed:
            logging.error('\033[31mFailed to export %s to %s because %s\033[0m', result.name, result.path, result.exception)
            # Remove libraries that failed exports 
            try:
                shutil.rmtree(result.path, onerror=ASTools.Library._rmtreeOnError)
            except FileNotFoundError as identifier:
                logging.debug('Failed to delete fail export lib, does not exist: %s', result.path)
            except:
                logging.exception('\033[31mFailed to delete: %s, because  %s\033[0m', result.path, sys.exc_info()[0])

    logging.info('Export Complete!')
    sys.exit(0)


if __name__ == "__main__":
    
    # Configure colored logger
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    main()
