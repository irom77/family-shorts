#!/usr/bin/env python3
"""Build a HyperFrames project for one short from its ledger (plan/shortNN.tsv) and copy (plan/copy.json).

  make_short.py <tape-dir> 02 [03 ...]  -> <tape-dir>/short02/ (index.html, compositions/, assets/clips/, BRIEF.md)

Layout: blur-filled 1080x1920 clips on track 0, title over the opening,
sparse bilingual chapter captions, end card over the last 8 s with a fade to black.
The clips must already exist in <tape-dir>/clips/shortNN/ (enhance_batch.sh).
"""
import json
import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template"
FADE = 0.08
END_LEN = 8.0
TITLE_LEN = 6.0

STYLE = """    #root { position: absolute; inset: 0; }
    #root .band { position: absolute; left: 90px; right: 90px; top: 250px; height: 250px;
      display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
      color: #f4ead8; text-shadow: 0 2px 18px rgba(0,0,0,0.6), 0 0 2px rgba(0,0,0,0.5); }
    #root .pl { font-family: "Playfair Display", serif; font-weight: 600; line-height: 1.05; }
    #root .rule { width: 72px; height: 2px; background: #d9b98a; margin: 22px 0 18px; }
    #root .en { font-family: "Inter", sans-serif; font-weight: 500; font-size: 30px; letter-spacing: 0.18em; text-transform: uppercase; opacity: 0.85; }
    /* soft dark pool behind the text band, so it reads over bright blurred frames */
    #root .scrim { position: absolute; left: -120px; right: -120px; top: 90px; height: 560px;
      background: radial-gradient(closest-side, rgba(0,0,0,0.55), rgba(0,0,0,0.32) 55%, rgba(0,0,0,0) 100%); }
"""


def r(x):
    return round(x + 1e-9, 2)


def title_html(t):
    size = 132 if len(t["pl"]) <= 9 else 112
    return f"""<template>
  <style>
{STYLE}    #root .band {{ top: 200px; height: 320px; }}
    #root .pl {{ font-size: {size}px; }}
    #root .date {{ font-family: "Playfair Display", serif; font-style: italic; font-size: 54px; margin-top: 6px; }}
  </style>
  <div id="root" data-composition-id="title" data-width="1080" data-height="1920">
    <div id="title-scrim" class="scrim" data-layout-ignore></div>
    <div class="band">
      <div id="title-pl" class="pl" data-var-text="title-pl">{t["pl"]}</div>
      <div id="title-date" class="date" data-var-text="date-pl">{t["date"]}</div>
      <div id="title-rule" class="rule"></div>
      <div id="title-en" class="en" data-var-text="title-en">{t["en"]}</div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    // On screen from frame 0 (thumbnail + hook); only a gentle settle.
    tl.fromTo("#title-pl", {{ y: 10, scale: 1.04 }}, {{ y: 0, scale: 1, duration: 2.4, ease: "power2.out" }}, 0);
    tl.fromTo("#title-rule", {{ scaleX: 0.2 }}, {{ scaleX: 1, duration: 1.2, ease: "power2.inOut" }}, 0);
    tl.to(["#title-pl", "#title-date", "#title-rule", "#title-en"], {{ opacity: 0, y: -10, duration: 0.7, ease: "power1.in", stagger: 0.05 }}, 5.0);
    tl.to("#title-scrim", {{ opacity: 0, duration: 0.9, ease: "power1.in" }}, 5.0);
    window.__timelines["title"] = tl;
  </script>
</template>
"""


