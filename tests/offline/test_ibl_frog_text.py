"""Gate v3.19.8 – IB Lab FROG: fester Fuß-Text (Georg Riegler 17.11.2026, Brief kaiscribe-frog-fusstext-n1).
Der Abholer ≥ 1.3.7 (ris-mods ibl/frog_ergebnis.py) liefert im Baustein das Feld „befundtext“: fertige Sätze für die
Beschreibung und die lateinischen Begriffe fürs Ergebnis – nur wenn mindestens eine Größe pathologisch ist. KaiScribe
setzt sie in den Standardbefund ein (ibl_bausteine.py, Abschnitt „IB Lab FROG“):
  Stellungssatz der Vorlage raus → Sätze mit Winkel und Norm; Gewölbesatz ersetzt („… regulär ausgebildet.“ ohne „bei
  ordnungsgemäßen Gelenkwinkeln“ bzw. der pathologische Satz); Vorfuß nur d.p.; Ergebnis: Begriffe als erster Punkt,
  Standardsatz weg, Diktiertes danach, Schlussanmerkung ohne Nummer; keine Messzeilen „… (IB Lab FROG).“ mehr.
Teil 1: die 10 echten (anonymen) Fälle vom 17.11.2026 + das Beispielbild – Bausteine genau so, wie die Brücke sie liefert
        (snapshots/frog10_bausteine.json, erzeugt mit ris-mods vorbefund + bruecke.baustein_lesen) → Texte als Snapshot
        (snapshots/frog10_befunde.txt; neu schreiben: FROG_SNAPSHOT=schreiben).
Teil 2: Einzelfälle wörtlich – Beispielbild, Vorfuß, Sprunggelenk mit Fuß, widersprüchliche Gewölbewinkel, mit Diktat
        (zusätzlicher Befund, Begriff schon diktiert, vom Diktat verneint, Vorlagensatz fehlt), neue Fassung, Gerüst,
        Prompt, Hervorhebung, Lesen des Felds, ohne Feld alles wie bis 3.19.7, Pipeline.
Keine Patientendaten (Auftragsnummern erfunden).  Aufruf: /usr/bin/python3 tests/offline/test_ibl_frog_text.py"""
import copy, json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402,F401

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import cas_vorlagen as cv  # noqa: E402
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
SNAP = ROOT / "tests" / "offline" / "snapshots"
FAELLE = json.loads((SNAP / "frog10_bausteine.json").read_text(encoding="utf-8"))["faelle"]
F = {f["nr"]: f for f in FAELLE}
SCHLUSS = "Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen."
STELLUNG = ("Das Fußskelett ist nach Form, Größe, Anzahl und Stellung der Phalangen, Ossa metatarsalia und der "
            "Fußwurzelknochen normal.")
GEWOELBE = "Das Fußgewölbe ist regulär ausgebildet bei ordnungsgemäßen Gelenkwinkeln."
PHALANGEN = "Die Stellung der Phalangen im Vergleich zu den Ossa metatarsalia ist ordnungsgemäß."
# CAS-Untersuchungscode der Fälle → (Vorlage, Diktat eines Normalbefunds)
CAS = {"fussl": ("fuß_in_2_ebenen", "Fuß links unauffällig."), "fussr": ("fuß_in_2_ebenen", "Fuß rechts unauffällig."),
       "fuss2": ("fuß_in_2_ebenen", "Fuß beidseits unauffällig."),
       "vofu2": ("vorfuß_in_2_ebenen", "Vorfuß beidseits unauffällig."),
       "spruful": ("sprunggelenk_mit_fuss", "Sprunggelenk links mit Fuß unauffällig."),
       "sprufu2": ("sprunggelenk_mit_fuss", "Sprunggelenk beidseits mit Fuß unauffällig.")}
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


def B(nr, **kw):
    d = copy.deepcopy(F[nr]["baustein"])
    d.update(kw)
    return I.aus_liste([d])


def normal(vorlage, diktat):
    """Normalbefund genau wie der Bypass ohne KI (pipeline.bypass_befund)."""
    return pl.bypass_befund(diktat, T[vorlage])


