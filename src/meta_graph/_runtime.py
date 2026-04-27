"""Shared CLI runtime helpers used by every subcommand module.

Lives outside cli.py to break the import cycle (cli imports commands; commands
import these helpers).
"""
from __future__ import annotations

import sys
from typing import Any

import click

from meta_graph.auth import AuthMissingError, Settings, resolve
from meta_graph.client import GraphClient
from meta_graph.errors import AuthError, GraphError
from meta_graph.output import emit_error


def global_options(f: Any) -> Any:
    """Decorator: attach the cross-cutting flags to a click command."""
    f = click.option("--token", envvar="META_GRAPH_TOKEN", default=None,
                     help="Access token. Falls back to $META_GRAPH_TOKEN, then config.")(f)
    f = click.option("--profile", default="default", show_default=True,
                     help="Config profile (block in ~/.config/meta-graph/config.toml).")(f)
    f = click.option("--api-version", default=None,
                     help="Graph API version, e.g. v22.0. Default: built-in.")(f)
    f = click.option("--app-secret", default=None, envvar="META_GRAPH_APP_SECRET",
                     help="App secret. Enables appsecret_proof signing.")(f)
    f = click.option("--timeout", type=int, default=None, help="HTTP timeout in seconds.")(f)
    f = click.option("--retries", type=int, default=None,
                     help="Retry budget for transient errors.")(f)
    f = click.option("--base", default=None, envvar="META_GRAPH_BASE",
                     help="Override API host. Default auto-detects from token: "
                          "IGAA*/IGQW* → graph.instagram.com, else graph.facebook.com.")(f)
    f = click.option("--pretty", is_flag=True,
                     help="Indent JSON; color when stdout is a TTY.")(f)
    f = click.option("--jq", default=None, metavar="EXPR",
                     help="Pipe output through jq (or a tiny path resolver if jq is missing).")(f)
    return f


def stash_globals(ctx: click.Context, **kwargs: Any) -> dict[str, Any]:
    """Capture global flags into ctx.obj so subcommands can read them."""
    ctx.ensure_object(dict)
    obj: dict[str, Any] = ctx.obj
    obj.update(kwargs)
    return obj


def build_client(ctx_obj: dict[str, Any]) -> GraphClient:
    """Resolve settings from ctx_obj and return a configured GraphClient.

    Exits with code 3 when no token is available.
    """
    try:
        s: Settings = resolve(
            cli_token=ctx_obj.get("token"),
            cli_api_version=ctx_obj.get("api_version"),
            cli_app_secret=ctx_obj.get("app_secret"),
            cli_timeout=ctx_obj.get("timeout"),
            cli_retries=ctx_obj.get("retries"),
            cli_base=ctx_obj.get("base"),
            profile=ctx_obj.get("profile") or "default",
        )
    except AuthMissingError as e:
        click.echo(f"meta: {e}", err=True)
        sys.exit(3)
    return GraphClient(
        token=s.token,
        version=s.api_version,
        app_secret=s.app_secret,
        timeout=s.timeout,
        retries=s.retries,
        base=s.base,
    )


def handle_graph_error(err: Exception) -> None:
    """Emit the error to stderr and exit with the right code."""
    emit_error(err)
    if isinstance(err, AuthError):
        sys.exit(3)
    if isinstance(err, GraphError):
        sys.exit(1)
    sys.exit(2)
