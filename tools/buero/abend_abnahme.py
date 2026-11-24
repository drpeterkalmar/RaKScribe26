r"""Pflicht-Abnahme am Büro-PC, Testpatient 451898 (kaiscribe-schulter-ergebnis-n1-abnahme, 24.11.2026).

Deckt in EINER Runde ab: Georgs Punkte 48–70 (3.23.0, Fälle A–K), Ursula 3.25.0 (G1/H1/K1 wie ursula_abnahme.py) und
die Rho-Regel/HIPPO ≥ 10 mm (3.26.0, Fälle R1–R3, M13/M9). Weg wie rho_osteopen_abnahme.py / ursula_abnahme.py:
ris-mods e2e/diktat_e2e.py, KaiScribe-KOPIE als Gast mit echtem CAS-Auftrag, getipptes Diktat (text_ins), echte KI,
EOL → <Nr>.rakscribe.txt (Brieftext), JobFinished. Mit --formatierer <RaKScribe-Format.ps1> macht diktat_e2e zusätzlich
eine Formatierer-Kopie (Word-Brief als RTF) – daraus prüft dieses Skript den Fettdruck der Überschriften.

Aufruf (py -3.12, nur Standardbibliothek; alle weiteren Argumente gehen unverändert an diktat_e2e.py fall):
  py -3.12 abend_abnahme.py --e2e <...\e2e\diktat_e2e.py> <FALL> --nr <Nr> --arbeit <A> --rakscribe <Kopie\KaiScribe.exe>
         --bruecke <...> --schluessel <Schlüssel.json> [--formatierer <RaKScribe-Format.ps1>] [--wiederholung]
  py -3.12 abend_abnahme.py liste      → Fälle mit CAS-Kürzel-Vorschlag und Diktat
Schlusszeile: ABENDABN=<ok|rot> FALL=.. NR=.. PRUEFUNGEN=k=ja|nein,... ABLAGE=<ja|nein> FETT=<ja|nein|-> E2E_EXIT=..
Schreibt nichts außer über den normalen Brücken-Weg (diktat_e2e: Sicherung nur 451898, nie vidieren)."""
import importlib.util
import json
import os
import re
import sys

# Fall → (CAS-Kürzel-Vorschlag, [Diktat 1, Nachdiktat …], Nur Text an?)
FAELLE = {
    "A": ("schultr", ["Schulter rechts in zwei Ebenen. Omarthrose Kellgren Lawrence 2. Enthesiopathiezeichen Tuberculum "
                      "majus. AC-Gelenksarthrose."], False),
    "B": ("schultr", ["Schulter rechts in zwei Ebenen. Kalkdepot mit Enkapsulation am Ansatz der Supraspinatussehne. "
                      "Ergebnis Doppelpunkt Tendinosis calcarea der Supraspinatussehne."], False),
    "C": ("usschul", ["Sonographie der Schulter rechts. Geringgradige Bursitiszeichen perifokal im Bereich der "
                    "Supraspinatussehne."], False),
    "D": ("fussr", ["Fuß rechts in zwei Ebenen. Knöcherner Bandausriss am Malleolus lateralis, 9 mm Fragment."], False),
    "E": ("usweich", ["Sonographie der Weichteile Oberschenkel rechts:\nKein Hämatom, keine Raumforderung.\n"
                       "Ergebnis:\nUnauffälliger Weichteilbefund."], True),
    "F1": ("bü+hür", ["Beckenübersicht und Hüfte rechts in zwei Ebenen. Beginnende Coxarthrose rechts."], False),
    "F2": ("bü+hür", ["Beckenübersicht: unauffällig. Hüfte rechts in zwei Ebenen: beginnende Coxarthrose."], False),
    "G": ("kniel", ["Knie links unauffällig."], False),
    "H": ("bühü", ["Beckenübersicht und Hüften beidseits. Coxarthrose links hochgradig, rechts gering."], False),
    "I": ("vofur", ["Vorfuß rechts in zwei Ebenen. Geringe Arthrose im MTP-I-Gelenk."], False),
    "J": ("knier", ["Kniegelenk rechts in zwei Ebenen. Geringe mediale Gonarthrose. Retropatellararthrose.",
                    "wav:j2.wav"], False),     # Nachdiktat gesprochen: „Zweitens Chondrokalzinose.“
    "K": ("gws+flws", ["Ganzaufnahme der Wirbelsäule a.p. und seitlich. Flachbogige skoliotische Asymmetrie. "
                       "Altersentsprechende Degeneration.",
                       "wav:k2.wav"], False),   # Nachdiktat gesprochen: „Funktionsaufnahmen der Lendenwirbelsäule. Keine Instabilität.“
    "G1": ("Ganzbein re.", ["Ganzbeinaufnahme im Stand. Beinachse varisch, Gonarthrose medial Grad zwei. "
                            "Hüftgelenk altersentsprechend."], False),
    "H1": ("hws", ["Halswirbelsäule in zwei Ebenen. 50-prozentige Höhenminderung C5/6, Unkovertebralarthrose beidseits. "
                   "Im Übrigen unauffällige Wirbelkörper. Im Übrigen keine Fehlstellung."], False),
    "K1": ("knier", ["Kniegelenk in zwei Ebenen. Beginnende Gonarthrose. Kein Erguss."], False),
    "R1": ("handgell", ["Handgelenk links unauffällig. Rho 9."], False),
    "R2": ("lws", ["LWS: geringe Osteochondrose L5/S1. Rho 8."], False),
    "R3": ("lws", ["LWS: geringe Osteochondrose L5/S1. Rho 6."], False),
    "M13": ("bü", ["Beckenübersicht."], False),      # + HIPPO-Baustein 13 mm / BLD 20 mm (ibl_abnahme_bausteine --hippo-becken)
    "M9": ("bü", ["Beckenübersicht."], False),       # + HIPPO-Baustein 9 mm (Fall 61)
}
OSTEOPEN = "osteopenischer knochenaspekt"
RHO_TEIL = "opportunistisches knochendichtescreening"
MINERAL = re.compile(r"(?:mineralgehalt|knochenmineralisation|kalksalzgehalt|mineralisation)[^.]{0,80}?"
                     r"(?:regelrecht|unauffällig|normal|altersentsprechend)", re.I)


