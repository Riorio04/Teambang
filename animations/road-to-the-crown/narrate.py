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
MIX = [("am_liam", 0.5), ("af_sky", 0.5)]
SPEED = 1.1
GAP, SCENE_IN, SCENE_OUT = 0.26, 0.3, 0.6
# Raises pitch 1.42x keeping resonance, then 1.22x pitch + resonance together: ~265 Hz, a young boy's range.
VOICE_FILTER = "rubberband=pitch=1.42:formant=preserved:pitchq=quality,asetrate=24000*1.22,aresample=24000,atempo=1/1.22"


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
    chunks, t, timing = [], 0.0, []
    for sc in script:
        start = t
        chunks.append(np.zeros(int(SCENE_IN * sr))); t += SCENE_IN
        phrases = []
        for i, text in enumerate(sc["phrases"]):
            a, sr = k.create(text, voice=style, speed=SPEED, lang="en-us")
            a = trim(a, sr)
            phrases.append({"text": text, "t": round(t, 3), "d": round(len(a) / sr, 3)})
            chunks.append(a); t += len(a) / sr
            gap = GAP if i < len(sc["phrases"]) - 1 else SCENE_OUT
            chunks.append(np.zeros(int(gap * sr))); t += gap
        timing.append({"id": sc["id"], "t": round(start, 3), "d": round(t - start, 3), "phrases": phrases})
        print(sc["id"], round(t - start, 2))
    sf.write(os.path.join(out, "narration_raw.wav"), np.concatenate(chunks).astype(np.float32), sr)
    json.dump(timing, open(os.path.join(out, "timing.json"), "w"), indent=1)
    print("total", round(t, 2))


if __name__ == "__main__":
    main(*sys.argv[1:4])
