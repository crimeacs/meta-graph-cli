"""Config-file resolution.

Looks at $XDG_CONFIG_HOME/meta-graph/config.toml (default: ~/.config/meta-graph/config.toml).

Format:

    [default]
    token = "EAA..."
    api_version = "v22.0"
    app_secret = "..."

    [profile.prod]
    token = "EAA..."
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "meta-graph" / "config.toml"


@dataclass
class Profile:
    token: str | None = None
    api_version: str | None = None
    app_secret: str | None = None
    timeout: int | None = None
    retries: int | None = None


def load_profile(name: str = "default") -> Profile:
    """Load `[default]` (when name=="default") or `[profile.<name>]`. Empty if file missing."""
    path = config_path()
    if not path.exists():
        return Profile()
    with path.open("rb") as f:
        data = tomllib.load(f)
    block: dict[str, Any]
    if name == "default":
        block = data.get("default") or {}
    else:
        block = (data.get("profile") or {}).get(name) or {}
    return Profile(
        token=block.get("token"),
        api_version=block.get("api_version"),
        app_secret=block.get("app_secret"),
        timeout=block.get("timeout"),
        retries=block.get("retries"),
    )
