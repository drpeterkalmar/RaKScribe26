"""Beleg Nr. 34: KOALA-Baustein aus Abholer-Code (ris-mods 56db19d) -> Brücke 2.5.22 (baustein_lesen + fuer_rakscribe) -> KaiScribe 3.19.13 (ibl_bausteine.einsetzen).
Aufruf: python3 koala34.py <ris-mods> <RaKScribe26>   (nur Testdaten, Nummer erfunden)"""
import json, os, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
RM, RS = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(RM / "ibl"), str(RM / "bruecke")]
from gemeinsam import kataloge_laden, regeln_laden
from vorbefund import erstelle_vorbefund
import abholer, ibl_bausteine as BB, bruecke
print("Abholer", abholer.VERSION, "| Brücke", bruecke.VERSION)
K, R = kataloge_laden(), regeln_laden()
daten = {"modul": "KOALA", "seite": "links", "qualitaet": {"status": "ok"},
         "messungen": {"kl_grad": {"wert": 3}, "gelenkspalt_min_medial": {"wert": "3.50"}, "gelenkspalt_min_lateral": {"wert": "6.10"}}}
v = erstelle_vorbefund(daten, K, R)
d = {"format": BB.FORMAT, "accession_number": "9990003001", "modul": "koala", "modul_name": "IB Lab KOALA", "version": 1,
     "aktualisiert": "2026-11-19T04:00:00", "vorbefund": v}
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "x.json"); Path(p).write_text(json.dumps(d, ensure_ascii=False, default=str), encoding="utf-8")
    b = BB.fuer_rakscribe(BB.baustein_lesen(p, "9990003001", "koala"))
print("Brücke liefert:", json.dumps({k: b.get(k) for k in ("modul", "seiten", "befundteil", "ergebnis")}, ensure_ascii=False))
# KaiScribe-Teil: Brücken-Modul aus dem Speicher nehmen, KaiScribe-Version laden, Nr.-34-Wortlaut prüfen
b["accno"] = "T-0034"; b["ziffer"] = 1; b["alter"] = 66
for m in ("ibl_bausteine", "bruecke"):
    sys.modules.pop(m, None)
sys.path[:0] = [str(RS / "source_code")]
sys.path[:] = [p for p in sys.path if not p.endswith("/bruecke") and not p.endswith("/ibl")]
import importlib
I = importlib.import_module("ibl_bausteine")
assert hasattr(I, "aus_liste"), "falsches ibl_bausteine"
import re as _re
src = (RS / "tests/offline/test_ibl_koala_text.py").read_text(encoding="utf-8")
# Fixture-Texte aus dem Test lesen (Nr. 34), nicht abtippen
ns = {}
exec(compile(src[src.index("def bericht"):src.index("def bericht")+120].split("\n\n")[0], "b", "exec"), ns)
T = json.loads((RS / "templates.json").read_text(encoding="utf-8"))
def grab(name):
    m = _re.search(name + r" = \((.*?)\)\n(?=NR34|K34|KI|e )", src, _re.S)
    return eval("(" + m.group(1) + ")")
BEF, ERG = grab("NR34_BEFUND"), grab("NR34_ERGEBNIS")
bericht = ns["bericht"]
VORLAGE = T["kniegelenk_in_2_ebenen"]["body"].split("\n", 2)[2]
ki = VORLAGE.replace("Kein Hinweis auf freie Gelenkkörper.", "Femoropatellar mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler Sklerosierung. Kein Hinweis auf freie Gelenkkörper.").replace("Unauffällige Weichteile.", "Geringer Gelenkerguss. Ansonsten unauffällige Weichteile.")
e = I.einsetzen(bericht("Kniegelenk links in 2 Ebenen", ki, "1. Mäßiggradige Femoropatellararthrose links (Arthrose Grad 3 nach Kellgren & Lawrence).\n2. Geringer Gelenkerguss links."), I.aus_liste([b]), diktat="Knie links. Mäßige patellofemorale Arthrose, geringer Gelenkserguss.")
soll = bericht("Kniegelenk links in 2 Ebenen", BEF, ERG)
print("WORTLAUT_GLEICH_NR34 =", e.report == soll, "| Hinweise:", e.hinweise)
print("--- Ergebnis KaiScribe ---"); print(e.report)
if e.report != soll:
    print("--- Soll ---"); print(soll)
