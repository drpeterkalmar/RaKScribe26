"""Gate v3.12.0 (Peter 13.10.2026: „Könnte RaKScribe von CAS erfahren, welche Untersuchungsart wir gleich diktieren
werden?“ — auch gemischte Diktate). Die RaKScribe-Brücke 1.1.0 reicht cas_leistungen_<id>.json nach.
Teil 1: cas_vorlagen.py (Vorlagenwahl mit CAS = Vorrang-Hinweis, Aufteilen gemischter Diktate, Hinweise, Seite).
Teil 2: pipeline.befund_aus_diktat mit CAS-Leistungen (Attrappe für Gemini, die Prompts mitschreibt): Diktat bestätigt
        CAS / Diktat allgemein → CAS / Diktat widerspricht → Diktat + Hinweis / zwei Leistungen beide diktiert /
        zwei Leistungen, eine diktiert / keine CAS-Datei (bit-gleich wie bisher, kein <cas_untersuchungen>).
Teil 3: EXE-Ablauf aus RaKScribe.py mit Attrappen (exe_stubs): Leistungen-Datei abholen → Band, nur zum eigenen Auftrag,
        halb geschrieben → später, Befund aus Text mit CAS → Hinweise im Band, EOL → grüne Bestätigung mit Titeln.
Teil 4 (nur am Mac, wenn ~/dev/ris-mods da ist): Protokoll gegen die echte Brückenseite (leistungen.py + auftrag.py).
Synthetische Diktate, keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_cas_leistungen.py"""
import json, os, pathlib, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import cas_vorlagen as cv  # noqa: E402
import detect  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


def L(kurz, text, mod, vorlage, seite=None, ohne=False):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": mod, "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": ohne, "bekannt": True}


# Beispiel-Leistungen wie aus der Brücke (Kurztexte und Vorlagen der Praxis-Zuordnung, ohne Patientendaten)
HWS = L("x-hws", "HWS", "Röntgen", "halswirbelsäule_in_2_ebenen")
LWS = L("x-lws", "LWS", "Röntgen", "lendenwirbelsäule_in_2_ebenen")
FUSSL = L("x-fuss-li", "Fuß links", "Röntgen", "fuß_in_2_ebenen", "links")
SOSUR = L("x-sono-schulter-re", "Sonographie der Schulter re.", "Sono", "sonografie_schultergelenk", "rechts")
USKNIE = L("x-sono-knie", "Sono Knie", "Sono", "sonografie_allgemein")
KOORD = L("x-zuschlag", "Zuschlag", "sonstige", None, ohne=True)
ABD = L("x-abd", "Abdomen-Leeraufnahme", "Röntgen", None)            # „?“ in der Zuordnung
CSU = L("x-ct-schulter", "CT Schulter", "CT", "allgemein")
erkennen = lambda t: detect.detect_template(t, T)  # noqa: E731


def wahlen(leistungen, diktat):
    cas = cv.CasHinweis(leistungen, T)
    segs = cv.aufteilen(pl.br.split_regionen(diktat), cas, T, erkennen)
    w = [cv.wahl(s, cas, T, erkennen) for s in segs]
    return segs, w, cv.hinweise(segs, w, cas, T)


# ───────────────────────────── Teil 1: cas_vorlagen ─────────────────────────────
cas = cv.CasHinweis([KOORD, HWS, ABD, L("neu", "Neu", "Röntgen", "gibt_es_nicht")], T)
check("Abrechnungsposten ignoriert, unbekannter Key → keine Vorlage", [l.kurz for l in cas.alle] == ["x-hws", "x-abd", "neu"]
      and [l.kurz for l in cas.mit_vorlage] == ["x-hws"] and cas.alle[2].vorlage is None)
check("Labels fürs Band", [cv.label(x["text"], x["kurz"], x["modalitaet"]) for x in (HWS, SOSUR, USKNIE, CSU, FUSSL)]
      == ["HWS", "Schulter re. (Sono)", "Knie (Sono)", "CT Schulter", "Fuß links"])
check("Regionen: Kombi-Vorlagen gehören zu mehreren", cv.regionen(cv.vorlagen_text("hws_und_lws", T)) == {"hws", "lws"}
      and cv.regionen(cv.vorlagen_text("wirbelsäule_gesamt", T)) == {"hws", "bws", "lws"}
      and cv.regionen(cv.vorlagen_text("sprunggelenk_mit_fuss", T)) == {"sprunggelenk", "fuss"})
check("Modalität aus Vorlage und Diktat", (cv.modalitaet_key("sonografie_schultergelenk", T),
                                           cv.modalitaet_key("schultergelenk_in_2_ebenen", T),
                                           cv.modalitaet_key("ct_thorax:", T), cv.modalitaet_key("allgemein", T),
                                           cv.modalitaet_text("Sonographie der Schulter"),
                                           cv.modalitaet_text("Mammographie und Sonographie"), cv.modalitaet_text("Knie"))
      == ("Sono", "Röntgen", "CT", None, "Sono", None, None))
