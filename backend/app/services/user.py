"""Service layer for User entity.

Provides CRUD operations over the users table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.

Soft-delete via ``is_active`` flag — list excludes inactive users
by default.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

# ---------------------------------------------------------------------------
# Allowed enum values (validated at service level)
# ---------------------------------------------------------------------------

ALLOWED_ROLES = frozenset({"director", "accountant", "employee"})


def _validate_role(value: str | None) -> None:
    """Raise ``ValueError`` if *value* is not a recognised role."""
    if value is not None and value not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role={value!r}. Allowed values: {sorted(ALLOWED_ROLES)}")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def list_users(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    role: str | None = None,
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
) -> list[User]:
    """Return a paginated list of users ordered by username.

    When *tenant_id* is provided the result is scoped to that tenant.
    When *role* is provided the result is further filtered by role.
    Inactive users are excluded unless *include_inactive* is ``True``.
    """
    stmt = select(User).order_by(User.username)

    if tenant_id is not None:
        stmt = stmt.where(User.tenant_id == tenant_id)

    if role is not None:
        _validate_role(role)
        stmt = stmt.where(User.role == role)

    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


def get_user(db: Session, user_id: UUID) -> User | None:
    """Return a single user by primary key, or ``None``."""
    return db.get(User, user_id)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def create_user(
    db: Session,
    payload: UserCreate,
) -> User:
    """Insert a new user and flush (no commit).

    Validates role and uniqueness constraints at the service level.
    Raises ``ValueError`` if:
    - A user with the same ``(tenant_id, username)`` already exists.
    - A user with the same ``(tenant_id, email)`` already exists.
    - ``role='employee'`` but ``employee_id`` is not set (also enforced by schema).
    """
    _validate_role(payload.role)

    # Check for duplicate username within tenant
    dup_username = select(User).where(
        User.tenant_id == payload.tenant_id,
        User.username == payload.username,
    )
    if db.execute(dup_username).scalar_one_or_none() is not None:
        raise ValueError(f"User with username={payload.username!r} already exists in tenant {payload.tenant_id}")

    # Check for duplicate email within tenant
    dup_email = select(User).where(
        User.tenant_id == payload.tenant_id,
        User.email == payload.email,
    )
    if db.execute(dup_email).scalar_one_or_none() is not None:
        raise ValueError(f"User with email={payload.email!r} already exists in tenant {payload.tenant_id}")

    user = User(**payload.model_dump())
    db.add(user)
    db.flush()
    return user


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def update_user(
    db: Session,
    user_id: UUID,
    payload: UserUpdate,
) -> User | None:
    """Partially update an existing user.

    Only fields explicitly set in *payload* are changed.
    Returns the updated instance or ``None`` if not found.
    Raises ``ValueError`` if the update would create a duplicate
    ``(tenant_id, username)`` or ``(tenant_id, email)``.
    """
    user = db.get(User, user_id)
    if user is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    # Validate role if being changed
    if "role" in update_data:
        _validate_role(update_data["role"])

    # Check for duplicate username if it is being changed
    new_username = update_data.get("username")
    if new_username is not None and new_username != user.username:
        effective_tenant = update_data.get("tenant_id", user.tenant_id)
        dup_stmt = select(User).where(
            User.tenant_id == effective_tenant,
            User.username == new_username,
            User.id != user_id,
        )
        if db.execute(dup_stmt).scalar_one_or_none() is not None:
            raise ValueError(f"User with username={new_username!r} already exists in tenant {effective_tenant}")

    # Check for duplicate email if it is being changed
    new_email = update_data.get("email")
    if new_email is not None and new_email != user.email:
        effective_tenant = update_data.get("tenant_id", user.tenant_id)
        dup_stmt = select(User).where(
            User.tenant_id == effective_tenant,
            User.email == new_email,
            User.id != user_id,
        )
        if db.execute(dup_stmt).scalar_one_or_none() is not None:
            raise ValueError(f"User with email={new_email!r} already exists in tenant {effective_tenant}")

    for field, value in update_data.items():
        setattr(user, field, value)

    db.flush()
    return user


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def delete_user(db: Session, user_id: UUID) -> bool:
    """Delete a user by primary key (hard delete).

    Returns ``True`` if the row was deleted, ``False`` if not found.
    """
    user = db.get(User, user_id)
    if user is None:
        return False

    db.delete(user)
    db.flush()
    return True
