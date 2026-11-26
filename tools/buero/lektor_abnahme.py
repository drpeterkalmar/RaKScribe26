r"""Pflicht-Abnahme kaiscribe-lektor-einbau-n1 (KaiScribe ≥ 3.32.0) am Büro-PC, Testpatient 451898, außerhalb der Ordi-Zeit.

Wie nicht_diktiert_abnahme.py: KaiScribe-KOPIE als Gast (ris-mods e2e/diktat_e2e.py, Befunder kp), echter CAS-Auftrag,
getipptes Diktat (text_ins) → echte Befund-KI (Konto A) → Lektor (Opus 5.5, Konto A) → EOL → <Nr>.rakscribe.txt.
Der Schalter der Ordi (X:\KaiScribe\Daten\lektor.json) wird NIE angefasst: das Werkzeug legt eine eigene Schalter-Datei
in --arbeit an und trägt LEKTOR_DATEI in die config.ini NEBEN DER KOPIE ein (danach wieder auf „aus“).
Fälle (je Fall ein frischer Eintrag, eine benutzte Nr. wird abgelehnt):
  L0 = Schalter AUS (kp false) → kein „[LEKTOR] gestartet“ im Protokoll, Verhalten wie 3.31.0 (Brief = Feld bei INS)
  L1 = Schalter AN für kp, 40 s warten, dann EOL → „[LEKTOR] fertig …“ mit ≥ 1 übernommener Korrektur oder ≥ 1 Prüfzeile;
       Prüfzeilen stehen in der Hinweiszeile (cas_hinweise, „(Lektor) – bitte prüfen“) und NIE im Brief; Brief = Feld
       nach dem Lektor (Korrekturen sind drin, Rest wörtlich)
  LS = Schalter AN, EOL SOFORT nach dem Befund → „[LEKTOR] bei EOL noch nicht fertig … Befund unverändert“, Brief = Feld
       bei INS (Ausfall-Fall „bei EOL nicht fertig“; Netz-/HTTP-Ausfall ist offline getestet: tests/offline/test_lektor.py)
Aufruf: py -3.12 lektor_abnahme.py --e2e <...\e2e\diktat_e2e.py> L1 --nr <Nr> --arbeit <A> --rakscribe <Kopie\KaiScribe.exe>
        --bruecke <...> --schluessel <Schlüssel.json> --log <Kopie\rakscribe.log> [--diktat 2]
Schlusszeile: LKABN=<ok|rot> FALL=.. NR=.. GESTARTET=.. FERTIG=.. UEBERNOMMEN=n PRUEFZEILEN=n PRUEFUNGEN=.. ABLAGE=ja|nein
Gibt außer dem Brieftext des synthetischen Diktats keinen Patiententext aus; schreibt nur über den normalen Brücken-Weg
(nie vidieren, danach stornieren)."""
import importlib.util
import json
import os
import re
import sys

# Diktate mit Stellen, die der Lektor melden/korrigieren soll (Seitenwiderspruch, Tippfehler wie im Messlauf n1)
DIKTATE = {
    "1": "Kniegelenk rechts in zwei Ebenen. Mäßiggradige mediale Gonarthrose links. Kein Gelenkserguss.",
    "2": "Handgelenk links in zwei Ebenen. Geringe radikarpale Arthrose mit Asymetrie des Gelenkspalts. Keine Fraktur.",
    "3": "Schultergelenk rechts in zwei Ebenen. Keine Luxation. Luxation des AC-Gelenkes Tossy 3. AC-Gelenk unauffällig.",
}
PRUEF = "(Lektor) – bitte prüfen"


