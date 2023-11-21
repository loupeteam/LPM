'''
 * File: ASTools.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
'''
AS Tools

This package contains all functions necessary to perform actions on 
AS projects outside of Automation Studio. 
'''

import fnmatch
import os.path
import json
import pathlib
import shutil
import subprocess
from typing import Dict, Tuple, Sequence, Union, List, Optional
import xml.etree.ElementTree as ET
import logging
import sys
import re
import ctypes
import configparser

# TODO: Support finding as default build paths
# TODO: Build project wrapper
# TODO: Move a lot of functionality into classes
# TODO: Add ability to manage package files
# TODO: Switch to lxml
# TODO: Support SGC
# TODO: Support partial library exports, for example if SG4 is successful but SG4-arm fails
#       This will require returning additional information or cleaning up partition exports ourselves
# TODO: Support ARSim

ASReturnCodes = {
    "Errors-Warnings": 3,
    "Errors": 2,
    "Warnings": 1,
    "None": 0
}

PVIReturnCodeText = {
    0: 'Application completed successfully',
    28320: 'File not found (.PIL file or "call" command)', 
    28321: 'Filename not specified (command line parameter)',
    28322: 'Unable to load BRErrorLB.DLL ("ReadErrorLogBook" command)',
    28323: 'DLL entry point not found ("ReadErrorLogBook" command)',
    28324: 'BR module not found ("Download" command)',
    28325: 'Syntax error in command line',
    28326: 'Unable to start PVI Manager ("StartPVIMan" command)',
    28327: 'Unknown command',
    28328: 'Unable to connect ("Connection" command with "C" parameter)',
    28329: 'Unable to establish connection in bootstrap loader mode',
    28330: 'Error transferring operating system in bootstrap loader mode',
    28331: 'Process aborted',
    28332: 'The specified directory doesn\'t exist',
    28333: 'No directory specified',
    28334: 'The application used to create an AR update file wasn\'t found ("ARUpdateFileGenerate" command)',
    28335: 'The specified AR base file (*.s*) is invalid ("ARUpdateFileGenerate" command)',
    28336: 'Error creating the AR update file ("ARUpdateFileGenerate" command)',
    28337: 'There is no valid connection to the PLC. In order to be able to read the CAN baud rate, the CAN ID or the CAN node number, you need a connection to the PLC',
    28338: 'The specified logger module doesn\'t exist on PLC ("Logger" command)',
    28339: 'The specified .br file is not a valid logger module ("Logger" command)',
    28340: 'The .pil file does not contain any information about the AR version to be installed.',
    28341: 'Transfer to the corresponding target system is not possible since the AR version on the target system does not yet support the transfer mode'
}

def getASPath(version:str) -> str:
    base = "C:\\BrAutomation"
    if version.lower() == 'base':
        return base
    else:
        return os.path.join(base, version.upper(), 'Bin-en')

def getASBuildPath(version:str) -> str:
    if version.lower() == 'base':
        return getASPath('base')
    else:
        return os.path.join(getASPath(version), "BR.AS.Build.exe")

def getPVITransferPath(version:str) -> str:
    base = getASPath('base')
    return os.path.join(base, 'PVI', version, 'PVI', 'Tools', 'PVITransfer')

def ASProjetGetConfigs(project: str) -> [str]:

    if(os.path.isfile(project)):
        project = os.path.split(project)[0]

    project = os.path.join(project, 'Physical')

    configs = [d for d in os.listdir(project) if os.path.isdir(os.path.join(project, d))]

    return configs

def batchBuildAsProject(project, ASPath:str, configurations=None, buildMode='Build', tempPath='', logPath='', binaryPath='', simulation=False, additionalArg:Union[str,list,tuple]=None) -> subprocess.CompletedProcess:
    if configurations is None: configurations = []

    for config in configurations:
        completedProcess = buildASProject(project, ASPath, configuration=config, buildMode=buildMode, tempPath=tempPath, logPath=logPath, binaryPath=binaryPath, simulation=simulation, additionalArg=additionalArg)
        if completedProcess.returncode > ASReturnCodes["Warnings"]:
            # Call out the end of a failed build
            logging.info(f'Build for configuration {config} has completed with errors, see DEBUG logging for details')
            return completedProcess
        else:
            # Call out the end of a successful build
            logging.info(f'Build for configuration {config} has completed without errors, see DEBUG logging for details')

    return completedProcess

def buildASProject(project, ASPath:str, configuration='', buildMode='Build', tempPath='', binaryPath='', logPath='', simulation=False, additionalArg:Union[str,list,tuple]=None) -> subprocess.CompletedProcess:
    
    commandLine = []
    commandLine.append(ASPath)
    commandLine.append('"' + os.path.abspath(project) + '"')
    
    if configuration:
        commandLine.append('-c')
        commandLine.append(configuration)
    
    # Possible valid values: Build, Rebuild, BuildAndTransfer, BuildAndCreateCompactFlash
    if buildMode:
        commandLine.append('-buildMode')
        commandLine.append(buildMode) # Documentation says this needs " around value but so far testing proves not
        if(buildMode.capitalize() == 'Rebuild'):
            commandLine.append('-all')
    
    if tempPath:
        commandLine.append('-t')
        commandLine.append(tempPath)

    if binaryPath:
        commandLine.append('-o')
        commandLine.append(binaryPath)
    
    if simulation:
        commandLine.append('-simulation')

    commandLine.append('-buildRUCPackage')

    if additionalArg:
        if type(additionalArg) is str:
            commandLine.append(additionalArg)
        elif type(additionalArg) is list or type(additionalArg) is tuple:
            commandLine.extend(additionalArg)
    
    # Call out the beginning of the build
    logging.info(f'Starting build for configuration {configuration}...')

    # Execute the process, and retrieve the process object for further processing.
    logging.debug(commandLine)
    process = subprocess.Popen(commandLine, stdout=subprocess.PIPE, encoding="utf-8", errors='replace')

    logging.info("Recording build log here: " + os.path.join(logPath, "build.log"))

    with open(os.path.join(logPath, "build.log"), "w", encoding='utf-8') as f:

        # TODO: find out if Jenkins is calling the script, and if not then don't augment the console message
        while process.returncode == None:
            raw = process.stdout.readline()
            data = raw.rstrip()
            f.write(raw)
            if data != "":
                # Search for the "warning" pattern.
                warningMatch = re.search('warning [0-9]*:', data)
                errorMatch = re.search('error [0-9]*:', data)
                if (warningMatch != None):
                    logging.warning("\033[32m" + data +"\033[0m")
                elif (errorMatch != None):
                    logging.error("\033[31m" + data +"\033[0m")
                else:  
                    logging.debug(data)  
            process.poll()

    return process

def CreateARSimStructure(RUCPackage:str, destination:str, version:str, startSim:bool=False):
    logging.info(f'Creating ARSim structure at {destination}')
    RUCPath = os.path.dirname(RUCPackage)
    RUCPil = os.path.join(RUCPath, 'CreateARSim.pil')
    with open(RUCPil, 'w+') as f:
        f.write(f'CreateARsimStructure "{RUCPackage}", "{destination}", "Start={int(startSim)}"\n')
        # If ARsim is being started, add a line that waits for a connection to be established.
        if startSim:
            f.write('Connection "/IF=TCPIP /SA=1", "/DA=2 /DAIP=127.0.0.1 /REPO=11160", "WT=120"')

    arguments = []
    print('PVI version: ' + version)
    arguments.append(os.path.join(getPVITransferPath(version), 'PVITransfer.exe'))
    # arguments.append('-automatic') # startSim only works with automatic mode
    arguments.append('-silent')
    # arguments.append('-autoclose')
    arguments.append(RUCPil)
    logging.debug(arguments)
    process = subprocess.run(arguments)

    logging.debug(process)
    if(process.returncode == 0):
        logging.debug('ARSim created')

        if startSim:
            # This because silent and autoclose mode do not support starting arsim
            pid = subprocess.Popen(os.path.join(destination, 'ar000loader.exe'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, creationflags=0x00000008)
    else:
        logging.debug(f'Error in creating ARSimStructure code {process.returncode}: {PVIReturnCodeText[process.returncode]}')
    
    return process

class LibExportInfo(object):
    def __init__(self, name, path, exception=None, lib=None):
        self.name = name
        self.path = path
        self.lib = lib
        self.exception = exception

        super().__init__()

class ProjectExportInfo(object):
    def __init__(self):
        self._success = []
        self._failed = []
        super().__init__()

    def addLibInfo(self, libInfo:LibExportInfo):
        if libInfo.exception is None:
            self._success.append(libInfo)
        else:
            self._failed.append(libInfo)

    def extend(self, *exportInfo):
        for info in exportInfo:
            self._success.extend(info._success)
            self._failed.extend(info._failed)

    @property
    def success(self) -> List[LibExportInfo]:
        return self._success

    @property
    def failed(self) -> List[LibExportInfo]:
        return self._failed

class Dependency:
    def __init__(self, name:str, minVersion='', maxVersion=''):
        self.name = name
        self.minVersion = minVersion
        self.maxVersion = maxVersion

class BuildConfig:
    def __init__(self, name, path='', typ='sg4', hardware=''):
        self.name = name
        self.type = typ
        self.hardware = hardware
        self.path = path

class xmlAsFile:
    def __init__(self, path: str, new_data:ET.ElementTree=None):
        self.path = path
        if (new_data == None):
            self.read()
        else:
            # In this case we create new content based on type.
            self._package = new_data
            self.package.write(self.path, xml_declaration=True, encoding='utf-8', method='xml')
    
    def read(self):
        '''Reads AS xml file into xml tree'''
        if not os.path.exists(self.path): raise FileNotFoundError(self.path)
        self._package = ET.parse(self.path)
        return self
    
    def write(self):
        '''Writes xml tree to file with AS Namespace'''
        # TODO: This loses the <?AutomationStudio Version=4.4.6.71 SP?>. This shouldn't cause any issues though
        #       This can be solved by extracting xml stuff with file writing (function that returns xml as string) then modify and write that
        ns = self._getASNamespace(self.package)
        ET.register_namespace('', ns) # TODO: This is a ET global effect
        self._indentXml(self.package.getroot()) # When we add items indent gets messed up 
        self.package.write(self.path, xml_declaration=True, encoding='utf-8', method='xml')
        return self

    def find(self, *levels) -> ET.Element:
        path = '.'
        for level in levels:
            path += '/' + self.nameSpaceFormatted + level
        
        return self.root.find(path)
    
    def findall(self, *levels) -> List[ET.Element]:
        path = '.'
        for level in levels:
            path += '/' + self.nameSpaceFormatted + level
        
        return self.root.findall(path)

    @property
    def nameSpaceFormatted(self) -> str:
        ns = self.nameSpace
        if ns != '':
            ns = '{' + ns + '}'
        return ns
    
    @property
    def nameSpace(self) -> str:
        return self._getASNamespace(self.package)

    @property
    def root(self) -> ET.Element:
        return self.package.getroot()
    
    @property
    def package(self) -> ET.ElementTree:
        return self._package

    @property
    def dirPath(self) -> str:
        return os.path.dirname(self.path)

    @property
    def getXmlType(self) -> str:
        '''Returns a string representation of xml type
            Note: This is for debug and view purposes only at this point, API may change
        '''
        # TODO: Populates this list
        #   Package
        #   Library
        #   Program
        #   Hardware - Not Supported
        ns = self._getASNamespace(self.package)
        return ns.split('/')[-1]

    @staticmethod
    def _indentXml(elem: ET.Element, level=0) -> None:
        '''Indent Element and sub elements'''
        
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                xmlAsFile._indentXml(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    @staticmethod
    def _getASNamespace(package: ET.ElementTree) -> str:
        '''Get Automation Studio's namespace for xml files'''
        ns = package.getroot().tag.split('}')
        if ns[0][0] == '{' :
            ns = ns[0][1:]
        else:
            ns = ''

        return ns
        # Examples: 'http://br-automation.co.at/AS/Package', 'http://br-automation.co.at/AS/Physical'

    @staticmethod
    def _getASNamespaceFormatted(package: ET.ElementTree) -> str:
        '''Get Automation Studio's namespace for xml files formatted for ElementTree'''
        ns = xmlAsFile._getASNamespace(package)
        if ns != '':
            ns = '{' + ns + '}'
        return ns

