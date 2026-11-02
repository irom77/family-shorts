#!/usr/bin/env python3
"""Build one self-contained HTML catalog of the family channel's public and unlisted videos.

Grouped by playlist (oldest year first), with thumbnails embedded so the file works as an email or
messaging attachment: nothing is hosted, and tapping a video opens it in the YouTube app.

  catalog.py --expect-channel <channel> --out <file.html> [--all-playlist PLAYLIST_ID] [--skip skip.txt]

Uses the family-shorts sign-in (~/.config/family-archive-youtube/token.json). Thumbnails are cached in
~/.cache/family-catalog/. With --all-playlist, every listed video missing from that playlist is
added to it, in catalog order, so one link (pinned to a Home Screen) always shows everything.
--skip names a text file of video ids to leave out, one per line (# starts a comment).
"""
import argparse
import base64
import html
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "family-shorts" / "scripts"))
from yt_family import channels, youtube  # noqa: E402

CACHE = Path.home() / ".cache" / "family-catalog"


def pages(call, **kw):
    page = None
    while True:
        r = call(**kw, maxResults=50, pageToken=page).execute()
        yield from r.get("items", [])
        page = r.get("nextPageToken")
        if not page:
            return


def thumb(vid):
    """270x480 JPEG data URI: the Short's own vertical frame, else the 16:9 one cropped to fit."""
    out = CACHE / f"{vid}.jpg"
    if not out.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        src = CACHE / f"{vid}.src.jpg"
        for name in ("oar2", "hqdefault"):
            try:
                src.write_bytes(urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/{name}.jpg", timeout=30).read())
                break
            except Exception:
                continue
        else:
            return ""
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-vf",
                        "scale=270:480:force_original_aspect_ratio=increase,crop=270:480", "-q:v", "6", str(out)],
                       check=True)
        src.unlink()
    return "data:image/jpeg;base64," + base64.b64encode(out.read_bytes()).decode()


def duration(iso):
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return ""
    h, mi, s = (int(x or 0) for x in m.groups())
    return f"{h}:{mi:02d}:{s:02d}" if h else f"{mi}:{s:02d}"


def filmy(n):
    """Polish plural: 1 film, 2-4 filmy, 5+ filmów (but 12-14 filmów)."""
    if n == 1:
        return "1 film"
    return f"{n} filmy" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else f"{n} filmów"


def split_title(t):
    """'Tort · 1 czerwca 1995 | The cake, 1995 #shorts' -> ('Tort · 1 czerwca 1995', 'The cake, 1995')."""
    t = re.sub(r"\s*#\w+", "", t).strip()
    pl, _, en = t.partition(" | ")
    return pl.strip(), en.strip()


def year(text):
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return int(m.group()) if m else 9999


def collect(yt):
    uploads = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0][
        "contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [i["contentDetails"]["videoId"] for i in pages(yt.playlistItems().list, part="contentDetails",
                                                          playlistId=uploads)]
    videos = {}
    for k in range(0, len(ids), 50):
        for v in yt.videos().list(part="snippet,status,contentDetails", id=",".join(ids[k:k + 50])).execute()["items"]:
            if v["status"]["privacyStatus"] in ("public", "unlisted"):
                videos[v["id"]] = v
    groups = []
    for p in pages(yt.playlists().list, part="snippet,status", mine=True):
        if p["status"]["privacyStatus"] == "private":
            continue
        vids = [i["contentDetails"]["videoId"] for i in pages(yt.playlistItems().list, part="contentDetails",
                                                               playlistId=p["id"])]
        groups.append({"id": p["id"], "title": p["snippet"]["title"], "vids": [v for v in vids if v in videos]})
    return videos, groups


def add_to_playlist(yt, pid, order):
    have = {i["contentDetails"]["videoId"] for i in pages(yt.playlistItems().list, part="contentDetails",
                                                           playlistId=pid)}
    for v in order:
        if v not in have:
            yt.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": v}}}).execute()
    return len([v for v in order if v not in have])


