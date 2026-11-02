---
name: family-catalog
description: Use when the user wants a list, page, catalog or index of the family YouTube channel's videos to share with family or friends by email or a messaging app, wants to refresh it after new uploads, open it from an iPhone Home Screen, or wants to leave a video out of it.
---

# Family video catalog

One self-contained HTML file lists every public and unlisted video on the family channel, grouped by
playlist (oldest year first), with a search box. Thumbnails are embedded, so it works as an email or
messaging attachment with nothing hosted and no sign-in. Tapping a video opens it in the YouTube app.
`<skill>` below means this skill's folder (`/home/irom/archive/.claude/skills/family-catalog`).
`$ARCHIVE`, `$CHANNEL` and `$ALL_PLAYLIST` come from `/home/irom/archive/local.env` (not in git).

The user does not want a hosted web page, public or behind a sign-in. Don't propose hosting.

## Build or refresh

Run from the repo root after `source local.env`:

```bash
PYTHONUNBUFFERED=1 uv run -q --no-project --with google-api-python-client --with google-auth-oauthlib \
  python -u <skill>/scripts/catalog.py --expect-channel "$CHANNEL" \
  --out "$ARCHIVE/Catalog/Archiwum_rodzinne.html" --skip "$ARCHIVE/Catalog/skip.txt" \
  --all-playlist "$ALL_PLAYLIST"
```

- **Sign-in:** the same token as family-shorts. On an auth error, use the sign-in command in that skill.
- **Run it after uploads finish**, not while an uploader runs, so the newest shorts are in their playlists.
- **Leave videos out:** add their ids to `$ARCHIVE/Catalog/skip.txt`, one per line (`#` starts a comment).
  Videos in no playlist appear under "Inne / Other"; check that section with the user.
- **Home Screen:** an attachment can't become a Home Screen icon. For that, `--all-playlist` keeps one
  unlisted "all videos" playlist complete. Its link opens in YouTube, and Safari can add it to the Home
  Screen. The page also gets a button for it. Its id is `$ALL_PLAYLIST`.
- **Quota:** a few list calls, plus 50 units per video added to the all-videos playlist (from the
  10,000-unit daily pool), so a first fill of about 100 videos uses half of a day's pool.

## Check, then hand over

- Screenshot at phone width with a local headless Chrome (the Playwright MCP may lack Chrome):
  `chrome-headless-shell --no-sandbox --hide-scrollbars --window-size=390,1700 --screenshot=<png> file://<html>`.
  Look at it: the cards, titles and section counts should be right.
- The page must work without JavaScript, because email and messaging previews on iPhone may not run it.
  Navigation uses plain anchors; the search box shows only when scripts run.
- Tell the user the file path, its size (about 18 KB per video), and what changed since the last build.
  Sending the file is theirs to do.
