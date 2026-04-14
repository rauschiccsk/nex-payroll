"""FastAPI dependencies for request-scoped DB sessions and authentication.

Provides:
  - ``get_db``  — re-exported from ``app.core.database``; yields a synchronous
    SQLAlchemy Session (pg8000 driver) with tenant-schema search_path support.
  - ``get_current_user`` — decodes JWT via ``auth_service.decode_token``,
    loads User via ``user_service.get_user_by_id``, enforces ``is_active``.

Both are **def** (synchronous) — NEVER async def.
"""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Re-export the canonical get_db from core.database — it already handles
# tenant schema isolation via tenant_schema_var context variable.
from app.core.database import get_db  # noqa: F401
from app.models.user import ALL_ROLES, User
from app.services.auth_service import decode_token
from app.services.user_service import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

__all__ = ["get_db", "get_current_user", "require_role"]


# ---------------------------------------------------------------------------
# get_current_user — JWT validation + DB lookup
# ---------------------------------------------------------------------------


def get_current_user(
    token: str = Depends(oauth2_scheme),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    """Decode JWT bearer token, load the corresponding User, verify active.

    Flow:
      1. Extract and validate JWT via ``auth_service.decode_token``.
      2. Load User from DB by ``payload.sub`` (user UUID).
      3. Verify user exists and ``is_active`` is True.

    Raises:
        HTTPException 401: token invalid/expired, user not found, or inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except ValueError:
        raise credentials_exception from None

    user = get_user_by_id(db, payload.sub)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# ---------------------------------------------------------------------------
# require_role — RBAC enforcement
# ---------------------------------------------------------------------------


def require_role(*allowed_roles: str) -> Callable[..., Any]:
    """Return a FastAPI dependency that enforces role-based access control.

    Usage::

        @router.get("/admin", dependencies=[Depends(require_role("director"))])
        def admin_endpoint(): ...

        @router.get("/manage", dependencies=[Depends(require_role("director", "accountant"))])
        def manage_endpoint(): ...

    The returned dependency calls ``get_current_user`` (JWT validation) and
    then checks that ``current_user.role`` is among *allowed_roles*.

    Raises:
        ValueError: if any role name is not in ``ALL_ROLES`` (at definition time).
        HTTPException 403: if the authenticated user's role is not permitted.
    """
    invalid = set(allowed_roles) - set(ALL_ROLES)
    if invalid:
        raise ValueError(f"Invalid role(s): {invalid}. Valid roles: {ALL_ROLES}")

    def _role_checker(
        current_user: User = Depends(get_current_user),  # noqa: B008
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _role_checker
