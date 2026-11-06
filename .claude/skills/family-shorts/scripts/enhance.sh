#!/usr/bin/env bash
# Enhance one DV segment into a 1080x1920 blur-fill vertical clip.
# usage: enhance.sh <source.avi> <start_sec> <dur_sec> <out.mp4>
# Handles NTSC DV (720x480, SAR 8:9), PAL DV (720x576, SAR 16:15) and Video CD (352x288 progressive
# MPEG-1, 4:3 whatever its SAR flag says) and old 320x240 YouTube downloads; all come out at 30 fps.
set -euo pipefail
SRC="$1"; SS="$2"; DUR="$3"; OUT="$4"
TMP="$(dirname "$OUT")/.$(basename "$OUT" .mp4)"
mkdir -p "$TMP"
TRF="$TMP/transforms.trf"
H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$SRC")

# Common front: deinterlace, crop overscan + head-switching noise, square pixels.
if [ "$H" = 240 ]; then
  # Old 240p YouTube upload (channel-originals): progressive and heavily compressed; trim edge junk
  # and deblock lightly. Already smoothed by the old encoder, so the denoise is lighter too (the DV
  # strength turns faces waxy).
  PRE="crop=312:234:4:3,deblock=filter=weak:block=8,setsar=1"
  DN="hqdn3d=1.5:1.5:3:3"
elif [ "$H" = 288 ]; then
  # Video CD: already progressive; soften MPEG-1 block edges before the denoise and upscale.
  PRE="crop=344:280:4:4,deblock=filter=weak:block=8,scale=374:280:flags=lanczos,setsar=1"
elif [ "$H" = 576 ]; then
  PRE="bwdif=mode=send_frame:parity=auto:deint=all,crop=704:564:8:6,scale=752:564:flags=lanczos,setsar=1"
else
  PRE="bwdif=mode=send_frame:parity=auto:deint=all,crop=704:464:8:6,scale=626:464:flags=lanczos,setsar=1"
fi

DN="${DN:-hqdn3d=3:2.5:5:4,nlmeans=s=2.2:p=5:r=11}"

# Pass 1: motion analysis for stabilization
ffmpeg -nostdin -hide_banner -nostats -loglevel error -y -ss "$SS" -t "$DUR" -i "$SRC" \
  -vf "$PRE,vidstabdetect=shakiness=5:accuracy=15:result=$TRF" -f null -

# Pass 2: stabilize (gentle), denoise, upscale, sharpen, light grade, blur-fill
ffmpeg -nostdin -hide_banner -nostats -loglevel error -y -ss "$SS" -t "$DUR" -i "$SRC" -filter_complex "\
[0:v]$PRE,vidstabtransform=input=$TRF:smoothing=18:optzoom=1:interpol=bicubic,\
$DN,\
scale=1080:800:flags=lanczos,unsharp=5:5:0.7:3:3:0.0,\
eq=contrast=1.05:saturation=1.12:gamma=1.02,fps=30,format=yuv420p,split[fg][b];\
[b]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,gblur=sigma=10,\
scale=1080:1920:flags=bicubic,eq=brightness=-0.10:saturation=0.85[bg];\
[bg][fg]overlay=x=0:y=520,format=yuv420p[v];\
[0:a]highpass=f=80,lowpass=f=12000,afftdn=nf=-28,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 16 -profile:v high -movflags +faststart \
  -c:a aac -b:a 192k "$OUT"
rm -rf "$TMP"
echo "OK $OUT"
