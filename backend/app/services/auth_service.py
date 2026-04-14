"""Authentication service: JWT token management and password hashing.

Provides low-level auth primitives used by routers and other services.
All functions are synchronous (no async).

DESIGN.md §2.3.1:
  - JWT via python-jose, HS256, 30-minute expiry
  - Secret: settings.payroll_jwt_secret
  - Password hashing: Argon2 via pwdlib
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.schemas.auth import TokenPayload

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ---------------------------------------------------------------------------
# Password hashing (Argon2 via pwdlib)
# ---------------------------------------------------------------------------

_pwd_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2.

    Returns the hashed string suitable for storing in ``password_hash`` column.
    """
    return _pwd_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2 hash.

    Returns ``True`` if the password matches, ``False`` otherwise.
    """
    return _pwd_hash.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT token creation / decoding
# ---------------------------------------------------------------------------


def create_access_token(
    user_id: UUID,
    tenant_id: UUID | None,
    role: str,
) -> str:
    """Create a signed HS256 JWT access token.

    Payload contains:
      - sub: str(user_id)
      - tenant_id: str(tenant_id) or None
      - role: user role
      - exp: UTC now + 30 minutes
    """
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id is not None else None,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.payroll_jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT access token.

    Returns a ``TokenPayload`` with the decoded claims.

    Raises:
        ValueError: if the token is invalid, expired, or missing
            required claims.
    """
    try:
        payload = jwt.decode(
            token,
            settings.payroll_jwt_secret,
            algorithms=[ALGORITHM],
        )
    except JWTError as exc:
        raise ValueError("Could not validate credentials") from exc

    sub = payload.get("sub")
    if sub is None:
        raise ValueError("Could not validate credentials")

    try:
        user_id = UUID(sub)
    except ValueError:
        raise ValueError("Could not validate credentials") from None

    tenant_id_raw = payload.get("tenant_id")
    tenant_id: UUID | None = None
    if tenant_id_raw is not None:
        try:
            tenant_id = UUID(tenant_id_raw)
        except ValueError:
            raise ValueError("Could not validate credentials") from None

    role = payload.get("role")
    if role is None:
        raise ValueError("Could not validate credentials")

    exp = payload.get("exp")
    if exp is None:
        raise ValueError("Could not validate credentials")

    return TokenPayload(
        sub=user_id,
        tenant_id=tenant_id,
        role=role,
        exp=int(exp),
    )
