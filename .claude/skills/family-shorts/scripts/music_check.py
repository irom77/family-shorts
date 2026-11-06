#!/usr/bin/env python3
"""Find recorded music in a short's audio before upload, and mute it.

Background music at a party (a DJ, a radio, a record) is somebody's recording: YouTube's Content ID
matches it and puts a copyright claim on the short. Live singing by people on the tape is fine.

  music_check.py <file.mp4> [...]                 one line per file: a per-second map + music ranges
  music_check.py <file.mp4> --mute <out.mp4>      copy with the music muted (video copied as is)

Map: '#' music likely, '+' possible, '.' none. Uses YAMNet (AudioSet classes) through MediaPipe,
CPU only. Run with:
  uv run -q --no-project --python 3.12 --with mediapipe python music_check.py …
The model (4 MB) is downloaded once to ~/.cache/family-shorts/yamnet.tflite.
"""
import argparse
import subprocess
import sys
import tempfile
import urllib.request
import wave
from pathlib import Path

import numpy as np

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/1/yamnet.tflite"
MODEL = Path.home() / ".cache" / "family-shorts" / "yamnet.tflite"
FADE = 0.3


def model():
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    return str(MODEL)


def scores(clf, path):
    """Music score per second of the file's audio."""
    from mediapipe.tasks.python.components.containers import audio_data
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "a.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(path), "-vn", "-ac", "1",
                        "-ar", "16000", str(wav)], check=True)
        w = wave.open(str(wav))
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    res = clf.classify(audio_data.AudioData.create_from_array(a, 16000))
    return [next((c.score for c in r.classifications[0].categories if c.category_name == "Music"), 0.0)
            for r in res]


def ranges(sc, gap=3):
    """Seconds scoring > 0.2 (music possible), merged across gaps of < gap s, as (start, end) pairs."""
    out = []
    for i, v in enumerate(sc):
        if v > 0.2:
            if out and i - out[-1][1] < gap:
                out[-1][1] = i + 1
            else:
                out.append([i, i + 1])
    return [tuple(r) for r in out]


def mute(src, dst, rs, dur):
    if not rs:
        af = "anull"
    elif sum(b - a for a, b in rs) > 0.6 * dur:
        af = "volume=0"  # mostly music: silence it all rather than leave chopped islands of sound
    else:
        # Duck each range to silence with short fades: volume follows a piecewise envelope.
        terms = []
        for a, b in rs:
            a0, b1 = max(a - FADE, 0), b + FADE
            terms.append(f"if(between(t,{a},{b}),0,if(between(t,{a0},{a}),({a}-t)/{FADE},"
                         f"if(between(t,{b},{b1}),(t-{b})/{FADE},1)))")
        af = "volume='" + "*".join(f"({x})" for x in terms) + "':eval=frame"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-map", "0", "-c:v", "copy",
                    "-af", af, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)], check=True)
    return af == "volume=0"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+")
    p.add_argument("--mute", help="write a copy of the (single) input with the music muted")
    a = p.parse_args()
    if a.mute and len(a.files) != 1:
        sys.exit("--mute takes one input file")
    from mediapipe.tasks.python import audio
    from mediapipe.tasks.python.core import base_options
    opts = audio.AudioClassifierOptions(base_options=base_options.BaseOptions(model_asset_path=model()),
                                        max_results=-1, running_mode=audio.RunningMode.AUDIO_CLIPS)
    with audio.AudioClassifier.create_from_options(opts) as clf:
        for f in a.files:
            sc = scores(clf, f)
            rs = ranges(sc)
            m = "".join("#" if v > .5 else "+" if v > .2 else "." for v in sc)
            print(f"{Path(f).name}\t{sum(b - x for x, b in rs)}s music\t{rs}\n  {m}", flush=True)
            if a.mute:
                whole = mute(f, a.mute, rs, len(sc))
                print(f"muted {'all' if whole else rs} -> {a.mute}")


if __name__ == "__main__":
    main()
