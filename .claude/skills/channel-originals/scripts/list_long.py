#!/usr/bin/env python3
"""List the channel's videos that are not Shorts: the old long uploads that shorts can be cut from.

  list_long.py --expect-channel <id> [--min-seconds 181]

Prints one line per video, oldest first: id, upload date, length, privacy, original file name, title.
Uses the family-shorts YouTube token (read-only calls, a few quota units).
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "family-shorts" / "scripts"))
import yt_family  # noqa: E402


def seconds(iso):
    h, m, s = (int(x or 0) for x in re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso).groups())
    return h * 3600 + m * 60 + s


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--expect-channel", required=True)
    p.add_argument("--min-seconds", type=int, default=181, help="Shorts are at most 180 s")
    a = p.parse_args()
    yt = yt_family.youtube()
    ch = yt.channels().list(part="id,contentDetails", mine=True).execute()["items"][0]
    if ch["id"] != a.expect_channel:
        sys.exit(f"token is for channel {ch['id']}, not {a.expect_channel}")
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, tok = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=tok).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok:
            break
    rows = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,contentDetails,status,fileDetails", id=",".join(ids[i:i + 50])).execute()
        for v in r["items"]:
            s = seconds(v["contentDetails"]["duration"])
            if s >= a.min_seconds:
                rows.append((v["snippet"]["publishedAt"][:10], v["id"], f"{s // 60}:{s % 60:02d}",
                             v["status"]["privacyStatus"], v.get("fileDetails", {}).get("fileName", "?"),
                             v["snippet"]["title"]))
    for d, vid, ln, priv, fn, title in sorted(rows):
        print(f"{vid}\t{d}\t{ln}\t{priv}\t{fn}\t{title}")


if __name__ == "__main__":
    main()
