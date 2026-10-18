#!/usr/bin/env python3
"""tools/verify_kurzsaetze.py — Live-Gate (Peter 18.10.2026): diktierte KURZSÄTZE dürfen nie wegfallen.

Anlass: E2E-Fall K10 (ris-mods, ISG-Diktat) – „die BWS ist nicht abgebildet“ fehlte in einer Runde im Befund.
Harmlos, aber dieselbe Mechanik würde auch „Keine Fraktur.“ oder „Vergleich mit Vorbefund nicht möglich.“ treffen.

Prüft je Diktat, ob jeder diktierte Kurzsatz INHALTLICH im Befund steht (Regex auf den Kern, Formulierung frei).
Absichtlich nur Sätze, die die Vorlage NICHT ohnehin mitbringt (sonst maskiert der Normalbefund einen Drop).
v3.16.6: + 4 Fälle (Funktionsaufnahmen/CT nur empfohlen, Hüfte nicht miterfasst, Kontrolle in 6 Wochen), VERBOTEN = Spezial-
Vorlage einer nur empfohlenen Untersuchung, Gegenprobe „keine erfundene Empfehlung“ bei Diktaten ohne Empfehlung.
Ketten: EXE (pp.exe_kette = pipeline.befund_aus_diktat) und Web (pp.web_kette = Call 0/1/2 wie pipeline.ts),
echtes Gemini, je N Läufe (Standard 3; temp 0 ist nicht deterministisch).

  python3 tools/verify_kurzsaetze.py [läufe]
Ergebnis: docs/benchmarks/kurzsaetze_live_<VERSION>.json, Exit 1 bei jedem fehlenden Kurzsatz.
"""
import json
import pathlib
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "source_code")]
import prod_pipeline as pp  # noqa: E402