class Library(xmlAsFile):
    '''
    TODO: Lib files appears to support <Files> or <Objects>
        AS will change from Files to Objects when a sub folder is added 
        Using <Objects> when AS prefers <Files> is fine
        Using <Files> when AS prefers <Objects> is also fine
        If changed to a non preferred method, AS will change back everytime it edits the pkg file
    '''
    def __init__(self, path):
        if(os.path.isdir(path)):
            path = os.path.join(path, getLibraryType(path) + '.lby')

        self.name = os.path.basename(os.path.dirname(path)) # Lib name is same as folder name
        self._dependencies = []
        super().__init__(path)
        self._xmlTag = self._getXmlTag(self.package)
        self._xmlTagChild = self._xmlTag[:-1] # We just want to remove the 's'

    @property
    def files(self) -> ET.Element:
        return self.find(self._xmlTag)

    @property
    def fileList(self):
        return self.findall(self._xmlTag, self._xmlTagChild)

    @property
    def dependencyList(self):
        return self.findall('Dependencies', 'Dependency')

    @property
    def dependencies(self) -> List[Dependency]:
        self._dependencies.clear()
        for element in self.dependencyList:
            self._dependencies.append(Dependency(element.get('ObjectName', 'Unknown'), element.get('FromVersion', ''), element.get('ToVersion', '')))

        return self._dependencies

    @property
    def dependencyNames(self) -> List[str]:
        names = []
        for dep in self.dependencies:
            names.append(dep.name)

        return names

    @property
    def version(self) -> str:
        return self.root.get("Version", '0')

    @property
    def description(self) -> str:
        return self.root.get("Description", '')

    @property
    def type(self):
        return getLibraryType(self.dirPath)

    def addObject(self, *paths):
        '''TODO: This should support packages'''
        for path in paths:
            if not os.path.isfile(path) and not os.path.isdir: raise FileNotFoundError(path)

            name = os.path.split(path)[1]
            newPath = os.path.join(self.path, name)
            shutil.copyfile(path, newPath)
            self._addObjectElement(newPath)
        self.write()

    def _addObjectElement(self, path):
        element = self._createPkgElement(path, self._xmlTagChild)
        self.files.append(element)
        if(element.get('Type') == 'Package' and self._xmlTag != 'Objects'):
            self._convertXmlTag(self._xmlTag, 'Objects')

    def addDependency(self, *dependency):
        for dependent in dependency:
            if dependent is not Dependency: raise TypeError('Expected Dependency class got', type(dependent))
            # TODO: Check if dependency exist if so update instead
            self.dependencies.append(self._createDependencyElement(dependent))

    def export(self, dest, buildFolder, buildConfigs, overwrite=False, binary=True, includeVersion=False) -> LibExportInfo:
        path = os.path.join(dest, self.name)
        if(includeVersion):
            path = os.path.join(path, 'V%s' % self.version)
        
        info = LibExportInfo(self.name, path, None, self)
        
        try:
            if overwrite and os.path.exists(path):
                logging.debug('Export already exists, removing %s', path)
                shutil.rmtree(path, onerror=self._rmtreeOnError)
        
            # pathlib.Path(path).mkdir(parents=True, exist_ok=True) # Create directory if it does not exist

            if binary:
                self._collectBinaryLibrary(buildFolder, path, buildConfigs)
            else:
                self._collectSourceLibrary(self.dirPath, path)

        except (FileNotFoundError, FileExistsError) as error:
            logging.debug(error)
            info.exception = error

        return info

    def synchronize(self):
        objects = self.files

        # Read Dir
        items = [i for i in os.listdir(self.dirPath)]
        usedItems = []
        toRemove = []

        # Update XML
        for obj in objects:
            if obj.text not in items:
                # print('Removing:', element.text)
                # Removing here will cause issues with loop 
                toRemove.append(obj)
            else:
                usedItems.append(obj.text)

        for obj in toRemove:
            objects.remove(obj)

        for item in items:
            if item not in usedItems:
                if os.path.splitext(item)[1] != '.lby':
                    if item not in ('SG4', 'SG3', 'SGC'): # We don't want to add library file to files
                        self._addObjectElement(os.path.join(self.dirPath, item))

        # Save
        self.write()

    def _convertXmlTag(self, fromTag: str, toTag: str):
        childTag = toTag[:-1]
        for elem in self.findall(fromTag):
            # print(elem)
            elem.tag = self.nameSpaceFormatted + toTag
            for child in elem:
                # print(child)
                child.tag = self.nameSpaceFormatted + childTag
                if toTag == 'Objects':
                    # We need to add type and so on
                    child.set('Type', 'File')
        
        self._xmlTag = toTag
        self._xmlTagChild = childTag

    def _collectBinaryLibrary(self, buildFolder, dest, buildConfigs:List[BuildConfig]) -> None:
        '''Copies all files for a binary library into dest'''
        
        packageFileName = self.type + '.lby'

        # buildPaths["source"]
        builds = {}
        # builds
        for build in buildConfigs:
            if builds.get(build.type) is None:
                builds[build.type] = build

        # Collect the required source files, while ignoring certain extensions.
        self._collectSourceLibrary(self.dirPath, dest, ['.c','.st','.cpp','.git','.vscode','.gitignore','jenkinsfile','CMakeLists.txt'], True)
        
        if builds.get("sg4") != None:
            self._collectConfigBinary(buildFolder, builds["sg4"], self.name, os.path.join(dest, 'SG4')) # Collect SG4 Intel
        if builds.get("sg4_arm") != None:
            self._collectConfigBinary(buildFolder, builds["sg4_arm"], self.name, os.path.join(dest, 'SG4', 'Arm')) # Collect SG4 ARM

        # TODO: Support SG3 and lower
        
        os.rename(os.path.join(dest, packageFileName), os.path.join(dest, 'Binary.lby'))
        newLib = Library(os.path.join(dest, 'Binary.lby'))
        newLib.root.set('SubType','Binary')
        newLib.synchronize()
        # updateLibraryFile(os.path.join(dest, 'Binary.lby'))
        
        return

    @staticmethod
    def _formatVersionString(version: str) -> str:
        new_version_list = []
        for x in version.split(sep='.'):
            new_version_list.append(str(int(x)))
        return '.'.join(new_version_list)

    @staticmethod
    def _createPkgElement(path: str, tag: str) -> ET.Element:
        # Create the element from path to be added
        attributes = {}
        attributes['Type'] = getPkgType(path)
        if attributes['Type'] == 'Library':
            attributes['Language'] = getLibraryType(path)
        if attributes['Type'] == 'Program':
            attributes['Language'] = getProgramType(path)
        element = ET.Element(tag, attrib=attributes)
        element.text = os.path.split(path)[1]
        element.tail = "\n" #+2*"  " Just stick with newline for now
        return element

    @staticmethod
    def _createDependencyElement(dependency:Dependency):
        # Create the element from path to be added
        attributes = {}
        attributes['ObjectName'] = dependency.name
        if(dependency.minVersion):
            attributes['FromVersion'] = dependency.minVersion
        if(dependency.maxVersion):
            attributes['ToVersion'] = dependency.maxVersion
        return ET.Element('Dependency', attributes)

    @staticmethod
    def _getXmlTag(package: ET.ElementTree) -> str:
        namespace = Library._getASNamespaceFormatted(package)
        for child in package.getroot():
            if child.tag.replace(namespace, '') in ('Files', 'Objects'):
                return child.tag.replace(namespace, '')
        return 'Files' # If none is found. Probably not a .lby file

    @staticmethod
    def _rmtreeOnError(func, path, exc_info):
        '''
        Error handler for ``shutil.rmtree``.

        If the error is due to an access error (read only file)
        it attempts to add write permission and then retries.

        If the error is for another reason it re-raises the error.

        Usage : ``shutil.rmtree(path, onerror=onerror)``
        '''
        import stat
        if not os.access(path, os.W_OK):
            # Is the error an access error ?
            # logging.debug('Access failed on: %s. Allowing access.', path)
            os.chmod(path, stat.S_IWUSR)
            func(path)
        else:
            raise Exception(*exc_info)

    @staticmethod
    def _collectSourceLibrary(sourceFolder: Union[str], dest: Union[str], excludes=None, ignoreFolders=False) -> None:
        '''Copies all files for a source library into dest
        
        Ignores excludes, a glob style sequence
        '''
        if excludes is None: excludes = []

        def _ignorePatterns(path, names):
            ignores = []     

            for name in names:
                # First evaluate the filter list.
                for item in excludes:
                    if name.lower().endswith(item.lower()):
                        ignores.append(name)
                # Then add to it all folders if required. 
                if ignoreFolders and os.path.isdir(os.path.join(path, name)):
                    ignores.append(name)
            return ignores

        # TODO: This errors if directory already exists
        #       This function just doesn't support that
        #       dir_util.copy_tree() is an option but it might not support ignore
        shutil.copytree(sourceFolder, dest, ignore=_ignorePatterns) 
        return

    @staticmethod
    def _collectConfigBinary(tempPath: str, config: BuildConfig, libraryName: str, dest) -> None:
        '''Collects all binary files associated with a HW Config'''

        pathlib.Path(dest).mkdir(parents=True, exist_ok=True) # Create directory if it does not exist

        shutil.copy2(os.path.join(tempPath, 'Objects', config.name, config.hardware, libraryName + '.br'), dest) # Library.br
        shutil.copy2(os.path.join(tempPath, 'Includes', libraryName + '.h'), dest) # Library.h
        shutil.copy2(os.path.join(tempPath, 'Archives', config.name, config.hardware, 'lib' + libraryName + '.a'), dest) # libLibrary.a
        return

    @staticmethod
    def _collectLogicalBinary(sourceFolder: Union[str], dest) -> None:
        '''Collects all Logical View files required for a binary library'''

        pathlib.Path(dest).mkdir(parents=True, exist_ok=True) # Create directory if it does not exist

        validExtensions = ['fun', 'lby', 'var', 'typ', 'md']

        for item in os.listdir(sourceFolder):
            # Get file extension. 
            splitItem = item.split('.')
            extension = splitItem[-1]
            if extension in validExtensions:
                shutil.copy(os.path.join(sourceFolder, item), dest)

        return

