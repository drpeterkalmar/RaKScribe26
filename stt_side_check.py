#!/usr/bin/env python3
"""stt_side_check.py — Seiten-Treue (links/rechts) der Audio-ASR-Kandidaten, n Wiederholungen."""
import base64, re, sys, collections
sys.argv = sys.argv[:1]
import stt_ab as S

CASES = {"test_diktat.ogg": ("rechts", "links"), "test-audio-bws.ogg": ("rechtskonvex", "linkskonvex"),
         "mamma_diktat.ogg": ("links", "rechts"), "schulter_diktat.ogg": ("linken", "rechten")}
ENG = {
    "2.5-flash ew3": S.gem("gemini-2.5-flash", "europe-west3", S.BASE),
    "3.5-flash eu": S.gem("gemini-3.5-flash", "eu", S.BASE),
    "3.5-flash-lite eu": S.gem("gemini-3.5-flash-lite", "eu", S.BASE),
    "3.1-flash-lite eu": S.gem("gemini-3.1-flash-lite", "eu", S.BASE),
}
N = 3
for f, (good, bad) in CASES.items():
    b64 = base64.b64encode(S.wav(S.PUB / f).read_bytes()).decode()
    for name, fn in ENG.items():
        c = collections.Counter(); dts = []
        for _ in range(N):
            try:
                t, dt = fn(b64); dts.append(dt)
            except Exception as e:
                c["ERR"] += 1; continue
            tl = t.lower()
            if re.search(r"\b" + bad, tl) and not re.search(r"\b" + good, tl):
                c["FALSCH"] += 1
            elif re.search(r"\b" + good, tl):
                c["ok"] += 1
            else:
                c["fehlt"] += 1
        print(f"{f:22s} {name:18s} {dict(c)}  median {sorted(dts)[len(dts)//2] if dts else 0:.1f}s")
