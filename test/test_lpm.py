import pytest
import os
import sys
from datetime import datetime
import re
import shutil

sys.path.insert(0, "./src")
import LPM


sys.path.insert(0, "./src/ASPython")
import ASTools

class TestLpmSrc:
    
    def setup_method(self, method):
        # Code to run before each test method

        # create temporary folder
        now = datetime.now()
        timestamp = now.strftime("%y%m%d-%H-%M-%S")
        test_folder = timestamp
        self.test_dir = os.path.join("./temp/", test_folder)

        # Source directory
        asproject_template_source = "./test/asproject_template_librarybuilderproject"

        # Copy the entire directory tree, allowing existing destination
        shutil.copytree(asproject_template_source, self.test_dir, dirs_exist_ok=True)
        print(f"Copied template to test folder: {self.test_dir}")

    def teardown_method(self, method):
        # Code to run after each test method

        # shutil.rmtree(self.test_dir)
        print("Teardown code")
    
    def test_version(self, capsys, monkeypatch):

        # argparse will exit from within for version, so we need the pytest context manager
        with pytest.raises(SystemExit):
            monkeypatch.setattr(sys, "argv", ["lpm.py", "-v"])
            LPM.main()
        
        # Verify output
        captured = capsys.readouterr()
        version_output = re.fullmatch(r"LPM: \d+\.\d+\.\d+\n", captured.out)
        assert version_output is not None

    def test_atn_install_as_src(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["lpm.py", "install", "atn", "-src"])
        monkeypatch.chdir(self.test_dir)
        LPM.main()

        assert os.path.exists(os.path.join(".", "TempObjects", "sourceInfo.json"))

        project = ASTools.Project(".")
        build_result = project.build("Intel")
        assert build_result.returncode == 0

        monkeypatch.undo()

    def test_build(self):
        assert True