class Project(xmlAsFile):
    def __init__(self, path: str):
        if(os.path.isdir(path)):
            # If we are given a dir, find first project file
            # If it doesn't exist super will error
            projectFile = [f for f in os.listdir(path) if f.endswith('.apj')][0] # Use first .apj found in dir
            path = os.path.join(path, projectFile)

        # TODO: Improve error message for file not found
        super().__init__(path)

        self.name = os.path.basename(os.path.splitext(path)[0]) # Get project name from .apj path
        self.sourcePath = os.path.join(self.dirPath, 'Logical')
        self.physicalPath = os.path.join(self.dirPath, 'Physical')
        self.tempPath = os.path.join(self.dirPath, 'Temp')
        self.binaryPath = os.path.join(self.dirPath, 'Binaries')
        self.cacheIgnore = ['_AS', 'Acp10*', 'Arnc0*', 'Mapp*', 'Motion', 'TRF_LIB', 'Mp*', 'As*']
        self.libraries:List[Library] = []

        self.cacheProject()
    
    def _checkIgnore(self, iterable, ignores) -> List[str]:
        if ignores is not None: 
            for ignore in ignores:
                iterable[:] = [name for name in iterable if not fnmatch.fnmatch(name, ignore)]
        return iterable

    def _checkLibIgnore(self, libs:List[Library], ignores) -> List[Library]:
        for ignore in ignores:
            libs[:] = [lib for lib in libs if not fnmatch.fnmatch(lib.path, ignore)]
        return libs

    def _resetCache(self): 
        self.libraries.clear()
        return

    def cacheProject(self):
        self._resetCache()

        for root, dirs, files in os.walk(self.sourcePath, topdown=True):
            dirs[:] = self._checkIgnore(dirs, self.cacheIgnore)
            files[:] = self._checkIgnore(files, self.cacheIgnore)

            for name in files:
                if name.endswith('.lby'): # This is a library
                    try:
                        lib = Library(os.path.join(root, name))
                        self.libraries.append(lib)
                    except:
                        # Do nothing if this lib failed to be found.
                        pass
                if name.endswith('.pkg'): # This is a package, and it could contain a link to a referenced library. 
                    package = Package(os.path.join(root, name))
                    objects = package.findall('Objects', 'Object')
                    for item in objects:
                        # Look for referenced library entries, and add them to the list of libraries.
                        if (item.get('Type', '').lower() == 'library') & (item.get('Reference', '').lower() == 'true'):
                            lib = Library(os.path.join(self.sourcePath, '..', item.text))
                            self.libraries.append(lib)
        return self

    def exportLibraries(self, dest, overwrite=False, buildConfigs:List[BuildConfig]=None, blacklist:list=None, whitelist:list=None, binary=True, includeVersion=False) -> ProjectExportInfo:
        if buildConfigs is None: buildConfigs = self.buildConfigs
        if whitelist is None: whitelist = []
        if blacklist is None: blacklist = []

        # Determine which libraries to build.
        exportLibs = []
        # If there's a 'whitelist', use this as a permissive filter applied to full library list.
        if len(whitelist) > 0:
            # Convert the list to lower case. 
            whitelist = [el.lower() for el in whitelist]
            for lib in self.libraries:
                if lib.name.lower() in whitelist:
                    exportLibs.append(lib)
        # If there's a 'blacklist', use this as a restrictive filter applied to full library list.
        elif len(blacklist) > 0: 
            # Convert the list to lower case. 
            blacklist = [el.lower() for el in blacklist]
            for lib in self.libraries:
                if lib.name.lower() not in blacklist:
                    exportLibs.append(lib)
        else:
            exportLibs = self.libraries.copy()

        exportInfo = ProjectExportInfo()
        for lib in exportLibs:
            print('Exporting ' + lib.name + '...')
            result = lib.export(dest, self.tempPath, self.buildConfigs, overwrite=overwrite, binary=binary, includeVersion=includeVersion)
            exportInfo.addLibInfo(result)

        return exportInfo

    def exportLibrary(self, library:Library, dest:str, overwrite=False, ignores:Union[tuple,list]=None, binary=True, includeVersion=False, withDependencies=True)-> ProjectExportInfo:
        exportInfo = ProjectExportInfo()
        
        if withDependencies:
            # Filter dependencies
            depNames = library.dependencyNames
            depNames = self._checkIgnore(depNames, ignores)
            depNames = self._checkIgnore(depNames, self.cacheIgnore)
            dependencies = self.getLibrariesByName(depNames)

            for dep in dependencies:
                result = self.exportLibrary(dep, dest, ignores=ignores, overwrite=overwrite, binary=binary, includeVersion=includeVersion)
                exportInfo.extend(result)

        result = library.export(dest, self.tempPath, self.buildConfigs, overwrite=overwrite, binary=binary, includeVersion=includeVersion)
        exportInfo.addLibInfo(result)

        return exportInfo

    def build(self, *configNames, buildMode='Build', tempPath='', binaryPath='', simulation=False, additionalArgs:Union[str,list,tuple]=None):
        for configName in configNames:
            simulation_status = self.getHardwareParameter(configName, 'Simulation')
            # Set simulation properly in hardware before building
            if simulation_status == '':
                self.setHardwareParameter(configName, 'Simulation', str(int(simulation)))
            elif bool(int(simulation_status)) != simulation:
                self.setHardwareParameter(configName, 'Simulation', str(int(simulation)))
        
        # TODO: Support should be better supported for return status here. Probably a list
        return batchBuildAsProject(self.path, getASBuildPath(self.ASVersion), configNames, buildMode, tempPath=tempPath, logPath=self.dirPath, binaryPath=binaryPath, simulation=simulation, additionalArg=additionalArgs)

    def createPIP(self, configName, destination):
        logging.info(f'Creating PIP at {destination}')
        
        # ASVersion is in the format AS45, whereas PVIVersion needs to be in the format V4.5.
        pviVersion = self.ASVersion.replace('AS','',1)
        pviVersion = 'V' + pviVersion[:1] + '.' + pviVersion[1:]

        # Retrieve the configuration object based on the name.
        config = self.getConfigByName(configName)

        # Retrieve RUCPackage location (this automatically gets placed by AS in the Binaries/<Config>/<Hardware> folder, and has a default name). 
        RUCPackagePath = os.path.join(self.binaryPath, config.name, config.hardware, 'RUCPackage', 'RUCPackage.zip')

        # Generate a .pil file that will contain a single instruction: CreatePIP.
        RUCFolderPath = os.path.dirname(RUCPackagePath)
        RUCPilPath = os.path.join(RUCFolderPath, 'CreatePIP.pil')
        with open(RUCPilPath, 'w+') as f:
            # TODO: may want to get so of the below options from arguments (i.e. initial install, forced reboot, etc). 
            f.write(f'CreatePIP "{RUCPackagePath}", "InstallMode=ForceReboot InstallRestriction=AllowPartitioning KeepPVValues=0 ExecuteInitExit=1 IgnoreVersion=1", "Default", "SupportLegacyAR=0", "DestinationDirectory={destination}"')

        # Call PVITransfer.exe to run the .pil script that was just created. 
        arguments = []
        arguments.append(os.path.join(getPVITransferPath(pviVersion), 'PVITransfer.exe'))
        arguments.append('-automatic') # bypass GUI prompts
        arguments.append('-silent') # don't show GUI at all
        arguments.append(RUCPilPath)
        arguments.append('-consoleOutput')
        logging.debug(arguments)
        process = subprocess.run(arguments)

        logging.debug(process)
        if(process.returncode == 0):
            logging.debug('PIP created')

        else:
            logging.debug(f'Error in creating PIP, code {process.returncode}: {PVIReturnCodeText[process.returncode]}')
        
        return process

    def createArsim(self, *configNames, startSim = False):
        '''*Deprecated* - see createSim'''
        return self.createSim(configNames, startSim=startSim)
    
    def createSim(self, *configNames, destination, startSim = False):
        pviVersion = self.ASVersion.replace('AS','',1)
        pviVersion = 'V' + pviVersion[:1] + '.' + pviVersion[1:]
        for configName in configNames:
            config = self.getConfigByName(configName)
            CreateARSimStructure(os.path.join(self.binaryPath, config.name, config.hardware, 'RUCPackage', 'RUCPackage.zip'), destination, pviVersion, startSim=startSim)
        pass

    def startSim(self, configName:str, build=False):
        pass

    def getLibraryByName(self, libName:str) -> Library:
        for lib in self.libraries:
            if lib.name == libName:
                return lib

        return None

    def getLibrariesByName(self, libNames:List[str]) -> List[Library]:
        libraries = []
        for lib in self.libraries:
            if lib.name in libNames:
                libraries.append(lib)
        
        return libraries

    def getConfigByName(self, configName:str) -> BuildConfig:
        # TODO: This raises exception if no config is found, StopIteration. Should be more descriptive
        return next(i for i in self.buildConfigs if i.name == configName)

    def getConstantValue(self, filePath:str, varName:str):
        # Retrieve the value of a constant variable defined in a .VAR file. 
        fullFilePath = os.path.join(self.dirPath, filePath)
        f = open(fullFilePath, "r")
        fileContents = f.read()
        return re.search(varName + ".*'(.*)'", fileContents).group(1)

    def getIniValue(self, filePath:str, sectionName:str, keyName:str):
        # Retrieve the value of a key defined in a .ini file. 
        fullFilePath = os.path.join(self.dirPath, filePath)
        config = configparser.ConfigParser()
        config.read(fullFilePath)
        return config[sectionName][keyName]

    @property
    def buildConfigs(self) -> List[BuildConfig]:
        return self._getConfigs(self.physicalPath)

    @property
    def buildConfigNames(self) -> List[str]:
        names = []
        for config in self.buildConfigs:
            names.append(config.name)
        return names

    @property
    def ASVersion(self) -> str:
        with open(self.path, 'r') as f:
            return self._parseASVersion(f.read())

    @staticmethod
    def _parseASVersion(apj:str) -> str:
        result = re.search('<?AutomationStudio Version="(.*)" ', apj).group(1).split('.')
        version = ''.join(result[0:2])     
        return 'AS' + version

    def getHardwareParameter(self, config, paramName) -> str:
        # Retrieve the value of a parameter defined in the configuration's Hardware.hw file. 
        hardwareFile = xmlAsFile(os.path.join(self.physicalPath, config, 'Hardware.hw'))
        element = hardwareFile.find("Module","Parameter[@ID='" + paramName + "']")
        if not element is None:
            attributes = element.attrib
            return attributes['Value']
        else:
            return ''

    def setHardwareParameter(self, config, paramName, paramValue):
        # Write a value to a specified parameter in the configuration's Hardware.hw file.
        hardwareFile = xmlAsFile(os.path.join(self.physicalPath, config, 'Hardware.hw'))
        try: 
            attributes = hardwareFile.find("Module","Parameter[@ID='" + paramName + "']").attrib
            attributes['Value'] = paramValue
            hardwareFile.write()
        except:
            # Getting here means the element to write to doesn't exist. It needs to be created. 
            # Set up the element that needs to be created. 
            attributes = {}
            attributes['ID'] = paramName
            attributes['Value'] = paramValue
            element = ET.Element('Parameter', attrib=attributes)
            # Create a parent map to determine the PLC node where the element will be added. 
            parent_map = {c: p for p in hardwareFile.package.iter() for c in p}
            # Use the ConfigurationID which should (?) always be there...
            config_element = hardwareFile.find("Module","Parameter[@ID='ConfigurationID']")
            for key, value in parent_map.items():
                if config_element == key:
                    parent = value
                    # Now find the parent element, and append the new parameter.
                    parent_element = hardwareFile.find("Module[@Name='" + parent.attrib["Name"] + "']")
                    parent_element.append(element)
                    hardwareFile.write()
                    return

    def _getConfigs(self, physicalPath: str) -> List[BuildConfig]:
        '''Get list of build configurations from physical directory'''
        physical = Package(os.path.join(self.physicalPath, 'Physical.pkg'))
        objects = physical.findall('Objects', 'Object')
        configurations = []
        for config in objects:
            if config.get('Type', '').lower() == 'configuration':
                path = os.path.join(physicalPath, config.text)
                configurations.append(BuildConfig(name=config.text, path=path, hardware=getHardwareFolderFromConfig(path)))
                configurations[-1].type = getConfigType(configurations[-1])
        return configurations

