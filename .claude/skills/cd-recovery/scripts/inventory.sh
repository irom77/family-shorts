#!/usr/bin/env bash
# What is in the Windows CD/DVD drive: drive letter, label, every file with size and date, the disc type,
# and any "bad block" errors Windows logged for the drive in the last hour. Reads only the directory, never
# file contents, so it is safe on a damaged disc.
# Usage: inventory.sh [drive letter, default: the first optical drive with a disc]
set -euo pipefail
PS=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
ps() { timeout "${T:-60}" "$PS" -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; $1" | tr -d '\r'; }

DRIVE=${1:-$(ps "Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=5' | ? Size | Select -First 1 -Expand DeviceID")}
DRIVE=${DRIVE%:}
[ -n "$DRIVE" ] || { echo "No optical drive with a disc. Check the drive letter in Explorer." >&2; exit 1; }
[ -n "$(ps "(Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='$DRIVE:'\").Size")" ] || { echo "No disc in $DRIVE: (or Windows cannot read its file list)." >&2; exit 1; }

echo "== Drive"
ps "Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='$DRIVE:'\" | Select DeviceID,VolumeName,FileSystem,Size | Format-List" | grep -v '^$'
ps "Get-PnpDevice -Class CDROM -PresentOnly | Select FriendlyName,InstanceId | Format-List" | grep -v '^$'

echo "== Files (path, bytes, date)"
FILES=$(T=120 ps "Get-ChildItem -LiteralPath '$DRIVE:\' -Recurse -Force -File | % { '{0}`t{1}`t{2:yyyy-MM-dd}' -f \$_.FullName, \$_.Length, \$_.LastWriteTime }")
echo "$FILES"

echo "== Disc type"
paths=$(cut -f1 <<<"$FILES" | tr '[:lower:]' '[:upper:]')
grep -q '\\MPEGAV\\.*\.DAT$' <<<"$paths" && echo "Video CD (MPEG-1 .DAT tracks in MPEGAV)"
grep -q '\\MPEG2\\.*\.MPG$' <<<"$paths" && echo "Super Video CD (MPEG-2 .MPG tracks in MPEG2)"
grep -q '\\VIDEO_TS\\VTS_.*\.VOB$' <<<"$paths" && echo "DVD-Video (VIDEO_TS .VOB titles)"
n_img=$(grep -cE '\.(JPE?G|PNG|TIFF?|BMP|GIF|HEIC|CR2|NEF)$' <<<"$paths" || true)
n_vid=$(grep -vE '\\(MPEGAV|MPEG2|VIDEO_TS)\\' <<<"$paths" | grep -cE '\.(AVI|MPE?G|MP4|MOV|WMV|ASF|M2TS|MTS|3GP|DV|VOB|FLV|MKV)$' || true)
echo "Photos: $n_img   Other video files: $n_vid   Total size: $(awk -F'\t' '{s+=$2} END {printf "%.1f MB", s/1048576}' <<<"$FILES")"

echo "== Newest file date (for the folder name)"
cut -f3 <<<"$FILES" | sort | tail -1

echo "== CD read errors logged by Windows in the last hour"
ps "\$e = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='cdrom'; StartTime=(Get-Date).AddHours(-1)} -ErrorAction SilentlyContinue; if (\$e) { '{0} bad-block events, last at {1}' -f \$e.Count, \$e[0].TimeCreated } else { 'none' }"