check("Satzanfang: zweites inhaltliches Wort", (cv.kopf("Sonographie der rechten Schulter"), cv.kopf("HWS in 2 Ebenen"),
                                                cv.kopf("Keine Ausstrahlung in die HWS"))
      == ("Sonographie der rechten Schulter", "HWS in 2 Ebenen", "Keine Ausstrahlung"))

segs, w, h = wahlen([HWS], "HWS: Osteochondrose C5/6.")
check("a) Diktat bestätigt CAS → HWS, kein Hinweis", [x.vorlage for x in w] == ["halswirbelsäule_in_2_ebenen"]
      and w[0].art == "bestaetigt" and h == [])
segs, w, h = wahlen([HWS], "Unauffällig.")
check("b) Diktat allgemein → CAS-Vorlage HWS", [(x.vorlage, x.art) for x in w] == [("halswirbelsäule_in_2_ebenen", "cas")]
      and h == [])
segs, w, h = wahlen([KOORD, HWS], "Unauffällig.")
check("   … Abrechnungsposten daneben stört nicht", [x.vorlage for x in w] == ["halswirbelsäule_in_2_ebenen"] and h == [])
segs, w, h = wahlen([HWS], "Schulter rechts: Omarthrose.")
check("c) Diktat nennt Region, die nicht in CAS steht → Diktat gewinnt + Hinweise",
      [(x.vorlage, x.art) for x in w] == [("schultergelenk_in_2_ebenen", "diktat")]
      and h == ["Schultergelenk in 2 Ebenen: nicht in den CAS-Leistungen", "HWS laut CAS, nicht diktiert"], str(h))
segs, w, h = wahlen([FUSSL, LWS], "Fuß links: Hallux valgus. LWS: Osteochondrose L4/5.")
check("d) zwei Leistungen, beide diktiert (Fuß links + LWS) → zwei Abschnitte in Diktat-Reihenfolge",
      segs == ["Fuß links: Hallux valgus.", "LWS: Osteochondrose L4/5."]
      and [x.vorlage for x in w] == ["fuß_in_2_ebenen", "lendenwirbelsäule_in_2_ebenen"] and h == [], f"{segs} {h}")
segs, w, h = wahlen([FUSSL, LWS], "LWS: Osteochondrose L4/5.")
check("e) zwei Leistungen, eine diktiert → ein Abschnitt + „Fuß links laut CAS, nicht diktiert“",
      [x.vorlage for x in w] == ["lendenwirbelsäule_in_2_ebenen"] and h == ["Fuß links laut CAS, nicht diktiert"], str(h))
segs, w, h = wahlen([HWS, SOSUR], "HWS: Steilstellung, Osteochondrose C5/6. Schulter rechts: Bursitis subacromialis.")
check("f) HWS Röntgen + Schulter Sono: zwei Abschnitte, Schulter bekommt die Sono-Vorlage (CAS kennt die Modalität)",
      len(segs) == 2 and [x.vorlage for x in w] == ["halswirbelsäule_in_2_ebenen", "sonografie_schultergelenk"]
      and w[1].erkannt == "schultergelenk_in_2_ebenen" and h == [], f"{segs} {[x.vorlage for x in w]}")
segs, w, h = wahlen([HWS, SOSUR], "Röntgen der Halswirbelsäule in zwei Ebenen: Steilstellung. Sonographie der rechten "
                                  "Schulter: Bursitis subacromialis, Supraspinatussehne intakt.")
check("   … ausformuliert („Röntgen der Halswirbelsäule …“, „Sonographie der rechten Schulter …“)",
      [x.vorlage for x in w] == ["halswirbelsäule_in_2_ebenen", "sonografie_schultergelenk"])
segs, w, h = wahlen([HWS, SOSUR], "Schulter rechts Sonographie: Bursitis. Keine Ausstrahlung in die HWS.")
check("g) HWS nur nebenbei erwähnt (nicht am Satzanfang) → nicht geteilt", len(segs) == 1
      and w[0].vorlage == "sonografie_schultergelenk", str(segs))
segs, w, h = wahlen([USKNIE], "Knie rechts: Baker-Zyste 3 cm.")
check("h) Diktat nennt nur die Region, CAS sagt Sono → Sono-Vorlage statt Röntgen-Knie",
      w[0].vorlage == "sonografie_allgemein" and w[0].erkannt == "kniegelenk_in_2_ebenen" and h == [])
segs, w, h = wahlen([USKNIE], "Röntgen Knie rechts: Gonarthrose.")
check("   … nennt das Diktat selbst „Röntgen“ → Diktat gewinnt + Hinweis", w[0].vorlage == "kniegelenk_in_2_ebenen"
      and h == ["Kniegelenk in 2 Ebenen: nicht in den CAS-Leistungen"], str(h))
