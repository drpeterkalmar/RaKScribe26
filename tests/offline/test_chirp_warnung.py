"""Gate (kaiscribe-sonnet-n3-beleg): Mac-Weg Chirp-Warnung → genau eine Kanban-Karte je Monat; alte KaiScribe je Rechner
→ eine Karte „neu starten“. Ohne VM: Ausgabe von tools/vm/kaiscribe_nutzung_lesen.py wird nachgestellt bzw. lokal erzeugt.
Aufruf: python3 tests/offline/test_chirp_warnung.py"""
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
spec = importlib.util.spec_from_file_location("cw", ROOT / "tools" / "mac" / "kaiscribe_chirp_warnung.py")
cw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cw)
spec = importlib.util.spec_from_file_location("kl", ROOT / "tools" / "vm" / "kaiscribe_nutzung_lesen.py")
kl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kl)

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


t = tempfile.mkdtemp(prefix="rks_chirp_")
cw.ZUSTAND = os.path.join(t, "zustand.json")
cw.KARTEI = os.path.join(t, "karten.json")
aufrufe = os.path.join(t, "aufrufe.txt")
fake = os.path.join(t, "kanban.py")
pathlib.Path(fake).write_text("import sys\nopen(%r, 'a', encoding='utf-8').write(repr(sys.argv[1:]) + '\\n')\n"
                              "print('#901 [peter] ' + sys.argv[2])\n" % aufrufe, encoding="utf-8")
cw.KANBAN = fake

# 1) VM-Leser lokal auf einem nachgebauten X:\RaKScribe\Daten (nur Zähler raus, nie Text/Nr/Benutzer)
daten = pathlib.Path(t, "Daten")
(daten / "laeufe").mkdir(parents=True)
(daten / "nutzung").mkdir()
lauf = {"modell": "anthropic/claude-sonnet-5-5", "kaiscribe": "3.19.1", "rechner": "CASWS10", "nr": "12345678901",
        "benutzer": "rg", "stt_roh": "Knie rechts Erguss", "ergebnis_vorschlag": "Kleiner Erguss."}
(daten / "laeufe" / "12345678901_20261116-130701.json").write_text(json.dumps(lauf), encoding="utf-8")
(daten / "laeufe" / "12345678902_20261116-154600.json").write_text(json.dumps(dict(lauf, maske="screening")), encoding="utf-8")
alt = dict(lauf, modell="gemini/gemini-3.5-flash", kaiscribe="3.18.9", rechner="CASWS08")
(daten / "laeufe" / "12345678903_20261116-090000.json").write_text(json.dumps(alt), encoding="utf-8")
(daten / "laeufe" / "kaputt_20261116-100000.json").write_text("{", encoding="utf-8")
monat = {"pc": "CASWS10", "tage": {"2026-11-16": {"befunde": 4, "ki": {"anthropic": 4}, "anthropic_usd": 0.2,
                                                  "stt_s": {"chirp": 1700.5}, "rueckfall_grund": {"Anthropic-Ausfall (timeout)": 1}}}}
(daten / "nutzung" / "2026-11_CASWS10.json").write_text(json.dumps(monat), encoding="utf-8")
(daten / "nutzung" / "tagesbericht_2026-11-16.txt").write_text("KaiScribe Tagesbericht 2026-11-16\nChirp 28.3 min\n",
                                                               encoding="utf-8")
buf = io.StringIO()
with redirect_stdout(buf):
    rc = kl.main(["--tage", "2026-11-16", "--ordner", str(daten)])
aus = buf.getvalue()
check("Leser: fertig, Läufe je Rechner/Modell/Version/Maske", rc == 0 and "NUTZUNG_LESEN=fertig" in aus
      and "LAUF 2026-11-16 rechner=CASWS10 modell=anthropic/claude-sonnet-5-5 kaiscribe=3.19.1 maske=nein anzahl=1" in aus
      and "maske=ja anzahl=1" in aus and "LAUF_KAPUTT 1" in aus, aus)
check("Leser: keine Nr, kein Benutzer, kein Text", "12345678901" not in aus and "Erguss" not in aus
      and "benutzer" not in aus and " rg" not in aus, aus)
check("Leser: Monatszähler + Rückfallgrund als Kategorie + Tagesbericht wörtlich",
      "NUTZUNG 2026-11 CASWS10 2026-11-16 befunde=4 anthropic=4 gemini=0 rueckfall=0" in aus
      and "gruende=Anthropic-Ausfall (timeout):1" in aus.replace("_", " ") and "| Chirp 28.3 min" in aus
      and "WARNDATEI 2026-11 nein" in aus, aus)

check("Leser: meldet den gelesenen Ordner", ("ORDNER %s" % daten) in aus, aus)

# 1b) Umzug (kaiscribe-umzug-n2): Standard X:\KaiScribe\Daten, fehlt der → X:\RaKScribe\Daten
check("Ordner: neuer Standard", kl.ORDNER_NEU == "X:\\KaiScribe\\Daten"
      and kl.standard_ordner(lambda o: o in {kl.ORDNER_NEU, kl.ORDNER_ALT}) == kl.ORDNER_NEU)
check("Ordner: Rückfall auf X:\\RaKScribe\\Daten", kl.standard_ordner(lambda o: o == kl.ORDNER_ALT) == kl.ORDNER_ALT)
check("Ordner: keiner da → neuer (Fehler „Ordner fehlt“)", kl.standard_ordner(lambda o: False) == kl.ORDNER_NEU)
gelesen = []
_alt_std = kl.standard_ordner
kl.standard_ordner = lambda: (gelesen.append(1), str(daten))[1]
buf = io.StringIO()
with redirect_stdout(buf):
    rc = kl.main(["--tage", "2026-11-16"])
