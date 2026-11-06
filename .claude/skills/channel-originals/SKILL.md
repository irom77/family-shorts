---
name: channel-originals
description: Use when the user wants Shorts made from old long videos already on the family YouTube channel (uploaded years ago, before the tape shorts), wants those old uploads listed, downloaded, catalogued or grouped into playlists, or names an old channel video by its title and asks for shorts from it.
---

# Old channel videos → Shorts

Some family videos exist only as old long uploads on the channel. The original tape or file is gone,
or nobody knows where it is. This skill gets the best copy YouTube still holds and hands it to the
`family-shorts` pipeline, which does the scanning, enhancing, rendering and uploading. Read that skill
too; its fixed rules (format, captions, no names, no reuse, review, unlisted) all apply here.

`<skill>` below means this skill's folder (`/home/irom/archive/.claude/skills/channel-originals`) and
`<fs>` means `/home/irom/archive/.claude/skills/family-shorts`. `$ARCHIVE`, `$SHORTS` and `$CHANNEL`
come from `/home/irom/archive/local.env`.

## Rules

- **Never change the old upload.** Don't delete it, edit it, or change its privacy unless the user
  asks. The shorts are new videos next to it.
- **Ask about a better source first.** If the user still has the tape, a capture or the original
  file, use that instead (as a normal `family-shorts` tape). The YouTube copy is a re-encode, often
  only 320x240 for uploads from around 2010–2014.
- **Snapshots:** `--describe false`, as always.

## 1. Find the videos

```bash
uv run -q --no-project --with google-api-python-client --with google-auth-oauthlib \
  python <skill>/scripts/list_long.py --expect-channel "$CHANNEL"
```

One line per non-Short video, oldest first: id, upload date, length, privacy, the file name it was
uploaded from, title. Match the user's titles to ids. The file name hints at what the source was
(`.flv` from an old web editor, `.MOV` from a phone).

## 2. Download and set up

```bash
<skill>/scripts/fetch.sh <video-id> <slug> <year>
```

- Saves `$ARCHIVE/YouTube/<video-id>.mkv` and its `.info.json`. This copy stays in the archive: it
  may be the only one off YouTube.
- Writes `work/yt_<slug>/plan/tape.json` with `out_dir` `$SHORTS/yt_<slug>`. The slug is a short
  local label (it can name the occasion; `work/` is not in git).
- The year goes into the end card. Fix it, and the dates in the copy, from the camera's date stamp
  once the scan shows it.
- A private video doesn't download without signing in. Ask the user to make it unlisted for the
  download, or to download it from YouTube Studio themselves.

## 3. Make the shorts

Follow `family-shorts` steps 1–5 on `work/yt_<slug>` (scan, plan, storyboard, enhance, build, render,
manifest). Differences for these sources:

- **Branding:** uploads from old web editors start and end with the editor's logo (a few seconds
  each). Keep shots out of them; the scan sheets show where they are.
- **Enhancement:** `enhance.sh` recognises a 320x240 source and uses a light deblock and denoise. The
  DV-strength denoise turns faces waxy at this size. Compare one enhanced still with a plain upscale
  of the same frame before the batch: blotches or smears that are in both come from the old upload.
- **Fewer, tighter shorts:** a 10-minute upload gives about 4–5 shorts without reusing a scene.
- **Description:** say it was restored from an old copy (`Nagranie z kasety wideo, odrestaurowane ze
  starej kopii.` / `Restored from an old copy of a home video tape.`), not from a DV tape.

**Done when:** the shorts are rendered, checked and in `$SHORTS/yt_<slug>/manifest.json`, and the user
has been told the folder and that the picture is limited by the old copy.

## 4. Upload, playlists, catalog

- **Upload** only when the user says so: `family-shorts` step 6, unlisted by default, minding the
  ~10-uploads-per-24 h channel cap across all manifests.
- **Playlists:** by default one unlisted playlist per old video, created with
  `yt_family.py playlist` from its manifest after the uploads finish. Titles follow the shorts' style
  (occasion and year, Polish | English, no names of people or places unless the user asks).
- **Catalog:** afterwards, refresh the family catalog (`family-catalog` skill) so the new playlists
  show up, and ask whether to publish it.
