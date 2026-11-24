#!/usr/bin/env python3
"""tools/stt_mistral/voxtral_ab.py — Mistral Voxtral (Endtext) gegen chirp_3 messen (stt-mistral-vergleich-n1, 24.11.2026).

Ziel: Entscheidungsgrundlage „von Google auf eine EU-Alternative wechseln?“ – KEIN Umbau von KaiScribe.

Regeln (Brief stt-mistral-vergleich-n1):
- Google-Testkosten hart 0 $: dieses Skript ruft Google NIE auf. chirp_3-Vergleichswerte kommen aus vorhandenen
  Ergebnissen (docs/benchmarks/stt_mistral/chirp3_basis_20261004.json = chirp_3-Teil von stt_ab_g35t, 6 Oggs × 3 Läufe).
- Mistral-Testdeckel 5 € (MISTRAL_TEST_LIMIT_EUR, nur senken). Kosten = Audiominuten × Listenpreis, Buch als JSONL.
- Datenschutz: ohne bestätigten bezahlten Tarif + AVV + keine Trainingsnutzung NUR Material ohne Patientenbezug:
  web_app/public/*.ogg (Sprachnachricht-Diktate) und synthetische say/Anna-Befundtexte (SYN unten, frei formuliert).
  Echte Praxisdiktate (--echt <ordner>) nur mit MISTRAL_AVV_BESTAETIGT=<Datum der Bestätigung>.

Aufruf
  python3 tools/stt_mistral/voxtral_ab.py --modelle           # Transkriptionsmodelle des Kontos auflisten
  python3 tools/stt_mistral/voxtral_ab.py [--laeufe 3]        # Messung public-Oggs + Synthetik, 3 Listen-Varianten
  python3 tools/stt_mistral/voxtral_ab.py --trocken           # ohne Netz: „Erkenner“ gibt die Referenz zurück (Harness-Test)
  python3 tools/stt_mistral/voxtral_ab.py --nur-chirp         # nur die chirp_3-Basiswerte auswerten (0 Aufrufe)

Schlüssel: MISTRAL_API_KEY oder Vaultwarden-Eintrag VW_NAME (vw_get.get_login). Modell: MISTRAL_STT_MODEL
(Standard voxtral-mini-latest = Batch-Transkription über /v1/audio/transcriptions).
"""
import argparse
import ast
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
PUB = ROOT / "web_app" / "public"
OUT = ROOT / "docs" / "benchmarks" / "stt_mistral"
BASIS = OUT / "chirp3_basis_20261004.json"
SCRATCH = pathlib.Path(os.environ.get("TMPDIR", str(pathlib.Path.home() / ".hermes/cache/scratch"))) / "voxtral_ab"
API = os.environ.get("MISTRAL_API_BASE", "https://api.mistral.ai")
MODELL = os.environ.get("MISTRAL_STT_MODEL", "voxtral-mini-latest")
VW_NAME = "Mistral API KaiScribe"
# Listenpreise (stt-quality-testing.md, mistral.ai Nov 2026): Batch 0,004 $/min, Realtime 0,008 $/min
PREIS_USD_MIN = {"batch": 0.004, "realtime": 0.008}
USD_EUR = 0.95
LIMIT_EUR = min(5.0, float(os.environ.get("MISTRAL_TEST_LIMIT_EUR", "5")))
BIAS_MAX = int(os.environ.get("MISTRAL_BIAS_MAX", "100"))  # Obergrenze Einträge context_bias (API-Grenze prüfen)

# Peters echte Minuten, Woche 17.–23.11.2026 (SKU-Bericht): Endtext 102 min, Live 125 min
WOCHE_ENDTEXT_MIN, WOCHE_LIVE_MIN = 102, 125
MONAT_FAKTOR = 365.25 / 12 / 7


def _konstanten(datei, *namen):
    """REF/TERMS/SIDE bzw. SYN aus den bestehenden A/B-Skripten lesen (eine Quelle, ohne deren Google-Importe)."""
    baum = ast.parse(pathlib.Path(datei).read_text(encoding="utf-8"))
    out = {}
    for k in baum.body:
        if isinstance(k, ast.Assign) and isinstance(k.targets[0], ast.Name) and k.targets[0].id in namen:
            out[k.targets[0].id] = ast.literal_eval(k.value)
    return out


