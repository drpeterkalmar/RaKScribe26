"""Gate v3.13.0 (Peter 13.10.2026: „Ginge es, dass RaKScribe beim Öffnen gleich eventuell vorhandene Bausteine von IBL
holt?“). Die RaKScribe-Brücke 1.2.0 reicht cas_ibl_<id>.json nach; RaKScribe setzt die Messwerte NACH der KI wörtlich ein.
Teil 1: ibl_bausteine.py — Lesen, Band, Messwerte, Zuordnung (Ziffer ↔ CAS-Leistung, Modul ↔ Region, Seite, mehrdeutig),
        Einsetzen, Doppelung, Widerspruch, unauffälliges Ergebnis, Rho, ältere Fassung ersetzen, Messwert-Gate, Prompt.
Teil 2: pipeline.befund_aus_diktat mit Bausteinen (KI-Attrappe schreibt das Diktat in den Befund): Prompt nur für den
        passenden Abschnitt, Zeilen am richtigen Ort, ohne Bausteine bit-gleich (keine IBL-Funktion aufgerufen).
Teil 3: EXE-Ablauf (exe_stubs): Datei abholen → Band „IB Lab: FROG rechts ✓“ (hervorgehoben), halb geschrieben/fremde
        Nummer, INS mit Bausteinen, neue Fassung nach dem Befund → Knopf „＋ IB Lab einfügen“, Menü aus, F9, EOL.
Teil 4 (nur am Mac, wenn ~/dev/ris-mods da ist): Protokoll gegen die echte Brückenseite (bruecke/ibl_bausteine.py +
        auftrag.py; Ablage-JSON wie vom IB-Lab-Abholer).
Synthetische Werte (ris-mods/ibl/beispiele), keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_ibl_bausteine.py"""
import importlib.util, json, os, pathlib, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import cas_vorlagen as cv  # noqa: E402
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# Bausteine wie aus der Brücke (Texte wie ibl/vorbefund.py sie aus ibl/beispiele bildet)
FROG_D = {"accno": "T-0021", "ziffer": 1, "modul": "frog", "name": "FROG", "modul_name": "IB Lab FROG",
          "version": 1, "aktualisiert": "2026-10-13T18:00:00", "seiten": ["rechts"],
          "befundteil": ["Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG).",
                         "Hallux-valgus-Winkel rechts 24,3° (IB Lab FROG)."],
          "ergebnis": ["Pes planus rechts (Calcaneusneigungswinkel 10,0°).",
                       "Mittelgradiger Hallux valgus rechts (Hallux-valgus-Winkel 24,3°)."],
          "hinweise": [], "nicht_zugeordnet": []}
FROG_BDS = dict(FROG_D, seiten=["rechts", "links"], version=2, aktualisiert="2026-10-13T18:04:00",
                befundteil=["Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG).",
                            "Calcaneusneigungswinkel links 12,4° (IB Lab FROG)."],
                ergebnis=["Pes planus beidseits (Calcaneusneigungswinkel rechts 10,0°, links 12,4°)."],
                nicht_zugeordnet=["IB Lab FROG links: Unbekannter Winkel = 3.1 deg"])
LAMA_D = {"accno": "T-0023", "ziffer": 3, "modul": "lama", "name": "LAMA", "modul_name": "IB Lab LAMA",
          "version": 1, "aktualisiert": "2026-10-13T18:01:00", "seiten": ["rechts", "links"],
          "befundteil": ["HKA-Winkel rechts 174,2° (IB Lab LAMA).", "HKA-Winkel links 179,1° (IB Lab LAMA).",
                         "Beinlängendifferenz 15 mm (IB Lab LAMA)."],
          "ergebnis": ["Genu varum rechts (HKA-Winkel 174,2°).", "Beinlängendifferenz von 15 mm."],
          "hinweise": ["LAMA: HKA-Konvention (< 180° = Varus) noch nicht an echtem SR bestätigt – Varus/Valgus bitte am "
                       "Bild prüfen."], "nicht_zugeordnet": []}
RHO_D = {"accno": "T-0051", "ziffer": 1, "modul": "rho", "name": "Rho", "modul_name": "16 Bit Rho", "version": 1,
         "seiten": [], "befundteil": ["Rho-Score 8 von 10 (16 Bit Rho)."],
         "ergebnis": ["Als Zufallsbefund KI-gestützter Hinweis auf eine wahrscheinlich verminderte Knochendichte (16 Bit "
                      "Rho, Score 8 von 10, kein Diagnostikum). Eine Knochendichtemessung (DXA) wird empfohlen."],
         "hinweise": ["16 Bit Rho: Ergebnistext ist ein Entwurf (Regel rho-score-8, endgültiger Baustein von Georg "
                      "ausständig) – bitte prüfen."], "nicht_zugeordnet": []}
RBF_D = {"accno": "T-0061", "ziffer": 1, "modul": "rbfracture", "name": "RBfracture", "version": 1,
         "befundteil": [], "ergebnis": [], "hinweise": ["RBfracture: Fraktur-Verdacht Radius links – bitte prüfen."]}


def B(*ds):
    return I.aus_liste(list(ds))


def L(kurz, text, mod, vorlage, seite=None, ohne=False):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": mod, "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": ohne, "bekannt": True}


FUSS_TPL = T["fuß_in_2_ebenen"]["body"].split("\n", 2)[2].strip()


