'''
 * File: CmdLineRunUnitTests.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
"""
@title CmdLineRunUnitTests
@description This python script takes in command line arguments 
and runs a series of unit tests against a live server

0.0.1 - Initial release
"""

# Python Modules
import argparse
import ctypes
import logging
import sys
import os
import shutil

# External Modules
import UnitTestTools  
import _version

def main():

    # Parse arguments from the command line 
    parser = argparse.ArgumentParser(description='Run unit tests via command line.')
    parser.add_argument('host', type=str, help='IP address of the PLC running the tests')
    parser.add_argument('-d', '--destination', type=str, help='Destination directory where test results should get placed')
    parser.add_argument('-a', '--all', action='store_true', help='Run all available tests')
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
    logging.debug('The host to be tested is: %s', args.host)

    logging.info('Querying test server to retrive list of available tests')
    testServer = UnitTestTools.UnitTestServer(args.host, args.destination)

    if testServer.connected:
        for testSuite in testServer.testSuites:
            logging.info(f'Running test suite {testSuite["device"]}')
            testServer.runTest(testSuite['device'])
    else:
        logging.error("Could not connect to the test server")
    
    sys.exit(0)
        
if __name__ == "__main__":
    
    # Configure colored logger
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    main()
