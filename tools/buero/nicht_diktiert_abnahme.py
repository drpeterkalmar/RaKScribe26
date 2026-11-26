r"""Pflicht-Abnahme kaiscribe-nicht-diktiert-streichen-n1 (KaiScribe ≥ 3.30.0, Georg 26.11.2026 „1b“) am Büro-PC, 451898.

Wie ursula_abnahme.py: ein getipptes Diktat (text_ins) → echte KI → EOL → <Nr>.rakscribe.txt (Brieftext).
Voraussetzung: CAS-Auftrag am Testpatienten mit MEHREREN Leistungen (z. B. LWS + Beckenübersicht wie M8 der
Rho-Abnahme), diktiert wird nur die LWS.
Fälle:  N1 = nur LWS diktiert → im Brief GENAU EIN Befund (Lendenwirbelsäule), keine Überschrift/kein Normaltext der
             nicht diktierten Leistung(en); im Protokoll (rakscribe.log der Kopie) „[CAS] Hinweis: … bestellt, aber nicht
             diktiert – bitte prüfen“ (= rote Prüfzeile im Befundfenster)
        A1 = alle Leistungen diktiert (LWS + Becken) → zwei Befunde, keine solche Prüfzeile (Gegenprobe)
Aufruf: py -3.12 nicht_diktiert_abnahme.py --e2e <...\e2e\diktat_e2e.py> N1 --nr <Nr> --arbeit <A>
        --rakscribe <Kopie\KaiScribe.exe> --bruecke <...> --schluessel <Schlüssel.json> [--log <rakscribe.log>]
Schlusszeile: NDABN=<ok|rot> FALL=.. NR=.. BEFUNDE=<n> PRUEFZEILE=<ja|nein|ungeprüft> PRUEFUNGEN=.. ABLAGE=<ja|nein>
Schreibt nichts außer über den normalen Brücken-Weg (nie vidieren). Gibt keinen Patiententext aus außer dem Brieftext
des synthetischen Diktats."""
import importlib.util
import os
import re
import sys

DIKTATE = {
    "N1": "Lendenwirbelsäule in zwei Ebenen. Geringe Osteochondrose L5/S1.",
    "A1": "Lendenwirbelsäule in zwei Ebenen: geringe Osteochondrose L5/S1. Beckenübersicht: unauffällig.",
}
PRUEF = "bestellt, aber nicht diktiert – bitte prüfen"


def e2e_laden(pfad):
    sys.path.insert(0, os.path.dirname(os.path.abspath(pfad)))
    spec = importlib.util.spec_from_file_location("diktat_e2e", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def faelle_eintragen(m):
    for name, text in DIKTATE.items():
        m.FAELLE[name] = {"titel": f"Nicht-diktiert-Abnahme {name}: getipptes Diktat → Befund → EOL → Ablage (Brieftext)",
                          "eol": True, "abschnitte": 1 if name == "N1" else 2,
                          "ablauf": m._START + [{"trigger": f"text_ins#{name.lower()}|{text}"},
                                                {"warte_auf": "kontrolle", "timeout_s": 300}, {"merke": "nach_ins"}]
                          + m._EOL}


def befund_titel(txt):
    """Überschriften der Befunde (ohne „Befund“/„Ergebnis“)."""
    out = []
    for z in txt.splitlines():
        m = re.match(r"#+\s*(.+?)\s*:?\s*$", z)
        if m and m.group(1).lower().rstrip(":") not in ("befund", "ergebnis"):
            out.append(m.group(1))
    return out


def log_pruefzeile(pfad):
    """Letzte „[CAS] Hinweis:“-Zeile der Kopie → enthält die Prüfzeile? None = kein Protokoll angegeben/lesbar."""
    if not pfad or not os.path.exists(pfad):
        return None
    with open(pfad, encoding="utf-8", errors="replace") as f:
        zeilen = [z for z in f if "[CAS] Hinweis:" in z]
    return bool(zeilen) and PRUEF in zeilen[-1]


def pruefen(fall, txt, log_ok):
    t = befund_titel(txt)
    low = txt.lower()
    p = {"titel_lws": any("lendenwirbelsäule" in x.lower() for x in t),
         "pruefzeile_nicht_im_brief": PRUEF not in txt}
    if fall == "N1":
        p["genau_ein_befund"] = len(t) == 1
        p["kein_becken_titel"] = not any("becken" in x.lower() for x in t)
        p["kein_becken_normaltext"] = "beckenschaufel" not in low and "iliosakral" not in low
        if log_ok is not None:
            p["pruefzeile_im_fenster"] = log_ok
    else:
        p["zwei_befunde"] = len(t) == 2
        if log_ok is not None:
            p["keine_pruefzeile"] = not log_ok
    return t, p


def main(argv):
    if "--e2e" not in argv:
        print(__doc__)
        return 2
    i = argv.index("--e2e")
    m = e2e_laden(argv[i + 1])
    rest = argv[:i] + argv[i + 2:]
    log_pfad = None
    if "--log" in rest:
        j = rest.index("--log")
        log_pfad = rest[j + 1]
        rest = rest[:j] + rest[j + 2:]
    fall = rest[0] if rest else ""
    if fall not in DIKTATE:
        print(f"NDABN=rot GRUND=fall_unbekannt ({fall})")
        return 2
    faelle_eintragen(m)
    rc = m.main(["fall"] + rest)
    a = {rest[k]: rest[k + 1] for k in range(len(rest) - 1) if rest[k].startswith("--")}
    r = m.json_lesen(os.path.join(os.path.abspath(a.get("--arbeit", ".")), fall, "ergebnis.json")) or {}
    txt = (r.get("ablage") or {}).get("txt") or ""
    print("\n--- abgelegter Text (<Nr>.rakscribe.txt, synthetisch) ---\n" + txt + "\n--- Ende ---")
    log_ok = log_pruefzeile(log_pfad)
    titel, p = pruefen(fall, txt, log_ok)
    print("Titel/Überschriften:", " | ".join(titel))
    hat = bool(txt.strip())
    ok = hat and all(p.values())
    print(f"NDABN={'ok' if ok else 'rot'} FALL={fall} NR={a.get('--nr')} BEFUNDE={len(titel)} "
          f"PRUEFZEILE={'ungeprüft' if log_ok is None else ('ja' if log_ok else 'nein')} "
          f"PRUEFUNGEN={','.join(k + '=' + ('ja' if v else 'nein') for k, v in p.items())} "
          f"ABLAGE={'ja' if hat else 'nein'} E2E_EXIT={rc}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
