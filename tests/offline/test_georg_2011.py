"""Gate kaiscribe-georg-2011-n1 – Georgs Diktiertag 20.11.2026 („Alles muss am Montag funktionieren“), EXE-Teil.
Die Textregeln (EXE = Web) prüft befund_regeln_test.py (Fixtures „georg_2011“, „rho“); hier die ganze EXE-Kette mit
KI-Attrappe und IB-Lab-Bausteinen:
   9   Winkel-Erläuterung (LAMA/FROG/HIPPO-Schlussanmerkung) als eigener Block „Anmerkung: …“ mit 1 Leerzeile davor
  19   Rho als eigener Einzelbefund am Schluss (auch bei Mehrfach), 31 Score 6 → kein Text, 7 → Text
  21b  RBfracture („KI: Verdacht auf …“) nie im Befund/Ergebnis, nur Hinweis
  34   auffällige FROG-Werte im Ergebnis des Fuß-Befunds auch bei Mehrfach (Hand + Fuß)
  41a  FROG ohne Diagnose (Abholer 1.3.14, RH 30): Messwerte ans Ende der Fuß-Beschreibung, kein Ergebnispunkt
  7/32 Befundanfang ohne „Im Übrigen“ auch in der EXE-Kette
Keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_georg_2011.py"""
import copy, json, pathlib, sys
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
F19 = json.loads((HIER / "snapshots" / "frog_1911_beidseits.json").read_text(encoding="utf-8"))
SCHLUSS = "Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen."
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def L(kurz, text, vorlage, seite, ziffer=1):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": "Röntgen", "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True, "ziffer": ziffer}


def vorlage_report(key, titel, erg_zusatz=""):
    v = T[key]
    return f"## {titel}\n\n## Befund\n{v['body'].split(chr(10), 2)[2]}\n\n## Ergebnis\n{v['ergebnis']}{erg_zusatz}"


def kontext(llm, leistungen=None, bausteine=None, log=None):
    cas = cv.CasHinweis(leistungen, T) if leistungen else None
    ibl = I.IblKontext(I.aus_liste(bausteine), cas_leistungen=leistungen) if bausteine else None
    return pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=llm, log=log or (lambda *a: None),
                      cas=cas, ibl=ibl)


def ergebnis_teil(report, titel=None):
    if titel:
        report = report.split(f"## {titel}", 1)[1].split("\n\n\n## ", 1)[0]
    return report.split("## Ergebnis\n", 1)[1].split("\n\n\n## ", 1)[0].rstrip()


# ───────────────────────────── 9: „Anmerkung: …“-Block ─────────────────────────────
r = "## Fuß links in 2 Ebenen\n\n## Befund\nText.\n\n## Ergebnis\nPes planus links.\n" + SCHLUSS
soll = "## Fuß links in 2 Ebenen\n\n## Befund\nText.\n\n## Ergebnis\nPes planus links.\n\nAnmerkung: " + SCHLUSS
check("9: Schlussanmerkung → „Anmerkung: …“ mit einer Leerzeile davor", I.anmerkung_absetzen(r) == soll,
      I.anmerkung_absetzen(r))
check("9: zweimal angewandt gleich, ohne Schlussanmerkung unverändert",
      I.anmerkung_absetzen(soll) == soll and I.anmerkung_absetzen("## A\n\n## Ergebnis\nX.") == "## A\n\n## Ergebnis\nX.")
r2 = ("## Ganzbeinaufnahme im Stand\n\n## Befund\nB.\n\n## Ergebnis\n1. Genu varum rechts.\n"
      "HKA = Hüft-Knie-Sprunggelenk-Winkel, MAD = mechanische Achsabweichung (Mikulicz-Linie).\n2. Gonarthrose rechts.\n\n\n"
      "## Fuß links in 2 Ebenen\n\n## Befund\nText.\n\n## Ergebnis\nPes planus links.\n" + SCHLUSS)
