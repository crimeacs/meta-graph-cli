"""Fetch Graph API doc pages, extract the content pagelet, write per-page markdown.

Reads urls.txt (one path per line under /docs/...). Writes markdown to _pages/.
Concurrent (8 workers, 45s timeout). Cached: pages with >200 bytes are skipped.
"""
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import html2text
from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
PAGES_DIR = REPO / "scripts" / "_pages"
URLS_FILE = REPO / "scripts" / "urls.txt"

BASE = "https://developers.facebook.com"
HDR = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    )
}


def make_h2t() -> html2text.HTML2Text:
    h = html2text.HTML2Text()
    h.body_width = 0
    h.ignore_images = False
    h.protect_links = True
    h.unicode_snob = True
    return h


def slug(path: str) -> str:
    return path.strip("/").replace("/", "__")


def fetch_one(path: str) -> tuple[str, str, int]:
    out_md = PAGES_DIR / (slug(path) + ".md")
    if out_md.exists() and out_md.stat().st_size > 200:
        return path, "cached", out_md.stat().st_size

    url = BASE + path
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return path, f"FETCH_ERR: {e}", 0

    soup = BeautifulSoup(html, "html.parser")
    pagelet = soup.find(id="documentation_body_pagelet")
    if not pagelet:
        pagelet = soup.find("article") or soup.find("main") or soup.body
    if not pagelet:
        return path, "NO_CONTENT", 0

    for d in pagelet.find_all(class_=["_li", "_660z", "_3u39"]):
        d.attrs = {}
    for a in pagelet.find_all("a", href=True):
        if a["href"].startswith("/"):
            a["href"] = BASE + a["href"]

    try:
        md = make_h2t().handle(str(pagelet))
    except Exception as e:
        return path, f"PARSE_ERR: {type(e).__name__}: {e}", 0

    lines = [ln.rstrip() for ln in md.splitlines()]
    out, blank = [], 0
    for ln in lines:
        if ln == "":
            blank += 1
            if blank > 2:
                continue
        else:
            blank = 0
        out.append(ln)
    md = "\n".join(out).strip() + "\n"

    out_md.write_text(f"<!-- source: {url} -->\n\n{md}")
    return path, "ok", out_md.stat().st_size


def main() -> None:
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    urls = [u.strip() for u in URLS_FILE.read_text().splitlines() if u.strip()]
    print(f"fetching {len(urls)} pages with 8 workers")

    results: list[tuple[str, str, int]] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_one, u): u for u in urls}
        for i, fut in enumerate(as_completed(futs), 1):
            path, status, size = fut.result()
            results.append((path, status, size))
            marker = "OK " if status in ("ok", "cached") else "!! "
            print(f"  [{i:3d}/{len(urls)}] {marker}{status:>10} {size:>7}b  {path}")

    ok = sum(1 for _, s, _ in results if s in ("ok", "cached"))
    print(f"\ndone: {ok}/{len(urls)} ok")

    (REPO / "scripts" / "manifest.txt").write_text(
        "".join(f"{s:>12}  {sz:>8}  {p}\n" for p, s, sz in sorted(results))
    )


if __name__ == "__main__":
    main()