segs, w, h = wahlen([FUSSL], "Fuß rechts: unauffällig.")
check("i) Seite widerspricht CAS → Hinweis (Diktat-Seite bleibt)", w[0].vorlage == "fuß_in_2_ebenen"
      and h == ["Seite: diktiert rechts, laut CAS links (Fuß links)"], str(h))
segs, w, h = wahlen([HWS, LWS], "HWS und LWS: Osteochondrose.")
check("j) zwei CAS-Leistungen in einem Satz → Kombi-Vorlage, kein Hinweis", [x.vorlage for x in w] == ["hws_und_lws"]
      and h == [])
segs, w, h = wahlen([FUSSL, LWS], "Unauffällig.")
check("k) zwei Leistungen, Diktat ohne Region → allgemein + beide „nicht diktiert“", w[0].vorlage == "allgemein"
      and len(h) == 2)
# v3.16.2 (Ordi-E2E 15.10.): CAS „Sono Abdomen F.“ (usabdf) → weiblich, auch wenn das Diktat kein Geschlecht nennt
USABDF = L("usabdf", "Sono Abdomen F.", "Sono", "sonografie_abdomen_weiblich")
USABDM = L("usabdm", "Sono Abdomen M.", "Sono", "sonografie_abdomen_maennlich")
TH = L("th", "Thorax", "Röntgen", "thorax_in_2_ebenen")
segs, w, h = wahlen([TH, USABDF], "Thorax p a und seitlich. Herz normal groß. Lunge frei. Ergebnis: Unauffälliger Thorax. "
                                  "Sonographie des Abdomens. Leber homogen. Gallenblase steinfrei. Ergebnis: Unauffälliger Oberbauch.")
check("r) CAS Sono Abdomen weiblich, Diktat ohne Geschlecht → weibliche Vorlage (detect allein: männlich)",
      [x.vorlage for x in w] == ["thorax_in_2_ebenen", "sonografie_abdomen_weiblich"] and w[1].erkannt ==
      "sonografie_abdomen_maennlich" and h == [], f"{[(x.vorlage, x.art) for x in w]} {h}")
segs, w, h = wahlen([USABDM], "Sonographie des Abdomens. Leber homogen.")
check("   … CAS männlich, Diktat ohne Geschlecht → männlich", [x.vorlage for x in w] == ["sonografie_abdomen_maennlich"], str(w))
segs, w, h = wahlen([USABDF], "Sonographie des Abdomens männlich. Prostata normal groß.")
check("   … Diktat nennt das Geschlecht selbst → Diktat gewinnt (wie bisher)", [x.vorlage for x in w] ==
      ["sonografie_abdomen_maennlich"], str(w))
segs, w, h = wahlen([USABDM], "Sonographie des Abdomens weiblich. Uterus unauffällig.")
check("   … und umgekehrt (weiblich diktiert, CAS männlich)", [x.vorlage for x in w] == ["sonografie_abdomen_weiblich"], str(w))
segs, w, h = wahlen([ABD], "Oberbauch: freie Luft unter dem Zwerchfell.")
check("l) Leistung ohne Vorlage („?“): kein Zwang, kein falscher Hinweis, wenn die Region diktiert ist", h == [], str(h))

# v3.13.1 (Peter 14.10.: CAS BWS + LWS, Diktat ohne Satzzeichen → BWS fiel still weg, EOL übergab nur die LWS)
BWS = L("x-bws", "BWS", "Röntgen", "brustwirbelsäule_in_2_ebenen")
for d, soll in [
    ("BWS Röntgen unauffällig LWS Röntgen hyperlordose, ansonsten unauffällig",
     ["BWS Röntgen unauffällig", "LWS Röntgen hyperlordose, ansonsten unauffällig"]),
    ("BWS unauffällig Röntgen LWS Hyperlordose", ["BWS unauffällig", "Röntgen LWS Hyperlordose"]),
    ("LWS Skoliose mit Scheitel thorakolumbal, BWS unauffällig",
     ["LWS Skoliose mit Scheitel thorakolumbal", "BWS unauffällig"]),
]:
    segs, w, h = wahlen([BWS, LWS], d)
    check(f"n) ohne Satzzeichen im Satz geteilt: {d[:40]}…", segs == soll and h == []
          and {x.vorlage for x in w} == {"brustwirbelsäule_in_2_ebenen", "lendenwirbelsäule_in_2_ebenen"}, f"{segs} {h}")
