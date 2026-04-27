"""GraphClient — a thin HTTP wrapper around graph.facebook.com.

Designed for the CLI but usable as a library. Handles:
  - URL construction with the configured Graph API version
  - Optional appsecret_proof signing (HMAC-SHA256 of token using app_secret)
  - Cursor-based pagination via `paginate()`
  - Batched requests via `batch()`
  - Exponential-backoff retry on retryable error codes
  - Typed exception mapping via meta_graph.errors.from_response
"""
from __future__ import annotations

import hashlib
import hmac
import json
import random
import re
import time
from collections.abc import Iterator
from typing import Any

import requests

from meta_graph.errors import RETRYABLE_CODES, GraphError, from_response
from meta_graph.version import DEFAULT_API_VERSION, __version__

GRAPH_BASE = "https://graph.facebook.com"
USER_AGENT = f"meta-graph-cli/{__version__}"

# Matches a leading /vXX.Y/ segment so we don't double-version paths.
_VERSION_PREFIX = re.compile(r"^/v\d+(\.\d+)?/")


class GraphClient:
    def __init__(
        self,
        token: str,
        *,
        version: str = DEFAULT_API_VERSION,
        app_secret: str | None = None,
        timeout: int = 30,
        retries: int = 3,
        base: str = GRAPH_BASE,
        session: requests.Session | None = None,
    ) -> None:
        if not token:
            raise ValueError("Access token is required")
        self.token = token
        self.version = version if version.startswith("v") else f"v{version}"
        self.app_secret = app_secret
        self.timeout = timeout
        self.retries = max(0, retries)
        self.base = base.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    # ----- URL building --------------------------------------------------

    def _url(self, path: str) -> str:
        path = path.strip()
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        if _VERSION_PREFIX.match(path):
            return self.base + path
        return f"{self.base}/{self.version}{path}"

    def _appsecret_proof(self) -> str | None:
        if not self.app_secret:
            return None
        return hmac.new(
            self.app_secret.encode("utf-8"),
            self.token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _auth_extras(self) -> dict[str, str]:
        out = {"access_token": self.token}
        proof = self._appsecret_proof()
        if proof:
            out["appsecret_proof"] = proof
        return out

    # ----- Core request --------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> Any:
        """Send a single request with retry on transient/rate-limit errors."""
        url = self._url(path)
        method = method.upper()
        auth = self._auth_extras()

        if method in ("GET", "DELETE"):
            send_params: dict[str, Any] | None = {**(params or {}), **auth}
            send_data: dict[str, Any] | None = None
        else:
            send_params = params or None
            send_data = {**(data or {}), **auth}

        last_network_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.request(
                    method,
                    url,
                    params=send_params,
                    data=send_data,
                    files=files,
                    timeout=self.timeout,
                )
            except requests.RequestException as e:
                last_network_exc = e
                if attempt < self.retries:
                    time.sleep(self._backoff(attempt))
                    continue
                raise GraphError(f"network error: {e}") from e

            try:
                body = resp.json()
            except ValueError:
                body = {"raw": resp.text}

            # Success: 2xx and no error envelope
            if resp.ok and not (isinstance(body, dict) and "error" in body):
                return body

            err = from_response(resp.status_code, body if isinstance(body, dict) else {})
            if err.code in RETRYABLE_CODES and attempt < self.retries:
                time.sleep(self._backoff(attempt))
                continue
            raise err

        raise GraphError(f"retry budget exhausted: {last_network_exc}")

    def _backoff(self, attempt: int) -> float:
        base: float = 0.5 * (2 ** attempt)
        return float(base + random.uniform(0, base * 0.5))

    # ----- Verbs ---------------------------------------------------------

    def get(self, path: str, **params: Any) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, **fields: Any) -> Any:
        return self.request("POST", path, data=fields)

    def delete(self, path: str, **params: Any) -> Any:
        return self.request("DELETE", path, params=params)

    # ----- Pagination ----------------------------------------------------

    def paginate(self, path: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Yield every item from `data` across all pages, following `paging.next`.

        Auto-stops when `paging.next` is missing.
        """
        next_url: str | None = None
        page = self.get(path, **params)
        while True:
            yield from page.get("data") or []
            next_url = (page.get("paging") or {}).get("next")
            if not next_url:
                return
            # Meta returns absolute URLs in `paging.next`; access_token already in query
            resp = self.session.get(next_url, timeout=self.timeout)
            try:
                page = resp.json()
            except ValueError:
                page = {}
            if isinstance(page, dict) and "error" in page:
                raise from_response(resp.status_code, page)

    # ----- Batch ---------------------------------------------------------

    def batch(self, batch_requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Run a batched request. See /docs/graph-api/batch-requests.

        Each entry is a dict like {"method": "GET", "relative_url": "me?fields=id,name"}.
        Returns the list of per-request response envelopes.
        """
        body = {
            "access_token": self.token,
            "batch": json.dumps(batch_requests),
            **{k: v for k, v in self._auth_extras().items() if k != "access_token"},
        }
        resp = self.session.post(
            f"{self.base}/{self.version}",
            data=body,
            timeout=self.timeout,
        )
        try:
            out = resp.json()
        except ValueError:
            out = {"raw": resp.text}
        if isinstance(out, dict) and "error" in out:
            raise from_response(resp.status_code, out)
        return out if isinstance(out, list) else []

    # ----- Convenience used by IG commands -------------------------------

    def list_pages_with_ig(self) -> list[dict[str, Any]]:
        """List Pages the token can manage, including their linked IG account id when present."""
        return list(
            self.paginate(
                "/me/accounts",
                fields="id,name,access_token,instagram_business_account",
            )
        )
