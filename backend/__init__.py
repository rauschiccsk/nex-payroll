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
#
# IMPORTANT: In addition to populating sys.modules, we must also set each
# aliased module as an **attribute** on its parent package.  Python's import
# system checks ``hasattr(parent, child)`` when resolving dotted names; if
# the attribute is missing it may attempt to re-import the subpackage from
# disk, bypassing the sys.modules alias and causing duplicate class bodies.
import importlib as _importlib  # noqa: E402

try:
    _importlib.import_module("app.models")
except Exception:  # pragma: no cover – DB deps may be absent in some envs
    pass
else:
    # Alias the top-level ``app`` package first so that child attrs can be set.
    if "app" in sys.modules:
        sys.modules.setdefault("backend.app", sys.modules["app"])

    for _key, _mod in list(sys.modules.items()):
        if _key.startswith("app."):
            _alias = f"backend.{_key}"
            sys.modules.setdefault(_alias, _mod)

    # Set module attributes on parent packages so that Python's attribute
    # lookup (used during dotted-name import resolution) finds the aliased
    # modules without re-importing them from disk.
    _backend_mod = sys.modules.get(__name__)
    if _backend_mod is not None and "app" in sys.modules:
        _backend_mod.app = sys.modules["app"]  # type: ignore[attr-defined]
    _app_mod = sys.modules.get("app")
    if _app_mod is not None and "app.models" in sys.modules:
        _app_mod.models = sys.modules["app.models"]  # type: ignore[attr-defined]
