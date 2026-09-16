"""Custom application exceptions and global error response handlers."""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("smartdesk.exceptions")


class SmartDeskException(Exception):
    """Base exception for all domain-specific errors in SmartDesk AI."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class LLMTimeoutException(SmartDeskException):
    """Raised when an external call to Google Gemini LLM times out beyond budget."""

    def __init__(self, message: str = "LLM request exceeded latency budget threshold (4.0s)") -> None:
        super().__init__(
            message=message,
            error_code="LLM_TIMEOUT",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT
        )


class LLMServiceException(SmartDeskException):
    """Raised when an external LLM API returns HTTP 429, 500, or invalid payload."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            error_code="LLM_SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class TicketNotFoundException(SmartDeskException):
    """Raised when a support ticket cannot be located."""

    def __init__(self, ticket_identifier: str) -> None:
        super().__init__(
            message=f"Support ticket '{ticket_identifier}' was not found.",
            error_code="TICKET_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )


class InvalidPromptException(SmartDeskException):
    """Raised when user prompt fails security validation (e.g. prompt injection)."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            message=f"Prompt rejected by security guardrail: {reason}",
            error_code="PROMPT_SECURITY_VIOLATION",
            status_code=status.HTTP_400_BAD_REQUEST
        )


async def smartdesk_exception_handler(request: Request, exc: SmartDeskException) -> JSONResponse:
    """Global exception handler converting domain exceptions to standardized JSON."""
    logger.warning(
        f"Handled SmartDeskException: {exc.error_code} - {exc.message} on {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unexpected unhandled runtime errors."""
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected internal server error occurred. Please contact system support.",
            "error_code": "UNHANDLED_EXCEPTION",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
        }
    )
