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

# Prevent dual-import of SQLAlchemy models.  When a module is loaded as
# ``app.models.tenant`` *and* later referenced as ``backend.app.models.tenant``,
# Python treats them as separate modules and re-executes the class body,
# causing "Table already defined" errors on the shared DeclarativeBase
# MetaData.  Pre-loading ``app.models`` and aliasing every ``app.*`` module
# under ``backend.app.*`` ensures a single module identity per file.
import importlib as _importlib  # noqa: E402

try:
    _importlib.import_module("app.models")
except Exception:  # pragma: no cover – DB deps may be absent in some envs
    pass
else:
    for _key, _mod in list(sys.modules.items()):
        if _key.startswith("app."):
            _alias = f"backend.{_key}"
            if _alias not in sys.modules:
                sys.modules[_alias] = _mod
    # Also alias the top-level ``app`` package itself.
    if "backend.app" not in sys.modules and "app" in sys.modules:
        sys.modules["backend.app"] = sys.modules["app"]