def e2e_laden(pfad):
    sys.path.insert(0, os.path.dirname(os.path.abspath(pfad)))
    spec = importlib.util.spec_from_file_location("diktat_e2e", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def schalter_setzen(arbeit, kopie_exe, an):
    """Eigene Schalter-Datei + LEKTOR_DATEI in der config.ini der KOPIE (nie die der Ordi)."""
    os.makedirs(arbeit, exist_ok=True)
    pf = os.path.join(os.path.abspath(arbeit), "lektor_test.json")
    with open(pf, "w", encoding="utf-8") as f:
        json.dump({"befunder": {"kp": bool(an), "rg": False}, "monatsdeckel_usd": 5}, f)
    ini = os.path.join(os.path.dirname(os.path.abspath(kopie_exe)), "config.ini")
    zeilen = open(ini, encoding="utf-8-sig").read().splitlines() if os.path.exists(ini) else ["[SETTINGS]"]
    zeilen = [z for z in zeilen if not z.strip().upper().startswith("LEKTOR_DATEI")]
    if not any(z.strip() == "[SETTINGS]" for z in zeilen):
        zeilen.insert(0, "[SETTINGS]")
    i = next(k for k, z in enumerate(zeilen) if z.strip() == "[SETTINGS]")
    zeilen.insert(i + 1, f"LEKTOR_DATEI = {pf}")
    with open(ini, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen) + "\n")
    return pf, ini


