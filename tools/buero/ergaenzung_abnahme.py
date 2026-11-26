r"""Pflicht-Abnahme kaiscribe-ergaenzung-ohne-ins-n1 am Büro-PC (Peter 26.11.2026, Diktat 20261126060: „Cursor rechts an
die falsch autobefundete Stelle, darüberdiktieren, ohne tippen“ – vorher kam der Text erst mit INS, EOL sagte „Erst INS“).

Fährt EIN echtes KaiScribe-Diktat am Testpatienten 451898 mit dem E2E-Werkzeug der Praxis (ris-mods e2e/diktat_e2e.py:
KaiScribe-KOPIE im WAV-Modus als Gast, eigene Brücke, CAS-Auftrag + Leistungen aus der Datenbank, echte Spracherkennung
aus den WAV-Dateien der Teststrecke, echte KI, EOL → <Nr>.rakscribe.txt = Brieftext, JobFinished). Fälle (KEIN INS nach
der Ergänzung – genau Peters Abnahmeablauf):
  K1 = Knie diktieren → INS → Text im Befund markieren → RECORD → Korrektur sprechen → RECORD (Pause) ⇒ Markierung rechts
       ERSETZT, links nichts angehängt, Status „der übrige Befund bleibt“ → EOL ⇒ direkt abgeschlossen (kein „Erst INS“)
  K2 = Knie diktieren → INS → Cursor ans Befund-Ende (Klick, keine Markierung) → RECORD → sprechen → RECORD (Pause) ⇒
       Text hinten angefügt, Rest Zeichen für Zeichen gleich → EOL ⇒ abgeschlossen
Aufruf (py -3.12, nur Standardbibliothek; alle weiteren Argumente gehen unverändert an diktat_e2e.py fall):
  py -3.12 ergaenzung_abnahme.py --e2e <...\e2e\diktat_e2e.py> K1 --nr <Nr> --arbeit <A> --rakscribe <Kopie\KaiScribe.exe>
         --bruecke <...> --schluessel <Praxis-Schlüssel.json> [--wiederholung]
Ausgabe: Prüfzeilen von diktat_e2e, der abgelegte Text (synthetisch, ohne Kopfdaten) und eine Schlusszeile
  ERGABN=<ok|rot> FALL=<K1|K2> NR=<Nr> PAUSE_RECHTS=<ja|nein> REST_GLEICH=<ja|nein> LINKS_GLEICH=<ja|nein>
         STATUS=<ja|nein> EOL_DIREKT=<ja|nein> ABLAGE=<ja|nein> E2E_EXIT=<rc>
Schreibt nichts außer über den normalen Brücken-Weg (diktat_e2e: Sicherung nur 451898, nie vidieren)."""
import importlib.util
import json
import os
import sys

MARK = "befund_suchen#Beginnende Gonarthrose|Gonarthrose|Osteophyten"   # wie E4b der Teststrecke / M156


def e2e_laden(pfad):
    sys.path.insert(0, os.path.dirname(os.path.abspath(pfad)))
    spec = importlib.util.spec_from_file_location("diktat_e2e", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def faelle(m):
    befund = m._START + [{"taste": "RECORD"}, {"sprich": "e4_knie.wav"}] + m._INS
    pause = [{"taste": "RECORD"}, {"merke": "start"}, {"sprich": "e4_knie_korrektur.wav"},
             {"taste": "RECORD", "danach_s": 10}, {"merke": "pause"}]          # Pause: Erkennung + Einfügen abwarten
    return {
        "K1": befund + [{"trigger": MARK}, {"merke": "markiert"}] + pause + m._EOL,
        "K2": befund + [{"trigger": "befund_klick#99999"}, {"merke": "markiert"}] + pause + m._EOL,
    }


def main(argv):
    if "--e2e" not in argv:
        print(__doc__)
        return 2
    i = argv.index("--e2e")
    m = e2e_laden(argv[i + 1])
    rest = argv[:i] + argv[i + 2:]
    fall = rest[0] if rest else ""
    f = faelle(m)
    if fall not in f:
        print(f"ERGABN=rot GRUND=fall_unbekannt ({fall})")
        return 2
    for name, ablauf in f.items():
        m.FAELLE[name] = {"titel": f"Ergänzungs-Abnahme {name}: Pause fügt rechts ein, EOL ohne INS",
                          "eol": True, "abschnitte": 1, "ablauf": ablauf}
    rc = m.main(["fall"] + rest)
    a = {rest[k]: rest[k + 1] for k in range(len(rest) - 1) if rest[k].startswith("--")}
    r = m.json_lesen(os.path.join(os.path.abspath(a.get("--arbeit", ".")), fall, "ergebnis.json")) or {}
    z = r.get("zustand") or {}
    vor_z = z.get("markiert") or {}
    ps = z.get("pause") or {}
    st = z.get("start") or {}
    eol = z.get("nach_eol") or {}
    vorher_befund = vor_z.get("result_voll") or ""
    rechts = ps.get("result_voll") or ""
    txt = (r.get("ablage") or {}).get("txt") or ""
    if fall == "K1":
        mk = vor_z.get("markiert") or {}
        vor, nach = mk.get("vorher") or "\0", mk.get("nachher") or "\0"
        rest_gleich = bool(mk.get("text")) and rechts.startswith(vor) and rechts.endswith(nach)
        mitte = rechts[len(vor):len(rechts) - len(nach)] if rest_gleich else ""
        pause_rechts = rest_gleich and bool(mitte.strip()) and (mk.get("text") or "\0") not in mitte
    else:
        rest_gleich = bool(vorher_befund) and rechts.startswith(vorher_befund.rstrip())
        mitte = rechts[len(vorher_befund.rstrip()):] if rest_gleich else ""
        pause_rechts = rest_gleich and bool(mitte.strip())
    links_gleich = (ps.get("transcript") or "") == (vor_z.get("transcript") or "") and bool(vor_z.get("transcript"))
    status_ok = "der übrige Befund bleibt" in str(st.get("status_text") or "") and ps.get("job_zustand") == "PAUSED"
    eol_direkt = "Erst INS" not in str(eol.get("hinweis") or "") and bool(txt)
    print("\n--- an der Stelle jetzt (nach der Pause, ohne INS) ---\n" + mitte + "\n--- Status bei RECORD ---\n"
          + str(st.get("status_text")) + "\n--- Status in der Pause ---\n" + str(ps.get("status_text"))
          + "\n--- abgelegter Text (<Nr>.rakscribe.txt, synthetisch) ---\n" + txt + "\n--- Ende ---")
    ok = pause_rechts and rest_gleich and links_gleich and status_ok and eol_direkt and rc == 0
    j = lambda b: "ja" if b else "nein"   # noqa: E731
    print(f"ERGABN={'ok' if ok else 'rot'} FALL={fall} NR={a.get('--nr')} PAUSE_RECHTS={j(pause_rechts)} "
          f"REST_GLEICH={j(rest_gleich)} LINKS_GLEICH={j(links_gleich)} STATUS={j(status_ok)} EOL_DIREKT={j(eol_direkt)} "
          f"ABLAGE={j(bool(txt))} E2E_EXIT={rc}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
