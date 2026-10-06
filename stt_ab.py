#!/usr/bin/env python3
"""stt_ab.py — STT-A/B auf den 6 echten Praxis-Diktaten (26.09.2026).
Engines: chirp_3 (IST-Produktion, STT v2 eu) vs. Gemini-Audio-ASR (EU-Endpoint
gemini-3.5-flash, mit/ohne Vokabel-Priming aus der Produktions-MEDICAL_PHRASES-Liste)
vs. gemini-3.8-flash (global, Referenz aus 06.09.). Termini-Hits + Latenz.
"""
import base64, json, pathlib, re, subprocess, sys, time, urllib.request, urllib.error
from google.oauth2 import service_account
import google.auth.transport.requests as gtr

ROOT = pathlib.Path(__file__).parent
PUB = ROOT / "web_app" / "public"
SA = pathlib.Path.home() / ".hermes/secrets/vertex-sa-key.json"
_c = service_account.Credentials.from_service_account_file(str(SA), scopes=["https://www.googleapis.com/auth/cloud-platform"])
import os
_stt = service_account.Credentials.from_service_account_info(json.load(open(os.environ["STT_KEY"]))["stt"], scopes=["https://www.googleapis.com/auth/cloud-platform"]) if os.environ.get("STT_KEY") else None
def stt_tok():
    if _stt is None:
        return tok()
    if not _stt.valid:
        _stt.refresh(gtr.Request())
    return _stt.token
def tok():
    if not _c.valid:
        _c.refresh(gtr.Request())
    return _c.token

PHRASES = json.loads((ROOT / "phrases.json").read_text(encoding="utf-8"))["medical_web"]  # Umbau Schritt 20: phrases.json

# Termini (Stamm, case-insensitive; Alternativen mit |)
TERMS = {
    "test_diktat.ogg": ["handgelenk", "kahnbein|scaphoid|skaphoid", "taille", "fraktur", "dislo", "unauffällig"],
    "test-audio-bws.ogg": ["flachbog", "rechtskonvex", "skoliose", "cobb", "9,5", "th ?4", "th ?8", "schmorl", "edgren", "scheuermann"],
    "mamma_diktat.ogg": ["mammasono", "bi-?rads", "18 ?mm", "axill", "mondor", "hautvenen"],
    "schulter_diktat.ogg": ["sonograph", "schulter", "tenosynovitis", "bizeps", "tendinopathie", "supraspinatus", "unauffällig"],
}

def wav(ogg):
    w = pathlib.Path("/tmp") / (ogg.stem + "_ab.wav")
    subprocess.run(["ffmpeg", "-y", "-i", str(ogg), "-ac", "1", "-ar", "16000", str(w)], capture_output=True)
    return w

def post(url, body, timeout=120):
    p = pathlib.Path("/tmp/stt_ab_body.json"); p.write_text(json.dumps(body))
    req = urllib.request.Request(url, data=p.read_bytes(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + (stt_tok() if "speech" in url else tok())})
    t = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d, time.time() - t

def chirp3(b64):
    d, dt = post("https://eu-speech.googleapis.com/v2/projects/rakscribe/locations/eu/recognizers/_:recognize",
                 {"config": {"languageCodes": ["de-DE"], "model": "chirp_3", "autoDecodingConfig": {},
                             "features": {"enableAutomaticPunctuation": True}}, "content": b64})
    return " ".join(r["alternatives"][0].get("transcript", "") for r in d.get("results", []) if r.get("alternatives")), dt

BASE = "Transkribiere dieses deutsche Radiologie-Diktat (österreichischer Radiologe) wörtlich. Nur der Transkript-Text, keine Kommentare."
PRIMED = BASE + (" Fachvokabular, das vorkommen KANN (nur verwenden, wenn es tatsächlich gesprochen wurde; nichts ergänzen): "
                 + "; ".join(PHRASES))

def gem(model, loc, prompt):
    def f(b64):
        host = {"eu": "https://aiplatform.eu.rep.googleapis.com", "global": "https://aiplatform.googleapis.com",
                "europe-west3": "https://europe-west3-aiplatform.googleapis.com"}[loc]
        gc = {"temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}
        d, dt = post(f"{host}/v1/projects/rakscribe/locations/{loc}/publishers/google/models/{model}:generateContent",
                     {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/wav", "data": b64}}, {"text": prompt}]}],
                      "generationConfig": gc})
        return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought")).strip(), dt
    return f

ENGINES = {
    "chirp_3 (IST)": chirp3,
    "gemini-2.5-flash ew3": gem("gemini-2.5-flash", "europe-west3", BASE),
    "gemini-3.5-flash eu": gem("gemini-3.5-flash", "eu", BASE),
    "gemini-3.5-flash eu +Vokabel": gem("gemini-3.5-flash", "eu", PRIMED),
}

def main():
    print(f"MEDICAL_PHRASES geladen: {len(PHRASES)}")
    res = {}
    for ogg in sorted(PUB.glob("*.ogg")):
        b64 = base64.b64encode(wav(ogg).read_bytes()).decode()
        print(f"\n===== {ogg.name}")
        for name, fn in ENGINES.items():
            try:
                txt, dt = fn(b64)
            except urllib.error.HTTPError as e:
                txt, dt = f"ERR {e.code} {e.read()[:150]}", 0
            except Exception as e:
                txt, dt = f"ERR {e}", 0
            terms = TERMS.get(ogg.name)
            hit = sum(1 for t in terms if re.search(t, txt, re.I)) if terms else None
            res.setdefault(name, []).append({"file": ogg.name, "dt": round(dt, 2), "hit": hit, "n": len(terms) if terms else None, "txt": txt})
            print(f"[{name}] {dt:.1f}s {'' if hit is None else f'{hit}/{len(terms)}'} :: {txt[:400]}")
    print("\n===== SUMME")
    for name, rows in res.items():
        h = sum(r["hit"] for r in rows if r["hit"] is not None); n = sum(r["n"] for r in rows if r["n"])
        dts = sorted(r["dt"] for r in rows if r["dt"])
        print(f"{name:32s} Termini {h}/{n}  Latenz median {dts[len(dts)//2] if dts else 0:.1f}s")
    (ROOT / "stt_ab_results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