def teile(report):
    """→ (Beschreibung ohne Leerzeilen am Rand, Ergebnis)."""
    befund = report.split("## Befund\n", 1)[1].split("\n## Ergebnis", 1)[0].strip()
    return befund, report.split("## Ergebnis\n", 1)[1].strip() if "## Ergebnis\n" in report else ""


def geaendert(alt, neu):
    """Der geänderte Teil der Beschreibung: die Sätze von neu, die in alt nicht stehen."""
    return " ".join(s for s in br_saetze(neu) if s not in alt) or "(unverändert)"


def br_saetze(text):
    import re
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])", text.replace("\n", " ")) if s.strip()]


FUSS_L = normal("fuß_in_2_ebenen", "Fuß links unauffällig.")
FUSS_B = normal("fuß_in_2_ebenen", "Fuß beidseits unauffällig.")
VORFUSS_L = normal("vorfuß_in_2_ebenen", "Vorfuß links unauffällig.")
VORFUSS_B = normal("vorfuß_in_2_ebenen", "Vorfuß beidseits unauffällig.")
OSG_L = normal("sprunggelenk_mit_fuss", "Sprunggelenk links mit Fuß unauffällig.")
check("Vorlagen enthalten die Sätze, die FROG ersetzt (Fuß, Sprunggelenk mit Fuß, Vorfuß)",
      STELLUNG in FUSS_L and GEWOELBE in FUSS_L and STELLUNG in OSG_L and GEWOELBE in OSG_L and PHALANGEN in VORFUSS_L
      and "Regelrechte Darstellung des Fußskeletts links." in FUSS_L, FUSS_L)

# ───────────────────────────── Teil 1: die 10 echten Fälle + Beispielbild ─────────────────────────────
zeilen = ["IB Lab FROG – fester Fuß-Text (Georg Riegler 17.11.2026): 10 echte anonyme Fälle + Beispielbild.",
          "Je Fall: geänderter Teil der Beschreibung und das Ergebnis, wie KaiScribe 3.19.8 sie in den Normalbefund setzt.",
          ""]
for f in FAELLE:
    vorlage, diktat = CAS[f["cas_code"]]
    alt = normal(vorlage, diktat)
    bs = I.aus_liste([f["baustein"]])
    e = I.einsetzen(alt, bs, diktat=diktat)
    befund, ergebnis = teile(e.report)
    titel = e.report.split("\n", 1)[0][3:]
    zeilen += [f"### Fall {f['nr']} – {titel} ({f['beschreibung']})",
               "Beschreibung: " + geaendert(teile(alt)[0], befund), "Ergebnis:"] + ergebnis.split("\n") + [""]
    if bs[0].befundtext is None:
        check(f"Fall {f['nr']}: nichts pathologisch → Standardtext bleibt wörtlich (auch „bei ordnungsgemäßen "
              "Gelenkwinkeln“), nichts eingesetzt", e.report == alt and e.zeilen == [] and GEWOELBE in e.report, e.report)
        continue
    fuss = vorlage != "vorfuß_in_2_ebenen"
    check(f"Fall {f['nr']} ({f['cas_code']}): Sätze der Vorlage ersetzt, keine Messzeile, Begriffe zuerst, Schluss unten, "
          "Gate ok",
          "(IB Lab FROG)" not in e.report and "ordnungsgemäßen Gelenkwinkeln" not in e.report
          and (STELLUNG not in e.report if fuss else True) and ergebnis.endswith("\n" + SCHLUSS)
          and ergebnis.count(SCHLUSS) == 1 and I.gate(e.report, e.zeilen) == [] and len(e.zeilen) >= 2
          and "Schneiderballen" not in e.report and "Regelrechte Darstellung des Fußskeletts" not in ergebnis
          and e.zuordnung == {"frog": titel} and "bitte prüfen" not in e.report, e.report)
snap_datei = SNAP / "frog10_befunde.txt"
snap = "\n".join(zeilen).rstrip() + "\n"
if os.environ.get("FROG_SNAPSHOT") == "schreiben":
    snap_datei.write_text(snap, encoding="utf-8")
    print("(Snapshot neu geschrieben)")