for d in ["LWS Hyperlordose, Spondylose bis in die BWS reichend", "LWS Hyperlordose, BWS-Kyphose",
          "BWS LWS unauffällig", "BWS und LWS unauffällig"]:
    segs, w, h = wahlen([BWS, LWS], d)
    check(f"o) Rückbezug/Kompositum/Aufzählung trennt nicht, aber Hinweis statt still: {d}", len(segs) == 1
          and h == ["BWS: im Diktat genannt, aber KEIN eigener Befund – bitte prüfen"], f"{segs} {h}")
segs, w, h = wahlen([HWS, SOSUR], "HWS Osteochondrose C5/6 Sonographie der rechten Schulter Bursitis subacromialis")
check("p) Vorspann „Sonographie der rechten“ gehört zum neuen Abschnitt",
      segs == ["HWS Osteochondrose C5/6", "Sonographie der rechten Schulter Bursitis subacromialis"]
      and [x.vorlage for x in w] == ["halswirbelsäule_in_2_ebenen", "sonografie_schultergelenk"], f"{segs}")
segs, w, h = wahlen([HWS, LWS], "HWS Osteochondrose C5/6, Ausstrahlung in die LWS nicht erkennbar")
check("q) „in die LWS“ ist kein neuer Abschnitt", len(segs) == 1, f"{segs}")
segs, w, h = wahlen([CSU], "CT der rechten Schulter: Mehrfragmentfraktur des Humeruskopfes.")
check("m) CT Schulter (keine CT-Vorlage) + Diktat „CT …“ → allgemein (Titel aus dem Diktat) statt Röntgen-Schulter",
      w[0].vorlage == "allgemein" and h == [], f"{w[0]} {h}")
segs, w, h = wahlen([HWS, SOSUR], "Schulter rechts: Bursitis subacromialis. HWS: Steilstellung. Nochmals zur Schulter: "
                                  "kein Erguss.")
check("n) Rückbezug teilt nicht erneut (Reihenfolge wie diktiert)", len(segs) == 2
      and segs[1].startswith("HWS") and "Nochmals zur Schulter" in segs[1], str(segs))

# v3.16.5: Untersuchung am Abschnittsanfang = CAS-Leistung → deren Vorlage (Befundwort weiter hinten zählt nicht)
HANDL = L("x-hand-li", "Hand inkl.Mittelhand li.", "Röntgen", "hand_in_2_ebenen", "links")
KNIER = L("x-knie-re", "Kniegelenk rechts", "Röntgen", "kniegelenk_in_2_ebenen", "rechts")
for leist, diktat, soll, art in (
        (HANDL, "Hand in zwei Ebenen. Regelrechte Stellung, keine Fraktur. Geringe Arthrose der Fingerendgelenke. "
                "Ergebnis: Geringe Polyarthrose der Fingerendgelenke.", "hand_in_2_ebenen", "kopf"),
        (HANDL, "Daumen links in zwei Ebenen. Keine Fraktur.", "finger_in_2_ebenen", "bestaetigt"),
        (KNIER, "Knie-TEP rechts in zwei Ebenen. Regelrechter Sitz der Prothese.", "knieprothese", "bestaetigt"),
        (KNIER, "Kniegelenk rechts in zwei Ebenen. Kleine Osteophyten.", "kniegelenk_in_2_ebenen", "bestaetigt")):
    _, w, _ = wahlen([leist], diktat)
    check(f"v3.16.5 Anfang des Abschnitts entscheidet: {diktat[:28]}… → {soll}",
          [x.vorlage for x in w] == [soll] and w[0].art == art, [(x.vorlage, x.art) for x in w])

# ───────────────────────────── Teil 2: Pipeline mit CAS ─────────────────────────────
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")


def kontext(cas, prompts):
    def llm(p):
        prompts.append(p)
        titel = p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0]
        return f"## {titel}\n\n## Befund\nBeschreibung laut Diktat, ausreichend lang für den Test.\n\n## Ergebnis\nBefund."
    return pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=llm, log=lambda *a: None, cas=cas)


prompts = []
erg = pl.befund_aus_diktat("Fuß links: Hallux valgus. LWS: Osteochondrose L4/5.",
                           kontext(cv.CasHinweis([FUSSL, LWS], T), prompts))
titel = [z[3:] for z in erg.report.splitlines() if z.startswith("## ") and z[3:] not in ("Befund", "Ergebnis")]
check("Pipeline d): zwei Befunde mit kanonischen Titeln in Diktat-Reihenfolge, Vorlagen je Abschnitt",
      titel == ["Fuß in 2 Ebenen", "Lendenwirbelsäule in 2 Ebenen"] and erg.vorlagen == ["fuß_in_2_ebenen",
                                                                                       "lendenwirbelsäule_in_2_ebenen"]
      and erg.cas_hinweise == [] and erg.vollstaendig, f"{titel} {erg.vorlagen}")