def page(sections, all_url, built):
    e = html.escape
    total = len({v["id"] for _, _, vs in sections for v in vs})
    chips, body = [], []
    for n, (title, url, vs) in enumerate(sections):
        pl, en = (title.split(" | ", 1) + [""])[:2]
        chips.append(f'<a class="chip" href="#s{n}">{e(pl)}</a>')
        cards = []
        for v in vs:
            tpl, ten = split_title(v["snippet"]["title"])
            cards.append(
                f'<a class="card" href="https://youtu.be/{v["id"]}" data-q="{e((tpl + " " + ten).lower())}">'
                f'<span class="thumb"><img src="{thumb(v["id"])}" alt="" loading="lazy">'
                f'<span class="dur">{duration(v["contentDetails"].get("duration"))}</span></span>'
                f'<span class="t">{e(tpl)}</span><span class="en">{e(ten)}</span></a>')
        play = f'<a class="play" href="{e(url)}">▶ Odtwórz wszystkie <i>Play all</i></a>' if url else ""
        body.append(f'<section id="s{n}"><header><h2>{e(pl)}</h2><p class="sub">{e(en)}'
                    f'{" · " if en else ""}{filmy(len(vs))}</p>{play}</header>'
                    f'<div class="grid">{"".join(cards)}</div></section>')
    allbtn = (f'<a class="all" href="{e(all_url)}">▶ Wszystkie filmy w YouTube <i>All videos in YouTube</i></a>'
              if all_url else "")
    return TEMPLATE.format(total=filmy(total), chips="".join(chips), sections="".join(body), allbtn=allbtn,
                           built=built)


