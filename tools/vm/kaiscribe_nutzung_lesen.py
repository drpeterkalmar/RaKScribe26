"""KaiScribe-Nutzung lesen (kaiscribe-sonnet-n3-beleg, 17.11.2026) — läuft auf der Automaten-VM als rakauto (X: nur lesen).

  py -3.12 kaiscribe_nutzung_lesen.py [--tage JJJJ-MM-TT,…] [--ordner X:\\RaKScribe\\Daten]

Gibt nur Zähler aus, nie Befundtext, Nr oder Benutzer:
  LAUF <tag> rechner=<PC> modell=<…> kaiscribe=<Version> maske=<ja|nein> anzahl=<n> von=<HH:MM> bis=<HH:MM>
  NUTZUNG <monat> <PC> <tag> befunde=… anthropic=… gemini=… rueckfall=… usd=… chirp_s=… gruende=<Kat:n;…>
  TAGESBERICHT <tag> (danach die Datei wörtlich, je Zeile mit „| “ davor; sie enthält nur Zahlen/Kategorien)
  WARNDATEI <monat> ja|nein
  NUTZUNG_LESEN=fertig
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

SICHER = re.compile(r"[^\w./() +-]")


def s(x, n=60):
    return SICHER.sub("_", str(x if x is not None else ""))[:n] or "-"


def _json(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return None


def laeufe(ordner, tage):
    """Lauf-Dateien <Nr>_<JJJJMMTT-HHMMSS>.json → Zähler je (tag, rechner, modell, kaiscribe, maske)."""
    z, kaputt = {}, 0
    muster = {t.replace("-", ""): t for t in tage}
    for pfad in glob.glob(os.path.join(ordner, "*.json")):
        m = re.search(r"_(\d{8})-(\d{2})(\d{2})\d{2}(?:-\d+)?\.json$", os.path.basename(pfad))
        if not m or m.group(1) not in muster:
            continue
        d = _json(pfad)
        if d is None:
            kaputt += 1
            continue
        k = (muster[m.group(1)], s(d.get("rechner")), s(d.get("modell")), s(d.get("kaiscribe"), 20),
             "ja" if d.get("maske") else "nein")
        e = z.setdefault(k, {"n": 0, "von": "99:99", "bis": "00:00"})
        hm = "%s:%s" % (m.group(2), m.group(3))
        e["n"] += 1
        e["von"], e["bis"] = min(e["von"], hm), max(e["bis"], hm)
    for k in sorted(z):
        e = z[k]
        print("LAUF %s rechner=%s modell=%s kaiscribe=%s maske=%s anzahl=%d von=%s bis=%s"
              % (k[0], k[1], k[2], k[3], k[4], e["n"], e["von"], e["bis"]))
    print("LAUF_KAPUTT %d" % kaputt)


def nutzung(ordner, tage):
    for monat in sorted({t[:7] for t in tage}):
        for pfad in sorted(glob.glob(os.path.join(ordner, "%s_*.json" % monat))):
            d = _json(pfad) or {}
            pc = s(d.get("pc") or os.path.basename(pfad)[8:-5])
            for tag, td in sorted((d.get("tage") or {}).items()):
                ki = td.get("ki") or {}
                gr = ";".join("%s:%s" % (s(g), int(n or 0)) for g, n in sorted((td.get("rueckfall_grund") or {}).items()))
                print("NUTZUNG %s %s %s befunde=%s anthropic=%s gemini=%s rueckfall=%s usd=%.4f chirp_s=%.1f gruende=%s"
                      % (monat, pc, s(tag, 10), int(td.get("befunde", 0) or 0), int(ki.get("anthropic", 0) or 0),
                         int(ki.get("gemini", 0) or 0), int(ki.get("rueckfall", 0) or 0),
                         float(td.get("anthropic_usd", 0) or 0), float((td.get("stt_s") or {}).get("chirp", 0) or 0),
                         gr or "-"))
        print("WARNDATEI %s %s" % (monat, "ja" if os.path.exists(os.path.join(ordner, "warnung_%s.txt" % monat)) else "nein"))
    for tag in tage:
        pfad = os.path.join(ordner, "tagesbericht_%s.txt" % tag)
        if not os.path.exists(pfad):
            print("TAGESBERICHT %s fehlt" % tag)
            continue
        print("TAGESBERICHT %s" % tag)
        with open(pfad, encoding="utf-8", errors="replace") as f:
            for zeile in f.read().splitlines()[:40]:
                print("| " + re.sub(r"\d{6,}", "<zahl>", zeile)[:300])


def main(argv=None):
    ap = argparse.ArgumentParser()
    heute = datetime.date.today()
    ap.add_argument("--tage", default=",".join(str(heute - datetime.timedelta(days=i)) for i in (1, 0)))
    ap.add_argument("--ordner", default="X:\\RaKScribe\\Daten")
    ap.add_argument("--ohne-laeufe", action="store_true")
    a = ap.parse_args(argv)
    tage = [t for t in a.tage.split(",") if re.match(r"^\d{4}-\d\d-\d\d$", t)]
    if not os.path.isdir(a.ordner):
        print("NUTZUNG_LESEN=fehler GRUND=Ordner fehlt")
        return 1
    if not a.ohne_laeufe:
        laeufe(os.path.join(a.ordner, "laeufe"), tage)
    nutzung(os.path.join(a.ordner, "nutzung"), tage)
    print("NUTZUNG_LESEN=fertig")
    return 0


if __name__ == "__main__":
    sys.exit(main())
