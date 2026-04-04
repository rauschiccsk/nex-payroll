"""Tests for Alembic migration configuration."""

import os

from alembic.config import Config
from alembic.script import ScriptDirectory


def _get_alembic_config() -> Config:
    """Return Alembic Config pointing at our alembic.ini."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(backend_dir, "alembic.ini")
    config = Config(ini_path)
    # Override script_location to absolute path
    config.set_main_option(
        "script_location",
        os.path.join(backend_dir, "alembic"),
    )
    return config


def test_alembic_revision_chain_is_linear():
    """Verify migration chain has no branches or gaps."""
    config = _get_alembic_config()
    script_dir = ScriptDirectory.from_config(config)

    revisions = list(script_dir.walk_revisions())
    assert len(revisions) > 0, "No migrations found"

    # Verify chain: walk from head to base without branching
    heads = script_dir.get_heads()
    assert len(heads) == 1, f"Expected single head, got {heads}"

    base = script_dir.get_base()
    assert base is not None, "No base revision found"


def test_alembic_initial_migration_exists():
    """Verify 001_create_schemas migration exists and has correct structure."""
    config = _get_alembic_config()
    script_dir = ScriptDirectory.from_config(config)

    rev = script_dir.get_revision("001")
    assert rev is not None, "Revision 001 not found"
    assert rev.down_revision is None, "Initial migration should have no down_revision"


def test_alembic_env_imports_base():
    """Verify env.py can import Base metadata for autogenerate."""
    from app.models import Base

    assert Base.metadata is not None
    # At minimum, Base should be importable with metadata
    assert hasattr(Base.metadata, "tables")
