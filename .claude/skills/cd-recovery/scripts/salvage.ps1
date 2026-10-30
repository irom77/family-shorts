# Copy one file off a damaged CD/DVD without hanging on bad sectors. Resumes from the end of an existing copy.
#
# Reads 64 KB chunks. A chunk that fails is re-read sector by sector, and unreadable sectors are zero-filled.
# After 3 bad sectors in a row it zero-fills a jump of $Jump sectors, doubling while it keeps landing on bad
# sectors (up to 16x); any good read resets it. Video CD .DAT files appear in Windows as RIFF/CDXA with a
# 44-byte header and 2352-byte raw sectors; everything else uses 2048-byte sectors.
#
# Log: <Dst>.log, ending with "DONE <bytes> bytes, <bad> bad sectors, <skipped> skipped sectors".
param([Parameter(Mandatory)][string]$Src, [Parameter(Mandatory)][string]$Dst, [int]$Jump = 75)

$in = New-Object IO.FileStream $Src, 'Open', 'Read', 'Read', 1   # bufferSize 1 = unbuffered: each read touches only its own sectors
$head = New-Object byte[] 12; [void]$in.Read($head, 0, 12)
$cdxa = [Text.Encoding]::ASCII.GetString($head, 0, 4) -eq 'RIFF' -and [Text.Encoding]::ASCII.GetString($head, 8, 4) -eq 'CDXA'
if ($cdxa) { $Sector = 2352; $Base = 44 } else { $Sector = 2048; $Base = 0 }
$Chunk = $Sector * 28; $MaxJump = $Jump * 16

[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($Dst))
$out = [IO.File]::Open($Dst, 'OpenOrCreate', 'Write', 'Read'); $out.Position = $out.Length
$len = $in.Length; $pos = $out.Length; $bad = 0; $run = 0; $jumpNow = $Jump; $skipped = 0
$buf = New-Object byte[] $Chunk; $log = "$Dst.log"
"start $Src at byte $pos of $len, sector $Sector" | Add-Content $log

while ($pos -lt $len) {
    # Read up to the next chunk boundary so later reads stay sector-aligned.
    $n = [Math]::Min($Chunk - (($pos - $Base) % $Chunk), $len - $pos)
    if ($pos -lt $Base) { $n = $Base - $pos }
    try {
        $in.Position = $pos; $got = $in.Read($buf, 0, $n); if ($got -le 0) { throw 'short read' }
        $out.Write($buf, 0, $got); $pos += $got; $run = 0; $jumpNow = $Jump
    }
    catch {
        $end = $pos + $n
        while ($pos -lt $end) {
            $m = [Math]::Min($Sector - (($pos - $Base) % $Sector), $end - $pos); $s = New-Object byte[] $m
            try { $in.Position = $pos; [void]$in.Read($s, 0, $m); $run = 0; $jumpNow = $Jump }
            catch { $bad++; $run++; "bad sector at byte $pos" | Add-Content $log }
            $out.Write($s, 0, $m); $pos += $m
            if ($run -ge 3) {
                $k = [Math]::Min([long]$jumpNow * $Sector, $len - $pos)
                $out.Write((New-Object byte[] $k), 0, $k); $pos += $k; $skipped += [Math]::Ceiling($k / $Sector)
                "skipped $([Math]::Ceiling($k / $Sector)) sectors to byte $pos" | Add-Content $log
                $jumpNow = [Math]::Min($jumpNow * 2, $MaxJump); $run = 2; break
            }
        }
    }
    $out.Flush()
    if (($pos % ($Sector * 2800)) -lt $Chunk) { "{0:N0} / {1:N0} bytes, {2} bad, {3} skipped sectors" -f $pos, $len, $bad, $skipped | Add-Content $log }
}
$in.Close(); $out.Close()
"DONE $pos bytes, $bad bad sectors, $skipped skipped sectors" | Add-Content $log
