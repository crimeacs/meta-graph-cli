"""Token + settings resolution.

Order of precedence (first hit wins):
  1. Explicit flag value (--token, --api-version, --app-secret)
  2. Environment variable (META_GRAPH_TOKEN, META_GRAPH_API_VERSION, META_GRAPH_APP_SECRET)
  3. Config file profile (~/.config/meta-graph/config.toml)
  4. Built-in default (api_version only)
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from meta_graph.config import load_profile
from meta_graph.version import DEFAULT_API_VERSION


@dataclass
class Settings:
    token: str
    api_version: str
    app_secret: str | None
    timeout: int
    retries: int
    profile: str
    base: str | None


class AuthMissingError(Exception):
    """Raised when no token can be resolved from any source."""


def resolve(
    *,
    cli_token: str | None = None,
    cli_api_version: str | None = None,
    cli_app_secret: str | None = None,
    cli_timeout: int | None = None,
    cli_retries: int | None = None,
    cli_base: str | None = None,
    profile: str = "default",
) -> Settings:
    p = load_profile(profile)

    token = cli_token or os.environ.get("META_GRAPH_TOKEN") or p.token
    if not token:
        raise AuthMissingError(
            "no access token found. Pass --token, set META_GRAPH_TOKEN, or write one to "
            f"the [{profile}] block of ~/.config/meta-graph/config.toml. Get a token from "
            "https://developers.facebook.com/tools/explorer/"
        )

    api_version = (
        cli_api_version
        or os.environ.get("META_GRAPH_API_VERSION")
        or p.api_version
        or DEFAULT_API_VERSION
    )

    app_secret = cli_app_secret or os.environ.get("META_GRAPH_APP_SECRET") or p.app_secret

    timeout = cli_timeout or _int_env("META_GRAPH_TIMEOUT") or p.timeout or 30
    env_retries = _int_env("META_GRAPH_RETRIES")
    if cli_retries is not None:
        retries: int = cli_retries
    elif env_retries is not None:
        retries = env_retries
    elif p.retries is not None:
        retries = p.retries
    else:
        retries = 3

    base = cli_base or os.environ.get("META_GRAPH_BASE") or p.base

    return Settings(
        token=token,
        api_version=api_version,
        app_secret=app_secret,
        timeout=int(timeout),
        retries=retries,
        profile=profile,
        base=base,
    )


def _int_env(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