class Package(xmlAsFile):
    '''TODO: Maybe if doesn't exist, create one'''
    def __init__(self, path: str, new_pkg=False):
        if(os.path.isdir(path)):
            path = os.path.join(path, 'Package.pkg')
            if (new_pkg):
                package_element = ET.Element('Package')
                package_element.set('xmlns', 'http://br-automation.co.at/AS/Package')
                objects_element = ET.SubElement(package_element, 'Objects')
                tree = ET.ElementTree(package_element)    
        if (new_pkg):
            super().__init__(path, tree)
        else:         
            super().__init__(path)
        
    def synchPackageFile(self):
        # TODO: Does not handle references

        items = [i for i in os.listdir(self.dirPath)]

        # TODO: update package with directory
        objsText = {}

        # Remove items not in dir from pkg 
        for element in self.objects:
            if element.text not in items:
                self._removePkgObject(element.text)
            else:
                objsText[element.text] = element

        # Add items in dir to pkg
        for item in items:
            if item == os.path.split(self.path)[1]: continue # Ignore pkg file
            if item not in objsText:
                self._addPkgObject(path=os.path.join(self.dirPath, item))

        self.write()
        
        return self

    def addObject(self, path, reference=False):
        '''Copy file or folder to package and directory'''
        name = os.path.basename(path)
        newPath = os.path.join(self.dirPath, name)
        if(os.path.dirname(path) != self.dirPath and not reference):
            # If object is not in dir, add it
            if os.path.isfile(path):
                shutil.copyfile(path, newPath)
            else:
                shutil.copytree(path, newPath)
        return self._addPkgObject(newPath)

    def addEmptyPackage(self, name):
        # Create the package (i.e. just the folder itself).
        full_path = self.dirPath + '/' + name
        os.mkdir(full_path)
        # Add the newly created package to its parent's .pkg.
        self._addPkgObject(full_path)
        # Create the .pkg for this new package.
        newPackage = Package(full_path, True)
        newPackage.write()
        return newPackage

    def removeObject(self, name):
        '''Remove file or folder from package and directory'''
        path_to_remove = os.path.join(self.dirPath, name)
        # Check to see if dealing with file or dir.
        if(os.path.isdir(path_to_remove)):
            shutil.rmtree(path_to_remove)
        elif(os.path.isfile(path_to_remove)):
            os.remove(path_to_remove)
        # Remove the entry from the .pkg file.      
        self._removePkgObject(name)
        return 

    def _removePkgObject(self, name):
        for child in self.objects:
            if (child.text == name):
                self.objects.remove(child)
        self.write()

    def _addPkgObject(self, path: str, reference=False, element: ET.Element = None) -> ET.Element:
        '''
            Add element to objects list in package file

            If no element is specified one will be created from path
        '''
        if(element is None):
            # If no element use provided path
            element = self._createElement(path, reference=reference)
        obj = self.find('Objects')
        obj.append(element)
        self.write()
        return element

    @staticmethod
    def _createElement(path: str, reference=False) -> ET.Element:
        if path is None: raise FileNotFoundError(path)
        # Create the element from path to be added
        attributes = {}
        if reference: attributes['Reference'] = True
        attributes['Type'] = getPkgType(path)
        if attributes['Type'] == 'Library':
            attributes['Language'] = getLibraryType(path)
        if attributes['Type'] == 'Program':
            attributes['Language'] = getProgramType(path)

        element = ET.Element('Object', attrib=attributes)
        if reference:
            element.text = os.path.abspath(path)
        else:
            element.text = os.path.basename(path)
        element.tail = "\n" #+2*"  " Just stick with newline for now
        return element

    @property
    def objects(self):
        return self.find('Objects')

    @property
    def objectList(self):
        return self.findall('Objects', 'Object')

