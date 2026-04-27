"""Tests for error envelope parsing."""
from __future__ import annotations

from meta_graph.errors import (
    AuthError,
    GraphError,
    InvalidRequestError,
    PermissionError_,
    RateLimitError,
    TransientError,
    from_response,
)


def env(code: int, **kw: object) -> dict:
    return {"error": {"code": code, "message": "oops", **kw}}


def test_auth() -> None:
    err = from_response(401, env(190))
    assert isinstance(err, AuthError)
    assert err.code == 190


def test_permission() -> None:
    assert isinstance(from_response(403, env(200)), PermissionError_)
    assert isinstance(from_response(403, env(10)), PermissionError_)


def test_rate_limit() -> None:
    for c in (4, 17, 32, 613):
        assert isinstance(from_response(400, env(c)), RateLimitError), f"code={c}"


def test_transient() -> None:
    for c in (1, 2):
        assert isinstance(from_response(500, env(c)), TransientError), f"code={c}"


def test_invalid_request() -> None:
    assert isinstance(from_response(400, env(100)), InvalidRequestError)


def test_unknown_code_is_base() -> None:
    err = from_response(400, env(999_999))
    assert isinstance(err, GraphError)
    # And not a more-specific subclass
    assert type(err) is GraphError


def test_no_envelope() -> None:
    err = from_response(500, {"raw": "internal"})
    assert isinstance(err, GraphError)
    assert err.http_status == 500


def test_str_includes_code() -> None:
    err = from_response(400, env(190, fbtrace_id="abc"))
    s = str(err)
    assert "code=190" in s
    assert "fbtrace=abc" in s