def bericht(titel, befund, ergebnis):
    return f"## {titel}\n\n## Befund\n{befund}\n\n## Ergebnis\n{ergebnis}"


def abschnitt_von(report, titel_wort):
    teile = report.split("\n\n\n")
    return next((t for t in teile if titel_wort in t.split("\n", 1)[0]), "")


# ───────────────────────────── Teil 1: ibl_bausteine ─────────────────────────────
bs = B(LAMA_D, FROG_D, {"modul": "x y"}, {"modul": "frog"}, "kaputt", RBF_D)
check("aus_liste: ungültige Einträge weg, sortiert nach Ziffer, Labels mit Seite",
      [(b.name, b.ziffer, b.label) for b in bs] == [("FROG", 1, "FROG rechts"), ("RBfracture", 1, "RBfracture"),
                                                    ("LAMA", 3, "LAMA beidseits")], str([(b.name, b.label) for b in bs]))
check("Band: „IB Lab: FROG rechts ✓ · LAMA beidseits ✓“, aus → Hinweis aufs Menü",
      I.band_text(B(FROG_D, LAMA_D)) == "IB Lab: FROG rechts ✓ · LAMA beidseits ✓"
      and I.band_text(B(FROG_D), an=False) == "IB Lab: FROG rechts  (Übernahme aus – Menü)" and I.band_text([]) == "")
mw = [I.messwert(z) for z in ("Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG).", "Rho-Score 8 von 10 (16 Bit Rho).",
                              "Länge des 1. Strahls (sagittal) rechts 62,5 mm (IB Lab FROG).",
                              "Kellgren-Lawrence-Grad: 3 (IB Lab KOALA).", "Gelenkerguss: positiv (Radiobotics RBfracture).")]
check("Messwerte lesen: Name, Wert wie geliefert, Zahl (auch „8 von 10“, Ziffer im Namen, Code ohne Zahl)",
      [(m.name, m.wert, str(m.zahl)) for m in mw] == [
          ("Calcaneusneigungswinkel", "10,0°", "10.0"), ("Rho-Score", "8 von 10", "8"),
          ("Länge des 1. Strahls (sagittal)", "62,5 mm", "62.5"), ("Kellgren-Lawrence-Grad", "3", "3"),
          ("Gelenkerguss", "positiv", "None")], str([(m.name, m.wert, m.zahl) for m in mw]))
m = I.messwert("Beinlängendifferenz 15 mm (IB Lab LAMA).")
check("Vergleich im Text: gleich (auch 1,5 cm = 15 mm), anders, ohne Zahl, fehlt",
      (I.im_text(m, "Beinlängendifferenz von 15 mm.")[0], I.im_text(m, "Beinlängendifferenz 1,5 cm")[0],
       I.im_text(m, "Beinlängendifferenz 9 mm.")[0], I.im_text(m, "Keine signifikante Beinlängendifferenz.")[0],
       I.im_text(m, "Beinlänge rechts 86 cm.")[0]) == ("gleich", "gleich", "anders", "ohne_zahl", "fehlt"))
check("Diagnose-Kern ohne Grad, Seite, Messwerte", [I.diagnose_kern(p) for p in (
    "Mittelgradiger Hallux valgus rechts (Hallux-valgus-Winkel 24,3°).", "Pes planus beidseits (Calcaneus…).",
    "Beinlängendifferenz von 15 mm.", "Geringgradige Gonarthrose rechts (KL-Grad 2).")]
      == ["hallux valgus", "pes planus", "beinlängendifferenz", "gonarthrose"])

rep = bericht("Fuß rechts in 2 Ebenen", "Hallux valgus mit Exostose am Metatarsale-I-Köpfchen.", "Hallux valgus.")
e = I.einsetzen(rep, B(FROG_D), diktat="Fuß rechts: Hallux valgus mit Exostose.")
check("a) ein Modul: Messwerte als eigener Absatz am Ende des Befundtexts, neue Diagnose ans Ergebnis (nummeriert), "
      "dieselbe Diagnose nicht doppelt", e.report == bericht(
          "Fuß rechts in 2 Ebenen", "Hallux valgus mit Exostose am Metatarsale-I-Köpfchen.\n\n"
          "Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG).\nHallux-valgus-Winkel rechts 24,3° (IB Lab FROG).",
          "1. Hallux valgus.\n2. Pes planus rechts (Calcaneusneigungswinkel 10,0°).")
      and e.hinweise == ["FROG: „Mittelgradiger Hallux valgus rechts (Hallux-valgus-Winkel 2…“ – Diagnose schon im "
                         "Befund, nicht doppelt angefügt"] and e.zuordnung == {"frog": "Fuß rechts in 2 Ebenen"}, e.report)
check("   … Messwert-Gate: eingesetzte Zeilen wörtlich, Zahlen 1:1", I.gate(e.report, e.zeilen) == []
      and len(e.zeilen) == 3 and all(z in e.report for z in FROG_D["befundteil"]))
check("   … Gate erkennt eine veränderte Zahl", I.gate(e.report.replace("10,0°", "10°"), e.zeilen) != [])

zwei = "\n\n\n".join([bericht("Fuß rechts in 2 Ebenen", "Arthrose im Großzehengrundgelenk.", "Arthrose MTP I."),
                      bericht("Ganzbeinaufnahme im Stand", "Varische Beinachse rechts.", "Genu varum rechts.")])
