#!/usr/bin/env bash
# Download one old upload from the channel and set up its work folder for the family-shorts scripts.
# usage: fetch.sh <video-id> <slug> <year>
#   -> $ARCHIVE/YouTube/<video-id>.mkv (+ .info.json), work/yt_<slug>/plan/tape.json
# YouTube keeps only its own re-encode; the original upload file can't be fetched through the API.
# Unlisted and public videos download without signing in; a private one has to be made unlisted first.
set -euo pipefail
ID="$1"; SLUG="$2"; YEAR="$3"
REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
. "$REPO/local.env"
DEST="$ARCHIVE/YouTube"; mkdir -p "$DEST"
if [ ! -s "$DEST/$ID.mkv" ]; then
  uvx yt-dlp@latest -q --no-warnings -f "bv*+ba/b" --merge-output-format mkv --write-info-json \
    --ffmpeg-location "$(dirname "$(command -v ffmpeg)")" -o "$DEST/%(id)s.%(ext)s" \
    "https://www.youtube.com/watch?v=$ID" < /dev/null
fi
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate:format=duration -of compact "$DEST/$ID.mkv"
W="$REPO/work/yt_$SLUG"; mkdir -p "$W/plan" "$W/scan"
[ -f "$W/plan/tape.json" ] || python3 - "$W/plan/tape.json" "$DEST/$ID.mkv" "$SHORTS/yt_$SLUG" "$YEAR" "$CHANNEL" "$ID" "$SLUG" <<'PY'
import json, sys
f, src, out, year, ch, vid, slug = sys.argv[1:]
json.dump({"tape": f"yt_{slug}", "source": src, "out_dir": out, "end_en": f"Family archive · {year}",
           "channel": ch, "youtube_source": vid}, open(f, "w"), indent=2, ensure_ascii=False)
PY
echo "ready: $W"