g = I.anmerkung_absetzen(r2)
check("9: je Untersuchung ans Ende ihres Ergebnisses (Mehrfach), Nummerierung zählt die Anmerkung nicht",
      "2. Gonarthrose rechts.\n\nAnmerkung: HKA = Hüft-Knie" in g and g.endswith("Pes planus links.\n\nAnmerkung: " + SCHLUSS)
      and br.ergebnis_nummerieren(g) == g and I.ist_schluss("Anmerkung: " + SCHLUSS), g)

# ───────────────────────────── 41a: FROG ohne Diagnose (Abholer 1.3.14, RH 30) ─────────────────────────────
MW = ["Gemessene Winkel d.p.: Hallux-valgus-Winkel 17°, Intermetatarsalwinkel I/II 7° und Metatarsophalangealwinkel V 10°.",
      "Gemessene Winkel seitlich: Calcaneusneigung 24°, Meary-Winkel 6° und Längsgewölbewinkel 114°."]
OHNE = {"accno": "999001200030", "ziffer": 1, "modul": "frog", "name": "FROG", "version": 1, "seiten": ["rechts"],
        "befundteil": [], "ergebnis": [],
        "hinweise": ["FROG: keine Diagnose, außerhalb der Norm: Meary-Winkel 6° – Messwerte ohne Diagnose im Befund, bitte am "
                     "KI-Bild prüfen."],
        "befundtext": {"format": 1, "begriffe": [], "stellung": [], "gewoelbe": [], "ohne_diagnose": True,
                       "messwerte": MW, "schluss": SCHLUSS}}
b = I.aus_liste([OHNE])[0]
check("41a: Baustein „ohne_diagnose“ wird gelesen (3.19 hat ihn verworfen)", b.befundtext is not None
      and b.befundtext["ohne_diagnose"] and b.befundtext["messwerte"] == MW, b.befundtext)
FUSS_R = L("fussr", "Fuß re.", "fuß_in_2_ebenen", "rechts")
erg = pl.befund_aus_diktat("Fuß rechts unauffällig.", kontext(lambda p: "", [FUSS_R], [OHNE]))
befund = erg.report.split("## Befund\n", 1)[1].split("## Ergebnis", 1)[0]
check("41a: Messwert-Sätze am Ende der Fuß-Beschreibung, Vorlagensätze bleiben",
      befund.rstrip().endswith(MW[0] + "\n" + MW[1]) and "Das Fußskelett ist nach Form" in befund, erg.report)
check("41a: kein Ergebnispunkt aus FROG – Normal-Ergebnis bleibt, Schlussanmerkung als „Anmerkung: …“",
      ergebnis_teil(erg.report) == T["fuß_in_2_ebenen"]["ergebnis"].rstrip(".") + " rechts.\n\nAnmerkung: " + SCHLUSS
      and erg.vollstaendig, ergebnis_teil(erg.report))
check("41a: Prüfzeile „bitte am KI-Bild prüfen“ bleibt sichtbar (rot in KaiScribe)",
      any("bitte am KI-Bild prüfen" in h for h in I.anzeige_hinweise(I.aus_liste([OHNE]))))