check("… Gen-Prompt mit <cas_untersuchungen> (Liste + Regeln „keine erfinden“)", len(prompts) == 2 and all(
    "<cas_untersuchungen>" in p and "- Fuß links – Vorlage: Fuß in 2 Ebenen" in p and "keine Untersuchung und keinen "
    "Befund erfinden" in p and "nicht diktierte CAS-Untersuchung bekommt keinen Abschnitt" in p for p in prompts))
prompts = []
erg = pl.befund_aus_diktat("Unauffällig.", kontext(cv.CasHinweis([HWS], T), prompts))
check("Pipeline b): „Unauffällig.“ + CAS HWS → Normalbefund HWS aus der Vorlage (ohne Gemini)",
      prompts == [] and erg.report.startswith("## Halswirbelsäule in 2 Ebenen") and "Lordose" in erg.report, erg.report[:80])
erg = pl.befund_aus_diktat("Unauffällig.", kontext(cv.CasHinweis([FUSSL], T), []))
check("… Seite aus CAS, wenn das Diktat keine nennt („Fuß links in 2 Ebenen“)",
      erg.report.startswith("## Fuß links in 2 Ebenen"), erg.report[:60])
prompts = []
erg = pl.befund_aus_diktat("Schulter rechts: Omarthrose.", kontext(cv.CasHinweis([HWS], T), prompts))
check("Pipeline c): Diktat gewinnt, Hinweise im Ergebnis (nicht im Befundtext)",
      erg.vorlagen == ["schultergelenk_in_2_ebenen"] and erg.cas_hinweise == [
          "Schultergelenk in 2 Ebenen: nicht in den CAS-Leistungen", "HWS laut CAS, nicht diktiert"]
      and "CAS" not in erg.report)
prompts = []
erg = pl.befund_aus_diktat("HWS: Steilstellung. Schulter rechts: Bursitis subacromialis.",
                           kontext(cv.CasHinweis([HWS, SOSUR], T), prompts))
check("Pipeline f): HWS Röntgen + Schulter Sono → zwei Befunde, Schulter mit Sono-Titel",
      [p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0] for p in prompts]
      == ["Halswirbelsäule in 2 Ebenen", "Sonographie des Schultergelenkes"], str(erg.vorlagen))

# v3.15.4 (Peter 15.10., Ordi-Probelauf: Leistung „Handgelenk bds.“, Diktat „SL-Spalt links, ansonsten unauffällig“ →
# 1. Versuch nur „Handgelenk links in 2 Ebenen“): beidseitige CAS-Leistung → IMMER beidseitiger Befund (deterministisch)
def kontext_seite(cas, prompts, seite_im_titel="links"):
    def llm(p):
        prompts.append(p)
        titel = p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0]
        t = pl.br.titel_mit_seite(titel, seite_im_titel)          # die KI nimmt (fälschlich) die diktierte Seite
        return (f"## {t}\n\n## Befund\nLinks pathologisch, rechts unauffällig, ausreichend lang für den Test.\n\n"
                "## Ergebnis\n1. Befund links.")
    return pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=llm, log=lambda *a: None, cas=cas)


BDS = [("Handgelenk", "handgelenk_in_2_ebenen", "Handgelenk bds.", "beidseits",
        "SL-Spalt links erweitert, ansonsten unauffällig", "Handgelenk beidseits in 2 Ebenen"),
       ("Knie", "kniegelenk_in_2_ebenen", "Knie bds.", "beidseits",
        "Knie links geringgradige Gonarthrose, ansonsten unauffällig", "Kniegelenk beidseits in 2 Ebenen"),
       ("Hüfte", "hüftgelenk_in_2_ebenen", "Hüfte beidseits", "beidseits",
        "Hüfte rechts mäßiggradige Coxarthrose", "Hüftgelenk beidseits in 2 Ebenen"),
       ("Schulter (Text „bilateral“, Brücke ohne Seite)", "schultergelenk_in_2_ebenen", "Schulter bilateral", None,
        "Schulter links Tendinosis calcarea", "Schultergelenk beidseits in 2 Ebenen"),
       ("Fuß", "fuß_in_2_ebenen", "Fuß bds.", "beidseits", "Fuß rechts Hallux valgus", "Fuß beidseits in 2 Ebenen")]
for name, key, text, seite, diktat, soll in BDS:
    prompts = []
    erg = pl.befund_aus_diktat(diktat, kontext_seite(cv.CasHinweis([L("x", text, "Röntgen", key, seite)], T), prompts))
    titel = erg.report.splitlines()[0]
    check(f"beidseits laut CAS – {name}: „{soll}“ (die KI schrieb die diktierte Seite), Prompt mit <cas_beidseits>, Hinweis",
          titel == "## " + soll and len(prompts) == 1 and "<cas_beidseits>" in prompts[0] and "„" + text + "“ ist BEIDSEITS"
          in prompts[0] and any("Befund beidseits" in h for h in erg.cas_hinweise), f"{titel} {erg.cas_hinweise}")
