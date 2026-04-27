"""Build docs/reference.md by concatenating per-page markdown from scripts/_pages/.

Five sections in order:
  1. Graph API guides
  2. Graph API reference (nodes + their edges)
  3. Instagram Platform guides (newest IG docs tree)
  4. Instagram Graph API how-to guides (older tree, more depth)
  5. Instagram Graph API reference (nodes + their edges)
"""
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAGES_DIR = REPO / "scripts" / "_pages"
OUT = REPO / "docs" / "reference.md"

GRAPH_GUIDE_ORDER = [
    "/docs/graph-api/overview",
    "/docs/graph-api/get-started",
    "/docs/graph-api/results",
    "/docs/graph-api/guides/versioning",
    "/docs/graph-api/guides/field-expansion",
    "/docs/graph-api/batch-requests",
    "/docs/graph-api/guides/secure-requests",
    "/docs/graph-api/guides/error-handling",
    "/docs/graph-api/guides/debugging",
    "/docs/graph-api/guides/upload",
    "/docs/graph-api/webhooks",
    "/docs/graph-api/changelog",
]
IG_PLATFORM_GUIDE_ORDER = [
    "/docs/instagram-platform/overview",
    "/docs/instagram-platform/create-an-instagram-app",
    "/docs/instagram-platform/instagram-api-with-instagram-login",
    "/docs/instagram-platform/instagram-api-with-facebook-login",
    "/docs/instagram-platform/content-publishing",
    "/docs/instagram-platform/sharing-to-feed",
    "/docs/instagram-platform/sharing-to-stories",
    "/docs/instagram-platform/insights",
    "/docs/instagram-platform/comment-moderation",
    "/docs/instagram-platform/private-replies",
    "/docs/instagram-platform/self-messaging",
    "/docs/instagram-platform/oembed",
    "/docs/instagram-platform/embed-button",
    "/docs/instagram-platform/webhooks",
    "/docs/instagram-platform/app-review",
    "/docs/instagram-platform/changelog",
    "/docs/instagram-platform/support",
]
IG_API_GUIDE_ORDER = [
    "/docs/instagram-api/guides/business-discovery",
    "/docs/instagram-api/guides/comment-moderation",
    "/docs/instagram-api/guides/content-publishing",
    "/docs/instagram-api/guides/hashtag-search",
    "/docs/instagram-api/guides/insights",
    "/docs/instagram-api/guides/mentions",
]


def slug(path: str) -> str:
    return path.strip("/").replace("/", "__")


def anchor(path: str) -> str:
    return slug(path).lower()


def title_from(path: str) -> str:
    leaf = path.rstrip("/").rsplit("/", 1)[-1]
    return leaf.replace("-", " ").replace("_", " ").title() or path


def slurp(path: str) -> str | None:
    p = PAGES_DIR / (slug(path) + ".md")
    return p.read_text() if p.exists() else None


def all_pages() -> list[str]:
    """Reverse-engineer the URL from each cached file in _pages/."""
    out = []
    for f in PAGES_DIR.iterdir():
        if not f.name.endswith(".md"):
            continue
        first = f.read_text().splitlines()[0]
        if first.startswith("<!-- source:"):
            url = first.split(": ", 1)[1].rsplit(" ", 1)[0]
            path = url.replace("https://developers.facebook.com", "")
            out.append(path)
    return sorted(out)


def render_node_with_edges(out, u: str, edges_by_node: dict[str, list[str]]) -> None:
    body = slurp(u)
    if not body:
        return
    out.write(f'<a id="{anchor(u)}"></a>\n\n{body.rstrip()}\n\n')
    node = u.rsplit("/", 1)[-1]
    edges = [e for e in edges_by_node.get(node, []) if slurp(e)]
    if edges:
        out.write(f"\n## Edges of `{node}`\n\n")
        for e in edges:
            edge_name = e.rsplit("/", 1)[-1]
            out.write(f'<a id="{anchor(e)}"></a>\n\n### `/{node}/{edge_name}`\n\n')
            out.write(slurp(e).rstrip() + "\n\n")
    out.write("---\n\n")


