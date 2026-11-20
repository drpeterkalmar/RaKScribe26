"""Kam der IB-Lab-Text in den KaiScribe-Befund? (kaiscribe-frog-einsetzen-n1, Georg 19.11.2026, RH 127) — läuft auf der
Automaten-VM als rakauto (X: nur lesen; keine Datenbank, keine Bilder).

  py -3.12 ibl_laeufe_pruefen.py [--von JJJJMMTT] [--module FROG,HIPPO] [--ordner X:\\RaKScribe\\Daten]

Je Lauf-Datei (X:\\RaKScribe\\Daten\\laeufe\\<Nr>_<Zeit>.json) mit einem der Module eine Zeile – nur Zähler/Kategorien,
nie Befundtext, Nr oder Benutzer:
  IBL_LAUF <JJJJMMTT-HHMM> rechner=<PC> kaiscribe=<Version> bruecke=<Version laut bruecke_<PC>.log> module=<…>
           zeilen=<eingesetzte Zeilen> frog_satz=ja|nein hippo_satz=ja|nein schluss=ja|nein urteil=OK|LEER|ALT
           ablage=<modul>:patho|normal|?,… (Abholer-Datei X:\\IBL-Vorbefunde\\<Nr><Ziffer>_<modul>.json: Ergebnispunkte/
           befundtext da = patho, beides leer = normal, keine Datei = ?)
  (urteil LEER = Modul da, 0 Zeilen; ALT = Brücke < 2.5.20 und KaiScribe < 3.19.15 – FROG-Text kam damals nicht durch;
   NORMAL = 0 Zeilen, aber alle Module laut Ablage ohne Pathologie – dann gibt es keinen Text, richtig so)
  IBL_LAEUFE n=<…> ok=<…> leer=<…> normal=<…>
"""
import argparse
import glob
import json
import os
import re

FROG_SATZ = re.compile(r"(?:Valgus|Varus)stellung der (?:Groß|Klein)zehe|Vergrößerter Intermetatarsalwinkel|"
                       r"(?:Erhöhtes|Abgeflachtes) Längsgewölbe")
HIPPO_SATZ = re.compile(r"Beckenschiefstand von|Der (?:LCE|AI|CCD)-Winkel beträgt|Kein Beckenschiefstand")
SCHLUSS = "Weitere Winkelmessungen sind den KI-Auswertungsbildern"
START = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d):\d\d \[start\] v([\d.]+)")
SICHER = re.compile(r"[^\w.,+-]")


def _v(t):
    try:
        return tuple(int(x) for x in str(t).split("."))
    except ValueError:
        return ()


def bruecke_stand(ordner):
    """PC → [(Zeit JJJJ-MM-TT HH:MM, Version)] aus den Brücken-Protokollen."""
    out = {}
    for p in glob.glob(os.path.join(ordner, "protokolle", "bruecke_*.log")):
        pc = os.path.basename(p)[8:-4]
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                out[pc] = [(m.group(1), m.group(2)) for m in map(START.match, f) if m]
        except OSError:
            pass
    return out


def ablage_art(ablage, nr, modul):
    """patho | normal | ? – nur Zähler aus der Abholer-Datei (Ergebnispunkte ohne Schlusssatz, befundtext)."""
    arten = set()
    for p in glob.glob(os.path.join(ablage, f"{nr}[0-9]_{modul.lower()}.json")):
        try:
            with open(p, encoding="utf-8-sig") as f:
                vb = (json.load(f) or {}).get("vorbefund") or {}
        except (OSError, ValueError, AttributeError):
            continue
        punkte = [e for e in vb.get("ergebnis_punkte") or [] if SCHLUSS not in str(e)]
        bt = vb.get("befundtext")
        arten.add("patho" if punkte or (isinstance(bt, dict) and bt.get(modul.lower())) else "normal")
    return "patho" if "patho" in arten else ("normal" if arten else "?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--von", default="20261119")
    ap.add_argument("--module", default="FROG,HIPPO")
    ap.add_argument("--ordner", default=r"X:\RaKScribe\Daten")
    ap.add_argument("--ablage", default=r"X:\IBL-Vorbefunde")
    a = ap.parse_args()
    module = [m.strip().upper() for m in a.module.split(",") if m.strip()]
    stand = bruecke_stand(a.ordner)
    n = ok = leer = normal = 0
    for p in sorted(glob.glob(os.path.join(a.ordner, "laeufe", "*.json"))):
        m = re.match(r"^(\d+)_(\d{8})-(\d{4})", os.path.basename(p))
        if not m or m.group(2) < a.von:
            continue
        try:
            with open(p, encoding="utf-8-sig") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        mods = [str(x) for x in d.get("ibl_module") or []]
        if not any(x.split()[0].upper() in module for x in mods if x.split()):
            continue
        n += 1
        rep = str(d.get("ergebnis_vorschlag") or "")
        pc = SICHER.sub("", str(d.get("rechner") or "?"))
        nr, tag, uhr = m.groups()
        zeit = f"{tag[:4]}-{tag[4:6]}-{tag[6:]} {uhr[:2]}:{uhr[2:]}"
        br = next((v for t, v in reversed(stand.get(pc, [])) if t <= zeit), "?")
        ks = SICHER.sub("", str(d.get("kaiscribe") or "?"))
        zeilen = int(d.get("ibl_zeilen") or 0)
        arten = {x.split()[0].upper(): ablage_art(a.ablage, nr, x.split()[0])
                 for x in mods if x.split() and x.split()[0].upper() in module}
        if zeilen > 0:
            urteil = "OK"
            ok += 1
        elif arten and all(v == "normal" for v in arten.values()):
            urteil = "NORMAL"
            normal += 1
        else:
            leer += 1
            urteil = "ALT" if (_v(br) and _v(br) < (2, 5, 20) and _v(ks) and _v(ks) < (3, 19, 15)) else "LEER"
        print(f"IBL_LAUF {tag}-{uhr} rechner={pc} kaiscribe={ks} bruecke={br} "
              f"module={'+'.join(SICHER.sub('', x.replace(' ', '_')) for x in mods)} zeilen={zeilen} "
              f"frog_satz={'ja' if FROG_SATZ.search(rep) else 'nein'} hippo_satz={'ja' if HIPPO_SATZ.search(rep) else 'nein'} "
              f"schluss={'ja' if SCHLUSS in rep else 'nein'} "
              f"ablage={','.join(f'{k}:{v}' for k, v in arten.items())} urteil={urteil}")
    print(f"IBL_LAEUFE n={n} ok={ok} leer={leer} normal={normal}")


if __name__ == "__main__":
    main()
