"""Voice the narration in script.json with Kokoro-82M and write timing.json + narration.wav.

Each phrase is voiced on its own, trimmed, and laid end to end with fixed gaps, so the
animation knows exactly when every phrase starts. The boy voice is a blend of two Kokoro
voices plus a pitch lift that is applied later by ffmpeg (see VOICE_FILTER).

Usage: python narrate.py MODEL.onnx VOICES.npz OUT_DIR
"""
import json, os, sys
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
MIX = [("am_liam", 0.42), ("af_sky", 0.58)]
# Pitch lift by plain resampling only (no time-stretch, so no warble): voiced slower by LIFT,
# then played back LIFT times faster. 1.12 is about two semitones.
LIFT = 1.12
SPEED = 1.1 / LIFT
GAP, SCENE_IN, SCENE_OUT = 0.26, 0.3, 0.6
# narration_raw.wav is already lifted (written at 24000*LIFT Hz); this only converts it for the mp3.
VOICE_FILTER = "aresample=48000"


def trim(a, sr, thr=0.012):
    idx = np.where(np.abs(a) > thr)[0]
    if not len(idx):
        return a
    s, e = max(idx[0] - int(.02 * sr), 0), min(idx[-1] + int(.06 * sr), len(a))
    return a[s:e]


def main(model, voices, out):
    k = Kokoro(model, voices)
    style = sum(k.get_voice_style(v) * w for v, w in MIX)
    script = json.load(open(os.path.join(HERE, "script.json")))
    sr = 24000
    eff = sr * LIFT  # playback rate: every duration below is in played-back seconds
    chunks, t, timing = [], 0.0, []
    for sc in script:
        start = t
        chunks.append(np.zeros(int(SCENE_IN * eff))); t += SCENE_IN
        phrases = []
        for i, text in enumerate(sc["phrases"]):
            a, sr = k.create(text, voice=style, speed=SPEED, lang="en-us")
            a = trim(a, sr)
            phrases.append({"text": text, "t": round(t, 3), "d": round(len(a) / eff, 3)})
            chunks.append(a); t += len(a) / eff
            gap = GAP if i < len(sc["phrases"]) - 1 else SCENE_OUT
            chunks.append(np.zeros(int(gap * eff))); t += gap
        timing.append({"id": sc["id"], "t": round(start, 3), "d": round(t - start, 3), "phrases": phrases})
        print(sc["id"], round(t - start, 2))
    sf.write(os.path.join(out, "narration_raw.wav"), np.concatenate(chunks).astype(np.float32), int(round(eff)))
    json.dump(timing, open(os.path.join(out, "timing.json"), "w"), indent=1)
    print("total", round(t, 2))


if __name__ == "__main__":
    main(*sys.argv[1:4])
