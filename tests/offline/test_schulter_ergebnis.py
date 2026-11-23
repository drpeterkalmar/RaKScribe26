"""Gate kaiscribe-schulter-ergebnis-n1 – Georg Riegler 22./23.11.2026, Punkte 48–70 (EXE-Kette).
Die Textregeln (EXE = Web) prüft befund_regeln_test.py (Fixtures „georg_2311“) und test_befundfeld.py (Punkt 62); hier
die ganze EXE-Kette mit KI-Attrappe, CAS-Leistungen und IB-Lab-Bausteinen:
  61   KOALA-Knie-Automatik aus (Kanban #514): KOALA-Baustein vorhanden, Diktat ohne Grad → kein KOALA-Text, kein Grad
  59   Kombibefund per DIKTAT (Becken + Hüfte in einem Titel → 1 Teil; getrennt → 2; nur CAS bü + Hüft-OP → 2; mit TEP →
       Prothesen-Kombi „… nach Hüft-TEP“)
  55a  seitenlose Hüft-OP-Leistung ohne Seite im Diktat → rote Prüfzeile (nie raten)
  60   RH 30-Muster: Diktat unter die Becken-Normalvorlage gehängt → Normalsätze der betroffenen Seite raus, Prüfzeile
       „Befund nicht geformt“ statt stiller „Regelrechte Darstellung“; HIPPO 12 mm → Ergebnispunkt
  63/67 Gerüst bleibt: RH-120-Muster (Ganzbein mit LAMA nicht diktiert → Gerüst-Teil wörtlich), RH-130-Muster (GWS-Teile
       bleiben, „Funktionsaufnahmen der LWS“ zusätzlich, SQUIRREL nicht im Funktions-Teil), Diff-Wächter (LAMA-Satz zurück)
  62   Cursor im Ergebnis + „zweitens …“ → neuer Punkt 2 (Cursor im Befund → normales Einfügen)
  49a/52 Nur Text: Überschriften als „## …“
Keine Patientendaten (Diktate nachgebaut).  Aufruf: /usr/bin/python3 tests/offline/test_schulter_ergebnis.py"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402,F401

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import befundfeld as bf  # noqa: E402
import cas_vorlagen as cv  # noqa: E402
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
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
    ibl = I.IblKontext(I.aus_liste(bausteine), cas_leistungen=leistungen) if bausteine is not None else None
    return pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=llm, log=lambda *a: None, cas=cas, ibl=ibl)


def titel_aus(p):
    return p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0] if "<untersuchung>" in p else "Befund"


def ki_vorlage(prompts, ergebnis=None):
    """KI-Attrappe: gibt die Normalvorlage der angefragten Untersuchung zurück (wie ein „stiller“ Lauf)."""
    def llm(p):
        prompts.append(p)
        titel = titel_aus(p)
        key = next((k for k, v in T.items() if v.get("display_name") == titel), None)
        body = T[key]["body"].split("\n", 2)[2] if key else "Text."
        erg = ergebnis if ergebnis is not None else (T[key]["ergebnis"] if key else "Unauffällig.")
        return f"## {titel}\n\n## Befund\n{body}\n\n## Ergebnis\n{erg}"
    return llm


def teile(report):
    return report.count("## Befund")


# ───────────────────────────── 61: KOALA-Knie-Automatik aus ─────────────────────────────
KOALA = {"accno": "T-0061", "ziffer": 1, "modul": "koala", "name": "KOALA", "modul_name": "IB Lab KOALA", "version": 1,
         "seiten": ["links"], "befundteil": ["Kellgren-Lawrence-Grad links 3 (IB Lab KOALA)."],
         "ergebnis": ["Mittelgradige Gonarthrose links (Kellgren-Lawrence-Grad 3)."], "hinweise": ["KOALA: KL 3"],
         "nicht_zugeordnet": []}
check("61: Schalter KOALA_KNIE_AUTOMATIK steht AUS (Kanban #514 erledigt, Peter 23.11.2026)", I.KOALA_KNIE_AUTOMATIK is False)
check("61: aus_liste lässt den KOALA-Baustein weg (kein Text, keine Hinweiszeile, kein Prompt-Block)", I.aus_liste([KOALA]) == [])
ps = []
KNIE_L = L("kn", "Knie li.", "kniegelenk_in_2_ebenen", "links")
erg = pl.befund_aus_diktat("Knie links in zwei Ebenen. Kein Erguss.", kontext(ki_vorlage(ps), [KNIE_L], [KOALA]))
check("61: KOALA-Baustein vorhanden, Diktat ohne Grad → kein KOALA-Text, kein K&L-Grad, kein KOALA im Prompt",
      "Kellgren" not in erg.report and "KOALA" not in erg.report and "Gonarthrose" not in erg.report
      and not any("<ibl_messwerte>" in p or "IB Lab KOALA" in p for p in ps), erg.report)
ps = []
erg = pl.befund_aus_diktat("Knie links: mäßige Gonarthrose.", kontext(
    lambda p: (ps.append(p), f"## {titel_aus(p)}\n\n## Befund\nNormale Form und Stellung.\n\n## Ergebnis\nMäßige Gonarthrose links.")[1],
    [KNIE_L], [KOALA]))
check("61: diktiertes Adjektiv „mäßige Gonarthrose“ → K&L-Satz Grad 3 wie Register (gilt weiter)",
      "(Arthrose Grad 3 nach Kellgren & Lawrence)" in erg.report and br.KL_TABELLE[3][:-1].lower() in erg.report.lower()
      and "IB Lab" not in erg.report, erg.report)

# ───────────────────────────── 59: Kombibefund per Diktat ─────────────────────────────
BUE = L("bü", "Beckenübersicht", "beckenübersicht_stehend", "", 1)
HUE_R = L("hü", "Hüfte re.", "hüftgelenk_in_2_ebenen", "rechts", 2)
HUEOP = L("hüop", "Hüft-OP", "hüftgelenk_in_2_ebenen", "", 2)
ps = []
erg = pl.befund_aus_diktat("Beckenübersicht und Hüfte rechts. Geringe Coxarthrose rechts. Unauffällige Weichteile.",
                           kontext(ki_vorlage(ps), [BUE, HUE_R]))
check("59: Diktat „Beckenübersicht und Hüfte rechts …“ → EIN Kombibefund (ein KI-Aufruf, ein Teil)",
      len(ps) == 1 and teile(erg.report) == 1 and "Hüft" in erg.report.split("\n")[0], f"{len(ps)} Aufrufe\n{erg.report}")
ps = []
erg = pl.befund_aus_diktat("Beckenübersicht: unauffällig. Hüftgelenk rechts: geringe Coxarthrose rechts.",
                           kontext(ki_vorlage(ps), [BUE, HUE_R]))
check("59: getrennt diktiert (eigener Abschnitt je Untersuchung) → zwei Teile", teile(erg.report) == 2, erg.report)
ps = []
erg = pl.befund_aus_diktat("Becken unauffällig. Hüfte rechts nach TEP regelrecht.", kontext(ki_vorlage(ps), [BUE, HUEOP]))
check("59: nur CAS bü + Hüft-OP ohne Kombi-Signal im Diktat → zwei Teile", teile(erg.report) == 2, erg.report)
ps = []
erg = pl.befund_aus_diktat("Beckenübersicht und Hüftgelenk rechts nach Hüft-TEP. Kein Lockerungszeichen.",
                           kontext(ki_vorlage(ps), [BUE, HUEOP]))
check("59: Kombi mit TEP → Prothesen-Kombi, Titel „Becken sowie Hüftgelenk in 2 Ebenen rechts nach Hüft-TEP“",
      teile(erg.report) == 1 and erg.report.startswith("## Becken sowie Hüftgelenk in 2 Ebenen rechts nach Hüft-TEP")
      and erg.vorlagen == [pl.KOMBI_PROTHESE], f"{erg.vorlagen}\n{erg.report}")

# ───────────────────────────── 55a: Seite der seitenlosen Hüft-OP ─────────────────────────────
erg = pl.befund_aus_diktat("Hüfte nach Operation regelrecht.", kontext(ki_vorlage([]), [HUEOP]))
check("55a: Hüft-OP ohne Seite (Leistung + Diktat) → rote Prüfzeile, nichts geraten",
      pl.SEITE_FEHLT.format(name=cv.CasHinweis([HUEOP], T).alle[0].label) in erg.cas_hinweise, erg.cas_hinweise)
erg = pl.befund_aus_diktat("Hüfte links nach Operation regelrecht.", kontext(ki_vorlage([]), [HUEOP]))
check("55a: Seite diktiert → keine Prüfzeile", not any("Seite weder" in h for h in erg.cas_hinweise), erg.cas_hinweise)

# ───────────────────────────── 60/60b: RH-30-Muster ─────────────────────────────
STILL = ("## Beckenübersicht stehend\n\n## Befund\nBeckenschiefstand von 12 mm, links tieferstehend. Beinlängendifferenz von "
         "9 mm, rechts kürzer. Mineralgehalt und Knochenstruktur sind regelrecht. Regelrechte Abbildung beider Pfannendächer. "
         "Ordnungsgemäße Stellung der normal geformten Hüftköpfe. Normal konfigurierte, glatte Gelenkflächen mit allseits "
         "normal weitem Gelenkspalt. Keine intra- oder periartikulären Verkalkungen. Unauffällige Weichteile. Status post "
         "Hüft-TEP rechts, kein sicheres Lockerungszeichen. Unveränderte mäßiggradige Coxarthrose links.\n\n## Ergebnis\n"
         "Regelrechte Darstellung des Beckens.")
erg = pl.befund_aus_diktat("Becken: Vergleich zur Voruntersuchung Befundänderung. Status post Hüft-TEP rechts, kein sicheres "
                           "Lockerungszeichen. Unveränderte mäßiggradige Coxarthrose links.",
                           kontext(lambda p: STILL, [BUE]))
check("60: Diktat unter der Normalvorlage → Hüftkopf-/Gelenkspalt-Normalsätze der betroffenen Seiten raus",
      "normal geformten Hüftköpfe" not in erg.report and "allseits normal weitem Gelenkspalt" not in erg.report, erg.report)
check("60b: HIPPO 12 mm → „Beckenschiefstand von 12 mm, links tiefer.“ im Ergebnis, nie „Regelrechte Darstellung“",
      "Beckenschiefstand von 12 mm, links tiefer." in br.ergebnis_nummerieren(erg.report).split("## Ergebnis")[1]
      and "Regelrechte Darstellung des Beckens" not in erg.report, erg.report)
UNGEFORMT = ("## Beckenübersicht stehend\n\n## Befund\nMineralgehalt und Knochenstruktur sind regelrecht. Status post "
             "Hüft-TEP rechts, kein sicheres Lockerungszeichen.\n\n## Ergebnis\nRegelrechte Darstellung des Beckens.")
check("60: Ergebnis „Regelrechte Darstellung“ trotz Pathologie → rote Prüfzeile „Befund nicht geformt“; leeres Ergebnis → Prüfzeile",
      any("Befund nicht geformt" in h for h in br.pruefzeilen_2311(UNGEFORMT, "", T))
      and any("Ergebnis leer" in h for h in br.pruefzeilen_2311(UNGEFORMT.split("Regelrechte Darstellung")[0], "", T)),
      br.pruefzeilen_2311(UNGEFORMT, "", T))
check("60: EXE-Kette hängt die Prüfzeilen an (pipeline._pruefen)", "br.pruefzeilen_2311(erg.report, erg.raw, ctx.templates)"
      in (ROOT / "source_code" / "pipeline.py").read_text(encoding="utf-8"))
erg = pl.befund_aus_diktat("Becken unauffällig.", kontext(ki_vorlage([]), [BUE]))
check("60: Gegenprobe Normalbefund → keine Prüfzeile", not any("nicht geformt" in h or "leer" in h for h in erg.cas_hinweise),
      erg.cas_hinweise)

# ───────────────────────────── 63/67: Gerüst bleibt ─────────────────────────────
LAMA = ("Traglinie des Ganzbeines (Mikulicz-Linie) links: HKA = 178,5°, mechanische Achsabweichung 4 mm medial. Gemessene "
        "Beinlänge links 812 mm.")
G120 = ("## Kniegelenk links in 2 Ebenen\n\n## Befund\nNormale Form und Stellung.\n\n## Ergebnis\nRegelrechte Darstellung des "
        "Kniegelenkes.\n\n\n## Ganzbeinaufnahme im Stand\n\n## Befund\n" + LAMA + " Lange Röhrenknochen: Normal geformt.\n\n"
        "## Ergebnis\nRegelrechte Beinachse links.")
N120 = ("## Kniegelenk links in 2 Ebenen\n\n## Befund\nGeringe Gonarthrose links.\n\n## Ergebnis\nGeringe Gonarthrose links.\n\n\n"
        "## Ganzbeinaufnahme im Stand\n\n## Befund\nRegelrechte Stellung des Beines. Unauffällige Hüftköpfe.\n\n## Ergebnis\n"
        "Regelrechte Darstellung der Beinachsen.")
r, h = bf.geruest_erhalten(G120, N120, "Knie links: geringe Gonarthrose.")
check("63 RH 120: Ganzbein nicht diktiert → Gerüst-Teil mit LAMA-Sätzen wörtlich, Knie aus dem Diktat",
      LAMA in r and "Unauffällige Hüftköpfe" not in r and "Geringe Gonarthrose links." in r and h, f"{h}\n{r}")
N120b = N120.replace("Regelrechte Stellung des Beines. Unauffällige Hüftköpfe.", "Geringe Varusstellung.")
r, h = bf.geruest_erhalten(G120, N120b, "Knie links: geringe Gonarthrose. Ganzbein: geringe Varusstellung.")
check("63: Ganzbein diktiert, LAMA-Satz fehlt im neuen Teil → Satz zurück + Prüfzeile (Diff-Wächter)",
      "HKA = 178,5°" in r and "Geringe Varusstellung." in r and any("wiederhergestellt" in x for x in h), f"{h}\n{r}")
SQ = "Rechtskonvexe skoliotische Krümmung der BWS und LWS (Th5–L1) mit einem Cobb-Winkel von 14°."
G130 = ("## Halswirbelsäule a.p.\n\n## Befund\nNormale Stellung der HWS.\n\n## Ergebnis\nRegelrechte Darstellung der HWS.\n\n\n"
        "## Brustwirbelsäule a.p.\n\n## Befund\n" + SQ + "\n\n## Ergebnis\nGeringgradige rechtskonvexe Skoliose der BWS und LWS."
        "\n\n\n## Lendenwirbelsäule a.p.\n\n## Befund\nNormale Lordose.\n\n## Ergebnis\nRegelrechte Darstellung der LWS.")
N130 = ("## Funktionsaufnahmen der Lendenwirbelsäule\n\n## Befund\n" + SQ + " Regelrechte Ausbiegung bei seitlichen Aufnahmen. "
        "Keine pathologischen Ventral- oder Dorsalverlagerungen.\n\n## Ergebnis\n1. Geringgradige rechtskonvexe Skoliose der "
        "BWS und LWS.\n2. Kein Hinweis auf eine segmentale Instabilität.")
r, h = bf.geruest_erhalten(G130, N130, "LWS mit Funktionsaufnahmen unauffällig.")
funk = r.split("## Funktionsaufnahmen der Lendenwirbelsäule", 1)[-1]
check("67 RH 130: GWS-Teile bleiben, „Funktionsaufnahmen der LWS“ ZUSÄTZLICH hinter der LWS (4 Teile)",
      r.count("## Befund") == 4 and r.index("## Lendenwirbelsäule a.p.") < r.index("## Funktionsaufnahmen"), r)
check("67: SQUIRREL (Cobb-Satz + Skoliose-Punkt) nur im GWS-Teil, nicht in den Funktionsaufnahmen",
      SQ not in funk and "Skoliose" not in funk and r.count(SQ) == 1, r)
check("63/67: ohne Gerüst bzw. gleicher Befund → unverändert", bf.geruest_erhalten("", N130, "x") == (N130, [])
      and bf.geruest_erhalten(N130, N130, "LWS")[0] == N130)

# ───────────────────────────── 62: Cursor im Ergebnis ─────────────────────────────
E3 = "## Knie rechts\n\n## Befund\nX.\n\n## Ergebnis\n1. Gonarthrose rechts.\n2. Erguss.\n3. Baker-Zyste."
e = bf.ergebnis_einfuegen(E3, "zweitens Chondrocalcinose", cursor=E3.index("2. Erguss"))
check("62: Cursor im Ergebnis + „zweitens …“ → neuer 2., alte 2./3. → 3./4., nie doppelte Nummern",
      e is not None and e[0].endswith("1. Gonarthrose rechts.\n2. Chondrocalcinose.\n3. Erguss.\n4. Baker-Zyste."), e)
check("62: Cursor im Befund → kein Ergebnis-Einfügen (normales Einfügen an der Stelle)",
      bf.ergebnis_einfuegen(E3, "zweitens Y", cursor=E3.index("X.")) is None)
check("62: ohne Ordnungswort → None (wie bisher)", bf.ergebnis_einfuegen(E3, "kleiner Erguss") is None)
src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("62: EXE-Cursor-Diktat nutzt ergebnis_einfuegen (nur ohne Markierung)",
      "_bf.ergebnis_einfuegen(vorher, text, gross, cursor=ziel[0]) if ziel[0] == ziel[1] else None" in src)
check("63/67: EXE baut das Gerüst nach dem Diktat mit geruest_erhalten zusammen",
      "_bf.geruest_erhalten(getattr(self, \"_vor_lauf\", \"\") or \"\", erg.report, self.final_transcript)" in src)

# ───────────────────────────── 49a/52: Nur Text ─────────────────────────────
e = pl.nur_text_aus_diktat("Sonographie Weichteile:\nKein Hinweis auf eine Raumforderung.\nErgebnis:\nUnauffälliger Befund.",
                           pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=None, log=lambda *a: None))
check("52: Nur Text – Untersuchungstitel und „Ergebnis:“ als Überschrift (## → fett in Anzeige/Zwischenablage)",
      e.report == "## Sonographie Weichteile\nKein Hinweis auf eine Raumforderung.\n## Ergebnis\nUnauffälliger Befund.", e.report)

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
