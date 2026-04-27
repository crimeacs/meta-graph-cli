"""`meta ig ...` — full Instagram Graph API surface as curated commands.

Coverage map:

  meta ig accounts                       List your Pages and their linked IG Business Accounts.
  meta ig user IG_ID                     Fields on an IG Business/Creator account.
  meta ig user IG_ID media               List media (paginated).
  meta ig user IG_ID stories             Active stories.
  meta ig user IG_ID tags                Media this account is tagged in.
  meta ig user IG_ID mentions            Comments/captions that @mentioned this account.
  meta ig user IG_ID insights            Account-level insights.
  meta ig user IG_ID live                Active live broadcasts.
  meta ig user IG_ID limit               Content publishing limit (24h post counter).

  meta ig publish IG_ID --image-url ...                  Single image
  meta ig publish IG_ID --video-url ... [--reel]         Single video / Reel
  meta ig publish IG_ID --carousel URL,URL,...           Carousel (2-10 items)
  meta ig publish IG_ID --story-image ... | --story-video ...   Story
  meta ig publish-status CONTAINER_ID                    Poll a container's status

  meta ig media MEDIA_ID                 Get a media object.
  meta ig media MEDIA_ID children        Children of a carousel.
  meta ig media MEDIA_ID comments        Comments on a media.
  meta ig media MEDIA_ID insights        Per-media insights.
  meta ig media MEDIA_ID delete          Delete a media object.

  meta ig comment COMMENT_ID             Get one comment.
  meta ig comment COMMENT_ID reply --message "..."       Reply.
  meta ig comment COMMENT_ID hide / unhide               Toggle visibility.
  meta ig comment COMMENT_ID delete                      Delete.
  meta ig comment-on MEDIA_ID --message "..."            Post a top-level comment.

  meta ig hashtag search QUERY           Resolve a hashtag string → hashtag id.
  meta ig hashtag HASHTAG_ID recent IG_ID    Recent media for the hashtag.
  meta ig hashtag HASHTAG_ID top IG_ID        Top media for the hashtag.

  meta ig business-discovery IG_ID --username NAME      Public IG Business profile.
  meta ig oembed URL                     Embed code for a public IG post URL.
"""
from __future__ import annotations

import time
from typing import Any

import click

from meta_graph._runtime import build_client, global_options, handle_graph_error, stash_globals
from meta_graph.errors import GraphError
from meta_graph.output import emit


@click.group()
@global_options
@click.pass_context
def ig(ctx: click.Context, **gflags: object) -> None:
    """Instagram Graph API: accounts, media, publishing, insights, comments, hashtags."""
    stash_globals(ctx, **gflags)


# ---- accounts / me --------------------------------------------------------

