"""Gate kaiscribe-ursula-2011-text-n1 – Ursula Hofmeisters Durchsicht der KaiScribe-Briefe vom 20.11.2026 (Text/Struktur).
Die Textregeln (EXE = Web) prüft befund_regeln_test.py (Fixtures „ursula_2011“); hier die ganze EXE-Kette mit KI-Attrappe:
   6   Ganzbein (paarige Region): Seite der CAS-Leistung in die Überschrift, wenn die KI sie weglässt; CAS ohne Seite → rote
       Prüfzeile – auch beim nicht diktierten Teil (Normalbefund laut CAS); Gegenprobe: diktierte/andere Seite bleibt
   5   Teil ohne Inhalt / loses Regions-Wort fallen am Ende der Kette weg; reiner IB-Lab-Teil (LAMA) bleibt mit Titel
   8   keine Leerzeile zwischen „## Ergebnis“ und dem Ergebnistext
   1   Ergebnistext als Überschrift („## Osteochondrose L4/5.“) → Text
   4   HWS ohne Seite im Titel, „50%ige“, „Im Übrigen“ nur einmal hintereinander
   2/7 Belege bestehender Regeln: Rho-Schlussbefund mit eigener Überschrift, ein Punkt ohne Nummer; Zehe ohne Nummer → rote
       Prüfzeile (georg-strahl-nummer)
Keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_ursula_2011.py"""
import json, pathlib, re, sys
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
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def L(kurz, text, vorlage, seite, ziffer=1):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": "Röntgen", "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True, "ziffer": ziffer}


def kontext(llm, leistungen=None, bausteine=None, log=None):
    cas = cv.CasHinweis(leistungen, T) if leistungen else None
    ibl = I.IblKontext(I.aus_liste(bausteine), cas_leistungen=leistungen) if bausteine else None
    return pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=llm, log=log or (lambda *a: None),
                      cas=cas, ibl=ibl)


def titel(report):
    return [z[3:] for z in report.split("\n") if z.startswith("## ") and z[3:] not in ("Befund", "Ergebnis")]


GB_KI = "## Ganzbeinaufnahme im Stand\n\n## Befund\nVarusfehlstellung.\n\n## Ergebnis\nVarusfehlstellung."
SEITE_FEHLT = "Seite weder in der CAS-Leistung noch im Diktat"

# ───────────────────────────── 6: Ganzbein-Überschrift mit Seite ─────────────────────────────
erg = pl.befund_aus_diktat("Ganzbeinaufnahme: Varusfehlstellung.",
                           kontext(lambda p: GB_KI, [L("gb", "Ganzbein re.", "ganzbeinaufnahme_im_stand", "rechts")]))
check("6: CAS „Ganzbein re.“, KI-Titel ohne Seite → „Ganzbeinaufnahme im Stand rechts“",
      titel(erg.report) == ["Ganzbeinaufnahme im Stand rechts"], erg.report)
erg = pl.befund_aus_diktat("Ganzbeinaufnahme links: Varusfehlstellung.",
                           kontext(lambda p: GB_KI.replace("im Stand", "im Stand links"),
                                   [L("gb", "Ganzbein re.", "ganzbeinaufnahme_im_stand", "rechts")]))
check("6 Gegenprobe: Titel nennt schon eine Seite → bleibt (nie zwei Seiten)",
      titel(erg.report) == ["Ganzbeinaufnahme im Stand links"], erg.report)
erg = pl.befund_aus_diktat("Ganzbeinaufnahme: Varusfehlstellung.",
                           kontext(lambda p: GB_KI, [L("gb", "Ganzbein", "ganzbeinaufnahme_im_stand", None)]))
check("6: CAS ohne Seite, Diktat ohne Seite → Titel ohne Seite + rote Prüfzeile (nie geraten)",
      titel(erg.report) == ["Ganzbeinaufnahme im Stand"] and any(SEITE_FEHLT in h for h in erg.cas_hinweise),
      (erg.report, erg.cas_hinweise))