_K = _konstanten(ROOT / "tools" / "stt_ab_g35t.py", "REF", "TERMS", "SIDE")
REF, TERMS, SIDE = _K["REF"], _K["TERMS"], _K["SIDE"]
REF["test_diktat2.ogg"] = REF["schulter_diktat.ogg"]  # gleicher Wortlaut (chirp_3-Text identisch)
# test-audio.ogg: Referenz aus dem chirp_3-Text, von Hand geprüft (Kommandos „Punkt“ als Wort)
REF["test-audio.ogg"] = ("Befund Nervus ulnaris deutlich vergrößerte Querschnittsfläche des Nervs am Sulcus nervi ulnaris mit 15 "
                         "Quadratmillimeter Punkt zusätzlicher hypertropher Musculus anconeus epitrochlearis als anatomische "
                         "Variante mit Kompression des Nervs am Sulcus Punkt bei Ellbogen Flexion Aggravation der Kompression Punkt")

_S = _konstanten(ROOT / "tools" / "chirp_adapt_ab2.py", "SYN")["SYN"]
# Synthetische Befundtexte im Hausstil, frei formuliert (keine Namen, Daten, Patientenbezug); bewusst mit Seiten,
# Zahlen/Maßen und Verneinungen. Gesprochen von macOS „Anna“.
SYN = {k: v[0] for k, v in _S.items()}
SYN.update({
    "syn_schulter_re": "Sonographie der rechten Schulter. Keine Ruptur der Supraspinatussehne. Tendinosis calcarea mit einem "
                       "Kalkdepot von 12 mal 4 Millimeter. Kein Erguss in der Bursa subacromialis. Die lange Bizepssehne "
                       "liegt regelrecht im Sulcus.",
    "syn_mammo": "Mammographie beidseits in zwei Ebenen. Involutionsmammae, ACR Typ B. Kein Herdbefund, kein suspekter "
                 "Mikrokalk. Links bei zwei Uhr eine Zyste mit 8 Millimeter Durchmesser. BIRADS 2 beidseits.",
    "syn_bws_li": "Brustwirbelsäule in zwei Ebenen. Flachbogige linkskonvexe Skoliose mit einem Cobb-Winkel von 14 Grad "
                  "zwischen Th6 und Th11. Keine Wirbelkörperhöhenminderung. Multisegmentale Spondylosis deformans.",
    "syn_huefte": "Beckenübersicht und Hüftgelenk links axial. Coxarthrose links mit Gelenkspaltverschmälerung auf 2 Millimeter, "
                  "rechts nicht. Kein Frakturnachweis. Keine periprothetische Lockerung.",
    "syn_ulnaris": "Sonographie des Nervus ulnaris links. Querschnittsfläche im Sulcus nervi ulnaris 9 Quadratmillimeter, "
                   "nicht vergrößert. Keine Luxation bei Flexion. Hoffmann-Tinel-Zeichen negativ.",
})

NEG = re.compile(r"\b(kein\w*|nicht|ohne|negativ)\b", re.I)
SEITE = re.compile(r"\b(rechts\w*|links\w*|rechte\w*|linke\w*|beidseit\w*)\b", re.I)


# ─── Kennzahlen ───────────────────────────────────────────────────────────────────────────────────────────────────────
def norm(t):
    t = t.lower().replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    t = re.sub(r"\{(\w+)\}", r"\1", t)           # chirp-Marker {Punkt} → punkt
    t = re.sub(r"(\d),(\d)", r"\1k\2", t)         # 9,5 bleibt ein Wort
    t = t.replace("°", " grad ")
    return re.sub(r"[^\w\s]", " ", t).split()


def wer(ref, hyp):
    """Echte Wortfehlerrate (Levenshtein auf Wörtern) in %."""
    r, h = norm(ref), norm(hyp)
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return round(100.0 * d[len(h)] / max(len(r), 1), 1)