# (Diktat, [(Kurzsatz, Regex auf den Inhalt – lowercase-Text)])
FAELLE = [
    ("Iliosakralgelenke. Mäßige subchondrale Sklerosierung der ISG beidseits, rechts betont. Gelenkspalt erhalten. "
     "Miterfasste LWS mit Osteochondrose L5 S1, die BWS ist nicht abgebildet. Ergebnis: Mäßige ISG-Arthrose beidseits, "
     "rechts betont.",
     [("die BWS ist nicht abgebildet", r"(bws|brustwirbels\w*)[^.\n]{0,40}nicht[^.\n]{0,25}(abgebildet|dargestellt|erfasst)"
       r"|nicht[^.\n]{0,30}(abgebildet|dargestellt|erfasst)[^.\n]{0,30}(bws|brustwirbels)")]),
    ("LWS in zwei Ebenen. Osteochondrose L4 L5 mit ventralen Spondylophyten. Vergleich mit Vorbefund nicht möglich. "
     "Ergebnis: Osteochondrose L4/L5.",
     [("Vergleich mit Vorbefund nicht möglich", r"vergleich[^.\n]{0,40}(nicht möglich|nicht vorliegend|liegt nicht vor|fehlt)"
       r"|vorbefund[^.\n]{0,30}(nicht|kein)")]),
    ("Knie rechts in zwei Ebenen. Mäßige Gonarthrose medial betont. Keine freien Gelenkkörper. "
     "Klinische Korrelation empfohlen.",
     [("Keine freien Gelenkkörper", r"(kein\w*|ohne)[^.\n]{0,25}(freie\w*\s+)?gelenkkörper"),
      ("Klinische Korrelation empfohlen", r"klinisch\w*[^.\n]{0,20}korrelation")]),
    ("Handgelenk links in zwei Ebenen. Zustand nach distaler Radiusfraktur mit Plattenosteosynthese, knöchern konsolidiert. "
     "Keine Materiallockerung. Keine neue Fraktur.",
     [("Keine Materiallockerung", r"(kein\w*|ohne)[^.\n]{0,30}(material)?lockerung|lockerung[^.\n]{0,25}(kein|nicht)"),
      ("Keine neue Fraktur", r"(kein\w*|ohne)[^.\n]{0,20}(neue|frische)[^.\n]{0,10}fraktur")]),
    ("Thorax liegend, eingeschränkt beurteilbar. ZVK von rechts jugulär, Spitze in Projektion auf die Vena cava superior. "
     "Kein Pneumothorax. Herz normal groß.",
     [("eingeschränkt beurteilbar", r"eingeschränkt[^.\n]{0,20}beurteil"),
      ("ZVK-Spitze in der V. cava superior", r"(zvk|venenkatheter)[^\n]{0,120}(vena cava|v\. cava|cava superior)")]),
    ("Hüfte links in zwei Ebenen. Mäßige Coxarthrose mit Gelenkspaltverschmälerung kranial. Kein Hinweis auf "
     "Hüftkopfnekrose. Ergebnis: Mäßige Coxarthrose links.",
     [("Kein Hinweis auf Hüftkopfnekrose", r"(kein\w*|ohne)[^.\n]{0,30}(hüft)?kopfnekrose")]),
    ("Sonographie Schulter rechts. Gelenkseitige Partialruptur der Supraspinatussehne. Keine Komplettruptur. "
     "Bursa subacromialis nicht verdickt.",
     [("Keine Komplettruptur", r"(kein\w*|ohne)[^.\n]{0,20}(komplett|vollständig|transmural)\w*[^.\n]{0,10}ruptur"
       r"|nicht[^.\n]{0,15}(komplett|vollständig|transmural)")]),
    ("Sprunggelenk rechts in zwei Ebenen. Weichteilschwellung lateral. Keine Fraktur. Gehaltene Aufnahmen "
     "bei klinischem Verdacht auf Bandinstabilität empfohlen.",
     [("Gehaltene Aufnahmen empfohlen", r"gehalten\w*[^.\n]{0,90}(empfohlen|empfehl|angeraten|sinnvoll)"
       r"|empfehl\w*[^.\n]{0,40}gehalten")]),
    # Fall 8b-Logik steht in VERBOTEN: empfohlene (nicht gemachte) gehaltene Aufnahmen dürfen nicht befundet werden
    # v3.16.6: dieselben Klassen weiter gefasst (Funktionsaufnahmen/CT nur empfohlen, Einschränkung beim Becken, Kontrolle)
    ("HWS in zwei Ebenen. Steilstellung der HWS. Osteochondrose C5 C6. Funktionsaufnahmen empfohlen.",
     [("Funktionsaufnahmen empfohlen", r"funktion\w*[^.\n]{0,60}(empfohlen|empfehl|angeraten|sinnvoll)|empfehl\w*[^.\n]{0,40}funktion")]),
    ("Becken. ISG-Arthrose beidseits. Die rechte Hüfte ist nicht vollständig miterfasst.",
     [("Die rechte Hüfte ist nicht miterfasst", r"hüft\w*[^.\n]{0,50}nicht[^.\n]{0,30}(miterfasst|erfasst|abgebildet|dargestellt)"
       r"|nicht[^.\n]{0,30}(miterfasst|erfasst|abgebildet|dargestellt)[^.\n]{0,40}hüft")]),
    ("Handgelenk links in zwei Ebenen. Zustand nach distaler Radiusfraktur, in achsengerechter Stellung konsolidierend. "
     "Röntgenkontrolle in 6 Wochen empfohlen.",
     [("Kontrolle in 6 Wochen empfohlen", r"kontroll\w*[^.\n]{0,40}(6|sechs) wochen|(6|sechs) wochen[^.\n]{0,40}kontroll")]),
    ("Thorax pa. Rundherd im rechten Oberfeld, 15 mm. CT Thorax zur weiteren Abklärung empfohlen.",
     [("CT Thorax zur Abklärung empfohlen", r"(\bct\b|computertomo\w*)[^.\n]{0,60}(empfohlen|empfehl|abklärung|angeraten)"
       r"|(empfehl|abklärung)\w*[^.\n]{0,40}(\bct\b|computertomo)"),
      ("Rundherd 15 mm", r"rundherd[^\n]{0,80}15 mm|15 mm[^\n]{0,60}rundherd")]),
]