class Task(xmlAsFile):
    def __init__(self, path: str):
        if(os.path.isdir(path)):
            self.path = path
            if('ANSIC.prg' in os.listdir(path)):
                self.type = 'ANSIC'
                super().__init__(os.path.join(path, 'ANSIC.prg'))
            elif('IEC.prg' in os.listdir(path)):
                self.type = 'IEC'
                super().__init__(os.path.join(path, 'IEC.prg'))
            else:
                self.type = None

class SwDeploymentTable(xmlAsFile):
    def __init__(self, path: str):
        if(os.path.isfile(path)):
            self.path = path
            super().__init__(path)
            # Look for any missing TaskClass tags, and add them in at the right locations. 
            # First check to see if target task class exists.
            for i in range(8):
                tc = self.find(f"TaskClass[@Name='Cyclic#{i+1}']")
                if (tc == None):
                    # TC doesn't exist yet, so create it. 
                    tc = self._addRootLevelElement('TaskClass', i, { "Name": f"Cyclic#{i+1}" })
            # Look for the Libraries tag, and add it in there if it's missing. 
            lib = self.find('Libraries')
            if (lib == None):
                lib = self._addRootLevelElement('Libraries')
            self.read()

    def deployLibrary(self, libraryFolder, library, attributes = {}):
        obj = self.find('Libraries')
        # Check to see if that library already exists. 
        for lib in self.libraries:
            if (lib.lower() == library.lower()):
                return
        # Library isn't in there yet, so let's add it.
        element = self._createLibraryElement(libraryFolder, library, attributeOverrides = attributes)
        obj.append(element)
        self.write()

    def deployTask(self, taskFolder, taskName, taskClass):
        # First get a handle on the target task class.
        cyclicName = "Cyclic#" + [s for s in taskClass if s.isdigit()][0]
        tc = self.find(f"TaskClass[@Name='{cyclicName}']")
        # Now check to see if the task has already been deployed here (if so, skip deployment).
        preexistingTask = self.find(f"TaskClass[@Name='{cyclicName}']","Task[@Name='" + taskName[:10] + "']")
        if(preexistingTask is not None):
            return
        # Task isn't in there yet, so let's add it. 
        element = self._createTaskElement(taskFolder, taskName)
        tc.append(element)
        self.write()

    def _createLibraryElement(self, libraryFolder, name, memory: str = 'UserROM', attributeOverrides = {}) -> ET.Element: 
        language = getLibraryType(os.path.join(libraryFolder, name))
        splitPath = os.path.split(libraryFolder)
        parentFolder = splitPath[-1]
        # Create the element from the provided arguments. 
        attributes = {}
        attributes['Name'] = name
        source = ('Libraries', parentFolder, name, 'lby')
        attributes['Source'] = '.'.join(source)
        attributes['Memory'] = memory
        attributes['Language'] = language
        attributes['Debugging'] = 'true'
        for attributeName in attributeOverrides:
            attributes[attributeName] = attributeOverrides[attributeName]
        element = ET.Element('LibraryObject', attrib=attributes)
        element.tail = "\n" #+2*"  " Just stick with newline for now
        return element

    def _createTaskElement(self, taskFolder, taskName, memory: str = 'UserROM') -> ET.Element:
        task = Task(os.path.join('Logical', taskFolder, taskName))
        language = task.type
        # Split the path, and add to it, since cpu.sw expects a '.' separated path. 
        splitPath = os.path.normpath(taskFolder).split(os.sep)
        splitPath.append(taskName)
        splitPath.append('prg')
        # Create the element from the provided arguments. 
        attributes = {}
        attributes['Name'] = taskName[:10] # Only taking the first 10 characters of name, because AS expects the truncation
        attributes['Source'] = '.'.join(splitPath)
        attributes['Memory'] = memory
        attributes['Language'] = language
        attributes['Debugging'] = 'true'
        element = ET.Element('Task', attrib=attributes)
        element.tail = "\n" #+2*"  " Just stick with newline for now
        return element
        
    def _addLibrariesElement(self):
        self._addRootLevelElement('Libraries')
        self.read()
        obj = self.find('Libraries')
        return obj

    def _addRootLevelElement(self, name, index = None, attributes = {}):
        element = ET.Element(name, attrib=attributes)
        element.tail = "\n"
        if (index is None):
            self.root.append(element)
        else:
            self.root.insert(index, element)
        self.write()

    @property
    def libraries(self) -> List:
        libraryList = []
        for element in self.findall('Libraries', 'LibraryObject'):
            libraryList.append(element.get('Name', 'Unknown'))
        return libraryList