@ig.command("accounts")
@click.pass_context
def accounts(ctx: click.Context) -> None:
    """List Pages you manage and their linked IG Business Account ids.

    For Instagram-with-Instagram-Login tokens (IGAA…) there are no Pages —
    the response collapses to a single row with `flow: "instagram-login"`.
    """
    client = build_client(ctx.obj)
    try:
        pages = client.list_pages_with_ig()
    except GraphError as e:
        handle_graph_error(e)
        return
    flow = "instagram-login" if client.is_instagram_login else "facebook-login"
    out = []
    for p in pages:
        ig_obj = p.get("instagram_business_account") or {}
        out.append(
            {
                "flow": flow,
                "page_id": p.get("id"),
                "page_name": p.get("name"),
                "ig_user_id": ig_obj.get("id"),
                "page_access_token": p.get("access_token"),
            }
        )
    emit({"data": out, "count": len(out)},
         pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig.group("me", invoke_without_command=True)
@click.option("--fields",
              default="user_id,username,name,biography,profile_picture_url,"
                      "followers_count,follows_count,media_count,website,account_type",
              show_default=False)
@click.pass_context
def ig_me(ctx: click.Context, fields: str) -> None:
    """The IG account tied to the current token.

    For IGAA… tokens, /me resolves directly to the IG user (no Page mediation).
    For EAA… tokens this calls /me/accounts and picks the first linked IG account.
    """
    client = build_client(ctx.obj)
    if ctx.invoked_subcommand is not None:
        # Stash the resolved id for sub-subcommands
        try:
            ig_id = _first_ig_id(client)
        except GraphError as e:
            handle_graph_error(e)
            return
        ctx.obj["ig_id"] = ig_id
        return
    try:
        if client.is_instagram_login:
            result = client.get("/me", fields=fields)
        else:
            ig_id = _first_ig_id(client)
            result = client.get(f"/{ig_id}", fields=fields)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_me.command("media")
@click.option("--fields", default=None, show_default=False)
@click.option("--limit", type=int, default=25, show_default=True)
@click.option("--all", "all_pages", is_flag=True, help="Follow paging.")
@click.pass_context
def me_media(ctx: click.Context, fields: str | None, limit: int, all_pages: bool) -> None:
    """List media on the IG account tied to the current token."""
    client = build_client(ctx.obj)
    fields = fields or DEFAULT_IG_MEDIA_FIELDS
    path = "/me/media" if client.is_instagram_login else f"/{ctx.obj['ig_id']}/media"
    try:
        if all_pages:
            data = list(client.paginate(path, fields=fields, limit=limit))
        else:
            page = client.get(path, fields=fields, limit=limit)
            data = page.get("data") or []
    except GraphError as e:
        handle_graph_error(e)
        return
    emit({"data": data, "count": len(data)},
         pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_me.command("insights")
@click.option("--metric", required=True)
@click.option("--period", default="day", show_default=True,
              type=click.Choice(["day", "week", "days_28", "lifetime"]))
@click.option("--since", default=None)
@click.option("--until", default=None)
@click.option("--metric-type", default=None)
@click.pass_context
def me_insights(ctx: click.Context, metric: str, period: str,
                since: str | None, until: str | None, metric_type: str | None) -> None:
    """Account insights for the IG account tied to the current token."""
    client = build_client(ctx.obj)
    path = "/me/insights" if client.is_instagram_login else f"/{ctx.obj['ig_id']}/insights"
    params: dict[str, Any] = {"metric": metric, "period": period}
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if metric_type:
        params["metric_type"] = metric_type
    try:
        result = client.get(path, **params)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


# ---- user ----------------------------------------------------------------

DEFAULT_IG_USER_FIELDS = (
    "id,username,name,biography,profile_picture_url,followers_count,"
    "follows_count,media_count,website"
)


@ig.group("user", invoke_without_command=True)
@click.argument("ig_id")
@click.option("--fields", default=DEFAULT_IG_USER_FIELDS, show_default=False,
              help="Fields to fetch on the IG account.")
@click.pass_context
def ig_user(ctx: click.Context, ig_id: str, fields: str) -> None:
    """Get fields on an IG Business/Creator account."""
    ctx.ensure_object(dict)
    ctx.obj["ig_id"] = ig_id
    if ctx.invoked_subcommand is not None:
        return
    client = build_client(ctx.obj)
    try:
        result = client.get(f"/{ig_id}", fields=fields)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


DEFAULT_IG_MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,media_url,permalink,thumbnail_url,"
    "timestamp,username,like_count,comments_count,is_shared_to_feed"
)


@ig_user.command("media")
@click.option("--fields", default=DEFAULT_IG_MEDIA_FIELDS, show_default=False)
@click.option("--limit", type=int, default=25, show_default=True,
              help="Page size; iterates until exhausted.")
@click.option("--all", "all_pages", is_flag=True,
              help="Follow paging to fetch every media (otherwise stops at --limit).")
@click.pass_context
def user_media(ctx: click.Context, fields: str, limit: int, all_pages: bool) -> None:
    """List media for the IG account."""
    client = build_client(ctx.obj)
    ig_id = ctx.obj["ig_id"]
    try:
        if all_pages:
            data = list(client.paginate(f"/{ig_id}/media", fields=fields, limit=limit))
        else:
            page = client.get(f"/{ig_id}/media", fields=fields, limit=limit)
            data = page.get("data") or []
    except GraphError as e:
        handle_graph_error(e)
        return
    emit({"data": data, "count": len(data)},
         pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_user.command("stories")
@click.option("--fields", default=DEFAULT_IG_MEDIA_FIELDS, show_default=False)
@click.pass_context
def user_stories(ctx: click.Context, fields: str) -> None:
    """List active stories for the IG account."""
    client = build_client(ctx.obj)
    ig_id = ctx.obj["ig_id"]
    try:
        result = client.get(f"/{ig_id}/stories", fields=fields)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_user.command("tags")
@click.option("--fields", default=DEFAULT_IG_MEDIA_FIELDS, show_default=False)
@click.pass_context
def user_tags(ctx: click.Context, fields: str) -> None:
    """Media this account has been product-tagged in (Shopping)."""
    client = build_client(ctx.obj)
    ig_id = ctx.obj["ig_id"]
    try:
        result = client.get(f"/{ig_id}/tags", fields=fields)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_user.command("mentions")
@click.option("--fields", default="id,caption_text,timestamp,media", show_default=True)
@click.pass_context
def user_mentions(ctx: click.Context, fields: str) -> None:
    """Captions/comments where this account was @mentioned."""
    client = build_client(ctx.obj)
    ig_id = ctx.obj["ig_id"]
    try:
        result = client.get(f"/{ig_id}/mentions", fields=fields)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_user.command("insights")
@click.option("--metric", required=True,
              help="Comma-separated list, e.g. impressions,reach,profile_views,follower_count")
@click.option("--period", default="day", show_default=True,
              type=click.Choice(["day", "week", "days_28", "lifetime"]))
@click.option("--since", default=None, help="Unix ts or ISO date.")
@click.option("--until", default=None, help="Unix ts or ISO date.")
@click.option("--metric-type", default=None,
              help="Required for v18+ for some metrics. Try 'total_value'.")
@click.pass_context
def user_insights(ctx: click.Context, metric: str, period: str,
                  since: str | None, until: str | None, metric_type: str | None) -> None:
    """Account-level insights."""
    client = build_client(ctx.obj)
    ig_id = ctx.obj["ig_id"]
    params: dict[str, Any] = {"metric": metric, "period": period}
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if metric_type:
        params["metric_type"] = metric_type
    try:
        result = client.get(f"/{ig_id}/insights", **params)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_user.command("live")
@click.pass_context
def user_live(ctx: click.Context) -> None:
    """Active live broadcasts on this account."""
    client = build_client(ctx.obj)
    ig_id = ctx.obj["ig_id"]
    try:
        result = client.get(f"/{ig_id}/live_media")
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_user.command("limit")
@click.pass_context
def user_limit(ctx: click.Context) -> None:
    """24-hour content-publishing limit (max 50 IG posts per rolling 24h window)."""
    client = build_client(ctx.obj)
    ig_id = ctx.obj["ig_id"]
    try:
        result = client.get(
            f"/{ig_id}/content_publishing_limit",
            fields="quota_usage,config",
        )
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


# ---- publish --------------------------------------------------------------

@ig.command("publish")
@click.argument("ig_id")
@click.option("--image-url", default=None, help="Single image (jpeg/png) URL.")
@click.option("--video-url", default=None, help="Single video URL.")
@click.option("--reel", is_flag=True, help="Treat --video-url as a Reel.")
@click.option("--carousel", default=None,
              help="Comma-separated list of 2-10 item URLs (images/videos).")
@click.option("--story-image", default=None, help="Story image URL.")
@click.option("--story-video", default=None, help="Story video URL.")
@click.option("--caption", default=None, help="Caption text.")
@click.option("--location-id", default=None, help="Optional FB Page id for location tag.")
@click.option("--user-tags", default=None,
              help='JSON list of user tags, e.g. \'[{"username":"foo","x":0.5,"y":0.5}]\'')
@click.option("--no-wait", is_flag=True,
              help="Return the container id immediately; don't poll/publish.")
@click.option("--poll-interval", type=int, default=3, show_default=True,
              help="Seconds between status polls (when waiting).")
@click.option("--poll-timeout", type=int, default=300, show_default=True,
              help="Give up after this many seconds.")
@click.pass_context
def publish(ctx: click.Context, ig_id: str, **kw: Any) -> None:
    """Publish a photo, video, Reel, carousel, or story.

    Two-step flow per the Content Publishing API:
      1) POST /{ig_id}/media → returns a container id
      2) POST /{ig_id}/media_publish?creation_id=<id> → returns the published media id

    For carousels, each child container is created first, then the parent.
    """
    client = build_client(ctx.obj)
    try:
        if kw["carousel"]:
            container_id = _create_carousel(client, ig_id, kw)
        elif kw["story_image"] or kw["story_video"]:
            container_id = _create_story(client, ig_id, kw)
        elif kw["image_url"]:
            container_id = _create_single(client, ig_id, kw, kind="IMAGE")
        elif kw["video_url"]:
            container_id = _create_single(client, ig_id, kw, kind="REELS" if kw["reel"] else "VIDEO")
        else:
            raise click.UsageError(
                "supply one of: --image-url, --video-url, --carousel, --story-image, --story-video"
            )

        result: dict[str, Any] = {"container_id": container_id}

        if kw["no_wait"]:
            emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))
            return

        status = _wait_container(
            client, container_id,
            timeout=kw["poll_timeout"], interval=kw["poll_interval"],
        )
        result["status"] = status

        if status.get("status_code") != "FINISHED":
            emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))
            return

        published = client.post(f"/{ig_id}/media_publish", creation_id=container_id)
        result["published"] = published
    except GraphError as e:
        handle_graph_error(e)
        return

    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


