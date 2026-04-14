"""Security utilities: JWT creation/validation, OAuth2 dependency.

DESIGN.md §2.3.1:
  - JWT via python-jose, HS256, 30-minute expiry
  - Token payload: sub=user.id, tenant_id, role, exp
  - Secret: settings.payroll_jwt_secret
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import ALL_ROLES, User
from app.services.auth_service import ALGORITHM  # re-exported for middleware
from app.services.auth_service import create_access_token as _create_access_token_raw

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


def create_access_token(user: User) -> str:
    """Create a signed JWT access token for the given user.

    Delegates to auth_service.create_access_token with user attributes.
    """
    return _create_access_token_raw(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )


# ---------------------------------------------------------------------------
# get_current_user dependency
# ---------------------------------------------------------------------------


def get_current_user(
    token: str = Depends(oauth2_scheme),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    """Decode JWT, load User from DB, verify is_active.

    Raises HTTP 401 if token is invalid, expired, or user not active.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.payroll_jwt_secret, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception from None

    try:
        uid = UUID(user_id)
    except ValueError:
        raise credentials_exception from None

    user = db.get(User, uid)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# ---------------------------------------------------------------------------
# require_role dependency factory
# ---------------------------------------------------------------------------


def require_role(*roles: str):
    """Return a FastAPI dependency that enforces RBAC.

    Usage::

        @router.get("/admin-only", dependencies=[Depends(require_role("director"))])
        def admin_endpoint(): ...

    Raises HTTP 403 if the authenticated user's role is not in *roles*.
    Raises ValueError at import time if an invalid role name is passed.
    """
    invalid = set(roles) - set(ALL_ROLES)
    if invalid:
        raise ValueError(f"Invalid role(s): {invalid}. Valid roles: {ALL_ROLES}")
    allowed: set[str] = set(roles)

    def _check_role(
        current_user: User = Depends(get_current_user),  # noqa: B008
    ) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check_role
