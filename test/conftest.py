import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_SRC = os.path.join(_REPO_ROOT, 'src')
_ASPY = os.path.join(_SRC, 'ASPython')

for path in (_SRC, _ASPY):
    if path not in sys.path:
        sys.path.insert(0, path)