check("Snapshot der 11 Texte unverändert (snapshots/frog10_befunde.txt)",
      snap_datei.exists() and snap_datei.read_text(encoding="utf-8") == snap, snap)

# ───────────────────────────── Teil 2: Einzelfälle wörtlich ─────────────────────────────
BILD_ST = ("Valgusstellung der Großzehe mit einem Hallux-valgus-Winkel von 42° (Norm 0–15°) bei vergrößertem "
           "Intermetatarsalwinkel I/II von 19° (Norm 0–10°).")
BILD_GW = ("Erhöhtes Längsgewölbe mit einer Calcaneusneigung von 37° (Norm 20–30°) und einem Längsgewölbewinkel von "
           "101° (Norm 115–135°).")
BILD_ERG = "Hochgradiger Hallux valgus links. Metatarsus primus varus links. Pes cavus links."
e = I.einsetzen(FUSS_L, B(11), diktat="Fuß links unauffällig.")
soll = FUSS_L.replace(STELLUNG, BILD_ST).replace(GEWOELBE, BILD_GW).replace(
    "Regelrechte Darstellung des Fußskeletts links.", BILD_ERG + "\n" + SCHLUSS)
check("Beispielbild (links: HVA 42, IMA 19, CIA 37, Meary 6, MAA 101): Stellungssatz → Valgus-Satz, Gewölbesatz → "
      "„Erhöhtes Längsgewölbe …“ (ohne Meary), Ergebnis ein Punkt ohne Nummer + Schlussanmerkung", e.report == soll,
      e.report)
check("   … Standard-Ergebnissatz ersetzt (Hinweis nur in der Anzeige), sonst kein Hinweis",
      e.hinweise == ["FROG: „Regelrechte Darstellung des Fußskeletts links.“ durch das IB-Lab-Ergebnis ersetzt"],
      str(e.hinweise))
check("   … eingesetzt = Sätze + Ergebnispunkt + Schluss (für Gate, Hervorhebung, neue Fassung)",
      e.zeilen == [BILD_ST, BILD_GW, BILD_ERG, SCHLUSS], str(e.zeilen))

e = I.einsetzen(FUSS_L, B(2), diktat="Fuß links unauffällig.")
b, erg = teile(e.report)
check("nur Hallux (Fall 2, ein Fuß, Seite nur aus dem CAS-Code): Gewölbe „… regulär ausgebildet.“ ohne Zusatz, die "
      "Seite im Ergebnis kommt aus dem Titel",
      b.startswith("Valgusstellung der Großzehe mit einem Hallux-valgus-Winkel von 22° (Norm 0–15°). Das Fußgewölbe "
                   "ist regulär ausgebildet. Mineralgehalt")
      and erg == "Mittelgradiger Hallux valgus links.\n" + SCHLUSS, e.report)
e = I.einsetzen(normal("fuß_in_2_ebenen", "Fuß rechts unauffällig."), B(9), diktat="Fuß rechts unauffällig.")
b, erg = teile(e.report)
check("nur Gewölbe (Fall 9, Pes planus): Stellungssatz entfällt ersatzlos, Gewölbesatz ersetzt",
      b.startswith("Abgeflachtes Längsgewölbe mit einem Meary-Winkel von −12° (Norm −4 bis 4°). Mineralgehalt")
      and erg == "Pes planus rechts.\n" + SCHLUSS, e.report)
e = I.einsetzen(FUSS_B, B(7), diktat="Fuß beidseits unauffällig.")
b, erg = teile(e.report)
check("beidseits gleich (Fall 7): ein Satz „beidseits“ mit den Werten je Seite, Begriffe „beidseits“; Gewölbe ohne "
      "sichere Seite bleibt ohne Seite",
      b.startswith("Valgusstellung der Großzehe beidseits mit einem Hallux-valgus-Winkel von rechts 31° und links 30° "
                   "(Norm 0–15°) bei vergrößertem Intermetatarsalwinkel I/II von rechts 16° und links 16° (Norm 0–10°). "
                   "Erhöhtes Längsgewölbe mit einer Calcaneusneigung von 34° (Norm 20–30°). Mineralgehalt")
      and erg == "Mittelgradiger Hallux valgus beidseits. Metatarsus primus varus beidseits. Pes cavus.\n" + SCHLUSS,
      e.report)
