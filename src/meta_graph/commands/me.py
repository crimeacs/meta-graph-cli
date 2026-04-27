"""`meta me` — quick profile + Pages helpers."""
from __future__ import annotations

import click

from meta_graph._runtime import build_client, global_options, handle_graph_error, stash_globals
from meta_graph.errors import GraphError
from meta_graph.output import emit


@click.group(invoke_without_command=True)
@global_options
@click.pass_context
def me(ctx: click.Context, **gflags: object) -> None:
    """Get the user/page tied to the current token, or list its sub-resources."""
    stash_globals(ctx, **gflags)
    if ctx.invoked_subcommand is not None:
        return
    client = build_client(ctx.obj)
    try:
        result = client.get("/me")
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@me.command("pages")
@click.option("--fields", default="id,name,access_token,instagram_business_account",
              show_default=True, help="Page fields to fetch.")
@click.pass_context
def pages(ctx: click.Context, fields: str) -> None:
    """List the Pages this token can manage (and their linked IG accounts)."""
    client = build_client(ctx.obj)
    try:
        result = list(client.paginate("/me/accounts", fields=fields))
    except GraphError as e:
        handle_graph_error(e)
        return
    emit({"data": result, "count": len(result)},
         pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@me.command("permissions")
@click.pass_context
def permissions(ctx: click.Context) -> None:
    """Show granted/declined permissions for the current token."""
    client = build_client(ctx.obj)
    try:
        result = client.get("/me/permissions")
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


def register(group: click.Group) -> None:
    group.add_command(me)
