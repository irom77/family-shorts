#!/usr/bin/env bash
# Stills at the start, middle and end of every segment of one short, one row per segment,
# to check in/out points before spending time on enhancement.
# usage: verify_sheet.sh <tape-dir> NN   -> <tape-dir>/plan/verify/sheet_NN.jpg
set -euo pipefail
. "$(dirname "$0")/tape.sh" "$1"; N="$2"
V="$TAPE_DIR/plan/verify"; mkdir -p "$V"; rm -f "$V/${N}_"*.jpg
while IFS=$'\t' read -r id a b note; do
  for p in s m e; do
    case $p in s) t=$(echo "$a+0.15" | bc);; m) t=$(echo "($a+$b)/2" | bc -l);; e) t=$(echo "$b-0.15" | bc);; esac
    ffmpeg -nostdin -v error -y -ss "$t" -i "$SRC" -frames:v 1 -vf "scale=240:160" "$V/${N}_${id}_$p.jpg"
  done
done < "$TAPE_DIR/plan/short$N.tsv"
ffmpeg -nostdin -v error -y -pattern_type glob -i "$V/${N}_*_[sme].jpg" \
  -vf "tile=3x$(wc -l < "$TAPE_DIR/plan/short$N.tsv"):padding=2:color=red" -frames:v 1 "$V/sheet_$N.jpg"
echo "$V/sheet_$N.jpg"
