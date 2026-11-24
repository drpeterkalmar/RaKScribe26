"""Gate kaiscribe-rho-titel-nummer-n1 – Punkt 47 (Georg 22.11.2026, Foto RH 49 vom 20.11.: „Die Überschrift bei opp gross
machen und mit Punkt 1. Starten“). RH 49 lief mit 3.19.15 (Rho damals noch IM Hüft-Teil: „2. Opportunistisches …“).
Seit 3.20.0 ist Rho ein eigener Schlussbefund; dieser Test hält die ganze EXE-Kette für genau Georgs Kombination fest
(Beckenübersicht + Hüfte rechts, IB Lab HIPPO mit Text, „Rho 8“ diktiert), einzeln und als Mehrfach:
  a) eigene Überschriftzeile „## Opportunistisches Knochendichtescreening (KI)“ ganz am Schluss (eigene ## -Zeile → der
     Formatierer setzt sie fett+unterstrichen wie jede Untersuchung; live belegt 23.11. 1123-059/073)
  b) Rho-Ergebnis = EIN Punkt ohne Nummer (Regel v3.18.3: ein Ergebnispunkt wird nie nummeriert), nie „2.“
  c) Haupt-Ergebnis mit 2 Punkten → „1.“, „2.“; HIPPO-Schlussanmerkung als „Anmerkung: …“ ohne Nummer, zählt nicht mit
  d) nirgends „Amerkung“ (RH 49: von Hand getippt, kommt in keinem Code vor)
Keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_rho_titel_nummer.py"""
import copy, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402,F401

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import cas_vorlagen as cv  # noqa: E402
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

HIER = pathlib.Path(__file__).resolve().parent
T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
HIPPO = json.loads((HIER / "hippo_bausteine.json").read_text(encoding="utf-8"))
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def L(kurz, text, vorlage, seite, ziffer=1):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": "Röntgen", "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True, "ziffer": ziffer}


def kontext(llm, leistungen=None, bausteine=None):
    cas = cv.CasHinweis(leistungen, T) if leistungen else None
    ibl = I.IblKontext(I.aus_liste(bausteine), cas_leistungen=leistungen) if bausteine else None
    return pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=llm, log=lambda *a: None, cas=cas, ibl=ibl)


def bloecke(report):
    """[(Titel, [Ergebnis-Zeilen ohne Leerzeilen])] je Einzelbefund."""
    aus = []
    for teil in re.split(r"\n(?=## (?!Befund\b|Ergebnis\b))", report.strip()):
        kopf = teil.split("\n", 1)[0]
        if not kopf.startswith("## "):
            continue
        erg = teil.split("## Ergebnis\n", 1)[1] if "## Ergebnis\n" in teil else ""
        aus.append((kopf[3:].strip(), [z for z in erg.split("\n") if z.strip()]))
    return aus


def pruefen(name, report):
    b = bloecke(report)
    titel = [t for t, _ in b]
    check(f"{name} a): Rho eigene Überschriftzeile ganz am Schluss, genau einmal",
          titel[-1:] == [br.RHO_TITEL] and titel.count(br.RHO_TITEL) == 1
          and f"\n## {br.RHO_TITEL}\n" in "\n" + report, report)
    rho_erg = b[-1][1] if b else []
    check(f"{name} b): Rho-Ergebnis = ein Punkt ohne Nummer (nie „2.“)", rho_erg == [br.RHO_ERGEBNIS], rho_erg)
    for t, erg in b[:-1]:
        zaehl = [z for z in erg if not br._UNNUM_RE.match(br._NUM_RE.sub("", z))]
        nummern = [re.match(r"^(\d+)\. ", z).group(1) if re.match(r"^\d+\. ", z) else None for z in zaehl]
        soll = [str(k + 1) for k in range(len(zaehl))] if len(zaehl) >= 2 else [None] * len(zaehl)
        check(f"{name} c): „{t}“ – {len(zaehl)} Punkt(e) {'1., 2., …' if len(zaehl) >= 2 else 'ohne Nummer'}, "
              "Anmerkung ohne Nummer", nummern == soll
              and all(not re.match(r"^\d", z) for z in erg if br._UNNUM_RE.match(br._NUM_RE.sub("", z))), erg)
    check(f"{name} d): kein „Amerkung“; Schlussanmerkung als „Anmerkung: “",
          "amerkung" not in report.lower() and ("Anmerkung: " in report) == any(
              z.startswith("Anmerkung:") for _, e in b for z in e), report)


# HIPPO mit fertigem Text (Abholer ≥ 1.3.11), nur rechts – wie RH 49 (Hüfte rechts)
hb = copy.deepcopy(next(f["baustein"] for f in HIPPO if f["baustein"].get("befundtext")
                        and f["baustein"]["befundtext"].get("schluss") and f["baustein"]["befundtext"].get("ergebnis")))
hb["ziffer"] = 1
ZWEI = "1. Mäßige Coxarthrose rechts.\n2. Geringe Osteochondrose L5/S1 miterfasst."


