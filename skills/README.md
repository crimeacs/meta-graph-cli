# `meta-graph` Claude Code skill

A Claude Code [Skill](https://www.anthropic.com/news/claude-skills) that teaches Claude how to operate the [`meta-graph`](https://github.com/crimeacs/meta-graph-cli) CLI to work with Meta's Graph API and Instagram Graph API.

When this skill is installed, conversational requests like:

- "Post this image to Instagram with caption '…'"
- "Show me reach on my last 10 posts"
- "Reply to all unanswered comments on this Reel"
- "What's the most-liked recent media for #espresso?"
- "Decode this access token"

…will trigger Claude to use the `meta` CLI directly, instead of asking you for `curl` snippets or hand-rolling Graph API URLs.

## Install

### Prerequisite

```bash
pip install meta-graph
export META_GRAPH_TOKEN="EAA..."   # from https://developers.facebook.com/tools/explorer/
```

(Or use a config file — see [auth docs](../docs/auth.md).)

### For Claude Code (user-global)

```bash
mkdir -p ~/.claude/skills
cp -r skills/meta-graph ~/.claude/skills/
```

Restart Claude Code (or open a new session) to pick it up.

### For Claude Code (project-local)

```bash
mkdir -p .claude/skills
cp -r path/to/meta-graph-cli/skills/meta-graph .claude/skills/
```

Then commit the skill folder if your team should share it.

### For Claude.ai

1. Zip the `meta-graph` folder.
2. Open Claude.ai → Settings → Capabilities → Skills.
3. Upload the zip.
4. Toggle the skill on.

## What it does

- Recognizes Instagram / Meta Graph API tasks in natural language.
- Runs `which meta` and offers to install if missing.
- Resolves your IG Business Account id via `meta ig accounts` before any IG operation.
- Walks the publish container flow (create → poll status → media_publish) for you.
- Maps Meta error codes (190, 200, 4, 100, 9004, 36003 …) to actionable fixes.
- Falls back to generic `meta get/post/delete` for anything not curated.
- Greps the bundled `docs/reference.md` (4.2 MB of Graph + IG endpoints) before guessing field names.

## What it deliberately does NOT do

- Run an OAuth flow in your browser (that's outside Claude Code's scope).
- Generate post creatives or copy (that's a different skill).
- Wrap Meta's official Python SDK (the CLI uses raw HTTP for version-agility).

## License

MIT — same as the CLI.