vorfuss = I._frog_plan(b, "Vorfuß rechts in 2 Ebenen", "rechts", "", [])
check("41a: Vorfuß → nur die d.p.-Werte", vorfuss is not None and vorfuss[0] == [MW[0]], vorfuss)
ohne_mw = copy.deepcopy(OHNE)
ohne_mw["befundtext"]["messwerte"] = []
check("41a: ohne Messwerte bleibt es wie bisher (nichts eingesetzt)", I.aus_liste([ohne_mw])[0].befundtext is None)
# 41a a) Widerspruch Gewölbe + andere Diagnose: Gewölbe-Satz „Uneinheitliche Winkel …“ statt des Vorlagensatzes
WID = copy.deepcopy(F19["bruecke_neu"])
if WID is not None and isinstance(WID.get("befundtext"), dict):
    UNEIN = ("Uneinheitliche Winkel des Längsgewölbes mit einer Calcaneusneigung von 22°, einem Meary-Winkel von −5° und "
             "einem Längsgewölbewinkel von 120°.")
    WID["befundtext"].update(gewoelbe=[UNEIN], gewoelbe_weg=False, gewoelbe_pathologisch=True)
    FUSS2 = L("fuss2", "Fuß bds.", "fuß_in_2_ebenen", "beidseits")
    erg = pl.befund_aus_diktat("Fuß beidseits unauffällig.", kontext(lambda p: "", [FUSS2], [WID]))
    check("41a a): widersprüchliche Gewölbewinkel → Satz „Uneinheitliche Winkel …“ statt Gewölbesatz, Begriff im Ergebnis",
          UNEIN in erg.report and "Das Fußgewölbe ist regulär ausgebildet bei" not in erg.report
          and "Digitus quintus varus" in ergebnis_teil(erg.report), erg.report)

# ───────────────────────────── 34: FROG im Ergebnis des Fuß-Befunds bei Mehrfach (Hand + Fuß) ─────────────────────────────
if WID is not None:
    NEU = copy.deepcopy(F19["bruecke_neu"])
    HAND2 = L("hand2", "Hand bds.", "hand_in_2_ebenen", "beidseits", ziffer=1)
    FUSS2 = L("fuss2", "Fuß bds.", "fuß_in_2_ebenen", "beidseits", ziffer=2)
    NEU["ziffer"] = 2

    def ki_mehrfach(p):
        if "<untersuchung>Fuß" in p:
            return vorlage_report("fuß_in_2_ebenen", "Fuß beidseits in 2 Ebenen", "")
        return vorlage_report("hand_in_2_ebenen", "Hand beidseits in 2 Ebenen", "")
    erg = pl.befund_aus_diktat("Hand beidseits: geringe Rhizarthrose beidseits. Fuß beidseits: unauffällig.",
                               kontext(ki_mehrfach, [HAND2, FUSS2], [NEU]))
    fuss_titel = next((z[3:] for z in erg.report.split("\n") if z.startswith("## Fuß")), None)
    check("34: Mehrfach Hand + Fuß – FROG-Begriff im Ergebnis des Fuß-Befunds, nicht der Hand",
          fuss_titel is not None and "Digitus quintus varus" in ergebnis_teil(erg.report, fuss_titel)
          and "Digitus quintus varus" not in erg.report.split("## " + fuss_titel)[0], erg.report)

# ───────────────────────────── 21b: RBfracture nur Hinweis ─────────────────────────────
RBF = {"accno": "999001200069", "ziffer": 1, "modul": "rbfracture", "name": "RBfracture", "version": 1,
       "befundteil": ["KI: Verdacht auf Fraktur Handgelenk."], "ergebnis": ["KI: Verdacht auf Fraktur Handgelenk."],
       "hinweise": []}
HGL = L("hgl", "Handgelenk li.", "handgelenk_in_2_ebenen", "links")
ki_hg = (lambda p: vorlage_report("handgelenk_in_2_ebenen", "Handgelenk links in 2 Ebenen")) if "handgelenk_in_2_ebenen" in T \
    else (lambda p: vorlage_report("allgemein", "Handgelenk links"))
erg = pl.befund_aus_diktat("Handgelenk links: geringe Weichteilschwellung.",
                           kontext(lambda p: ki_hg(p).replace("## Ergebnis\n", "## Ergebnis\n1. Geringe Weichteilschwellung.\n2. KI: Verdacht auf Gelenkserguss.\n").replace(T.get("handgelenk_in_2_ebenen", T["allgemein"])["ergebnis"], ""),
                                   [HGL], [RBF]))
check("21b: RBfracture-Text weder im Befund noch im Ergebnis, KI-Punkt der KI gestrichen, Hinweis bleibt",
      "KI:" not in erg.report and "Verdacht auf Fraktur" not in erg.report
      and any("KI: Verdacht auf Fraktur Handgelenk." in h for h in I.anzeige_hinweise(I.aus_liste([RBF]))), erg.report)

