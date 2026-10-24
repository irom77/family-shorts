#!/usr/bin/env bash
# Render shorts one at a time (memory) and copy each to the tape's Windows Shorts folder.
# usage: render_all.sh <tape-dir> NN [NN...]     log: <tape-dir>/plan/render_all.log
# Never run it next to enhance jobs or a hyperframes check: Chrome + ffmpeg together OOM WSL.
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/tape.sh" "$1"; shift
cd "$TAPE_DIR"; mkdir -p "$OUT_DIR"
for n in "$@"; do
  f=$(python3 -c "import json;print(json.load(open('plan/copy.json'))['$n']['file'])")
  echo "$(date +%T) render short$n"
  (cd short$n && npx --yes hyperframes@0.8.190 render -o renders/short$n.mp4 --fps 30 --quality delivery --no-browser-gpu < /dev/null) > plan/render_$n.log 2>&1 \
    && cp short$n/renders/short$n.mp4 "$OUT_DIR/$f" && cmp -s short$n/renders/short$n.mp4 "$OUT_DIR/$f" \
    && echo "$(date +%T) DONE short$n -> $f" || echo "$(date +%T) FAIL short$n (see plan/render_$n.log)"
done
echo ALLDONE
