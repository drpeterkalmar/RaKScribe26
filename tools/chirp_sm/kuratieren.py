#!/usr/bin/env python3
"""chirp-fachwortliste-n1: Hand-Sichtung der VM-Auswahl (cfw_liste.py, Ausgabe nur gefilterte Fachwörter).
Liest die Ausgabezeilen LISTE-WOERTER/LISTE-PHRASEN (am Mac nur die schon streng gefilterte Liste) und streicht
Allgemeinwörter, die Chirp sicher kann (Brief: „z. B. Nachweis“), Doppel-Beugeformen und Satz-Fragmente.
  python3 tools/chirp_sm/kuratieren.py <lauf.txt> [de_50k.txt]  → schreibt phrases.json "chirp_sm"
Mit de_50k.txt (öffentliche Häufigkeitsliste, hermitdave/FrequencyWords 2018 de_50k) bleiben nur Einträge, deren Wörter
ALLE nicht in der Liste stehen (Variante „smr“, am 24.11.2026 am besten gemessen, 316 Einträge). Dieselbe Liste nutzt
der spätere Mistral-Vergleich (Voxtral context biasing): phrases.json → chirp_sm.
"""
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HIER))

# Allgemeinwörter / allgemeine Adjektive ohne belastbaren Chirp-Fehlhör-Beleg (Hand-Sichtung 24.11.2026)
RAUS = set("""
Nachweis Auffälligkeiten suspekten Mäßige strukturierter Normbereich begrenzte Beidseitige Beginnende Hochgradige
soliden Vereinzelte nachweisbar heterogen Resistenzen Erhaltenes Deutliche Befundänderung zystischen Hochauflösender
s-förmige median allseits ausgeweitet normalem abführenden Harmonische Verdickung sämtlicher vergrößerten messende
proximalen axial abgehender Fortgeschrittene vereinbar Abschnitten Mitabgebildete Normwert weiterführende angedeuteter
partiell beschwerdefrei kompatibel Ausgeprägte dichtes abgrenzbare Diskrete Stationäre aufgetretene Segmenten distalen
dorsale Regelmäßige haltender regelrechter Nervs blanden Narbenverhältnissen Geringe Übrigen seitlich vermehrte Ebenen
pathologisches einsehbaren lateral
intakte Ungehinderte homogen Heterogene abzugrenzen verstärkte Horizontale sekundären versorgte Mitdargestellte
Moderate entfaltet fokal rückgebildet höhergradige Aufteilung betonte linksseitig versus Kompression erkennbar Multiple
ebendort Serielle Projektion zentral rechtsseitig entspringt nachzuweisen eingeschränkte weitgehend wesentlicher
verbliebenen Ausläufer Schnappens Fettgewebe zarter Ganzbeines Unterarm Unterschenkel
""".split())
PHRASEN_BEHALTEN = [
    "strukturierter Drüsenkörper", "Regelmäßige Knochentextur", "periarticuläre Weichteilzone", "suspekten Verkalkungen",
    "subchondraler Sklerosierung", "Spondylosis deformans", "Positive Familienanamnese", "rechtskonvexe Skoliose",
    "linkskonvexe Skoliose", "suspekter Mikrokalk", "skoliotische Asymmetrie", "skoliotische Fehlhaltung",
    "Nearthrosis interspinosa", "Farbcodierte Duplexsonographie", "abführenden Gallenwege", "zentrale Reflexband",
    "Vena cava", "zystischen Herdläsion", "suspekten Herdläsion", "abgehender Endäste", "nervalen Auftreibung",
    "Flachbogig rechtskonvexe", "Parailiacal beidseits",
]


WORT = __import__("re").compile(r"[0-9]+(?:[.,][0-9]+)?|[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)*")


def main(lauf, de_pfad=None):
    woerter, phrasen = [], []
    for z in open(lauf, encoding="utf-8"):
        if z.startswith("LISTE-WOERTER "):
            woerter = [x[0] for x in json.loads(z[14:])]
        if z.startswith("LISTE-PHRASEN "):
            phrasen = [x[0] for x in json.loads(z[14:])]
    fehlt = [p for p in PHRASEN_BEHALTEN if p not in phrasen]
    if fehlt:
        sys.exit("Phrasen nicht in der VM-Auswahl: %s" % fehlt)
    liste = [w for w in woerter if w not in RAUS] + PHRASEN_BEHALTEN
    pfad = os.path.join(ROOT, "phrases.json")
    ph = json.load(open(pfad, encoding="utf-8"))
    alt = set(p.lower() for p in ph["chirp"])
    liste = [w for w in dict.fromkeys(liste) if w.lower() not in alt]
    if de_pfad:
        de = set(z.split()[0].lower() for z in open(de_pfad, encoding="utf-8") if z.strip())
        liste = [p for p in liste if all(w.lower() not in de for w in WORT.findall(p) if not w.isdigit())]
    ph["chirp_sm"] = liste
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(ph, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("chirp_sm", len(liste), "davon Mehrwort", sum(1 for p in liste if " " in p))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