e = I.einsetzen(FUSS_B, B(5), diktat="Fuß beidseits unauffällig.")
check("beidseits verschieden (Fall 5): Begriffe getrennt nach Seite, rechts zuerst",
      teile(e.report)[1] == "Geringgradiger Hallux valgus rechts. Mittelgradiger Hallux valgus links.\n" + SCHLUSS,
      e.report)

# Vorfuß: nur d.p.
e = I.einsetzen(VORFUSS_L, B(11), diktat="Vorfuß links unauffällig.")
b, erg = teile(e.report)
check("Vorfuß (Beispielbild): Phalangen-Satz → Valgus-Satz, KEIN Gewölbe-Satz, im Ergebnis nur die d.p.-Begriffe",
      PHALANGEN not in b and BILD_ST in b and "Längsgewölbe" not in e.report and "Pes cavus" not in e.report
      and b.startswith("Das Fußskelett ist nach Form, Größe und Anzahl der Phalangen")
      and erg == "Hochgradiger Hallux valgus links. Metatarsus primus varus links.\n" + SCHLUSS, e.report)
e = I.einsetzen(VORFUSS_B, B(9), diktat="Vorfuß beidseits unauffällig.")
check("Vorfuß, FROG nur am Gewölbe auffällig: nichts eingesetzt, Befund unverändert", e.report == VORFUSS_B
      and e.zeilen == [], e.report)
mpv = copy.deepcopy(F[11]["baustein"])
mpv["befundtext"].update(stellung=["Vergrößerter Intermetatarsalwinkel I/II von 19° (Norm 0–10°)."], phalangen=False,
                         begriffe=[{"art": "dp", "text": "Metatarsus primus varus", "seite": "links"}])
e = I.einsetzen(VORFUSS_L, I.aus_liste([mpv]), diktat="Vorfuß links unauffällig.")
check("Vorfuß, nur Metatarsus primus varus: der Phalangen-Satz bleibt, der FROG-Satz steht dahinter",
      PHALANGEN + " Vergrößerter Intermetatarsalwinkel I/II von 19° (Norm 0–10°). Mineralgehalt" in e.report
      and teile(e.report)[1] == "Metatarsus primus varus links.\n" + SCHLUSS, e.report)

# Sprunggelenk mit Fuß
e = I.einsetzen(OSG_L, B(6), diktat="Sprunggelenk links mit Fuß unauffällig.")
b, erg = teile(e.report)
check("Sprunggelenk mit Fuß (Fall 6): Sätze an der Stelle der Fuß-Sätze, vom Standard-Ergebnis bleibt das Sprunggelenk",
      "Normal weiter Gelenkspalt. Varusstellung der Kleinzehe mit einem Metatarsophalangealwinkel V von 14° (Norm 0–10°). "
      "Erhöhtes Längsgewölbe mit einem Längsgewölbewinkel von 109° (Norm 115–135°). Die mitdargestellten" in b
      and erg == ("1. Digitus quintus varus links. Pes cavus links.\n2. Regelrechte Darstellung des oberen "
                  "Sprunggelenkes links.\n" + SCHLUSS), e.report)

# widersprüchliche Gewölbewinkel: kein Gewölbesatz
w = copy.deepcopy(F[2]["baustein"])
w["befundtext"].update(gewoelbe=[], gewoelbe_weg=True)
e = I.einsetzen(FUSS_L, I.aus_liste([w]), diktat="Fuß links unauffällig.")
check("Gewölbewinkel widersprüchlich: Gewölbesatz ersatzlos gestrichen (auch nicht „regulär“)",
      "gewölbe" not in e.report.lower() and teile(e.report)[0].startswith(
          "Valgusstellung der Großzehe mit einem Hallux-valgus-Winkel von 22° (Norm 0–15°). Mineralgehalt"), e.report)

