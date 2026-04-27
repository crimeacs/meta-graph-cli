"""`meta token` — token introspection and exchange helpers.

Note: `info` and `debug` use /debug_token which requires either an app
access token or a user token whose app_id matches the inspected token.
The simplest pattern: provide --app-id and --app-secret (the app's
"access token" is `<app_id>|<app_secret>`).
"""
from __future__ import annotations

import click

from meta_graph._runtime import build_client, global_options, handle_graph_error, stash_globals
from meta_graph.errors import GraphError
from meta_graph.output import emit


def _app_token(app_id: str, app_secret: str) -> str:
    return f"{app_id}|{app_secret}"


@click.group()
@global_options
@click.pass_context
def token(ctx: click.Context, **gflags: object) -> None:
    """Introspect, debug, and refresh access tokens."""
    stash_globals(ctx, **gflags)


@token.command("info")
@click.option("--app-id", required=False, envvar="META_GRAPH_APP_ID",
              help="Your app id. Required for the underlying /debug_token call.")
@click.option("--app-secret", required=False, envvar="META_GRAPH_APP_SECRET",
              help="Your app secret. Used to build the app access token for /debug_token.")
@click.pass_context
def info(ctx: click.Context, app_id: str | None, app_secret: str | None) -> None:
    """Decode the current token: scopes, expiry, app, user."""
    client = build_client(ctx.obj)
    inspector_token = (
        _app_token(app_id, app_secret) if (app_id and app_secret) else client.token
    )
    try:
        result = client.get(
            "/debug_token",
            input_token=client.token,
            access_token=inspector_token,
        )
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@token.command("debug")
@click.argument("input_token")
@click.option("--app-id", required=False, envvar="META_GRAPH_APP_ID",
              help="Your app id (used to build the inspector token).")
@click.option("--app-secret", required=False, envvar="META_GRAPH_APP_SECRET",
              help="Your app secret.")
@click.pass_context
def debug(ctx: click.Context, input_token: str, app_id: str | None, app_secret: str | None) -> None:
    """Decode an arbitrary access token via /debug_token."""
    client = build_client(ctx.obj)
    inspector_token = (
        _app_token(app_id, app_secret) if (app_id and app_secret) else client.token
    )
    try:
        result = client.get(
            "/debug_token",
            input_token=input_token,
            access_token=inspector_token,
        )
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@token.command("refresh")
@click.option("--app-id", required=True, envvar="META_GRAPH_APP_ID")
@click.option("--app-secret", required=True, envvar="META_GRAPH_APP_SECRET")
@click.pass_context
def refresh(ctx: click.Context, app_id: str, app_secret: str) -> None:
    """Exchange a short-lived user token for a long-lived (~60-day) one.

    See https://developers.facebook.com/docs/facebook-login/access-tokens#extending
    """
    client = build_client(ctx.obj)
    try:
        result = client.get(
            "/oauth/access_token",
            grant_type="fb_exchange_token",
            client_id=app_id,
            client_secret=app_secret,
            fb_exchange_token=client.token,
        )
    except GraphError as e:
        handle_graph_error(e)
        return
    if isinstance(result, dict) and "access_token" in result:
        click.echo(
            "# write this into ~/.config/meta-graph/config.toml under [default] token = ...",
            err=True,
        )
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


def register(group: click.Group) -> None:
    group.add_command(token)
