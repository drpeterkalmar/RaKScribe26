#!/usr/bin/env python3
"""tools/pause_segment_ab.py — Messung v3.8.0 (Peter 11.10., Nachtrag 1): Verliert die Abschnitts-Transkription beim
SpeechMike-Pausieren Wörter an den Pausengrenzen gegenüber der Ganz-Audio-Transkription?

Für jedes echte Praxis-Diktat (web_app/public/*.ogg, Duplikate per Prüfsumme raus) werden 2–3 Schnittstellen MITTEN in
Sprechpausen gesucht (Pegel unter der Schwelle ≥ 0,3 s), dann:
  - Ganz-Audio  → chirp_3 (Produktionsfunktion stt.chirp3_worker, gleiche Phrasen) — RUNS-mal (Grundrauschen von chirp_3)
  - Abschnitte  → je Abschnitt chirp_3, Texte in Reihenfolge mit Leerzeichen verbunden — RUNS-mal
Vergleich auf Wortebene (klein, ohne Satzzeichen, difflib): „verloren an der Grenze“ = Wörter, die im Ganz-Audio stehen und
in den Abschnitten fehlen, höchstens 2 Wörter neben einer Schnittstelle. Abweichungen anderswo werden mitgezählt, aber getrennt
ausgewiesen (chirp_3 schwankt auch beim Ganz-Audio, siehe Spalte „ganz↔ganz“).

  PRAXIS_KEY=<rakscribe-praxis-key.json> /usr/bin/python3 tools/pause_segment_ab.py [RUNS] > ergebnis.txt
"""
import difflib
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source_code"))
import stt  # noqa: E402  (Produktionscode der EXE: chirp_3-Request + Segmentierung, Phrasen aus phrases.json)

from google.oauth2 import service_account  # noqa: E402
import google.auth.transport.requests as gtr  # noqa: E402

SR = 16000
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 2
_CRED = service_account.Credentials.from_service_account_info(
    json.load(open(os.environ["PRAXIS_KEY"]))["stt"], scopes=["https://www.googleapis.com/auth/cloud-platform"])


def token():
    if not _CRED.valid:
        _CRED.refresh(gtr.Request())
    return _CRED.token


def pcm(ogg):
    roh = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ogg), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True, timeout=60).stdout
    return np.frombuffer(roh, dtype=np.int16)


def pausen(x, rahmen=320, min_s=0.3):
    """Sprechpausen als (start_s, ende_s): Rahmen-RMS unter Rauschboden + 12 % des Abstands zur Sprachlautstärke."""
    n = len(x) // rahmen
    rms = np.sqrt(np.mean(x[:n * rahmen].astype(np.float64).reshape(n, rahmen) ** 2, axis=1))
    boden, laut = np.percentile(rms, 10), np.percentile(rms, 90)
    still = rms < boden + 0.12 * (laut - boden)
    out, i = [], 0
    while i < n:
        if still[i]:
            j = i
            while j < n and still[j]:
                j += 1
            if (j - i) * rahmen / SR >= min_s:
                out.append((i * rahmen / SR, j * rahmen / SR))
            i = j
        else:
            i += 1
    return out


def schnitte(x, max_n=3, rand_s=1.5, abstand_s=2.5):
    dauer = len(x) / SR
    kand = [p for p in pausen(x) if p[0] > rand_s and p[1] < dauer - rand_s]
    kand.sort(key=lambda p: p[0] - p[1])  # längste Pausen zuerst
    gewaehlt = []
    for a, b in kand:
        m = (a + b) / 2
        if all(abs(m - g) >= abstand_s for g in gewaehlt):
            gewaehlt.append(m)
        if len(gewaehlt) >= max_n:
            break
    return sorted(gewaehlt)


def chirp(x):
    t0 = time.time()
    txt = stt.chirp3_worker(x, SR, "eu", token())
    return (txt or "").strip(), time.time() - t0


NORM = re.compile(r"[^\wäöüß%,./-]+", re.I)


def woerter(t):
    out = []
    for w in t.split():
        w = w.lower().strip(".,:;!?„“\"()[]–-")
        if w:
            out.append(w)
    return out


