"""TenantResolverMiddleware -- sets PostgreSQL search_path per request.

Extracts tenant_id and role from the JWT token, resolves the tenant's
schema_name, and stores it in the ``tenant_schema_var`` context variable
so that ``get_db()`` issues ``SET search_path TO {schema}, shared, public``.

Attaches ``request.state.current_user`` (User object) and
``request.state.tenant_id`` for downstream access.

Skips auth routes (/api/v1/auth/*), /health, and documentation endpoints.

Raises:
    401 if JWT is invalid, expired, or user not found / inactive.
    403 if the resolved tenant is inactive.
"""

import logging
import re

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.database import SessionLocal, tenant_schema_var
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth_service import decode_token

logger = logging.getLogger(__name__)

# Routes that do NOT require tenant resolution
_SKIP_PATTERN = re.compile(r"^(/health|/api/v1/auth/|/docs|/redoc|/openapi\.json)")


class TenantResolverMiddleware(BaseHTTPMiddleware):
    """Resolve tenant from JWT and set PostgreSQL search_path via context var.

    For each authenticated request:
    1. Decode JWT -> extract tenant_id, role, user_id.
    2. Load User from DB, attach to ``request.state.current_user``.
    3. If role == 'superadmin': skip search_path, ``request.state.tenant_id = None``.
    4. Else: look up Tenant -> set ``tenant_schema_var`` context var.
    5. Return 401 on invalid JWT / missing user, 403 on inactive tenant.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path

        # Skip routes that don't need tenant context
        if _SKIP_PATTERN.match(path):
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            # No token — let the endpoint's own auth dependency handle 401
            return await call_next(request)

        jwt_token = auth_header[len("Bearer ") :]

        # Decode JWT — raises ValueError on invalid / expired token
        try:
            token_payload = decode_token(jwt_token)
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Could not validate credentials"},
            )

        # Load user from DB
        db = SessionLocal()
        try:
            user = db.get(User, token_payload.sub)
            if user is None or not user.is_active:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Could not validate credentials"},
                )

            # Attach user object to request state
            request.state.current_user = user

            # Superadmin: skip search_path setup entirely
            if token_payload.role == "superadmin":
                request.state.tenant_id = None
                return await call_next(request)

            # Regular user: tenant_id is required
            tenant_id = token_payload.tenant_id
            if tenant_id is None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Could not validate credentials"},
                )

            tenant = db.get(Tenant, tenant_id)
            if tenant is None:
                logger.warning("Tenant %s not found", tenant_id)
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Could not validate credentials"},
                )

            if not tenant.is_active:
                logger.warning("Tenant %s is inactive", tenant_id)
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Tenant is inactive"},
                )

            schema_name = tenant.schema_name

            # Store in request.state for downstream access
            request.state.tenant_schema = schema_name
            request.state.tenant_id = str(tenant_id)

            # Set context variable so get_db() picks it up and
            # issues SET search_path on the endpoint's session.
            ctx_token = tenant_schema_var.set(schema_name)
            try:
                response = await call_next(request)
                return response
            finally:
                tenant_schema_var.reset(ctx_token)
        finally:
            db.close()