def _create_single(client: Any, ig_id: str, kw: dict[str, Any], *, kind: str) -> str:
    fields: dict[str, Any] = {}
    if kind == "IMAGE":
        fields["image_url"] = kw["image_url"]
    elif kind == "VIDEO":
        fields["media_type"] = "VIDEO"
        fields["video_url"] = kw["video_url"]
    elif kind == "REELS":
        fields["media_type"] = "REELS"
        fields["video_url"] = kw["video_url"]
    if kw["caption"]:
        fields["caption"] = kw["caption"]
    if kw["location_id"]:
        fields["location_id"] = kw["location_id"]
    if kw["user_tags"]:
        fields["user_tags"] = kw["user_tags"]
    out = client.post(f"/{ig_id}/media", **fields)
    return str(out["id"])


def _create_carousel(client: Any, ig_id: str, kw: dict[str, Any]) -> str:
    urls = [u.strip() for u in kw["carousel"].split(",") if u.strip()]
    if not 2 <= len(urls) <= 10:
        raise click.UsageError("carousel needs 2-10 item URLs")
    children: list[str] = []
    for u in urls:
        is_video = u.lower().endswith((".mp4", ".mov"))
        body = {"is_carousel_item": "true"}
        if is_video:
            body["media_type"] = "VIDEO"
            body["video_url"] = u
        else:
            body["image_url"] = u
        out = client.post(f"/{ig_id}/media", **body)
        children.append(out["id"])
    parent_body: dict[str, Any] = {"media_type": "CAROUSEL", "children": ",".join(children)}
    if kw["caption"]:
        parent_body["caption"] = kw["caption"]
    if kw["location_id"]:
        parent_body["location_id"] = kw["location_id"]
    out = client.post(f"/{ig_id}/media", **parent_body)
    return str(out["id"])


