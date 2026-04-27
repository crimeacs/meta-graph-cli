"""Unit tests for GraphClient — no network."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from meta_graph.client import GRAPH_BASE, GRAPH_IG_BASE, GraphClient, detect_base
from meta_graph.errors import (
    AuthError,
    GraphError,
    InvalidRequestError,
    PermissionError_,
    RateLimitError,
    TransientError,
)


def fake_response(status: int = 200, body: Any = None) -> MagicMock:
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.ok = 200 <= status < 300
    r.json = MagicMock(return_value=body if body is not None else {})
    r.text = ""
    return r


def make_client(*, app_secret: str | None = None, retries: int = 0) -> GraphClient:
    s = MagicMock(spec=requests.Session)
    s.headers = {}
    return GraphClient("TOKEN", app_secret=app_secret, retries=retries, session=s)


def test_url_versioning() -> None:
    c = make_client()
    assert c._url("/me") == "https://graph.facebook.com/v22.0/me"
    assert c._url("me/posts") == "https://graph.facebook.com/v22.0/me/posts"
    # already-versioned path is left alone
    assert c._url("/v18.0/me") == "https://graph.facebook.com/v18.0/me"
    # absolute URLs pass through
    assert c._url("https://example.com/x") == "https://example.com/x"


def test_appsecret_proof() -> None:
    c = make_client(app_secret="SECRET")
    proof = c._appsecret_proof()
    # Known SHA-256 HMAC of "TOKEN" with key "SECRET"
    import hashlib
    import hmac
    expected = hmac.new(b"SECRET", b"TOKEN", hashlib.sha256).hexdigest()
    assert proof == expected
    assert make_client()._appsecret_proof() is None


def test_get_injects_auth() -> None:
    c = make_client()
    c.session.request.return_value = fake_response(200, {"id": "1"})  # type: ignore[attr-defined]
    out = c.get("/me", fields="id,name")
    assert out == {"id": "1"}
    args, kwargs = c.session.request.call_args  # type: ignore[attr-defined]
    assert args[0] == "GET"
    assert kwargs["params"]["access_token"] == "TOKEN"
    assert kwargs["params"]["fields"] == "id,name"


def test_post_puts_auth_in_body() -> None:
    c = make_client()
    c.session.request.return_value = fake_response(200, {"id": "1"})  # type: ignore[attr-defined]
    out = c.post("/PAGE_ID/feed", message="hi")
    assert out == {"id": "1"}
    _, kwargs = c.session.request.call_args  # type: ignore[attr-defined]
    assert kwargs["data"]["access_token"] == "TOKEN"
    assert kwargs["data"]["message"] == "hi"


@pytest.mark.parametrize(
    "code,exc",
    [
        (190, AuthError),
        (102, AuthError),
        (200, PermissionError_),
        (10, PermissionError_),
        (4, RateLimitError),
        (32, RateLimitError),
        (1, TransientError),
        (100, InvalidRequestError),
    ],
)
def test_error_mapping(code: int, exc: type[GraphError]) -> None:
    c = make_client(retries=0)
    c.session.request.return_value = fake_response(  # type: ignore[attr-defined]
        400, {"error": {"code": code, "message": "boom"}}
    )
    with pytest.raises(exc):
        c.get("/me")


def test_retry_on_transient() -> None:
    c = make_client(retries=2)
    c.session.request.side_effect = [  # type: ignore[attr-defined]
        fake_response(500, {"error": {"code": 1, "message": "transient"}}),
        fake_response(200, {"ok": True}),
    ]
    # Backoff would sleep; monkeypatch to instant
    c._backoff = lambda _attempt: 0  # type: ignore[method-assign]
    out = c.get("/me")
    assert out == {"ok": True}
    assert c.session.request.call_count == 2  # type: ignore[attr-defined]


def test_no_retry_on_permanent() -> None:
    c = make_client(retries=3)
    c.session.request.return_value = fake_response(  # type: ignore[attr-defined]
        400, {"error": {"code": 100, "message": "bad request"}}
    )
    c._backoff = lambda _attempt: 0  # type: ignore[method-assign]
    with pytest.raises(InvalidRequestError):
        c.get("/me")
    # only one call: code 100 is not retryable
    assert c.session.request.call_count == 1  # type: ignore[attr-defined]


def test_paginate_follows_next() -> None:
    c = make_client()
    c.session.request.return_value = fake_response(  # type: ignore[attr-defined]
        200,
        {
            "data": [{"id": "1"}, {"id": "2"}],
            "paging": {"next": "https://graph.facebook.com/page2"},
        },
    )
    page2 = fake_response(200, {"data": [{"id": "3"}]})
    c.session.get = MagicMock(return_value=page2)  # type: ignore[attr-defined]
    out = list(c.paginate("/me/accounts"))
    assert [x["id"] for x in out] == ["1", "2", "3"]


def test_batch_serializes() -> None:
    c = make_client()
    c.session.post = MagicMock(return_value=fake_response(200, [{"code": 200}]))  # type: ignore[attr-defined]
    out = c.batch([{"method": "GET", "relative_url": "me"}])
    assert out == [{"code": 200}]
    _, kwargs = c.session.post.call_args  # type: ignore[attr-defined]
    assert "batch" in kwargs["data"]
    assert kwargs["data"]["access_token"] == "TOKEN"


def test_token_required() -> None:
    with pytest.raises(ValueError):
        GraphClient("")


def test_detect_base_from_token() -> None:
    assert detect_base("IGAAxxx") == GRAPH_IG_BASE
    assert detect_base("IGQWxxx") == GRAPH_IG_BASE
    assert detect_base("EAAxxx") == GRAPH_BASE
    assert detect_base("123|abc") == GRAPH_BASE
    assert detect_base("anything") == GRAPH_BASE


def test_client_auto_picks_instagram_host_for_igaa() -> None:
    c = GraphClient("IGAAtoken")
    assert c.is_instagram_login is True
    assert c._url("/me") == f"{GRAPH_IG_BASE}/v22.0/me"


def test_client_picks_facebook_host_for_eaa() -> None:
    c = GraphClient("EAAtoken")
    assert c.is_instagram_login is False
    assert c._url("/me") == f"{GRAPH_BASE}/v22.0/me"


def test_explicit_base_overrides_token_prefix() -> None:
    c = GraphClient("IGAAtoken", base="https://example.test/graph")
    assert c.base == "https://example.test/graph"
    assert c.is_instagram_login is False


def test_list_pages_with_ig_synthesizes_for_instagram_login() -> None:
    """IG-direct tokens have no Pages — verify we fake a single-row response."""
    s = MagicMock(spec=requests.Session)
    s.headers = {}
    s.request.return_value = fake_response(
        200, {"user_id": "17841999", "username": "myaccount", "name": "My Account"}
    )
    c = GraphClient("IGAAtok", session=s)
    rows = c.list_pages_with_ig()
    assert len(rows) == 1
    assert rows[0]["instagram_business_account"]["id"] == "17841999"
    assert rows[0]["name"] == "myaccount"
