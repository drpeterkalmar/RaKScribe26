#!/usr/bin/env python3
"""stt_ab_g35t.py — STT-A/B (04.10.2026): chirp_3 (IST-Produktion, STT v2 eu, CHIRP_PHRASES
boost 10) vs. Gemini 3.5 Transcribe (gemini-3.5-transcribe-preview, Vertex `global`,
mit/ohne custom_vocabulary = CHIRP_PHRASES) auf den 6 echten Praxis-Diktaten.

Misst je Engine: Termini-Hits, WER gegen Referenz (4 Diktate), Seiten-Treue (links/rechts,
n Wiederholungen — LLM-ASR-Pitfall!), Latenz. Zusätzlich: läuft Gemini 3.5 Transcribe mit
dem Praxis-AQ-Key (x-goog-api-key, EIN-Key-Prinzip) statt SA-Bearer?

Aufruf:  STT_KEY=.praxis-key.tmp.json /usr/bin/python3 stt_ab_g35t.py [runs=3]
"""
import base64, difflib, json, os, pathlib, re, subprocess, sys, time, urllib.request, urllib.error
from google.oauth2 import service_account
import google.auth.transport.requests as gtr

ROOT = pathlib.Path(__file__).parent
PUB = ROOT / "web_app" / "public"
SCRATCH = pathlib.Path(os.environ.get("TMPDIR", str(pathlib.Path.home() / ".hermes/cache/scratch")))
SCRATCH.mkdir(parents=True, exist_ok=True)
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 3

SA = pathlib.Path.home() / ".hermes/secrets/vertex-sa-key.json"
_c = service_account.Credentials.from_service_account_file(str(SA), scopes=["https://www.googleapis.com/auth/cloud-platform"])
PRAXIS = json.load(open(os.environ["STT_KEY"])) if os.environ.get("STT_KEY") else None
_stt = service_account.Credentials.from_service_account_info(PRAXIS["stt"], scopes=["https://www.googleapis.com/auth/cloud-platform"]) if PRAXIS else None
AQ = PRAXIS.get("vertex_api_key") if PRAXIS else None

def tok(c):
    if not c.valid:
        c.refresh(gtr.Request())
    return c.token

CHIRP_PHRASES = json.loads((ROOT / "phrases.json").read_text(encoding="utf-8"))["chirp"]  # Umbau Schritt 20: phrases.json

# Referenzen (radiologist-verified, fast-stt/references + Skill) — für WER
REF = {
    "test_diktat.ogg": "Handgelenk Röntgen rechts nicht dislozierte Fraktur der Scaphoidtaille ansonsten unauffälliger Befund",
    "test-audio-bws.ogg": "BWS Röntgen flachbogig rechtskonvexe Skoliose der laterale Cobb-Winkel beträgt 9,5 Grad gemessen an der Oberkante Th4 gegenüber Oberkante Th8 multisegmentale Schmorlsche Impressionen mit Edgren-Vaino-Zeichen als Zeichen für Zustand nach Morbus Scheuermann ansonsten unauffällig",
    "mamma_diktat.ogg": "Mammasonographie beidseits thrombosierte Hautvenen links im axillären Quadranten auslaufend in die linke Axilla bis 18 mm Durchmesser im Sinne eines Morbus Mondor ansonsten beidseits unauffällig BI-RADS 2",
    "schulter_diktat.ogg": "Röntgen und Sonographie des linken Schultergelenkes Tenosynovitis der langen Bizepssehne Tendinopathie und Tendinosis calcarea der Supraspinatussehne mit Begleitbursitis ansonsten unauffällig",
}
TERMS = {
    "test_diktat.ogg": ["handgelenk", "scaphoid|skaphoid|kahnbein", "taille", "fraktur", "dislo", "unauffällig"],
    "test-audio-bws.ogg": ["flachbog", "rechtskonvex", "skoliose", "cobb", "9,5", "th ?4", "th ?8", "schmorl", "edgren", "scheuermann"],
    "mamma_diktat.ogg": ["mammasono", "bi-?rads", "18 ?mm", "axill", "mondor", "hautvenen"],
    "schulter_diktat.ogg": ["sonograph", "schulter", "tenosynovitis", "bizeps", "tendinopathie", "supraspinatus", "unauffällig"],
    "test_diktat2.ogg": ["sonograph", "schulter", "tenosynovitis", "bizeps", "tendinopathie", "supraspinatus", "unauffällig"],
    "test-audio.ogg": ["baustein", "ulnaris", "querschnittsfläche", "sulcus", "15", "anconeus", "epitrochlearis", "kompression", "ellbogen"],
}
# Seiten-Wahrheit: Muster, das vorkommen MUSS / NICHT vorkommen darf
SIDE = {
    "test_diktat.ogg": (r"\brechts\b", r"\blinks\b"),
    "test-audio-bws.ogg": (r"rechtskonvex", r"linkskonvex"),
    "mamma_diktat.ogg": (r"\blinks\b|linke Axilla", r"\brechts\b|rechte Axilla"),
    "schulter_diktat.ogg": (r"linken Schulter", r"rechten Schulter"),
    "test_diktat2.ogg": (r"linken Schulter", r"rechten Schulter"),
}