def caption_html(cid, pl, en, dur):
    size = 78 if len(pl) <= 18 else 64
    return f"""<template>
  <style>
{STYLE}    #root .pl {{ font-size: {size}px; }}
  </style>
  <div id="root" data-composition-id="{cid}" data-width="1080" data-height="1920">
    <div id="{cid}-scrim" class="scrim" data-layout-ignore></div>
    <div class="band">
      <div id="{cid}-pl" class="pl">{pl}</div>
      <div id="{cid}-rule" class="rule"></div>
      <div id="{cid}-en" class="en">{en}</div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#{cid}-scrim", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.7, ease: "power1.out" }}, 0.3);
    tl.fromTo(["#{cid}-pl", "#{cid}-en"], {{ opacity: 0, y: 24 }}, {{ opacity: 1, y: 0, duration: 0.8, ease: "power3.out", stagger: 0.18 }}, 0.4);
    tl.fromTo("#{cid}-rule", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.7, ease: "power2.inOut" }}, 0.55);
    tl.to(["#{cid}-pl", "#{cid}-rule", "#{cid}-en", "#{cid}-scrim"], {{ opacity: 0, duration: 0.6, ease: "power1.in" }}, {r(dur - 0.9)});
    window.__timelines["{cid}"] = tl;
  </script>
</template>
"""


def endcard_html(en):
    return f"""<template>
  <style>
{STYLE}    #root .pl {{ font-size: 70px; }}
    #root .fade {{ position: absolute; inset: 0; background: #000; }}
  </style>
  <div id="root" data-composition-id="endcard" data-width="1080" data-height="1920">
    <div id="endcard-scrim" class="scrim" data-layout-ignore></div>
    <div class="band">
      <div id="endcard-pl" class="pl">Archiwum rodzinne</div>
      <div id="endcard-rule" class="rule"></div>
      <div id="endcard-en" class="en">{en}</div>
    </div>
    <div id="endcard-fade" class="fade" data-layout-ignore></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#endcard-scrim", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.9, ease: "power1.out" }}, 1.0);
    tl.fromTo(["#endcard-pl", "#endcard-en"], {{ opacity: 0, y: 24 }}, {{ opacity: 1, y: 0, duration: 0.9, ease: "power3.out", stagger: 0.2 }}, 1.2);
    tl.fromTo("#endcard-rule", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.8, ease: "power2.inOut" }}, 1.4);
    tl.fromTo("#endcard-fade", {{ opacity: 0 }}, {{ opacity: 1, duration: 1.3, ease: "power1.in" }}, {r(END_LEN - 1.4)});
    window.__timelines["endcard"] = tl;
  </script>
</template>
"""


BRIEF = """---
workflow: general-video
flow: automation
storyboard: yes
message: "A warm, real moment from our family's past — {title}"
destination: YouTube Shorts (@irom77), private upload only after confirmation
aspect: "9:16"
language: bilingual (Polish main line, English subtitle)
length: 30–180s (target 45–90s)
---

## Intent
Archival family DV tape `{source}` cut into vertical Shorts. Short #{num} = {title}.

## Customizations
- Framing: blur-fill — full 4:3 picture centred at y=520..1320, blurred copy fills the frame (baked by ffmpeg).
- Enhancement (ffmpeg, CPU): bwdif deinterlace, vidstab, hqdn3d+nlmeans, square pixels, lanczos to 1080x800, unsharp, light grade.
- Audio: original camcorder sound (cleaned, loudnorm). No music.
- Titles: date + occasion title, sparse bilingual chapter captions, end card. No people named.

## Notes
- Output folder: {out_dir}
- No scene may be reused across shorts; ledger in ../plan/.
"""


