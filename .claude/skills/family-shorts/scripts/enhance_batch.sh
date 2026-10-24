#!/usr/bin/env bash
# Enhance every segment of the given shorts: at most 3 at a time (each ffmpeg peaks ~1.5 GB;
# more OOM-kills WSL), skipping clips that already exist, then decode-check every clip.
# usage: enhance_batch.sh <tape-dir> NN [NN...]     log: <tape-dir>/plan/enhance.log
# Run detached:  nohup setsid enhance_batch.sh <tape-dir> 09 10 > /dev/null 2>&1 < /dev/null &
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/tape.sh" "$1"; shift
export HERE SRC
LOG="$TAPE_DIR/plan/enhance.log"; : > "$LOG"
for n in "$@"; do
  mkdir -p "$TAPE_DIR/clips/short$n"
  while IFS=$'\t' read -r id a b note; do
    out="$TAPE_DIR/clips/short$n/seg_$id.mp4"
    [ -s "$out" ] || printf '%s\t%s\t%s\n' "$a" "$(echo "$b-$a" | bc)" "$out"
  done < "$TAPE_DIR/plan/short$n.tsv"
done | xargs -P3 -d '\n' -I{} bash -c 'IFS=$'"'"'\t'"'"' read -r a d o <<< "{}"; "$HERE/enhance.sh" "$SRC" "$a" "$d" "$o" < /dev/null || { echo "FAIL $o"; rm -f "$o"; }' >> "$LOG" 2>&1
for n in "$@"; do for f in "$TAPE_DIR/clips/short$n"/seg_*.mp4; do
  e=$(ffmpeg -nostdin -v error -i "$f" -f null - 2>&1 | wc -l)
  [ "$e" = 0 ] || { echo "CORRUPT $f ($e errors) - deleted, rerun to redo" >> "$LOG"; rm -f "$f"; }
done; done
echo ALLDONE >> "$LOG"
