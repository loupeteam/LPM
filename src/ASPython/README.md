# Info
Tool is provided by Loupe  
https://loupe.team  
info@loupe.team  
1-800-240-7042  

# Description

This repo provides Python tooling for interacting with Automation Studio projects in a programmatic way. 

The core capabilities live in the [ASTools](./ASTools.py) script, which contains classes that represent the various levels of an Automation Studio project. Although these can be directly imported into a user script, the more common usage pattern is to wrap this functionality in a user-facing Python script that is intended to be called from the command line directly (with argparse support for argument parsing). Each of these wrapper scripts begin with the `CmdLine` prefix, and their capabilities are briefly described below:
- [CmdLineARSim.py](CmdLineARSim.py): create an ARsim package for a given AS project. With the options to build the project, include user files, and start the simulator. 
- [CmdLineBuild.py](CmdLineBuild.py): build one or more configurations in an AS project. 
- [CmdLineCreateInstaller.py](CmdLineCreateInstaller.py): generate a portable ISS-based Windows installer that includes all required files to run ARsim.
- [CmdLineDeployLibraries.py](CmdLineDeployLibraries.py): deploy Automation Studio libraries to a specific cpu.sw file. 
- [CmdLineExportLib.py](CmdLineExportLib.py): export Automation Studio libraries into shareable binary or source formats. 
- [CmdLineGetSafetyCrc.py](CmdLineGetSafetyCrc.py): retrieve the CRC of the specified B&R Safe Application in a project. 
- [CmdLineGetVersion.py](CmdLineGetVersion.py): retrieve the build version of an AS project. 
- [CmdLinePackageHmi.py](CmdLinePackageHmi.py): package a webHMI-based HMI for distribution. 
- [CmdLineRunUnitTests.py](CmdLineRunUnitTests.py): run the unit tests that are defined in the Automation Studio project. Note that this wrapper uses the [UnitTestTools.py](UnitTestTools.py) backend script. 

For a more detailed look at each script's API, please call the script with the `-h` argument. For example, `python CmdLineBuild.py -h`. 

# Licensing

This project is licensed under the [MIT License](LICENSE).
