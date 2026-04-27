"""`meta nodes / edges / fields` — offline discovery from embedded docs data.

Reads src/meta_graph/data/*.json built from docs/reference.md by
scripts/build_data.py. The data is shipped with the wheel.
"""
from __future__ import annotations

import json
from importlib import resources
from typing import Any

import click


def _load(name: str) -> Any:
    pkg = "meta_graph.data"
    try:
        text = resources.files(pkg).joinpath(f"{name}.json").read_text()
    except FileNotFoundError:
        return {}
    return json.loads(text)


@click.command("nodes")
def nodes() -> None:
    """List all known Graph API + Instagram nodes."""
    data = _load("nodes")
    if isinstance(data, list):
        for n in data:
            click.echo(n)
    else:
        for k in sorted(data):
            click.echo(k)


@click.command("edges")
@click.argument("node")
def edges(node: str) -> None:
    """List the edges of a node."""
    data = _load("edges")
    if not isinstance(data, dict):
        click.echo("(no data)", err=True)
        return
    items = data.get(node) or data.get(node.replace("-", "_")) or []
    if not items:
        click.echo(f"no edges known for {node!r}; try `meta nodes`", err=True)
        return
    for e in items:
        click.echo(e)


@click.command("fields")
@click.argument("node")
def fields(node: str) -> None:
    """List the documented fields of a node (best-effort, parsed from reference.md)."""
    data = _load("fields")
    if not isinstance(data, dict):
        click.echo("(no data)", err=True)
        return
    items = data.get(node) or data.get(node.replace("-", "_")) or []
    if not items:
        click.echo(f"no fields known for {node!r}; try `meta nodes`", err=True)
        return
    for f in items:
        click.echo(f)


def register(group: click.Group) -> None:
    group.add_command(nodes)
    group.add_command(edges)
    group.add_command(fields)
