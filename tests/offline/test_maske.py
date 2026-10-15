"""Gate v3.15.0 Mammo-Maske (Peter 14.10.2026): source_code/maske.py ohne Oberfläche.
Teil 1: Vorbefund nach Labels zerlegen (Hausform, Schreibraum-Form, Labels im Absatz, kurativ, Tomosynthese, Ende des
        Ergebnisses, Fließtext ohne Labels) — Fälle aus maske_faelle.txt (synthetisch).
Teil 2: „unverändert“ → Satz mit Vergleichsdatum (deterministisch), ACR/BI-RADS aus dem Diktat, Erkennen der Mammographie
        an den CAS-Leistungen (Datenbank und Rückfall), Normalbaustein „Mammo 1“.
Teil 3: Maske: Vorschläge, Navigation (feste Reihenfolge), Übernehmen, Diktat ersetzt, Stille ändert nichts, späte
        Erkennung verfällt, Tippen, Neu, offene Vorschläge → INS warnt, zweites INS ohne sie, Befund (Markdown), Screening-
        Text je BI-RADS, kurativ ohne, fehlende Werte.
Teil 4: Datenschutz: die Korrektur (KI) bekommt NUR Peters Diktat eines Felds — nie den Vorbefund.
Teil 5: Tastenbelegung (masken.json, config.ini [MASKE]) — eingeübte Tasten werden nie umgedeutet.
Aufruf: /usr/bin/python3 tests/offline/test_maske.py"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import maske as M  # noqa: E402
import bausteine as BS  # noqa: E402

F = json.loads((pathlib.Path(__file__).resolve().parent / "maske_faelle.txt").read_text(encoding="utf-8"))
DEF_ALL = M.laden(str(ROOT / "masken.json"))
D = DEF_ALL["masken"]["mammographie"]
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# ───────────────────────────── Teil 1: zerlegen ─────────────────────────────
for fall in F["zerlegen"]:
    z = M.zerlegen(fall["text"], D)
    check(f"zerlegen: {fall['name']} – Felder", z.felder == fall["felder"], json.dumps(z.felder, ensure_ascii=False, indent=1))
    check(f"zerlegen: {fall['name']} – Werte", z.werte == fall["werte"], repr(z.werte))
    if "titel" in fall:
        check(f"zerlegen: {fall['name']} – Titel", z.titel == fall["titel"], repr(z.titel))
    if "rest_beginnt" in fall:
        check(f"zerlegen: {fall['name']} – Rest (nicht in den Feldern)", z.rest.startswith(fall["rest_beginnt"]), repr(z.rest[:60]))

# ───────────────────────────── Teil 2: Regeln ─────────────────────────────
for fall in F["vergleich"]:
    ist = M.vergleich(fall["text"], fall["datum"], D)
    check(f"vergleich: {fall['text'][:50]}…", ist == fall["soll"], f"\n   IST  {ist!r}\n   SOLL {fall['soll']!r}")
check("vergleich ohne Datum: nur sauberer Satz", M.vergleich("keine Herde", "", D) == "Keine Herde.")
for fall in F["werte"]:
    rest, w = M.werte_aus_text(fall["text"])
    check(f"Werte: {fall['text']!r}", rest == fall["rest"] and w == fall["werte"], f"{rest!r} {w}")
for text, soll in F["unveraendert"]:
    check(f"unverändert? {text!r} → {soll}", M.ist_unveraendert(text, D) is soll)
for fall in F["erkennen"]:
    ist = M.erkennen(fall["leistungen"], D)
    check(f"erkennen: {fall['name']}", ist == fall["soll"], repr(ist))
check("erkennen: ohne Leistungen → keine Maske", M.erkennen(None, D) is None and M.erkennen([], D) is None)

NORMAL = M.normal_zerlegung(BS.laden(str(ROOT / "ordi_bausteine.json")), D)
check("Normalbaustein Mammo 1 (mam1): nur der Mammographie-Teil ist ein Vorschlag (leere Labels, ACR/BIRADS ohne Wert nicht)",
      set(NORMAL.felder) == {"mammographie"}, repr(NORMAL.felder))
check("… ohne Vorbefund: „Verglichen mit ..........“ fällt weg",
      M.ohne_platzhalter(NORMAL.felder["mammographie"]) == "Kleinfleckig strukturierter Drüsenkörper. Keine suspekten "
      "Verkalkungen. Subcutis und Cutis unauffällig.", M.ohne_platzhalter(NORMAL.felder["mammographie"]))
check("… mit Vorbefund-Datum eingesetzt", M.ohne_platzhalter(NORMAL.felder["mammographie"], "2024-06-05")
      == "Verglichen mit 05.06.2024 unverändert kleinfleckig strukturierter Drüsenkörper. Keine suspekten Verkalkungen. "
      "Subcutis und Cutis unauffällig.")

# ───────────────────────────── Teil 3: Maske ─────────────────────────────
VB_TEXT = F["zerlegen"][0]["text"]
VB = {"nr": "20241012001", "datum": "2024-06-05", "text": VB_TEXT, "werte": {"acr": "2", "birads": "2"}}
KORR = []


def korrektur(t):
    KORR.append(t)
    return t.strip().rstrip(".") + "."


def neu_maske(**k):
    a = dict(art="screening", seite=None, sono=True, vorbefund=VB, normal=NORMAL)
    a.update(k)
    return M.Maske(D, **a)


m = neu_maske()
check("Vorschläge aus dem Vorbefund in allen 4 Feldern, Datum 05.06.2024",
      [f.quelle for f in m.felder] == ["vorbefund"] * 4 and m.datum == "05.06.2024"
      and m.felder[3].vorschlag_werte == {"acr": "2", "birads": "2"}, m.zustand())
check("Navigation: Start Feld 1, 3× Vorspulen = Ergebnis, am Ende bleibt es, Rückspulen zurück",
      m.aktiv == 0 and m.naechstes() and m.naechstes() and m.naechstes() and m.feld.id == "ergebnis"
      and not m.naechstes() and m.voriges() and m.feld.id == "sonographie")
m.gehe_zu(0)
check("INS mit offenen Vorschlägen → kein Befund (None)", M.befund_bauen(m) is None and len(m.offene()) == 4)
warn = M.offene_meldung(m)
check("Warnung nennt die Felder und die Auswege", "Inspektion und Palpation (Vorbefund)" in warn and "F3 übernimmt" in warn
      and "INS noch einmal" in warn, warn)
msg = m.uebernehmen()
check("F3 übernimmt die Inspektion wörtlich", m.felder[0].quelle == "uebernommen" and m.felder[0].text == "Unauffällig."
      and msg == "Inspektion und Palpation: übernommen", msg)
m.uebernehmen()
check("F3 noch einmal → wieder Vorschlag", m.felder[0].quelle == "vorbefund" and m.felder[0].text == "")
m.uebernehmen()
m.naechstes()
v0 = m.version
k, s, t = m.reservieren()
check("Record im Feld: Abschnitt angemeldet, Feld bleibt Vorschlag bis Text da ist", m.felder[1].quelle == "vorbefund"
      and m.felder[1].wartet and M.anzeige_zustand(m.felder[1], m.datum) == "Vorbefund 05.06.2024")
m.diktat_fertig(k, s, t, "unverändert")
check("„unverändert“ → Feld diktiert, Anzeige gleich mit Vergleichsdatum (ohne KI)", m.felder[1].quelle == "diktat"
      and M.vorschau(m.felder[1], m) == "Verglichen mit 05.06.2024 beidseits unverändert vereinzelte insuspekte "
      "Verkalkungen sowie Gefäßverkalkungen. Im Übrigen unauffällig strukturierter Drüsenkörper. Cutis und Subcutis "
      "unauffällig." and m.version > v0, M.vorschau(m.felder[1], m))
m.naechstes()
k2, s2, t2 = m.reservieren()
m.diktat_fertig(k2, s2, t2, "")
check("Stille beim Durchspringen ändert nichts (Sonographie bleibt Vorschlag)", m.felder[2].quelle == "vorbefund"
      and not m.felder[2].wartet)
k3, s3, t3 = m.reservieren()
m.uebernehmen()
m.diktat_fertig(k3, s3, t3, "spät erkannter Text")
check("Erkennung, die nach F3 eintrifft, verfällt (Feld bleibt übernommen)", m.felder[2].quelle == "uebernommen"
      and m.felder[2].text == "Verglichen mit 05.06.2024 weiterhin keine suspekten mammären oder axillären Veränderungen.",
      m.felder[2].text)
m.naechstes()
k4, s4, t4 = m.reservieren()
m.diktat_fertig(k4, s4, t4, "unverändert ACR 2 BIRADS 2")
check("Ergebnis „unverändert ACR 2 BIRADS 2“ → Vorbefund-Ergebnis + Werte", M.vorschau(m.felder[3], m)
      == "Mastopathie mit insuspekten Verkalkungen." and M.werte_vorschau(m.felder[3], m) == {"acr": "2", "birads": "2"})
KORR.clear()
b = M.befund_bauen(m, korrektur=korrektur)
SOLL = ("## Mammographie beidseits – Screening\n\n## Befund\nInspektion und Palpation: Unauffällig.\n\n"
        "Mammographie: Verglichen mit 05.06.2024 beidseits unverändert vereinzelte insuspekte Verkalkungen sowie "
        "Gefäßverkalkungen. Im Übrigen unauffällig strukturierter Drüsenkörper. Cutis und Subcutis unauffällig.\n\n"
        "Sonographie: Verglichen mit 05.06.2024 weiterhin keine suspekten mammären oder axillären Veränderungen.\n\n"
        "## Ergebnis\nMastopathie mit insuspekten Verkalkungen.\nACR: 2\nBIRADS: 2\n\n"
        + D["schluss"]["screening"]["texte"]["2"])
check("Befund: Titel Screening, Labels, Ergebnis mit ACR/BIRADS, Screening-Text BI-RADS 2 — wörtlich", b.report == SOLL,
      f"\n{b.report}\n---SOLL---\n{SOLL}")
check("… ohne KI-Aufruf (alles übernommen/„unverändert“), keine Hinweise", KORR == [] and b.ki_aufrufe == 0
      and b.hinweise == [], f"{KORR} {b.hinweise}")

# freies Diktat ersetzt den Vorbefund; KI bekommt nur das Diktat
m2 = neu_maske()
for i, txt in ((0, "unauffällig"), (1, "beidseits neue gruppierte Mikroverkalkungen links oben außen"),
               (3, "suspekter Mikrokalk links ACR C BIRADS 4")):
    m2.gehe_zu(i)
    a_, b_, c_ = m2.reservieren()
    m2.diktat_fertig(a_, b_, c_, txt)
check("Sonographie nicht berührt → offen, INS warnt", [f.id for f in m2.offene()] == ["sonographie"])
KORR.clear()
b2 = M.befund_bauen(m2, korrektur=korrektur, ohne_offene=True)
check("zweites INS: Befund ohne das offene Feld + Hinweis", "Sonographie:" not in b2.report
      and b2.hinweise[0] == "Nicht im Befund (Vorschlag nicht übernommen): Sonographie", b2.hinweise)
check("Diktat ersetzt den Vorbefund (Feldtext = korrigiertes Diktat)",
      "Mammographie: Beidseits neue gruppierte Mikroverkalkungen links oben außen." in b2.report
      and "Gefäßverkalkungen" not in b2.report and "Inspektion und Palpation: Unauffällig." in b2.report, b2.report)
check("Ergebnis: Werte aus dem Diktat (ACR C, BIRADS 4), Text ohne sie", "## Ergebnis\nSuspekter Mikrokalk links.\nACR: C\n"
      "BIRADS: 4" in b2.report, b2.report)
check("BI-RADS 4 im Screening: kein Screening-Text, Hinweis „wie bisher in CAS“",
      "Verlaufskontrolle" not in b2.report and any("BI-RADS 4 (Screening)" in h for h in b2.hinweise), b2.hinweise)
check("KI je Feld nur mit dem Diktat dieses Felds", sorted(KORR) == sorted(["unauffällig", "beidseits neue gruppierte "
      "Mikroverkalkungen links oben außen", "suspekter Mikrokalk links"]), KORR)
n_vor = len(KORR)
M.befund_bauen(m2, korrektur=korrektur, ohne_offene=True)
check("zweiter Bau ohne neues Diktat: keine weitere KI (Ergebnis je Rohtext gemerkt)", len(KORR) == n_vor)
a_, b_, c_ = m2.reservieren(1)
m2.diktat_fertig(a_, b_, c_, "zusätzlich Zyste rechts")
check("Nachdiktat im selben Feld hängt an", m2.felder[1].roh == "beidseits neue gruppierte Mikroverkalkungen links oben "
      "außen zusätzlich Zyste rechts")
check("Tippen: von Hand geändert → getippt (ohne KI); gleiche Anzeige → nichts",
      m2.tippen(0, "Unauffälliger Tastbefund.") and m2.felder[0].quelle == "getippt" and not m2.tippen(0, "Unauffälliger Tastbefund."))
check("Ergebnis getippt mit Werten: Anzeige bleibt wie getippt, Werte erkannt, im Befund getrennt",
      m2.tippen(3, "Zyste links.\nACR: 1\nBIRADS: 2") and M.vorschau(m2.felder[3], m2) == "Zyste links.\nACR: 1\nBIRADS: 2"
      and M.werte_vorschau(m2.felder[3], m2) == {"acr": "1", "birads": "2"}
      and "## Ergebnis\nZyste links.\nACR: 1\nBIRADS: 2" in M.befund_bauen(m2, korrektur=korrektur, ohne_offene=True).report,
      f"{m2.felder[3].text!r}")
msg = m2.verwerfen(1)
check("Verwerfen → wieder Vorbefund", m2.felder[1].quelle == "vorbefund" and "wieder Vorbefund" in msg)
m2.neu()
check("Neu (F1/F9) → alle wieder Vorschlag, Feld 1 aktiv", [f.quelle for f in m2.felder] == ["vorbefund"] * 4 and m2.aktiv == 0)

# ohne Sono-Leistung: Feld eingeklappt, nicht offen, nicht im Befund — Diktat schaltet es zu
m3 = neu_maske(sono=False)
check("ohne Sono-Leistung: Sonographie eingeklappt, nicht offen", not m3.felder[2].sichtbar
      and [f.id for f in m3.offene()] == ["inspektion", "mammographie", "ergebnis"])
for i in (0, 1, 3):
    m3.uebernehmen(i)
b3 = M.befund_bauen(m3)
check("… Befund ohne Sonographie, ohne Warnung", b3 is not None and "Sonographie" not in b3.report and not b3.ohne)
m3.gehe_zu(2)
a_, b_, c_ = m3.reservieren()
m3.diktat_fertig(a_, b_, c_, "keine suspekten Herde")
b3b = M.befund_bauen(m3, korrektur=korrektur)
check("… Diktat ins eingeklappte Feld schaltet es zu", m3.felder[2].sichtbar and "Sonographie: Keine suspekten Herde."
      in b3b.report, b3b.report)

# kein Vorbefund: Normalbaustein als Vorschlag, kurativ ohne Screening-Text
m4 = M.Maske(D, art="kurativ", seite="links", sono=False, vorbefund=None, normal=NORMAL)
check("kein Vorbefund: nur Mammographie hat den Normalbaustein als Vorschlag (ohne Vergleich)",
      [f.quelle for f in m4.felder] == ["leer", "vorlage", "leer", "leer"]
      and m4.felder[1].vorschlag.startswith("Kleinfleckig strukturierter Drüsenkörper"), m4.zustand())
check("… Warnung nennt den Normalbaustein", "Mammographie (Normalbaustein)" in M.offene_meldung(m4))
m4.uebernehmen(1)
for i, txt in ((0, "unauffällig"), (3, "unauffälliger Befund ACR 1 BIRADS 1")):
    a_, b_, c_ = m4.reservieren(i)
    m4.diktat_fertig(a_, b_, c_, txt)
b4 = M.befund_bauen(m4, korrektur=korrektur)
check("kurativ, eine Seite: Titel „Mammographie links“, kein Screening-Text",
      b4.report.startswith("## Mammographie links\n") and "Verlaufskontrolle" not in b4.report
      and "ACR: 1\nBIRADS: 1" in b4.report, b4.report)
check("„unverändert“ ohne Vorbefund → so übernommen + Hinweis", M.feld_verarbeiten(
    M.Feld(id="x", label="Inspektion und Palpation", teile=["unverändert"], quelle="diktat"), m4)[:3]
      == ("Unverändert.", {}, "Inspektion und Palpation: „unverändert“ ohne Vorbefund – so übernommen"))

# Werte fehlen → Hinweis; Werte nur in einem anderen Feld diktiert → übernommen
m5 = M.Maske(D, art="screening", sono=True, vorbefund=None, normal=M.Zerlegung())
for i, txt in ((1, "unauffällig, Drüsendichte ACR B"), (3, "unauffälliger Befund")):
    a_, b_, c_ = m5.reservieren(i)
    m5.diktat_fertig(a_, b_, c_, txt)
b5 = M.befund_bauen(m5, korrektur=korrektur)
check("ACR aus dem Mammographie-Diktat übernommen, BI-RADS fehlt → Hinweis, ohne BI-RADS kein Screening-Text",
      "ACR: B" in b5.report and "BIRADS fehlt im Ergebnis" in b5.hinweise and "Verlaufskontrolle" not in b5.report,
      f"{b5.report}\n{b5.hinweise}")

# Kontext kommt nach dem Öffnen
m6 = M.Maske(D, art="screening", sono=True, vorbefund=None, normal=NORMAL)
m6.uebernehmen(1)
m6.vorbefund_setzen(VB)
check("Vorbefund kommt später: nur Felder im Vorschlag-Stand ändern sich (übernommener Normalbaustein bleibt)",
      [f.quelle for f in m6.felder] == ["vorbefund", "uebernommen", "vorbefund", "vorbefund"]
      and m6.felder[1].text.startswith("Kleinfleckig"), m6.zustand())
VB_ABW = dict(VB, werte={"acr": "3", "birads": "2"})
check("ACR im Brief (2) ≠ Doppelbefundung (3) → Hinweis; Doppelbefundung gilt", M.Maske(D, vorbefund=VB_ABW).werte_abweichung()
      == "Vorbefund: BI-RADS im Brief 2, Doppelbefundung 2".replace("BI-RADS im Brief 2, Doppelbefundung 2",
                                                                     "ACR im Brief 2, Doppelbefundung 3")
      and M.Maske(D, vorbefund=VB_ABW).felder[3].vorschlag_werte == {"acr": "3", "birads": "2"})
check("ACR B im Brief = 2 in der Doppelbefundung → kein Hinweis",
      M.Maske(D, vorbefund=dict(VB, text=VB_TEXT.replace("ACR: 2", "ACR: B"))).werte_abweichung() == "")

# ───────────────────────────── Teil 4: Datenschutz ─────────────────────────────
GEHEIM = "VORBEFUND-GEHEIMTEXT-4711"
vb_geheim = dict(VB, text=VB_TEXT.replace("Unauffällig.", f"Unauffällig {GEHEIM}.").replace("Mastopathie", f"{GEHEIM} Mastopathie"))
m7 = neu_maske(vorbefund=vb_geheim)
KORR.clear()
for i, txt in ((0, "unverändert"), (1, "beidseits unauffällig"), (2, "unverändert"), (3, "unverändert ACR 2 BIRADS 1")):
    a_, b_, c_ = m7.reservieren(i)
    m7.diktat_fertig(a_, b_, c_, txt)
b7 = M.befund_bauen(m7, korrektur=korrektur)
check("KI bekommt nur Peters Diktat (nie den Vorbefund), „unverändert“ ohne KI", KORR == ["beidseits unauffällig"]
      and all(GEHEIM not in k for k in KORR), KORR)
check("… der Vorbefund steht trotzdem (deterministisch) im Befund", b7.report.count(GEHEIM) == 2 and "BIRADS: 1" in b7.report)
check("maske.py ruft selbst keine KI auf (kein gemini/urllib)", "import gemini" not in (ROOT / "source_code" / "maske.py")
      .read_text(encoding="utf-8") and "urllib" not in (ROOT / "source_code" / "maske.py").read_text(encoding="utf-8"))

# ───────────────────────────── Teil 5: Tasten ─────────────────────────────
bel = M.tasten_belegung(DEF_ALL)
check("Standard: Vorspulen = nächstes Feld, Rückspulen = voriges, F3 = übernehmen, F4 = Maske aus/an",
      bel == {"FF": "naechstes_feld", "REW": "voriges_feld", "F3": "uebernehmen", "F4": "maske_umschalten"}, repr(bel))
check("Text für Protokoll/Hilfezeile", M.tasten_text(bel) == "Vorspulen = nächstes Feld · Rückspulen = voriges Feld · "
      "F3 = Vorbefund übernehmen · F4 = Maske aus/an", M.tasten_text(bel))
check("Kurzfassung für die Hilfezeile der Maske", M.tasten_kurz(bel) == "Vorspulen/Rückspulen = Feld · F3 = übernehmen · "
      "F4 = Maske aus", M.tasten_kurz(bel))
log = []
bel2 = M.tasten_belegung(DEF_ALL, {"naechstes_feld": "FF INSTR", "voriges_feld": "INS", "quatsch": "F4"}, log=log.append)
check("config.ini: zusätzliche Taste (INSTR) geht, eingeübte (INS) nie, unbekannte Aktion ignoriert",
      bel2.get("INSTR") == "naechstes_feld" and "INS" not in bel2 and "REW" not in bel2 and len(log) == 2, f"{bel2} {log}")

print("\n" + ("✅ MASKE PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
