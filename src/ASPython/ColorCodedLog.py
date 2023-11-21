'''
 * File: ColorCodedLog.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
# Python Modules
import logging
import sys
from typing import Optional, Union 

def InitializeLogger(logName:str="main", logLevel:Union[int, str, None]=None, logStringFormat:Optional[str]=None, infoColor:Optional[str]=None, debugColor:Optional[str]=None, warningColor:Optional[str]=None, errorColor:Optional[str]=None, criticalColor:Optional[str]=None, disableColors:Optional[bool]=False):
    """Function for Initalizing a logger with a custom format"""
    
    # Find logger with given name. if it does not exist it will create one
    logger = logging.getLogger(logName)

    # Set logging level 
    if logLevel: logger.setLevel(logLevel)

    # For loop through handlers to see if one already exists
    customHandler = None
    for handler in logger.handlers:
        if isinstance(handler.formatter, CustomFormatter):
            customHandler = handler
            logFormatter = handler.formatter
            break

    # Create custom handler if one does not exist
    if customHandler is None:
        customHandler = logging.StreamHandler(sys.stderr)
        customHandler.setLevel(logging.DEBUG)
        logFormatter = CustomFormatter()
        customHandler.setFormatter(logFormatter)
        logger.addHandler(customHandler)

 
    if logStringFormat: logFormatter.msgFormat = logStringFormat

    # Disable colors by removing the color from the format string
    if disableColors:
        logFormatter.debug = ""
        logFormatter.info = ""
        logFormatter.warning = ""
        logFormatter.error = ""
        logFormatter.critical = ""
    else:
        # Only apply color if argument was passed in
        if debugColor: logFormatter.debug = debugColor
        if infoColor: logFormatter.info = debugColor
        if warningColor: logFormatter.warning = debugColor
        if errorColor: logFormatter.error = debugColor
        if criticalColor: logFormatter.critical = debugColor

    return logger

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    # Default values 
    defaultDebug = "\x1b[38;21m"
    defaultInfo = "\x1b[38;21m"
    defaultWarning = "\x1b[33;21m"
    defaultError = "\x1b[31;21m"
    defaultCritical = "\x1b[31;1m"
    defaultReset = "\x1b[0m"   
    defaultMsgFormat = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    def __init__(self):
        self._debug = CustomFormatter.defaultDebug
        self._info = CustomFormatter.defaultInfo
        self._warning = CustomFormatter.defaultWarning 
        self._error = CustomFormatter.defaultError
        self._critical = CustomFormatter.defaultCritical
        self._msgFormat = CustomFormatter.defaultMsgFormat
        self._reset = CustomFormatter.defaultReset
        self.generate()

    # Make setter regenterate formatDict for each property 
    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        self._debug = value
        self.generate()
        return self._debug

    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, value):
        self._info = value
        self.generate()
        return self._info

    @property
    def warning(self):
        return self._warning

    @warning.setter
    def warning(self, value):
        self._warning = value
        self.generate()
        return self._warning

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, value):
        self._error = value
        self.generate()
        return self._error

    @property
    def critical(self):
        return self._critical

    @critical.setter
    def critical(self, value):
        self._critical = value
        self.generate()
        return self._critical

    @property
    def msgFormat(self):
        return self._msgFormat

    @msgFormat.setter
    def msgFormat(self, value):
        self._msgFormat = value
        self.generate()
        return self._msgFormat

    @property
    def reset(self):
        return self._reset

    @reset.setter
    def reset(self, value):
        self._reset = value
        self.generate()
        return self._reset

    def generate(self):
        self._formatDict = {
            logging.DEBUG: self.debug + self.msgFormat + self.reset,
            logging.INFO: self.info + self.msgFormat + self.reset,
            logging.WARNING: self.warning + self.msgFormat + self.reset,
            logging.ERROR: self.error + self.msgFormat + self.reset,
            logging.CRITICAL: self.critical + self.msgFormat + self.reset
        }
        return self

    def format(self, record):
        log_fmt = self._formatDict.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def main():

    logger = InitializeLogger(logLevel="DEBUG")
    logger.info('info message')
    logger.debug('debug message')
    logger.warning('warning message')
    logger.error('error message')

    logger2 = InitializeLogger(debugColor="\x1b[31;21m")
    logger2.debug('debug message red')

    logger = InitializeLogger(disableColors=True)
    logger.info('info message')
    logger.debug('debug message')
    logger.warning('warning message')
    logger.error('error message')
    
    logger2 = InitializeLogger(debugColor="\x1b[31;21m")
    logger2.debug('debug message red')


if __name__ == "__main__":
    main()
    
