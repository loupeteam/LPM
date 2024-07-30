import pytest
import os
import sys
from datetime import datetime
import re
import shutil
import json

sys.path.insert(0, "./src")
import LPM


sys.path.insert(0, "./src/ASPython")
import ASTools


LPM_AS_TEMPLATE_FOLDER_NAME = "asproject_template_librarybuilderproject"
LPM_AS_TEMPLATE_PATH = os.path.join("./test/", LPM_AS_TEMPLATE_FOLDER_NAME)

class TestLpmSrc:
    
    @classmethod
    def setup_class(cls):
        # Code to run before each test method

        # Ensure AS Template exists (create if necessary)
        cls.ensure_as_template_exists()

        # create temporary folder
        now = datetime.now()
        timestamp = now.strftime("%y%m%d-%H-%M-%S")
        test_folder = timestamp
        cls.test_dir = os.path.join("./temp/", test_folder)

        # Source directory
        asproject_template_source = LPM_AS_TEMPLATE_PATH

        # Copy the entire directory tree, allowing existing destination
        shutil.copytree(asproject_template_source, cls.test_dir, dirs_exist_ok=True)
        print(f"Copied template to test folder: {cls.test_dir}")

    @classmethod
    def teardown_class(cls):
        # Code to run after each test method

        # shutil.rmtree(cls.test_dir)
        print("Teardown code")
    
    @classmethod
    def ensure_as_template_exists(cls):
        
        # ensure template folder exists
        if not os.path.exists(LPM_AS_TEMPLATE_PATH):
            os.mkdir(LPM_AS_TEMPLATE_PATH)
        
        # determine if already set up with library bulder project 
        try:
            with open(os.path.join(LPM_AS_TEMPLATE_PATH, "package.json")) as p:
                package_dict = json.load(p)
                if "@loupeteam/librarybuilderproject" in package_dict["dependencies"]:
                    template_reinit_required = False
                else:
                    template_reinit_required = True
        except:
            template_reinit_required = True
        
        if template_reinit_required:
            print("No template found. Creating...")

            # delete everything inside the template folder, if any (to start afresh)
            for filename in os.listdir(LPM_AS_TEMPLATE_PATH):
                file_path = os.path.join(LPM_AS_TEMPLATE_PATH, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory and all its contents
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')

            monkeypatch = pytest.MonkeyPatch()

            # lpm init        
            monkeypatch.chdir(path=LPM_AS_TEMPLATE_PATH)
            monkeypatch.setattr(sys, "argv", ["lpm.py", "--silent", "init"])
            LPM.main()

            # lpm install library builder project
            monkeypatch.setattr(sys, "argv", ["lpm.py", "--silent", "install", "librarybuilderproject"])
            LPM.main()
            
            monkeypatch.undo()
            
            # Manually modify package.json (avoid dealing with console prompting with "lpm configure")
            with open(os.path.join(LPM_AS_TEMPLATE_PATH, "package.json"), 'r') as p:
                package_dict = json.load(p)
            package_dict["lpmConfig"] = {"deploymentConfigs": ["Intel", "Arm"], "gitClient": "GitExtensions"}
            with open(os.path.join(LPM_AS_TEMPLATE_PATH, "package.json"), 'w') as p:
                json.dump(package_dict, p, indent=2)

            print("Template creation complete.")

        else:
            print("Template found. No need to (re)create.")

    def test_version(self, capsys, monkeypatch):

        # argparse will exit from within for version, so we need the pytest context manager
        with pytest.raises(SystemExit):
            monkeypatch.setattr(sys, "argv", ["lpm.py", "-v"])
            LPM.main()
        
        # Verify output
        captured = capsys.readouterr()
        version_output = re.fullmatch(r"LPM: \d+\.\d+\.\d+\n", captured.out)
        assert version_output is not None

    # Prior to installing atn, install 1 of 3 dependencies
    def test_stringext_install(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["lpm.py", "install", "stringext"])
        monkeypatch.chdir(self.test_dir)
        try:
            LPM.main()

            with open("package.json") as p:
                package_dict = json.load(p)
                assert "@loupeteam/stringext" in package_dict["dependencies"]
        finally:
            monkeypatch.undo()

    # Prior to installing atn, install 2nd of 3 dependencies, with explicit version
    def test_vartools_install_at_version(self, capsys, monkeypatch):
        monkeypatch.chdir(self.test_dir)

        try:
            # Attempt invalid version
            version_invalid = "0.99.9"
            monkeypatch.setattr(sys, "argv", ["lpm.py", "install", f"vartools@{version_invalid}"])

            LPM.main()
            captured = capsys.readouterr()
            
            print(captured.out)
            err_match = re.search(r"Error while attempting to install package", captured.out)
            assert err_match is not None

            # Attempt valid version
            version_valid = "0.11.3"
            monkeypatch.setattr(sys, "argv", ["lpm.py", "install", f"vartools@{version_valid}"])
        
            LPM.main()

            with open("package.json") as p:
                package_dict = json.load(p)
                assert "@loupeteam/vartools" in package_dict["dependencies"]
                assert version_valid in package_dict["dependencies"]["@loupeteam/vartools"]
        
        finally:
            monkeypatch.undo()

    def test_atn_install_as_src(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["lpm.py", "install", "atn", "-src"])
        monkeypatch.chdir(self.test_dir)
        try:
            LPM.main()
            assert os.path.exists(os.path.join(".", "TempObjects", "sourceInfo.json"))
            # TODO Add more assertions
        finally:
            monkeypatch.undo()

    def test_build_intel(self, monkeypatch):
        monkeypatch.chdir(self.test_dir)
        try:
            project = ASTools.Project(".")
            build_result = project.build("Intel")
            assert build_result.returncode == 0 or build_result.returncode == 1  # 0: no issues, 1: warnings only
        finally:
            monkeypatch.undo()

    def test_build_arm(self, monkeypatch):
        monkeypatch.chdir(self.test_dir)
        try:
            project = ASTools.Project(".")
            build_result = project.build("Arm")
            assert build_result.returncode == 0 or build_result.returncode == 1  # 0: no issues, 1: warnings only
        finally:
            monkeypatch.undo()






