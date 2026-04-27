"""Output emitters: JSON (default), --pretty (rich), --jq (passthrough)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import Any


def emit(value: Any, *, pretty: bool = False, jq: str | None = None) -> None:
    """Write `value` to stdout in the requested format.

    Default: compact JSON (jq-friendly).
    --pretty: indented JSON, colored if stdout is a TTY (via rich).
    --jq: pipe through `jq` if installed; falls back to a tiny path resolver.
    """
    text = json.dumps(value, indent=None, default=_default)

    if jq:
        text = _apply_jq(text, jq)
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return

    if pretty:
        if sys.stdout.isatty():
            try:
                from rich.console import Console
                from rich.json import JSON

                Console().print(JSON(text))
                return
            except ImportError:  # pragma: no cover
                pass
        sys.stdout.write(json.dumps(value, indent=2, default=_default) + "\n")
        return

    sys.stdout.write(text + "\n")


def emit_error(err: Exception) -> None:
    """Write an error to stderr as JSON so scripts can still parse it."""
    payload = {
        "error": {
            "type": err.__class__.__name__,
            "message": str(err),
        }
    }
    for attr in ("code", "subcode", "fbtrace_id", "http_status"):
        v = getattr(err, attr, None)
        if v is not None:
            payload["error"][attr] = v
    body = getattr(err, "body", None)
    if body:
        payload["error"]["body"] = body
    sys.stderr.write(json.dumps(payload, indent=2, default=_default) + "\n")


def _apply_jq(text: str, expr: str) -> str:
    if shutil.which("jq"):
        try:
            res = subprocess.run(
                ["jq", expr],
                input=text,
                text=True,
                capture_output=True,
                check=True,
            )
            return res.stdout
        except subprocess.CalledProcessError as e:
            sys.stderr.write(e.stderr)
            sys.exit(1)

    # Fallback: support tiny `.path.to.field` expressions only.
    obj = json.loads(text)
    return json.dumps(_jq_lite(obj, expr), default=_default) + "\n"


def _jq_lite(obj: Any, expr: str) -> Any:
    expr = expr.strip().lstrip(".")
    if not expr:
        return obj
    cur = obj
    for part in expr.split("."):
        if not part:
            continue
        if "[" in part:
            key, idx = part.split("[", 1)
            idx = idx.rstrip("]")
            if key:
                cur = cur[key]
            cur = cur[int(idx)]
        else:
            cur = cur[part]
    return cur


def _default(o: Any) -> Any:
    if hasattr(o, "isoformat"):
        return o.isoformat()
    return str(o)
