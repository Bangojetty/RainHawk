"""Make `dawn_walker` importable when pytest runs from the project root.

Pytest is invoked from `projects/dawn-walker/`, so the project root is the
parent of this `tests/` directory. Add it to sys.path so `import
dawn_walker` works without an editable install.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