def main() -> None:
    pages = all_pages()
    by = lambda pred: [p for p in pages if pred(p)]

    graph_guides = [u for u in GRAPH_GUIDE_ORDER if u in pages]
    graph_refs = sorted(by(lambda p: p.startswith("/docs/graph-api/reference/")))
    graph_nodes = [p for p in graph_refs if p.count("/") == 4]
    graph_edges = [p for p in graph_refs if p.count("/") == 5]

    ig_platform = [u for u in IG_PLATFORM_GUIDE_ORDER if u in pages]
    ig_api_guides = [u for u in IG_API_GUIDE_ORDER if u in pages]
    ig_refs = sorted(by(lambda p: p.startswith("/docs/instagram-api/reference/")))
    ig_nodes = [p for p in ig_refs if p.count("/") == 4]
    ig_edges = [p for p in ig_refs if p.count("/") == 5]

    edges_by_node: dict[str, list[str]] = {}
    for e in graph_edges + ig_edges:
        parts = e.split("/")
        edges_by_node.setdefault(parts[4], []).append(e)
    for k in edges_by_node:
        edges_by_node[k].sort()

    now = datetime.datetime.now().strftime("%Y-%m-%d")

    with OUT.open("w") as out:
        out.write(f"""# Meta Graph API + Instagram — Documentation Reference

> Crawled from <https://developers.facebook.com/docs/> on {now}.
> Source-of-truth for the [`meta-graph` Python CLI](https://github.com/crimeacs/meta-graph-cli).
> Each section preserves its original source URL in an HTML comment.

Contents:

- {len(graph_guides)} Graph API guide pages
- {len(graph_nodes)} Graph API reference node pages
- {len(graph_edges)} Graph API edge sub-pages
- {len(ig_platform)} Instagram Platform guides (latest tree — **start here for IG**)
- {len(ig_api_guides)} Instagram Graph API how-to guides
- {len(ig_nodes)} Instagram Graph API reference nodes
- {len(ig_edges)} Instagram Graph API edge sub-pages

---

## Table of contents

### Graph API · Guides
""")
        for u in graph_guides:
            out.write(f"- [{title_from(u)}](#{anchor(u)})\n")

        out.write("\n### Graph API · Reference\n")
        for n in graph_nodes:
            node = n.rsplit("/", 1)[-1]
            out.write(f"- [{title_from(n)}](#{anchor(n)})\n")
            for e in edges_by_node.get(node, []):
                if slurp(e):
                    out.write(f"  - [`/{e.rsplit('/', 1)[-1]}`](#{anchor(e)})\n")

        out.write("\n### Instagram Platform · Guides\n")
        for u in ig_platform:
            out.write(f"- [{title_from(u)}](#{anchor(u)})\n")

        out.write("\n### Instagram Graph API · How-to\n")
        for u in ig_api_guides:
            out.write(f"- [{title_from(u)}](#{anchor(u)})\n")

        out.write("\n### Instagram Graph API · Reference\n")
        for n in ig_nodes:
            node = n.rsplit("/", 1)[-1]
            out.write(f"- [{title_from(n)}](#{anchor(n)})\n")
            for e in edges_by_node.get(node, []):
                if slurp(e):
                    out.write(f"  - [`/{e.rsplit('/', 1)[-1]}`](#{anchor(e)})\n")

        out.write("\n---\n\n# Graph API — Guides\n\n")
        for u in graph_guides:
            body = slurp(u)
            if body:
                out.write(f'<a id="{anchor(u)}"></a>\n\n{body.rstrip()}\n\n---\n\n')

        out.write("# Graph API — Reference\n\n")
        for u in graph_nodes:
            render_node_with_edges(out, u, edges_by_node)

        out.write("# Instagram Platform — Guides\n\n")
        for u in ig_platform:
            body = slurp(u)
            if body:
                out.write(f'<a id="{anchor(u)}"></a>\n\n{body.rstrip()}\n\n---\n\n')

        out.write("# Instagram Graph API — How-to\n\n")
        for u in ig_api_guides:
            body = slurp(u)
            if body:
                out.write(f'<a id="{anchor(u)}"></a>\n\n{body.rstrip()}\n\n---\n\n')

        out.write("# Instagram Graph API — Reference\n\n")
        for u in ig_nodes:
            render_node_with_edges(out, u, edges_by_node)

    print(f"wrote {OUT}, size:", OUT.stat().st_size)


if __name__ == "__main__":
    main()
