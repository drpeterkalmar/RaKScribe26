r"""Pflicht-Abnahme kaiscribe-rho-osteopen-n1 am Büro-PC (Georg 22.11.2026: Rho ≥ 7 → „Osteopenischer Knochenaspekt.“).

Fährt EIN echtes KaiScribe-Diktat am Testpatienten 451898 mit dem E2E-Werkzeug der Praxis (ris-mods e2e/diktat_e2e.py:
KaiScribe-KOPIE im WAV-Modus als Gast, eigene Brücke mit der VBView-Zeile, CAS-Auftrag + Leistungen aus der Datenbank,
echte KI, EOL → <Nr>.rakscribe.txt = Text, den CAS in den Brief übernimmt, JobFinished). Statt Audio tippt der Ablauf
den Diktattext ins Diktat-Feld („Befund aus Text“, Selbsttest-Phase text_ins) – Spracherkennung ist hier nicht Prüfgegenstand.
Fälle:  R8 = „Lendenwirbelsäule … Rho Score 8.“ → Rho-Schlussbefund + „Osteopenischer Knochenaspekt.“ statt Normalsatz
        R6 = dasselbe mit Score 6 → kein Rho-Text, Mineralisations-Normalsatz bleibt (Gegenprobe)
        M8 = LWS + Beckenübersicht, Rho 8 (Eintrag mit zwei Leistungen) → in BEIDEN Teilen ersetzt
Aufruf (py -3.12, nur Standardbibliothek; alle weiteren Argumente gehen unverändert an diktat_e2e.py fall):
  py -3.12 rho_osteopen_abnahme.py --e2e <...\e2e\diktat_e2e.py> R8 --nr <Nr> --arbeit <A> --rakscribe <Kopie\KaiScribe.exe>
         --bruecke <...> --schluessel <Praxis-Schlüssel.json> [--wiederholung]
Ausgabe: die Prüfzeilen von diktat_e2e, danach der abgelegte Text (synthetisch, ohne Kopfdaten) und eine Schlusszeile
  RHOABN=<ok|rot> FALL=<R8|R6|M8> NR=<Nr> OSTEOPEN=<n> NORMALSATZ=<n> RHO_TEXT=<ja|nein> ABLAGE=<ja|nein>
Schreibt nichts außer über den normalen Brücken-Weg (diktat_e2e: Sicherung nur 451898, nie vidieren)."""
import importlib.util
import json
import os
import re
import sys

DIKTATE = {
    "R8": ("Lendenwirbelsäule in zwei Ebenen. Geringe Osteochondrose L5/S1. Rho Score 8.", 2, True),
    "R6": ("Lendenwirbelsäule in zwei Ebenen. Geringe Osteochondrose L5/S1. Rho Score 6.", 1, False),
    "M8": ("Lendenwirbelsäule in zwei Ebenen: geringe Osteochondrose L5/S1. Rho Score 8. "
           "Beckenübersicht: unauffällig.", 3, True),
}
OSTEOPEN = "osteopenischer knochenaspekt"
# Mineralisations-Normalsatz (wie befund_regeln._osteo_normal, hier nur grob zum Zählen)
NORMALSATZ = re.compile(r"(?:mineralgehalt|knochenmineralisation|kalksalzgehalt)[^.]{0,80}?"
                        r"(?:regelrecht|unauffällig|normal)|(?:regelrecht|normal)\w*\s+(?:knochen)?mineral", re.I)


def e2e_laden(pfad):
    sys.path.insert(0, os.path.dirname(os.path.abspath(pfad)))
    spec = importlib.util.spec_from_file_location("diktat_e2e", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def faelle_eintragen(m):
    for name, (text, abschnitte, _rho) in DIKTATE.items():
        m.FAELLE[name] = {"titel": f"Rho-Abnahme {name}: getipptes Diktat → Befund → EOL → Ablage (Brieftext)",
                          "eol": True, "abschnitte": abschnitte,
                          "ablauf": m._START + [{"trigger": f"text_ins#{name.lower()}|{text}"},
                                                {"warte_auf": "kontrolle", "timeout_s": 300}, {"merke": "nach_ins"}]
                          + m._EOL}


def main(argv):
    if "--e2e" not in argv:
        print(__doc__)
        return 2
    i = argv.index("--e2e")
    m = e2e_laden(argv[i + 1])
    rest = argv[:i] + argv[i + 2:]
    fall = rest[0] if rest else ""
    if fall not in DIKTATE:
        print(f"RHOABN=rot GRUND=fall_unbekannt ({fall})")
        return 2
    faelle_eintragen(m)
    rc = m.main(["fall"] + rest)
    a = {rest[k]: rest[k + 1] for k in range(len(rest) - 1) if rest[k].startswith("--")}
    r = m.json_lesen(os.path.join(os.path.abspath(a.get("--arbeit", ".")), fall, "ergebnis.json")) or {}
    txt = (r.get("ablage") or {}).get("txt") or ""
    print("\n--- abgelegter Text (<Nr>.rakscribe.txt, synthetisch) ---\n" + txt + "\n--- Ende ---")
    beschreibung = "\n".join(t.split("## Ergebnis", 1)[0] for t in txt.split("\n## ") if "Knochendichtescreening" not in t[:80])
    n_o = txt.lower().count(OSTEOPEN)
    n_n = len(NORMALSATZ.findall(beschreibung))
    rho = "Knochendichtescreening" in txt
    soll_rho = DIKTATE[fall][2]
    if soll_rho:
        soll = n_o == (2 if fall == "M8" else 1) and n_n == 0 and rho
    else:
        soll = n_o == 0 and n_n >= 1 and not rho
    print(f"RHOABN={'ok' if soll and txt else 'rot'} FALL={fall} NR={a.get('--nr')} OSTEOPEN={n_o} NORMALSATZ={n_n} "
          f"RHO_TEXT={'ja' if rho else 'nein'} ABLAGE={'ja' if txt else 'nein'} E2E_EXIT={rc}")
    return 0 if soll and txt else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