def e2e_laden(pfad):
    sys.path.insert(0, os.path.dirname(os.path.abspath(pfad)))
    spec = importlib.util.spec_from_file_location("diktat_e2e", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def faelle_eintragen(m):
    for name, (_, texte, nur_text) in FAELLE.items():
        schritte = [{"trigger": "nur_text_an"}] if nur_text else []
        for i, text in enumerate(texte):
            merk = {"merke": "nach_ins" if i == len(texte) - 1 else f"nach_ins{i}"}
            if text.startswith("wav:"):   # echtes Nachdiktat: kein Cursor-Ziel, Aufnahme, gesprochene Datei, INS
                schritte += [{"trigger": "befund_fokus_weg"}, {"taste": "RECORD"}, {"sprich": text[4:]}, {"taste": "INS"},
                             {"warte_auf": "kontrolle", "timeout_s": 300}, {"warte_s": 3}, merk]
            else:
                schritte += [{"trigger": f"text_ins#{name.lower()}{i}|{text}"},
                             {"warte_auf": "kontrolle", "timeout_s": 300}, {"warte_s": 3}, merk]
        m.FAELLE[name] = {"titel": f"Abend-Abnahme {name}: getipptes Diktat → Befund → EOL → Ablage (Brieftext)",
                          "eol": True, "abschnitte": 1, "ablauf": m._START + schritte + m._EOL}


# ── Text-Hilfen (nur Struktur) ──
def teile(txt):
    """(Befundtext, Ergebnistext) – Ergebnis = alles nach der letzten Zeile „Ergebnis“."""
    m = list(re.finditer(r"(?mi)^(?:#+\s*)?Ergebnis\s*:?[ \t]*$", txt))
    if not m:
        m2 = list(re.finditer(r"(?mi)^(?:#+\s*)?Ergebnis\s*:", txt))
        if not m2:
            return txt, ""
        return txt[:m2[-1].start()], txt[m2[-1].start():]
    return txt[:m[-1].start()], txt[m[-1].end():]


def punkte(erg):
    return [z.strip() for z in erg.splitlines() if re.match(r"\s*\d+\.\s", z)]


def pos(txt, *muster):
    low = txt.lower()
    for mu in muster:
        i = low.find(mu.lower())
        if i >= 0:
            return i
    return -1


def ueberschriften(txt):
    return [z for z in txt.splitlines() if z.startswith("#")]


def titel(txt):
    """Untersuchungstitel = Überschriften außer Befund/Ergebnis/Beurteilung/Anmerkung."""
    return [t for t in ueberschriften(txt)
            if not re.match(r"#+\s*(Befund|Ergebnis|Beurteilung|Anmerkung|Fragestellung|Klinik)\b", t, re.I)]


def pruefen(fall, txt):
    low = txt.lower()
    bef, erg = teile(txt)
    bl, el = bef.lower(), erg.lower()
    p = {"keine_leere_ueberschrift": not re.search(r"(?m)^#+\s*$", txt),
         "im_uebrigen_nie_doppelt": not re.search(r"(?i)im übrigen[^.\n]*\.\s*im übrigen", txt)}
    if fall == "A":
        i_ac = pos(bef, "akromioklavikular", "ac-gelenk")
        i_ans = pos(bef, "ansonsten die gelenkflächen")
        i_ent = pos(bef, "kortikale unregelmäßigkeiten und vermehrte sklerosierung am tuberculum majus")
        p["befund_ac_vor_ansonsten"] = 0 <= i_ac < i_ans
        p["befund_ansonsten_vor_enthesiopathie"] = 0 <= i_ans < i_ent
        p["befund_satz_kortikal_tuberculum"] = i_ent >= 0
        e_om, e_ac, e_en = pos(erg, "omarthrose"), pos(erg, "akromioklavikular", "ac-gelenk"), pos(erg, "enthesiopath")
        p["ergebnis_reihe_omarthrose_ac_enthesiopathie"] = 0 <= e_om < e_ac < e_en
        p["ergebnis_omarthrose_grad_2"] = bool(re.search(r"omarthrose[^\n]{0,80}grad\s*2|grad\s*2\)?[^\n]{0,20}omarthrose", el))
    elif fall == "B":
        p["enkapsulation"] = "enkapsulation" in low
        p["keine_einkapselung"] = "einkapselung" not in low
        p["ergebnis_abschnitt"] = bool(re.search(r"(?mi)^(?:#+\s*)?Ergebnis\s*:?\s*$", txt))
        p["kein_wort_doppelpunkt"] = "doppelpunkt" not in low
        p["ergebnis_tendinosis"] = "tendinosis calcarea" in el or "kalk" in el
    elif fall == "C":
        p["bursitis_satz"] = "bursitis" in bl
        normal = [s for s in re.split(r"(?<=\.)\s+", bef) if "bursa" in s.lower()
                  and re.search(r"(?i)\bkein|unauffällig|regelrecht|nicht verdickt|ohne", s)]
        p["bursa_normalsatz_weg"] = not normal
    elif fall == "D":
        i_f = pos(bef, "bandausriss", "ausriss")
        i_u = pos(bef, "im übrigen glatte")
        p["fraktur_satz"] = i_f >= 0
        p["im_uebrigen_glatte_danach"] = 0 <= i_f < i_u
        letzter = [a for a in re.split(r"\n\s*\n", bef.strip()) if a.strip()][-1:] or [""]
        p["kein_eigener_absatz_am_ende"] = not re.match(r"(?i)\s*knöcherne[rn]? bandausriss", letzter[0])
        p["keine_warnung_kein_eigener_befund"] = "kein eigener befund" not in low
    elif fall == "E":
        p["titel_da"] = bool(titel(txt)) or bool(re.search(r"(?mi)^sonographie", txt))
        p["ergebnis_abschnitt"] = bool(re.search(r"(?mi)^(?:#+\s*)?Ergebnis\s*:?", txt))
        p["kein_wort_doppelpunkt"] = "doppelpunkt" not in low
    elif fall == "F1":
        t = titel(txt)
        p["ein_kombititel"] = len(t) == 1 and "becken" in t[0].lower() and "hüft" in t[0].lower()
    elif fall == "F2":
        p["zwei_teile"] = len(titel(txt)) == 2
    elif fall == "G":
        p["kein_koala"] = "koala" not in low
        p["kein_kl_grad"] = not re.search(r"kellgren|grad\s*\d", low)
    elif fall == "H":
        p["coxarthrose_li_grad_4"] = bool(re.search(r"(grad\s*4[^\n]{0,60}links|links[^\n]{0,60}grad\s*4)", el))
        p["coxarthrose_re_grad_2"] = bool(re.search(r"(grad\s*2[^\n]{0,60}rechts|rechts[^\n]{0,60}grad\s*2)", el))
    elif fall == "I":
        p["mtp_grad_2"] = bool(re.search(r"grad\s*(2|ii)\b", el)) and not re.search(r"grad\s*(1|3|4|i|iii|iv)\b", el)
    elif fall == "J":
        pu = punkte(erg)
        p["punkt2_chondrokalzinose"] = len(pu) >= 2 and "chondrokalz" in pu[1].lower()
        p["mind_3_punkte"] = len(pu) >= 3
    elif fall == "K":
        t = titel(txt)
        p["vier_teile"] = len(t) == 4
        p["funktion_teil"] = any("funktion" in x.lower() for x in t)
        p["skoliotisch_bleibt"] = "skoliot" in low
    elif fall == "G1":
        p["titel_ganzbein_rechts"] = "ganzbeinaufnahme im stand rechts" in low
        p["keine_leerzeile_nach_ergebnis"] = not re.search(r"(?mi)^(?:#+\s*)?Ergebnis:?[ \t]*\n[ \t]*\n", txt)
    elif fall == "H1":
        p["prozent_ige"] = "50%ige" in txt or "50 %ige" in txt
        p["kein_prozentig_wort"] = "prozentig" not in low
        p["titel_ohne_beidseits"] = not any("beidseits" in t.lower() for t in ueberschriften(txt))
        p["keine_leerzeile_nach_ergebnis"] = not re.search(r"(?mi)^(?:#+\s*)?Ergebnis:?[ \t]*\n[ \t]*\n", txt)
    elif fall == "K1":
        p["titel_knie"] = any("knie" in t.lower() for t in ueberschriften(txt))
    elif fall == "R1":
        p["kein_rho_teil"] = RHO_TEIL not in low
        p["kein_osteopen"] = OSTEOPEN not in low
    elif fall == "R2":
        p["rho_teil"] = RHO_TEIL in low
        p["osteopen"] = OSTEOPEN in low
    elif fall == "R3":
        p["kein_rho_teil"] = RHO_TEIL not in low
        p["kein_osteopen"] = OSTEOPEN not in low
        p["mineral_normalsatz"] = bool(MINERAL.search(txt))
    elif fall == "M13":
        pu = punkte(erg)
        p["punkt_beckenschiefstand_13"] = any("beckenschiefstand von 13 mm" in x.lower() for x in pu) \
            or "beckenschiefstand von 13 mm" in el
        p["punkt_bld_20"] = "beinlängendifferenz von 20 mm" in el
        p["kein_regelrecht_becken"] = "regelrechte darstellung des beckens" not in el
        p["anmerkung_da"] = "weitere winkelmessungen" in el
    elif fall == "M9":
        p["beschreibung_9mm"] = "9 mm" in bl
        p["kein_ergebnispunkt_9mm"] = "beckenschiefstand" not in el
    return p


# ── RTF (Word-Brief der Formatierer-Kopie): Fettdruck der Überschriften ──
def rtf_laeufe(rtf):
    """[(text, fett)] – kleiner RTF-Leser: Gruppen, \\b/\\b0, \\par, \\uN?, \\'xx; versteckter Text (\\v) zählt nicht."""
    out, stapel, fett, versteckt, i, n = [], [], False, False, 0, len(rtf)
    skip_ziel = 0
    while i < n:
        c = rtf[i]
        if c == "{":
            stapel.append((fett, versteckt, skip_ziel))
            i += 1
            if rtf.startswith("\\*", i):
                skip_ziel = len(stapel)
        elif c == "}":
            fett, versteckt, skip_ziel = stapel.pop() if stapel else (False, False, 0)
            i += 1
        elif c == "\\":
            m = re.match(r"\\([a-zA-Z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\(.)", rtf[i:])
            if not m:
                i += 1
                continue
            i += m.end()
            wort, zahl, hexz, sym = m.group(1), m.group(2), m.group(3), m.group(4)
            aktiv = not skip_ziel and not versteckt
            if wort in ("fonttbl", "colortbl", "stylesheet", "info"):
                skip_ziel = len(stapel)
            elif wort == "b":
                fett = zahl != "0"
            elif wort == "plain":
                fett, versteckt = False, False
            elif wort == "v":
                versteckt = zahl != "0"
            elif wort in ("par", "line") and aktiv:
                out.append(("\n", fett))
            elif wort == "u" and aktiv:
                out.append((chr(int(zahl) % 65536), fett))
                if i < n and rtf[i] == "?":
                    i += 1
            elif hexz and aktiv:
                out.append((bytes([int(hexz, 16)]).decode("cp1252", "replace"), fett))
            elif sym and sym in "\\{}" and aktiv:
                out.append((sym, fett))
        elif c in "\r\n":
            i += 1
        else:
            if not skip_ziel and not versteckt:
                out.append((c, fett))
            i += 1
    return out


def fett_zeilen(rtf):
    """{Zeile: ganz fett?} je Absatz des Briefs."""
    zeilen, akt = {}, []
    for ch, f in rtf_laeufe(rtf) + [("\n", False)]:
        if ch == "\n":
            t = "".join(c for c, _ in akt).strip()
            if t:
                zeilen[t] = all(ff for c, ff in akt if c.strip())
            akt = []
        else:
            akt.append((ch, f))
    return zeilen


def fett_pruefen(fall, arbeit, txt):
    """Fettdruck im Word-Brief: Ergebnis-Zeile und Untersuchungstitel fett (nur wenn eine Formatierer-Kopie da ist)."""
    for name in ("kopie-formatiert.rtf",):
        p = os.path.join(arbeit, fall, "format", name)
        if os.path.exists(p):
            break
    else:
        return None, {}
    with open(p, encoding="latin-1") as f:
        z = fett_zeilen(f.read())
    erwartet = [re.sub(r"^#+\s*", "", t).strip() for t in titel(txt)]
    erwartet += [k for k in z if re.match(r"(?i)^Ergebnis\s*:?$", k)]
    befund = {}
    for e in erwartet:
        treffer = [k for k in z if k.rstrip(":").strip().lower() == e.rstrip(":").strip().lower()]
        befund[e[:60]] = bool(treffer) and all(z[k] for k in treffer)
    return (all(befund.values()) if befund else None), befund


def liste():
    for k, (kurz, texte, nt) in FAELLE.items():
        print(f"{k:<4} CAS={kurz:<14} {'NurText ' if nt else ''}" + " || ".join(texte))
    return 0


def main(argv):
    if argv[:1] == ["liste"]:
        return liste()
    if "--e2e" not in argv:
        print(__doc__)
        return 2
    i = argv.index("--e2e")
    m = e2e_laden(argv[i + 1])
    rest = argv[:i] + argv[i + 2:]
    fall = rest[0] if rest else ""
    if fall not in FAELLE:
        print(f"ABENDABN=rot GRUND=fall_unbekannt ({fall})")
        return 2
    faelle_eintragen(m)
    rc = m.main(["fall"] + rest)
    a = {rest[k]: rest[k + 1] for k in range(len(rest) - 1) if rest[k].startswith("--")}
    arbeit = os.path.abspath(a.get("--arbeit", "."))
    r = m.json_lesen(os.path.join(arbeit, fall, "ergebnis.json")) or {}
    txt = (r.get("ablage") or {}).get("txt") or ""
    print("\n--- abgelegter Text (<Nr>.rakscribe.txt, synthetisch) ---\n" + txt + "\n--- Ende ---")
    p = pruefen(fall, txt)
    fett, fb = fett_pruefen(fall, arbeit, txt)
    print("Titel/Überschriften:", " | ".join(ueberschriften(txt)))
    print("Fettdruck Word-Brief:", json.dumps(fb, ensure_ascii=False) if fb else "keine Formatierer-Kopie")
    hat = bool(txt.strip())
    ok = hat and all(p.values()) and fett is not False
    print(f"ABENDABN={'ok' if ok else 'rot'} FALL={fall} NR={a.get('--nr')} "
          f"PRUEFUNGEN={','.join(k + '=' + ('ja' if v else 'nein') for k, v in p.items())} "
          f"ABLAGE={'ja' if hat else 'nein'} FETT={'-' if fett is None else ('ja' if fett else 'nein')} E2E_EXIT={rc}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
