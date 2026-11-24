r"""Pflicht-Abnahme kaiscribe-sammel-2311 am Büro-PC (Peter 23.11.2026, Videos RH 156/165: markierter Text wird nicht ersetzt).

Fährt EIN echtes KaiScribe-Diktat am Testpatienten 451898 mit dem E2E-Werkzeug der Praxis (ris-mods e2e/diktat_e2e.py:
KaiScribe-KOPIE im WAV-Modus als Gast, eigene Brücke, CAS-Auftrag + Leistungen aus der Datenbank, echte Spracherkennung
aus den WAV-Dateien der Teststrecke, echte KI, EOL → <Nr>.rakscribe.txt = Brieftext, JobFinished). Fälle:
  M156 = Knie diktieren → INS → Text im Befund markieren → RECORD → Korrektur sprechen → RECORD (Pause) → Auswahl weg
         OHNE Klick (wie PLAY/Fokuswechsel in RH 156) → RECORD (weiter) → INS → die Markierung ist ERSETZT → EOL
  M165 = Knie diktieren → INS → neue Aufnahme ohne Ziel → RECORD (Pause) → in der Pause markieren → RECORD (weiter) →
         Korrektur sprechen → RECORD (Pause) → Auswahl weg → RECORD (weiter) → INS → Markierung ERSETZT → EOL
Aufruf (py -3.12, nur Standardbibliothek; alle weiteren Argumente gehen unverändert an diktat_e2e.py fall):
  py -3.12 markierung_abnahme.py --e2e <...\e2e\diktat_e2e.py> M156 --nr <Nr> --arbeit <A> --rakscribe <Kopie\KaiScribe.exe>
         --bruecke <...> --schluessel <Praxis-Schlüssel.json> [--wiederholung]
Ausgabe: die Prüfzeilen von diktat_e2e, danach der abgelegte Text (synthetisch, ohne Kopfdaten) und eine Schlusszeile
  MARKABN=<ok|rot> FALL=<M156|M165> NR=<Nr> MARKIERT=<n Zeichen> STATUS_ERSETZT=<ja|nein> GEHALTEN=<ja|nein>
          ERSETZT=<ja|nein> REST_GLEICH=<ja|nein> ABLAGE=<ja|nein> E2E_EXIT=<rc>
Schreibt nichts außer über den normalen Brücken-Weg (diktat_e2e: Sicherung nur 451898, nie vidieren)."""
import importlib.util
import json
import os
import sys

MARK = "befund_suchen#Beginnende Gonarthrose|Gonarthrose|Osteophyten"   # wie E4b der Teststrecke


def e2e_laden(pfad):
    sys.path.insert(0, os.path.dirname(os.path.abspath(pfad)))
    spec = importlib.util.spec_from_file_location("diktat_e2e", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def faelle(m):
    befund = m._START + [{"taste": "RECORD"}, {"sprich": "e4_knie.wav"}] + m._INS
    ende = [{"taste": "INS"}, {"warte_auf": "kontrolle", "timeout_s": 300}, {"merke": "nach_korrektur"}] + m._EOL
    return {
        "M156": befund + [{"trigger": MARK}, {"merke": "markiert"},
                          {"taste": "RECORD"}, {"merke": "start"}, {"sprich": "e4_knie_korrektur.wav"},
                          {"taste": "RECORD", "danach_s": 4}, {"trigger": "befund_sel_weg#1"}, {"merke": "sel_weg"},
                          {"taste": "RECORD"}, {"merke": "weiter"}] + ende,
        "M165": befund + [{"trigger": "befund_fokus_weg#1"}, {"taste": "RECORD"}, {"merke": "start_ohne"},
                          {"taste": "RECORD", "danach_s": 2}, {"trigger": MARK}, {"merke": "markiert"},
                          {"taste": "RECORD"}, {"merke": "start"}, {"sprich": "e4_knie_korrektur.wav"},
                          {"taste": "RECORD", "danach_s": 4}, {"trigger": "befund_sel_weg#1"}, {"merke": "sel_weg"},
                          {"taste": "RECORD"}, {"merke": "weiter"}] + ende,
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
        print(f"MARKABN=rot GRUND=fall_unbekannt ({fall})")
        return 2
    for name, ablauf in f.items():
        m.FAELLE[name] = {"titel": f"Markierungs-Abnahme {name}: markierter Text im Befund wird durch das Diktat ersetzt",
                          "eol": True, "abschnitte": 1, "ablauf": ablauf}
    rc = m.main(["fall"] + rest)
    a = {rest[k]: rest[k + 1] for k in range(len(rest) - 1) if rest[k].startswith("--")}
    r = m.json_lesen(os.path.join(os.path.abspath(a.get("--arbeit", ".")), fall, "ergebnis.json")) or {}
    z = r.get("zustand") or {}
    mk = (z.get("markiert") or {}).get("markiert") or {}
    st = z.get("start") or {}
    sw = z.get("sel_weg") or {}
    nk = (z.get("nach_korrektur") or {}).get("result_voll") or ""
    txt = (r.get("ablage") or {}).get("txt") or ""
    n = len(mk.get("text") or "")
    status_ok = f"Ersetzt markierten Text ({n} Zeichen)" in str(st.get("status_text") or "") and st.get("ziel_text_n") == n
    gehalten = sw.get("markierung") is not None and (z.get("weiter") or {}).get("ziel_text_n") == n
    vor, nach = mk.get("vorher") or "\0", mk.get("nachher") or "\0"
    rest_gleich = bool(n) and nk.startswith(vor) and nk.endswith(nach)
    mitte = nk[len(vor):len(nk) - len(nach)] if rest_gleich else ""
    ersetzt = rest_gleich and bool(mitte.strip()) and (mk.get("text") or "\0") not in mitte
    print("\n--- markiert ---\n" + json.dumps({k: mk.get(k) for k in ("text", "von", "bis")}, ensure_ascii=False)
          + "\n--- an der Stelle jetzt ---\n" + mitte + "\n--- Status bei RECORD ---\n" + str(st.get("status_text"))
          + "\n--- abgelegter Text (<Nr>.rakscribe.txt, synthetisch) ---\n" + txt + "\n--- Ende ---")
    ok = n > 0 and status_ok and gehalten and ersetzt and rest_gleich and bool(txt) and rc == 0
    j = lambda b: "ja" if b else "nein"
    print(f"MARKABN={'ok' if ok else 'rot'} FALL={fall} NR={a.get('--nr')} MARKIERT={n} STATUS_ERSETZT={j(status_ok)} "
          f"GEHALTEN={j(gehalten)} ERSETZT={j(ersetzt)} REST_GLEICH={j(rest_gleich)} ABLAGE={j(bool(txt))} E2E_EXIT={rc}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