e = I.einsetzen(zwei, B(LAMA_D, FROG_D), segmente=["Fuß rechts: Arthrose MTP I.", "Ganzbein: Genu varum rechts."])
fuss, bein = abschnitt_von(e.report, "Fuß"), abschnitt_von(e.report, "Ganzbein")
check("b) zwei Module/zwei Untersuchungen: FROG → Fuß, LAMA → Ganzbein (Region), je am richtigen Ort",
      "Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG)." in fuss and "HKA-Winkel" not in fuss
      and "HKA-Winkel rechts 174,2° (IB Lab LAMA)." in bein and "Calcaneus" not in bein
      and "2. Beinlängendifferenz von 15 mm." in bein and "Genu varum rechts (HKA" not in bein
      and e.zuordnung == {"frog": "Fuß rechts in 2 Ebenen", "lama": "Ganzbeinaufnahme im Stand"}, e.report)
check("   … Abschnitte bleiben durch zwei Leerzeilen getrennt, Gate ok", e.report.count("\n\n\n") == 1
      and I.gate(e.report, e.zeilen) == [])

beide = "\n\n\n".join([bericht("Fuß links in 2 Ebenen", "Unauffällig.", "Regelrechte Darstellung des Fußskeletts links."),
                       bericht("Fuß rechts in 2 Ebenen", "Hallux valgus.", "Hallux valgus rechts.")])
e = I.einsetzen(beide, B(FROG_D))
check("c) zwei Fuß-Abschnitte: die Seite des Bausteins entscheidet (rechts)",
      "Calcaneus" in abschnitt_von(e.report, "Fuß rechts") and "Calcaneus" not in abschnitt_von(e.report, "Fuß links"))
cas_l = [L("x-fuss-re", "Fuß rechts", "Röntgen", "fuß_in_2_ebenen", "rechts"),
         L("x-fuss-li", "Fuß links", "Röntgen", "fuß_in_2_ebenen", "links")]
frog_ohne_seite = dict(FROG_D, seiten=[], ziffer=2, befundteil=["Calcaneusneigungswinkel 10° (IB Lab FROG)."])
e = I.einsetzen(beide, B(frog_ohne_seite), cas_leistungen=cas_l, templates=T)
check("d) Ziffer der Leistung ↔ CAS-Leistung: Ziffer 2 = „Fuß links“ (ohne Seite im Baustein)",
      "Calcaneusneigungswinkel 10°" in abschnitt_von(e.report, "Fuß links") and e.zuordnung == {"frog": "Fuß links in 2 Ebenen"})
e = I.einsetzen(beide, B(dict(FROG_D, ziffer=2)), cas_leistungen=cas_l, templates=T)
check("   … Ziffer zeigt auf „links“, Baustein sagt „rechts“ → Ziffer verworfen, Seite entscheidet",
      e.zuordnung == {"frog": "Fuß rechts in 2 Ebenen"}, str(e.zuordnung))
e = I.einsetzen(beide, B(frog_ohne_seite))
check("e) mehrdeutig (zwei Füße, keine Seite, keine Ziffer) → eigener Absatz am Ende + Hinweis",
      e.report.endswith("\n\nCalcaneusneigungswinkel 10° (IB Lab FROG).\nPes planus rechts (Calcaneusneigungswinkel 10,0°).")
      and e.zuordnung == {"frog": I.ENDE} and any("keiner Untersuchung eindeutig zuzuordnen" in h for h in e.hinweise),
      e.report[-160:])
e = I.einsetzen(bericht("Lendenwirbelsäule in 2 Ebenen", "Osteochondrose L4/5.", "Osteochondrose L4/5."), B(FROG_D))
check("   … Region passt nicht (FROG zu LWS) → Absatz am Ende + Hinweis, nichts in den LWS-Befund",
      e.zuordnung == {"frog": I.ENDE} and e.report.startswith(bericht("Lendenwirbelsäule in 2 Ebenen",
                                                                      "Osteochondrose L4/5.", "Osteochondrose L4/5.")))

rep = bericht("Fuß rechts in 2 Ebenen", "Calcaneusneigungswinkel 10 Grad, Pes planus.", "Pes planus.")
e = I.einsetzen(rep, B(FROG_D), diktat="Fuß rechts: Calcaneusneigungswinkel 10 Grad, Pes planus.")
check("f) Doppelung: Messwert mit gleicher Zahl und Diagnose schon diktiert → nicht doppelt, Hinweise",
      e.report.count("Calcaneusneigungswinkel") == 1 + 0 and "Pes planus rechts (Calc" not in e.report
      and "Hallux-valgus-Winkel rechts 24,3° (IB Lab FROG)." in e.report
      and any("Calcaneusneigungswinkel schon im Befund (10 grad)" in h for h in e.hinweise), e.report + str(e.hinweise))
rep = bericht("Fuß rechts in 2 Ebenen", "Calcaneusneigungswinkel 15°. Hallux valgus.", "Hallux valgus.")
e = I.einsetzen(rep, B(FROG_D), diktat="Fuß rechts: Calcaneusneigungswinkel 15 Grad. Hallux valgus.")
check("g) Widerspruch: diktiert 15°, IB Lab 10,0° → Diktat bleibt, IB-Lab-Wert nicht angefügt, sichtbarer Hinweis",
      "Calcaneusneigungswinkel 15°" in e.report and "10,0° (IB Lab FROG)" not in e.report
      and any("Calcaneusneigungswinkel im Befund 15°, laut IB Lab 10,0° – bitte prüfen" in h for h in e.hinweise),
      str(e.hinweise))