def ki_einzeln(p):
    v = T["beckenübersicht_und_hüfte"]
    return (f"## Beckenübersicht und Hüftgelenk rechts in 2 Ebenen\n\n## Befund\n{v['body'].split(chr(10), 2)[2]}\n\n"
            f"## Ergebnis\n{ZWEI}")


BH = L("bhr", "Beckenübersicht + Hüfte re.", "beckenübersicht_und_hüfte", "rechts")
erg = pl.befund_aus_diktat("Beckenübersicht und Hüfte rechts: mäßige Coxarthrose rechts, geringe Osteochondrose L5/S1 "
                           "miterfasst. Rho 8.", kontext(ki_einzeln, [BH], [hb]))
# kaiscribe-rho-regel-becken-n1 (Kanban #533, EINE Rho-Regel): Becken/Hüfte ohne LWS → kein Rho-Teil, Hinweis
check("Einzel Becken+Hüfte re + HIPPO + Rho 8: kein Rho-Teil (Rho-Regel: nur LWS), Hinweis in der Anzeige",
      br.RHO_TITEL not in erg.report and "(Rho)" not in erg.report
      and any("Rho: kein Rho-Text – Rho-Region nicht LWS" in h for h in erg.cas_hinweise), (erg.report, erg.cas_hinweise))
LW = L("lws", "LWS", "lendenwirbelsäule_in_2_ebenen", None)


def ki_lws(p):
    v = T["lendenwirbelsäule_in_2_ebenen"]
    return f"## Lendenwirbelsäule in 2 Ebenen\n\n## Befund\n{v['body'].split(chr(10), 2)[2]}\n\n## Ergebnis\n{ZWEI}"


erg = pl.befund_aus_diktat("LWS: mäßige Coxarthrose rechts, geringe Osteochondrose L5/S1. Rho 8.", kontext(ki_lws, [LW]))
pruefen("Einzel LWS + Rho 8", erg.report)
check("Einzel LWS: Rho-Text mit Score 8 im Rho-Befund, nicht im LWS-Teil",
      "Der Score von 8 (Skala 1–10)" in erg.report.split(f"## {br.RHO_TITEL}")[1]
      and "(Rho)" not in erg.report.split(f"## {br.RHO_TITEL}")[0], erg.report)

BUE = L("bü", "Beckenübersicht", "beckenübersicht_stehend", None, ziffer=1)
HR = L("hr", "Hüfte re.", "hüftgelenk_in_2_ebenen", "rechts", ziffer=2)
hb2 = dict(copy.deepcopy(hb), ziffer=2)


LW2 = L("lws", "LWS", "lendenwirbelsäule_in_2_ebenen", None, ziffer=2)


def ki_mehrfach(p):
    if "<untersuchung>Lendenwirbel" in p:
        return ki_lws(p)
    if "<untersuchung>Beckenübersicht" in p:
        v = T["beckenübersicht_stehend"]
        return f"## Beckenübersicht stehend\n\n## Befund\n{v['body'].split(chr(10), 2)[2]}\n\n## Ergebnis\n{v['ergebnis']}"
    v = T["hüftgelenk_in_2_ebenen"]
    return f"## Hüftgelenk rechts in 2 Ebenen\n\n## Befund\n{v['body'].split(chr(10), 2)[2]}\n\n## Ergebnis\n{ZWEI}"


erg = pl.befund_aus_diktat("Hüfte rechts: mäßige Coxarthrose rechts. LWS: geringe Osteochondrose L5/S1, Rho 8.",
                           kontext(ki_mehrfach, [HR, LW2], [dict(copy.deepcopy(hb), ziffer=1)]))
pruefen("Mehrfach Hüfte re + HIPPO + LWS + Rho 8", erg.report)
check("Mehrfach: 3 Einzelbefunde (Hüfte, LWS, Rho)", len(bloecke(erg.report)) == 3, erg.report)
erg = pl.befund_aus_diktat("Beckenübersicht: unauffällig. Hüfte rechts: mäßige Coxarthrose rechts, geringe Osteochondrose "
                           "L5/S1 miterfasst, Rho 8.", kontext(ki_mehrfach, [BUE, HR], [hb2]))
check("Mehrfach Becken + Hüfte (ohne LWS) + Rho 8: 2 Einzelbefunde, kein Rho-Teil (Rho-Regel)",
      len(bloecke(erg.report)) == 2 and br.RHO_TITEL not in erg.report, erg.report)

# Rho als einziger Punkt seines Befunds bleibt auch nach erneutem Nummerieren ohne Nummer
r = br.rho_einfuegen("## Hüftgelenk rechts in 2 Ebenen\n\n## Befund\nText.\n\n## Ergebnis\n1. A.\n2. B.", "8")
check("Nachbearbeiten zweimal: Rho-Punkt bleibt ohne Nummer, Haupt-Ergebnis 1., 2.",
      br.nachbearbeiten(br.nachbearbeiten(r)).rstrip().endswith("## Ergebnis\n" + br.RHO_ERGEBNIS)
      and "1. A.\n2. B." in br.nachbearbeiten(r), br.nachbearbeiten(r))

print(f"\n{'❌ ' + str(fails) + ' Fehler' if fails else '✅ alle grün'}")
sys.exit(1 if fails else 0)
