---
name: family-shorts
description: Turn a family DV tape (NTSC or PAL .avi from the Romaniuk archive) into restored 9:16 YouTube Shorts with bilingual Polish/English titles, render them with HyperFrames, and upload them to @irom77. Use when the user wants shorts/clips/reels from a tape, asks to make the next tape (002, 003, 005–008), re-render or re-caption a short, upload or change privacy of a family short, or compare the PAL/NTSC copies of a tape.
---

# Family archive → YouTube Shorts

One tape becomes several 45–90 s vertical shorts. Picking the moments, writing the captions and
reviewing the frames is your job. Scanning, enhancement, project building, rendering, manifests and
upload are scripts in `scripts/`; `<skill>` below means this skill's folder
(`/home/irom/archive/.claude/skills/family-shorts`).

## Fixed rules (the user chose these; don't change them without asking)

- **Format:** 1080x1920, blur-fill: the full 4:3 picture at y=520..1320 over a blurred copy of itself.
- **Captions:** bilingual, Polish main line with an English subtitle. Each short has a title (occasion
  plus date) over the first 6 s, 0–2 sparse chapter captions, and an end card ("Archiwum rodzinne")
  over the last 8 s.
- **No names.** Never name people or places in captions, titles or descriptions.
- **Audio and length:** original camcorder audio, cleaned and loudness-normalised, no music. Target
  45–90 s; hard limits 30–180 s.
- **No reuse:** a scene goes into at most one short. The ledger is `plan/shortNN.tsv`, and earlier
  shorts' TSVs are the record of what's taken.
- **Review before upload:** show the user the storyboard (shot list plus captions) before enhancing.
  Upload only after the user says so explicitly, with the privacy they name; when they name none, use `unlisted` (the user's default since 2026-10-25: watchable by anyone with the link, not listed in search or on the channel). Playlists are unlisted too, since a public playlist would expose the unlisted videos in it.
  Don't upload anything sensitive, such as undressed children (short 08 of tape 001 was kept off
  YouTube for this reason).
- **Snapshots:** always `--describe false`. Without it, frames go to Gemini.

## Folders

| What | Where |
|---|---|
| Sources | `/mnt/c/Users/irekr/Videos/Archive/99199_Romaniuk PAL DV Files/` and `… NTSC DV Files/` |
| Working files per tape | `/home/irom/archive/work/<tape>/` (`plan/`, `scan/`, `clips/`, `shortNN/`) |
| Finished MP4s + `manifest.json` | `/mnt/c/Users/irekr/Videos/Archive/Shorts/<tape>_<yyyy-mm-dd>/` |

**Which source:**

- **Tapes 001–003:** the "PAL"-folder file is really NTSC DV, but one generation earlier than the
  "NTSC"-folder copy and slightly sharper. Use the "PAL"-folder file.
- **Tapes 005–008:** the two folders hold independent captures. The PAL one is sharper with better
  colour; the NTSC one keeps the full 60 fields/s motion. Default to PAL.
- **Unsure:** run `scripts/compare_pair.sh <P.avi> <N.avi> <outdir>` (about 30 min per tape).
  Results are in `work/compare/<tape>/summary.txt`. The 008 run was stopped early. 005–007 were
  compared with an older version of the script, so read their `summary.txt` for the resolution and
  frame rate only.

## Workflow

Every script takes the tape folder (`work/<tape>`) first and reads `plan/tape.json` from it:

```json
{ "tape": "002", "source": "/mnt/c/.../002_15,08,1993_Chrzest_Oli.avi",
  "out_dir": "/mnt/c/Users/irekr/Videos/Archive/Shorts/002_1993-08-15",
  "end_en": "Family archive · 1993", "channel": "UCBoriY5wyxsxBh09ctbyvnw" }
```

### 1. Scan the tape

Takes about 15–25 min.

```bash
nohup setsid <skill>/scripts/scan.sh work/<tape> > work/<tape>/scan/run.log 2>&1 < /dev/null &
```

It writes `scan/sheets/sheet_NN.jpg`: 10x8 thumbs, one every 2 s, 160 s per sheet. Thumb k of
sheet N is at `(N-1)*160 + 2k` s. It also writes `scan/cuts.txt` (scene cuts in seconds) and
`scan/rms.txt` (loudness per second).

Read every sheet. Write a short list of the tape's events with time ranges.

**Done when:** every sheet has been read and the event list covers the whole tape.

### 2. Plan the shorts

Write one short per event or theme.

- **`plan/shortNN.tsv`** (number shorts on from the last short of this tape): one shot per line, as
  `id<TAB>in_s<TAB>out_s<TAB>note`. Shots are 4–12 s each, start and end on clean frames, and use ids
  unique within the tape (a letter per short plus a number: `b01`, `c03`).
- **`plan/copy.json`** gets one entry per short:

```json
"09": { "file": "short_09_<slug>.mp4",
        "title": { "pl": "Tort", "date": "3 maja 1996", "en": "The cake · May 3, 1996" },
        "captions": [ { "id": "cap-candles", "at": "c03", "pl": "Zdmuchnij świeczki!", "en": "Blow out the candles!" } ],
        "yt_title": "Tort · 3 maja 1996 | The cake, 1996 #shorts",
        "yt_desc": "Archiwum rodzinne: … Nagranie z kasety DV, odrestaurowane.\nFamily archive: … Restored from DV tape.\n\n#shorts #archiwum #1996 #familyarchive #homevideo",
        "tags": ["…", "archiwum rodzinne", "family archive", "home video", "dv tape", "shorts"] }
```