def _zahlen(t):
    t = t.lower().replace("°", " grad")
    t = re.sub(r"\bth\s*(\d+)", r"th\1", t)
    t = re.sub(r"\b(millimeter|mm)\b", "mm", t)
    return re.findall(r"th\d+|l\d\b|\d+(?:,\d+)?", t)


def fachwoerter_in(ref, liste):
    nr = " ".join(norm(ref))
    return [p for p in liste if " ".join(norm(p)) and re.search(r"\b" + re.escape(" ".join(norm(p))) + r"\b", nr)]


def bewerte(datei, ref, hyp, fachliste):
    out = {"wer": wer(ref, hyp) if ref else None}
    nh = " ".join(norm(hyp))
    if datei in TERMS:                              # Termini-Muster der bisherigen Messungen (vergleichbar mit chirp)
        out["termini"] = [sum(bool(re.search(p, hyp.lower())) for p in TERMS[datei]), len(TERMS[datei])]
    if ref:
        fw = fachwoerter_in(ref, fachliste)
        out["fachwort"] = [sum(bool(re.search(r"\b" + re.escape(" ".join(norm(p))) + r"\b", nh)) for p in fw), len(fw)]
        zr, zh = _zahlen(ref), _zahlen(hyp)
        out["zahlen"] = [sum(min(zr.count(z), zh.count(z)) for z in set(zr)), len(zr)]
        nr_, nh_ = [m.lower() for m in NEG.findall(ref)], [m.lower() for m in NEG.findall(hyp)]
        out["verneinung"] = [sum(min(nr_.count(z), nh_.count(z)) for z in set(nr_)), len(nr_)]
        sr, sh = [m.lower()[:4] for m in SEITE.findall(ref)], [m.lower()[:4] for m in SEITE.findall(hyp)]
        out["seite_ok"] = sr == sh
    if datei in SIDE:
        muss, nie = SIDE[datei]
        out["seite_ok"] = bool(re.search(muss, hyp)) and not re.search(nie, hyp) and out.get("seite_ok", True)
    return out


# ─── Mistral ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def schluessel():
    k = os.environ.get("MISTRAL_API_KEY")
    if k:
        return k
    sys.path.insert(0, str(pathlib.Path.home() / ".hermes" / "scripts"))
    try:
        from vw_get import get_login
        return get_login(VW_NAME)[1]
    except Exception as e:  # noqa: BLE001
        sys.exit(f"Kein Mistral-Schlüssel (MISTRAL_API_KEY / Vaultwarden „{VW_NAME}“): {type(e).__name__}. "
                 "Nicht selbst registrieren – Kanban-Karte für Peter.")


def _multipart(felder, datei_feld, pfad):
    grenze = "----vx" + uuid.uuid4().hex
    teile = []
    for k, v in felder:
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    teile.append((f'--{grenze}\r\nContent-Disposition: form-data; name="{datei_feld}"; filename="{pfad.name}"\r\n'
                  f"Content-Type: audio/wav\r\n\r\n").encode() + pfad.read_bytes() + b"\r\n")
    teile.append(f"--{grenze}--\r\n".encode())
    return b"".join(teile), f"multipart/form-data; boundary={grenze}"