class CpuConfig(xmlAsFile):
    def __init__(self, path: str):
        if(os.path.isfile(path)):
            self.path = path
            super().__init__(path)  
            self.buildElement = self.find('Configuration', 'Build')
            self.arElement = self.find('Configuration', 'AutomationRuntime')

    def getGccVersion(self):      
        if 'GccVersion' in self.buildElement.attrib:
            return(self.buildElement.attrib['GccVersion'])
        else:
            return None
    
    def setGccVersion(self, value):
        self.buildElement.attrib['GccVersion'] = value
        self.write()

    def getPreBuildStep(self):      
        if 'PreBuildStep' in self.buildElement.attrib:
            return(self.buildElement.attrib['PreBuildStep'])
        else:
            return None
    
    def setPreBuildStep(self, value):
        self.buildElement.attrib['PreBuildStep'] = value
        self.write()

    def getArVersion(self):
        if 'Version' in self.arElement.attrib:
            return(self.arElement.attrib['Version'])
        else:
            return None
    
    def setArVersion(self, value):
        self.arElement.attrib['Version'] = value
        self.write()
        
    # Define accessible properties.
    gccVersion = property(getGccVersion, setGccVersion)
    preBuildStep = property(getPreBuildStep, setPreBuildStep)
    arVersion = property(getArVersion, setArVersion)

