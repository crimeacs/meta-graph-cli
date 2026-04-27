"""Typed exceptions mirroring Meta's Graph API error taxonomy.

Reference: https://developers.facebook.com/docs/graph-api/guides/error-handling
Codes drawn from the documented top-level error.code values.
"""
from __future__ import annotations

from typing import Any


class GraphError(Exception):
    """Base for any Graph API error response."""

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        subcode: int | None = None,
        type_: str | None = None,
        fbtrace_id: str | None = None,
        http_status: int | None = None,
        body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.type = type_
        self.fbtrace_id = fbtrace_id
        self.http_status = http_status
        self.body = body or {}

    def __str__(self) -> str:
        bits = [super().__str__()]
        if self.code is not None:
            bits.append(f"code={self.code}")
        if self.subcode is not None:
            bits.append(f"subcode={self.subcode}")
        if self.fbtrace_id:
            bits.append(f"fbtrace={self.fbtrace_id}")
        return " | ".join(bits)


class AuthError(GraphError):
    """Token invalid, expired, or session has been invalidated. (codes 102, 190)"""


class PermissionError_(GraphError):
    """Missing permission / scope. (codes 10, 200, 299)"""


class RateLimitError(GraphError):
    """Throttling. (codes 4, 17, 32, 613)"""


class TransientError(GraphError):
    """Temporary, retryable. (codes 1, 2)"""


class InvalidRequestError(GraphError):
    """Malformed request, missing parameter. (codes 100, 803)"""


# Map Meta error.code -> exception class. Default falls back to GraphError.
_CODE_MAP: dict[int, type[GraphError]] = {
    1: TransientError,
    2: TransientError,
    4: RateLimitError,
    10: PermissionError_,
    17: RateLimitError,
    32: RateLimitError,
    100: InvalidRequestError,
    102: AuthError,
    190: AuthError,
    200: PermissionError_,
    299: PermissionError_,
    613: RateLimitError,
    803: InvalidRequestError,
}


# Codes worth retrying with exponential backoff (transient + rate-limit).
RETRYABLE_CODES = {1, 2, 4, 17, 32, 613}


def from_response(http_status: int, body: dict[str, Any]) -> GraphError:
    """Build a typed GraphError from a Meta error envelope.

    The envelope is `{"error": {"message": "...", "code": <int>, ...}}` per
    https://developers.facebook.com/docs/graph-api/guides/error-handling
    """
    err = body.get("error") if isinstance(body, dict) else None
    if not isinstance(err, dict):
        return GraphError(f"HTTP {http_status}: {body!r}", http_status=http_status, body=body)
    code = err.get("code")
    cls = _CODE_MAP.get(int(code), GraphError) if isinstance(code, int) else GraphError
    return cls(
        err.get("message", "Graph API error"),
        code=err.get("code"),
        subcode=err.get("error_subcode"),
        type_=err.get("type"),
        fbtrace_id=err.get("fbtrace_id"),
        http_status=http_status,
        body=body,
    )
