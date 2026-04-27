---
name: meta-platform-ops
description: Operate Meta's Graph API and Instagram Graph API from the command line via the `meta` CLI (https://github.com/crimeacs/meta-graph-cli). Use when the user asks to post, publish, or schedule to Instagram (photo, video, Reel, carousel, story); fetch IG media, stories, mentions, tags, insights or analytics; reply to / hide / moderate IG comments; search Instagram hashtags or find recent/top media for a hashtag; run public business-discovery on another IG profile; get an IG embed code; post to or read a Facebook Page feed; list Pages they manage; debug or refresh an access token; or call any Graph API endpoint like /me, /<page-id>/feed, /<ig-id>/media. Triggers on phrases like "post to Instagram", "publish IG reel", "IG insights", "Instagram analytics", "IG hashtag search", "reply to comment on IG", "Facebook Page post", "Meta Graph API", "WhatsApp Business API", "long-lived token", or any mention of `graph.facebook.com`. Skip for general OAuth questions, browser-side JS SDK work, or pure design/copy tasks.
license: MIT
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
metadata:
  version: 0.1.0
  repo: https://github.com/crimeacs/meta-graph-cli
  cli-binary: meta
---

# meta-platform-ops

Use the `meta` CLI to talk to Meta's Graph API and Instagram Graph API. The CLI is a thin HTTP wrapper — anything documented at <https://developers.facebook.com/docs/graph-api/> or <https://developers.facebook.com/docs/instagram-platform/> is reachable.

## When to use this skill

YES, use it when the user wants to:

- **Publish to Instagram**: photo, video, Reel, carousel (2–10 items), story.
- **Read IG content**: media list, single post, stories, comments, insights (account- or media-level), mentions, tags.
- **Moderate IG comments**: reply, hide/unhide, delete.
- **Discover**: search a hashtag → fetch its recent / top media; look up a public IG Business profile by username (business-discovery).
- **Embed**: get the oEmbed code for an IG post URL.
- **Manage tokens**: introspect the current token, exchange short-lived → long-lived, list scopes.
- **Use Facebook Pages**: list `me/accounts`, post to `<page>/feed`, read insights.
- **Run any other Graph API call**: fall back to `meta get/post/delete <path>` for anything not curated.

NO, this skill isn't for: building an OAuth login UI, embedding the JS SDK in a web app, designing post creatives, or general social-media copywriting (do those before calling `meta`).

## Setup checklist (run first time, then skip)

Before any command, verify:

```bash
which meta || pip install meta-graph-cli
```

If `meta` is missing and pip install fails, fall back to the local source install: `pip install -e ~/Documents/meta-graph-cli`.

Then verify auth — in priority order, check whether ONE of these is set:

```bash
echo "${META_GRAPH_TOKEN:+token in env}"
test -f ~/.config/meta-graph/config.toml && echo "config file present"
```

If neither is true, **stop and ask the user** to either paste a token from <https://developers.facebook.com/tools/explorer/> (with at minimum the `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `instagram_manage_comments`, `pages_show_list`, `pages_read_engagement` scopes) or run `meta token refresh --app-id ... --app-secret ...` to convert a short-lived to a long-lived (~60-day) token.

## Mental model

Meta has **two Instagram API flows**, and the CLI auto-detects which one a token uses:

| Token prefix | Flow | Host | Page mediation? |
|---|---|---|---|
| `EAA…` | Instagram **with Facebook Login** | `graph.facebook.com` | yes — needs a linked FB Page |
| `IGAA…` / `IGQW…` | Instagram **with Instagram Login** | `graph.instagram.com` | no — token IS the IG account |

The CLI picks the right host automatically from the token's prefix; override with `--base` only when needed.

**Resolving the IG user id**:

```bash
# Either flow:
meta ig me                 # returns the IG account on either flow
meta ig accounts           # also works on either; IG-direct returns one row, IG-flow="instagram-login"
```

For the Facebook-Login flow, `meta ig accounts` returns one row per Page, each with `ig_user_id`. Pass that id to every subsequent `meta ig user`, `meta ig publish`, `meta ig hashtag` command.

For the Instagram-Login flow, you can use the `meta ig me` shortcuts (`me media`, `me insights`) so you never need the explicit id, OR run `meta ig me --jq '.user_id'` once and reuse the value. `meta ig publish me ...` also works (the token resolves `/me/media` correctly on graph.instagram.com).

## Core workflows