rep = bericht("Fuß rechts in 2 Ebenen", "Hallux valgus. Kein Plattfuß.", "Hallux valgus.")
e = I.einsetzen(rep, B(FROG_D), diktat="Fuß rechts: Hallux valgus, kein Plattfuß.")
check("   … Diktat verneint die Diagnose („kein Plattfuß“) → Pes planus nicht angefügt, Hinweis",
      "Pes planus" not in e.report and any("Diktat verneint „plattfuß“" in h for h in e.hinweise), str(e.hinweise))
rep = bericht("Fuß rechts in 2 Ebenen", "Senkfuß, sonst unauffällig.", "Senkfuß.")
e = I.einsetzen(rep, B(FROG_D), diktat="Fuß rechts: Senkfuß, sonst unauffällig.")
check("   … nur ein verwandtes Wort („Senkfuß“) → im Zweifel anhängen und markieren",
      "Pes planus rechts (Calcaneusneigungswinkel 10,0°)." in e.report
      and any("Befund nennt schon „senkfuß“" in h for h in e.hinweise), str(e.hinweise))
normal = pl.bypass_befund("Fuß rechts unauffällig.", T["fuß_in_2_ebenen"])
e = I.einsetzen(normal, B(FROG_D), diktat="Fuß rechts unauffällig.")
check("h) Normalbefund: Messwerte angefügt, Diagnosen NICHT ins unauffällige Ergebnis, Hinweis",
      "Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG)." in e.report and "Pes planus" not in e.report
      and e.report.rstrip().endswith("Regelrechte Darstellung des Fußskeletts rechts.")
      and any("nicht ins Ergebnis übernommen – Ergebnis unauffällig" in h for h in e.hinweise), e.report[-300:])
rep = bericht("Fuß rechts in 2 Ebenen", FUSS_TPL, "Hallux valgus.")
e = I.einsetzen(rep, B(FROG_D), diktat="Fuß rechts: Hallux valgus.")
check("i) Vorlagensatz „Fußgewölbe … regulär“ neben IB-Lab-Diagnose → Hinweis, Text bleibt",
      "Das Fußgewölbe ist regulär ausgebildet" in e.report and any(
          "Befundtext „Das Fußgewölbe ist regulär ausgebildet bei ordnun…“ widerspricht IB Lab" in h for h in e.hinweise),
      str(e.hinweise))
thorax = pl.br.rho_einfuegen(bericht("Thorax in 2 Ebenen", "Unauffällig.", "Unauffälliger Befund."), "8")
e = I.einsetzen(thorax, B(RHO_D), diktat="Thorax unauffällig. Rho 8.")
check("j) Rho: RaKScribes eigener Rho-Baustein steht schon da → IB-Lab-Rho nicht doppelt",
      e.report == thorax and e.hinweise == ["Rho: Rho-Text schon im Befund – nicht doppelt angefügt"], str(e.hinweise))
e = I.einsetzen(pl.br.rho_einfuegen(bericht("Thorax in 2 Ebenen", "Unauffällig.", "Unauffälliger Befund."), "6"),
                B(RHO_D), diktat="Thorax unauffällig. Rho 6.")
check("   … anderer Score diktiert (6 ≠ 8) → Widerspruch-Hinweis, nichts angefügt",
      any("Score im Befund 6, laut 16 Bit Rho 8 von 10" in h for h in e.hinweise), str(e.hinweise))
e = I.einsetzen(bericht("Thorax in 2 Ebenen", "Unauffällig.", "Unauffälliger Befund."), B(RHO_D), diktat="Thorax unauffällig.")
check("   … ohne eigenen Rho-Text: Score in den Befund, Ergebnis auch bei unauffälligem Ergebnis (wie Georgs Baustein)",
      "Rho-Score 8 von 10 (16 Bit Rho)." in e.report and "2. Als Zufallsbefund KI-gestützter Hinweis" in e.report
      and "1. Unauffälliger Befund." in e.report, e.report)
e = I.einsetzen(bericht("Handgelenk links in 2 Ebenen", "Distale Radiusfraktur.", "Distale Radiusfraktur."),
                B(RBF_D))
check("k) Hinweise des Bausteins (RBfracture, Entwürfe) nie im Befund, nur Anzeige",
      "RBfracture" not in e.report and I.anzeige_hinweise(B(RBF_D, RHO_D, FROG_BDS)) == [
          "FROG: 1 Messgröße(n) nicht zugeordnet (Katalog ergänzen)",
          "RBfracture: Fraktur-Verdacht Radius links – bitte prüfen.",
          "16 Bit Rho: Ergebnistext ist ein Entwurf (Regel rho-score-8, endgültiger Baustein von Georg ausständig) – "
          "bitte prüfen."],
      str(I.anzeige_hinweise(B(RBF_D, RHO_D, FROG_BDS))))
rep = bericht("Fuß rechts in 2 Ebenen", "Hallux valgus.", "Hallux valgus.")
e1 = I.einsetzen(rep, B(FROG_D), diktat="Hallux valgus.")
e2 = I.einsetzen(e1.report, B(FROG_BDS), diktat="Hallux valgus.", entfernen=e1.eingesetzt[("T-0021", "frog")])
check("l) neue Fassung ersetzt die alte wörtlich (v1 raus, v2 rein, Ergebnis neu durchgezählt)",
      "Hallux-valgus-Winkel rechts 24,3°" not in e2.report and "Calcaneusneigungswinkel links 12,4° (IB Lab FROG)." in e2.report
      and e2.report.count("Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG).") == 1 and "Pes planus rechts" not in e2.report
      and "2. Pes planus beidseits (Calcaneusneigungswinkel rechts 10,0°, links 12,4°)." in e2.report
      and e2.nicht_entfernt == [], e2.report)
