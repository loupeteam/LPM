import re

class PackageNameVersion:
    def __init__(self, input: str):
        reValidInput = r"^(@loupeteam[\\\/])?(\w+)@?(@v?(\d+\.\d+\.\d+))?$"
        match = re.search(reValidInput, input, re.IGNORECASE)
        if not match: raise ValueError
        self._baseName = match.group(2).lower()
        self._versionText = match.group(4) if match.group(4) is not None else ''
    
    @property
    def baseName(self):
        return f"{self._baseName}"
    
    @property
    def fullName(self):
        return f"@loupeteam/{self._baseName}"
    
    @property
    def version(self):
        if self._versionText != '':
            return self._versionText
        else:
            return ''