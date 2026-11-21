"""Custom exception classes for structured error handling."""


class AppException(Exception):
    """Base application exception with an error code and status."""

    def __init__(
        self,
        message: str = "An error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: list | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []
        super().__init__(self.message)


class BadRequestError(AppException):
    def __init__(self, message: str = "Bad request", details: list | None = None):
        super().__init__(message, "BAD_REQUEST", 400, details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message, "UNAUTHORIZED", 401)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, "FORBIDDEN", 403)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND", 404)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, "CONFLICT", 409)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", details: list | None = None):
        super().__init__(message, "VALIDATION_ERROR", 422, details)
