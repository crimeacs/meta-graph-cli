# meta-graph

A clean, `httpie`-style command-line client for Meta's [Graph API](https://developers.facebook.com/docs/graph-api/) and [Instagram Graph API](https://developers.facebook.com/docs/instagram-platform/).

```
$ meta me
{"id": "10000...", "name": "Jane Doe"}

$ meta ig accounts
{"data": [{"page_id": "12345", "page_name": "My Page", "ig_user_id": "17841..."}], "count": 1}

$ meta ig publish 17841... --image-url https://example.com/img.jpg --caption "Hello world"
{"container_id": "18002...", "status": {"status_code": "FINISHED"}, "published": {"id": "17984..."}}
```

No SDK to wrap, no React app to log in to, no config server. Just your token and a thin HTTP shell.

---

## Why

Meta ships SDKs (Python, JS, PHP) but no CLI. The SDKs are typed object hierarchies that don't translate to flags, and the official one is heavy and Marketing-skewed. `meta-graph` is the missing piece: a small, version-agile CLI that maps directly to the underlying HTTP API and bundles the entire Graph + Instagram reference offline.

## Install

```bash
pip install meta-graph        # binary becomes `meta`
```

Or from source:

```bash
git clone https://github.com/crimeacs/meta-graph-cli && cd meta-graph-cli
pip install -e .
```

## Auth

Get a short-lived user token from the [Graph API Explorer](https://developers.facebook.com/tools/explorer/) and either:

```bash
export META_GRAPH_TOKEN="EAA..."
```

…or write a config file at `~/.config/meta-graph/config.toml`:

```toml
[default]
token = "EAA..."
api_version = "v22.0"
app_secret = "..."          # optional; enables appsecret_proof signing

[profile.prod]
token = "EAA..."
```

Use `--profile prod` to switch profiles.

```bash
meta token info             # decode scopes, expiry, app id
meta token refresh --app-id ... --app-secret ...   # short-lived → long-lived (~60 days)
```

## Commands

### Generic (works for any endpoint Meta exposes)

```bash
meta get /me fields=id,name,email
meta get /PAGE_ID/feed fields=id,message,created_time limit=50
meta post /PAGE_ID/feed message='Hello world'
meta delete /POST_ID
echo '[{"method":"GET","relative_url":"me"},
       {"method":"GET","relative_url":"me/accounts?limit=2"}]' | meta batch
```

### Profile + Pages

```bash
meta me                      # /me
meta me pages                # /me/accounts (with linked IG account ids)
meta me permissions          # granted/declined permissions
```

### Instagram (the headline curated surface)

```bash
# accounts
meta ig accounts

# user
meta ig user IG_ID                                   # account fields
meta ig user IG_ID media [--all]                      # list media
meta ig user IG_ID stories                            # active stories
meta ig user IG_ID tags                               # tagged in
meta ig user IG_ID mentions                           # @mentions
meta ig user IG_ID insights --metric impressions,reach --period day
meta ig user IG_ID limit                              # 24h publish quota
meta ig user IG_ID live                               # active live broadcasts

# publish (two-step container flow handled for you)
meta ig publish IG_ID --image-url https://example.com/img.jpg --caption "..."
meta ig publish IG_ID --video-url https://example.com/clip.mp4
meta ig publish IG_ID --video-url https://... --reel
meta ig publish IG_ID --carousel "https://a.jpg,https://b.jpg,https://c.mp4" --caption "..."
meta ig publish IG_ID --story-image https://example.com/story.jpg
meta ig publish-status CONTAINER_ID

# media
meta ig media MEDIA_ID
meta ig media MEDIA_ID children
meta ig media MEDIA_ID comments [--all]
meta ig media MEDIA_ID insights --metric impressions,reach,saved,video_views
meta ig media MEDIA_ID delete

# comments
meta ig comment-on MEDIA_ID --message "Welcome!"
meta ig comment COMMENT_ID
meta ig comment COMMENT_ID reply --message "Thanks!"
meta ig comment COMMENT_ID hide
meta ig comment COMMENT_ID unhide
meta ig comment COMMENT_ID delete

# hashtags
meta ig hashtag search "barista"
meta ig hashtag recent HASHTAG_ID
meta ig hashtag top HASHTAG_ID

# discovery + embed
meta ig business-discovery IG_ID --username @nasa
meta ig oembed https://www.instagram.com/p/SHORTCODE/
```

### Discovery (offline; ships with the wheel)

```bash
meta nodes                   # every documented Graph + IG node
meta edges page              # edges of /page
meta fields user             # documented fields of /user
```

## Output

```bash
meta get /me                    # compact JSON, jq-friendly
meta get /me --pretty           # indented + colored when stdout is a TTY
meta get /me --jq '.id'         # passthrough to jq if installed; tiny fallback otherwise
```

Errors go to stderr as JSON. Exit codes:

| code | meaning |
|---|---|
| 0 | success |
| 1 | Graph API error |
| 2 | usage error (bad flags / JSON) |
| 3 | auth (token missing / invalid / expired) |

## Design

- **Thin HTTP wrapper.** No FB SDK; just `requests`. The CLI follows the Graph API shape directly so anything Meta documents is reachable via `meta get/post/delete`.
- **Auto retry** on transient codes (`1`, `2`) and rate limits (`4`, `17`, `32`, `613`) with exponential backoff + jitter.
- **`appsecret_proof` signing** on every request when `app_secret` is configured (recommended for Live-mode apps).
- **Cursor pagination** via `--all` on listing commands; underlying `client.paginate()` follows `paging.next` until exhausted.
- **Batched requests** via `meta batch` (reads JSON array from stdin).
- **Bundled docs** at `docs/reference.md` — every Graph + Instagram endpoint scraped in one searchable markdown file. Regenerated via `python scripts/scrape.py && python scripts/concat.py && python scripts/build_data.py`.

## Claude Code skill

A [Claude Code skill](https://www.anthropic.com/news/claude-skills) that teaches Claude how to drive this CLI for natural-language Instagram/Meta tasks ships at [`skills/meta-graph/`](./skills/meta-graph/). Install with:

```bash
mkdir -p ~/.claude/skills && cp -r skills/meta-graph ~/.claude/skills/
```

Then ask Claude things like *"post this image to Instagram with caption '…'"* or *"reply to all unanswered comments on this Reel"* — it'll resolve your IG account, run the right `meta ig …` invocations, and surface error codes with actionable fixes. See [`skills/README.md`](./skills/README.md) for details.

## Library use

```python
from meta_graph.client import GraphClient

client = GraphClient(token="EAA...", version="v22.0", app_secret="...")
me = client.get("/me", fields="id,name")
for media in client.paginate("/IG_ID/media", fields="id,caption,timestamp"):
    print(media["id"], media.get("caption"))
```

## Development

```bash
pip install -e .[dev]
pytest -q                       # unit + vcr replay
ruff check src/ tests/
mypy --strict src/meta_graph
```

## License

MIT — see [LICENSE](./LICENSE).

The bundled `docs/reference.md` is scraped from <https://developers.facebook.com/docs/> and is © Meta Platforms, Inc.