# mit Diktat: die KI hat die Vorlagensätze übernommen und Diktiertes ergänzt
KI = FUSS_L.replace("Keine intra- und periartikulären Verkalkungen.",
                    "Verschmälerung des Gelenkspalts im Großzehengrundgelenk mit subchondraler Sklerose.").replace(
    "Regelrechte Darstellung des Fußskeletts links.", "Arthrose im Großzehengrundgelenk links.")
e1 = I.einsetzen(KI, B(11), diktat="Fuß links: Arthrose im Großzehengrundgelenk.")
check("mit Diktat: FROG-Begriffe Punkt 1, der diktierte Befund Punkt 2, Schlussanmerkung ohne Nummer; Diktiertes bleibt",
      teile(e1.report)[1] == f"1. {BILD_ERG}\n2. Arthrose im Großzehengrundgelenk links.\n{SCHLUSS}"
      and "Verschmälerung des Gelenkspalts im Großzehengrundgelenk mit subchondraler Sklerose." in e1.report
      and BILD_ST in e1.report and BILD_GW in e1.report and e1.hinweise == [], e1.report + str(e1.hinweise))
e = I.einsetzen(KI.replace("Arthrose im Großzehengrundgelenk links.",
                           "1. Hallux valgus links.\n2. Arthrose im Großzehengrundgelenk links."), B(11),
                diktat="Fuß links: Hallux valgus, Arthrose im Großzehengrundgelenk.")
check("Begriff schon diktiert: nicht doppelt ins Ergebnis (Hinweis), die Sätze mit den Winkeln kommen trotzdem",
      teile(e.report)[1] == ("1. Metatarsus primus varus links. Pes cavus links.\n2. Hallux valgus links.\n"
                             f"3. Arthrose im Großzehengrundgelenk links.\n{SCHLUSS}") and BILD_ST in e.report
      and e.hinweise == ["FROG: „Hochgradiger Hallux valgus links“ – schon diktiert, nicht doppelt angefügt"],
      e.report + str(e.hinweise))
e = I.einsetzen(KI, B(11), diktat="Fuß links: kein Hallux valgus. Arthrose im Großzehengrundgelenk.")
check("Diktat verneint den Begriff: aus der d.p.-Aufnahme kommt nichts (Hinweis nur in der Anzeige), das Gewölbe schon",
      "Valgusstellung" not in e.report and "Hallux valgus" not in e.report and "Metatarsus" not in e.report
      and BILD_GW in e.report and teile(e.report)[1] == f"1. Pes cavus links.\n2. Arthrose im Großzehengrundgelenk "
                                                         f"links.\n{SCHLUSS}"
      and e.hinweise == ["FROG: „Hochgradiger Hallux valgus links“ – Diktat verneint „hallux valgus“, bitte prüfen "
                         "(nicht eingesetzt)"] and "bitte prüfen" not in e.report, e.report + str(e.hinweise))
e = I.einsetzen(KI, B(11), diktat="Fuß links: kein Hohlfuß, kein Hallux valgus. Arthrose im Großzehengrundgelenk.")
check("Diktat verneint beides (Hallux valgus und Hohlfuß): nichts eingesetzt, Befund unverändert, zwei Hinweise",
      e.report == KI and e.zeilen == [] and len(e.hinweise) == 2 and all("verneint" in h for h in e.hinweise),
      e.report + str(e.hinweise))
e = I.einsetzen(KI, B(11), diktat="Fuß links: kein Plattfuß. Arthrose im Großzehengrundgelenk.")
check("Diktat verneint nur den Plattfuß, IB Lab misst einen Hohlfuß: kein Widerspruch, alles wird eingesetzt",
      teile(e.report)[1] == f"1. {BILD_ERG}\n2. Arthrose im Großzehengrundgelenk links.\n{SCHLUSS}"
      and BILD_GW in e.report and e.hinweise == [], e.report + str(e.hinweise))
