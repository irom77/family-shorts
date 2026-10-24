#!/usr/bin/env python3
"""Add or refresh shorts in the tape's Windows manifest.json (what yt_family.py uploads from).

  manifest.py <tape-dir> 02 [03 ...]

Takes title/description/tags from plan/copy.json and segments from shortNN/segments.json.
New entries are "private"; an existing entry keeps its privacy and youtube record.
"""
import json
import subprocess
import sys
from pathlib import Path


def win(p):
    p = str(p)
    return p[5].upper() + ":\\" + p[7:].replace("/", "\\") if p.startswith("/mnt/") else p


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    work = Path(sys.argv[1]).resolve()
    tape = json.loads((work / "plan" / "tape.json").read_text())
    copy = json.loads((work / "plan" / "copy.json").read_text())
    mpath = Path(tape["out_dir"]) / "manifest.json"
    m = json.loads(mpath.read_text()) if mpath.exists() else {}
    m.setdefault("source", win(tape["source"]))
    shorts = m.setdefault("shorts", [])
    for num in (n.zfill(2) for n in sys.argv[2:]):
        c = copy[num]
        f = Path(tape["out_dir"]) / c["file"]
        if not f.exists():
            sys.exit(f"short{num}: {f} not rendered/copied yet")
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                             "-of", "csv=p=0", str(f)], text=True))
        segs = json.loads((work / f"short{num}" / "segments.json").read_text())["segments"]
        old = next((s for s in shorts if s["id"] == f"short_{num}"), None)
        entry = {
            "id": f"short_{num}", "file": c["file"], "source": win(tape["source"]), "duration_s": round(dur, 1),
            "title": c["yt_title"], "description": c["yt_desc"], "tags": c["tags"],
            "privacy": old["privacy"] if old else "private",
            "segments": [{"id": s["id"], "src_in": s["in"], "src_out": s["out"], "at": s["at"], "note": s["note"]}
                         for s in segs],
        }
        if old and "youtube" in old:
            entry["youtube"] = old["youtube"]
        if old:
            shorts[shorts.index(old)] = entry
        else:
            shorts.append(entry)
        print(f"short_{num}: {dur:.1f}s, {len(segs)} segments, {entry['privacy']}")
    shorts.sort(key=lambda s: s["id"])
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n")
    print(mpath)


if __name__ == "__main__":
    main()
