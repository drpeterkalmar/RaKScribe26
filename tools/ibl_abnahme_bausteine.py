"""Abnahme-Bausteine für den Testpatienten (kaiscribe-frog-einsetzen-n1, Georg 19.11.2026: „Teste das immer ob es funktioniert“).

Schreibt einen ECHTEN FROG- und einen ECHTEN HIPPO-Baustein im Format der Abholer-Ablage (X:\\IBL-Vorbefunde\\<AccNo>_<modul>.json,
Format ibl-abholer/1) für die AccNo einer Testnummer – Inhalt aus den anonymen Fällen der Tests (nur Winkel/Messwerte, keine
Patientendaten): FROG = Fall vom 19.11.2026 (Fuß beidseits, Digitus quintus varus beidseits; tests/offline/snapshots/
frog_1911_beidseits.json), HIPPO = Fall 52 vom 18.11.2026 (tests/offline/hippo_bausteine.json). Die Brücke liest sie wie jeden
Abholer-Baustein; KaiScribe ≥ 3.19.15 holt den Text bei einer älteren Brücke selbst aus derselben Datei.

  python3 tools/ibl_abnahme_bausteine.py <Ziel-Ordner> [--frog <AccNo>] [--hippo <AccNo>] [--version N]
         [--frog-ohne <AccNo>] [--lama <AccNo>] [--squirrel <AccNo>]

3.20.0 (kaiscribe-georg-2011-abnahme, Georgs Diktiertag): --frog-ohne = FROG ohne Diagnose (RH 30, Abholer 1.3.15, Messwerte +
rote Prüfzeile), --lama = LAMA Fall 5 (beidseits regelrecht, BLD 11 mm, Anmerkung „/Traglinie des Ganzbeines“), beide mit dem
Abholer-Code erzeugt (tests/offline/abnahme_georg_2011/), --squirrel = SQUIRREL „einzeln“ (Cobb 44° Th5–Th12,
tests/offline/squirrel_bausteine.json Fall 4).

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
ABNAHME = ROOT / "tests" / "offline" / "abnahme_georg_2011"
SQUIRREL = ROOT / "tests" / "offline" / "squirrel_bausteine.json"


def vorrat_datei(name, accno, version):
    d = json.loads((ABNAHME / f"{name}.json").read_text(encoding="utf-8"))
    for k in [k for k in d if k.startswith("_")]:
        d.pop(k)
    d.update(accession_number=accno, version=version, aktualisiert=time.strftime("%Y-%m-%dT%H:%M:%S"))
    return d


def squirrel_datei(accno, version, fall="einzeln"):
    b = next(f["baustein"] for f in json.loads(SQUIRREL.read_text(encoding="utf-8")) if f["fall"] == fall)
    return {"format": FORMAT, "accession_number": accno, "modul": "squirrel", "modul_name": "IB Lab SQUIRREL",
            "version": version, "aktualisiert": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "vorbefund": {"befundteil": b["befundteil"], "ergebnis_punkte": b["ergebnis"],
                          "hinweise_fuer_befunder": b.get("hinweise") or [], "nicht_zugeordnet": [],
                          "befundtext": {"squirrel": dict(b["befundtext"], format=1)}}}


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


def hippo_becken_datei(accno, version, mm=13):
    """kaiscribe-rho-regel-becken-n1 (Georg FINAL 20.11.): mm=13 → RH 101 nachgestellt (13 mm re tiefer, BLD 20 mm als
    ergebnis_becken, Abholer ≥ 1.3.18), mm=9 → Fall 61 (9 mm, nur Beschreibung)."""
    d = hippo_datei(accno, version, nr=61)
    if mm == 13:
        bt = d["vorbefund"]["befundtext"]["hippo"]
        bt["saetze"] = ["Beckenschiefstand von 13 mm, rechts tieferstehend.", "Beinlängendifferenz von 20 mm."]
        bt["ergebnis_becken"] = list(bt["saetze"])
        d["vorbefund"]["befundteil"] = [z.replace("9 mm", "13 mm").replace("Beinlängendifferenz 3 mm",
                                                                               "Beinlängendifferenz 20 mm")
                                        for z in d["vorbefund"]["befundteil"]]
    return d


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
    ap.add_argument("--frog")
    ap.add_argument("--hippo")
    ap.add_argument("--frog-ohne")
    ap.add_argument("--lama")
    ap.add_argument("--squirrel")
    ap.add_argument("--hippo-becken", help="AccNo: HIPPO-Becken-Baustein (--mm 13 = RH 101 nachgestellt, 9 = Fall 61)")
    ap.add_argument("--mm", type=int, default=13, choices=(13, 9))
    ap.add_argument("--version", type=int, default=1)
    a = ap.parse_args(argv)
    for acc in filter(None, (a.frog, a.hippo, a.frog_ohne, a.lama, a.squirrel, a.hippo_becken)):
        if not re.fullmatch(r"\d{12}", acc):
            sys.exit(f"AccNo {acc!r}: 12 Ziffern (Diktatnummer + Ziffer der Leistung)")
    if a.frog:
        f = frog_datei(a.frog, a.version)
        print("FROG ", schreiben(a.ziel, f))
        bt = f["vorbefund"]["befundtext"]["frog"]
        print("  erwartet Befund:  ", " ".join(bt["stellung"] + bt["gewoelbe"]))
        print("  erwartet Ergebnis:", " ".join(f"{x['text']} {x['seite']}." for x in bt["begriffe"]), "/", bt["schluss"])
    if a.frog_ohne:
        f = vorrat_datei("frog_ohne_diagnose", a.frog_ohne, a.version)
        print("FROG (ohne Diagnose)", schreiben(a.ziel, f))
        bt = f["vorbefund"]["befundtext"]["frog"]
        print("  erwartet Befund (Ende der Beschreibung):", " ".join(bt["messwerte"]))
        print("  erwartet Ergebnis: kein FROG-Punkt / Anmerkung:", bt["schluss"])
        print("  erwartet Prüfzeile (rot):", f["vorbefund"]["hinweise_fuer_befunder"][-1])
    if a.hippo_becken:
        f = hippo_becken_datei(a.hippo_becken, a.version, a.mm)
        print(f"HIPPO-Becken {a.mm} mm", schreiben(a.ziel, f))
        bt = f["vorbefund"]["befundtext"]["hippo"]
        print("  erwartet Befund:  ", " ".join(bt["saetze"]))
        print("  erwartet Ergebnis:", " / ".join(bt.get("ergebnis_becken") or ["(kein Becken-Punkt)"]), "/", bt["schluss"])
    if a.lama:
        f = vorrat_datei("lama", a.lama, a.version)
        print("LAMA ", schreiben(a.ziel, f))
        print("  erwartet Ergebnis:", " / ".join(f["vorbefund"]["ergebnis_punkte"]))
    if a.squirrel:
        f = squirrel_datei(a.squirrel, a.version)
        print("SQUIRREL", schreiben(a.ziel, f))
        bt = f["vorbefund"]["befundtext"]["squirrel"]
        print("  erwartet Befund:  ", " ".join(bt["saetze"]))
        print("  erwartet Ergebnis:", bt["ergebnis"], "/", bt["schluss"])
    if a.hippo:
        h = hippo_datei(a.hippo, a.version)
        print("HIPPO", schreiben(a.ziel, h))
        bt = h["vorbefund"]["befundtext"]["hippo"]
        print("  erwartet Befund:  ", " ".join(bt["saetze"]))
        print("  erwartet Ergebnis:", bt["ergebnis"], "/", bt["schluss"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
