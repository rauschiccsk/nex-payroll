"""TenantResolverMiddleware — sets PostgreSQL search_path per request.

Extracts tenant_id from the JWT token, resolves the tenant's schema_name,
and stores it in the ``tenant_schema_var`` context variable so that
``get_db()`` can issue ``SET search_path TO {schema}, public``.

Skips auth routes (/api/v1/auth/*), /health, and documentation endpoints.
"""

import logging
import re

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.database import SessionLocal, tenant_schema_var
from app.core.security import ALGORITHM
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# Routes that do NOT require tenant resolution
_SKIP_PATTERN = re.compile(r"^(/health|/api/v1/auth/|/docs|/redoc|/openapi\.json)")


class TenantResolverMiddleware(BaseHTTPMiddleware):
    """Resolve tenant from JWT and set PostgreSQL search_path via context var."""

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

        try:
            payload = jwt.decode(
                jwt_token,
                settings.payroll_jwt_secret,
                algorithms=[ALGORITHM],
            )
            tenant_id: str | None = payload.get("tenant_id")
        except JWTError:
            # Invalid token — let get_current_user raise 401
            return await call_next(request)

        if tenant_id is None:
            return await call_next(request)

        # Look up tenant schema
        db = SessionLocal()
        try:
            tenant = db.get(Tenant, tenant_id)
            if tenant is None or not tenant.is_active:
                logger.warning("Tenant %s not found or inactive", tenant_id)
                return await call_next(request)

            schema_name = tenant.schema_name

            # Store in request.state for downstream access
            request.state.tenant_schema = schema_name
            request.state.tenant_id = tenant_id

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