# TODO: Remove
def getConfigs(physicalPath: str) -> List[BuildConfig]:
    '''*Deprecated* - Get list of build configurations from physical directory'''
    # TODO: Remove Fn
    logging.warning('Function getConfigs Deprecated')
    package = readXmlFile(os.path.join(physicalPath, 'Physical.pkg'))
    objects = getPkgObjectList(package)
    configurations = []
    for config in objects:
        if config.get('Type', '').lower() == 'configuration':
            path = os.path.join(physicalPath, config.text)
            configurations.append(BuildConfig(name=config.text, path=path, hardware=getHardwareFolderFromConfig(path)))
            configurations[-1].type = getConfigType(configurations[-1])
    return configurations
# TODO: Move to Build Config Class
def getConfigType(config: BuildConfig) -> str:
    '''Gets the config type based on cpu'''
    # TODO: Move these constants to package scope
    sg4arm = 'sg4_arm'
    sg4 = 'sg4'
    cpu = {
        'x20cp04': sg4arm,
        'x20cp13': sg4,
        'x20cp14': sg4,
        'x20cp3': sg4,
        'apc': sg4,
        '5pc': sg4,
    }

    for key, value in cpu.items():   # iter on both keys and values
            if config.hardware.lower().startswith(key):
                    return value

    return sg4
# TODO: Needed by Library and Package Class. Maybe leave as function
def getLibraryType(path: str) -> str:
    if os.path.exists(os.path.join(path, 'ANSIC.lby')): 
        return 'ANSIC'
    elif os.path.exists(os.path.join(path, 'IEC.lby')):
        return 'IEC'
    elif os.path.exists(os.path.join(path, 'Binary.lby')):
        return 'Binary'
    
    return 'None'
# TODO: Keep with getLibraryType Fn. Maybe leave as function
def getProgramType(path: str) -> str:
    if os.path.exists(os.path.join(path, 'ANSIC.prg')): 
        return 'ANSIC'
    elif os.path.exists(os.path.join(path, 'IEC.prg')):
        return 'IEC'
    elif os.path.exists(os.path.join(path, 'Binary.prg')):
        return 'Binary'
    
    return 'None'
# TODO: Keep with getLibraryType Fn. Maybe leave as function
def getPkgType(path: str):
    if os.path.exists(path) == False: raise FileNotFoundError(path)

    # Could be a :
    #   Package (a folder)
    #   File (myTask.var)
    #   Program (a folder with a .prg)
    #   Library (a folder with a .lby)

    if os.path.isdir(path):
        # Check inside dir to find type
        if getLibraryType(path) != 'None': return 'Library'
        if getProgramType(path) != 'None': return 'Program'
        return 'Package' # TODO: maybe check to make sure it has a .pkg file?
    elif os.path.isfile(path):
        return 'File'
# TODO: Remove
def collectBinaryLibrary(lib: Library, buildFolder, dest, buildName:List[BuildConfig]=None) -> None:
    '''*Deprecated* - Copies all files for a binary library into dest'''
    # TODO: Remove Fn
    logging.warning('Function collectBinaryLibrary Deprecated')
    
    packageFileName = lib.type + '.lby'

    # buildPaths["source"]
    builds = {}
    # builds
    for build in buildName:
        if builds.get(build.type) is None:
            builds[build.type] = build

    collectSourceLibrary(lib.dirPath, dest, ['*.c','*.st'])
    
    if builds.get("sg4") != None:
        collectConfigBinary(buildFolder, builds["sg4"], lib.name, os.path.join(dest, 'SG4')) # Collect SG4 Intel
    if builds.get("sg4_arm") != None:
        collectConfigBinary(buildFolder, builds["sg4_arm"], lib.name, os.path.join(dest, 'SG4', 'Arm')) # Collect SG4 ARM

    # TODO: Support SG3 and lower
    
    os.rename(os.path.join(dest, packageFileName), os.path.join(dest, 'Binary.lby'))
    newLib = Library(os.path.join(dest, 'Binary.lby'))
    newLib.root.set('SubType','Binary')
    newLib.synchronize()
    # updateLibraryFile(os.path.join(dest, 'Binary.lby'))
    
    return
# TODO: Remove
def getASNamespaceFormatted(package: ET.ElementTree) -> str:
    '''*Deprecated*'''
    logging.warning('Function getASNamespaceFormatted Deprecated')
    ns = getASNamespace(package)
    if ns != '':
        ns = '{' + ns + '}'
    return ns
# TODO: Remove
def getASNamespace(package: ET.ElementTree) -> str:
    '''*Deprecated* - Get Automation Studio's namespace for xml files'''
    logging.warning('Function getASNamespace Deprecated')
    ns = package.getroot().tag.split('}')
    if ns[0][0] == '{' :
        ns = ns[0][1:]
    else:
        ns = ''

    return ns
    # return 'http://br-automation.co.at/AS/Package'
    # return 'http://br-automation.co.at/AS/Physical'