def voxtral(pfad, bias, key, timeout=120):
    felder = [("model", MODELL), ("language", "de")] + [("context_bias", b) for b in bias]
    body, ct = _multipart(felder, "file", pfad)
    req = urllib.request.Request(f"{API}/v1/audio/transcriptions", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": ct})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d.get("text", "").strip(), round(time.time() - t0, 2), d.get("usage", {})


def modelle(key):
    req = urllib.request.Request(f"{API}/v1/models", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    for m in d.get("data", []):
        if re.search(r"voxtral|transcri", m.get("id", ""), re.I):
            print(m["id"], json.dumps(m.get("capabilities", {}), ensure_ascii=False)[:160])


class Kostenbuch:
    def __init__(self, pfad):
        self.pfad, self.eur = pfad, 0.0
        if pfad.exists():
            self.eur = sum(json.loads(z)["eur"] for z in pfad.read_text().splitlines() if z.strip())

    def vorab(self, minuten, art="batch"):
        eur = minuten * PREIS_USD_MIN[art] * USD_EUR
        if self.eur + eur > LIMIT_EUR:
            raise SystemExit(f"Mistral-Testdeckel {LIMIT_EUR} € erreicht ({self.eur:.3f} € gebucht) – Abbruch.")
        return eur

    def buche(self, datei, minuten, eur):
        self.eur += eur
        with self.pfad.open("a") as f:
            f.write(json.dumps({"zeit": datetime.datetime.now().isoformat(timespec="seconds"), "datei": datei,
                                "modell": MODELL, "min": round(minuten, 3), "eur": round(eur, 5)}) + "\n")


# ─── Audio ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def als_wav(src, ziel):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(ziel)], check=True,
                   timeout=60)
    return ziel


def dauer_min(p):
    s = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, timeout=30).stdout
    return float(s) / 60


def material(echt=None):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    m = []
    for f in sorted(PUB.glob("*.ogg")):
        m.append((f.name, als_wav(f, SCRATCH / (f.stem + ".wav")), REF.get(f.name)))
    for k, txt in SYN.items():
        w = SCRATCH / f"{k}.wav"
        if not w.exists():
            aiff = SCRATCH / f"{k}.aiff"
            subprocess.run(["say", "-v", "Anna", "-o", str(aiff), txt], check=True, timeout=60)
            als_wav(aiff, w)
        m.append((k, w, txt))
    if echt:
        if not os.environ.get("MISTRAL_AVV_BESTAETIGT"):
            sys.exit("--echt nur mit MISTRAL_AVV_BESTAETIGT=<Datum> (bezahlter Tarif + AVV + keine Trainingsnutzung).")
        for w in sorted(pathlib.Path(echt).glob("*.wav")):
            ref = w.with_suffix(".ref.txt")
            m.append((w.name, w, ref.read_text(encoding="utf-8") if ref.exists() else None))
    return m


def listen():
    ph = json.loads((ROOT / "phrases.json").read_text(encoding="utf-8"))
    chirp, sm = ph["chirp"], [p for p in ph["chirp_sm"] if p not in ph["chirp"]]
    return {"ohne": [], "chirp85": chirp[:BIAS_MAX], "chirp+sm": (chirp + sm)[:BIAS_MAX]}, chirp + sm


# ─── Auswertung ───────────────────────────────────────────────────────────────────────────────────────────────────────
def zusammenfassen(zeilen):
    """zeilen: dicts mit variante, datei, dt, min, kennzahlen → je Variante Summen."""
    agg = {}
    for z in zeilen:
        a = agg.setdefault(z["variante"], {"n": 0, "wer": [], "termini": [0, 0], "fachwort": [0, 0], "zahlen": [0, 0],
                                           "verneinung": [0, 0], "seite_falsch": 0, "seite_n": 0, "dt": 0.0, "min": 0.0})
        a["n"] += 1
        if z.get("wer") is not None:
            a["wer"].append(z["wer"])
        for k in ("termini", "fachwort", "zahlen", "verneinung"):
            if k in z:
                a[k][0] += z[k][0]; a[k][1] += z[k][1]
        if "seite_ok" in z:
            a["seite_n"] += 1; a["seite_falsch"] += not z["seite_ok"]
        if z.get("dt") is not None and z.get("min"):
            a["dt"] += z["dt"]; a["min"] += z["min"]
    for a in agg.values():
        a["wer_mittel"] = round(sum(a["wer"]) / len(a["wer"]), 1) if a["wer"] else None
        a["s_je_min"] = round(a["dt"] / a["min"], 1) if a["min"] else None
        del a["wer"]
    return agg


def chirp_basis(fachliste):
    d = json.loads(BASIS.read_text(encoding="utf-8"))
    zeilen = []
    for r in d["laeufe"]:
        k = bewerte(r["file"], REF.get(r["file"]), r["txt"], fachliste)
        zeilen.append({"variante": "chirp_3 +85 (04.10.)", "datei": r["file"], "dt": r["dt"],
                       "min": d["dauer_s"][r["file"]] / 60, **k})
    return zeilen