OHNE = KI.replace(STELLUNG + " " + GEWOELBE + " ", "Zustand nach Fraktur des Os metatarsale V. ")
e = I.einsetzen(OHNE, B(11), diktat="Fuß links: Zustand nach Fraktur MT V. Arthrose im Großzehengrundgelenk.")
check("Vorlagensätze nicht mehr da (der Arzt hat dazu diktiert): FROG-Sätze als eigener Absatz am Ende der "
      "Beschreibung + Hinweis, am Diktierten wird nichts geändert",
      f"Die Weichteile sind unauffällig.\n\n{BILD_ST}\n{BILD_GW}\n\n## Ergebnis\n1. {BILD_ERG}" in e.report
      and "Zustand nach Fraktur des Os metatarsale V. Mineralgehalt" in e.report and I.gate(e.report, e.zeilen) == []
      and e.hinweise == ["FROG: Satz der Vorlage zu Zehenstellung/Fußgewölbe nicht gefunden – IB-Lab-Sätze am Ende der "
                         "Beschreibung, bitte prüfen"], e.report + str(e.hinweise))
abw = I.einsetzen(KI.replace("subchondraler Sklerose.", "subchondraler Sklerose. Hallux-valgus-Winkel 30°."), B(11),
                  diktat="Fuß links: Arthrose im Großzehengrundgelenk. Hallux-valgus-Winkel 30 Grad.")
check("abweichend diktierter Winkel: Hinweis nur in der Anzeige", any("Hallux-valgus-Winkel" in h and "bitte prüfen" in h
                                                                     for h in abw.hinweise), str(abw.hinweise))

# neue Fassung (Knopf „＋ IB Lab einfügen“) und noch einmal dieselbe
neu = copy.deepcopy(F[11]["baustein"])
neu["version"] = 2
NEU_ST = "Valgusstellung der Großzehe mit einem Hallux-valgus-Winkel von 44° (Norm 0–15°)."
neu["befundtext"]["stellung"] = [NEU_ST]
neu["befundtext"]["begriffe"] = [x for x in neu["befundtext"]["begriffe"] if "Metatarsus" not in x["text"]]
neu["ergebnis"] = ["Hochgradiger Hallux valgus links. Pes cavus links.", SCHLUSS]
e2 = I.einsetzen(e1.report, I.aus_liste([neu]), diktat="Fuß links: Arthrose im Großzehengrundgelenk.",
                 entfernen=e1.zeilen)
check("neue Fassung: die alten Sätze werden an Ort und Stelle ersetzt, das Ergebnis neu, nichts doppelt, nichts offen",
      e2.report == e1.report.replace(BILD_ST, NEU_ST).replace(BILD_ERG, "Hochgradiger Hallux valgus links. Pes cavus "
                                                                        "links.")
      and e2.nicht_entfernt == [] and e2.report.count(SCHLUSS) == 1 and I.gate(e2.report, e2.zeilen) == [], e2.report)
e3 = I.einsetzen(e1.report, B(11), diktat="Fuß links: Arthrose im Großzehengrundgelenk.")
check("dieselbe Fassung noch einmal eingesetzt: Befund bit-gleich", e3.report == e1.report and e3.zeilen == e1.zeilen,
      e3.report)
fremd = I.einsetzen(e1.report, I.aus_liste([neu]), diktat="", entfernen=e1.zeilen + ["Beinlänge rechts 86,4 cm (IB Lab "
                                                                                   "LAMA)."])
check("… eine nicht mehr vorhandene fremde Zeile bleibt als offen gemeldet (FROG schluckt sie nicht)",
      fremd.nicht_entfernt == ["Beinlänge rechts 86,4 cm (IB Lab LAMA)."], str(fremd.nicht_entfernt))

# zwei Untersuchungen im Befund
zwei = "\n\n\n".join([FUSS_L, normal("kniegelenk_in_2_ebenen", "Knie links unauffällig.")
                      if "kniegelenk_in_2_ebenen" in T else "## Knie links in 2 Ebenen\n\n## Befund\nRegelrecht.\n\n"
                      "## Ergebnis\nRegelrechte Darstellung des Kniegelenks links."])
e = I.einsetzen(zwei, B(11), segmente=["Fuß links unauffällig.", "Knie links unauffällig."])
fuss_teil, knie_teil = e.report.split("\n\n\n", 1)
check("zwei Untersuchungen: FROG nur im Fuß-Abschnitt, der zweite Abschnitt bit-gleich",
      BILD_ST in fuss_teil and SCHLUSS in fuss_teil and knie_teil == zwei.split("\n\n\n", 1)[1], e.report)