e3 = I.einsetzen(e1.report, B(FROG_D), diktat="Hallux valgus.")
check("   … dieselbe Fassung noch einmal → nichts doppelt (idempotent)", e3.report == e1.report, e3.report)
ordi = "## Mammographie beidseits\n\n## Befund\nText.\n\n## Ergebnis\nPunkt eins\nPunkt zwei"
e = I.einsetzen(ordi, B(dict(RHO_D, accno="1")), diktat="Baustein Mammo.")
check("m) wörtlicher Ordi-Baustein (mehrere unnummerierte Punkte) bleibt unnummeriert",
      "\nPunkt eins\nPunkt zwei\nAls Zufallsbefund" in e.report, e.report)
blk = I.prompt_block(B(FROG_D, LAMA_D, RBF_D))
check("n) Gen-Prompt <ibl_messwerte>: nur Messgrößen-Namen, keine Zahlen, keine Diagnosen, Regeln",
      "- FROG: Calcaneusneigungswinkel, Hallux-valgus-Winkel" in blk and "- LAMA: HKA-Winkel, Beinlängendifferenz" in blk
      and "RBfracture" not in blk and not any(c.isdigit() for c in blk.replace("ibl_messwerte", ""))
      and "Pes planus" not in blk and "Nenne diese Messwerte nicht selbst" in blk and I.prompt_block(B(RBF_D)) == "", blk)
blk = I.prompt_block(B(FROG_D), T["fuß_in_2_ebenen"]["body"])
check("   … mit Vorlage: widersprechender Vorlagensatz wörtlich als „nicht übernehmen“ (nur bei IB-Lab-Diagnose)",
      "„Das Fußgewölbe ist regulär ausgebildet bei ordnungsgemäßen Gelenkwinkeln.“" in blk and "nicht übernehmen" in blk
      and "nicht übernehmen" not in I.prompt_block(B(dict(FROG_D, ergebnis=[])), T["fuß_in_2_ebenen"]["body"]), blk)
check("   … je Abschnitt nur passende Module (FROG zum Fuß, nicht zur LWS)",
      [b.name for b in I.fuer_abschnitt(B(FROG_D, LAMA_D, RHO_D), {"fuss"})] == ["FROG"]
      and I.fuer_abschnitt(B(FROG_D), {"lws"}) == [])

# ───────────────────────────── Teil 2: Pipeline mit Bausteinen ─────────────────────────────


def ki_attrappe(prompts):
    def llm(p):
        prompts.append(p)
        titel = p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0]
        diktat = p.split("<diktat>\n", 1)[1].split("\n</diktat>")[0]
        rest = diktat.split(":", 1)[-1].strip() or "Unauffälliger Befund."
        return f"## {titel}\n\n## Befund\nBeschreibung laut Diktat: {diktat}\n\n## Ergebnis\n{rest}"
    return llm


def kontext(prompts, ibl=None, cas=None):
    return pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=ki_attrappe(prompts), log=lambda *a: None,
                      cas=cas, ibl=ibl)


prompts = []
erg = pl.befund_aus_diktat("Fuß rechts: Hallux valgus. LWS: Osteochondrose L4/5.",
                           kontext(prompts, I.IblKontext(B(FROG_D)),
                                   cv.CasHinweis([L("x-fuss", "Fuß rechts", "Röntgen", "fuß_in_2_ebenen", "rechts"),
                                                  L("x-lws", "LWS", "Röntgen", "lendenwirbelsäule_in_2_ebenen")], T)))
fuss, lws = abschnitt_von(erg.report, "Fuß"), abschnitt_von(erg.report, "Lendenwirbel")
check("Pipeline: <ibl_messwerte> nur im Prompt des Fuß-Abschnitts, nicht der LWS",
      len(prompts) == 2 and ["<ibl_messwerte>" in p for p in prompts] == [True, False], str(len(prompts)))
check("… Messwerte + neue Diagnose im Fuß-Befund, nichts in der LWS, Hinweis in erg.ibl, nicht im Befund",
      "Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG)." in fuss and "Pes planus rechts" in fuss
      and "IB Lab" not in lws and erg.ibl is not None and erg.ibl.hinweise and "bitte prüfen" not in erg.report
      and erg.vollstaendig, erg.report)
prompts = []
erg = pl.befund_aus_diktat("Fuß rechts unauffällig.", kontext(prompts, I.IblKontext(B(FROG_D))))
check("Pipeline Normalbefund (ohne KI): Messwerte drin, Diagnosen nicht, Hinweis", prompts == []
      and "Hallux-valgus-Winkel rechts 24,3° (IB Lab FROG)." in erg.report and "Pes planus" not in erg.report
      and any("Ergebnis unauffällig" in h for h in erg.ibl.hinweise))
prompts = []
erg = pl.befund_aus_diktat("Ganzbein: Genu varum rechts.", kontext(prompts, I.IblKontext(B(LAMA_D))))
check("Pipeline LAMA Ganzbein: HKA/Beinlängendifferenz eingesetzt, Genu varum nicht doppelt",
      "HKA-Winkel links 179,1° (IB Lab LAMA)." in erg.report and erg.report.count("Genu varum") == 2
      and "Beinlängendifferenz von 15 mm." in erg.report, erg.report)

