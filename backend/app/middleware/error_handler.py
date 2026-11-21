"""Global exception handler middleware."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException

logger = logging.getLogger("societyos")


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all AppException subclasses with a consistent JSON envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — log and return 500."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": [],
            },
        },
    )