def schalter_zurueck(ini):
    """Nach dem Lauf: LEKTOR_DATEI = aus in der Kopie (Schalter wieder aus)."""
    if ini and os.path.exists(ini):
        zeilen = [("LEKTOR_DATEI = aus" if z.strip().upper().startswith("LEKTOR_DATEI") else z)
                  for z in open(ini, encoding="utf-8-sig").read().splitlines()]
        with open(ini, "w", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")


def faelle_eintragen(m, diktat):
    text = DIKTATE[diktat]
    vor = m._START + [{"trigger": f"text_ins#lektor|{text}"}, {"warte_auf": "kontrolle", "timeout_s": 300},
                      {"merke": "nach_ins"}]
    m.FAELLE["L0"] = {"titel": "Lektor-Abnahme L0: Schalter aus → wie bisher", "eol": True, "abschnitte": 1,
                      "ablauf": vor + [{"warte_s": 20}, {"merke": "vor_eol"}] + m._EOL}
    m.FAELLE["L1"] = {"titel": "Lektor-Abnahme L1: Schalter an → Korrektur/Prüfzeile vor EOL", "eol": True, "abschnitte": 1,
                      "ablauf": vor + [{"warte_s": 40}, {"merke": "vor_eol"}] + m._EOL}
    m.FAELLE["LS"] = {"titel": "Lektor-Abnahme LS: EOL bevor der Lektor fertig ist → Befund unverändert", "eol": True,
                      "abschnitte": 1, "ablauf": vor + m._EOL}


def log_lektor(pfad, ab=0):
    """[LEKTOR]-Zeilen der Kopie ab Byte ab → dict (nur Zahlen aus der Fertig-Zeile)."""
    if not pfad or not os.path.exists(pfad):
        return None
    with open(pfad, "rb") as f:
        f.seek(ab)
        zeilen = [z for z in f.read().decode("utf-8", "replace").splitlines() if "[LEKTOR]" in z]
    d = {"gestartet": any("[LEKTOR] gestartet" in z for z in zeilen),
         "fertig": any("[LEKTOR] fertig" in z for z in zeilen),
         "nicht_fertig": any("bei EOL noch nicht fertig" in z for z in zeilen),
         "ausgefallen": any("[LEKTOR] ausgefallen" in z for z in zeilen), "uebernommen": 0, "pruefzeilen": 0}
    for z in zeilen:
        m = re.search(r"übernommen (\d+).*Prüfzeilen (\d+)", z)
        if m and "[LEKTOR] fertig" in z:
            d["uebernommen"], d["pruefzeilen"] = int(m.group(1)), int(m.group(2))
    return d


def _norm(t):
    return " ".join((t or "").replace("\r", "").replace("#", "").replace("*", "").split())


def _gleich(feld, brief):
    """Feldtext (im Zustand evtl. gekürzt) steht so im Brief: Vergleich ohne Markdown, auf die Länge des Felds."""
    f, b = _norm(feld), _norm(brief)
    return bool(f) and (f in b or b.startswith(f[:400]))


def pruefen(fall, txt, ergebnis, lk):
    zust = ergebnis.get("zustand") or {}
    ins = (zust.get("nach_ins") or {}).get("result_voll") or ""
    vor_eol = (zust.get("vor_eol") or {}).get("result_voll") or ins
    hinw = (zust.get("vor_eol") or zust.get("nach_ins") or {}).get("cas_hinweise") or []
    p = {"pruefzeile_nie_im_brief": PRUEF not in txt and "(Lektor)" not in txt, "protokoll_da": lk is not None}
    lk = lk or {}
    if fall == "L0":
        p["kein_lektor"] = not lk.get("gestartet")
        p["brief_wie_ins"] = _gleich(ins, txt)
    elif fall == "L1":
        p["gestartet_und_fertig"] = lk.get("gestartet") and lk.get("fertig")
        p["korrektur_oder_pruefzeile"] = lk.get("uebernommen", 0) + lk.get("pruefzeilen", 0) >= 1
        p["pruefzeile_rot_im_fenster"] = lk.get("pruefzeilen", 0) == 0 or any(PRUEF in h for h in hinw)
        p["brief_wie_feld_nach_lektor"] = _gleich(vor_eol, txt)
    else:
        p["gestartet"] = bool(lk.get("gestartet"))
        p["bei_eol_nicht_fertig"] = bool(lk.get("nicht_fertig")) and not lk.get("fertig")
        p["brief_wie_ins"] = _gleich(ins, txt)
    return p


def main(argv):
    if "--e2e" not in argv:
        print(__doc__)
        return 2
    i = argv.index("--e2e")
    m = e2e_laden(argv[i + 1])
    rest = argv[:i] + argv[i + 2:]
    opt = {}
    for k in ("--log", "--diktat"):
        if k in rest:
            j = rest.index(k)
            opt[k] = rest[j + 1]
            rest = rest[:j] + rest[j + 2:]
    fall = rest[0] if rest else ""
    if fall not in ("L0", "L1", "LS"):
        print(f"LKABN=rot GRUND=fall_unbekannt ({fall})")
        return 2
    a = {rest[k]: rest[k + 1] for k in range(len(rest) - 1) if rest[k].startswith("--")}
    faelle_eintragen(m, opt.get("--diktat", "1"))
    _pf, ini = schalter_setzen(a.get("--arbeit", "."), a["--rakscribe"], an=fall != "L0")
    log_pfad = opt.get("--log")
    ab = os.path.getsize(log_pfad) if log_pfad and os.path.exists(log_pfad) else 0
    try:
        rc = m.main(["fall"] + rest)
    finally:
        schalter_zurueck(ini)
    r = m.json_lesen(os.path.join(os.path.abspath(a.get("--arbeit", ".")), fall, "ergebnis.json")) or {}
    txt = (r.get("ablage") or {}).get("txt") or ""
    print("\n--- abgelegter Text (<Nr>.rakscribe.txt, synthetisch) ---\n" + txt + "\n--- Ende ---")
    lk = log_lektor(log_pfad, ab)
    p = pruefen(fall, txt, r, lk)
    hat = bool(txt.strip())
    ok = hat and all(p.values())
    lk = lk or {}
    print(f"LKABN={'ok' if ok else 'rot'} FALL={fall} NR={a.get('--nr')} GESTARTET={'ja' if lk.get('gestartet') else 'nein'} "
          f"FERTIG={'ja' if lk.get('fertig') else 'nein'} UEBERNOMMEN={lk.get('uebernommen', 0)} "
          f"PRUEFZEILEN={lk.get('pruefzeilen', 0)} "
          f"PRUEFUNGEN={','.join(k + '=' + ('ja' if v else 'nein') for k, v in p.items())} "
          f"ABLAGE={'ja' if hat else 'nein'} SCHALTER_KOPIE=aus E2E_EXIT={rc}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