def _create_story(client: Any, ig_id: str, kw: dict[str, Any]) -> str:
    if kw["story_image"]:
        body = {"image_url": kw["story_image"], "media_type": "STORIES"}
    else:
        body = {"video_url": kw["story_video"], "media_type": "STORIES"}
    out = client.post(f"/{ig_id}/media", **body)
    return str(out["id"])


def _wait_container(client: Any, container_id: str, *, timeout: int, interval: int) -> dict[str, Any]:
    deadline = time.time() + timeout
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = client.get(f"/{container_id}", fields="status_code,status")
        if last.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"):
            return last
        time.sleep(interval)
    return last


@ig.command("publish-status")
@click.argument("container_id")
@click.pass_context
def publish_status(ctx: click.Context, container_id: str) -> None:
    """Check the processing status of a publish container."""
    client = build_client(ctx.obj)
    try:
        result = client.get(f"/{container_id}", fields="status_code,status")
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


# ---- media ----------------------------------------------------------------

@ig.group("media", invoke_without_command=True)
@click.argument("media_id")
@click.option("--fields", default=DEFAULT_IG_MEDIA_FIELDS, show_default=False)
@click.pass_context
def ig_media(ctx: click.Context, media_id: str, fields: str) -> None:
    """Get an IG media object."""
    ctx.ensure_object(dict)
    ctx.obj["media_id"] = media_id
    if ctx.invoked_subcommand is not None:
        return
    client = build_client(ctx.obj)
    try:
        result = client.get(f"/{media_id}", fields=fields)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_media.command("children")