# Gerüst vor dem Diktat, Prompt, Hervorhebung, Band
g = I.geruest(B(11), [{"kurz": "fussl", "text": "Fuß links", "appc": "", "modalitaet": "Röntgen", "seite": "links",
                       "vorlage": "fuß_in_2_ebenen", "ohne_vorlage": False, "bekannt": True}], T)
check("Gerüst: nur die FROG-Sätze und das Ergebnis, keine Messzeilen",
      g.report == f"## Fuß links in 2 Ebenen\n\n## Befund\n{BILD_ST}\n{BILD_GW}\n\n## Ergebnis\n{BILD_ERG}\n{SCHLUSS}"
      and g.zeilen == [BILD_ST, BILD_GW, BILD_ERG, SCHLUSS], g.report)
g2 = I.geruest(B(2), None, T)
check("Gerüst, Gewölbe normal: kein „Das Fußgewölbe ist regulär …“ ohne Vorlagentext",
      "Fußgewölbe" not in g2.report and "Mittelgradiger Hallux valgus" in g2.report, g2.report)
check("Gerüst ohne Pathologie (Fall 4): keins", I.geruest(B(4), None, T) is None)
blk = I.prompt_block(B(11), T["fuß_in_2_ebenen"]["body"])
check("Prompt: keine Zahl, kein Begriff aus dem Ergebnis; die KI lässt die Vorlagensätze stehen (KaiScribe ersetzt sie)",
      "<ibl_messwerte>" in blk and "FROG" in blk and "wörtlich und unverändert" in blk and "42" not in blk
      and "Hallux" not in blk and "Pes cavus" not in blk and "nicht übernehmen" not in blk, blk)
check("Prompt ohne Bausteine bzw. ohne Pathologie: leer (bit-gleich wie bisher)", I.prompt_block([]) == ""
      and I.prompt_block(B(4)) == "", I.prompt_block(B(4)))
check("Hervorhebung: die pathologischen Sätze und die Begriffe, nicht der Normalsatz und nicht die Schlussanmerkung",
      I.auffaellige_zeilen(B(2)) == ["Valgusstellung der Großzehe mit einem Hallux-valgus-Winkel von 22° (Norm 0–15°).",
                                     "Mittelgradiger Hallux valgus"]
      and I.auffaellige_zeilen(B(11)) == [BILD_ST, BILD_GW, "Hochgradiger Hallux valgus links",
                                          "Metatarsus primus varus links", "Pes cavus links"],
      str(I.auffaellige_zeilen(B(11))))
check("Baustein: keine Befundzeilen mehr, hat Inhalt; Details (alle Winkel) bleiben im Baustein",
      I.befund_zeilen(B(11)[0]) == [] and I.hat_inhalt(B(11)[0]) and len(B(11)[0].befundteil) == 8
      and not I.hat_inhalt(B(4)[0]))

# Feld lesen
alt_fmt = {k: v for k, v in F[11]["baustein"].items() if k != "befundtext"}
check("Feld „befundtext“: nur FROG, nur Fassung 1, nur mit Begriffen – sonst None",
      B(11)[0].befundtext["begriffe"][0] == {"art": "dp", "text": "Hochgradiger Hallux valgus", "seite": "links"}
      and I.aus_liste([alt_fmt])[0].befundtext is None
      and I.aus_liste([dict(F[11]["baustein"], befundtext=dict(F[11]["baustein"]["befundtext"], format=2))])[0].befundtext
      is None
      and I.aus_liste([dict(F[11]["baustein"], befundtext=dict(F[11]["baustein"]["befundtext"], begriffe=[]))])[
          0].befundtext is None
      and I.aus_liste([dict(F[11]["baustein"], befundtext="kaputt")])[0].befundtext is None
      and I.aus_liste([dict(F[11]["baustein"], modul="lama", name="LAMA")])[0].befundtext is None)
