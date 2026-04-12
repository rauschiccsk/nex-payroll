"""Application settings via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """NEX Payroll application settings.

    Loaded from environment variables (and .env file if present).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+pg8000://nex_payroll:changeme@db:5432/nex_payroll"
    test_database_url: str = "postgresql+pg8000://nex_payroll:changeme@db:5432/nex_payroll_test"

    # Security
    secret_key: str = "changeme-generate-a-real-secret-key"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:9173",
        "http://localhost:5173",
    ]

    # Application
    app_name: str = "NEX Payroll"
    debug: bool = False


settings = Settings()