erg = pl.befund_aus_diktat("Handgelenk links unauffällig", kontext_seite(cv.CasHinweis([L("x", "Handgelenk bds.", "Röntgen",
                           "handgelenk_in_2_ebenen", "beidseits")], T), []))
check("beidseits laut CAS, Normalbefund (ohne KI): „Handgelenk beidseits in 2 Ebenen“, Ergebnis „… beidseits.“",
      erg.report.startswith("## Handgelenk beidseits in 2 Ebenen") and "beidseits." in erg.report.split("## Ergebnis")[1],
      erg.report)
prompts = []
erg = pl.befund_aus_diktat("SL-Spalt links erweitert, ansonsten unauffällig", kontext_seite(cv.CasHinweis([L(
    "x", "Handgelenk li.", "Röntgen", "handgelenk_in_2_ebenen", "links")], T), prompts))
check("Gegenprobe: Leistung einseitig (links) + Diktat links → bleibt einseitig, kein <cas_beidseits>",
      erg.report.startswith("## Handgelenk links in 2 Ebenen") and not any("<cas_beidseits>" in p for p in prompts),
      erg.report[:60])
for text, key in (("Beckenübersicht bds.", "beckenübersicht_stehend"), ("LWS beidseits", "lendenwirbelsäule_in_2_ebenen")):
    erg = pl.befund_aus_diktat("unauffällig", kontext_seite(cv.CasHinweis([L("x", text, "Röntgen", key, "beidseits")], T), []))
    check(f"Gegenprobe: unpaarige Region ({text}) bekommt nie „beidseits“", "beidseits" not in erg.report.splitlines()[0],
          erg.report.splitlines()[0])
check("Titel: Seite ersetzt bzw. ergänzt", [cv.titel_beidseits(t) for t in ("Handgelenk links in 2 Ebenen",
      "Sonographie des Schultergelenkes rechts", "Hüftgelenk re. in 2 Ebenen", "Kniegelenk in 2 Ebenen",
      "Fuß beidseits in 2 Ebenen")] == ["Handgelenk beidseits in 2 Ebenen", "Sonographie des Schultergelenkes beidseits",
      "Hüftgelenk beidseits in 2 Ebenen", "Kniegelenk beidseits in 2 Ebenen", "Fuß beidseits in 2 Ebenen"],
      str([cv.titel_beidseits(t) for t in ("Handgelenk links in 2 Ebenen", "Sonographie des Schultergelenkes rechts",
                                            "Hüftgelenk re. in 2 Ebenen", "Kniegelenk in 2 Ebenen")]))

# keine CAS-Datei: bit-gleich wie bisher (CAS-Funktionen werden gar nicht aufgerufen)
gesperrt = {}
for name in ("aufteilen", "wahl", "hinweise", "prompt_block", "CasHinweis"):
    gesperrt[name] = getattr(cv, name)
    setattr(cv, name, lambda *a, n=name, **k: (_ for _ in ()).throw(AssertionError(f"cas_vorlagen.{n} ohne CAS")))
try:
    ok = True
    for diktat in ("Knie rechts unauffällig.", "Schulter rechts: Omarthrose. Ellbogen rechts: Epicondylitis.",
                   "HWS: Osteochondrose C5/6, sonst unauffällig.", "Unauffällig.", "Rho 8. LWS: Osteochondrose."):
        alt, neu = [], []
        e1 = pl.befund_aus_diktat(diktat, kontext(None, neu))
        # Referenz: dieselben Schritte wie bis v3.11.0 (split_regionen → detect_template → gen_prompt ohne CAS-Block)
        for seg in pl.br.split_regionen(diktat):
            seg_ohne = pl.br.rho_erkennen(seg)[0]
            key = detect.detect_template(seg_ohne, T)
            if not pl.ist_normalbefund(seg_ohne, key, DISPLAY):
                # v3.15.5: diktierte umschriebene Befunde → <widersprueche> an der Stelle {examples} (wie ohne CAS)
                alt.append(pl.gen_prompt(seg_ohne, T[key], PROMPT, "", pl.br.widerspruch_prompt(
                    pl.br.widerspruch_befunde(seg_ohne), T[key]["body"])))
        ok = (ok and sorted(alt) == sorted(neu)       # Regionen laufen parallel → Reihenfolge der KI-Aufrufe nicht fest
              and e1.cas_hinweise == [] and e1.vorlagen == [] and not any("cas_untersuchungen" in p for p in neu))
    check("ohne CAS-Datei: Prompts bit-gleich mit dem bisherigen Weg, keine CAS-Funktion aufgerufen", ok)
finally:
    for name, f in gesperrt.items():
        setattr(cv, name, f)
check("leere Leistungsliste = keine CAS-Datei", not cv.CasHinweis([], T) and not cv.CasHinweis([KOORD], T))