LWS = L("lws", "LWS", "lendenwirbelsäule_in_2_ebenen", None, ziffer=1)
LWS_KI = "## Lendenwirbelsäule in 2 Ebenen\n\n## Befund\nOsteochondrose L4/5 mit Höhenminderung.\n\n## Ergebnis\nOsteochondrose L4/5."
erg = pl.befund_aus_diktat("Lendenwirbelsäule: Osteochondrose L4/5.",
                           kontext(lambda p: LWS_KI, [LWS, L("gb", "Ganzbein", "ganzbeinaufnahme_im_stand", None, ziffer=2)]))
check("6: nicht diktierter Ganzbein-Teil ohne Seite (Normalbefund laut CAS) → auch dort rote Prüfzeile",
      any(SEITE_FEHLT in h for h in erg.cas_hinweise) and any(cv.NICHT_DIKTIERT_NORMAL in h for h in erg.cas_hinweise),
      erg.cas_hinweise)
check("6 Gegenprobe: Wirbelsäule (nicht paarig) bekommt keine Seite und keine Seiten-Prüfzeile",
      "Lendenwirbelsäule in 2 Ebenen" in titel(erg.report) and not erg.fehler
      and not any(h.startswith("LWS") and SEITE_FEHLT in h for h in erg.cas_hinweise), (erg.report, erg.cas_hinweise))

# ───────────────────────────── 5 + 8 + 1: Schluss der Kette ─────────────────────────────
KNIE_KI = ("## Kniegelenk rechts in 2 Ebenen\n\n## Befund\nMäßige Gonarthrose medial.\n\n## Ergebnis\n\n"
           "Mäßige Gonarthrose rechts medial.\n\n## Defileeaufnahme Patella einseitig\n\nBecken")
erg = pl.befund_aus_diktat("Kniegelenk rechts: mäßige Gonarthrose medial.", kontext(lambda p: KNIE_KI))
check("5 (RH 120/47): leere Überschrift „Defileeaufnahme Patella einseitig“ und loses „Becken“ fallen weg",
      titel(erg.report) == ["Kniegelenk rechts in 2 Ebenen"] and "Becken" not in erg.report
      and erg.report.rstrip().endswith("(Arthrose Grad 3 nach Kellgren & Lawrence)."), erg.report)
check("8 (RH 37): keine Leerzeile zwischen „## Ergebnis“ und dem Ergebnistext", "## Ergebnis\n\n" not in erg.report, erg.report)
erg = pl.befund_aus_diktat("Lendenwirbelsäule: Osteochondrose L4/5.",
                           kontext(lambda p: LWS_KI.replace("## Ergebnis\nOsteochondrose", "## Ergebnis\n## Osteochondrose")))
check("1 (RH 31/119): Ergebnistext als Überschrift → normaler Ergebnistext (genau einmal)",
      titel(erg.report) == ["Lendenwirbelsäule in 2 Ebenen"] and erg.report.count("Osteochondrose L4/5.") == 1 and "\n## Osteochondrose" not in erg.report, erg.report)

LAMA_SCHLUSS = ("HKA = Hüft-Knie-Sprunggelenk-Winkel, MAD = mechanische Achsabweichung (Mikulicz-Linie/Traglinie des "
                "Ganzbeines). Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.")
LAMA = {"accno": "999001200077", "ziffer": 2, "modul": "lama", "name": "LAMA", "version": 1, "seiten": ["rechts", "links"],
        "befundteil": ["HKA-Winkel rechts 178,1° (IB Lab LAMA)."],
        "ergebnis": ["Regelrechte Beinachse beidseits (HKA rechts 1,9°, links 0,9°; MAD rechts 12,6 mm, links 11,7 mm).",
                     LAMA_SCHLUSS], "hinweise": []}