def wer(ref, hyp):
    def norm(t):
        t = t.lower().replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
        return re.sub(r"[^\w\s]", " ", t)
    rw, hw = norm(ref).split(), norm(hyp).split()
    sm = difflib.SequenceMatcher(None, rw, hw)
    matched = sum(b.size for b in sm.get_matching_blocks())
    return (max(len(rw), len(hw)) - matched) / max(len(rw), 1)

def wav(ogg):
    w = SCRATCH / (ogg.stem + "_g35t.wav")
    if not w.exists():
        subprocess.run(["ffmpeg", "-y", "-i", str(ogg), "-ac", "1", "-ar", "16000", str(w)], capture_output=True)
    return w

def post(url, body, headers, timeout=120):
    p = SCRATCH / "stt_ab_g35t_body.json"; p.write_text(json.dumps(body))
    req = urllib.request.Request(url, data=p.read_bytes(), headers={"Content-Type": "application/json", **headers})
    t = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d, time.time() - t

def chirp3(b64):
    if _stt is None:
        raise RuntimeError("STT_KEY (Praxis-Key) nötig — vertex-sa hat kein speech-Recht")
    d, dt = post("https://eu-speech.googleapis.com/v2/projects/rakscribe/locations/eu/recognizers/_:recognize",
                 {"config": {"languageCodes": ["de-DE"], "model": "chirp_3", "autoDecodingConfig": {},
                             "features": {"enableAutomaticPunctuation": True},
                             "adaptation": {"phraseSets": [{"inlinePhraseSet": {"phrases": [{"value": v, "boost": 10} for v in CHIRP_PHRASES]}}]}},
                  "content": b64}, {"Authorization": "Bearer " + tok(_stt)})
    return " ".join(r["alternatives"][0].get("transcript", "") for r in d.get("results", []) if r.get("alternatives")), dt

def g35t(vocab, auth="sa"):
    def f(b64):
        url = "https://aiplatform.googleapis.com/v1/projects/rakscribe/locations/global/publishers/google/models/gemini-3.5-transcribe-preview:generateContent"
        cfg = {"languageCodes": ["de-DE"]}
        if vocab:
            cfg["customVocabulary"] = CHIRP_PHRASES
        body = {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/wav", "data": b64}}]}],
                "generationConfig": {"audioTranscriptionConfig": cfg}}
        hdr = {"x-goog-api-key": AQ} if auth == "aq" else {"Authorization": "Bearer " + tok(_c)}
        d, dt = post(url, body, hdr)
        parts = d["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if not p.get("thought")).strip(), dt
    return f

ENGINES = {
    "chirp_3 +PhraseSet (IST)": chirp3,
    "g3.5-transcribe global": g35t(False),
    "g3.5-transcribe global +Vokabel": g35t(True),
}
if AQ:
    ENGINES["g3.5-transcribe global +Vokabel (AQ-Key)"] = g35t(True, auth="aq")

def main():
    print(f"CHIRP_PHRASES: {len(CHIRP_PHRASES)} | runs={RUNS} | Praxis-Key: {'ja' if PRAXIS else 'NEIN'}")
    res = {}
    for ogg in sorted(PUB.glob("*.ogg")):
        b64 = base64.b64encode(wav(ogg).read_bytes()).decode()
        print(f"\n===== {ogg.name}")
        for name, fn in ENGINES.items():
            for run in range(RUNS):
                try:
                    txt, dt = fn(b64)
                except urllib.error.HTTPError as e:
                    txt, dt = f"ERR {e.code} {e.read()[:200]}", 0
                except Exception as e:
                    txt, dt = f"ERR {e}", 0
                terms = TERMS.get(ogg.name, [])
                hit = sum(1 for t in terms if re.search(t, txt, re.I))
                w = round(100 * wer(REF[ogg.name], txt), 1) if ogg.name in REF and not txt.startswith("ERR") else None
                side = None
                if ogg.name in SIDE and not txt.startswith("ERR"):
                    must, mustnot = SIDE[ogg.name]
                    side = bool(re.search(must, txt, re.I)) and not re.search(mustnot, txt, re.I)
                res.setdefault(name, []).append({"file": ogg.name, "run": run, "dt": round(dt, 2), "hit": hit, "n": len(terms), "wer": w, "side_ok": side, "txt": txt})
                if run == 0 or txt != res[name][-2]["txt"]:
                    print(f"[{name}] r{run} {dt:.1f}s {hit}/{len(terms)} WER={w} side={side} :: {txt[:300]}")
                else:
                    print(f"[{name}] r{run} {dt:.1f}s (identisch)")
    print("\n===== SUMME")
    for name, rows in res.items():
        ok = [r for r in rows if not r["txt"].startswith("ERR")]
        h = sum(r["hit"] for r in ok); n = sum(r["n"] for r in ok)
        ws = [r["wer"] for r in ok if r["wer"] is not None]
        sides = [r["side_ok"] for r in ok if r["side_ok"] is not None]
        dts = sorted(r["dt"] for r in ok if r["dt"])
        err = len(rows) - len(ok)
        print(f"{name:42s} Termini {h}/{n}  WER Ø {sum(ws)/len(ws) if ws else float('nan'):.1f} %  Seite ok {sum(sides)}/{len(sides)}  Latenz median {dts[len(dts)//2] if dts else 0:.1f}s  ERR {err}")
    (ROOT / "stt_ab_g35t_results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
