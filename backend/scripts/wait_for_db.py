"""Wait for PostgreSQL database to become available.

Used in CI/CD pipeline to ensure DB is ready before running
migrations and tests. Uses pg8000 driver (ICC standard).
"""

import sys
import time

import pg8000.native


def wait_for_db(dsn: str, max_retries: int = 30, delay: float = 2.0) -> bool:
    """Wait for database to accept connections.

    Args:
        dsn: PostgreSQL connection string.
        max_retries: Maximum number of connection attempts.
        delay: Seconds between retries.

    Returns:
        True if connection succeeded, False otherwise.
    """
    # Parse DSN components from SQLAlchemy-style URL
    # Format: postgresql+pg8000://user:pass@host:port/dbname
    from urllib.parse import urlparse

    parsed = urlparse(dsn.replace("postgresql+pg8000://", "postgresql://"))

    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or ""
    database = parsed.path.lstrip("/") or "postgres"

    for attempt in range(1, max_retries + 1):
        try:
            conn = pg8000.native.Connection(
                user=user,
                password=password,
                host=host,
                port=port,
                database=database,
            )
            conn.run("SELECT 1")
            conn.close()
            print(f"Database ready after {attempt} attempt(s)")
            return True
        except Exception as e:
            print(f"Attempt {attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                time.sleep(delay)

    print("Database not available after all retries")
    return False


if __name__ == "__main__":
    import os

    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql+pg8000://nex_payroll:changeme@localhost:9174/nex_payroll",
    )
    if not wait_for_db(dsn):
        sys.exit(1)