### Publish content (handles container creation + status polling automatically)

```bash
# Single image
meta ig publish $IG_ID --image-url https://example.com/img.jpg --caption "..."

# Single video
meta ig publish $IG_ID --video-url https://example.com/clip.mp4 --caption "..."

# Reel (note --reel flag changes media_type to REELS)
meta ig publish $IG_ID --video-url https://example.com/reel.mp4 --reel --caption "..."

# Carousel (2-10 image+video URLs, comma-separated)
meta ig publish $IG_ID --carousel "https://a.jpg,https://b.jpg,https://c.mp4" --caption "..."

# Story
meta ig publish $IG_ID --story-image https://example.com/story.jpg
meta ig publish $IG_ID --story-video https://example.com/story.mp4

# Don't wait for processing (returns container id immediately)
meta ig publish $IG_ID --image-url https://... --no-wait
```

**Output shape**: `{container_id, status: {status_code: "FINISHED"|"IN_PROGRESS"|"ERROR"|"EXPIRED"}, published: {id}}`. The CLI polls `status_code` every 3s up to 5 min by default. If the user explicitly wants to background a long video, pass `--no-wait` and resume later with `meta ig publish-status $CONTAINER_ID && meta post /$IG_ID/media_publish creation_id=$CONTAINER_ID`.

### Read content

```bash
meta ig user $IG_ID                                       # account fields
meta ig user $IG_ID media [--all]                         # list media (paginated)
meta ig user $IG_ID stories                               # active stories
meta ig user $IG_ID tags                                  # product-tagged in
meta ig user $IG_ID mentions                             # @-mentions
meta ig media $MEDIA_ID                                   # single post
meta ig media $MEDIA_ID children                          # carousel children
meta ig media $MEDIA_ID comments [--all]                  # comments with replies
```

For all listing commands, prefer `--all` only when the user wants every item. Default is the first page (25 by default).

### Insights

Account-level metrics need a `--metric` list and a `--period`. Common combos:

```bash
# 7-day daily traffic
meta ig user $IG_ID insights --metric impressions,reach,profile_views --period day --since 7daysago

# Audience demographics (lifetime, single-value)
meta ig user $IG_ID insights --metric audience_gender_age,audience_country --period lifetime

# Followers over time (28-day rollup)
meta ig user $IG_ID insights --metric follower_count --period day --since 28daysago
```

Per-media metrics:

```bash
# Photo / video
meta ig media $MEDIA_ID insights --metric impressions,reach,saved,engagement

# Reel
meta ig media $MEDIA_ID insights --metric reach,plays,total_interactions,saved,shares

# Story (must be queried while the story is live, < 24h old)
meta ig media $MEDIA_ID insights --metric impressions,reach,replies,exits,taps_forward,taps_back
```

When a metric returns `(#100) Tried accessing nonexisting field`, the metric name has changed in the user's Graph API version — fall back to `meta --api-version v18.0 ig media $MEDIA_ID insights ...` or check `docs/reference.md` for the correct name.

### Comment moderation

```bash
meta ig comment-on $MEDIA_ID --message "Welcome!"        # post a top-level comment
meta ig comment $COMMENT_ID                               # read
meta ig comment $COMMENT_ID reply --message "Thanks!"
meta ig comment $COMMENT_ID hide                          # hide from public view
meta ig comment $COMMENT_ID unhide
meta ig comment $COMMENT_ID delete                        # confirms before deleting
```

Bulk-reply pattern:

```bash
meta ig media $MEDIA_ID comments --all --jq '.data[] | select(.replies == null) | .id' \
  | while read -r CID; do
      meta ig comment "$CID" reply --message "Thanks for stopping by!"
    done
```

### Hashtag flows

```bash
HASHTAG_ID=$(meta ig hashtag search "barista" --jq '.data[0].id')
meta ig hashtag recent $HASHTAG_ID --jq '.data[].permalink'
meta ig hashtag top    $HASHTAG_ID --jq '.data[].permalink'
```

A user account can resolve only **30 unique hashtags per 7-day rolling window** (Meta limit). Cache the `hashtag_id` rather than re-resolving the same string.

### Generic escape hatch

Anything not curated is one `meta get/post/delete` away:

```bash
meta get /$PAGE_ID/feed fields=id,message,created_time limit=50
meta post /$PAGE_ID/photos url=https://example.com/img.jpg caption='Hi'
meta delete /$POST_ID
echo '[{"method":"GET","relative_url":"me"},{"method":"GET","relative_url":"me/accounts"}]' | meta batch
```

