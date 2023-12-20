import pytest
import sys
sys.path.append('./src/')
from Package import PackageNameVersion

class Test_PackageNameVersion:
    def test_validInputsNoVersion(self):

        # valid inputs without version number
        validInputsNoVersion = ["atn",
                                "atn@",
                                "/atn",
                                "\\atn",
                                "/atn@",
                                "\\atn@",
                                "@loupeteam/atn",
                                "@loupeteam\\atn",
                                "@loupeteam/atn@",
                                "@loupeteam\\atn@",
                                "ATN",
                                "@LOUPETEAM/atn",
                                ]

        for i in validInputsNoVersion:
            p = PackageNameVersion(i)
            assert p.getBaseName() == "atn"
            assert p.getFullName() == "@loupeteam/atn"
            assert p.getVersion() == ""

    def test_validInputsWithVersion(self):
        # Valid inputs with version number
        validInputsWithVersion = [  "atn@v3.1.0",
                                    "atn@V3.1.0",
                                    "atn@3.1.0",
                                    "atn@03.01.0",
                                    "@loupeteam/atn@v3.1.0",
                                    "@loupeteam/atn@V3.1.0",
                                    "@loupeteam/atn@3.1.0",
                                    "@loupeteam/atn@03.01.0",
                                    "@loupeteam\\atn@v3.1.0",
                                    "@loupeteam\\atn@V3.1.0",
                                    "@loupeteam\\atn@3.1.0",
                                    ]
        
        for i in validInputsWithVersion:
            p = PackageNameVersion(i)
            assert p.getBaseName() == "atn"
            assert p.getFullName() == "@loupeteam/atn"
            assert p.getVersion() == "v3.1.0"

    def test_versionLeadingZeros(self):
        # Leading zeros are not truncated 
        # (though its debatable whether we want to parse to integer)
        p = PackageNameVersion("atn@v03.01.00")
        assert p.getBaseName() == "atn"
        assert p.getFullName() == "@loupeteam/atn"
        assert p.getVersion() == "v03.01.00"

    def test_invalidInputs(self):
        # Invalid inputs
        invalidInputs =    ["atn@v3.1",
                            "atn@v3.1.0.1",
                            "atn@w3.1.0",
                            "atn@v3.a.0",
                            "@somebogusorg/atn",
                            "somebogusorg/atn",
                            "loupeteam/atn",    # maybe this should be valid
                            "#~atn$%~"
                            ]
        
        for i in invalidInputs:
            with pytest.raises(ValueError):
                p = PackageNameVersion(i)