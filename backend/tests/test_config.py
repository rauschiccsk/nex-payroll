"""Tests for application settings (app.core.config)."""

from app.core.config import Settings, settings


def test_settings_instance_exists():
    """Verify settings singleton is created on module import."""
    assert settings is not None
    assert isinstance(settings, Settings)


def test_settings_default_database_url():
    """Verify default DATABASE_URL uses pg8000 driver."""
    s = Settings()
    assert "pg8000" in s.database_url
    assert s.database_url.startswith("postgresql+pg8000://")


def test_settings_default_test_database_url():
    """Verify default TEST_DATABASE_URL uses pg8000 driver and separate DB."""
    s = Settings()
    assert "pg8000" in s.test_database_url
    assert s.test_database_url.startswith("postgresql+pg8000://")
    assert s.test_database_url != s.database_url


def test_settings_default_app_name():
    """Verify default app name."""
    s = Settings()
    assert s.app_name == "NEX Payroll"


def test_settings_default_debug_is_false():
    """Verify debug mode is off by default."""
    s = Settings()
    assert s.debug is False


def test_settings_default_secret_key():
    """Verify a default secret key exists (placeholder)."""
    s = Settings()
    assert s.secret_key is not None
    assert len(s.secret_key) > 0
