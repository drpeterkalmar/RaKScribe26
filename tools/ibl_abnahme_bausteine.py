"""Abnahme-Bausteine für den Testpatienten (kaiscribe-frog-einsetzen-n1, Georg 19.11.2026: „Teste das immer ob es funktioniert“).

Schreibt einen ECHTEN FROG- und einen ECHTEN HIPPO-Baustein im Format der Abholer-Ablage (X:\\IBL-Vorbefunde\\<AccNo>_<modul>.json,
Format ibl-abholer/1) für die AccNo einer Testnummer – Inhalt aus den anonymen Fällen der Tests (nur Winkel/Messwerte, keine
Patientendaten): FROG = Fall vom 19.11.2026 (Fuß beidseits, Digitus quintus varus beidseits; tests/offline/snapshots/
frog_1911_beidseits.json), HIPPO = Fall 52 vom 18.11.2026 (tests/offline/hippo_bausteine.json). Die Brücke liest sie wie jeden
Abholer-Baustein; KaiScribe ≥ 3.19.15 holt den Text bei einer älteren Brücke selbst aus derselben Datei.

  python3 tools/ibl_abnahme_bausteine.py <Ziel-Ordner> --frog <AccNo> [--hippo <AccNo>] [--version N]

AccNo = Diktatnummer (11 Ziffern) + Ziffer der Leistung im CAS-Eintrag (1, 2 …). Danach die Dateien wieder entfernen.
Ausgabe: Pfade + erwarteter Text (Befund/Ergebnis), damit der Brief-Text gegengeprüft werden kann.
"""
import argparse
import copy
import json
import os
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
FROG = ROOT / "tests" / "offline" / "snapshots" / "frog_1911_beidseits.json"
HIPPO = ROOT / "tests" / "offline" / "hippo_bausteine.json"
FORMAT = "ibl-abholer/1"


def frog_datei(accno, version):
    d = copy.deepcopy(json.loads(FROG.read_text(encoding="utf-8"))["abholer_datei"])
    d.update(accession_number=accno, version=version, aktualisiert=time.strftime("%Y-%m-%dT%H:%M:%S"))
    return d


def hippo_datei(accno, version, nr=52):
    b = next(f["baustein"] for f in json.loads(HIPPO.read_text(encoding="utf-8")) if f["nr"] == nr)
    return {"format": FORMAT, "accession_number": accno, "modul": "hippo", "modul_name": "IB Lab HIPPO", "version": version,
            "aktualisiert": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "vorbefund": {"befundteil": b["befundteil"], "ergebnis_punkte": b["ergebnis"],
                          "hinweise_fuer_befunder": b.get("hinweise") or [], "nicht_zugeordnet": [],
                          "befundtext": {"hippo": dict(b["befundtext"], format=1)}}}


def schreiben(ordner, d):
    p = os.path.join(ordner, f"{d['accession_number']}_{d['modul']}.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("ziel")
    ap.add_argument("--frog", required=True)
    ap.add_argument("--hippo")
    ap.add_argument("--version", type=int, default=1)
    a = ap.parse_args(argv)
    for acc in filter(None, (a.frog, a.hippo)):
        if not re.fullmatch(r"\d{12}", acc):
            sys.exit(f"AccNo {acc!r}: 12 Ziffern (Diktatnummer + Ziffer der Leistung)")
    f = frog_datei(a.frog, a.version)
    print("FROG ", schreiben(a.ziel, f))
    bt = f["vorbefund"]["befundtext"]["frog"]
    print("  erwartet Befund:  ", " ".join(bt["stellung"] + bt["gewoelbe"]))
    print("  erwartet Ergebnis:", " ".join(f"{x['text']} {x['seite']}." for x in bt["begriffe"]), "/", bt["schluss"])
    if a.hippo:
        h = hippo_datei(a.hippo, a.version)
        print("HIPPO", schreiben(a.ziel, h))
        bt = h["vorbefund"]["befundtext"]["hippo"]
        print("  erwartet Befund:  ", " ".join(bt["saetze"]))
        print("  erwartet Ergebnis:", bt["ergebnis"], "/", bt["schluss"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
