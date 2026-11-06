---
name: family-catalog
description: Use when the user wants a list, page, catalog or index of the family YouTube channel's videos to share with family or friends by email or a messaging app, wants to refresh it after new uploads, open it from an iPhone Home Screen, or wants to leave a video out of it.
---

# Family video catalog

One self-contained HTML page lists every public and unlisted video on the family channel, grouped by
playlist (oldest year first), with a search box. Thumbnails are embedded. Tapping a video opens it in
the YouTube app. The same page goes out two ways:

- **The site (main way):** on Cloudflare Pages at `https://$CF_PROJECT.pages.dev/$CATALOG_PATH/`. The
  address is the only protection, like an unlisted video: no sign-in, nothing listed or indexed, and
  the site root shows nothing. Family keep one link and can put it on their Home Screen with its icon.
- **The file:** `$ARCHIVE/Catalog/Archiwum_rodzinne.html`, to send as an attachment if wanted.

`<skill>` below means this skill's folder (`/home/irom/archive/.claude/skills/family-catalog`).
`$ARCHIVE`, `$CHANNEL`, `$ALL_PLAYLIST`, `$CF_PROJECT` and `$CATALOG_PATH` come from
`/home/irom/archive/local.env` (not in git). Never write the site address, the project name or the
path into a tracked file, and never host the page from a public repo or under a guessable address.

## Build or refresh

Run from the repo root after `source local.env`:

```bash
PYTHONUNBUFFERED=1 uv run -q --no-project --with google-api-python-client --with google-auth-oauthlib \
  python -u <skill>/scripts/catalog.py --expect-channel "$CHANNEL" \
  --out "$ARCHIVE/Catalog/Archiwum_rodzinne.html" --site "$ARCHIVE/Catalog/site" --site-path "$CATALOG_PATH" \
  --skip "$ARCHIVE/Catalog/skip.txt" --all-playlist "$ALL_PLAYLIST" --news "$ARCHIVE/Catalog/news.json"
```

- **Sign-in:** the same token as family-shorts. On an auth error, use the sign-in command in that skill.
- **Run it after uploads finish**, not while an uploader runs, so the newest shorts are in their playlists.
- **Thumbnails:** YouTube makes a new upload's thumbnail a few minutes after the upload. The build
  waits up to 15 minutes for missing ones. It prints `NO THUMBNAIL` for any still missing; those cards
  show a plain tile, so rebuild later.
- **News:** `--news` keeps a log between builds (not in git). Under the title, the page shows a
  "Nowości / What's new" box with the build date and the last three days with changes in the past
  30 days. Each line links to its playlist's section. Cards added in the last 7 days get a "Nowe"
  badge. A re-upload with the same title as a video that left the catalog counts as "poprawione /
  fixed", not as new. The first build seeds the log from upload dates. Always pass the same file:
  with a new one, the news starts over from upload dates and misses re-uploads.
- **Home Screen:** the site page has its icon (`assets/icon.png`, titled "Archiwum"). An attachment
  can't become a Home Screen icon.
- **Leave videos out:** add their ids to `$ARCHIVE/Catalog/skip.txt`, one per line (`#` starts a comment).
  Videos in no playlist appear under "Inne / Other"; check that section with the user.
- **All-videos playlist:** `--all-playlist` keeps one unlisted playlist complete, and the page gets a
  button for it. Its id is `$ALL_PLAYLIST`.
- **Quota:** a few list calls, plus 50 units per video added to the all-videos playlist (from the
  10,000-unit daily pool), so a first fill of about 100 videos uses half of a day's pool.

## Publish

Only after the check below, and only when the user asks to publish. Run from an empty scratch folder,
never from `~` or a project folder:

```bash
npx --yes wrangler@4.151.0 pages deploy "$ARCHIVE/Catalog/site" --project-name "$CF_PROJECT" \
  --branch main --commit-dirty=true
```

- **The project already exists** on the user's Cloudflare account. Never run `wrangler pages project
  create` or `wrangler deploy`. In wrangler 4.15x, `pages project create` hands over to Workers
  auto-setup. In `~` that wrote `~/wrangler.jsonc` and tried to publish an unrelated project folder as
  a public Worker. It failed only on a file-size limit. If the project is ever gone, create it with
  the API: `POST /accounts/<id>/pages/projects` with `{"name": "$CF_PROJECT", "production_branch": "main"}`.
- **Sign-in:** if wrangler says it is not authenticated, the user runs
  `! cd ~ && npx --yes wrangler@4.151.0 login`. The login can land in `~/.config/.wrangler/config/`
  while wrangler reads `~/.wrangler/config/` once that folder exists. If so, copy `default.toml` across.
- **Verify:** `curl -s -o /dev/null -w '%{http_code}'` gives 200 for `…pages.dev/$CATALOG_PATH/` and
  404 for the site root and for a made-up path.
- **Old deployments** keep their own `<hash>.$CF_PROJECT.pages.dev` addresses, under the same secret path.
  If the secret path ever leaks, pick a new `CATALOG_PATH`, rebuild, deploy, send family the new link,
  and delete the old deployments in the Cloudflare dashboard.

## Check, then hand over

- Screenshot at phone width with a local headless Chrome (the Playwright MCP may lack Chrome):
  `chrome-headless-shell --no-sandbox --hide-scrollbars --window-size=390,1700 --screenshot=<png> file://<html>`.
  Look at it: the cards, titles and section counts should be right.
- The page must work without JavaScript, because email and messaging previews on iPhone may not run it.
  Navigation uses plain anchors; the search box shows only when scripts run.
- Tell the user what changed since the last build, the site link (from `local.env`) once published,
  and the file path and size (about 18 KB per video). Sending the link or file is theirs to do.
