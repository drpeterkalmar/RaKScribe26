#!/usr/bin/env python3
"""tools/chirp_adapt_ab2.py — finale kuratierte chirp_3-PhraseSet-Liste (CHIRP_PHRASES) vs. ohne,
auf den 6 echten Diktaten + 4 say/Anna-Synthesen mit Fachtermini (Regressions-Check)."""
import sys, base64, json, re, subprocess, pathlib, urllib.error
sys.argv = ['x']
import stt_ab as S

CHIRP_PHRASES = [
    # Wirbelsäule
    "flachbogig", "flachbogige Skoliose", "rechtskonvex", "linkskonvex", "Cobb-Winkel",
    "Th1", "Th2", "Th3", "Th4", "Th5", "Th6", "Th7", "Th8", "Th9", "Th10", "Th11", "Th12",
    "Schmorlsche Impressionen", "Edgren-Vaino-Zeichen", "Morbus Scheuermann", "Osteochondrose",
    "Spondylosis deformans", "Spondylarthrose", "Unkovertebralgelenksarthrose", "Facettengelenksarthrose",
    "Discopathiezeichen", "Diskopathie", "Antelisthese", "Retrolisthese", "Neoarthrosis interspinosa",
    "kyphotische Fehlhaltung", "Streckhaltung", "Fibroostosen",
    # Gelenke / Knochen
    "Kellgren und Lawrence", "Gonarthrose", "Coxarthrose", "Omarthrose", "Rhizarthrose",
    "Retropatellararthrose", "Femorotibialkompartiment", "Scaphoidtaille", "Kahnbeintaille",
    "Collum chirurgicum", "Radiusköpfchen", "Humeruskopfhochstand", "Garden",
    # Weichteil-/Sehnen-Sono
    "Supraspinatussehne", "Infraspinatussehne", "Subscapularissehne", "lange Bizepssehne",
    "Tenosynovitis", "Tendinopathie", "Tendinosis calcarea", "Begleitbursitis", "Enthesiopathie",
    "Plantarfaszie", "Arthro-Broström",
    # Mamma / Gefäße / Nerven
    "Mammasonographie", "BI-RADS", "Morbus Mondor", "Sulcus nervi ulnaris", "Nervus ulnaris",
    "Musculus anconeus epitrochlearis", "Hoffmann-Tinel-Zeichen", "Kiloh-Nevin", "Hypothenarmuskulatur",
    "faszikulär", "Thorax p.a.",
]

SYN = {  # say/Anna, Termini
    "syn_lws": ("Lendenwirbelsäule in zwei Ebenen. Flachbogige linkskonvexe Skoliose. Osteochondrose L4 L5. Neoarthrosis interspinosa L3 bis L5. Discopathiezeichen. Ansonsten unauffällig.",
                ["flachbog", "linkskonvex", "osteochondrose", "neoarthros", "discopathie|diskopathie"]),
    "syn_knie": ("Kniegelenk links in zwei Ebenen. Gonarthrose Grad zwei nach Kellgren und Lawrence im medialen Femorotibialkompartiment. Geringgradige Retropatellararthrose.",
                 ["gonarthrose", "kellgren", "lawrence", "femorotibial", "retropatellar"]),
    "syn_fuss": ("Sonographie der Plantarfaszie rechts. Verdickte Plantarfaszie mit Fibroostosen am Ansatz, Enthesiopathie. Zustand nach Arthro-Broström.",
                 ["plantarfaszie", "fibroostos", "enthesiopath", "brostr"]),
    "syn_hand": ("Handgelenk rechts in zwei Ebenen. Rhizarthrose rechts. Keine Fraktur, insbesondere keine Fraktur der Scaphoidtaille. Ansonsten unauffällig.",
                 ["rhizarthrose", "fraktur", "scaphoid|skaphoid|kahnbein", "unauffällig"]),
}


def synth(name, text):
    a = pathlib.Path(f"/tmp/{name}.aiff"); w = pathlib.Path(f"/tmp/{name}.wav")
    subprocess.run(["say", "-v", "Anna", "-o", str(a), text], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(a), "-ar", "16000", "-ac", "1", str(w)], capture_output=True)
    return w


def run(b64, phr, boost=10):
    cfg = {"languageCodes": ["de-DE"], "model": "chirp_3", "autoDecodingConfig": {},
           "features": {"enableAutomaticPunctuation": True}}
    if phr:
        cfg["adaptation"] = {"phraseSets": [{"inlinePhraseSet": {"phrases": [{"value": p, "boost": boost} for p in phr]}}]}
    d, dt = S.post("https://eu-speech.googleapis.com/v2/projects/rakscribe/locations/eu/recognizers/_:recognize",
                   {"config": cfg, "content": b64})
    return " ".join(r["alternatives"][0].get("transcript", "") for r in d.get("results", []) if r.get("alternatives")), dt


items = [(f.name, f, S.TERMS.get(f.name)) for f in sorted(S.PUB.glob("*.ogg"))]
items += [(n, None, t) for n, (_, t) in SYN.items()]
tot = {}
for name, f, terms in items:
    wav = S.wav(f) if f else synth(name, SYN[name][0])
    b64 = base64.b64encode(wav.read_bytes()).decode()
    for label, phr in [("ohne", None), ("curated", CHIRP_PHRASES)]:
        try:
            t, dt = run(b64, phr)
        except urllib.error.HTTPError as e:
            t, dt = f"ERR {e.code} {e.read()[:300]}", 0
        h = sum(1 for x in terms if re.search(x, t, re.I)) if terms else None
        if terms:
            tot.setdefault(label, [0, 0]); tot[label][0] += h; tot[label][1] += len(terms)
        print(f"{name:20s} {label:8s} {dt:.1f}s {'' if h is None else f'{h}/{len(terms)}'} :: {t[:240]}")
print(len(CHIRP_PHRASES), "Phrasen;", tot)
json.dump(CHIRP_PHRASES, open("chirp_phrases.json", "w"), ensure_ascii=False, indent=1)