# ohne Bausteine: bit-gleich wie bisher (IBL-Funktionen werden gar nicht aufgerufen)
gesperrt = {}
for name in ("einsetzen", "prompt_block", "fuer_abschnitt"):
    gesperrt[name] = getattr(I, name)
    setattr(I, name, lambda *a, n=name, **k: (_ for _ in ()).throw(AssertionError(f"ibl_bausteine.{n} ohne Bausteine")))
try:
    ok = True
    for diktat in ("Fuß rechts: Hallux valgus.", "Fuß rechts unauffällig.", "Schulter rechts: Omarthrose. Ellbogen rechts: "
                                                                           "Epicondylitis.", "Rho 8. LWS: Osteochondrose."):
        for ibl in (None, I.IblKontext(B(RBF_D))):          # nur Hinweise (kein Inhalt) = wie ohne Bausteine
            alt, neu = [], []
            e0 = pl.befund_aus_diktat(diktat, kontext(alt))
            e1 = pl.befund_aus_diktat(diktat, kontext(neu, ibl))
            ok = ok and alt == neu and e0.report == e1.report and e1.ibl is None
    check("ohne Bausteine (bzw. nur Hinweise): Prompts + Befund bit-gleich, keine IBL-Funktion aufgerufen", ok)
finally:
    for name, f in gesperrt.items():
        setattr(I, name, f)
check("IblKontext ohne Inhalt ist „falsch“", not I.IblKontext(B(RBF_D)) and not I.IblKontext([]) and I.IblKontext(B(FROG_D)))

# ───────────────────────────── Teil 3: EXE-Ablauf ─────────────────────────────
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: False
cas_mod = mod._cas
ORDNER = tempfile.mkdtemp(prefix="rks_ibl_")
LLM_PROMPTS = []
mod._llm_aufruf = ki_attrappe(LLM_PROMPTS)


def ablegen(nr, aid):
    with open(os.path.join(ORDNER, cas_mod.AUFTRAG), "w", encoding="utf-8") as f:
        json.dump({"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": "kp", "bruecke_pid": 4242,
                   "zeit": time.time(), "zeit_text": "", "testbefund": False}, f)


def ibl_ablegen(aid, nr, bausteine, roh=None):
    p = os.path.join(ORDNER, f"cas_ibl_{aid}.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(roh if roh is not None else json.dumps({"protokoll": 1, "auftrag_id": aid, "nr": nr,
                                                        "quelle": "ibl-abholer/1", "bausteine": bausteine,
                                                        "zeit": time.time()}, ensure_ascii=False))
    os.replace(tmp, p)
    t = time.time() + len(ibl_ablagen)        # Änderungszeit sicher neu (die EXE liest nur bei Änderung)
    ibl_ablagen.append(p)
    os.utime(p, (t, t))


ibl_ablagen = []


def antwort(aid):
    try:
        with open(os.path.join(ORDNER, f"cas_antwort_{aid}.json"), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


class FakeBand:
    def __init__(self):
        self.sichtbar, self.cfg = False, {}

    def pack(self, **k):
        self.sichtbar = True

    def pack_forget(self):
        self.sichtbar = False

    def winfo_ismapped(self):
        return self.sichtbar

    def configure(self, **k):
        self.cfg.update(k)

    def cget(self, k):
        return self.cfg.get(k, "")


class Var:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


def neue_app():
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
    S.CLIPBOARD.data = {13: "ALT"}
    app = S.baue_app(mod)
    app._cas, app._cas_aufnahmen, app._cas_test = None, [], False
    app._cas_kanal = cas_mod.Kanal(ORDNER, pid=777, version="3.13.0", prozess_lebt=lambda pid: True)
    app._fensterziel = mod._fz.Fensterziel(None)
    app.cas_label, app.cas_hinweis_label, app.bestaetigung_label = S.FakeWidget(), S.FakeWidget(), S.FakeWidget()
    app.cas_band, app.bestaetigung_band, app.main_container = FakeBand(), FakeBand(), None
    app.ibl_label, app.ibl_hinweis_label = FakeBand(), FakeBand()
    app.ibl_zeile, app.ibl_knopf = FakeBand(), FakeBand()
    app.ibl_var = Var(True)
    app.destroy = lambda: None
    return app


def bis_ruhe(app, timeout=8):
    ok = S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)
    S.pump(app, lambda: False, 0.2)
    return ok


app = neue_app()
ablegen("20261013002", "z1")
app._cas_einmal()
check("Auftrag ohne IB-Lab-Datei: keine IB-Lab-Zeile (wie 3.12.0)", app._cas is not None and app._cas.ibl is None
      and not app.ibl_zeile.sichtbar and app.ibl_label.cget("text") == "")
ibl_ablegen("z1", "20261013002", [], roh='{"auftrag_id": "z1", "bau')
app._cas_einmal()
check("halb geschriebene Datei → nächster Takt", app._cas.ibl is None)
ibl_ablegen("z1", "20261013002", [FROG_D])
app._cas_einmal()
check("Baustein kommt: Band-Zeile „IB Lab: FROG rechts ✓“ sichtbar, kurz hervorgehoben, Band höher",
      app.ibl_label.cget("text") == "IB Lab: FROG rechts ✓" and app.ibl_zeile.sichtbar
      and getattr(app, "_ibl_hervorgehoben", 0) == 1 and app.ibl_label.cget("fg_color") == mod.READY_GREEN
      and app.cas_band.cfg.get("height") == 76 and not app.ibl_knopf.sichtbar, app.ibl_label.cget("text"))
