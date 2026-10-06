#!/usr/bin/env python3
"""meddictate_bench.py — unabhängiger STT-Benchmark auf Corti MedDictate (de), 04.10.2026.

Datensatz: https://huggingface.co/datasets/corti/med-dictate (9 deutsche Diktate, 107–450 s,
3 davon Radiologie: MRT Gehirn, CT Abdomen, MRT LWS; mit annotierten Fachtermini).
ElevenLabs publizierte darauf (Blog 22.09.2026, DE-Spalte): Scribe v2 Medical 7,2 % WER,
GPT Transcribe 9,6 %, Scribe v2 base 11,7 %, Muse Voice 13,3 %. Dieses Skript misst die
Engines, die RaKScribe mit dem Praxis-Key erreichen kann, mit derselben Daten-Grundlage:
  - chirp_3 + CHIRP_PHRASES (IST-Produktion; >60 s → 50 s-Segmente + 4 s Overlap, Stitch wie App)
  - gemini-3.5-transcribe-preview (Vertex global, ganze Datei, ± customVocabulary)

Metriken: WER gegen `transcription_formatted` (normalisiert: lowercase, Umlaute, Satzzeichen
raus) und Term-Recall (Anteil der `medical_terms_formatted`, die normalisiert im Transkript
vorkommen). WER-Zahlen sind NICHT 1:1 mit ElevenLabs' Tabelle vergleichbar (andere
Normalisierung) — Term-Recall ist die robustere Vergleichsgröße.

Aufruf:  STT_KEY=.praxis-key.tmp.json /usr/bin/python3 meddictate_bench.py [--only-radiology]
"""
import base64, difflib, json, os, pathlib, re, subprocess, sys, time, urllib.request, urllib.error
from google.oauth2 import service_account
import google.auth.transport.requests as gtr

ROOT = pathlib.Path(__file__).parent
SCR = pathlib.Path(os.environ.get("TMPDIR", str(pathlib.Path.home() / ".hermes/cache/scratch")))
DATA = SCR / "meddictate"
AUD = DATA / "audio"
ONLY_RAD = "--only-radiology" in sys.argv
RADIOLOGY = {"sample_3", "sample_7", "sample_8"}

SA = pathlib.Path.home() / ".hermes/secrets/vertex-sa-key.json"
_c = service_account.Credentials.from_service_account_file(str(SA), scopes=["https://www.googleapis.com/auth/cloud-platform"])
PR = json.load(open(os.environ["STT_KEY"]))
_stt = service_account.Credentials.from_service_account_info(PR["stt"], scopes=["https://www.googleapis.com/auth/cloud-platform"])

def tok(c):
    if not c.valid:
        c.refresh(gtr.Request())
    return c.token

CHIRP_PHRASES = json.loads((ROOT / "phrases.json").read_text(encoding="utf-8"))["chirp"]  # Umbau Schritt 20: phrases.json

def ensure_data():
    AUD.mkdir(parents=True, exist_ok=True)
    pq_file = DATA / "de.parquet"
    if not pq_file.exists():
        subprocess.run(["curl", "-sL", "-o", str(pq_file), "https://huggingface.co/datasets/corti/med-dictate/resolve/main/de/test-00000-of-00001.parquet"], check=True)
    if not list(AUD.glob("*.json")):
        import pyarrow.parquet as pq
        for row in pq.read_table(str(pq_file)).to_pylist():
            a = row["audio"]
            (AUD / f"{row['id']}.wav").write_bytes(a["bytes"])
            json.dump({k: row[k] for k in ("id", "transcription", "transcription_formatted", "medical_terms", "medical_terms_formatted")},
                      open(AUD / f"{row['id']}.json", "w"), ensure_ascii=False)

def norm(t):
    t = t.lower().replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()

def wer(ref, hyp):
    rw, hw = norm(ref).split(), norm(hyp).split()
    sm = difflib.SequenceMatcher(None, rw, hw, autojunk=False)
    matched = sum(b.size for b in sm.get_matching_blocks())
    return (max(len(rw), len(hw)) - matched) / max(len(rw), 1)

def term_recall(terms, hyp):
    h = " " + norm(hyp) + " "
    hits = [t for t in terms if " " + norm(t) + " " in h or norm(t) in h]
    return len(hits), len(terms), [t for t in terms if t not in hits]

def duration(wav):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)], capture_output=True, text=True).stdout.strip()
    return float(out)

def post(url, body, headers, timeout=300):
    p = SCR / "meddictate_body.json"; p.write_text(json.dumps(body))
    for attempt, pause in enumerate((0, 20, 45, 90, 120)):
        if pause:
            time.sleep(pause)
        req = urllib.request.Request(url, data=p.read_bytes(), headers={"Content-Type": "application/json", **headers})
        t = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read()), time.time() - t
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 4:
                print(f"    … HTTP {e.code}, Retry in {((0, 20, 45, 90, 120)[attempt + 1])} s")
                continue
            raise

def chirp3_segment(wav_b64):
    d, dt = post("https://eu-speech.googleapis.com/v2/projects/rakscribe/locations/eu/recognizers/_:recognize",
                 {"config": {"languageCodes": ["de-DE"], "model": "chirp_3", "autoDecodingConfig": {},
                             "features": {"enableAutomaticPunctuation": True},
                             "adaptation": {"phraseSets": [{"inlinePhraseSet": {"phrases": [{"value": v, "boost": 10} for v in CHIRP_PHRASES]}}]}},
                  "content": wav_b64}, {"Authorization": "Bearer " + tok(_stt)})
    return " ".join(r["alternatives"][0].get("transcript", "") for r in d.get("results", []) if r.get("alternatives")), dt