erg = pl.befund_aus_diktat("Lendenwirbelsäule: Osteochondrose L4/5.",
                           kontext(lambda p: LWS_KI, [LWS, L("gb", "Ganzbein bds.", "ganzbeinaufnahme_im_stand", "beidseits", 2)],
                                   [LAMA]))
check("5 Gegenprobe: reiner IB-Lab-Teil (Ganzbein mit LAMA, nicht diktiert) bleibt mit Titel und LAMA-Ergebnis",
      any(t.startswith("Ganzbein") for t in titel(erg.report)) and "Regelrechte Beinachse beidseits" in erg.report, erg.report)
erg = pl.befund_aus_diktat("Kniegelenk rechts: Erguss.", kontext(lambda p: (
    "## Kniegelenk rechts in 2 Ebenen\n\n## Befund\nErguss.\n\n## Ergebnis\nGelenkerguss rechts.")))
check("5 Gegenprobe: diktierter Teil mit kurzem Text bleibt", titel(erg.report) == ["Kniegelenk rechts in 2 Ebenen"]
      and "Erguss" in erg.report, erg.report)

# ───────────────────────────── 4: HWS ohne Seite, Prozent, „Im Übrigen“ ─────────────────────────────
erg = pl.befund_aus_diktat("HWS: 50-prozentige Höhenminderung C5/6, Unkovertebralarthrose beidseits.", kontext(lambda p: (
    "## HWS beidseits in 2 Ebenen\n\n## Befund\n50-prozentige Höhenminderung C5/6. Unkovertebralarthrose beidseits. "
    "Im Übrigen sind die Weichteile unauffällig. Im Übrigen sind Mineralgehalt und Knochenstruktur normal.\n\n"
    "## Ergebnis\n1. 50-prozentige Höhenminderung C5/6.\n2. Unkovertebralarthrose beidseits.")))
check("4c: HWS-Überschrift ohne „beidseits“, im Befundtext bleibt das diktierte „beidseits“",
      titel(erg.report) == ["HWS in 2 Ebenen"] and "Unkovertebralarthrose beidseits" in erg.report, erg.report)
check("4b: „50-prozentige“ → „50%ige“ (Befund und Ergebnis)",
      "prozentig" not in erg.report and erg.report.count("50%ige Höhenminderung") == 2, erg.report)
check("4a: „Im Übrigen“ nur beim ersten Satz der Folge",
      erg.report.count("Im Übrigen") == 1, erg.report)

# ───────────────────────────── 2/7: Belege bestehender Regeln ─────────────────────────────
erg = pl.befund_aus_diktat("Hüftgelenk rechts: geringe Coxarthrose. Rho 8.", kontext(lambda p: (
    "## Hüftgelenk rechts in 2 Ebenen\n\n## Befund\nGeringe Coxarthrose.\n\n## Ergebnis\nGeringe Coxarthrose rechts.")))
teile = erg.report.split(f"## {br.RHO_TITEL}")
check("2 (RH 49, rho-titel-nummer seit 3.20/3.22): Rho-Teil mit eigener Überschrift, ein Punkt ohne Nummer",
      len(teile) == 2 and br.RHO_ERGEBNIS in teile[1] and not re.search(r"(?m)^\d+\. Opportunistisch", erg.report), erg.report)
erg = pl.befund_aus_diktat("Zehe links: kleine Verkalkung plantar.", kontext(lambda p: (
    "## Zehe links in 2 Ebenen\n\n## Befund\nKleine Verkalkung plantar.\n\n## Ergebnis\nKleine Verkalkung plantar links."),
    [L("zehl", "Zehe li.", "zehe_in_2_ebenen", "links")]))
check("7 (RH 55, georg-strahl-nummer seit 3.20.0): Zehe ohne Nummer → rote Prüfzeile, nichts geraten",
      any("Nummer (I–V) nicht diktiert" in h for h in erg.cas_hinweise), erg.cas_hinweise)

print(f"\n{'✅ ALLE GRÜN' if not fails else f'❌ {fails} FAIL'}")
sys.exit(1 if fails else 0)