S.pump(app, lambda: False, 0.2)
check("… Hervorhebung geht wieder weg", app.ibl_label.cget("fg_color") == "transparent")
app._cas_einmal()
check("unveränderte Datei wird nicht neu gelesen (keine zweite Hervorhebung)", app._ibl_hervorgehoben == 1)
app.transcript_text.text = "Fuß rechts: Hallux valgus."
app.befund_aus_text(kontrolle=True)
bis_ruhe(app)
check("INS mit Baustein: Messwerte + neue Diagnose im Befund, zur Kontrolle, nichts eingefügt",
      "Calcaneusneigungswinkel rechts 10,0° (IB Lab FROG)." in app.result_text.text
      and "Pes planus rechts (Calcaneusneigungswinkel 10,0°)." in app.result_text.text
      and app._status_raw == "KONTROLLE" and S.AUFZ.tasten == [], app.result_text.text[:300])
check("… Gen-Prompt informiert (<ibl_messwerte>), Hinweise amber in der IB-Lab-Zeile, Stand gemerkt",
      LLM_PROMPTS and "<ibl_messwerte>" in LLM_PROMPTS[-1] and app.ibl_hinweis_label.cget("text").startswith("⚠  FROG:")
      and app._ibl_im_befund == {("T-0021", "frog"): 1} and not app.ibl_knopf.sichtbar,
      app.ibl_hinweis_label.cget("text"))
ibl_ablegen("z1", "20261013002", [FROG_BDS, LAMA_D])
app._cas_einmal()
check("v3.14.0 neue Fassung + weiteres Modul nach dem Befund: automatisch SICHTBAR eingefügt (Hinweis, hervorgehoben), "
      "kein Knopf nötig", "12,4°" in app.result_text.text and not app.ibl_knopf.sichtbar
      and getattr(app, "_ibl_auto_n", 0) == 1 and any("nachgekommen" in h for h in S.AUFZ.hinweise[-3:])
      if hasattr(S.AUFZ, "hinweise") else "12,4°" in app.result_text.text and getattr(app, "_ibl_auto_n", 0) == 1,
      app.ibl_label.cget("text"))
app.ibl_einfuegen()
check("… v1-Zeilen ersetzt, v2 drin, LAMA ohne Ganzbein-Abschnitt → Absatz am Ende + Hinweis (Knopf danach ohne Wirkung)",
      "Hallux-valgus-Winkel rechts 24,3°" not in app.result_text.text
      and "Calcaneusneigungswinkel links 12,4° (IB Lab FROG)." in app.result_text.text
      and app.result_text.text.rstrip().endswith("Beinlängendifferenz von 15 mm.") and not app.ibl_knopf.sichtbar
      and any("LAMA beidseits: keiner Untersuchung eindeutig zuzuordnen" in h for h in app._ibl_hinweise)
      and any("Katalog ergänzen" in h for h in app._ibl_hinweise) and any("HKA-Konvention" in h for h in app._ibl_hinweise),
      app.result_text.text[-400:])
app._ibl_details()
check("Klick auf die IB-Lab-Zeile zeigt alle Werte und Hinweise", S.AUFZ.dialoge and S.AUFZ.dialoge[-1][0] == "showinfo"
      and "LAMA beidseits – Version 1 (im Befund)" in S.AUFZ.dialoge[-1][2], str(S.AUFZ.dialoge[-1:])[:200])
befund = app.result_text.text
app.befund_fertig()
check("v3.14.0 erstes EOL kurz nach dem automatischen Einsetzen: noch nicht gesendet (bitte prüfen)",
      antwort("z1").get("status") != "fertig" and app._cas is not None)
app.befund_fertig()
check("EOL: Befund samt IB-Lab-Werten an CAS, grünes Band, IB-Lab-Zeile weg",
      antwort("z1").get("status") == "fertig" and app.bestaetigung_band.sichtbar and not app.ibl_zeile.sichtbar
      and app.ibl_label.cget("text") == "" and getattr(app, "_ibl_hinweise", []) == [])
with open(os.path.join(ORDNER, "cas_ergebnis_20261013002.txt"), encoding="utf-8") as f:
    check("… übergebener Text = sichtbarer Befund (Messwerte 1:1)", f.read() == befund.strip()
          and "Calcaneusneigungswinkel links 12,4° (IB Lab FROG)." in befund)

ablegen("20261013003", "z2")
app._cas_einmal()
ibl_ablegen("z2", "20261013999", [FROG_D])      # andere Diktatnummer
app._cas_einmal()
check("IB-Lab-Datei zu anderer Diktatnummer wird verworfen", app._cas.ibl is None and not app.ibl_zeile.sichtbar)
ibl_ablegen("z2", "20261013003", [FROG_D])
app._cas_einmal()
app.ibl_var = Var(False)
app._ibl_umgeschaltet()
check("Menü „IB-Lab-Bausteine übernehmen“ aus: Zeile grau mit Hinweis aufs Menü",
      app.ibl_label.cget("text") == "IB Lab: FROG rechts  (Übernahme aus – Menü)"
      and app.ibl_label.cget("text_color") == mod.TEXT_FAINT, app.ibl_label.cget("text"))
