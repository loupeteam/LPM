import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_SRC = os.path.join(_REPO_ROOT, 'src')
_ASPY = os.path.join(_SRC, 'ASPython')

# Prepend in reverse so that `_SRC` ends up at index 0 (highest precedence).
# There's no naming collision today between modules under `src/` and the
# vendored `aspython` package, but ordering the search this way matches the
# intent: project sources first, vendored submodule second.
for path in (_ASPY, _SRC):
    if path not in sys.path:
        sys.path.insert(0, path)
