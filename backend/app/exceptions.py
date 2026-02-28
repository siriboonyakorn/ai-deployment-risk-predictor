"""
Application-specific exception hierarchy.

Raise these instead of ``fastapi.HTTPException`` in services and routers.
The exception handlers registered in ``main.py`` translate them into proper
JSON responses automatically.
"""

from __future__ import annotations


class AppError(Exception):
    """
    Base class for all application errors.

    Attributes:
        message:     Human-readable description.
        status_code: HTTP status code to return (default 500).
        detail:      Optional extra payload included in the JSON body.
    """

    status_code: int = 500

    def __init__(self, message: str = "Internal server error", *, status_code: int | None = None, detail: str | None = None):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.detail = detail or message
        super().__init__(self.message)


# ── 4xx ────────────────────────────────────────────────────────────────

class NotFoundError(AppError):
    """Resource not found (404)."""
    status_code = 404

    def __init__(self, resource: str = "Resource", identifier: str | int = ""):
        msg = f"{resource} '{identifier}' not found." if identifier else f"{resource} not found."
        super().__init__(msg)


class ConflictError(AppError):
    """Duplicate / already-exists (409)."""
    status_code = 409

    def __init__(self, message: str = "Resource already exists."):
        super().__init__(message)


class ValidationError(AppError):
    """Unprocessable input (422)."""
    status_code = 422


class AuthenticationError(AppError):
    """Unauthenticated request (401)."""
    status_code = 401

    def __init__(self, message: str = "Not authenticated."):
        super().__init__(message)


class ForbiddenError(AppError):
    """Forbidden / rate-limited (403)."""
    status_code = 403

    def __init__(self, message: str = "Forbidden."):
        super().__init__(message)


# ── 5xx ────────────────────────────────────────────────────────────────

class ExternalServiceError(AppError):
    """Upstream API failure (502)."""
    status_code = 502

    def __init__(self, service: str = "external service", reason: str = ""):
        msg = f"Error communicating with {service}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class ServiceUnavailableError(AppError):
    """Feature not configured / dependency missing (503)."""
    status_code = 503

    def __init__(self, message: str = "Service unavailable."):
        super().__init__(message)