# ───────────────────────────── Teil 3: EXE-Ablauf ─────────────────────────────
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: False
cas_mod = mod._cas
ORDNER = tempfile.mkdtemp(prefix="rks_casl_")
LLM_PROMPTS = []


def llm_attrappe(p):
    LLM_PROMPTS.append(p)
    titel = p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0]
    return f"## {titel}\n\n## Befund\nBeschreibung laut Diktat, ausreichend lang für den Test.\n\n## Ergebnis\nBefund."


mod._llm_aufruf = llm_attrappe


def ablegen(nr, aid):
    with open(os.path.join(ORDNER, cas_mod.AUFTRAG), "w", encoding="utf-8") as f:
        json.dump({"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": "kp", "bruecke_pid": 4242,
                   "zeit": time.time(), "zeit_text": "", "testbefund": False}, f)


def leistungen_ablegen(aid, nr, leistungen, roh=None):
    p = os.path.join(ORDNER, f"cas_leistungen_{aid}.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write(roh if roh is not None else json.dumps(
            {"protokoll": 1, "auftrag_id": aid, "nr": nr, "roh": "Untersuchung: …", "leistungen": leistungen,
             "quelle": "CASSpeechMagic.DBModule.GetExaminationsText", "katalog": "Test", "ms": 2700, "zeit": time.time()},
            ensure_ascii=False))


def antwort(aid):
    try:
        with open(os.path.join(ORDNER, f"cas_antwort_{aid}.json"), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


class FakeBand:
    def __init__(self):
        self.sichtbar = False

    def pack(self, **k):
        self.sichtbar = True

    def pack_forget(self):
        self.sichtbar = False

    def winfo_ismapped(self):
        return self.sichtbar


def neue_app():
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
    S.CLIPBOARD.data = {13: "ALT"}
    app = S.baue_app(mod)
    app._cas, app._cas_aufnahmen, app._cas_test = None, [], False
    app._cas_kanal = cas_mod.Kanal(ORDNER, pid=777, version="3.12.0", prozess_lebt=lambda pid: True)
    app._fensterziel = mod._fz.Fensterziel(None)
    app.cas_label, app.cas_hinweis_label, app.bestaetigung_label = S.FakeWidget(), S.FakeWidget(), S.FakeWidget()
    app.cas_band, app.bestaetigung_band, app.main_container = FakeBand(), FakeBand(), None
    app.destroy = lambda: None
    return app


def bis_ruhe(app, timeout=8):
    ok = S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)
    S.pump(app, lambda: False, 0.2)
    return ok


app = neue_app()
ablegen("20261014003", "x1")
app._cas_einmal()
check("Auftrag ohne Leistungen: Band wie bisher", app._cas is not None and app._cas.leistungen is None
      and app.cas_label.cget("text") == "●  CAS-Diktat 20261014003 (kp)   ·   EOL schickt den Befund an CAS",
      app.cas_label.cget("text"))
leistungen_ablegen("x1", "20261014003", [HWS], roh='{"auftrag_id": "x1", "le')
app._cas_einmal()
check("halb geschriebene Leistungen-Datei → nächster Takt", app._cas.leistungen is None)
leistungen_ablegen("x1", "20261014003", [KOORD, HWS, SOSUR])
app._cas_einmal()
check("Leistungen kommen nach: Band „… · HWS · Schulter re. (Sono)“ (Abrechnungsposten nicht)",
      app.cas_label.cget("text") == "●  CAS-Diktat 20261014003 (kp) · HWS · Schulter re. (Sono)", app.cas_label.cget("text"))
app.transcript_text.text = "HWS: Steilstellung. Schulter rechts: Bursitis subacromialis."
app.befund_aus_text(kontrolle=True)
bis_ruhe(app)
check("Befund aus Text mit CAS: zwei Befunde (HWS Röntgen, Schulter Sono), zur Kontrolle, nichts eingefügt",
      "## Halswirbelsäule in 2 Ebenen" in app.result_text.text and "## Sonographie des Schultergelenkes" in app.result_text.text
      and app._status_raw == "KONTROLLE" and S.AUFZ.tasten == [], app.result_text.text[:120])
check("… Gen-Prompt bekam die CAS-Untersuchungen", LLM_PROMPTS and all("<cas_untersuchungen>" in p for p in LLM_PROMPTS))
app.befund_fertig()
check("EOL: an CAS, grüne Bestätigung mit Nummer und Titeln (Band sichtbar, CAS-Band weg)",
      antwort("x1").get("status") == "fertig" and app.bestaetigung_band.sichtbar and not app.cas_band.sichtbar
      and app._bestaetigung_text == "✓  An CAS übergeben: 20261014003  ·  Halswirbelsäule in 2 Ebenen · Sonographie des "
                                    "Schultergelenkes" and app.bestaetigung_label.cget("text") == app._bestaetigung_text,
      getattr(app, "_bestaetigung_text", ""))

