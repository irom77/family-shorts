#!/usr/bin/env bash
# Turn what recover.sh saved into things a person can judge:
#  - each video (VCD .DAT, SVCD .MPG, a DVD title's VOBs joined, or any other video file) -> <name>_recovered.mp4
#    (H.264 CRF 16 at the source resolution, AAC 192k), a contact sheet <name>_sheet.jpg (42 frames spread
#    over the whole video) and a per-minute damage table in <name>_damage.txt;
#  - photos -> damaged.txt lists any that fail to decode.
# Decoder errors per minute are a better damage measure than the bad-sector count: video sectors on a Video
# CD have no error correction, so most damage reads back silently as corrupt data.
# Usage: review.sh DEST
set -uo pipefail
DEST=$1; cd "$DEST"
shopt -s nullglob nocaseglob globstar

convert() {  # convert NAME INPUT...
  local name=$1; shift; local in
  if [ $# -gt 1 ]; then in="concat:$(IFS='|'; echo "$*")"; else in=$1; fi
  [ -s "${name}_recovered.mp4" ] || ffmpeg -nostdin -v quiet -y -fflags +genpts+discardcorrupt -err_detect ignore_err -i "$in" \
      -map 0:v:0 -map '0:a:0?' -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k \
      -movflags +faststart "${name}_recovered.mp4"
  local dur; dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "${name}_recovered.mp4" | cut -d. -f1)
  [ -n "$dur" ] && [ "$dur" -gt 0 ] || { echo "$name: conversion produced no video"; return; }
  local step=$(( dur / 42 > 1 ? dur / 42 : 1 ))
  ffmpeg -nostdin -v error -y -i "${name}_recovered.mp4" -vf "fps=1/$step,scale=240:-2,tile=6x7" -frames:v 1 "${name}_sheet.jpg"
  { echo "minute  decoder errors  (0 = clean; hundreds = mostly broken picture)"
    for ((m = 0; m * 60 < dur; m++)); do
      printf '%5d  %d\n' "$m" "$(ffmpeg -nostdin -v error -ss $((m * 60)) -t 60 -fflags +discardcorrupt -i "$in" -map 0:v:0 -f null - 2>&1 | wc -l)"
    done; } > "${name}_damage.txt"
  printf '%s: %d min %02d s, sheet every %d s -> %s_recovered.mp4\n' "$name" $((dur / 60)) $((dur % 60)) "$step" "$name"
}

for f in **/MPEGAV/*.DAT **/MPEG2/*.MPG; do convert "$(basename "${f%.*}")" "$f"; done
for first in **/VIDEO_TS/VTS_*_1.VOB; do
  t=${first%_1.*}; parts=("$t"_[1-9].VOB "$t"_[1-9][0-9].VOB)   # _0.VOB is the title menu
  convert "$(basename "$t")" $(printf '%s\n' "${parts[@]}" | sort -V)
done
for f in **/*.{avi,mpg,mpeg,mp4,mov,wmv,asf,m2ts,mts,3gp,dv,flv,mkv}; do
  case "$f" in *_recovered.mp4|*/MPEG2/*|*/VIDEO_TS/*) continue ;; esac
  convert "$(basename "${f%.*}")" "$f"
done

: > damaged.txt; n=0
for f in **/*.{jpg,jpeg,png,tif,tiff,bmp,gif}; do
  case "$f" in *_sheet.jpg) continue ;; esac
  n=$((n + 1))
  [ "$(ffmpeg -nostdin -v error -i "$f" -f null - 2>&1 | wc -l)" -eq 0 ] || echo "$f" >> damaged.txt
done
[ $n -gt 0 ] && echo "photos: $n checked, $(wc -l < damaged.txt) damaged (listed in damaged.txt)"
[ -s damaged.txt ] || rm -f damaged.txt
