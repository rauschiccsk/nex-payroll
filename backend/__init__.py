"""NEX Payroll backend package."""

import os
import sys

# When ``backend`` is imported as a top-level package (e.g.
# ``from backend.app.services.x import …``), the internal modules rely on
# ``from app.…`` imports.  Ensure the *backend/* directory itself is on
# sys.path so that ``app`` resolves correctly.
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