ALT = {"accno": "T-0021", "ziffer": 1, "modul": "frog", "name": "FROG", "modul_name": "IB Lab FROG", "version": 1,
       "seiten": ["rechts"], "befundteil": ["Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG).",
                                            "Hallux-valgus-Winkel rechts 24,3° (IB Lab FROG)."],
       "ergebnis": ["Pes planus rechts (Calcaneusneigungswinkel 10,0°).",
                    "Mittelgradiger Hallux valgus rechts (Hallux-valgus-Winkel 24,3°)."],
       "hinweise": [], "nicht_zugeordnet": []}
rep = "## Fuß rechts in 2 Ebenen\n\n## Befund\nArthrose im Großzehengrundgelenk.\n\n## Ergebnis\nArthrose MTP I."
e = I.einsetzen(rep, I.aus_liste([ALT]), diktat="Fuß rechts: Arthrose MTP I.")
check("ohne das Feld (Abholer < 1.3.7): alles wie bis 3.19.7 – Messzeilen + Ergebnispunkte mit Winkel",
      "Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG).\nHallux-valgus-Winkel rechts 24,3° (IB Lab FROG)." in e.report
      and "2. Pes planus rechts (Calcaneusneigungswinkel 10,0°)." in e.report and SCHLUSS not in e.report, e.report)
check("ohne FROG: Befund unverändert", I.einsetzen(FUSS_L, [], diktat="Fuß links unauffällig.").report == FUSS_L)

# Nummerierung: Schlussanmerkung zählt nicht mit
check("Ergebnis-Nummerierung: FROG-Schlussanmerkung ohne Nummer; ein Punkt davor bleibt unnummeriert, zwei werden gezählt",
      br.ergebnis_nummerieren(f"## Ergebnis\n1. Pes planus rechts.\n{SCHLUSS}") == f"## Ergebnis\nPes planus rechts.\n{SCHLUSS}"
      and br.ergebnis_nummerieren(f"## Ergebnis\nPes planus rechts.\nArthrose MTP I.\n{SCHLUSS}")
      == f"## Ergebnis\n1. Pes planus rechts.\n2. Arthrose MTP I.\n{SCHLUSS}")


# Pipeline: Normalbefund ohne KI und mit KI-Attrappe
def L(kurz, text, vorlage, seite):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": "Röntgen", "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True}


def kontext(prompts, bausteine, cas, antwort=None):
    def llm(p):
        prompts.append(p)
        return antwort
    return pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=llm, log=lambda *a: None, cas=cas,
                      ibl=I.IblKontext(bausteine))


FUSS_CAS = cv.CasHinweis([L("fussl", "Fuß links", "fuß_in_2_ebenen", "links")], T)
prompts = []
erg = pl.befund_aus_diktat("Fuß links unauffällig.", kontext(prompts, B(11), FUSS_CAS))
check("Pipeline, Normalbefund ohne KI: derselbe Text wie oben, Hinweis nur in erg.ibl", prompts == []
      and erg.report == soll and erg.vollstaendig and "bitte prüfen" not in erg.report, erg.report)
prompts = []
erg = pl.befund_aus_diktat("Fuß links: Arthrose im Großzehengrundgelenk.", kontext(prompts, B(11), FUSS_CAS, KI))
check("Pipeline mit KI: <ibl_messwerte> mit dem FROG-Satz im Prompt, Begriffe vor dem diktierten Befund",
      len(prompts) == 1 and "FROG: Übernimm die Vorlagen-Sätze" in prompts[0]
      and f"1. {BILD_ERG}\n2. Arthrose im Großzehengrundgelenk links.\n{SCHLUSS}" in erg.report and BILD_ST in erg.report,
      erg.report)
prompts = []
erg = pl.befund_aus_diktat("Fuß rechts unauffällig.",
                           kontext(prompts, B(4), cv.CasHinweis([L("fussr", "Fuß rechts", "fuß_in_2_ebenen", "rechts")], T)))
check("Pipeline, FROG ohne Pathologie (Fall 4): Normalbefund wörtlich wie ohne IB Lab",
      erg.report == normal("fuß_in_2_ebenen", "Fuß rechts unauffällig.") and prompts == [], erg.report)

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
