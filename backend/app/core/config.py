"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """NEX Payroll application settings.

    All values are loaded from environment variables.
    Defaults are provided for local development only.
    """

    DATABASE_URL: str = "postgresql+pg8000://payroll:payroll@localhost:5432/payroll"
    PAYROLL_ENCRYPTION_KEY: str = ""
    PAYROLL_JWT_SECRET: str = "dev-secret-change-me"
    OLLAMA_URL: str = "http://localhost:11434"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