TEMPLATE = """<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="color-scheme" content="dark light">
<title>Archiwum rodzinne</title>
<style>
:root {{ --bg:#16192a; --bg2:#1f2336; --card:#262a3f; --text:#f5efe6; --muted:#b9ae9f; --accent:#e0a96d; --line:#33384f; }}
@media (prefers-color-scheme: light) {{
  :root {{ --bg:#f7f2ea; --bg2:#efe7da; --card:#ffffff; --text:#2a2420; --muted:#7a6d60; --accent:#a8662a; --line:#e2d8c8; }}
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; -webkit-text-size-adjust:100%; }}
body {{ margin:0; background:var(--bg); color:var(--text);
  font:15px/1.35 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
a {{ color:inherit; text-decoration:none; }}
.hero {{ padding:calc(28px + env(safe-area-inset-top)) 16px 18px; text-align:center;
  background:radial-gradient(120% 90% at 50% 0%, var(--bg2), var(--bg)); }}
.hero h1 {{ margin:0; font:600 34px/1.1 ui-serif, "New York", Georgia, serif; letter-spacing:.2px; }}
.hero .rule {{ width:44px; height:2px; background:var(--accent); margin:12px auto; border-radius:2px; }}
.hero p {{ margin:0; color:var(--muted); font-size:12px; letter-spacing:2.5px; text-transform:uppercase; }}
.all {{ display:inline-block; margin-top:16px; padding:10px 16px; border-radius:999px; background:var(--accent);
  color:#1c1710; font-weight:600; font-size:14px; }}
.all i, .play i {{ font-style:normal; opacity:.7; font-weight:400; }}
nav {{ position:sticky; top:0; z-index:5; display:flex; gap:8px; overflow-x:auto; padding:10px 16px;
  background:var(--bg); background:color-mix(in srgb, var(--bg) 88%, transparent); -webkit-backdrop-filter:blur(12px); backdrop-filter:blur(12px);
  border-bottom:1px solid var(--line); scrollbar-width:none; }}
nav::-webkit-scrollbar {{ display:none; }}
.chip {{ flex:none; padding:7px 13px; border-radius:999px; background:var(--card); border:1px solid var(--line);
  font-size:13px; white-space:nowrap; }}
#q {{ display:none; width:calc(100% - 32px); margin:14px 16px 0; padding:11px 14px; border-radius:12px; font-size:16px;
  border:1px solid var(--line); background:var(--card); color:var(--text); }}
.js #q {{ display:block; }}
main {{ max-width:1100px; margin:0 auto; padding:0 0 calc(32px + env(safe-area-inset-bottom)); }}
section {{ padding:22px 16px 4px; scroll-margin-top:56px; }}
section header {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 12px; margin-bottom:12px; }}
h2 {{ margin:0; font:600 22px/1.2 ui-serif, "New York", Georgia, serif; }}
.sub {{ margin:0; color:var(--muted); font-size:13px; flex:1 1 auto; }}
.play {{ color:var(--accent); font-size:13px; font-weight:600; }}
.grid {{ display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:14px 12px; }}
@media (min-width:600px) {{ .grid {{ grid-template-columns:repeat(4, minmax(0, 1fr)); }} }}
@media (min-width:960px) {{ .grid {{ grid-template-columns:repeat(6, minmax(0, 1fr)); }} }}
.card {{ display:block; -webkit-tap-highlight-color:transparent; }}
.thumb {{ position:relative; display:block; aspect-ratio:9/16; border-radius:14px; overflow:hidden; background:var(--card);
  box-shadow:0 6px 18px rgba(0,0,0,.25); transition:transform .15s; }}
.card:active .thumb {{ transform:scale(.97); }}
.thumb img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.dur {{ position:absolute; right:6px; bottom:6px; padding:2px 6px; border-radius:6px; background:rgba(0,0,0,.65);
  color:#fff; font-size:11px; font-variant-numeric:tabular-nums; }}
.t {{ display:block; margin-top:7px; font-weight:600; font-size:14px; }}
.en {{ display:block; color:var(--muted); font-size:12px; margin-top:1px; }}
.hide {{ display:none !important; }}
footer {{ text-align:center; color:var(--muted); font-size:12px; padding:8px 16px 24px; }}
</style>
</head>
<body>
<div class="hero">
  <h1>Archiwum rodzinne</h1>
  <div class="rule"></div>
  <p>Family archive · {total}</p>
  {allbtn}
</div>
<nav>{chips}</nav>
<input id="q" type="search" placeholder="Szukaj… / Search…" autocomplete="off">
<main>{sections}</main>
<footer>Stuknij film, aby obejrzeć w YouTube · Tap a video to watch in YouTube<br>{built}</footer>
<script>
document.documentElement.classList.add("js");
document.getElementById("q").addEventListener("input", function (ev) {{
  var q = ev.target.value.trim().toLowerCase();
  document.querySelectorAll("section").forEach(function (s) {{
    var n = 0;
    s.querySelectorAll(".card").forEach(function (c) {{
      var hit = !q || c.dataset.q.indexOf(q) >= 0; c.classList.toggle("hide", !hit); n += hit;
    }});
    s.classList.toggle("hide", n === 0);
  }});
}});
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--expect-channel", required=True, help="channel id, title or @handle")
    ap.add_argument("--out", required=True)
    ap.add_argument("--all-playlist", help="playlist id that should hold every listed video")
    ap.add_argument("--skip", help="file of video ids to leave out, one per line")
    a = ap.parse_args()

    yt = youtube()
    chans = channels(yt)
    want = a.expect_channel.lower().lstrip("@")
    if not any(want in (c["id"].lower(), c["title"].lower(), c["handle"].lower().lstrip("@")) for c in chans):
        sys.exit(f"token is for {chans}, not {a.expect_channel!r}: nothing built")

    videos, groups = collect(yt)
    if a.skip and Path(a.skip).exists():
        for line in Path(a.skip).read_text().splitlines():
            videos.pop(line.split("#")[0].strip(), None)
        for g in groups:
            g["vids"] = [v for v in g["vids"] if v in videos]
    groups = [g for g in groups if g["id"] != a.all_playlist and g["vids"]]
    groups.sort(key=lambda g: (year(g["title"]), g["title"]))
    sections, seen = [], set()
    for g in groups:
        sections.append((g["title"], f"https://www.youtube.com/playlist?list={g['id']}", [videos[v] for v in g["vids"]]))
        seen |= set(g["vids"])
    rest = sorted((v for k, v in videos.items() if k not in seen), key=lambda v: v["snippet"]["publishedAt"])
    if rest:
        sections.append(("Inne | Other", "", rest))

    order = list(dict.fromkeys(v["id"] for _, _, vs in sections for v in vs))
    all_url = ""
    if a.all_playlist:
        print("ADDED", add_to_playlist(yt, a.all_playlist, order), "to the all-videos playlist")
        all_url = f"https://www.youtube.com/playlist?list={a.all_playlist}"

    built = "Stan na / As of " + datetime.now().strftime("%Y-%m-%d")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(sections, all_url, built), encoding="utf-8")
    print("CATALOG", out, f"{len(order)} videos in {len(sections)} sections, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
