"""Shared response envelopes used across all endpoints."""

from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success envelope."""

    success: bool = True
    data: T
    message: str = ""


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[str] = []


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    success: bool = False
    error: ErrorDetail


class PaginatedData(BaseModel, Generic[T]):
    """Wrapper for paginated list responses."""

    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int
