"""Gate kaiscribe-mehrfach-seitenlos-n1 (Georg Riegler 19.11.2026, Foto: CAS lws + bü in EINEM Diktat → nur ein LWS-Befund,
Becken hineingemischt, HIPPO-Zeile als eigener Absatz am Ende; „Wie funktioniert es, wenn ich 2 Untersuchungen habe?“).
Regel-Register: „Mehrere Untersuchungen in einem Diktat → je Untersuchung eigener Befund mit eigener Vorlage“.
Teil 1: Regionen-Trenner ohne Seite (befund_regeln.split_regionen; Web gleich über befund_regeln_fixtures.json „split“).
Teil 2: Satz-Zuordnung nach Inhalt mit CAS (cas_vorlagen.inhalt_zuordnen): Diktat ohne Überschriften → beide Befunde.
Teil 3: ganze EXE-Kette (pipeline.befund_aus_diktat, KI-Attrappe) mit Georgs Fall (maskiert) + HIPPO-Baustein:
        zwei Befunde „Lendenwirbelsäule in 2 Ebenen“ + „Beckenübersicht …“, HIPPO-Sätze + Schlusssatz nur im Beckenbefund,
        Coxarthrose mit K&L-Tabellensatz Grad 2 links nur im Beckentext.
Synthetische Diktate, keine Patientendaten.  Aufruf: python3 tests/offline/test_mehrfach_seitenlos.py"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import cas_vorlagen as cv  # noqa: E402
import detect  # noqa: E402
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
erkennen = lambda t: detect.detect_template(t, T)  # noqa: E731
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def L(kurz, text, vorlage, seite=None):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": "Röntgen", "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True}


LWS = L("lws", "LWS", "lendenwirbelsäule_in_2_ebenen")
BUE = L("bü", "Becken", "beckenübersicht_stehend")          # wie die Praxis-Zuordnung (Kürzel bü)
BUE_H = L("bü", "Beckenübersicht", "beckenübersicht_und_hüfte")

# Georgs Fall (maskiert, Wortlaut sinngemäß aus dem Foto vom 19.11.2026)
GEORG = ("LWS in 2 Ebenen: Geringe Verschmälerung der Bandscheibenfächer L2 bis L4 mit Sklerosierung. Geringe Spondylophyten "
         "L3 bis L5. Beckenübersicht: Geringgradige Coxarthrose links. Geringe Fibroostosen an der SIAS und am Trochanter "
         "major beidseits.")
# dasselbe ohne Satzzeichen (chirp_3 ohne Interpunktion)
GEORG_FLIESSEND = ("LWS geringe Verschmälerung der Bandscheibenfächer L2 bis L4 mit Sklerosierung geringe Spondylophyten L3 bis "
                   "L5 Becken geringgradige Coxarthrose links geringe Fibroostosen an der SIAS und am Trochanter major beidseits")
# Nachtrag Georg 19.11. 09:26: fließend ohne Regionsnennung
GEMISCHT = ("geringe Coxarthrose links, Osteochondrose L5/S1, Fibroostosen am Trochanter major beidseits, Spondylophyten L3 "
            "bis L5")


# ───────────────────────────── Teil 1: Trenner ohne Seite ─────────────────────────────
check("Georgs Diktat → zwei Abschnitte (LWS | Becken)", br.split_regionen(GEORG) == [
    "LWS in 2 Ebenen: Geringe Verschmälerung der Bandscheibenfächer L2 bis L4 mit Sklerosierung. Geringe Spondylophyten "
    "L3 bis L5.", "Beckenübersicht: Geringgradige Coxarthrose links. Geringe Fibroostosen an der SIAS und am Trochanter "
    "major beidseits."], br.split_regionen(GEORG))
check("Schulter + Ellbogen (Georg 05.10.) bleibt zwei Befunde",
      len(br.split_regionen("Schulter rechts Punkt Omarthrose Punkt Ellbogen rechts Punkt Arthrose Punkt")) == 2)
check("HWS + LWS ohne CAS bleibt EIN Abschnitt (Kombi-Vorlage hws_und_lws)",
      br.split_regionen("HWS: Osteochondrose C5/C6. LWS: Spondylose.") == ["HWS: Osteochondrose C5/C6. LWS: Spondylose."])
check("„Fibroostosen am Becken“ mitten im Satz trennt nicht",
      len(br.split_regionen("LWS: Spondylose L4. Fibroostosen am Becken beidseits.")) == 1)

# ───────────────────────────── Teil 2: Zuordnung nach Inhalt ─────────────────────────────
cas = cv.CasHinweis([LWS, BUE], T)


def zuordnen(diktat, c=cas):
    segs = cv.aufteilen(br.split_regionen(diktat), c, T, erkennen)
    return cv.inhalt_zuordnen(segs, c, T, erkennen)


segs, leist, h = zuordnen(GEMISCHT)
check("Nachtrag-Fixture: ohne Überschriften auf beide Befunde verteilt (Diktat-Reihenfolge)",
      segs == ["geringe Coxarthrose links, Fibroostosen am Trochanter major beidseits",
               "Osteochondrose L5/S1, Spondylophyten L3 bis L5"]
      and [l.vorlage for l in leist] == ["beckenübersicht_stehend", "lendenwirbelsäule_in_2_ebenen"] and h == [],
      f"{segs} {h}")
segs, leist, h = zuordnen("LWS: Osteochondrose L5/S1. Geringgradige Coxarthrose links. Beckenschiefstand, rechts tiefer. "
                          "Osteopenie.")
check("Becken-Begriffe im LWS-Abschnitt wandern in den Beckenbefund, „rechts tiefer“/„Osteopenie“ folgen dem Satz davor",
      segs == ["LWS: Osteochondrose L5/S1.", "Geringgradige Coxarthrose links. Beckenschiefstand, rechts tiefer. Osteopenie."]
      and leist[1].vorlage == "beckenübersicht_stehend", segs)
segs, leist, h = zuordnen("LWS: Osteochondrose L5/S1. Kniegelenk mit Erguss. Spondylose.")
check("Knie-Satz ohne Knie im CAS-Auftrag → bleibt stehen + Prüfzeile",
      any("Knie nicht im CAS-Auftrag" in x and "bitte prüfen" in x for x in h), h)
segs, leist, h = zuordnen("LWS: Spondylose. Osteochondrose L5/S1 und ISG-Arthrose beidseits. Becken: Coxarthrose links.")
check("Satz mit LWS- UND Becken-Begriff → bleibt beim Abschnitt + Prüfzeile (kein Raten)",
      segs[0] == "LWS: Spondylose. Osteochondrose L5/S1 und ISG-Arthrose beidseits."
      and any("nicht eindeutig" in x for x in h), f"{segs} {h}")
segs, leist, h = zuordnen("LWS: Spondylose L4. Becken: Coxarthrose links.")
check("klar getrennt diktiert → unverändert (keine Umbauten)", segs == ["LWS: Spondylose L4.", "Becken: Coxarthrose links."]
      and leist == [None, None] and h == [], f"{segs} {leist}")
segs, leist, h = zuordnen("Fuß links: Hallux valgus. Coxarthrose rechts.", cv.CasHinweis([L("f", "Fuß links", "fuß_in_2_ebenen",
                                                                                              "links"), LWS], T))
check("Becken-Begriff ohne Becken im CAS → Prüfzeile, kein neuer Befund", len(segs) == 1 and any("Becken/Hüfte" in x for x in h),
      f"{segs} {h}")
segs, leist, h = zuordnen("Schulter rechts: Omarthrose. Ellbogen rechts: Arthrose.", cv.CasHinweis([LWS], T))
check("nur eine CAS-Untersuchung → keine Zuordnung nach Inhalt", leist == [None, None] and h == [])

# ───────────────────────────── Teil 3: ganze EXE-Kette ─────────────────────────────
KL2 = br.KL_TABELLE["2"] if "2" in br.KL_TABELLE else br.KL_TABELLE[2]


def ki_attrappe(prompts):
    """KI-Attrappe: Befund aus Vorlage + Diktat des Abschnitts; geringgradige Coxarthrose → K&L-Tabellensatz Grad 2."""
    def llm(p):
        prompts.append(p)
        titel = p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0]
        diktat = p.rsplit("<diktat>", 1)[1].split("</diktat>")[0].strip()
        key = next(k for k, v in T.items() if v.get("display_name") == titel)
        body = T[key]["body"].split("\n", 2)[2]
        befund, erg = [], []
        if "oxarthrose links" in diktat:
            befund.append("Linkes Hüftgelenk: " + KL2)
            erg.append("Geringgradige Coxarthrose links (Arthrose Grad 2 nach Kellgren & Lawrence).")
        if "Fibroostosen" in diktat:
            befund.append("Geringe Fibroostosen an der Spina iliaca anterior superior und am Trochanter major beidseits.")
            erg.append("Geringe Fibroostosen beidseits.")
        if "L2 bis L4" in diktat or "Osteochondrose" in diktat:
            befund.append("Geringe Verschmälerung der Bandscheibenfächer L2 bis L4 mit Sklerosierung der Grund- und Deckplatten.")
            erg.append("Geringe Osteochondrose L2 bis L4.")
        if "Spondylophyten" in diktat:
            befund.append("Geringe ventrale Spondylophyten L3 bis L5.")
            erg.append("Geringe Spondylose L3 bis L5.")
        return (f"## {titel}\n\n## Befund\n" + "\n".join(befund + [body]) + "\n\n## Ergebnis\n"
                + ("\n".join(erg) or T[key].get("ergebnis", "")))
    return llm


HIPPO = I.aus_liste([{
    "accno": "T-G19", "ziffer": 2, "modul": "hippo", "name": "HIPPO", "modul_name": "IB Lab HIPPO", "version": 1,
    "aktualisiert": "2026-11-19T09:00:00", "seiten": ["rechts", "links"],
    "befundteil": ["Beckenhöhendifferenz 1 mm (IB Lab HIPPO).", "Beinlängendifferenz 1 mm (IB Lab HIPPO)."],
    "ergebnis": ["Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen."],
    "hinweise": [], "nicht_zugeordnet": [], "vorwerte": [],
    "befundtext": {"format": 1, "saetze": ["Beckenschiefstand von 1 mm, rechts tieferstehend.",
                                           "Beinlängendifferenz von 1 mm, rechts kürzer."],
                   "ergebnis": "", "schluss": "Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.",
                   "kind": False, "becken": True},
    "alter": 70}])
SCHLUSS = "Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen."


def bloecke(report):
    """Report → {Titel: Text des Abschnitts}."""
    out, titel = {}, None
    for z in report.split("\n"):
        k = z.strip()
        if k.startswith("## ") and k[3:].strip() not in ("Befund", "Ergebnis"):
            titel = k[3:].strip()
            out[titel] = ""
        elif titel:
            out[titel] += z + "\n"
    return out


for name, diktat, leistungen in (("Georg (Überschriften)", GEORG, [LWS, BUE]),
                                 ("Georg ohne Satzzeichen", GEORG_FLIESSEND, [LWS, BUE]),
                                 ("Nachtrag ohne Regionsnennung", GEMISCHT, [LWS, BUE]),
                                 ("Georg mit BÜ = Beckenübersicht und Hüfte", GEORG, [LWS, BUE_H])):
    prompts = []
    c = cv.CasHinweis(leistungen, T)
    ctx = pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=ki_attrappe(prompts), log=lambda *a: None,
                     cas=c, ibl=I.IblKontext(HIPPO, cas_leistungen=leistungen))
    erg = pl.befund_aus_diktat(diktat, ctx)
    b = bloecke(erg.report)
    # Vorlage des Beckenbefunds: die der CAS-Leistung – nennt das Diktat „Beckenübersicht:“, gilt bei CAS „Beckenübersicht
    # und Hüfte“ die genauere des Diktats (cas_vorlagen.abgleich, wie bisher)
    becken_v = next((v for v in erg.vorlagen if v != "lendenwirbelsäule_in_2_ebenen"), leistungen[1]["vorlage"])
    becken_titel = T[becken_v]["display_name"]
    check(f"{name}: Vorlagen LWS + Becken (Diktat-Reihenfolge)", erg.vorlagen == (
              [becken_v, "lendenwirbelsäule_in_2_ebenen"] if diktat == GEMISCHT else ["lendenwirbelsäule_in_2_ebenen", becken_v])
          and becken_v in ("beckenübersicht_stehend", leistungen[1]["vorlage"]), erg.vorlagen)
    lws_t, bk_t = b.get("Lendenwirbelsäule in 2 Ebenen", ""), b.get(becken_titel, "")
    check(f"{name}: zwei Befunde „Lendenwirbelsäule in 2 Ebenen“ + „{becken_titel}“, beide vollständig",
          set(b) == {"Lendenwirbelsäule in 2 Ebenen", becken_titel} and erg.vollstaendig and len(prompts) == 2,
          f"{list(b)} {erg.fehler}\n{erg.report}")
    check(f"{name}: HIPPO-Sätze + Schlusssatz nur im Beckenbefund",
          "Beckenschiefstand von 1 mm, rechts tieferstehend." in bk_t and "Beinlängendifferenz von 1 mm, rechts kürzer." in bk_t
          and SCHLUSS in bk_t and "Beckenschiefstand" not in lws_t and SCHLUSS not in lws_t
          and erg.ibl is not None and erg.ibl.zuordnung.get("hippo") == becken_titel, erg.report)
    check(f"{name}: Coxarthrose (K&L-Tabellensatz Grad 2 links) + Fibroostosen nur im Beckentext, LWS ohne Becken-Befund",
          ("Coxarthrose links (Arthrose Grad 2 nach Kellgren & Lawrence)" in bk_t and KL2 in bk_t
           and "Fibroostosen" in bk_t and "oxarthrose" not in lws_t and "Fibroostosen" not in lws_t
           and "Trochanter" not in lws_t) if diktat != GEMISCHT else
          ("Coxarthrose links (Arthrose Grad 2 nach Kellgren & Lawrence)" in bk_t and "oxarthrose" not in lws_t),
          erg.report)
    check(f"{name}: LWS-Befund mit den Wirbelsäulen-Befunden, Becken ohne", "Spondylophyten" in lws_t
          and "Spondylophyten" not in bk_t and "Bandscheibenfächer" not in bk_t, erg.report)
    check(f"{name}: keine Prüfzeilen", not [x for x in erg.cas_hinweise if "prüfen" in x or "nicht diktiert" in x],
          erg.cas_hinweise)
    if name.startswith("Georg (Ü"):
        print("\n── Prüftext (Bericht) ──\n" + erg.report + "\n──")

# Rho in einem gemischten Diktat → zum LWS-Befund
prompts = []
ctx = pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=ki_attrappe(prompts), log=lambda *a: None,
                 cas=cv.CasHinweis([LWS, BUE], T))
erg = pl.befund_aus_diktat(GEMISCHT + ", Rho 8", ctx)
b = bloecke(erg.report)
# kaiscribe-georg-2011-n1 (Georg 20.11.2026, Punkte 19/40c): Rho ist ein eigener Einzelbefund ganz am Schluss
check("Rho-Auslöser im gemischten Diktat → eigener Rho-Befund am Schluss, weder im LWS- noch im Becken-Befund",
      "(Rho)" not in b.get("Lendenwirbelsäule in 2 Ebenen", "x") and "(Rho)" not in b.get("Beckenübersicht stehend", "x")
      and "(Rho)" in b.get(br.RHO_TITEL, "") and erg.report.rstrip().endswith(br.RHO_ERGEBNIS)
      and erg.report.index("## " + br.RHO_TITEL) > erg.report.index("## Beckenübersicht stehend"),
      erg.report)

# ohne CAS: Georgs Diktat mit Überschriften → trotzdem zwei Befunde (Regionen-Trenner)
prompts = []
ctx = pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=ki_attrappe(prompts), log=lambda *a: None)
erg = pl.befund_aus_diktat(GEORG, ctx)
check("ohne CAS (Web/alte Brücke): Überschriften trennen → zwei Befunde", len(prompts) == 2
      and erg.report.count("## Befund") == 2, erg.report[:300])

print(f"\n{'✅ ALLE GRÜN' if not fails else f'❌ {fails} rot'}")
sys.exit(1 if fails else 0)
