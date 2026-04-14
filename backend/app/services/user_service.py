"""High-level user service for authentication and user management.

Provides ``authenticate_user``, ``get_user_by_id``, and ``create_user``
functions that build on the lower-level user CRUD service and auth
service (JWT / password hashing from Task 13.1).

All functions are synchronous (def, not async def) and accept a
SQLAlchemy ``Session``.  They flush but never commit — the caller
(typically a FastAPI endpoint) owns the transaction.

Errors are reported via ``ValueError`` — the router layer catches
them and converts to the appropriate HTTP status code.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth_service import hash_password, verify_password

# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------


def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> User | None:
    """Authenticate a user by username and password.

    Queries the public ``users`` table for an active user matching the
    given *username*.  If found, verifies *password* against the stored
    Argon2 hash.  On success, updates ``last_login_at`` and flushes.

    Returns the ``User`` instance on success, ``None`` when the
    username is not found, the account is inactive, or the password
    does not match.
    """
    stmt = select(User).where(
        User.username == username,
        User.is_active.is_(True),
    )
    user = db.execute(stmt).scalar_one_or_none()

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    # Update last_login_at on successful authentication
    user.last_login_at = datetime.now(UTC)
    db.flush()
    return user


# ---------------------------------------------------------------------------
# get_user_by_id
# ---------------------------------------------------------------------------


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    """Return a single user by primary key, or ``None``.

    Uses ``Session.get`` for optimal PK lookup (identity-map aware).
    """
    return db.get(User, user_id)


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user with password hashing and constraint validation.

    Validates:
    - Unique ``(tenant_id, username)`` — raises ``ValueError`` on duplicate.
    - Unique ``(tenant_id, email)`` — raises ``ValueError`` on duplicate.
    - ``role='employee'`` requires ``employee_id`` (also enforced by schema).

    The plaintext password from *user_data* is hashed via Argon2 before
    persisting.  Flushes but does **not** commit — the caller owns the
    transaction.

    Returns the newly created ``User`` instance (with server-generated
    ``id`` and timestamps populated after flush).

    Raises:
        ValueError: on constraint violations (duplicate username/email,
            missing employee_id for role='employee').
    """
    # -- Validate unique username within tenant --
    dup_username = select(User).where(
        User.tenant_id == user_data.tenant_id,
        User.username == user_data.username,
    )
    if db.execute(dup_username).scalar_one_or_none() is not None:
        raise ValueError(f"User with username={user_data.username!r} already exists in tenant {user_data.tenant_id}")

    # -- Validate unique email within tenant --
    dup_email = select(User).where(
        User.tenant_id == user_data.tenant_id,
        User.email == user_data.email,
    )
    if db.execute(dup_email).scalar_one_or_none() is not None:
        raise ValueError(f"User with email={user_data.email!r} already exists in tenant {user_data.tenant_id}")

    # -- Build model instance --
    data = user_data.model_dump()
    data["password_hash"] = hash_password(data.pop("password"))

    user = User(**data)
    db.add(user)
    db.flush()
    return user