def main(WORK, num):
    tape = json.loads((WORK / "plan" / "tape.json").read_text())
    copy = json.loads((WORK / "plan" / "copy.json").read_text())[num]
    segs = []
    for line in (WORK / "plan" / f"short{num}.tsv").read_text().splitlines():
        sid, a, b, note = line.split("\t")
        segs.append({"id": sid, "in": float(a), "out": float(b), "note": note})
    proj = WORK / f"short{num}"
    (proj / "compositions").mkdir(parents=True, exist_ok=True)
    clips = proj / "assets" / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    for f in ("hyperframes.json", "CLAUDE.md"):
        shutil.copy(TEMPLATE / f, proj / f)
    shutil.copy(TEMPLATE / "CLAUDE.md", proj / "AGENTS.md")
    (proj / "package.json").write_text((TEMPLATE / "package.json").read_text().replace("__NAME__", f"short{num}"))
    (proj / "meta.json").write_text(json.dumps({"id": f"short{num}", "name": f"short{num}"}, indent=2) + "\n")

    at, videos = 0.0, []
    for i, s in enumerate(segs):
        s["dur"] = r(s["out"] - s["in"])
        s["at"] = r(at)
        src = WORK / "clips" / f"short{num}" / f"seg_{s['id']}.mp4"
        shutil.copy(src, clips / src.name)
        fades = (f' data-fade-in="{FADE}"' if i else "") + \
                f' data-fade-out="{1.2 if i == len(segs) - 1 else FADE}"'
        videos.append(f'      <video id="shot-{s["id"]}" class="clip shot" src="assets/clips/seg_{s["id"]}.mp4" '
                      f'data-start="{s["at"]}" data-duration="{s["dur"]}" data-track-index="0" data-has-audio="true"'
                      f'{fades} playsinline style="z-index: 1"></video>')
        at += s["dur"]
    total = r(at)
    if not 30 <= total <= 180:
        sys.exit(f"short{num}: {total}s is outside 30-180 s")

    t = copy["title"]
    hosts = [("title", 0, TITLE_LEN)]
    (proj / "compositions" / "title.html").write_text(title_html(t))
    by_id = {s["id"]: s for s in segs}
    for c in copy.get("captions", []):
        s = by_id[c["at"]]
        if s["at"] < TITLE_LEN or s["at"] + s["dur"] > total - END_LEN:
            sys.exit(f"caption {c['id']} overlaps the title or end card")
        (proj / "compositions" / f"{c['id']}.html").write_text(caption_html(c["id"], c["pl"], c["en"], s["dur"]))
        hosts.append((c["id"], s["at"], s["dur"]))
    (proj / "compositions" / "endcard.html").write_text(endcard_html(copy.get("end_en", tape["end_en"])))
    hosts.append(("endcard", r(total - END_LEN), END_LEN))
    host_html = [f'      <div id="{h}" data-composition-id="{h}" data-composition-src="compositions/{h}.html" '
                 f'data-start="{a}" data-duration="{d}" data-track-index="1" data-track-kind="graphics" '
                 f'data-width="1080" data-height="1920" style="z-index: 2"></div>' for h, a, d in hosts]

    variables = json.dumps([
        {"id": "title-pl", "type": "string", "label": "Title (PL)", "default": t["pl"]},
        {"id": "date-pl", "type": "string", "label": "Date (PL)", "default": t["date"]},
        {"id": "title-en", "type": "string", "label": "Title (EN)", "default": t["en"]},
    ], ensure_ascii=False).replace("'", "&#39;")  # the attribute is single-quoted
    head = (TEMPLATE / "index_head.html").read_text().replace("__VARIABLES__", variables)
    (proj / "index.html").write_text(f"""{head}<body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="{total}"
      data-width="1080"
      data-height="1920"
    >
      <!-- Footage: enhanced, blur-filled 1080x1920 segments (source timecodes in ../plan/short{num}.tsv) -->
{chr(10).join(videos)}

      <!-- Text scenes -->
{chr(10).join(host_html)}
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
""")
    (proj / "BRIEF.md").write_text(BRIEF.format(title=t["en"], num=int(num), source=Path(tape["source"]).name,
                                                out_dir=tape["out_dir"]))
    (proj / "segments.json").write_text(json.dumps({"total": total, "segments": segs}, ensure_ascii=False, indent=2) + "\n")
    print(f"short{num}: {len(segs)} shots, {total}s, captions: {[c['id'] for c in copy.get('captions', [])]}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    for n in sys.argv[2:]:
        main(Path(sys.argv[1]).resolve(), n.zfill(2))
