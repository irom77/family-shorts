#!/usr/bin/env bash
# Compare one tape's "PAL"-folder copy (P) with its "NTSC"-folder copy (N).
# usage: compare_pair.sh <P.avi> <N.avi> <outdir>
# Writes <outdir>/summary.txt and worst-frame stills; prints the summary.
set -uo pipefail
P="$1"; N="$2"; O="$3"; mkdir -p "$O"
ff() { ffmpeg -nostdin -hide_banner "$@"; }
probe() { ffprobe -v error -select_streams v -show_entries stream=width,height,r_frame_rate,pix_fmt -show_entries format=duration,size -of default=nw=1:nk=0 "$1" | tr '\n' ' '; }

{
echo "P: $P"; echo "   $(probe "$P")"
echo "N: $N"; echo "   $(probe "$N")"
} > "$O/summary.txt"

# Full-tape picture comparison: one PSNR value per frame, and the frame count of each copy.
ff -i "$P" -i "$N" -lavfi "[0:v][1:v]psnr=stats_file=$O/psnr.log" -f null - 2> "$O/psnr.err"
ff -v error -i "$P" -map 0:v -c copy -f framecrc - 2>/dev/null | grep -vc '^#' > "$O/frames_P"
ff -v error -i "$N" -map 0:v -c copy -f framecrc - 2>/dev/null | grep -vc '^#' > "$O/frames_N"

# Full-tape audio: decoded PCM hash of each copy.
# (hashed per 1-second chunk, so a difference shows how much of the tape it covers)
ff -v error -i "$P" -map 0:a:0 -af asetnsamples=n=48000 -f framemd5 - 2>/dev/null | grep -v '^#' | awk -F, '{print $NF}' > "$O/audio_P"
ff -v error -i "$N" -map 0:a:0 -af asetnsamples=n=48000 -f framemd5 - 2>/dev/null | grep -v '^#' | awk -F, '{print $NF}' > "$O/audio_N"

# Sharpness on three 300-frame windows (lower blur = sharper).
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$P")
for f in P N; do eval src=\$$f
  for p in 0.2 0.5 0.8; do t=$(echo "$D*$p" | bc -l)
    ff -ss "$t" -i "$src" -frames:v 300 -vf "blurdetect,metadata=print:file=-" -an -f null - 2>/dev/null \
      | awk -F= '/blur=/{b+=$2;n++} END{if(n) printf "%.3f ", b/n}'
  done > "$O/blur_$f"
done

python3 - "$O" <<'EOF'
import sys, re, math
from pathlib import Path
o = Path(sys.argv[1]); s = []
vals = []
for line in (o / "psnr.log").read_text().splitlines():
    m = re.search(r"n:(\d+).*?psnr_avg:(\S+)", line)
    if m:
        v = m.group(2); vals.append((int(m.group(1)), math.inf if v == "inf" else float(v)))
fp, fn = (o / "frames_P").read_text().strip(), (o / "frames_N").read_text().strip()
ap, an = (o / "audio_P").read_text().split(), (o / "audio_N").read_text().split()
asame = sum(1 for a, b in zip(ap, an) if a == b)
fin = [v for _, v in vals if v != math.inf]
same = sum(1 for _, v in vals if v == math.inf)
low = sorted([x for x in vals if x[1] < 35], key=lambda x: x[1])
bp, bn = (o / "blur_P").read_text().split(), (o / "blur_N").read_text().split()
s.append(f"frames: P={fp} N={fn} compared={len(vals)} -> {'MATCH' if fp == fn == str(len(vals)) else 'DIFFERENT'}")
s.append(f"audio:  {asame} of {max(len(ap), len(an))} one-second chunks identical (P {len(ap)} s, N {len(an)} s)")
if fin:
    s.append(f"video:  identical frames={same}, differing={len(fin)}, PSNR avg={sum(fin)/len(fin):.1f} dB min={min(fin):.1f} dB")
else:
    s.append(f"video:  all {same} frames bit-identical")
s.append(f"        frames below 35 dB: {len(low)}" + (f"; worst: {[(n, round(v, 1)) for n, v in low[:8]]}" if low else ""))
s.append(f"blur (lower = sharper): P={bp} N={bn} -> {'P sharper' if sum(map(float, bp)) < sum(map(float, bn)) else 'N sharper or equal'}")
(o / "worst.txt").write_text("\n".join(str(n) for n, _ in low[:6]))
with open(o / "summary.txt", "a") as f:
    f.write("\n".join(s) + "\n")
EOF

# Side-by-side stills (P left, N right) of the worst-matching frames, to see which copy is damaged.
i=0; for n in $(cat "$O/worst.txt"); do
  t=$(echo "$n/29.97" | bc -l)
  ff -v error -y -ss "$t" -i "$P" -ss "$t" -i "$N" -filter_complex "[0:v][1:v]hstack,scale=960:-1" -frames:v 1 "$O/worst_$i.jpg"
  i=$((i+1)); done
cat "$O/summary.txt"
