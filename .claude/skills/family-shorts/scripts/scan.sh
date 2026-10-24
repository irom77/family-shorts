#!/usr/bin/env bash
# Scan a whole tape once so shots can be picked from pictures, not by watching an hour of video.
# usage: scan.sh <tape-dir>
# Writes <tape-dir>/scan/: scd.txt (scene-change scores), rms.txt (loudness per second),
# thumbs/ (one frame every 2 s) and sheets/sheet_NN.jpg (10x8 thumbs = 160 s per sheet;
# thumb k of sheet N is at (N-1)*160 + k*2 seconds).
# Single-purpose passes on purpose: the static ffmpeg crashes on one big multi-output graph.
set -euo pipefail
. "$(dirname "$0")/tape.sh" "$1"
O="$TAPE_DIR/scan"; mkdir -p "$O/thumbs" "$O/sheets"
ff() { ffmpeg -nostdin -hide_banner -nostats "$@"; }
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,field_order,sample_aspect_ratio -of compact "$SRC" | tee "$O/probe.txt"
ff -i "$SRC" -an -vf "scale=320:240,scdet=threshold=8,metadata=print:key=lavfi.scd.score:file=$O/scd.txt" -f null - 2> "$O/scd.log"
ff -i "$SRC" -vn -af "asetnsamples=48000,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=$O/rms.txt" -f null - 2> "$O/rms.log"
ff -loglevel error -y -i "$SRC" -an -vf "fps=1/2,scale=240:180" -q:v 4 "$O/thumbs/%05d.jpg"
n=$(ls "$O/thumbs" | wc -l); i=0
for s in $(seq 1 80 "$n"); do i=$((i+1))
  ff -loglevel error -y -framerate 1 -start_number "$s" -i "$O/thumbs/%05d.jpg" -frames:v 80 \
    -vf "scale=180:135,tile=10x8:padding=3:color=red" -frames:v 1 "$O/sheets/sheet_$(printf %02d $i).jpg"
done
# Scene cuts more than 1 s apart, in seconds (a cut list to pick in/out points from).
grep -oE "scd.time: [0-9.]+" "$O/scd.log" | awk '{t=$2+0; if (t-p>1.0) printf "%.1f\n", t; p=t}' > "$O/cuts.txt" || true
echo "scan: $n thumbs, $i sheets, $(wc -l < "$O/cuts.txt") cuts -> $O"