@click.option("--fields", default=DEFAULT_IG_MEDIA_FIELDS, show_default=False)
@click.pass_context
def media_children(ctx: click.Context, fields: str) -> None:
    """Children of a carousel."""
    client = build_client(ctx.obj)
    media_id = ctx.obj["media_id"]
    try:
        result = client.get(f"/{media_id}/children", fields=fields)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_media.command("comments")
@click.option("--fields", default="id,text,username,timestamp,like_count,replies",
              show_default=True)
@click.option("--all", "all_pages", is_flag=True, help="Follow paging.")
@click.pass_context
def media_comments(ctx: click.Context, fields: str, all_pages: bool) -> None:
    """List comments on this media."""
    client = build_client(ctx.obj)
    media_id = ctx.obj["media_id"]
    try:
        if all_pages:
            data = list(client.paginate(f"/{media_id}/comments", fields=fields))
            result: dict[str, Any] = {"data": data, "count": len(data)}
        else:
            result = client.get(f"/{media_id}/comments", fields=fields)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_media.command("insights")
@click.option("--metric", required=True,
              help="Comma-separated list, e.g. impressions,reach,saved,video_views")
@click.pass_context
def media_insights(ctx: click.Context, metric: str) -> None:
    """Per-media insights."""
    client = build_client(ctx.obj)
    media_id = ctx.obj["media_id"]
    try:
        result = client.get(f"/{media_id}/insights", metric=metric)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_media.command("delete")
@click.confirmation_option(prompt="Delete this media?")
@click.pass_context
def media_delete(ctx: click.Context) -> None:
    """Delete a media object."""
    client = build_client(ctx.obj)
    media_id = ctx.obj["media_id"]
    try:
        result = client.delete(f"/{media_id}")
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


# ---- comments -------------------------------------------------------------

@ig.command("comment-on")
@click.argument("media_id")
@click.option("--message", required=True, help="Comment text.")
@click.pass_context
def comment_on(ctx: click.Context, media_id: str, message: str) -> None:
    """Post a top-level comment on a media object."""
    client = build_client(ctx.obj)
    try:
        result = client.post(f"/{media_id}/comments", message=message)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig.group("comment", invoke_without_command=True)
@click.argument("comment_id")
@click.option("--fields", default="id,text,username,timestamp,like_count,hidden",
              show_default=True)
@click.pass_context
def ig_comment(ctx: click.Context, comment_id: str, fields: str) -> None:
    """Get / reply to / hide / delete a comment."""
    ctx.ensure_object(dict)
    ctx.obj["comment_id"] = comment_id
    if ctx.invoked_subcommand is not None:
        return
    client = build_client(ctx.obj)
    try:
        result = client.get(f"/{comment_id}", fields=fields)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_comment.command("reply")
@click.option("--message", required=True)
@click.pass_context
def comment_reply(ctx: click.Context, message: str) -> None:
    """Reply to a comment."""
    client = build_client(ctx.obj)
    cid = ctx.obj["comment_id"]
    try:
        result = client.post(f"/{cid}/replies", message=message)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_comment.command("hide")
@click.pass_context
def comment_hide(ctx: click.Context) -> None:
    """Hide a comment."""
    client = build_client(ctx.obj)
    cid = ctx.obj["comment_id"]
    try:
        result = client.post(f"/{cid}", hide="true")
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_comment.command("unhide")
@click.pass_context
def comment_unhide(ctx: click.Context) -> None:
    """Unhide a comment."""
    client = build_client(ctx.obj)
    cid = ctx.obj["comment_id"]
    try:
        result = client.post(f"/{cid}", hide="false")
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@ig_comment.command("delete")
@click.confirmation_option(prompt="Delete this comment?")
@click.pass_context
def comment_delete(ctx: click.Context) -> None:
    """Delete a comment."""
    client = build_client(ctx.obj)
    cid = ctx.obj["comment_id"]
    try:
        result = client.delete(f"/{cid}")
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


# ---- hashtag --------------------------------------------------------------

@ig.group("hashtag")
@click.pass_context
def hashtag(ctx: click.Context) -> None:
    """Search hashtags and read their recent / top media."""


@hashtag.command("search")
@click.argument("query")
@click.option("--user-id", default=None,
              help="IG user id to use as the searching account (defaults to your first IG account).")