kl.standard_ordner = _alt_std
check("Leser ohne --ordner nimmt den Standardordner", rc == 0 and gelesen and "LAUF_KAPUTT 1" in buf.getvalue(), buf.getvalue())
check("Mac-Texte zeigen den neuen Ordner", "X:\\KaiScribe\\Daten\\nutzung" in cw.__doc__
      and "RaKScribe\\Daten" not in pathlib.Path(cw.__file__).read_text(encoding="utf-8"))

# 2) Auswertung: 1 Tag → keine Warnung (Mindesttage), Beleg-Tabelle, alter Rechner erkannt
e = cw.auswerten(aus, "2026-11-16")
check("Auswertung: Chirp 28,3 min, aus 1 Tag, noch keine Warnung", abs(e["chirp_min"] - 28.34) < 0.01 and e["tage"] == 1
      and not e["warn_eigen"] and not e["warn_exe"] and e["bericht"][0].startswith("KaiScribe Tagesbericht"), e)
check("alter Rechner: CASWS08 mit Gemini 3.18.9, CASWS10 nicht", set(cw.alte_rechner(e["laeufe"])) == {"CASWS08"})
check("Beleg-Tabelle", "| 2026-11-16 | CASWS10 | anthropic/claude-sonnet-5-5 | 3.19.1 Maske | 1" in cw.beleg_tabelle(e))
check("Rückfall-Modell zählt nicht als alt", not cw.alte_rechner([{"tag": "2026-11-16", "rechner": "X", "kaiscribe": "3.19.4",
                                                                   "modell": "gemini/gemini-3.5-flash_(Rückfall)"}]))

# 3) Warnung über eigene Hochrechnung (3 Tage) → genau eine Karte je Monat
roh = ("NUTZUNG 2026-11 CASWS10 2026-11-16 befunde=4 anthropic=4 gemini=0 rueckfall=0 usd=0.2 chirp_s=1700.5 gruende=-\n"
       "NUTZUNG 2026-11 CASWS14 2026-11-18 befunde=1 anthropic=1 gemini=0 rueckfall=1 usd=0.02 chirp_s=60 "
       "gruende=Datum fehlt:1\nWARNDATEI 2026-11 nein\nTAGESBERICHT 2026-11-18\n| KaiScribe Tagesbericht 2026-11-18\n"
       "NUTZUNG_LESEN=fertig\n")
e = cw.auswerten(roh, "2026-11-18")
check("eigene Hochrechnung: 29,3 min in 3 Tagen ≈ 4 €/Monat → keine Warnung", e["tage"] == 3 and not e["warn_eigen"]
      and 3.9 < e["hoch_eur"] < 4.2, e["hoch_eur"])
roh2 = roh.replace("chirp_s=60 ", "chirp_s=1500 ")
e = cw.auswerten(roh2, "2026-11-18")
check("eigene Hochrechnung > 6 € ab 3 Tagen → Warnung", e["warn_eigen"] and e["hoch_eur"] > 6, e["hoch_eur"])
txt = cw.karte_text(e)
check("Kartentext: Quelle X:\\KaiScribe\\Daten\\nutzung", "Quelle: X:\\KaiScribe\\Daten\\nutzung" in txt, txt)
check("Kartentext: Minuten, €, Rückfälle, a/b/c, keine Quota-Änderung", "hochgerechnet" in txt and "1 Rückfälle" in txt
      and "a) so lassen" in txt and "Keine automatische Quota-Änderung" in txt, txt)
check("noch keine Karte im Monat", not cw.karte_schon_da("2026-11"))
cw.karte_anlegen(e)
check("Karte angelegt (Spalte peter) + Zustand", "--peter" in pathlib.Path(aufrufe).read_text(encoding="utf-8")
      and cw.karte_schon_da("2026-11") and json.load(open(cw.ZUSTAND))["karten"]["2026-11"]["karte"] == 901)
check("Dezember wieder frei", not cw.karte_schon_da("2026-12"))
os.remove(cw.ZUSTAND)
pathlib.Path(cw.KARTEI).write_text(json.dumps({"karten": [{"titel": cw.TITEL.format(eur="7,10", monat="2026-11")}]}),
                                   encoding="utf-8")
check("Zustand weg → Titelsuche in der Kartei verhindert die zweite Karte", cw.karte_schon_da("2026-11"))
check("EXE-Zeile WARNUNG reicht auch", cw.auswerten(roh.replace("| KaiScribe Tagesbericht 2026-11-18\n",
                                                                "| KaiScribe Tagesbericht 2026-11-18\n| WARNUNG: Chirp\n"),
                                                    "2026-11-18")["warn_exe"])
check("Warndatei reicht auch", cw.auswerten(roh.replace("WARNDATEI 2026-11 nein", "WARNDATEI 2026-11 ja"), "2026-11-18")["warn_exe"])

# 4) Alte KaiScribe: einmal je Rechner+Version eine Karte
pathlib.Path(aufrufe).write_text("", encoding="utf-8")
e = cw.auswerten(aus, "2026-11-16")
check("alte KaiScribe → Karte CASWS08", cw.rechner_merken(e) == ["CASWS08 3.18.9 gemini/gemini-3.5-flash"]
      and "KaiScribe an CASWS08 einmal schließen/neu starten" in pathlib.Path(aufrufe).read_text(encoding="utf-8"))
check("zweiter Lauf: keine zweite Karte", cw.rechner_merken(e) == [])
check("letzter Lauf je Rechner im Zustand", json.load(open(cw.ZUSTAND))["rechner"]["CASWS10"]["kaiscribe"] == "3.19.1")

print(f"\n{'❌ ' + str(fails) + ' Fehler' if fails else '✅ alle grün'}")
sys.exit(1 if fails else 0)