# Fall-Nr. → Muster, die NICHT im Befund stehen dürfen (erfundene Inhalte aus falscher Vorlage)
VERBOTEN = {8: [("Befund der nur EMPFOHLENEN gehaltenen Aufnahmen", r"öffnungswinkel|talusvorschub|mit gehaltenen aufnahmen")],
            # v3.16.6: nur empfohlene Untersuchung ≠ Vorlage (Titel/Normalsätze der Spezial-Vorlage)
            9: [("Befund der nur EMPFOHLENEN Funktionsaufnahmen", r"## funktionsaufnahmen|ante- und retroflexion|treppenphänomen")],
            10: [("Vorlage Becken + Hüfte trotz „nicht miterfasst“", r"## beckenübersicht und hüfte")],
            12: [("Vorlage CT Thorax trotz „CT empfohlen“", r"## ct thorax|mediastinum: keine")]}
# v3.16.6 Gegenprobe gegen Erfinden: ohne diktierte Empfehlung darf keine im Befund stehen
ERFUNDEN = ("keine erfundene Empfehlung", r"empfohlen|empfehl|angeraten|anzuraten|ratsam|\bggf\b|gegebenenfalls")


def verboten(i):
    v = list(VERBOTEN.get(i + 1, []))
    if not re.search(r"empf|angerat|anzurat|ratsam|ggf", FAELLE[i][0].lower()):
        v.append(ERFUNDEN)
    return v


def befundtext(rep):
    """Alles außer der Titelzeile; Befund + Ergebnis zählen beide (der Satz darf auch im Ergebnis stehen)."""
    return re.sub(r"\s+", " ", rep or "").lower()


def lauf(kette, diktat):
    try:
        return (pp.exe_kette if kette == "exe" else pp.web_kette)(diktat) or ""
    except Exception as e:  # noqa: BLE001
        return "FEHLER %r" % e


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    auftraege = [(k, i, r) for i in range(len(FAELLE)) for k in ("exe", "web") for r in range(n)]
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        reps = list(ex.map(lambda a: lauf(a[0], FAELLE[a[1]][0]), auftraege))
    out, fehlt, gesamt = [], 0, 0
    for (k, i, r), rep in zip(auftraege, reps):
        diktat, saetze = FAELLE[i]
        txt = befundtext(rep)
        miss = [s for s, rx in saetze if not re.search(rx, txt)]
        miss += [s for s, rx in verboten(i) if re.search(rx, txt)]
        saetze = saetze + verboten(i)
        gesamt += len(saetze)
        fehlt += len(miss)
        out.append({"fall": i + 1, "kette": k, "lauf": r + 1, "diktat": diktat, "fehlt": miss, "befund": rep})
    print("Kurzsätze: %d/%d erhalten (%d Läufe je Kette, %.0f s)" % (gesamt - fehlt, gesamt, n, time.time() - t0))
    for i, (diktat, saetze) in enumerate(FAELLE):
        for s, _ in saetze + verboten(i):
            for k in ("exe", "web"):
                rot = sum(1 for o in out if o["fall"] == i + 1 and o["kette"] == k and s in o["fehlt"])
                print("  %s Fall %d %-4s %d/%d  %s" % ("✅" if not rot else "❌", i + 1, k, n - rot, n, s))
    ver = (ROOT / "VERSION").read_text().strip()
    ziel = ROOT / "docs" / "benchmarks" / ("kurzsaetze_live_%s.json" % ver)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps({"version": ver, "laeufe": n, "erhalten": gesamt - fehlt, "gesamt": gesamt,
                                "ergebnisse": out}, ensure_ascii=False, indent=1))
    print("→", ziel.relative_to(ROOT))
    sys.exit(1 if fehlt else 0)


if __name__ == "__main__":
    main()
