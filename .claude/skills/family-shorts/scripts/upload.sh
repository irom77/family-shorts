#!/usr/bin/env bash
# Upload shorts listed in the tape's manifest.json to @irom77. Only after the user said so.
# usage: upload.sh <tape-dir> <private|unlisted|public> NN [NN...]   log: <tape-dir>/plan/upload.log
# videos.insert has its own quota bucket: 100 uploads per day per Cloud project.
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/tape.sh" "$1"; PRIV="$2"; shift 2
cd /tmp   # uv must not pick up a project from the tape folder
for n in "$@"; do
  echo "$(date +%T) short_$n"
  PYTHONUNBUFFERED=1 uv run -q --no-project --with google-api-python-client --with google-auth-oauthlib python -u \
    "$HERE/yt_family.py" upload --manifest "$OUT_DIR/manifest.json" --short "short_$n" --privacy "$PRIV" \
    --expect-channel "$CHANNEL" 2>&1 | grep -vE '^uploaded [0-9]+%$' | tail -3
done
echo ALLDONE
