# Family archive

Tools and Claude Code skills for restoring the Romaniuk family DV tapes and publishing them.

- **Sources** (Windows): `C:\Users\irekr\Videos\Archive\99199_Romaniuk PAL DV Files\` and
  `…\99199_Romaniuk NTSC DV Files\`.
- **Working files:** `work/<tape>/` in this repo (WSL: `/home/irom/archive`).
- **Finished videos:** `C:\Users\irekr\Videos\Archive\Shorts\<tape>_<date>\`.

## Skills

Skills live in `.claude/skills/<name>/`. Claude Code loads them automatically when it is started in
this folder. You can call a skill by name (`/family-shorts`), or describe the job in plain words and
Claude picks the matching skill.

| Skill | What it does | Say something like |
|---|---|---|
| [`family-shorts`](.claude/skills/family-shorts/SKILL.md) | One DV tape → restored 9:16 YouTube Shorts with Polish/English captions, rendered with HyperFrames and uploaded to @irom77 | "make shorts from tape 002", "upload shorts 09–11", "make short 05 unlisted" |

### family-shorts

**What it makes.** Each tape becomes several 45–90 s vertical shorts:

- **Picture:** blur-fill framing (the full 4:3 picture over a blurred copy of itself), restored by
  deinterlacing, stabilising, denoising and upscaling.
- **Sound:** the original camcorder audio, cleaned and normalised. No music.
- **Text:** a Polish title with an English subtitle, at most two short captions, and an end card.
  No people or places are named.
- **No repeats:** no scene appears in two shorts.

**How a session goes.**

1. **Ask:** start Claude Code in this folder and say e.g. *"make shorts from tape 002"*.
2. **Scan:** Claude scans the tape (about 20 min) and reads contact sheets of the whole tape.
3. **Storyboard:** Claude proposes a storyboard: the shorts, their shots with timecodes, and the
   captions. Adjust anything here; this is the cheap moment to change your mind.
4. **Make:** Claude enhances the shots, builds and checks the HyperFrames projects, and renders them.
   The MP4s and a `manifest.json` appear in the tape's Shorts folder.
5. **Review:** watch them there.
6. **Upload:** say *"upload shorts 09–11"* (unlisted unless you name private or public). Nothing is uploaded
   without this. You get the links back.

**Limits worth knowing.**

- **Uploads:** YouTube allows **100 uploads per day** on this project (videos.insert has its own quota bucket).
- **YouTube sign-in:** it expires after about **7 days**, because the Google app is in testing mode.
  When it does, Claude asks you to run the sign-in command; it opens a browser.
- **Pace:** enhancement and rendering are CPU-heavy and memory-limited in WSL. Expect 1–2 hours of
  machine time per tape, and avoid heavy work in VS Code meanwhile.

**Which copy of a tape is used.** For tapes 001–003 the "PAL" folder holds the better copy of the same
NTSC recording; the "NTSC" copies of 001–003 are redundant. For tapes 005–008 the two folders are
separate captures (PAL is sharper; NTSC has smoother motion), so keep both. Details are in
`work/compare/<tape>/summary.txt`.

**Scripts** (in `.claude/skills/family-shorts/scripts/`; each takes the tape folder `work/<tape>`
first and reads its `plan/tape.json`):

| Script | Job |
|---|---|
| `scan.sh` | Contact sheets, scene cuts and loudness for a whole tape |
| `verify_sheet.sh` | Start/middle/end stills of every shot of one short |
| `enhance.sh` / `enhance_batch.sh` | Restore shots to 1080x1920 clips (NTSC or PAL), 3 at a time |
| `make_short.py` | Build a HyperFrames project from `plan/shortNN.tsv` + `plan/copy.json` |
| `render_all.sh` | Render one by one and copy to the Shorts folder |
| `manifest.py` | Add rendered shorts to the folder's `manifest.json` |
| `upload.sh` / `yt_family.py` | Upload to YouTube, change privacy |
| `compare_pair.sh` | Compare a tape's "PAL" and "NTSC" copies |

`tools/yt_family.py` and `tools/compare_pair.sh` are links to the skill's copies. `work/001/scripts/`
holds the original tape-001 versions and is kept for reference only.

**Status.** All uploads are unlisted (changed 2026-10-25). Tape 001: shorts 01–07 uploaded, 08 kept offline. Tape 002: shorts 01–06 uploaded. Tape 005: shorts 01–04 uploaded and in a playlist; 05 waits for the channel upload cap. Links are in
`C:\Users\irekr\Videos\Archive\Shorts\001_1996-05-03\manifest.json`.

## Adding a skill

Create `.claude/skills/<name>/SKILL.md` with `name` and `description` front matter. The description
says when Claude should use the skill. Put helper scripts in `scripts/` next to it, and add a row to
the table above plus a short section on how to use it.
