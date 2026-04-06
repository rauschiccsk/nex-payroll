"""Generic paginated response schema for list endpoints."""

from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    """Paginated list response: {"items": [...], "total": N, "skip": 0, "limit": 50}."""

    items: list[T]
    total: int
    skip: int
    limit: int