def stitch(a, b, window=14):
    """Wie App.tsx stitchOverlaps: längste gemeinsame Wortfolge zwischen Ende von a und Anfang von b."""
    aw, bw = a.split(), b.split()
    ta, hb = aw[-window:], bw[:window]
    sm = difflib.SequenceMatcher(None, [norm(x) for x in ta], [norm(x) for x in hb], autojunk=False)
    m = sm.find_longest_match(0, len(ta), 0, len(hb))
    if m.size >= 3:
        return " ".join(aw[:len(aw) - len(ta) + m.a + m.size] + bw[m.b + m.size:])
    return a + " " + b

def chirp3_full(wav):
    dur = duration(wav)
    if dur <= 59:
        return chirp3_segment(base64.b64encode(wav.read_bytes()).decode())
    parts, total_dt, start = [], 0.0, 0.0
    while start < dur:
        seg = SCR / "md_seg.wav"
        subprocess.run(["ffmpeg", "-y", "-i", str(wav), "-ss", f"{start:.2f}", "-t", "50", "-ac", "1", "-ar", "16000", str(seg)], capture_output=True)
        txt, dt = chirp3_segment(base64.b64encode(seg.read_bytes()).decode())
        parts.append(txt); total_dt += dt
        start += 46  # 50 s Fenster, 4 s Rückhören
    out = parts[0]
    for p in parts[1:]:
        out = stitch(out, p)
    return out, total_dt

def g35t(wav, vocab):
    flac = SCR / "md.flac"
    subprocess.run(["ffmpeg", "-y", "-i", str(wav), "-ac", "1", "-ar", "16000", str(flac)], capture_output=True)
    b64 = base64.b64encode(flac.read_bytes()).decode()
    cfg = {"languageCodes": ["de-DE"]}
    if vocab:
        cfg["customVocabulary"] = CHIRP_PHRASES
    d, dt = post("https://aiplatform.googleapis.com/v1/projects/rakscribe/locations/global/publishers/google/models/gemini-3.5-transcribe-preview:generateContent",
                 {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/flac", "data": b64}}]}],
                  "generationConfig": {"audioTranscriptionConfig": cfg}}, {"Authorization": "Bearer " + tok(_c)})
    parts = d["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts if not p.get("thought")).strip(), dt

ENGINES = {
    "chirp_3 +PhraseSet (IST)": chirp3_full,
    "gemini-3.5-transcribe": lambda w: g35t(w, False),
    "gemini-3.5-transcribe +Vokabel": lambda w: g35t(w, True),
}

def main():
    ensure_data()
    res = {}
    for meta in sorted(AUD.glob("*.json")):
        m = json.load(open(meta))
        sid = m["id"]
        if ONLY_RAD and sid not in RADIOLOGY:
            continue
        wav = AUD / f"{sid}.wav"
        dur = duration(wav)
        print(f"\n===== {sid} ({dur:.0f} s{', RADIOLOGIE' if sid in RADIOLOGY else ''}) — {m['transcription_formatted'][:90]!r}")
        for name, fn in ENGINES.items():
            try:
                txt, dt = fn(wav)
            except urllib.error.HTTPError as e:
                txt, dt = f"ERR {e.code} {e.read()[:200]}", 0
            except Exception as e:
                txt, dt = f"ERR {e}", 0
            if txt.startswith("ERR"):
                print(f"  [{name}] {txt}")
                res.setdefault(name, []).append({"id": sid, "err": txt})
                continue
            w = wer(m["transcription_formatted"], txt)
            w_raw = wer(m["transcription"], txt)  # Roh-Referenz mit wörtlichen Diktierkommandos (Doppelpunkt, neue Zeile, Zahlen als Wörter)
            hit, n, missed = term_recall(m["medical_terms_formatted"], txt)
            hit_raw, _, _ = term_recall(m["medical_terms"], txt)
            res.setdefault(name, []).append({"id": sid, "radiology": sid in RADIOLOGY, "dur": dur, "dt": round(dt, 1), "wer": round(100 * w, 1),
                                             "wer_raw": round(100 * w_raw, 1), "wer_best": round(100 * min(w, w_raw), 1),
                                             "term_hit": max(hit, hit_raw), "term_n": n, "missed": missed, "txt": txt})
            print(f"  [{name}] {dt:5.1f}s  WER fmt {100*w:5.1f} % / roh {100*w_raw:5.1f} %  Termini {max(hit, hit_raw)}/{n}  fehlend z.B.: {missed[:6]}")
    print("\n===== SUMME (einfacher Mittelwert über Diktate; WER_best = min(formatiert, roh) je Diktat)")
    # Paarweise: nur Diktate, die bei ALLEN Engines ohne Fehler durchliefen
    common = None
    for rows in res.values():
        ids = {r["id"] for r in rows if "err" not in r}
        common = ids if common is None else common & ids
    for name, rows in res.items():
        ok = [r for r in rows if "err" not in r]
        for label, sel in (("alle", ok), ("paarweise", [r for r in ok if r["id"] in (common or set())]), ("Radiologie", [r for r in ok if r["radiology"]])):
            if not sel:
                continue
            w = sum(r["wer_best"] for r in sel) / len(sel)
            th = sum(r["term_hit"] for r in sel); tn = sum(r["term_n"] for r in sel)
            dt = sum(r["dt"] for r in sel) / len(sel)
            print(f"{name:34s} {label:10s} n={len(sel)}  WER_best Ø {w:5.1f} %  Term-Recall {100*th/tn:5.1f} % ({th}/{tn})  Ø Latenz {dt:5.1f} s  ERR {len(rows)-len(ok)}")
    (ROOT / "meddictate_bench_results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
