"""Gate IB Lab KOALA → Kniebefund nach der K&L-Tabelle (Georg Riegler 18.11.2026, GO, Brief kaiscribe-kl-tabelle-zurueck-n1).
Abnahme-Fixtures Nr. 34 und Nr. 50 (Wortlaut von Georg freigegeben) – deterministisch in ibl_bausteine (nach der KI) und
durch die ganze EXE-Kette (pipeline.befund_aus_diktat mit KI-Attrappe, alle Wächter danach). Dazu: KL 3 rechts (Brief
Punkt 4), Kompartiment lateral, KL 0/1, Alter < 18, Prothese, seitliches Bild, mehrere a.p.-Bilder mit verschiedenen
Graden, diktierte Gonarthrose (Diktat geht vor), Normal-Ergebnis ersetzt, zweimal einsetzen, Patella axial, Gerüst,
Gen-Prompt. Synthetische Werte, keine Patientendaten.  Aufruf: python3 tests/offline/test_ibl_koala_text.py"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import ibl_bausteine as I  # noqa: E402

I.KOALA_KNIE_AUTOMATIK = True   # Punkt 61: der alte KOALA-Weg bleibt hinter dem Schalter geprüft (live AUS)
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def koala(seiten, befundteil, ergebnis=(), **kw):
    d = {"accno": "T-0034", "ziffer": 1, "modul": "koala", "name": "KOALA", "modul_name": "IB Lab KOALA", "version": 1,
         "seiten": list(seiten), "befundteil": list(befundteil), "ergebnis": list(ergebnis), "hinweise": [],
         "nicht_zugeordnet": []}
    d.update(kw)
    return I.aus_liste([d])


def zeilen(seite, kl, med=None, lat=None):
    s = f" {seite}" if seite else ""
    out = [f"Kellgren-Lawrence-Grad{s} {kl} (IB Lab KOALA)."]
    if med is not None:
        out.append(f"Minimale Gelenkspaltweite medial{s} {med} mm (IB Lab KOALA).")
    if lat is not None:
        out.append(f"Minimale Gelenkspaltweite lateral{s} {lat} mm (IB Lab KOALA).")
    return out


def bericht(titel, befund, ergebnis):
    return f"## {titel}\n\n## Befund\n{befund}\n\n## Ergebnis\n{ergebnis}"


VORLAGE = T["kniegelenk_in_2_ebenen"]["body"].split("\n", 2)[2]
FP3 = "Femoropatellar mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler Sklerosierung."
ERGUSS = "Geringer Gelenkerguss. Ansonsten unauffällige Weichteile."


def ki_text(fp=FP3, erguss=ERGUSS, vorlage=VORLAGE):
    """So soll die KI nach dem Prompt schreiben: Vorlage wörtlich, Femoropatellar-Satz hinter dem Gelenkspalt-Satz, Erguss
    am Ende (der femorotibiale Teil kommt von KaiScribe)."""
    t = vorlage.replace("Kein Hinweis auf freie Gelenkkörper.", f"{fp} Kein Hinweis auf freie Gelenkkörper.") if fp else vorlage
    return t.replace("Unauffällige Weichteile.", erguss) if erguss else t


# ───────────────────────────── Nr. 34 (66 m, KL 3 links, medial 3,5 / lateral 6,1 mm) ─────────────────────────────
NR34_BEFUND = ("Normale Stellung der dargestellten Skelettabschnitte. Patella in regelrechter Position. Mineralgehalt und "
               "Knochenstruktur sind regelrecht. Glatte und scharfe Kontur der Kortikalis ohne pathologische "
               "Konturunterbrechung. Normale Breite der Kompakta. Medial mäßiggradige Gelenksspaltverschmälerung mit "
               "multiplen Osteophyten und subchondraler Sklerosierung. Lateral normal weiter Gelenkspalt. Femoropatellar "
               "mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler Sklerosierung. Kein "
               "Hinweis auf freie Gelenkkörper. Keine intra- oder periartikulären Verkalkungen. Geringer Gelenkerguss. "
               "Ansonsten unauffällige Weichteile.")
NR34_ERGEBNIS = ("1. Mäßiggradige Gonarthrose links medial (Arthrose Grad 3 nach Kellgren & Lawrence).\n"
                 "2. Mäßiggradige Femoropatellararthrose links (Arthrose Grad 3 nach Kellgren & Lawrence).\n"
                 "3. Geringer Gelenkerguss links.")
NR34_DIKTAT = "Knie links. Mäßige patellofemorale Arthrose, geringer Gelenkserguss."
K34 = koala(["links"], zeilen("links", 3, "3,50", "6,10"), ["Mittelgradige Gonarthrose links (Kellgren-Lawrence-Grad 3)."],
            alter=66)
KI34 = bericht("Kniegelenk links in 2 Ebenen", ki_text(),
               "1. Mäßiggradige Femoropatellararthrose links (Arthrose Grad 3 nach Kellgren & Lawrence).\n"
               "2. Geringer Gelenkerguss links.")
e = I.einsetzen(KI34, K34, diktat=NR34_DIKTAT)
check("Nr. 34: Befund und Ergebnis wörtlich wie von Georg freigegeben",
      e.report == bericht("Kniegelenk links in 2 Ebenen", NR34_BEFUND, NR34_ERGEBNIS) and not e.hinweise,
      e.report + "\n" + str(e.hinweise))
check("Nr. 34: keine mm-Werte, keine Messzeile, kein „betont“, Abholer-Punkt „Mittelgradige …“ nicht übernommen",
      " mm" not in e.report and "IB Lab KOALA" not in e.report and "betont" not in e.report
      and "Mittelgradige" not in e.report, e.report)
# KI hat (alte Arthrose-Regel) „Normale Form und Stellung …“ gestrichen und „im Übrigen“ geschrieben → gleiches Ergebnis
ki_alt = ki_text().replace("Normale Form und Stellung der dargestellten Skelettabschnitte. ", "") \
    .replace("Der Gelenkspalt ist allseits normal weit.", "Der Gelenkspalt ist im Übrigen normal weit.")
e = I.einsetzen(bericht("Kniegelenk links in 2 Ebenen", ki_alt, "1. Mäßiggradige Femoropatellararthrose links (Arthrose "
                        "Grad 3 nach Kellgren & Lawrence).\n2. Geringer Gelenkerguss links."), K34, diktat=NR34_DIKTAT)
check("Nr. 34, KI-Variante (Stellungssatz gestrichen, „im Übrigen normal weit“): trotzdem Georgs Wortlaut",
      e.report == bericht("Kniegelenk links in 2 Ebenen", NR34_BEFUND, NR34_ERGEBNIS), e.report)
# Live-Läufe 18.11. (Sonnet 5.5): „Normale Stellung … beidseits.“ bzw. diktierte Wortwahl „Mäßige patellofemorale Arthrose“
ki_live = bericht("Kniegelenk links in 2 Ebenen", ki_text().replace("Normale Form und Stellung der dargestellten "
                  "Skelettabschnitte.", "Normale Stellung der dargestellten Skelettabschnitte links."),
                  "1. Mäßige patellofemorale Arthrose links (Arthrose Grad 3 nach Kellgren & Lawrence).\n"
                  "2. Geringer Gelenkerguss links.")
e3 = I.einsetzen(ki_live, K34, diktat=NR34_DIKTAT)
check("Nr. 34, KI-Wortwahl aus den Live-Läufen: Stellungssatz ohne Seite, „Mäßiggradige Femoropatellararthrose links …“",
      e3.report == bericht("Kniegelenk links in 2 Ebenen", NR34_BEFUND, NR34_ERGEBNIS), e3.report)
# Live 18.11. #2: Femoropatellar-Satz VOR „Der Gelenkspalt ist im Übrigen allseits normal weit.“ (KI)
ki_vor = bericht("Kniegelenk links in 2 Ebenen", ki_text(fp="").replace("Der Gelenkspalt ist allseits normal weit.",
                 FP3 + " Der Gelenkspalt ist im Übrigen allseits normal weit."),
                 "1. Mäßiggradige Femoropatellararthrose links (Arthrose Grad 3 nach Kellgren & Lawrence).\n"
                 "2. Geringer Gelenkerguss links.")
e4 = I.einsetzen(ki_vor, K34, diktat=NR34_DIKTAT)
check("Nr. 34, Femoropatellar vor dem Gelenkspalt-Satz („im Übrigen allseits“): Reihenfolge Medial – Lateral – Femoropatellar",
      e4.report == bericht("Kniegelenk links in 2 Ebenen", NR34_BEFUND, NR34_ERGEBNIS), e4.report)
# Live 18.11. #3/#5: Weichteilsatz als eigener Absatz, „Im Übrigen sind die Gelenkflächen …“
ki_abs = bericht("Kniegelenk links in 2 Ebenen", ki_text().replace(" " + ERGUSS, "\n\n" + ERGUSS).replace(
    "Die Gelenkflächen sind normal geformt und kongruent.", "Im Übrigen sind die Gelenkflächen normal geformt und kongruent."),
    "1. Mäßiggradige Femoropatellararthrose links (Arthrose Grad 3 nach Kellgren & Lawrence).\n2. Geringer Gelenkerguss links.")
e5 = I.einsetzen(ki_abs, K34, diktat=NR34_DIKTAT)
check("Nr. 34, Weichteilsatz als eigener Absatz + „Im Übrigen sind die Gelenkflächen …“: Georgs Wortlaut (ein Absatz)",
      e5.report == bericht("Kniegelenk links in 2 Ebenen", NR34_BEFUND, NR34_ERGEBNIS), e5.report)
e2 = I.einsetzen(e.report, K34, diktat=NR34_DIKTAT)
check("Nr. 34: zweimal eingesetzt (Knopf „IB Lab einfügen“) → unverändert, nichts doppelt", e2.report == e.report, e2.report)

# ───────────────────────────── Nr. 50 (68 w, KL 2 beidseits, medial 4,7 / lateral 6,1 bzw. 6,3) ─────────────────────────────
NR50_FT = ("Beidseits medial geringe Osteophytenbildung mit geringer Gelenksspaltverschmälerung und geringer "
           "Randzuschärfung. Lateral beidseits normal weiter Gelenkspalt.")
NR50_FP = ("Femoropatellar beidseits mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler "
           "Sklerosierung.")
NR50_ERGEBNIS = ("1. Geringgradige Gonarthrose beidseits medial (Arthrose Grad 2 nach Kellgren & Lawrence).\n"
                 "2. Mäßiggradige Femoropatellararthrose beidseits (Arthrose Grad 3 nach Kellgren & Lawrence).\n"
                 "3. Geringer Gelenkerguss beidseits.")
NR50_DIKTAT = "Knie beidseits. Mäßige patellofemorale Arthrose beidseits, geringer Gelenkserguss beidseits."
K50 = koala(["rechts", "links"], zeilen("rechts", 2, "4,70", "6,10") + zeilen("links", 2, "4,70", "6,30"),
            ["Geringgradige Gonarthrose beidseits (Kellgren-Lawrence-Grad 2)."], alter=68)
KI50 = bericht("Kniegelenk beidseits in 2 Ebenen", ki_text(fp=NR50_FP),
               "1. Mäßiggradige Femoropatellararthrose beidseits (Arthrose Grad 3 nach Kellgren & Lawrence).\n"
               "2. Geringer Gelenkerguss beidseits.")
e = I.einsetzen(KI50, K50, diktat=NR50_DIKTAT)
befund50 = NR34_BEFUND.replace("Medial mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler "
                               "Sklerosierung. Lateral normal weiter Gelenkspalt. " + FP3, NR50_FT + " " + NR50_FP)
check("Nr. 50: „Beidseits medial …“, „Lateral beidseits …“, Femoropatellar Grad 3 neben KOALA Grad 2, Ergebnis zusammengefasst",
      e.report == bericht("Kniegelenk beidseits in 2 Ebenen", befund50, NR50_ERGEBNIS), e.report)

# ───────────────────────────── ganze EXE-Kette (KI-Attrappe, alle Wächter danach) ─────────────────────────────


def kette(diktat, bausteine, ki_befund, ki_ergebnis):
    prompts = []

    def llm(p):
        prompts.append(p)
        titel = p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0]
        seite = br.diktierte_seite(diktat)
        return bericht(titel.replace(" in ", f" {seite} in ", 1), ki_befund, ki_ergebnis)
    ctx = pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=llm, log=lambda *a: None,
                     ibl=I.IblKontext(bausteine))
    return pl.befund_aus_diktat(diktat, ctx), prompts


ki_bds = bericht("Kniegelenk beidseits in 2 Ebenen", ki_text(fp="").replace("Der Gelenkspalt ist allseits normal weit.",
                 NR50_FP.replace("Femoropatellar beidseits", "Beidseits femoropatellar") + " Der Gelenkspalt ist allseits "
                 "normal weit."), "1. Mäßiggradige Femoropatellararthrose beidseits (Arthrose Grad 3 nach Kellgren & "
                 "Lawrence).\n2. Geringer Gelenkerguss beidseits.")
for var in ("Der Gelenkspalt ist femorotibial allseits normal weit.", "Im Übrigen ist der Gelenkspalt femorotibial allseits "
            "normal weit.", "Ansonsten ist der Gelenkspalt beidseits normal weit."):
    e = I.einsetzen(ki_bds.replace("Der Gelenkspalt ist allseits normal weit.", var), K50, diktat=NR50_DIKTAT)
    check(f"Nr. 50, KI-Variante „{var}“ wird ersetzt",
          e.report == bericht("Kniegelenk beidseits in 2 Ebenen", befund50, NR50_ERGEBNIS), e.report)
e = I.einsetzen(ki_bds, K50, diktat=NR50_DIKTAT)
check("Nr. 50, Live-Variante „Beidseits femoropatellar …“ davor: → „Femoropatellar beidseits …“ dahinter",
      e.report == bericht("Kniegelenk beidseits in 2 Ebenen", befund50, NR50_ERGEBNIS), e.report)

erg, prompts = kette(NR34_DIKTAT, K34, ki_text(), "1. Mäßiggradige Femoropatellararthrose links (Arthrose Grad 3 nach "
                     "Kellgren & Lawrence).\n2. Geringer Gelenkerguss links.")
check("Kette Nr. 34: Gen-Prompt mit KOALA-Anweisung, ohne Messwerte und ohne „wird eingefügt“-Messzeilen",
      len(prompts) == 1 and I.KOALA_PROMPT in prompts[0] and "3,50" not in prompts[0] and "6,10" not in prompts[0]
      and "Kellgren-&-Lawrence-Grad laut IB Lab" not in prompts[0], prompts[0][-3000:] if prompts else "")
check("Kette Nr. 34: Wächter (K&L, Arthrose, Widerspruch, Abschnitte) lassen Georgs Wortlaut stehen",
      erg.report == bericht("Kniegelenk links in 2 Ebenen", NR34_BEFUND, NR34_ERGEBNIS), erg.report)
erg, prompts = kette(NR50_DIKTAT, K50, ki_text(fp=NR50_FP), "1. Mäßiggradige Femoropatellararthrose beidseits (Arthrose "
                     "Grad 3 nach Kellgren & Lawrence).\n2. Geringer Gelenkerguss beidseits.")
check("Kette Nr. 50: K&L-Wächter setzt den Femoropatellar-Grad 3 NICHT auf den KOALA-Grad 2",
      erg.report == bericht("Kniegelenk beidseits in 2 Ebenen", befund50, NR50_ERGEBNIS), erg.report)

K3R = koala(["rechts"], zeilen("rechts", 3, "2,1", "5,0"))
erg, prompts = kette("Kniegelenk rechts in zwei Ebenen. Kein Hinweis auf eine Fraktur.", K3R, VORLAGE,
                     "Regelrechte Darstellung des Kniegelenkes rechts.")
check("Kette KL 3 rechts, Diktat ohne Arthrose: Arthrose-Wächter lässt den KOALA-Punkt stehen, Normal-Ergebnis ersetzt",
      erg.report.endswith("## Ergebnis\nMäßiggradige Gonarthrose rechts medial (Arthrose Grad 3 nach Kellgren & Lawrence).")
      and "Medial mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler Sklerosierung. Lateral "
      "normal weiter Gelenkspalt." in erg.report and "Im Übrigen" not in erg.report, erg.report)
erg, prompts = kette("Knie rechts unauffällig.", K3R, VORLAGE, "Regelrechte Darstellung des Kniegelenkes rechts.")
check("Kette KL 3 rechts, Normalbefund-Diktat (ohne KI): KOALA-Text trotzdem drin",
      not prompts and "Mäßiggradige Gonarthrose rechts medial (Arthrose Grad 3 nach Kellgren & Lawrence)." in erg.report
      and "Normale Stellung der dargestellten Skelettabschnitte." in erg.report, erg.report)

# ───────────────────────────── Brief Punkt 4: KL 3 rechts ─────────────────────────────
KR = koala(["rechts"], zeilen("rechts", 3))
e = I.einsetzen(bericht("Kniegelenk rechts in 2 Ebenen", VORLAGE, "Regelrechte Darstellung des Kniegelenkes rechts."), KR,
                diktat="Knie rechts unauffällig.")
check("KL 3 rechts ohne Gelenkspaltweiten: „Mäßiggradige Gelenksspaltverschmälerung …“ ohne Kompartiment, Normal-Ergebnis "
      "ersetzt (ein Punkt, unnummeriert), Prüf-Hinweis",
      "Normale Breite der Kompakta. Mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler "
      "Sklerosierung. Kein Hinweis" in e.report
      and e.report.endswith("## Ergebnis\nMäßiggradige Gonarthrose rechts (Arthrose Grad 3 nach Kellgren & Lawrence).")
      and "Regelrechte Darstellung" not in e.report and any("Kompartiment" in h for h in e.hinweise),
      e.report + str(e.hinweise))
KRL = koala(["rechts"], zeilen("rechts", 4, "5,2", "1,9"))
e = I.einsetzen(bericht("Kniegelenk rechts in 2 Ebenen", VORLAGE, "Regelrechte Darstellung des Kniegelenkes rechts."), KRL,
                diktat="Knie rechts.")
check("KL 4 rechts, lateral enger: „Lateral aufgehobener Gelenksspalt … Zystenbildung …“, „Medial normal weiter …“",
      "Lateral aufgehobener Gelenksspalt mit ausgeprägter subchondraler Sklerosierung, Zystenbildung und ausgeprägten "
      "Osteophyten. Medial normal weiter Gelenkspalt." in e.report
      and "Hochgradige Gonarthrose rechts lateral (Arthrose Grad 4 nach Kellgren & Lawrence)." in e.report, e.report)

# ───────────────────────────── kein KOALA-Text ─────────────────────────────
NORMAL_LI = bericht("Kniegelenk links in 2 Ebenen", VORLAGE, "Regelrechte Darstellung des Kniegelenkes links.")
for kl in (0, 1):
    e = I.einsetzen(NORMAL_LI, koala(["links"], zeilen("links", kl, "4,4", "5,9")), diktat="Knie links unauffällig.")
    check(f"KL {kl}: Vorlage unverändert, kein Text, kein Hinweis", e.report == NORMAL_LI and not e.hinweise,
          e.report + str(e.hinweise))
e = I.einsetzen(NORMAL_LI, koala(["links"], zeilen("links", 3, "2,0", "5,0"), alter=16), diktat="Knie links.")
check("Alter 16: kein KOALA-Text, Hinweis", e.report == NORMAL_LI and any("unter 18" in h for h in e.hinweise), e.report)
check("Alter unbekannt (Brücke liefert keins): Text kommt", I.koala_hat_text(koala(["links"], zeilen("links", 3, "2,0", "5,0"))[0]))
PROTH = bericht("Knieprothese links", T["knieprothese"]["body"].split("\n", 2)[2], "Regelrechte Lage der Knie-TEP links.")
e = I.einsetzen(PROTH, koala(["links"], zeilen("links", 3, "2,0", "5,0")), diktat="Knie-TEP links.")
check("Prothese (Vorlage/Diktat): kein KOALA-Text", e.report == PROTH and any("Knieprothese" in h for h in e.hinweise),
      e.report + str(e.hinweise))
e = I.einsetzen(NORMAL_LI, koala(["links"], zeilen("links", 3, "2,0", "5,0")), diktat="Knie links, St. p. Knie-TEP rechts.")
check("Prothese im Diktat erwähnt: kein KOALA-Text", e.report == NORMAL_LI, e.report)
e = I.einsetzen(NORMAL_LI, koala(["links"], ["Knie seitlich links:"] + zeilen("links", 3, "2,0", "5,0")), diktat="Knie links.")
check("Werte unter „Knie seitlich links:“ zählen nie", e.report == NORMAL_LI, e.report)
ZWEI = koala(["links"], ["Knie a.p. links:"] + zeilen("links", 2, "3,0", "5,0") + ["Knie a.p. stehend links:"]
             + zeilen("links", 3, "2,5", "5,0"))
e = I.einsetzen(NORMAL_LI, ZWEI, diktat="Knie links.")
check("Zwei a.p.-Bilder links mit Grad 2 und 3: kein Text, rote Prüfzeile (⚠ … bitte am Bild prüfen)",
      e.report == NORMAL_LI and any(h.startswith("⚠") and "2, 3" in h and "am Bild prüfen" in h for h in e.hinweise),
      str(e.hinweise))
KNIE_D = bericht("Kniegelenk links in 2 Ebenen", "Mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und "
                 "subchondraler Sklerosierung.", "Mäßige Gonarthrose links (Arthrose Grad 3 nach Kellgren & Lawrence).")
e = I.einsetzen(KNIE_D, koala(["links"], zeilen("links", 2, "3,0", "5,0")), diktat="Knie links: mäßige Gonarthrose.")
check("Diktierte Gonarthrose (mäßig = 3) ≠ KOALA 2: Diktat geht vor, kein Text, Prüf-Hinweis",
      e.report == KNIE_D and any("der diktierte Grad gilt" in h for h in e.hinweise), e.report + str(e.hinweise))
e = I.einsetzen(KNIE_D, koala(["links"], zeilen("links", 3, "3,0", "5,0")), diktat="Knie links: Gonarthrose Grad 3 nach Kellgren.")
check("Diktierter Grad = KOALA-Grad: nichts doppelt", e.report == KNIE_D and any("schon diktiert" in h for h in e.hinweise),
      e.report + str(e.hinweise))
check("Femoropatellar-/Retropatellararthrose im Diktat ist keine femorotibiale Gonarthrose",
      not I._koala_gonarthrose_diktiert(NR34_DIKTAT) and not I._koala_gonarthrose_diktiert("geringgradige Retropatellararthrose")
      and I._koala_gonarthrose_diktiert("mäßige mediale Gonarthrose") and I._koala_gonarthrose_diktiert("KL 2"))

# ───────────────────────────── Patella axial, Gerüst, Gen-Prompt ─────────────────────────────
PAT = T["kniegelenk_in_2_ebenen_mit_patella_axial"]["body"].split("\n", 2)[2]
e = I.einsetzen(bericht("Kniegelenk links in 2 Ebenen mit Patella axial", PAT, "Regelrechte Darstellung des Kniegelenkes "
                        "links."), K34, diktat="Knie links mit Patella axial.")
check("Patella axial: „Femoropatellarer Gelenkspalt normal weit.“ bleibt, femorotibialer Satz an der Gelenkspalt-Stelle",
      "Femoropatellarer Gelenkspalt normal weit." in e.report and "Normale Breite der Kompakta. Medial mäßiggradige" in e.report
      and "allseits normal weit" not in e.report and "normal geformt und kongruent" not in e.report, e.report)
LEISTUNG = [{"kurz": "KNI", "text": "Knie li", "vorlage": "kniegelenk_in_2_ebenen", "seite": "links", "ziffer": 1}]
g = I.geruest(K34, LEISTUNG, T)
check("Gerüst vor dem Diktat: ganze Knie-Vorlage mit KOALA-Text + Punkt (sofort EOL = fertiger Befund)",
      g is not None and g.report == bericht("Kniegelenk links in 2 Ebenen", NR34_BEFUND.replace(" " + FP3, "")
                                            .replace(ERGUSS, "Unauffällige Weichteile."),
                                            "Mäßiggradige Gonarthrose links medial (Arthrose Grad 3 nach Kellgren & Lawrence)."),
      g.report if g else "None")
g = I.geruest(koala(["links"], zeilen("links", 1, "4,0", "5,0")), LEISTUNG, T)
check("Gerüst KL 1: keins", g is None)
blk = I.prompt_block(K34, T["kniegelenk_in_2_ebenen"]["body"], NR34_DIKTAT)
check("Gen-Prompt KL ≥ 2: KOALA-Anweisung statt Grad-Satz, kein „weglassen“ des Gelenkspalt-Satzes",
      I.KOALA_PROMPT in blk and "nicht übernehmen" not in blk and "laut IB Lab: Kellgren" not in blk, blk)
blk = I.prompt_block(K34, T["kniegelenk_in_2_ebenen"]["body"], "Knie links: mäßige Gonarthrose.")
check("Gen-Prompt bei diktierter Gonarthrose: alter Grad-Satz (Diktat geht vor), keine KOALA-Anweisung",
      I.KOALA_PROMPT not in blk and "Kellgren-&-Lawrence-Grad laut IB Lab" in blk, blk)
check("K&L-Tabelle in befund_regeln = Wortlaut im Gen-Prompt (alle Grade 0–4)",
      all(s in PROMPT for s in br.KL_TABELLE.values()))

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