ablegen("20261014004", "x2")
app._cas_einmal()
leistungen_ablegen("x2", "20261014004", [HWS])
app._cas_einmal()
check("neuer Auftrag: Bestätigung weg, eigene Leistungen", app._bestaetigung_text == "" and app._cas.labels() == ["HWS"]
      and not app.bestaetigung_band.sichtbar and app.cas_band.sichtbar)
LLM_PROMPTS.clear()
app.transcript_text.text = "Schulter rechts: Omarthrose."
app.befund_aus_text(kontrolle=True)
bis_ruhe(app)
check("Diktat widerspricht CAS → Hinweise im Band (amber), Befund nach Diktat",
      app.cas_hinweis_label.cget("text") == "⚠  Schultergelenk in 2 Ebenen: nicht in den CAS-Leistungen  ·  HWS laut CAS, "
                                            "nicht diktiert" and "## Schultergelenk" in app.result_text.text,
      app.cas_hinweis_label.cget("text"))
app.reset_dictation()
check("F9 leert die Hinweise (Auftrag bleibt)", app.cas_hinweis_label.cget("text") == "" and app._cas is not None)
app.cas_abbrechen()

ablegen("20261014005", "x3")
app._cas_einmal()
leistungen_ablegen("x3", "20261014999", [HWS])     # andere Diktatnummer
app._cas_einmal()
check("Leistungen zu anderer Diktatnummer werden verworfen", app._cas.leistungen == [] and app._cas.labels() == [])
app.cas_abbrechen()

ablegen("20261014006", "x4")
app._cas_einmal()
LLM_PROMPTS.clear()
app.transcript_text.text = "Knie rechts unauffällig."
app.befund_aus_text(kontrolle=True)
bis_ruhe(app)
check("ohne Leistungen-Datei: Befund wie bisher, keine Hinweise", app.result_text.text.startswith("## Kniegelenk")
      and getattr(app, "_cas_hinweise", []) == [])
app.cas_abbrechen()

# ───────────────────────────── Teil 4: gegen die echte Brückenseite (nur Mac) ─────────────────────────────
BR = pathlib.Path.home() / "dev" / "ris-mods" / "bruecke"
if (BR / "leistungen.py").exists():
    sys.path.insert(0, str(BR))
    import auftrag as br_auftrag  # noqa: E402
    import leistungen as br_l  # noqa: E402
    katalog = br_l.katalog_laden([str(BR.parent / "katalog" / "leistungskatalog_kuerzel.tsv")])
    zuordnung = br_l.zuordnung_lesen(str(BR.parent / "katalog" / "kuerzel_vorlage.tsv"))
    # echte Praxis-Kürzel nur zur Laufzeit aus dem privaten Repo (nie hier im öffentlichen Code)
    zeilen = [z.rstrip("\n").split("\t") for z in open(BR.parent / "katalog" / "kuerzel_vorlage.tsv", encoding="utf-8")][1:]
    k_hws = next(z[0] for z in zeilen if z[3] == "halswirbelsäule_in_2_ebenen" and z[1] == "HWS")
    k_schulter = next(z[0] for z in zeilen if z[3] == "sonografie_schultergelenk" and z[1].endswith("re."))
    k_ohne = next(z[0] for z in zeilen if z[3] == "-" and z[1] and not z[1][0].isdigit())
    roh = f"Untersuchung: {k_hws}, {k_schulter}, {k_ohne}"
    liste = br_l.aufloesen(br_l.zerlegen(roh, katalog), katalog, zuordnung)
    kanal = br_auftrag.Kanal(ORDNER, pid=4242)
    kanal.leistungen_senden("y1", br_l.datei_inhalt("y1", "20261014007", roh, liste, 2712, katalog.quelle))
    a = cas_mod.Auftrag({"auftrag_id": "y1", "nr": "20261014007"})
    a.leistungen = cas_mod.Kanal(ORDNER).leistungen_lesen(a)
    h = cv.CasHinweis(a.leistungen, T)
    check("Protokoll gegen bruecke/leistungen.py: Band „HWS · Schulter re. (Sono)“, Vorlagen gültig",
          a.labels() == ["HWS", "Schulter re. (Sono)"] and [l.vorlage for l in h.mit_vorlage]
          == ["halswirbelsäule_in_2_ebenen", "sonografie_schultergelenk"], f"{a.labels()} {h.alle}")
    kanal.aufraeumen("y1", "20261014007")
    check("… Brücke räumt die Leistungen-Datei auf", not os.path.exists(os.path.join(ORDNER, "cas_leistungen_y1.json")))
else:
    print("(Teil 4 übersprungen: ~/dev/ris-mods/bruecke nicht vorhanden)")

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