LLM_PROMPTS.clear()
app.transcript_text.text = "Fuß rechts: Hallux valgus."
app.befund_aus_text(kontrolle=True)
bis_ruhe(app)
check("… aus: Befund wie 3.12.0 (keine Werte, kein <ibl_messwerte>, keine Hinweise, kein Knopf)",
      "IB Lab" not in app.result_text.text and LLM_PROMPTS and "<ibl_messwerte>" not in LLM_PROMPTS[-1]
      and getattr(app, "_ibl_hinweise", []) == [] and not app.ibl_knopf.sichtbar)
app.ibl_var = Var(True)
app._ibl_umgeschaltet()
check("… wieder an: Knopf bietet die Werte für den schon erstellten Befund an", app.ibl_knopf.sichtbar)
app.reset_dictation()
check("F9: Befund + Hinweise weg, Knopf weg, Bausteine bleiben beim Auftrag", app.result_text.text == ""
      and not app.ibl_knopf.sichtbar and app.ibl_zeile.sichtbar and app._ibl_im_befund == {})
app.cas_abbrechen()
check("Abbrechen: IB-Lab-Zeile weg", not app.ibl_zeile.sichtbar)
app.result_text.text = "## Fuß rechts in 2 Ebenen\n\n## Befund\nText vom vorigen, abgebrochenen Auftrag.\n\n## Ergebnis\nX."
ablegen("20261013004", "z3")
app._cas_einmal()
ibl_ablegen("z3", "20261013004", [FROG_D])
app._cas_einmal()
check("Text vom vorigen Auftrag (nach „Abbrechen“ stehen geblieben): kein Knopf – Werte erst beim nächsten INS",
      app.ibl_zeile.sichtbar and not app.ibl_knopf.sichtbar and app.ibl_label.cget("text") == "IB Lab: FROG rechts ✓"
      and app._ibl_offen() == [], app.ibl_label.cget("text"))
app.cas_abbrechen()

# ───────────────────────────── Teil 4: gegen die echte Brückenseite (nur Mac) ─────────────────────────────
BR = pathlib.Path.home() / "dev" / "ris-mods" / "bruecke"
if (BR / "ibl_bausteine.py").exists():
    sys.path.insert(0, str(BR))
    import auftrag as br_auftrag  # noqa: E402
    spec = importlib.util.spec_from_file_location("bruecke_ibl", BR / "ibl_bausteine.py")
    br_ibl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(br_ibl)
    ablage = tempfile.mkdtemp(prefix="rks_ibl_ablage_")
    # Ablage-JSON im Format des IB-Lab-Abholers (ibl-abholer/1); Texte wie vorbefund.py zu ibl/beispiele/frog_beidseits
    stamm = br_ibl.stamm("20261013007", 1, "frog")       # Dateiname wie vom Abholer (Schema nur im privaten Repo)
    with open(os.path.join(ablage, stamm + ".json"), "w", encoding="utf-8") as f:
        json.dump({"format": "ibl-abholer/1", "programm": "ibl-abholer 1.0.1", "accession_number": stamm.split("_")[0],
                   "modul": "frog", "modul_name": "IB Lab FROG", "studien_uid": "1.2", "studiendatum": "20261013",
                   "version": 1, "erstellt": "2026-10-13T18:00:00", "aktualisiert": "2026-10-13T18:00:00", "kontext": {},
                   "text": "…", "vorbefund": {"befundteil": FROG_BDS["befundteil"],
                                              "ergebnis_punkte": FROG_BDS["ergebnis"], "hinweise_fuer_befunder": [],
                                              "nicht_zugeordnet": FROG_BDS["nicht_zugeordnet"]},
                   "quellen": [{"sop": "1.2.3", "seiten": ["rechts", "links"], "eingaben": []}], "verlauf": []}, f)
    beob = br_ibl.Beobachter("20261013007", ablage, 20, time.time).starten(synchron=True)
    beob.takt()
    br_auftrag.Kanal(ORDNER, pid=4242).ibl_senden("y1", beob.datei_inhalt("y1"))
    a = cas_mod.Auftrag({"auftrag_id": "y1", "nr": "20261013007"})
    a.ibl = cas_mod.Kanal(ORDNER).ibl_lesen(a)
    got = I.aus_liste(a.ibl)
    check("Protokoll gegen bruecke/ibl_bausteine.py: Band „IB Lab: FROG beidseits ✓“, Zeilen 1:1",
          I.band_text(got) == "IB Lab: FROG beidseits ✓" and got[0].befundteil == FROG_BDS["befundteil"]
          and got[0].ziffer == 1 and got[0].version == 1, str(a.ibl)[:200])
    e = I.einsetzen(bericht("Fuß beidseits in 2 Ebenen", "Hallux valgus beidseits.", "Hallux valgus beidseits."), got)
    check("… eingesetzt, Gate ok", I.gate(e.report, e.zeilen) == [] and "Calcaneusneigungswinkel links 12,4° (IB Lab FROG)."
          in e.report)
    br_auftrag.Kanal(ORDNER, pid=4242).aufraeumen("y1", "20261013007")
    check("… Brücke räumt cas_ibl_<id>.json auf", not os.path.exists(os.path.join(ORDNER, "cas_ibl_y1.json")))
else:
    print("(Teil 4 übersprungen: ~/dev/ris-mods/bruecke/ibl_bausteine.py nicht vorhanden)")

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
