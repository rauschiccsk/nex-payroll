"""Security utilities: JWT creation/validation, OAuth2 dependency.

DESIGN.md §2.3.1:
  - JWT via python-jose, HS256, 30-minute expiry
  - Token payload: sub=user.id, tenant_id, role, exp
  - Secret: settings.payroll_jwt_secret
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


def create_access_token(user: User) -> str:
    """Create a signed JWT access token for the given user.

    Payload: sub=str(user.id), tenant_id=str(user.tenant_id),
             role=user.role, exp=utcnow+30min
    """
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.payroll_jwt_secret, algorithm=ALGORITHM)


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
