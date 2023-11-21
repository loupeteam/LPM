'''
 * File: UnitTestTools.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
'''
UnitTest Tools

This package contains tools for running unit tests.
'''

import os
import requests
import subprocess
import logging

class UnitTestServer():
    def __init__(self, host = 'http://127.0.0.1', destination = './TestResults'):
        self._host = host
        self._destination = destination
        self.connected = False
        # Retrieve list of tests.
        try:
            r = requests.get(url = self._host + '/WsTest/?', params = {})
            if r.status_code == 200:
                data = r.json()
                self.testSuites = data['itemList']
                self.connected = True
            else:
                logging.error(f'Received HTTP response {r.status_code} from the test server')
        except Exception as e:
            logging.error(f'Exception occurred while connecting to the test server ({e})')

    def runTest(self, name):
        for testSuite in self.testSuites:
            if testSuite['device'] == name:
                r = requests.get(url = self._host + '/WsTest/' + name, params = {})
                if r.status_code == 200:
                    f = open(f'{os.path.join(self._destination, name)}.xml', 'w')
                    f.write(r.text)
                    f.close()