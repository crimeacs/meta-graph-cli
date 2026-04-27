"""Generic verbs: get / post / delete / batch."""
from __future__ import annotations

import json
import sys

import click

from meta_graph._runtime import build_client, global_options, handle_graph_error, stash_globals
from meta_graph.errors import GraphError
from meta_graph.output import emit


def _parse_kv(items: tuple[str, ...]) -> dict[str, str]:
    """key=value strings → dict."""
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise click.BadParameter(f"expected key=value, got {item!r}")
        k, v = item.split("=", 1)
        out[k] = v
    return out


@click.command()
@click.argument("path")
@click.argument("kv", nargs=-1)
@global_options
@click.pass_context
def get(ctx: click.Context, path: str, kv: tuple[str, ...], **gflags: object) -> None:
    """GET /<path> with optional query params as key=value pairs.

    \b
    Examples
      meta get /me fields=id,name,email
      meta get /PAGE_ID/feed fields=id,message limit=50
      meta get /search q=python type=user
    """
    stash_globals(ctx, **gflags)
    client = build_client(ctx.obj)
    try:
        result = client.get(path, **_parse_kv(kv))
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@click.command()
@click.argument("path")
@click.argument("kv", nargs=-1)
@global_options
@click.pass_context
def post(ctx: click.Context, path: str, kv: tuple[str, ...], **gflags: object) -> None:
    """POST /<path> with body fields as key=value pairs.

    \b
    Examples
      meta post /PAGE_ID/feed message='Hello world'
      meta post /PAGE_ID/photos url=https://example.com/img.png caption='Caption'
    """
    stash_globals(ctx, **gflags)
    client = build_client(ctx.obj)
    try:
        result = client.post(path, **_parse_kv(kv))
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@click.command()
@click.argument("path")
@click.argument("kv", nargs=-1)
@global_options
@click.pass_context
def delete(ctx: click.Context, path: str, kv: tuple[str, ...], **gflags: object) -> None:
    """DELETE /<path>."""
    stash_globals(ctx, **gflags)
    client = build_client(ctx.obj)
    try:
        result = client.delete(path, **_parse_kv(kv))
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@click.command()
@click.option("--file", "file_", type=click.Path(exists=True, dir_okay=False),
              default=None, help="Read batch JSON from this file (default: stdin).")
@global_options
@click.pass_context
def batch(ctx: click.Context, file_: str | None, **gflags: object) -> None:
    """Run a batched request.

    Reads a JSON array of {"method": "...", "relative_url": "..."} entries
    from --file or stdin.

    \b
    Example
      echo '[{"method":"GET","relative_url":"me"},
             {"method":"GET","relative_url":"me/accounts?limit=2"}]' | meta batch
    """
    stash_globals(ctx, **gflags)
    raw = open(file_).read() if file_ else sys.stdin.read()
    try:
        requests_ = json.loads(raw)
    except json.JSONDecodeError as e:
        click.echo(f"meta batch: invalid JSON: {e}", err=True)
        sys.exit(2)
    if not isinstance(requests_, list):
        click.echo("meta batch: input must be a JSON array of request objects", err=True)
        sys.exit(2)

    client = build_client(ctx.obj)
    try:
        result = client.batch(requests_)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


def register(group: click.Group) -> None:
    group.add_command(get)
    group.add_command(post)
    group.add_command(delete)
    group.add_command(batch)