A caption covers its whole shot (`at`). It must not sit under the title (first 6 s) or the end card
(last 8 s); `make_short.py` refuses if it does.

Check the cut points:

```bash
<skill>/scripts/verify_sheet.sh work/<tape> NN
```

This writes start, middle and end stills of every shot. Read the sheet; move any in or out point that
lands on a cut, a blank frame or the VCR ▶ marker (first ~1.5 s of a tape). Then show the user the
storyboard.

**Done when:**
- every short is 30–180 s;
- no shot overlaps a shot in any other TSV of the tape;
- every verify sheet is clean;
- the user has seen the storyboard.

### 3. Enhance the shots

Takes about 1 min per 10 s shot, 3 at a time.

```bash
nohup setsid <skill>/scripts/enhance_batch.sh work/<tape> 09 10 11 > /dev/null 2>&1 < /dev/null &
```

Wait for `ALLDONE` in `plan/enhance.log`. It skips shots that already exist, and it deletes and
reports any clip that fails to decode. Rerun the same command until the log has no `FAIL` or
`CORRUPT` lines. Lines like `AC EOB marker is absent` / `Concealing bitstream errors` are dropouts on
the tape itself, not failures.

### 4. Build, check and look

```bash
<skill>/scripts/make_short.py work/<tape> 09 10 11
cd work/<tape>/short09 && npx --yes hyperframes@0.8.190 check --json --no-browser-gpu
npx --yes hyperframes@0.8.190 snapshot --at 1,<caption s>,<end-4 s> --describe false
```

Fix every check error, then read the snapshots: title, each caption and the end card must be legible.
To change the look, edit the templates in `make_short.py` and rebuild, not the generated HTML.

**Done when:** check passes, and the snapshots of each short have been looked at.

### 5. Render

Renders take about 5–8 min per short, one at a time.

```bash
nohup setsid <skill>/scripts/render_all.sh work/<tape> 09 10 11 > work/<tape>/plan/render_all.log 2>&1 < /dev/null &
<skill>/scripts/manifest.py work/<tape> 09 10 11
```

`render_all.sh` copies each render to `out_dir` and verifies the copy. `manifest.py` adds the shorts
to `out_dir/manifest.json` as private.

Check each MP4:
- 1080x1920 h264 + aac;
- `ffmpeg -v error -i f -f null -` prints nothing;
- loudness about -16 LUFS;
- a 5-frame contact sheet looks right.

**Done when:** every MP4 passes these checks and is listed in the manifest.

### 6. Upload

Upload only when the user asks.

```bash
nohup setsid <skill>/scripts/upload.sh work/<tape> unlisted 09 10 > work/<tape>/plan/upload.log 2>&1 < /dev/null &
```

- **Quota:** videos.insert has its own bucket of 100 calls per day per Cloud project, separate from the 10,000-unit pool for other calls (the pool still pays for the `privacy` updates).
- **Channel cap:** separately from quota, YouTube refuses with `uploadLimitExceeded` after about
  10 uploads per rolling 24 h on @irom77 (hit on 2026-10-25). Count the `uploaded_at` times in all
  manifests before a batch; upload the rest once the oldest upload in the window is 24 h old.
- **What it writes:** the uploader records each video's id, URL and channel in the manifest.
- **Check:** `curl -s -o /dev/null -w '%{http_code}' "https://www.youtube.com/oembed?url=<url>"`
  should give 200 for public and unlisted videos.
- **Playlist per tape:** after the uploads finish (not while they run — both write the manifest),
  `yt_family.py playlist --manifest … --title "…" --description "…" --expect-channel UCBoriY5wyxsxBh09ctbyvnw`
  creates the playlist once, records it in the manifest and adds any uploaded short not yet in it,
  in manifest order. Rerun it after later uploads. No names of people or places in the title.
- **Change privacy later:** `yt_family.py privacy --manifest … --short short_NN --privacy unlisted --expect-channel UCBoriY5wyxsxBh09ctbyvnw`.
- **Sign-in:** the OAuth app is in testing mode, so the token lasts about 7 days. On an auth error the
  user re-signs in with:
  `! uv run --no-project --with google-api-python-client --with google-auth-oauthlib python <skill>/scripts/yt_family.py auth --from-token ~/.config/family-archive-youtube/token.json`

Report the links to the user.

**Done when:** every requested short has a youtube record in the manifest and its oembed returns 200.

## Machine limits (learned the hard way)

- **Memory:** WSL has about 15 GB and VS Code holds about 7 GB. Run at most 3 enhance jobs at once,
  and never alongside `hyperframes check`, `snapshot` or `render`. Six parallel jobs OOM-killed the
  WSL session twice.
- **Long jobs:** start every job longer than about 2 min with `nohup setsid … < /dev/null &`, so a
  dropped session doesn't kill it.
- **stdin:** background `ffmpeg` in a shell loop eats stdin and corrupts clips. The scripts pass
  `-nostdin` or `< /dev/null`; keep doing that in anything new.
- **The local static ffmpeg 7.0.2:**
  - It asserts on large multi-output analysis graphs, so use single-purpose passes.
  - It has no `drawtext`.
- **Killing jobs:** never `pkill -f` a pattern that also matches your own shell. Kill by PID.
- **Christening tapes:** expect single bright fields from photo flashes. They are in the source, not
  a bug.
