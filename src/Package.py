import re

class PackageNameVersion:
    def __init__(self, input: str):
        reValidInput = r"^(@loupeteam[\\\/])?(\w+)@?(@v?(\d+\.\d+\.\d+))?$"
        match = re.search(reValidInput, input, re.IGNORECASE)
        if not match: raise ValueError
        self.baseName = match.group(2).lower()
        self.versionText = match.group(4) if match.group(4) is not None else ''
    
    def getBaseName(self):
        return f"{self.baseName}"
    
    def getFullName(self):
        return f"@loupeteam/{self.baseName}"
    
    def getVersion(self):
        if self.versionText != '':
            return self.versionText
        else:
            return ''