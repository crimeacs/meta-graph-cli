# Cookbook

Real recipes you'll actually use. Every example assumes `META_GRAPH_TOKEN` is set.

## 1. Get your IG account id quickly

```bash
meta ig accounts --jq '.data[0].ig_user_id'
```

## 2. Publish a single photo and capture the published id

```bash
meta ig publish 17841... \
  --image-url https://example.com/img.jpg \
  --caption "Hello world" \
  --jq '.published.id'
```

## 3. Publish a Reel and don't wait for processing

```bash
CID=$(meta ig publish 17841... \
  --video-url https://example.com/clip.mp4 --reel \
  --no-wait --jq '.container_id')

# Poll on your own schedule
while true; do
  STATUS=$(meta ig publish-status "$CID" --jq '.status_code')
  echo "$STATUS"
  [ "$STATUS" = "FINISHED" ] && meta post /17841.../media_publish creation_id=$CID && break
  [ "$STATUS" = "ERROR" ] && exit 1
  sleep 3
done
```

## 4. Publish a 5-image carousel

```bash
meta ig publish 17841... \
  --carousel "https://a.jpg,https://b.jpg,https://c.jpg,https://d.jpg,https://e.jpg" \
  --caption "5 photos in one post"
```

## 5. Daily account insights as CSV

```bash
meta ig user 17841... insights \
  --metric impressions,reach,profile_views,website_clicks \
  --period day \
  --jq '.data[] | "\(.name),\(.values[-1].value),\(.values[-1].end_time)"'
```

## 6. Find recent posts with a hashtag

```bash
HASHTAG_ID=$(meta ig hashtag search "barista" --jq '.data[0].id')
meta ig hashtag recent "$HASHTAG_ID" --jq '.data[].permalink'
```

## 7. Auto-reply to every new comment on a post

```bash
meta ig media 1798... comments --all --jq '.data[] | select(.replies == null) | .id' \
  | while read -r CID; do
    meta ig comment "$CID" reply --message "Thanks for stopping by!"
  done
```

## 8. Public competitor profile (read-only, no follow)

```bash
meta ig business-discovery 17841... --username @nasa \
  --jq '.business_discovery | {name, followers_count, media_count, biography}'
```

## 9. Batched requests (one round trip, two reads)

```bash
echo '[
  {"method": "GET", "relative_url": "me?fields=id,name"},
  {"method": "GET", "relative_url": "me/accounts?fields=id,name&limit=5"}
]' | meta batch --jq '.[].body | fromjson'
```

## 10. Long-lived token exchange

```bash
meta token refresh --app-id "$APP_ID" --app-secret "$APP_SECRET" --jq '.access_token'
# copy the value into ~/.config/meta-graph/config.toml
```

## 11. Library use, paginate every media

```python
from meta_graph.client import GraphClient

client = GraphClient(token="EAA...", app_secret="...")
total = 0
for media in client.paginate("/17841.../media", fields="id,caption,timestamp", limit=100):
    print(media["id"], media.get("caption", "")[:60])
    total += 1
print(f"{total} total")
```

## 12. Use a different Graph API version per call

```bash
meta --api-version v18.0 get /me
```

## 13. Switch profiles (e.g. dev vs prod)

```toml
# ~/.config/meta-graph/config.toml
[default]
token = "EAA_dev..."

[profile.prod]
token = "EAA_prod..."
app_secret = "..."
```

```bash
meta --profile prod ig accounts
```