For discovery (offline, no network needed):

```bash
meta nodes                # 75+ documented nodes
meta edges ig-user        # all edges of /<ig-user>
meta fields user          # documented fields of /user
```

The exhaustive reference (4.2 MB, 70k lines) ships at `~/Documents/meta-graph-cli/docs/reference.md`. **Grep it before guessing field names.**

## Output handling

The CLI outputs JSON to stdout by default. Pass `--pretty` for indented + colored, or `--jq <expr>` for a value extraction:

```bash
meta ig accounts --jq '.data[0].ig_user_id'                              # single value
meta ig user $IG_ID media --all --jq '.data[] | "\(.id) \(.timestamp)"'  # list
```

When piping to other tools, leave the default JSON. When showing the user a summary, use `--pretty` only if the result is small (<50 lines); otherwise pull specific fields with `--jq`.

## Error handling

The CLI maps Meta error codes to typed exceptions and exits with:

| code | meaning |
|---|---|
| 0 | success |
| 1 | Graph API error (any code that isn't auth) |
| 2 | usage error (bad flags, malformed JSON) |
| 3 | auth error (token missing, invalid, or expired) |

When you see exit 3, the user's token is expired or missing scopes. Ask them to:

1. Regenerate at <https://developers.facebook.com/tools/explorer/>, or
2. Run `meta token refresh --app-id "$APP_ID" --app-secret "$APP_SECRET"` if they have a long-lived setup, or
3. Check granted scopes with `meta token info --app-id ... --app-secret ...`.

Common failures + cause + fix:

| `error.code` | meaning | fix |
|---|---|---|
| 190 | token invalid / session expired | regenerate or refresh |
| 102 | session invalidated by user re-auth | user must log in again |
| 200 / 10 / 299 | missing permission | add scope to token in App Dashboard |
| 4 / 17 / 32 / 613 | rate limit | CLI auto-retries; if it still fails, back off + try again later |
| 100 | invalid request (bad field, missing param) | check field name vs `docs/reference.md` |
| 9004 | media `image_url`/`video_url` not reachable | URL must be public + HTTPS + content-type matches |
| 36003 | publish container in `ERROR` state | usually unsupported codec; re-encode video to H.264/AAC |

## Examples

### "Post a photo to Instagram with caption 'Hello world'"

```bash
IG_ID=$(meta ig accounts --jq '.data[0].ig_user_id')
meta ig publish "$IG_ID" --image-url https://example.com/img.jpg --caption "Hello world"
```

### "Show me reach for my last 5 posts"

```bash
IG_ID=$(meta ig accounts --jq '.data[0].ig_user_id')
meta ig user "$IG_ID" media --jq '.data[:5] | .[].id' | while read -r MID; do
  echo -n "$MID "
  meta ig media "$MID" insights --metric reach --jq '.data[0].values[0].value'
done
```

### "Reply to every unanswered comment on post X with 'Thanks!'"

```bash
meta ig media $MEDIA_ID comments --all \
  --jq '.data[] | select(.replies == null) | .id' \
  | while read -r CID; do
      meta ig comment "$CID" reply --message "Thanks!"
    done
```

### "What hashtag should I use? Show me top media for #brewedmagic"

```bash
HID=$(meta ig hashtag search "brewedmagic" --jq '.data[0].id')
meta ig hashtag top "$HID" --jq '.data[] | {id, like_count, comments_count, permalink}'
```

### "Decode this token someone sent me"

```bash
meta token debug "EAA..." --app-id "$APP_ID" --app-secret "$APP_SECRET"
```

## Composability

This skill is safe to run alongside others. It owns nothing global — only invocation of the `meta` CLI. If a higher-priority skill (e.g. one that bundles a fully-managed IG OAuth flow) is also active, it can pre-resolve the token; this skill will pick it up via `META_GRAPH_TOKEN`.

## When NOT to invoke

- The user wants UI/UX help for an Instagram-themed React component → graphic/frontend skill, not this one.
- The user is asking general questions about IG API design without a concrete task → answer from knowledge, don't shell out.
- The user is using a different language SDK (e.g. `facebook-business` Python package) and wants help wrapping it → this skill is CLI-only; redirect to library docs.
- The user has zero credentials and isn't ready to set up a Meta app → guide them through <https://developers.facebook.com/apps/> creation first; only invoke `meta` once a token exists.
