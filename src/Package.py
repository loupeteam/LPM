import re

class PackageNameVersion:
    def __init__(self, input: str):

        # Extract text after optional org prefix
        reOrgPrefix = r"^(@loupeteam[\\\/])?([\w@\.]+)$"
        match = re.search(reOrgPrefix, input, re.IGNORECASE)
        if not match: raise ValueError
        inputWithoutOrg = match.group(2)
        
        # Extract package name and optional version
        rePackageAndVersion = r"^(\w+)@?(@v?(\d+\.\d+\.\d+))?$"
        match = re.search(rePackageAndVersion, inputWithoutOrg, re.IGNORECASE)
        if not match: raise ValueError
        self.baseName = match.group(1).lower()
        if match.group(3) is not None:
            self.versionText = match.group(3)
        else:
            self.versionText = ''  

    def getBaseName(self):
        return f"{self.baseName}"
    
    def getFullName(self):
        return f"@loupeteam/{self.baseName}"
    
    def getVersion(self):
        if self.versionText != '':
            return f"v{self.versionText}"
        else:
            return ''