@click.pass_context
def hashtag_search(ctx: click.Context, query: str, user_id: str | None) -> None:
    """Resolve a hashtag string to its hashtag id."""
    client = build_client(ctx.obj)
    if not user_id:
        try:
            user_id = _first_ig_id(client)
        except GraphError as e:
            handle_graph_error(e)
            return
    try:
        result = client.get("/ig_hashtag_search", user_id=user_id, q=query.lstrip("#"))
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@hashtag.command("recent")
@click.argument("hashtag_id")
@click.option("--user-id", default=None, help="IG user id (defaults to your first IG account).")
@click.option("--fields", default=DEFAULT_IG_MEDIA_FIELDS, show_default=False)
@click.pass_context
def hashtag_recent(ctx: click.Context, hashtag_id: str, user_id: str | None, fields: str) -> None:
    """Recent media (within 24h) for a hashtag id."""
    client = build_client(ctx.obj)
    if not user_id:
        try:
            user_id = _first_ig_id(client)
        except GraphError as e:
            handle_graph_error(e)
            return
    try:
        result = client.get(
            f"/{hashtag_id}/recent_media", user_id=user_id, fields=fields,
        )
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


@hashtag.command("top")
@click.argument("hashtag_id")
@click.option("--user-id", default=None)
@click.option("--fields", default=DEFAULT_IG_MEDIA_FIELDS, show_default=False)
@click.pass_context
def hashtag_top(ctx: click.Context, hashtag_id: str, user_id: str | None, fields: str) -> None:
    """Top media of all time for a hashtag id."""
    client = build_client(ctx.obj)
    if not user_id:
        try:
            user_id = _first_ig_id(client)
        except GraphError as e:
            handle_graph_error(e)
            return
    try:
        result = client.get(
            f"/{hashtag_id}/top_media", user_id=user_id, fields=fields,
        )
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


def _first_ig_id(client: Any) -> str:
    """Best IG user id for the current token.

    On the IG-direct flow we ask /me directly. On the FB-mediated flow we walk
    /me/accounts and pick the first Page that has a linked IG Business Account.
    """
    if getattr(client, "is_instagram_login", False):
        me = client.get("/me", fields="user_id")
        uid = me.get("user_id") or me.get("id")
        if uid:
            return str(uid)
        raise GraphError("could not resolve /me on the IG-direct flow.")
    pages = client.list_pages_with_ig()
    for p in pages:
        ig_obj = p.get("instagram_business_account") or {}
        if ig_obj.get("id"):
            return str(ig_obj["id"])
    raise GraphError(
        "no Instagram Business Account linked to any Page on this token. "
        "Pass --user-id explicitly."
    )


# ---- business discovery ---------------------------------------------------

@ig.command("business-discovery")
@click.argument("ig_id")
@click.option("--username", required=True, help="Public IG username to inspect.")
@click.option("--fields",
              default="username,followers_count,follows_count,media_count,biography,name,profile_picture_url,website",
              show_default=False)
@click.pass_context
def business_discovery(ctx: click.Context, ig_id: str, username: str, fields: str) -> None:
    """Public profile of any IG Business/Creator by username (read-only)."""
    client = build_client(ctx.obj)
    try:
        result = client.get(
            f"/{ig_id}",
            fields=f"business_discovery.username({username}){{{fields}}}",
        )
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


# ---- oembed ---------------------------------------------------------------

@ig.command("oembed")
@click.argument("url")
@click.option("--maxwidth", type=int, default=None)
@click.option("--omit-script", is_flag=True, default=False)
@click.pass_context
def oembed(ctx: click.Context, url: str, maxwidth: int | None, omit_script: bool) -> None:
    """Get embed code for a public IG post URL.

    Requires an app + app token (token = '<app_id>|<app_secret>').
    """
    client = build_client(ctx.obj)
    params: dict[str, Any] = {"url": url}
    if maxwidth:
        params["maxwidth"] = maxwidth
    if omit_script:
        params["omit_script"] = "true"
    try:
        result = client.get("/instagram_oembed", **params)
    except GraphError as e:
        handle_graph_error(e)
        return
    emit(result, pretty=ctx.obj.get("pretty", False), jq=ctx.obj.get("jq"))


def register(group: click.Group) -> None:
    group.add_command(ig)
