"""CLI entry point. Wires together global options + subcommand groups."""
from __future__ import annotations

import click

from meta_graph.version import __version__


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="meta")
def main() -> None:
    """`meta` — a command-line client for Meta's Graph API and Instagram Graph API.

    \b
    Examples
      meta get /me fields=id,name,email
      meta me pages
      meta ig accounts
      meta ig publish IG_ID --image-url https://... --caption "Hello"
      meta ig insights IG_ID --metric impressions,reach --period day
      meta nodes
      meta token info
    """


# Subcommand registration. Each commands/* module exposes register(group).
from meta_graph.commands import discovery, generic, ig, me, token  # noqa: E402

generic.register(main)
me.register(main)
token.register(main)
discovery.register(main)
ig.register(main)
