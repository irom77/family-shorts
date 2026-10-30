---
name: cd-recovery
description: Use when the user puts an old CD or DVD in the Windows drive (D:) and wants the family videos or photos on it explored, copied or rescued — Video CD (MPEGAV/AVSEQ01.DAT), Super Video CD, DVD-Video (VIDEO_TS) or a data disc of JPG/AVI files — and especially when a copy is slow or frozen, Windows logs "cdrom has a bad block", Explorer or IsoBuster reports unreadable files or a CRC error, or a copy process cannot be killed.
---

# Recovering video and photos from old CDs and DVDs

Old burned discs (around 2000) are often partly unreadable. A normal Windows copy (Explorer,
`Copy-Item`, `cp` on `/mnt/d`) retries a bad sector for minutes. It can wedge the drive and leave a copy
process that ignores kill. The scripts here read around damage instead: they zero-fill what won't read,
jump over bad runs, resume after any interruption, and then show what survived. `<skill>` below means
`/home/irom/archive/.claude/skills/cd-recovery`.

## Steps

1. **Inventory (safe, reads only the directory):** `bash <skill>/scripts/inventory.sh [D]`. It prints the
   label, every file, the disc type, the newest file date, and recent Windows bad-block events. Tell the
   user what is on the disc before copying.
2. **Destination:** `$ARCHIVE/CD_<LABEL>_<year>/` (`$ARCHIVE` is in `/home/irom/archive/local.env`, not in git),
   with the year from the newest file date. Ask only if the label is empty or unclear.
3. **Recover, detached:**
   `nohup setsid bash <skill>/scripts/recover.sh D <dest> > /dev/null 2>&1 < /dev/null &`.
   Media files only by default (`--all` adds VCD/DVD player and menu files). A good disc takes minutes;
   a damaged one takes hours. Rerunning resumes and skips finished files.
4. **Watch:** a Monitor on `<dest>/recover.log` (per file `DONE …` or `FAILED`, then `ALLDONE`), plus the
   output file size so you can see stalls. Report the MB copied, bad sectors and jumps when the user asks.
5. **Review:** `bash <skill>/scripts/review.sh <dest>`. Each video becomes `<name>_recovered.mp4`,
   `<name>_sheet.jpg` (42 frames across the whole video) and `<name>_damage.txt` (decoder errors per
   minute). Photos that fail to decode go to `damaged.txt`. **Read the sheet** and describe the content and
   the quality honestly, including which minutes are clean.
6. **Keep** the raw copies (`MPEGAV/*.DAT`, `VIDEO_TS/*.VOB`, photos) next to the MP4: review can be
   redone from them, and they are the best copy that exists.

## Rules

- **Never** copy a disc with Explorer, `Copy-Item`, `robocopy` or `cp`, and never let two programs read the
  drive at once (IsoBuster, a second script, a media player). Only `recover.sh` reads the disc, one file at
  a time.
- **Inventory first, then the copy.** Don't read file contents to "peek" while a copy runs.
- **Damage is worse than the bad-sector count.** Video CD video sectors (Mode 2 Form 2) have no error
  correction, so most damage reads back silently as corrupt data. Judge by the sheet and `_damage.txt`.
- **Don't make shorts or uploads from a disc** unless the user asks after seeing the review. For shorts,
  use the family-shorts skill on `<name>_recovered.mp4`.

## When it goes wrong

| Symptom | What to do |
|---|---|
| Copy stops growing for 10+ min, and even `inventory.sh` times out | Drive is wedged. `Stop-Process` won't work (the process is stuck in a kernel read). Ask the user to **unplug the drive's USB cable** for 10 s (an internal drive needs a restart); eject and reinsert is not enough. If it is still stuck, restart Windows. Then rerun `recover.sh`; it resumes. Check first that nothing else needs WSL (uploaders, renders) and restart those afterwards. |
| Thousands of bad sectors and hours to go | Normal for a dye-faded burned CD. Let it run. Offer: another (older) drive, a disc resurfacing service for scratches, or the original tape if one exists. |
| A `Get-CimInstance Win32_Process … -like '*salvage*'` search returns two PIDs | One is the search itself. Filter with `$_.ProcessId -ne $PID`. |
| `Permission denied` reading a file Windows is still writing | The writer holds it. Wait for it; don't open a second reader. |
| IsoBuster lists "files on unreadable locations" | It confirms the damage. `recover.sh` still salvages those files around the bad spots. |

## How salvage.ps1 reads

Reads go in 64 KB chunks, unbuffered. A failed chunk is re-read sector by sector (2352 B for a VCD `.DAT`,
which Windows shows as RIFF/CDXA with a 44-byte header; 2048 B otherwise), and bad sectors are zero-filled.
After 3 bad sectors in a row it zero-fills a jump of 75 sectors (about 1 s of VCD video), doubling up to
1200 while it keeps landing on bad ones. The doubling can overshoot the end of a long bad run by a few
seconds of good video; that is the price of finishing in hours instead of days. To favour completeness
on a short, precious disc, run `JUMP=15 bash <skill>/scripts/recover.sh …`.
Per-file logs (`<file>.log`) list each bad sector and jump.