# ───────────────────────────── 19/31: Rho ─────────────────────────────
LWS = L("lws", "LWS", "lendenwirbelsäule_in_2_ebenen", None, ziffer=1)
BUE = L("bü", "Beckenübersicht", "beckenübersicht_stehend", None, ziffer=2)


def ki_lws_bue(p):
    if "<untersuchung>Beckenübersicht" in p:
        return vorlage_report("beckenübersicht_stehend", "Beckenübersicht stehend")
    return vorlage_report("lendenwirbelsäule_in_2_ebenen", "Lendenwirbelsäule in 2 Ebenen")


for score, text in (("6", False), ("7", True)):
    erg = pl.befund_aus_diktat(f"LWS: Osteochondrose L5/S1. Rho {score}.", kontext(ki_lws_bue))
    check(f"31: Rho {score} → {'Text' if text else 'kein Text'}", (br.RHO_ERGEBNIS in erg.report) == text
          and ("(Rho)" in erg.report) == text and "Rho" not in erg.raw.split("Rho")[0][-1:], erg.report)
erg = pl.befund_aus_diktat("Lendenwirbelsäule: Osteochondrose L5/S1, Rho 8. Beckenübersicht: unauffällig.",
                           kontext(ki_lws_bue, [LWS, BUE]))
bloecke = [z[3:] for z in erg.report.split("\n") if z.startswith("## ") and z[3:] not in ("Befund", "Ergebnis")]
check("19/40c: Mehrfach LWS + Becken mit Rho → Rho als eigener Befund ganz am Schluss mit eigenem Ergebnis",
      bloecke[-1:] == [br.RHO_TITEL] and len(bloecke) == 3 and erg.report.rstrip().endswith(br.RHO_ERGEBNIS)
      and erg.report.count("(Rho)") == 1, erg.report)

# ───────────────────────────── 7/32: Befundanfang in der EXE-Kette ─────────────────────────────
KNIE = L("knier", "Knie re.", "kniegelenk_in_2_ebenen", "rechts")
ki_knie = (lambda p: vorlage_report("kniegelenk_in_2_ebenen", "Kniegelenk rechts in 2 Ebenen")
           .replace("## Befund\nNormale Form", "## Befund\nIm Übrigen normale Form")
           .replace("## Ergebnis\n" + T["kniegelenk_in_2_ebenen"]["ergebnis"], "## Ergebnis\nZarte Fibroostose am Patellaoberpol rechts.")
           .replace("Unauffällige Weichteile.", "Zarte Fibroostose am Patellaoberpol. Unauffällige Weichteile."))
log = []
erg = pl.befund_aus_diktat("Knie rechts: zarte Fibroostose am Patellaoberpol.", kontext(ki_knie, [KNIE], log=log.append))
check("32: Knie – Befund beginnt mit „Normale Form und Stellung …“, nie mit „Im Übrigen“ (Protokoll [GRUNDREGEL])",
      erg.report.split("## Befund\n", 1)[1].startswith("Normale Form und Stellung")
      and any(str(x).startswith("[GRUNDREGEL]") for x in log), erg.report)

# ───────────────────────────── 16/17: RH 84 Sprunggelenk + Fuß, Jones-Fraktur ─────────────────────────────
import re  # noqa: E402


def ki_vorlage(p, erg="Unauffälliger Befund."):
    u = re.search(r"<untersuchung>(.*?)</untersuchung>", p).group(1)
    k = next(k for k, v in T.items() if v.get("display_name") == u)
    return f"## {u}\n\n## Befund\n{T[k]['body'].split(chr(10), 2)[2]}\n\n## Ergebnis\n{erg}"


