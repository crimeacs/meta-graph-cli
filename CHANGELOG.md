# Changelog

## 0.1.0 — 2026-04-27

Initial release.

### CLI

- `meta get|post|delete <path> [k=v ...]` — generic Graph API verbs.
- `meta batch` — JSON array on stdin → batched request.
- `meta me`, `meta me pages`, `meta me permissions` — profile + Pages.
- `meta token info|debug|refresh` — token introspection and long-lived exchange.
- `meta nodes`, `meta edges <node>`, `meta fields <node>` — offline discovery from bundled docs.
- **Instagram, full surface:**
  - `meta ig accounts` — Pages + linked IG ids.
  - `meta ig user IG_ID` (+ `media`, `stories`, `tags`, `mentions`, `insights`, `live`, `limit`).
  - `meta ig publish` — single image / video / Reel / carousel / story; container + media_publish handled for you.
  - `meta ig publish-status CONTAINER_ID`.
  - `meta ig media MEDIA_ID` (+ `children`, `comments`, `insights`, `delete`).
  - `meta ig comment-on`, `meta ig comment` (+ `reply`, `hide`, `unhide`, `delete`).
  - `meta ig hashtag search|recent|top`.
  - `meta ig business-discovery`, `meta ig oembed`.

### Library

- `from meta_graph.client import GraphClient` exposes `get/post/delete/paginate/batch`.
- Typed errors: `AuthError`, `PermissionError_`, `RateLimitError`, `TransientError`, `InvalidRequestError`, `GraphError`.
- Auto-retry with exponential backoff + jitter on transient + rate-limit codes.
- Optional `appsecret_proof` signing (auto-on when `app_secret` is provided).

### Tooling

- Bundles `docs/reference.md` (~4 MB, 70k lines) — every Meta Graph + Instagram endpoint.
- `scripts/{scrape,concat,build_data}.py` regenerate the reference + offline discovery JSON.
- GitHub Actions: ruff + mypy --strict + pytest on Python 3.10/3.11/3.12.
- MIT licensed.