# TODO: Remove
def indentXml(elem: ET.Element, level=0):
    '''*Deprecated* - Indent Element and sub elements'''
    logging.warning('Function indentXml Deprecated')
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indentXml(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
# TODO: Remove
def readXmlFile(file: str) -> ET.ElementTree:
    '''*Deprecated* - Reads library, or package file into xml tree'''
    logging.warning('Function readXmlFile Deprecated')
    # nsUnformatted = getASNamespace()
    # ET.register_namespace('', nsUnformatted) # TODO: This is a ET global effect
    # ET.register_namespace('', 'http://br-automation.co.at/AS/Package') # TODO: This is a ET global effect

    # Load File && Parse XML
    package = ET.parse(file)
    return package
# TODO: Remove
def writeXmlFile(file: str, package: ET.ElementTree):
    '''*Deprecated* - Writes xml tree to library, hardware, or package file'''
    logging.warning('Function writeXmlFile Deprecated')
    # TODO: This loses the <?AutomationStudio Version=4.4.6.71 SP?>. This shouldn't cause any issues though
    #       This can be solved by extracting xml stuff with file writing (function that returns xml as string) then modify and write that
    
    ns = getASNamespace(package)
    ET.register_namespace('', ns) # TODO: This is a ET global effect
    indentXml(package.getroot()) # When we add items indent gets messed up 
    package.write(file, xml_declaration=True, encoding='utf-8', method='xml')
    return
# TODO: Remove
def updatePackageFile(file: str, output:str=None) -> None:
    '''*Deprecated* see Package.synchPackageFile - Updates package file with files in directory'''
    # TODO: Does not handle references
    # TODO: Remove Fn
    logging.warning('Funcion updatePackageFile Deprecated')

    if(os.path.isfile(file)):
        directory = os.path.split(file)[0]

    package = readXmlFile(file)
    objs = getPkgObjectList(package)
    items = [i for i in os.listdir(directory)]

    # TODO: update package with directory
    objsText = {}

    for element in objs:
        if element.text not in items:
            removePkgObject(package, element)
        else:
            objsText[element.text] = element

    for item in items:
        if item == os.path.split(file)[1]: continue
        if item not in objsText:
            addPkgObject(package, path=os.path.join(directory, item))
    
    if output is None: output = file
    writeXmlFile(output, package)
    return package
# TODO: Remove
def getPkgObjectList(package: ET.ElementTree) -> List[ET.Element]:
    '''*Deprecated* - Returns objects list from package file'''
    # TODO: Remove Fn
    logging.warning('Function getPkgObjectList Deprectated')
    nameSpace = getASNamespaceFormatted(package)
    root = package.getroot()
    objs = root.findall('./' + nameSpace + 'Objects/' + nameSpace + 'Object')
    return objs
# TODO: Remove
def removePkgObject(package: ET.ElementTree, element: ET.Element):
    '''*Deprecated* - Remove element from objects list in package file'''
    # TODO: Remove Fn
    logging.warning('Function removePkgObject Deprectated')
    nameSpace = getASNamespaceFormatted(package)
    root = package.getroot()
    obj = root.find('./' + nameSpace + 'Objects')
    obj.remove(element)
    return
# TODO: Remove
def addPkgObject(package: ET.ElementTree, element: ET.Element = None, path: str = None) -> ET.Element:
    '''
        *Deprecated* - 
        Add element to objects list in package file

        If no element is specified one will be created from path
    '''
    # TODO: Remove Fn
    logging.warning('Function addPkgObject Deprectated')
    if(element is None):
        # If no element use provided path
        element = createPkgElement(path)
    
    nameSpace = getASNamespaceFormatted(package)
    root = package.getroot()
    obj = root.find('./' + nameSpace + 'Objects')
    obj.append(element)
    return element
# TODO: Remove
def createPkgElement(path: str, reference=False) -> ET.Element:
    '''*Deprecated*'''
    if path is None: raise FileNotFoundError(path)
    # Create the element from path to be added
    attributes = {}
    if reference: attributes['Reference'] = True
    attributes['Type'] = getPkgType(path)
    if attributes['Type'] == 'Library':
        attributes['Language'] = getLibraryType(path)
    if attributes['Type'] == 'Program':
        attributes['Language'] = getProgramType(path)

    element = ET.Element('Object', attrib=attributes)
    if reference:
        element.text = os.path.abspath(path)
    else:
        element.text = os.path.basename(path)
    element.tail = "\n" #+2*"  " Just stick with newline for now
    return element
# TODO: Remove
def collectSourceLibrary(sourceFolder: Union[str], dest: Union[str], excludes=None) -> None:
    '''*Deprecated* - Copies all files for a source library except excludes into dest'''
    # TODO: Remove Fn
    logging.warning('Function collectSourceLibrary Deprecated')
    if excludes is None: excludes = []

    # TODO: This errors if directory already exists
    #       This function just doesn't support that
    #       dir_util.copy_tree() is an option but it might not support ignore
    shutil.copytree(sourceFolder, dest, ignore=shutil.ignore_patterns(*excludes)) 
    return
# TODO: Remove
def collectConfigBinary(tempPath: str, config: BuildConfig, libraryName: str, dest) -> None:
    '''*Deprecated* - Collects all binary files associated with a HW Config'''
    # TODO: Remove Fn
    logging.warning('Function collectConfigBinary Deprecated')
    pathlib.Path(dest).mkdir(parents=True, exist_ok=True) # Create directory if it does not exist

    shutil.copy2(os.path.join(tempPath, 'Objects', config.name, config.hardware, libraryName + '.br'), dest) # Library.br
    shutil.copy2(os.path.join(tempPath, 'Includes', libraryName + '.h'), dest) # Library.h
    shutil.copy2(os.path.join(tempPath, 'Archives', config.name, config.hardware, 'lib' + libraryName + '.a'), dest) # libLibrary.a
    return
# TODO: Remove
def getHardwareFolderFromConfig(configPath):
    '''*Deprecated* - Gets hardware folder name from path to configuration folder'''

    # TODO: We are assuming that there is only one hardware folder under config
    #       This may be a safe assumption but i am not sure
    hardware = [d for d in os.listdir(configPath) if os.path.isdir(os.path.join(configPath, d))][0]

    return hardware

def toDict(obj, classkey=None):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = toDict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return toDict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [toDict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, toDict(value, classkey)) 
            for key, value in obj.__dict__.items() 
            if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj

def main():
    pathlib.Path('Test/Exports').mkdir(parents=True, exist_ok=True) # Create directory if it does not exist

    sandbox = Project('C:\\Projects\\Path\\To\\Project')
    print(toDict(sandbox.buildConfigs))
   
    # input("Press Enter to continue...")
    return

if __name__ == "__main__":
    # Set up color coding
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    
    formatter = '[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s','%m-%d %H:%M:%S'
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    main()