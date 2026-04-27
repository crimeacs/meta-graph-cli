"""CLI parsing tests via click.testing.CliRunner — no network."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from meta_graph.cli import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_help_shows_subcommands(runner: CliRunner) -> None:
    res = runner.invoke(main, ["--help"])
    assert res.exit_code == 0
    # core verbs
    for sub in ("get", "post", "delete", "batch", "me", "ig", "token", "nodes", "edges", "fields"):
        assert sub in res.output


def test_version(runner: CliRunner) -> None:
    res = runner.invoke(main, ["--version"])
    assert res.exit_code == 0
    assert "0.1.0" in res.output


def test_no_token_exits_3(runner: CliRunner) -> None:
    # No env, no config, no flag → must exit 3
    with patch.dict("os.environ", {}, clear=False):
        # ensure HOME points somewhere without a config
        with patch.dict("os.environ", {"META_GRAPH_TOKEN": "", "XDG_CONFIG_HOME": "/nonexistent"}):
            res = runner.invoke(main, ["get", "/me"])
    assert res.exit_code == 3
    assert "no access token" in res.output.lower() or "no access token" in (res.stderr_bytes or b"").decode()


def test_get_kv_parsing(runner: CliRunner) -> None:
    """Confirm key=value parsing surfaces a useful error on bad input."""
    res = runner.invoke(main, ["get", "/me", "badnoeq", "--token", "fake"])
    assert res.exit_code != 0
    assert "key=value" in res.output or "key=value" in (res.stderr_bytes or b"").decode()


def test_nodes_offline(runner: CliRunner) -> None:
    res = runner.invoke(main, ["nodes"])
    assert res.exit_code == 0
    assert "user" in res.output  # "user" is a known node


def test_edges_offline(runner: CliRunner) -> None:
    res = runner.invoke(main, ["edges", "ig-user"])
    assert res.exit_code == 0
    assert "media" in res.output
    assert "stories" in res.output


def test_edges_unknown_node(runner: CliRunner) -> None:
    res = runner.invoke(main, ["edges", "no-such-node"])
    assert res.exit_code == 0  # we exit 0 with a helpful stderr; that's deliberate
    assert "no edges known" in (res.stderr_bytes or b"").decode() or "no edges known" in res.output


def test_ig_subcommands_listed(runner: CliRunner) -> None:
    res = runner.invoke(main, ["ig", "--help"])
    assert res.exit_code == 0
    for sub in (
        "accounts", "user", "media", "publish", "publish-status",
        "comment", "comment-on", "hashtag", "business-discovery", "oembed",
    ):
        assert sub in res.output


def test_publish_requires_one_source(runner: CliRunner) -> None:
    """`meta ig publish` without any source flag should fail with usage error."""
    res = runner.invoke(main, ["ig", "publish", "IG_ID", "--token", "fake", "--no-wait"])
    # UsageError → exit 2 (click's default for usage error)
    assert res.exit_code != 0


def test_batch_invalid_json(runner: CliRunner) -> None:
    res = runner.invoke(main, ["batch", "--token", "fake"], input="not json")
    assert res.exit_code == 2
    assert "invalid JSON" in res.output or "invalid JSON" in (res.stderr_bytes or b"").decode()


def test_batch_must_be_list(runner: CliRunner) -> None:
    res = runner.invoke(main, ["batch", "--token", "fake"], input=json.dumps({"not": "a list"}))
    assert res.exit_code == 2
