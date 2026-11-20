"""SQUIRREL-Bausteine für tests/offline/test_ibl_squirrel_text.py erzeugen (Brief kaiscribe-squirrel-ergebnistext-n1).
Mit dem Code von ris-mods (Abholer ibl/vorbefund.py + ibl/squirrel_ergebnis.py, Brücke bruecke/ibl_bausteine.py) – dieselben
Eingaben wie ris-mods ibl/tests/test_squirrel_ergebnis.py (Fixture SQUIRREL_SR, synthetische Kurven, keine Patientendaten).
Aufruf: python3 tools/squirrel_bausteine_erzeugen.py [Pfad zu ris-mods]   → tests/offline/squirrel_bausteine.json"""
import json, pathlib, sys, tempfile
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1]
RM = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path.home() / "dev" / "ris-mods")
sys.path[:0] = [str(RM / "ibl"), str(RM / "bruecke")]
from gemeinsam import kataloge_laden, regeln_laden  # noqa: E402
from sr_lesen import sr_lesen  # noqa: E402
from vorbefund import erstelle_vorbefund  # noqa: E402
import ibl_bausteine as BR  # noqa: E402  (Brücke)

K, R = kataloge_laden(), regeln_laden()
ANAT = {"labeling": "anatomisch", "metall": "", "coronal_seite": None}


def kurve(wert, lok="T5-T12", konvex="Dextroconvex"):
    m = {"wert": wert, "einheit": "deg"}
    if lok:
        m["lokalisation"] = lok
    if konvex:
        m["konvexitaet"] = konvex
    return m


def eingabe(messungen, squirrel=ANAT, alter=40 * 12):
    return {"modul": "SQUIRREL", "seite": None, "messungen": messungen, "qualitaet": {"status": "ok"},
            "squirrel": squirrel, "patient": {"alter_monate": alter}}


def frueher(wert, lok="T5-T12", konvex="Dextroconvex", datum="20250310"):
    return {"modul": "squirrel", "schluessel": "cobb_1", "seite": "", "vergleich": wert, "anzeige": f"{wert}°",
            "zusatz": {"lokalisation": lok, "konvexitaet": konvex}, "region": "", "projektion": "",
            "sicher": True, "regeln": True, "datum": datum, "quelle": "ib_lab"}


def baustein(nr, vorbefund):
    accno = f"T-90{nr:02d}1"
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / f"{accno}_squirrel.json"
        p.write_text(json.dumps({"format": BR.FORMAT, "accession_number": accno, "modul": "squirrel",
                                 "modul_name": "SQUIRREL", "version": 1, "aktualisiert": "2026-11-20T10:00:00",
                                 "vorbefund": vorbefund}, ensure_ascii=False, default=str), encoding="utf-8")
        return BR.fuer_rakscribe(BR.baustein_lesen(str(p), accno, "squirrel"))


fix = json.loads((RM / "ibl" / "tests" / "fixtures_iblab" / "SQUIRREL_SR.json").read_text(encoding="utf-8"),
                 parse_float=Decimal)
faelle = [
    ("fixture", "SQUIRREL_SR 20,9/44,5/31,2 → 21/44/31, anatomisch", erstelle_vorbefund(sr_lesen(fix, K), K, R)),
    ("index", "Index-Labeling 44,5° (ohne Höhe/Region)",
     erstelle_vorbefund([eingabe({"cobb_1": kurve("44.5", "V5-V12")}, squirrel={"labeling": "index"})], K, R)),
    ("unter10", "alle Cobb < 10° (kein Text)",
     erstelle_vorbefund([eingabe({"cobb_1": kurve("9.4"), "cobb_2": kurve("8", "T12-L4", "Levoconvex")})], K, R)),
    ("einzeln", "eine Krümmung 44,5° Th5–Th12 rechtskonvex", erstelle_vorbefund([eingabe({"cobb_1": kurve("44.5")})], K, R)),
    ("kind", "Kind 12 J., 44,5°", erstelle_vorbefund([eingabe({"cobb_1": kurve("44.5")}, alter=12 * 12)], K, R)),
    ("vorwert", "Vorwert 03/2025 39° → 44,5° (+5°, Progredienz)",
     erstelle_vorbefund([eingabe({"cobb_1": kurve("44.5")})], K, R, verlauf={"frueher": [frueher("39.0")]})),
    ("metall", "Metall/Implantat (nur Prüfzeile)",
     erstelle_vorbefund([eingabe({"cobb_1": kurve("44.5")}, squirrel=dict(ANAT, metall="implant"))], K, R)),
    ("ohne_konvex", "Konvexität fehlt (Prüfzeile)",
     erstelle_vorbefund([eingabe({"cobb_1": kurve("25", konvex=None)})], K, R)),
]
out = [{"nr": i + 1, "fall": k, "beschreibung": t, "baustein": baustein(i + 1, v)} for i, (k, t, v) in enumerate(faelle)]
ziel = ROOT / "tests" / "offline" / "squirrel_bausteine.json"
ziel.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
print(f"{len(out)} Bausteine → {ziel.relative_to(ROOT)}")