def vergleich(ganz, teile):
    """(verloren_an_grenze, sonst_verloren, ergaenzt, ersetzt, details) Ganz-Audio-Wörter vs. Abschnitts-Wörter."""
    a = woerter(ganz)
    b, grenzen = [], []
    for t in teile:
        if b:
            grenzen.append(len(b))
        b += woerter(t)
    verloren_g, verloren_s, ergaenzt, ersetzt, details = 0, 0, 0, 0, []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        an_grenze = any(j1 - 2 <= g <= j2 + 2 for g in grenzen)
        weg = max(0, (i2 - i1) - (j2 - j1)) if op == "replace" else (i2 - i1 if op == "delete" else 0)
        dazu = max(0, (j2 - j1) - (i2 - i1)) if op == "replace" else (j2 - j1 if op == "insert" else 0)
        if op == "replace":
            ersetzt += min(i2 - i1, j2 - j1)
        if an_grenze:
            verloren_g += weg
        else:
            verloren_s += weg
        ergaenzt += dazu
        details.append(f"{op:7s} {'GRENZE' if an_grenze else 'innen '} ganz={' '.join(a[i1:i2])!r} teile={' '.join(b[j1:j2])!r}")
    return verloren_g, verloren_s, ergaenzt, ersetzt, details


def main():
    gesehen, summe = set(), {"grenze": 0, "sonst": 0, "ergaenzt": 0, "ersetzt": 0, "ganz_ganz": 0, "woerter": 0,
                             "t_ganz": 0.0, "t_letzter": 0.0, "dateien": 0, "schnitte": 0}
    for ogg in sorted((ROOT / "web_app" / "public").glob("*.ogg")):
        h = hashlib.md5(ogg.read_bytes()).hexdigest()
        if h in gesehen:
            print(f"\n=== {ogg.name}: Duplikat, übersprungen")
            continue
        gesehen.add(h)
        x = pcm(ogg)
        cuts = schnitte(x)
        if not cuts:
            print(f"\n=== {ogg.name}: keine geeignete Sprechpause, übersprungen")
            continue
        grenzen = [0] + [int(c * SR) for c in cuts] + [len(x)]
        print(f"\n=== {ogg.name}  {len(x) / SR:.1f} s, Schnitte bei {', '.join(f'{c:.2f}' for c in cuts)} s")
        summe["dateien"] += 1
        summe["schnitte"] += len(cuts)
        ganze = []
        for r in range(RUNS):
            t, dt = chirp(x)
            ganze.append(t)
            summe["t_ganz"] += dt
            print(f"  ganz #{r + 1} ({dt:.1f} s): {t}")
        if RUNS > 1:
            gg = vergleich(ganze[0], [ganze[1]])
            summe["ganz_ganz"] += gg[0] + gg[1] + gg[2] + gg[3]
            print(f"  ganz↔ganz Abweichungen: {gg[0] + gg[1]} weg, {gg[2]} dazu, {gg[3]} ersetzt")
        for r in range(RUNS):
            teile, zeiten = [], []
            for k in range(len(grenzen) - 1):
                t, dt = chirp(x[grenzen[k]:grenzen[k + 1]])
                teile.append(t)
                zeiten.append(dt)
            summe["t_letzter"] += zeiten[-1]
            print(f"  teile #{r + 1} ({' + '.join(f'{z:.1f}' for z in zeiten)} s): " + " ‖ ".join(teile))
            vg, vs, dazu, ers, det = vergleich(ganze[r], teile)
            summe["grenze"] += vg
            summe["sonst"] += vs
            summe["ergaenzt"] += dazu
            summe["ersetzt"] += ers
            summe["woerter"] += len(woerter(ganze[r]))
            print(f"    → an Grenze verloren {vg}, sonst verloren {vs}, ergänzt {dazu}, ersetzt {ers}")
            for d in det:
                print("      " + d)
    print("\n=== Summe")
    print(json.dumps(summe, ensure_ascii=False))
    print(f"Grenz-Verluste: {summe['grenze']} Wörter bei {summe['schnitte']} Schnitten × {RUNS} Läufe "
          f"({summe['woerter']} Wörter verglichen). GATE {'BESTANDEN' if summe['grenze'] == 0 else 'NICHT bestanden'}")


if __name__ == "__main__":
    main()
