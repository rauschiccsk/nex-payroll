"""NEX Payroll — Configuration module."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str

    # Security
    PAYROLL_ENCRYPTION_KEY: str  # Fernet 32-byte hex key for salary encryption
    PAYROLL_JWT_SECRET: str  # JWT token signing key

    # External services
    OLLAMA_URL: str = "http://andros:9132"  # NEX Brain RAG endpoint

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
