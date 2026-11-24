"""Gate IB Lab HIPPO → Becken-/Hüft-Text (Georg Riegler 18.11.2026, GO 19:58, Brief kaiscribe-hippo-ergebnistext-n1).
Die Bausteine (tests/offline/hippo_bausteine.json) entstehen mit dem Abholer-Code (ris-mods ibl/hippo_ergebnis.py) und der
Brücke aus den echten Fällen vom 18.11.2026 (anonym: lfd. Nr. + TT.MM., nur Messwerte). Geprüft: CAS-Vorlagen
„Beckenübersicht stehend“ (vier Sätze heraus, HIPPO-Sätze am Anfang), „Beckenübersicht und Hüfte“ und Prothesen-Vorlage (nur
die Zeile „Beckenschiefstand: …“ ersetzt), Hüfte, Kind < 16 (nur beschreibend), Prüfzeile bei widersprechendem
Vorlagensatz, Normal-Ergebnis ersetzt, Schlussanmerkung ohne Nummer, schon diktiert, zweimal einsetzen, Gerüst,
Gen-Prompt. Snapshot aller Texte: tests/offline/snapshots/hippo_befunde.txt.
Aufruf: python3 tests/offline/test_ibl_hippo_text.py [--snapshot-schreiben]"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import ibl_bausteine as I  # noqa: E402

HIER = pathlib.Path(__file__).resolve().parent
T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
FAELLE = json.loads((HIER / "hippo_bausteine.json").read_text(encoding="utf-8"))
SNAP = HIER / "snapshots" / "hippo_befunde.txt"
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def baustein(nr):
    return I.aus_liste([next(f["baustein"] for f in FAELLE if f["nr"] == nr)])


def vorlage(key):
    v = T[key]
    return v["display_name"], v["body"].split("\n", 2)[2], v["ergebnis"]


def bericht(key, befund=None, ergebnis=None):
    titel, body, erg = vorlage(key)
    return f"## {titel}\n\n## Befund\n{body if befund is None else befund}\n\n## Ergebnis\n{erg if ergebnis is None else ergebnis}"


VIER = ["Anatomisch normale und symmetrische Form des Beckenskeletts.", "Beide Beckenschaufeln stehen gleichhoch.",
        "Der CCD-Winkel ist im Normbereich.",
        "Die artikulierenden Flächen sind kongruent bei guter Deckung der Hüftköpfe durch die Pfannen."]
ENDE = "Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen."

# ── Fall 61: nur Beckenschiefstand/BLD (Beckenübersicht stehend) ──
B61 = baustein(61)
e = I.einsetzen(bericht("beckenübersicht_stehend"), B61, diktat="Beckenübersicht.")
befund = e.report.split("## Befund\n")[1].split("\n\n## Ergebnis")[0]
check("Fall 61: HIPPO-Sätze am Anfang, danach „Mineralgehalt und Knochenstruktur …“",
      befund.startswith("Geringer Beckenschiefstand von 9 mm, rechts tieferstehend. Beinlängendifferenz von 3 mm, links "
                        "kürzer. Mineralgehalt und Knochenstruktur sind regelrecht."), befund)
check("Fall 61: die vier Vorlagen-Sätze entfallen immer (auch ohne Auffälligkeit)", not [s for s in VIER if s in befund], befund)
check("Fall 61: kein Ergebnispunkt aus HIPPO – Normal-Ergebnis bleibt, Schluss ohne Nummer darunter",
      e.report.endswith("## Ergebnis\nRegelrechte Darstellung des Beckens.\n" + ENDE), e.report)
check("Fall 61: keine Prüfzeile, keine Messzeile", not e.hinweise and "(IB Lab HIPPO)" not in e.report, e.hinweise)

# ── Fall 52: grenzwertig + steiles Pfannendach, Coxa valga beidseits ──
B52 = baustein(52)
e = I.einsetzen(bericht("beckenübersicht_stehend"), B52, diktat="Beckenübersicht.")
P52 = ("Grenzwertige Überdachung des rechten Hüftkopfes bei steilem Pfannendach. Grenzwertige Überdachung des linken "
       "Hüftkopfes. Coxa valga beidseits.")
S52 = ("LCE = lateraler Center-Edge-Winkel nach Wiberg, AI = Acetabulumindex nach Tönnis, CCD = Caput-Collum-Diaphysen-"
       "Winkel. " + ENDE)
check("Fall 52: Begriffe als (einziger, unnummerierter) Punkt, Normal-Ergebnis ersetzt, Schluss mit Abkürzungen",
      e.report.endswith(f"## Ergebnis\n{P52}\n{S52}"), e.report)
check("Fall 52: Winkel-Sätze mit Wert ohne Norm",
      "Der LCE-Winkel beträgt rechts 23° und links 22°. Der AI-Winkel beträgt rechts 13°. Der CCD-Winkel beträgt rechts "
      "145° und links 146°. Mineralgehalt" in e.report and "(Norm" not in e.report and "[" not in e.report, e.report)
check("Fall 52: rote Prüfzeile für „Regelrechte Abbildung beider Pfannendächer.“ (bleibt im Text)",
      any("Regelrechte Abbildung beider Pfannendächer" in h and "prüfen" in h for h in e.hinweise)
      and "Regelrechte Abbildung beider Pfannendächer." in e.report, e.hinweise)
check("Fall 52: Gate – jede eingesetzte Zeile steht wörtlich im Befund", not I.gate(e.report, e.zeilen), e.zeilen)

# Diktat mit Diktiertem: weitere Punkte folgen, nummeriert; Schluss bleibt unten ohne Nummer
ki = bericht("beckenübersicht_stehend", ergebnis="Beginnende Coxarthrose beidseits.")
e = I.einsetzen(ki, B52, diktat="Beginnende Coxarthrose beidseits.")
check("Fall 52 + Diktat: HIPPO-Punkt zuerst, Diktiertes als 2., Schluss ohne Nummer",
      e.report.endswith(f"## Ergebnis\n1. {P52}\n2. Beginnende Coxarthrose beidseits.\n{S52}"), e.report)

# schon diktiert: „Coxa valga beidseits“ nicht doppelt
ki = bericht("beckenübersicht_stehend", ergebnis="Coxa valga beidseits.")
e = I.einsetzen(ki, B52, diktat="Coxa valga beidseits.")
erg = e.report.split("## Ergebnis\n")[1]
check("Fall 52: schon diktierte Coxa valga nicht doppelt",
      erg.count("Coxa valga") == 1 and any("schon diktiert" in h for h in e.hinweise), erg)

# zweimal einsetzen (Knopf „IB Lab einfügen“ mit derselben Fassung) → unverändert
e1 = I.einsetzen(bericht("beckenübersicht_stehend"), B52, diktat="Becken.")
e2 = I.einsetzen(e1.report, B52, diktat="Becken.")
check("Fall 52: zweites Einsetzen ändert nichts", e1.report == e2.report, e2.report)

# ── Fall 61 in „Beckenübersicht und Hüfte“: nur die Zeile ersetzt ──
e = I.einsetzen(bericht("beckenübersicht_und_hüfte"), B61, diktat="Becken und Hüfte.")
check("Beckenübersicht und Hüfte: Zeile „Beckenschiefstand: Keiner. …“ durch die HIPPO-Sätze ersetzt",
      "## Befund\nGeringer Beckenschiefstand von 9 mm, rechts tieferstehend. Beinlängendifferenz von 3 mm, links kürzer.\n"
      "Skelett: Symmetrische Beckenform." in e.report and "Beckenschiefstand: Keiner" not in e.report, e.report)

# ── Fall 54: einseitige Prothese ──
B54 = baustein(54)
e = I.einsetzen(bericht("beckenübersicht_mit_einseitiger_hüftprothese"), B54, diktat="Becken, Prothese links.")
check("Fall 54 (Prothese links): nur die Zeile ersetzt, Prothesen-Ergebnis bleibt als 2. Punkt",
      "## Befund\nGeringer Beckenschiefstand von 4 mm, rechts tieferstehend. Beinlängendifferenz von 6 mm, links kürzer. "
      "Der LCE-Winkel beträgt rechts 23°.\nSkelett:" in e.report
      and e.report.endswith("## Ergebnis\n1. Grenzwertige Überdachung des rechten Hüftkopfes.\n2. Regelrechte Lage der "
                            "Hüftprothese ohne Lockerungszeichen.\nLCE = lateraler Center-Edge-Winkel nach Wiberg. " + ENDE),
      e.report)
check("Fall 54: Prothesen-Prüfzeile des Abholers in der Anzeige",
      any("Hüftprothese" in h and "prüfen" in h for h in I.anzeige_hinweise(B54)), I.anzeige_hinweise(B54))

# ── Fall 66: Kind (7 J.) nur beschreibend ──
B66 = baustein(66)
e = I.einsetzen(bericht("beckenübersicht_stehend"), B66, diktat="Becken.")
check("Fall 66 (Kind): Winkel-Sätze in der Beschreibung, kein Ergebnisbegriff, Schluss bleibt",
      "Der CCD-Winkel beträgt rechts 148° und links 160°." in e.report and "Coxa valga" not in e.report
      and "Hüftdysplasie" not in e.report
      and e.report.endswith("## Ergebnis\nRegelrechte Darstellung des Beckens.\nLCE = lateraler Center-Edge-Winkel nach "
                            "Wiberg, AI = Acetabulumindex nach Tönnis, CCD = Caput-Collum-Diaphysen-Winkel. " + ENDE), e.report)
check("Fall 66: keine Prüfzeile wegen des Alters", not [h for h in e.hinweise + I.anzeige_hinweise(B66)
                                                       if "Jahre" in h or "Alter" in h or "Kind" in h], e.hinweise)

# ── Fall 58: Hüfte a.p. links, AI −7° ──
B58 = baustein(58)
e = I.einsetzen(bericht("hüftgelenk_in_2_ebenen"), B58, diktat="Hüfte links.")
check("Fall 58 (Hüfte): Satz am Anfang, Hüft-Sätze zu Form/CCD/Deckung heraus, Begriff als Punkt",
      "## Befund\nDer AI-Winkel beträgt links −7°. Mineralgehalt" in e.report
      and "Der CCD-Winkel ist im Normbereich" not in e.report and "guter Deckung" not in e.report
      and e.report.endswith("## Ergebnis\nVermehrte Überdachung des linken Hüftkopfes.\nAI = Acetabulumindex nach Tönnis. "
                            + ENDE), e.report)

# ── kein befundtext (Ganzbein, unauffällige Hüfte) → nichts eingesetzt ──
for nr in (59, 60):
    b = baustein(nr)
    e = I.einsetzen(bericht("hüftgelenk_in_2_ebenen"), b, diktat="Hüfte.")
    check(f"Fall {nr}: ohne HIPPO-Text bleibt der Befund unverändert", e.report == bericht("hüftgelenk_in_2_ebenen"),
          e.report)

# ── Nummerierung / Schluss ──
check("ist_schluss erkennt die HIPPO-Schlussanmerkung", I.ist_schluss(S52) and I.ist_schluss("AI = Acetabulumindex nach "
                                                                                              "Tönnis. " + ENDE))
check("befund_regeln: HIPPO-Schluss zählt nicht mit (ein Punkt ohne Nummer)",
      br.ergebnis_nummerieren("## Ergebnis\n1. Coxa valga rechts.\nCCD = Caput-Collum-Diaphysen-Winkel. " + ENDE)
      == "## Ergebnis\nCoxa valga rechts.\nCCD = Caput-Collum-Diaphysen-Winkel. " + ENDE)

# ── Gerüst und Prompt ──
g = I.geruest(B52, [{"kurz": "bü", "text": "Beckenübersicht", "vorlage": "beckenübersicht_stehend"}], T)
check("Gerüst: Vorlage mit HIPPO-Sätzen, Begriffe-Punkt, Schluss",
      g is not None and "## Befund\nGeringer Beckenschiefstand von 7 mm" in g.report and VIER[0] not in g.report
      and g.report.endswith(f"## Ergebnis\n{P52}\n{S52}"), g.report if g else None)
g = I.geruest(B61, [{"kurz": "bü", "text": "Beckenübersicht", "vorlage": "beckenübersicht_stehend"}], T)
check("Gerüst ohne Auffälligkeit: Normal-Ergebnis der Vorlage + Schluss",
      g is not None and g.report.endswith("## Ergebnis\nRegelrechte Darstellung des Beckens.\n" + ENDE),
      g.report if g else None)
pb = I.prompt_block(B52, vorlage("beckenübersicht_stehend")[1])
check("Gen-Prompt: HIPPO-Regel, keine Zahlen, keine Diagnosen", I.HIPPO_PROMPT in pb and "23°" not in pb
      and "Coxa valga" not in pb, pb)

# ── kaiscribe-rho-regel-becken-n1 (Kanban #533, Georg FINAL 20.11.2026): Becken/BLD ≥ 10 mm als eigene Ergebnispunkte ──
def becken_baustein(saetze, ergebnis="", ergebnis_becken=None, kind=False, nr="T-101"):
    d = json.loads(json.dumps(next(f["baustein"] for f in FAELLE if f["nr"] == 61)))
    d["accno"] = nr
    d["befundtext"] = {"format": 1, "saetze": saetze, "ergebnis": ergebnis, "schluss": ENDE, "kind": kind, "becken": True}
    if ergebnis_becken is not None:
        d["befundtext"]["ergebnis_becken"] = ergebnis_becken
    return I.aus_liste([d])


RH101_P = ["Beckenschiefstand von 13 mm, rechts tieferstehend.", "Beinlängendifferenz von 20 mm."]
B101 = becken_baustein(["Beckenschiefstand von 13 mm, rechts tieferstehend.", "Beinlängendifferenz von 20 mm.",
                        "Der LCE-Winkel beträgt rechts 18°."], "Hüftdysplasie rechts.", RH101_P)
e = I.einsetzen(bericht("beckenübersicht_stehend"), B101, diktat="Beckenübersicht.")
check("RH 101: Begriff zuerst, dann 13 mm Beckenschiefstand und 20 mm BLD als eigene Punkte, Schluss ohne Nummer",
      e.report.endswith("## Ergebnis\n1. Hüftdysplasie rechts.\n2. Beckenschiefstand von 13 mm, rechts tieferstehend.\n"
                        "3. Beinlängendifferenz von 20 mm.\n" + ENDE), e.report)
check("RH 101: Sätze bleiben auch in der Beschreibung", "## Befund\nBeckenschiefstand von 13 mm, rechts tieferstehend. "
      "Beinlängendifferenz von 20 mm." in e.report, e.report)
e2 = I.einsetzen(e.report, B101, diktat="Beckenübersicht.", entfernen=e.eingesetzt[("T-101", "hippo")])
check("RH 101: zweites Einsetzen ändert nichts (Becken-Punkte nicht doppelt)", e2.report == e.report, e2.report)
B30 = becken_baustein(["Beckenschiefstand von 12 mm, links tieferstehend.", "Beinlängendifferenz von 4 mm."], "",
                      ["Beckenschiefstand von 12 mm, links tieferstehend."], nr="T-30")
e = I.einsetzen(bericht("beckenübersicht_stehend"), B30, diktat="Beckenübersicht.")
check("RH 30: 12 mm ohne Begriff → eigener Punkt ersetzt das Normal-Ergebnis",
      e.report.endswith("## Ergebnis\nBeckenschiefstand von 12 mm, links tieferstehend.\n" + ENDE)
      and "Regelrechte Darstellung des Beckens" not in e.report, e.report)
ki = bericht("beckenübersicht_stehend", ergebnis="Beginnende Coxarthrose beidseits.")
e = I.einsetzen(ki, B30, diktat="Beginnende Coxarthrose beidseits.")
check("RH 30 + Diktat: Becken-Punkt vor dem Diktierten, nummeriert",
      "## Ergebnis\n1. Beckenschiefstand von 12 mm, links tieferstehend.\n2. Beginnende Coxarthrose beidseits.\n" + ENDE
      in e.report, e.report)
ki = bericht("beckenübersicht_stehend", ergebnis="Beckenschiefstand rechts.")
e = I.einsetzen(ki, B30, diktat="Beckenschiefstand rechts.")
check("Diktierter Beckenschiefstand im Ergebnis → IB-Lab-Punkt nicht doppelt, Hinweis",
      "Beckenschiefstand von 12 mm" not in e.report.split("## Ergebnis")[1]
      and any("nicht doppelt" in h for h in e.hinweise), (e.report, e.hinweise))
e = I.einsetzen(bericht("beckenübersicht_stehend"), B61, diktat="Beckenübersicht.")
check("9 mm (Fall 61): nur Beschreibung, kein Ergebnispunkt", "## Ergebnis\nRegelrechte Darstellung des Beckens.\n" + ENDE
      in e.report and "Beckenschiefstand" not in e.report.split("## Ergebnis")[1], e.report)
BK = becken_baustein(["Beckenschiefstand von 13 mm, rechts tieferstehend."], "", RH101_P[:1], kind=True, nr="T-K")
e = I.einsetzen(bericht("beckenübersicht_stehend"), BK, diktat="Beckenübersicht.")
check("Kind: kein Becken-Ergebnispunkt (auch wenn die Liste käme)",
      "Beckenschiefstand" not in e.report.split("## Ergebnis")[1], e.report)
g = I.geruest(B101, [{"kurz": "bü", "text": "Beckenübersicht", "vorlage": "beckenübersicht_stehend"}], T)
check("Gerüst RH 101: Begriff + Becken-Punkte + Schluss",
      g is not None and g.report.endswith("## Ergebnis\n1. Hüftdysplasie rechts.\n2. Beckenschiefstand von 13 mm, rechts "
                                          "tieferstehend.\n3. Beinlängendifferenz von 20 mm.\n" + ENDE),
      g.report if g else None)
g = I.geruest(B30, [{"kurz": "bü", "text": "Beckenübersicht", "vorlage": "beckenübersicht_stehend"}], T)
check("Gerüst RH 30: Becken-Punkt statt Normal-Ergebnis",
      g is not None and g.report.endswith("## Ergebnis\nBeckenschiefstand von 12 mm, links tieferstehend.\n" + ENDE),
      g.report if g else None)
check("HIPPO_PROMPT unterdrückt die Becken-Punkte nicht (KaiScribe setzt sie selbst ein)",
      "ab 10 mm setzt KaiScribe danach selbst als eigenen Ergebnispunkt" in I.HIPPO_PROMPT)

# ── Snapshot aller Fälle ──
zeilen = []
for f in FAELLE:
    b = I.aus_liste([f["baustein"]])
    reg = "hüftgelenk_in_2_ebenen" if f["nr"] in (58, 60, 62, 63) else (
        "beckenübersicht_mit_einseitiger_hüftprothese" if f["nr"] == 54 else "beckenübersicht_stehend")
    e = I.einsetzen(bericht(reg), b, diktat="Diktat ohne Befund.")
    zeilen += [f"### Fall {f['nr']} ({f['datum']}, {reg})", e.report, "Hinweise: " + " | ".join(e.hinweise + I.anzeige_hinweise(b)),
               ""]
text = "\n".join(zeilen)
if "--snapshot-schreiben" in sys.argv:
    SNAP.write_text(text, encoding="utf-8")
check("Snapshot der 16 Fälle unverändert (tests/offline/snapshots/hippo_befunde.txt)",
      SNAP.exists() and SNAP.read_text(encoding="utf-8") == text, "neu schreiben: --snapshot-schreiben")

print(f"\n{'✅ ALLE GRÜN' if not fails else f'❌ {fails} Fehler'}")
sys.exit(1 if fails else 0)
