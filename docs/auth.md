# Authentication

Meta tokens are HTTPS bearer credentials. `meta-graph` doesn't run an OAuth flow; it accepts a token from any of these sources, in priority order:

1. `--token <value>` flag (highest)
2. `META_GRAPH_TOKEN` environment variable
3. `~/.config/meta-graph/config.toml` profile

A `[default]` block is loaded unless you pass `--profile <name>`.

## Getting a token

For development, the easiest path is the [Graph API Explorer](https://developers.facebook.com/tools/explorer/):

1. Pick your app from the dropdown.
2. Generate a User Access Token with the scopes you need. Common ones:
   - `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`,
     `instagram_manage_comments`, `instagram_manage_messages`
   - `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`,
     `pages_manage_metadata`, `pages_manage_engagement`, `pages_messaging`
   - `business_management` (if your app uses Business Manager)
3. Click "Generate Access Token" and copy the value.

Paste it into `~/.config/meta-graph/config.toml`:

```toml
[default]
token = "EAA..."
api_version = "v22.0"
app_secret = "abc..."          # optional but recommended for Live-mode apps
```

## Long-lived tokens

User tokens from the Explorer expire in ~1 hour. Exchange for a long-lived (~60 days) token:

```bash
meta token refresh --app-id "$APP_ID" --app-secret "$APP_SECRET"
```

…then write the returned `access_token` back to `config.toml`.

For Pages, the long-lived user token is then used to read `/me/accounts` — each Page's
`access_token` field is a never-expiring Page Access Token (so long as the user
keeps the underlying user token alive). `meta me pages` returns these directly.

## App access tokens

Some endpoints (notably `/instagram_oembed` and `/debug_token`) accept an *app
access token*, which is just `<app_id>|<app_secret>` as a single string:

```bash
meta --token "$APP_ID|$APP_SECRET" ig oembed https://www.instagram.com/p/SHORTCODE/
```

## `appsecret_proof`

Live-mode apps require requests to be signed with an HMAC-SHA256 of the access
token using your app secret. `meta-graph` adds `appsecret_proof` automatically
when `app_secret` is configured (via flag, env, or config). For most use cases
just set it once in `config.toml` and forget about it.

## Token introspection

```bash
meta token info --app-id "$APP_ID" --app-secret "$APP_SECRET"
# → app_id, type, expires_at, scopes, granular_scopes, is_valid
```

`info` defaults to using the current token as both inspector and subject, which
works in dev mode but fails in Live mode — provide an app id + secret to build
the inspector token.

## Common auth errors

| code | meaning | fix |
|---|---|---|
| 190 | Token invalid / session expired | Regenerate via Explorer or `meta token refresh` |
| 102 | Session has been invalidated | User re-auth needed |
| 200 | Missing permission | Check the scopes attached to your token |
| 10 / 299 | App not authorized for this op | Add the relevant Permission in App Dashboard |