OSG = L("osgl", "OSG li.", "sprunggelenk_in_2_ebenen", "links", ziffer=1)
FUSSL = L("fussl", "Fuß li.", "fuß_in_2_ebenen", "links", ziffer=2)
erg = pl.befund_aus_diktat("Jones-Fraktur Os metatarsale V links.",
                           kontext(lambda p: ki_vorlage(p, "Jones-Fraktur links."), [OSG, FUSSL]))
titel = [z[3:] for z in erg.report.split("\n") if z.startswith("## ") and z[3:] not in ("Befund", "Ergebnis")]
check("16: Jones/Os metatarsale V → Vorfuß-Vorlage (nicht „allgemein“), Region Fuß",
      erg.vorlagen[0] == "vorfuß_in_2_ebenen" and cv.regionen("Jones-Fraktur Os metatarsale V") == {"fuss"}, erg.vorlagen)
check("16: 2 CAS-Leistungen, 1 diktierte Region → die zweite (OSG) bekommt ihren Normalbefund + Prüfzeile",
      "Sprunggelenk links in 2 Ebenen" in titel and T["sprunggelenk_in_2_ebenen"]["body"].split("\n", 2)[2][:40] in erg.report
      and any(cv.NICHT_DIKTIERT_NORMAL in h for h in erg.cas_hinweise), (titel, erg.cas_hinweise))
check("41b: Os naviculare cornutum zählt zum Fuß, nicht zur Hand", cv.regionen("kleines Os naviculare cornutum") == {"fuss"},
      cv.regionen("kleines Os naviculare cornutum"))

# ───────────────────────────── 36/37a/35: LWS + Ganzbein (nur LAMA, nicht diktiert) ─────────────────────────────
LAMA_SCHLUSS = ("HKA = Hüft-Knie-Sprunggelenk-Winkel, MAD = mechanische Achsabweichung (Mikulicz-Linie/Traglinie des "
                "Ganzbeines). Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.")
LAMA = {"accno": "999001200077", "ziffer": 2, "modul": "lama", "name": "LAMA", "version": 1, "seiten": ["rechts", "links"],
        "befundteil": ["HKA-Winkel rechts 178,1° (IB Lab LAMA)."],
        "ergebnis": ["Regelrechte Beinachse beidseits (HKA rechts 1,9°, links 0,9°; MAD rechts 12,6 mm, links 11,7 mm).",
                     LAMA_SCHLUSS], "hinweise": []}
LWS1 = L("lws", "LWS", "lendenwirbelsäule_in_2_ebenen", None, ziffer=1)
GB = L("gb", "Ganzbein bds.", "ganzbeinaufnahme_im_stand", "beidseits", ziffer=2)
erg = pl.befund_aus_diktat("Lendenwirbelsäule: Osteochondrose L5/S1.",
                           kontext(lambda p: ki_vorlage(p, "Osteochondrose L5/S1."), [LWS1, GB], [LAMA]))
gb_titel = next((z[3:] for z in erg.report.split("\n") if z.startswith("## Ganzbein")), None)
check("36/37a: reiner KI-Teil (Ganzbein mit LAMA, nicht diktiert) bekommt eigenen Befund mit Titel aus der CAS-Leistung",
      gb_titel is not None and "Regelrechte Beinachse beidseits" in ergebnis_teil(erg.report, gb_titel)
      and ergebnis_teil(erg.report, gb_titel).endswith("Anmerkung: " + LAMA_SCHLUSS), erg.report)
ki_var = (lambda p: ki_vorlage(p, "Unauffälliger Befund.").replace(
    "## Befund\n", "## Befund\nMAD links 11,7 mm und rechts 12,6 mm mit Varisierung.\n"))
erg = pl.befund_aus_diktat("Ganzbeinaufnahme im Stand beidseits: MAD links 11,7 mm, rechts 12,6 mm.",
                           kontext(ki_var, [GB], [LAMA]))
check("35: LAMA im Normbereich → kein „Varisierung“ im Befundtext, Werte bleiben",
      "Varisierung" not in erg.report and "MAD links 11,7 mm und rechts 12,6 mm." in erg.report, erg.report)

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