def kosten_monat():
    mon_e, mon_l = WOCHE_ENDTEXT_MIN * MONAT_FAKTOR, WOCHE_LIVE_MIN * MONAT_FAKTOR
    return {"min_endtext": round(mon_e), "min_live": round(mon_l),
            "mistral_batch_usd": round(mon_e * PREIS_USD_MIN["batch"], 2),
            "mistral_realtime_usd": round(mon_l * PREIS_USD_MIN["realtime"], 2)}


def tabelle(agg):
    z = ["| Variante | Läufe | WER Ø % | Termini | Fachwort | Zahlen | Verneinung | Seite falsch | s je Audio-min |",
         "|---|---|---|---|---|---|---|---|---|"]
    f = lambda p: f"{p[0]}/{p[1]}" if p[1] else "–"  # noqa: E731
    for v, a in agg.items():
        z.append(f"| {v} | {a['n']} | {a['wer_mittel']} | {f(a['termini'])} | {f(a['fachwort'])} | {f(a['zahlen'])} | "
                 f"{f(a['verneinung'])} | {a['seite_falsch']}/{a['seite_n']} | {a['s_je_min']} |")
    return "\n".join(z)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--laeufe", type=int, default=3)
    ap.add_argument("--modelle", action="store_true")
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--nur-chirp", action="store_true")
    ap.add_argument("--echt")
    a = ap.parse_args()
    varianten, fachliste = listen()
    chirp = chirp_basis(fachliste)
    if a.nur_chirp:
        print(tabelle(zusammenfassen(chirp)))
        print(json.dumps(kosten_monat(), ensure_ascii=False))
        return
    key = None if a.trocken else schluessel()
    if a.modelle:
        return modelle(key)
    OUT.mkdir(parents=True, exist_ok=True)
    stempel = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    buch = Kostenbuch(OUT / "kostenbuch.jsonl") if not a.trocken else None
    zeilen = []
    for name, wav, ref in material(a.echt):
        mi = dauer_min(wav)
        for v, bias in varianten.items():
            for lauf in range(min(a.laeufe, 5)):
                if a.trocken:
                    txt, dt = ref or "", 0.0
                else:
                    eur = buch.vorab(mi)
                    try:
                        txt, dt, _ = voxtral(wav, bias, key)
                    except urllib.error.HTTPError as e:
                        msg = e.read().decode(errors="replace")[:300]
                        print(f"HTTP {e.code} {name} {v}: {msg}", file=sys.stderr)
                        if v != "ohne" and e.code in (400, 422):
                            txt, dt = None, None  # Liste vom Konto/Modell abgelehnt → Variante nicht messbar
                        else:
                            raise
                    buch.buche(name, mi, eur)
                if txt is None:
                    break
                zeilen.append({"variante": f"voxtral {v}", "datei": name, "lauf": lauf, "dt": dt, "min": mi, "txt": txt,
                               **bewerte(name, ref, txt, fachliste)})
    pub = {r["file"] for r in json.loads(BASIS.read_text(encoding="utf-8"))["laeufe"]}
    vgl = zusammenfassen(chirp + [z for z in zeilen if z["datei"] in pub])
    syn = zusammenfassen([z for z in zeilen if z["datei"] not in pub])
    ziel = OUT / f"voxtral_{'trocken' if a.trocken else stempel}.json"
    ziel.write_text(json.dumps({"modell": MODELL, "zeilen": zeilen, "vergleich_public": vgl, "synthetik": syn,
                                "kosten_monat": kosten_monat(), "test_eur": round(buch.eur, 4) if buch else 0},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    print("## 6 Sprachnachricht-Diktate (chirp_3 aus Altwerten)\n" + tabelle(vgl))
    print("\n## Synthetik say/Anna (kein chirp-Altwert)\n" + tabelle(syn))
    print(json.dumps(kosten_monat(), ensure_ascii=False), "→", ziel.relative_to(ROOT))


if __name__ == "__main__":
    main()
