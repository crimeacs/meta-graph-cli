"""Parse docs/reference.md and emit src/meta_graph/data/{nodes,edges,fields}.json.

Run after a fresh scrape (scrape.py + concat.py) to refresh what `meta nodes`,
`meta edges <node>`, and `meta fields <node>` return.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REF = REPO / "docs" / "reference.md"
OUT = REPO / "src" / "meta_graph" / "data"

# TOC lines under "### Reference" sections look like:
#   - [Page](#docs__graph-api__reference__page)
#     - [`/feed`](#docs__graph-api__reference__page__feed)
NODE_RE = re.compile(
    r"^- \[([^\]]+)\]\(#docs__(?:graph-api|instagram-api)__reference__([a-z0-9_\-]+)\)\s*$",
    re.MULTILINE,
)
EDGE_RE = re.compile(
    r"^  - \[`/([a-z0-9_\-]+)`\]\(#docs__(?:graph-api|instagram-api)__reference__"
    r"([a-z0-9_\-]+)__([a-z0-9_\-]+)\)\s*$",
    re.MULTILINE,
)
# Heuristic for fields: lines under a node's <a id="..."></a> anchor that look like:
#   `field_name` — description    OR    `field_name` `<type>` ...
FIELDS_HINT = re.compile(r"^[\*\-]\s*`([a-z][a-z0-9_]*)`", re.MULTILINE)


def main() -> None:
    text = REF.read_text()

    nodes: list[str] = []
    for m in NODE_RE.finditer(text):
        nodes.append(m.group(2))
    nodes = sorted(set(nodes))

    edges: dict[str, list[str]] = defaultdict(list)
    for m in EDGE_RE.finditer(text):
        edges[m.group(2)].append(m.group(1))
    edges_clean = {k: sorted(set(v)) for k, v in sorted(edges.items())}

    # Field extraction: scan each node's section between its <a id> anchor and the next
    # <a id> at the same level. Pull the list of `backtick` tokens that look like fields.
    fields: dict[str, list[str]] = {}
    anchor_re = re.compile(r'<a id="docs__(?:graph-api|instagram-api)__reference__([a-z0-9_\-]+)">')
    matches = list(anchor_re.finditer(text))
    for i, m in enumerate(matches):
        node = m.group(1)
        if "__" in node:  # this is an edge anchor; skip
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end]
        # Stop at the first "## Edges of" so we don't bleed into edge content
        edge_idx = chunk.find("## Edges of")
        if edge_idx >= 0:
            chunk = chunk[:edge_idx]
        found = sorted(set(FIELDS_HINT.findall(chunk)))
        # Drop generic noise tokens
        noise = {"id", "and", "or", "the", "a", "true", "false", "data", "error",
                 "yes", "no", "default", "type", "method", "fields", "limit", "since",
                 "until", "after", "before", "name", "value", "code"}
        found = [f for f in found if f not in noise and len(f) > 1]
        if found:
            fields[node] = found

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "nodes.json").write_text(json.dumps(nodes, indent=2))
    (OUT / "edges.json").write_text(json.dumps(edges_clean, indent=2))
    (OUT / "fields.json").write_text(json.dumps(fields, indent=2))

    print(f"nodes:  {len(nodes)}")
    print(f"edges:  {sum(len(v) for v in edges_clean.values())} across {len(edges_clean)} nodes")
    print(f"fields: {sum(len(v) for v in fields.values())} across {len(fields)} nodes")


if __name__ == "__main__":
    main()
