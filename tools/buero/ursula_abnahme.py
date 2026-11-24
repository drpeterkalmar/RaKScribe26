r"""Pflicht-Abnahme kaiscribe-ursula-2011-text-n1 (KaiScribe 3.25.0) am Büro-PC, Testpatient 451898.

Wie rho_osteopen_abnahme.py: ein getipptes Diktat (text_ins) → echte KI → EOL → <Nr>.rakscribe.txt (Brieftext).
Fälle:  G1 = CAS-Leistung „Ganzbein re.“, Diktat OHNE Seite → Titel „Ganzbeinaufnahme im Stand rechts“
        H1 = CAS-Leistung HWS, „50-prozentige Höhenminderung C5/6, Unkovertebralarthrose beidseits“
             → Titel ohne „beidseits“, „50%ige“, keine Leerzeile nach „Ergebnis:“, „Im Übrigen“ nie doppelt hintereinander
        K1 = Knie kurz (Gegenprobe, Titel Kniegelenk bleibt)
Aufruf: py -3.12 ursula_abnahme.py --e2e <...\e2e\diktat_e2e.py> G1 --nr <Nr> --arbeit <A> --rakscribe <Kopie\KaiScribe.exe>
        --bruecke <...> --schluessel <Schlüssel.json> [--wiederholung]
Schlusszeile: URSABN=<ok|rot> FALL=.. NR=.. TITEL=.. PRUEFUNGEN=.. ABLAGE=<ja|nein>
Schreibt nichts außer über den normalen Brücken-Weg (nie vidieren)."""
import importlib.util
import json
import os
import re
import sys

DIKTATE = {
    "G1": "Ganzbeinaufnahme im Stand. Beinachse varisch, Gonarthrose medial Grad zwei. Hüftgelenk altersentsprechend.",
    "H1": ("Halswirbelsäule in zwei Ebenen. 50-prozentige Höhenminderung C5/6, Unkovertebralarthrose beidseits. "
           "Im Übrigen unauffällige Wirbelkörper. Im Übrigen keine Fehlstellung."),
    "K1": "Kniegelenk in zwei Ebenen. Beginnende Gonarthrose. Kein Erguss.",
}


def e2e_laden(pfad):
    sys.path.insert(0, os.path.dirname(os.path.abspath(pfad)))
    spec = importlib.util.spec_from_file_location("diktat_e2e", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def faelle_eintragen(m):
    for name, text in DIKTATE.items():
        m.FAELLE[name] = {"titel": f"Ursula-Abnahme {name}: getipptes Diktat → Befund → EOL → Ablage (Brieftext)",
                          "eol": True, "abschnitte": 1,
                          "ablauf": m._START + [{"trigger": f"text_ins#{name.lower()}|{text}"},
                                                {"warte_auf": "kontrolle", "timeout_s": 300}, {"merke": "nach_ins"}]
                          + m._EOL}


def pruefen(fall, txt):
    """Liefert (Titelzeilen, {Prüfung: bool}) aus dem abgelegten Brieftext (nur Struktur)."""
    zeilen = txt.splitlines()
    titel = [z for z in zeilen if z.startswith("## ") or z.startswith("# ")]
    low = txt.lower()
    p = {}
    ohne_leer = bool(txt.strip())
    p["keine_leerzeile_nach_ergebnis"] = not re.search(r"(?mi)^(?:#+\s*)?Ergebnis:?[ \t]*\n[ \t]*\n", txt)
    p["kein_ergebnistext_als_ueberschrift"] = not any(re.match(r"#+\s*Ergebnis\s*:\s*\S", t) for t in titel)
    p["keine_leere_ueberschrift"] = not re.search(r"(?m)^#+\s*$", txt)
    p["im_uebrigen_nie_doppelt"] = not re.search(r"(?i)im übrigen[^.\n]*\.\s*im übrigen", txt)
    if fall == "G1":
        p["titel_ganzbein_rechts"] = "ganzbeinaufnahme im stand rechts" in low
    if fall == "H1":
        p["prozent_ige"] = "50%ige" in txt or "50 %ige" in txt
        p["kein_prozentig_wort"] = "prozentig" not in low
        p["titel_ohne_beidseits"] = not any("beidseits" in t.lower() for t in titel)
    if fall == "K1":
        p["titel_knie"] = any("knie" in t.lower() for t in titel)
    return titel, p, ohne_leer


def main(argv):
    if "--e2e" not in argv:
        print(__doc__)
        return 2
    i = argv.index("--e2e")
    m = e2e_laden(argv[i + 1])
    rest = argv[:i] + argv[i + 2:]
    fall = rest[0] if rest else ""
    if fall not in DIKTATE:
        print(f"URSABN=rot GRUND=fall_unbekannt ({fall})")
        return 2
    faelle_eintragen(m)
    rc = m.main(["fall"] + rest)
    a = {rest[k]: rest[k + 1] for k in range(len(rest) - 1) if rest[k].startswith("--")}
    r = m.json_lesen(os.path.join(os.path.abspath(a.get("--arbeit", ".")), fall, "ergebnis.json")) or {}
    txt = (r.get("ablage") or {}).get("txt") or ""
    print("\n--- abgelegter Text (<Nr>.rakscribe.txt, synthetisch) ---\n" + txt + "\n--- Ende ---")
    titel, p, hat = pruefen(fall, txt)
    print("Titel/Überschriften:", " | ".join(titel))
    ok = hat and all(p.values())
    print(f"URSABN={'ok' if ok else 'rot'} FALL={fall} NR={a.get('--nr')} "
          f"PRUEFUNGEN={','.join(k + '=' + ('ja' if v else 'nein') for k, v in p.items())} "
          f"ABLAGE={'ja' if hat else 'nein'} E2E_EXIT={rc}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
