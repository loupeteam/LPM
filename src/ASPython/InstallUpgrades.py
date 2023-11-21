'''
 * File: InstallUpgrades.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
"""
@title InstallUpgrades
@description This python script takes in command line arguments 
and installs all AS upgrades in the specified directory
"""

#Python Modules
import argparse
import logging
import sys
import ctypes
import os
import subprocess
# import psutil # This is a third party library

from _version import __version__

# Sample call for this script:
# python InstallUpgrades.py "C:/Temp/downloading" -brp "C:\BrAutomation" -asp "C:\BrAutomation\AS49" -l INFO

# def getService(name):

#     service = None
#     try:
#         service = psutil.win_service_get(name)
#         service = service.as_dict()
#     except Exception as ex:
#         print(str(ex))
#     return service

def installBRUpgrade(upgrade:str, brPath:str, asPath:str):
    commandLine = []
    commandLine.append(upgrade)
    commandLine.append('-G=' + brPath)
    commandLine.append('-V=' + asPath)
    commandLine.append('-R=Y')

    # Execute the process, and retrieve the process object.
    logging.info('Started installing upgrade ' + upgrade)
    logging.debug(commandLine)
    process = subprocess.run(commandLine)   
    
    if process.returncode == 0:
        logging.info('Finished install upgrade ' + upgrade)
    else:
        logging.error('Error while installing upgrade ' + upgrade + ' (return code = ' + process.returncode + ')')
    
    return process.returncode

def main():
    #parse arguments from the command line 
    parser = argparse.ArgumentParser(description='Install AS upgrades')
    parser.add_argument('upgradePath', type=str, help='Path to single upgrade or a folder containing upgrades')
    parser.add_argument('-brp','--brpath', type=str, help='Global AS install path')
    parser.add_argument('-asp','--aspath', type=str, help='AS install path for the desired AS version')
    parser.add_argument('-l', '--logLevel', type=str.upper, help='Log level', choices=['DEBUG','INFO','WARNING', 'ERROR'], default='')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=__version__))   
    args = parser.parse_args()

    # Allow setting log level via command line
    if(args.logLevel):
        lognum = getattr(logging, args.logLevel)
        if not isinstance(lognum, int):
            raise ValueError('Invalid log level: %s' % args.logLevel)
        logging.getLogger().setLevel(level=lognum)

    #save parsed information in to variables. 
    logging.debug('The upgrades Path is: %s', args.upgradePath)
    logging.debug('The global AS install path is: %s', args.brpath)
    logging.debug('The local AS install path is: %s', args.aspath)
    logging.debug('The log level will be: %s', args.logLevel)

    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0



    # service = getService('BrUpgrSrvAS45')
    # print(service)

    # upgradeServiceStatus = os.system('BR.AS.UpgradeService sshd status')
    # logging.debug('Upgrade status %i', upgradeServiceStatus)
    # upgradeServiceStatus = os.system('systemctl is-active --quiet BrUpgrSrvAS45')
    # logging.debug('Upgrade status %i', upgradeServiceStatus)

    logging.debug('Terminal is admin: %i', is_admin)

    if not is_admin:
        logging.error('Admin privileges required. Open terminal with as Administrator')
        sys.exit(1)
        
    

    if os.path.isdir(args.upgradePath):
        # Move into upgrade folder.
        os.chdir(args.upgradePath)
        for upgrade in os.listdir():
            # If the item is a .exe file, try to install it.
            if os.path.isfile(upgrade) and upgrade.lower().endswith('.exe'):         
                installBRUpgrade(upgrade, args.brpath, args.aspath)
    
    elif os.path.isfile(args.upgradePath) and args.upgradePath.lower().endswith('.exe'):
        os.chdir(os.path.dirname(args.upgradePath)) # We do this to match the case above
        installBRUpgrade(args.upgradePath, args.brpath, args.aspath)

    else:
        logging.error('Path provided neither an upgrade or a directory: ' + args.upgradePath)
        sys.exit(args.upgradePath + ' is not a valid AS upgrade')
    
    sys.exit(0)

if __name__ == "__main__":
    
    #configure colored logger
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    main()
