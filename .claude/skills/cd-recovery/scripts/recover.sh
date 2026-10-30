#!/usr/bin/env bash
# Copy the media files of a disc into DEST with salvage.ps1, one file at a time (two readers on one drive
# slow both and can wedge it). Files already finished (DONE in their .log) are skipped, and an unfinished
# copy resumes, so rerunning after a stop, a USB replug or a reboot is safe.
# Run it detached; it takes minutes on a good disc and hours on a bad one:
#   nohup setsid bash recover.sh D "$ARCHIVE/CD_<LABEL>_<year>" > /dev/null 2>&1 < /dev/null &
# Progress: DEST/recover.log (one line per file) and DEST/<file>.log (per-file detail).
# Usage: [JUMP=75] recover.sh DRIVE DEST [--all]   (--all also copies VCD/DVD player files, menus and other non-media;
# JUMP is the first skip, in sectors, after 3 bad sectors in a row: smaller keeps more video but takes longer)
# DRIVE is a letter (D) or a Windows folder to read instead of a disc root (C:\Users\...\copy-of-disc).
set -euo pipefail
DRIVE=${1%:}; DEST=$2; ALL=${3:-}
if [ ${#DRIVE} -eq 1 ]; then ROOT="$DRIVE:\\"; else ROOT=${DRIVE%\\}\\; fi
PS=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DEST"; LOG="$DEST/recover.log"
cp "$HERE/salvage.ps1" "$DEST/salvage.ps1"   # PowerShell runs scripts from a Windows path, not from \\wsl$
WDEST=$(wslpath -w "$DEST")
log() { echo "$(date '+%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }

MEDIA='\.(DAT|MPG|MPEG|VOB|AVI|MP4|MOV|WMV|ASF|M2TS|MTS|3GP|DV|FLV|MKV|JPG|JPEG|PNG|TIF|TIFF|BMP|GIF|HEIC|CR2|NEF)$'
mapfile -t FILES < <(timeout 120 "$PS" -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-ChildItem -LiteralPath '$ROOT' -Recurse -Force -File | Sort-Object FullName | % { \$_.FullName }" | tr -d '\r')
log "disc $ROOT: ${#FILES[@]} files -> $WDEST"

for SRC in "${FILES[@]}"; do
  REL=${SRC#"$ROOT"}
  if [ "$ALL" != --all ]; then
    # Video CD player data (VCD/, EXT/, CDI/, SEGMENT/) and the .DAT under them are not video.
    grep -qiE "$MEDIA" <<<"$REL" || continue
    grep -qiE '^(VCD|SVCD|EXT|CDI|SEGMENT)\\' <<<"$REL" && continue
  fi
  DST="$WDEST\\$REL"; DLOG="$DEST/$(tr '\\' / <<<"$REL").log"
  if [ -f "$DLOG" ] && grep -q '^DONE' "$DLOG"; then continue; fi
  log "start $REL"
  "$PS" -NoProfile -ExecutionPolicy Bypass -File "$WDEST\\salvage.ps1" -Src "$SRC" -Dst "$DST" -Jump "${JUMP:-75}" < /dev/null | tr -d '\r' >> "$LOG" 2>&1 || true
  if grep -q '^DONE' "$DLOG" 2>/dev/null; then log "$REL: $(tail -1 "$DLOG")"; else log "$REL: FAILED, see $DLOG"; fi
done
log "ALLDONE"
