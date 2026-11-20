"""Gate IB Lab SQUIRREL → Skoliose-Text (Georg Riegler 20.11.2026 „1a 2a 3a 4a 5ja“, Peter 20.11.2026 Punkt 20/40b, Brief
kaiscribe-squirrel-ergebnistext-n1). Die Bausteine (tests/offline/squirrel_bausteine.json) entstehen mit dem Abholer-Code
(ris-mods ibl/vorbefund.py + ibl/squirrel_ergebnis.py) und der Brücke (tools/squirrel_bausteine_erzeugen.py) aus der
Fixture SQUIRREL_SR und synthetischen Kurven – keine Patientendaten. Geprüft: GWS a.p. (Achsensatz „Wirbelsäule: Normale
Stellung, …“ ersetzt), Gesamte Wirbelsäule (Sätze als erster Absatz, „Normaler Achsenverlauf“/„achsengerechte Stellung“
heraus, Kyphose bleibt), Index-Labeling, alle < 10° (kein Feld), Diktat „flachbogige skoliotische Asymmetrie“ (nur
Cobb-Satz, kein Ergebnissatz), verneint, Kind 12 J., Vorwert +5°, Metall (nur Prüfzeile), Konvexität fehlt, keine
Messzeilen, zweimal einsetzen, Ablage-Rückfall, Gerüst, Gen-Prompt, Gleichheit der Muster mit ris-mods.
Snapshot aller Texte: tests/offline/snapshots/squirrel_befunde.txt.
Aufruf: python3 tests/offline/test_ibl_squirrel_text.py [--snapshot-schreiben]"""
import json, pathlib, re, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import ibl_bausteine as I  # noqa: E402

HIER = pathlib.Path(__file__).resolve().parent
T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
FAELLE = json.loads((HIER / "squirrel_bausteine.json").read_text(encoding="utf-8"))
SNAP = HIER / "snapshots" / "squirrel_befunde.txt"
GWS, GESAMT, LWS = "ganzaufnahme_der_wirbelsäule_a-p", "wirbelsäule_gesamt", "lendenwirbelsäule_in_2_ebenen"
ENDE = "Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen."
fails = 0
snap = []


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def roh(fall):
    return next(f["baustein"] for f in FAELLE if f["fall"] == fall)


def baustein(fall):
    return I.aus_liste([roh(fall)])


def bericht(key, befund=None, ergebnis=None):
    v = T[key]
    body = v["body"].split("\n", 2)[2]
    return (f"## {v['display_name']}\n\n## Befund\n{body if befund is None else befund}\n\n## Ergebnis\n"
            f"{v['ergebnis'] if ergebnis is None else ergebnis}")


def teil(report, was):
    return report.split("## Befund\n")[1].split("\n\n## Ergebnis")[0] if was == "befund" else \
        report.split("## Ergebnis\n")[1]


def merken(name, e):
    snap.append(f"=== {name}\n{e.report}\n--- Hinweise\n" + "\n".join(e.hinweise))


S1 = "Linkskonvexe skoliotische Krümmung der BWS (Th2–Th5) mit einem Cobb-Winkel von 21°."
S2 = "Rechtskonvexe skoliotische Krümmung der BWS (Th5–Th12) mit einem Cobb-Winkel von 44°."
S3 = "Linkskonvexe skoliotische Krümmung der BWS und LWS (Th12–L4) mit einem Cobb-Winkel von 31°."
P_FIX = ("Hochgradige rechtskonvexe Skoliose der BWS. Mittelgradige linkskonvexe Skoliose der BWS und LWS. Mittelgradige "
         "linkskonvexe Skoliose der BWS.")

# ── Baustein lesen ──
B = baustein("fixture")
bt = B[0].befundtext
check("Fixture: befundtext.squirrel gelesen (21/44/31, kranial → kaudal, Cobb-Satz, Schluss)",
      bt is not None and bt["saetze"] == [S1, S2, S3] and bt["ergebnis"] == P_FIX and bt["schluss"] == ENDE
      and bt["cobb_satz"] == "Cobb-Winkel 21° (Th2–Th5), 44° (Th5–Th12) und 31° (Th12–L4)." and bt["anatomisch"]
      and len(bt["kruemmungen"]) == 3, bt)
check("Fixture: Abholer liefert kein ergebnis_punkte (ohne Diktat kein Skoliose-Satz)", B[0].ergebnis == [], B[0].ergebnis)
check("Fixture: keine Messzeilen in befund_zeilen, hat_inhalt", I.befund_zeilen(B[0]) == [] and I.hat_inhalt(B[0]))
check("Fassung ≠ 1 bzw. ohne Sätze → kein Text (Verhalten bis 3.19.15)",
      I._befundtext("squirrel", dict(roh("fixture")["befundtext"], format=2)) is None
      and I._befundtext("squirrel", dict(roh("fixture")["befundtext"], saetze=[])) is None)

# ── GWS a.p.: Achsensatz der Vorlage ersetzt, Ergebnis ersetzt, Schluss ──
e = I.einsetzen(bericht(GWS), B, diktat="Ganzaufnahme der Wirbelsäule.")
merken("Fixture · GWS a.p. · ohne Krümmung im Diktat", e)
bef = teil(e.report, "befund")
check("GWS a.p.: „Wirbelsäule: “ + Skoliose-Sätze an der Stelle von „Normale Stellung, flachbogige …“",
      bef.startswith(f"Wirbelsäule: {S1} {S2} {S3} Alignementlinien regelrecht.\nWirbelkörper:")
      and "Normale Stellung" not in bef and "flachbogige" not in bef, bef)
check("GWS a.p.: Skoliose-Punkt als einziger Punkt, Normal-Ergebnis ersetzt, Schluss ohne Nummer",
      teil(e.report, "ergebnis") == f"{P_FIX}\n{ENDE}", teil(e.report, "ergebnis"))
check("GWS a.p.: keine Messzeile „(IB Lab SQUIRREL)“, Gate grün",
      "(IB Lab SQUIRREL)" not in e.report and not I.gate(e.report, e.zeilen), e.report)
check("GWS a.p.: keine Prüfzeile (nur „ersetzt“-Hinweis)", not [h for h in e.hinweise if "prüfen" in h], e.hinweise)

# zweimal einsetzen: nichts doppelt
e2 = I.einsetzen(e.report, B, diktat="Ganzaufnahme der Wirbelsäule.")
check("zweimal einsetzen: Befund unverändert", e2.report == e.report, e2.report)

# ── Gesamte Wirbelsäule (HWS/BWS/LWS-Abschnitte): erster Absatz, Achsensätze heraus, Kyphose bleibt (40b) ──
e = I.einsetzen(bericht(GESAMT), B, diktat="Gesamte Wirbelsäule.")
merken("Fixture · Gesamte Wirbelsäule", e)
bef = teil(e.report, "befund")
check("Gesamte WS: Skoliose-Sätze als erster Absatz vor „HWS:“", bef.startswith(f"{S1} {S2} {S3}\n\nHWS:\n"), bef)
check("Gesamte WS (40b): „Normaler Achsenverlauf.“ und „Annähernd achsengerechte Stellung.“ entfallen",
      "Achsenverlauf" not in bef and "achsengerechte" not in bef, bef)
check("Gesamte WS (40b): „Harmonische Kyphose.“ bleibt, Beschriftungen bleiben",
      "BWS:\nHarmonische Kyphose." in bef and "HWS:\nAlle Wirbelkörper" in bef and "LWS:\nAnzahl und Höhe" in bef, bef)
check("Gesamte WS: Normal-Ergebnis ersetzt", teil(e.report, "ergebnis") == f"{P_FIX}\n{ENDE}", teil(e.report, "ergebnis"))

# ── Vorlage mit „Achsengerechte Stellung“ + Kyphose-Satz (KI-Text ohne Abschnitte) ──
ki = ("Harmonische Kyphose der BWS. Annähernd achsengerechte Stellung. Wirbelkörper nach Anzahl, Form und Größe regelrecht.")
e = I.einsetzen(bericht(GWS, befund=ki), baustein("einzeln"), diktat="Wirbelsäule.")
merken("Einzeln · Achsengerechte Stellung + Kyphose", e)
check("Achsensatz → an seiner Stelle der Skoliose-Satz, Kyphose-Satz bleibt davor",
      teil(e.report, "befund") == f"Harmonische Kyphose der BWS. {S2} Wirbelkörper nach Anzahl, Form und Größe regelrecht.",
      teil(e.report, "befund"))

# ── Index-Labeling: ohne Höhe/Region ──
e = I.einsetzen(bericht(GWS), baustein("index"), diktat="Wirbelsäule.")
merken("Index-Labeling", e)
check("Index: „Rechtskonvexe skoliotische Krümmung mit einem Cobb-Winkel von 44°.“, Punkt ohne Region",
      "Wirbelsäule: Rechtskonvexe skoliotische Krümmung mit einem Cobb-Winkel von 44°. Alignementlinien" in e.report
      and teil(e.report, "ergebnis") == f"Hochgradige rechtskonvexe Skoliose.\n{ENDE}", e.report)

# ── alle < 10°: kein Feld → wie bis 3.19.15 (nur Messzeilen, kein Skoliose-Text, kein Ergebnis) ──
U = baustein("unter10")
e = I.einsetzen(bericht(GWS), U, diktat="Wirbelsäule.")
merken("alle < 10°", e)
check("< 10°: kein befundtext vom Abholer", U[0].befundtext is None)
check("< 10°: kein Skoliose-Text, Ergebnis der Vorlage bleibt, kein Schluss",
      "skoliotische Krümmung" not in e.report and teil(e.report, "ergebnis").startswith("Regelrechte Darstellung der "
                                                                                       "Wirbelsäule.")
      and ENDE not in e.report, e.report)

# ── Diktat „flachbogige skoliotische Asymmetrie“ (Punkt 20): Wortwahl bleibt, nur Cobb-Satz, kein Ergebnissatz ──
ki = ("Wirbelsäule: Normale Stellung, flachbogige skoliotische Asymmetrie. Alignementlinien regelrecht.\n"
      "Wirbelkörper: Anzahl, Form, Größe und Stellung zueinander regelrecht.")
e = I.einsetzen(bericht(GWS, befund=ki, ergebnis="Flachbogige skoliotische Asymmetrie."), B,
                diktat="Ganzwirbelsäule, flachbogige skoliotische Asymmetrie, sonst unauffällig.")
merken("Diktat flachbogige skoliotische Asymmetrie", e)
bef = teil(e.report, "befund")
check("Diktat: Satz des Arztes wörtlich, dahinter NUR der Cobb-Satz",
      bef.startswith("Wirbelsäule: Normale Stellung, flachbogige skoliotische Asymmetrie. Cobb-Winkel 21° (Th2–Th5), 44° "
                     "(Th5–Th12) und 31° (Th12–L4). Alignementlinien regelrecht."), bef)
check("Diktat: keine Skoliose-Sätze, kein Skoliose-Ergebnissatz, nie zusätzlich „Skoliose“",
      S2 not in e.report and "Skoliose" not in e.report, e.report)
check("Diktat: Ergebnis des Arztes bleibt, Schluss ohne Nummer darunter",
      teil(e.report, "ergebnis") == f"Flachbogige skoliotische Asymmetrie.\n{ENDE}", teil(e.report, "ergebnis"))
check("Diktat: Gate grün (Cobb-Satz wörtlich)", not I.gate(e.report, e.zeilen) and bt["cobb_satz"] in e.zeilen, e.zeilen)
e2 = I.einsetzen(e.report, B, diktat="Ganzwirbelsäule, flachbogige skoliotische Asymmetrie, sonst unauffällig.")
check("Diktat zweimal einsetzen: Befund unverändert", e2.report == e.report, e2.report)

# verneint: „keine Skoliose“ zählt auch (Wortwahl bleibt, Cobb-Satz, kein Punkt); Achsensatz entfällt (40b)
ki = "Annähernd achsengerechte Stellung. Keine Skoliose. Wirbelkörper regelrecht."
e = I.einsetzen(bericht(GWS, befund=ki, ergebnis="Keine Skoliose."), baustein("einzeln"), diktat="Keine Skoliose.")
merken("Diktat verneint", e)
check("verneint: „Keine Skoliose. Cobb-Winkel 44° (Th5–Th12).“, Achsensatz weg, kein Skoliose-Punkt",
      teil(e.report, "befund") == "Keine Skoliose. Cobb-Winkel 44° (Th5–Th12). Wirbelkörper regelrecht."
      and teil(e.report, "ergebnis") == f"Keine Skoliose.\n{ENDE}", e.report)
# diktierter Achsensatz bleibt (40b gilt nur für den Vorlagensatz)
ki = "Achsengerechte Stellung mit flachbogiger Asymmetrie. Wirbelkörper regelrecht."
e = I.einsetzen(bericht(GWS, befund=ki, ergebnis="Flachbogige Asymmetrie."), baustein("einzeln"),
                diktat="achsengerechte Stellung mit flachbogiger Asymmetrie")
check("Satz des Arztes mit Achse + Krümmung bleibt wörtlich, Cobb-Satz dahinter",
      teil(e.report, "befund") == "Achsengerechte Stellung mit flachbogiger Asymmetrie. Cobb-Winkel 44° (Th5–Th12). "
                                  "Wirbelkörper regelrecht.", teil(e.report, "befund"))
# Kyphose/Lordose zählen nicht als Krümmung
check("Muster: Kyphose/Lordose/Hyperkyphose zählen nicht, Skoliose/Asymmetrie/Seitausbiegung/rechtskonvex schon",
      not I.squirrel_diktiert("Verstärkte Kyphose der BWS, Hyperlordose der LWS, Streckhaltung der HWS.")
      and all(I.squirrel_diktiert(x) for x in ("flachbogige Skoliose", "skoliotische Asymmetrie", "Seitausbiegung",
                                                "rechtskonvex", "S-förmig", "keine Skoliose", "konvex nach links")))
# die VORLAGE zählt nicht als Diktat: Bis 3.19.19 enthielt die GWS-Vorlage „flachbogige rechts-konvexe Skoliose“; seit
# kaiscribe-gws-ap-normaltext-n1 (Peter 20.11.2026, #459 „a“) nur noch „Normale Stellung.“ – ohne Diktat Skoliose-Text
# aus SQUIRREL, der Achsensatz ist ersetzt (Gate ohne SQUIRREL: tests/offline/test_gws_ap_normaltext.py)
e = I.einsetzen(bericht(GWS), baustein("einzeln"), diktat="Wirbelsäule unauffällig.")
check("Vorlage mit „Skoliose“ zählt nicht als Diktat: Skoliose-Satz + Punkt",
      S2 in e.report and "flachbogige rechts-konvexe" not in e.report and "Normale Stellung" not in e.report
      and teil(e.report, "ergebnis").startswith("Hochgradige rechtskonvexe Skoliose der BWS."), e.report)
# erst ohne, dann mit Diktat einsetzen (Knopf nach neuem Diktat): eigener Punkt + Sätze werden ersetzt
e1 = I.einsetzen(bericht(GWS, befund="Wirbelsäule: Normale Stellung. Wirbelkörper regelrecht."), baustein("einzeln"),
                 diktat="Wirbelsäule.")
e2 = I.einsetzen(e1.report.replace("Wirbelkörper regelrecht.", "Flachbogige Asymmetrie. Wirbelkörper regelrecht."),
                 baustein("einzeln"), diktat="flachbogige Asymmetrie", entfernen=e1.eingesetzt[I.aus_liste([roh("einzeln")])[0].schluessel])
check("zweite Fassung mit Diktat: Skoliose-Satz und -Punkt weg, Cobb-Satz hinter dem Diktat-Satz",
      "Skoliose" not in e2.report and "Flachbogige Asymmetrie. Cobb-Winkel 44° (Th5–Th12)." in e2.report, e2.report)

# ── Kind 12 J.: gleicher Text ──
e_k = I.einsetzen(bericht(GWS), baustein("kind"), diktat="Wirbelsäule.")
e_e = I.einsetzen(bericht(GWS), baustein("einzeln"), diktat="Wirbelsäule.")
merken("Kind 12 J.", e_k)
check("Kind 12 J.: derselbe Befund wie beim Erwachsenen (3a)", e_k.report == e_e.report and baustein("kind")[0].befundtext["kind"],
      e_k.report)

# ── Vorwert +5°: Progredienz im Ergebnis ──
e = I.einsetzen(bericht(GWS), baustein("vorwert"), diktat="Wirbelsäule.")
merken("Vorwert 39° → 44°", e)
check("Vorwert: „Zunahme von 39° (03/2025) auf 44° im Sinne einer Progredienz.“ direkt hinter der Krümmung",
      teil(e.report, "ergebnis") == "Hochgradige rechtskonvexe Skoliose der BWS. Zunahme von 39° (03/2025) auf 44° im "
                                    f"Sinne einer Progredienz.\n{ENDE}", teil(e.report, "ergebnis"))
e = I.einsetzen(bericht(GWS, ergebnis="Flachbogige skoliotische Asymmetrie."), baustein("vorwert"),
                diktat="flachbogige skoliotische Asymmetrie")
check("Vorwert + Diktat: Vorwert neutral im Cobb-Satz, keine Progredienz",
      "Cobb-Winkel 44° (Th5–Th12; Vorwert 03/2025: 39°)." in e.report and "Progredienz" not in e.report, e.report)

# ── Metall: nur Prüfzeile (rot), keine Messzeilen, kein Gerüst ──
M = baustein("metall")
e = I.einsetzen(bericht(GWS), M, diktat="Wirbelsäule.")
merken("Metall", e)
check("Metall: Befund unverändert (keine Messzeile, kein Text)", e.report == bericht(GWS), e.report)
check("Metall: rote Prüfzeile „⚠ SQUIRREL: Metall/Implantat … prüfen“",
      [h for h in I.anzeige_hinweise(M) if h.startswith("⚠ SQUIRREL: Metall") and "prüfen" in h], I.anzeige_hinweise(M))
check("Metall: kein Gerüst", I.geruest(M) is None)

# ── Konvexität fehlt: Text ohne Richtung + rote Prüfzeile ──
K = baustein("ohne_konvex")
e = I.einsetzen(bericht(GWS), K, diktat="Wirbelsäule.")
merken("Konvexität fehlt", e)
check("ohne Konvexität: „Skoliotische Krümmung der BWS …“ + Prüfzeile rot",
      "Wirbelsäule: Skoliotische Krümmung der BWS (Th5–Th12) mit einem Cobb-Winkel von 25°." in e.report
      and any(h.startswith("⚠") and "Konvexität" in h for h in I.anzeige_hinweise(K)), (e.report, I.anzeige_hinweise(K)))

# ── nicht diktierte Krümmung im KI-Text → Prüfzeile ──
ki = "Wirbelsäule: Flachbogige rechtskonvexe Skoliose. Alignementlinien regelrecht."
e = I.einsetzen(bericht(GWS, befund=ki), baustein("einzeln"), diktat="Wirbelsäule.")
check("KI-Text nennt Krümmung ohne Diktat → ⚠-Prüfzeile",
      any(h.startswith("⚠ SQUIRREL") and "Flachbogige rechtskonvexe Skoliose" in h for h in e.hinweise), e.hinweise)

# ── keine passende Untersuchung: Absatz am Ende ──
knie = "## Kniegelenk links in 2 Ebenen\n\n## Befund\nUnauffällig.\n\n## Ergebnis\nRegelrechte Darstellung."
e = I.einsetzen(knie, baustein("einzeln"), diktat="Knie links.")
check("ohne Wirbelsäulen-Untersuchung: Text als Absatz am Ende + Prüfhinweis",
      e.report.endswith(f"{S2}\nHochgradige rechtskonvexe Skoliose der BWS.\n{ENDE}")
      and any("eindeutig zuzuordnen" in h for h in e.hinweise), e.report)

# ── Gerüst vor dem Diktat ──
L = [{"ziffer": 1, "kurz": "gws", "text": "Ganzaufnahme der Wirbelsäule", "vorlage": GWS}]
g = I.geruest(B, L, T)
snap.append(f"=== Gerüst GWS a.p.\n{g.report}")
check("Gerüst: GWS-Vorlage mit den Skoliose-Sätzen, Punkt, Schluss",
      g is not None and g.report.startswith("## Ganzaufnahme der Wirbelsäule a.-p.\n\n## Befund\nWirbelsäule: " + S1)
      and g.report.endswith(f"## Ergebnis\n{P_FIX}\n{ENDE}") and "(IB Lab SQUIRREL)" not in g.report, g and g.report)
g = I.geruest(B)
check("Gerüst ohne Leistung: nur die Sätze (eine Zeile) + Punkt + Schluss",
      g is not None and f"## Befund\n{S1} {S2} {S3}\n" in g.report, g and g.report)

# ── Gen-Prompt ──
p = I.prompt_block(B, T[GWS]["body"], diktat="Wirbelsäule.")
check("Gen-Prompt: SQUIRREL-Zeile + Regel (Vorlage wörtlich, keine eigene Skoliose, Wortwahl des Arztes)",
      "SQUIRREL: Sätze zur seitlichen Krümmung" in p and I.SQUIRREL_PROMPT in p and "44" not in p, p)
p = I.prompt_block(B, T[GWS]["body"], diktat="flachbogige skoliotische Asymmetrie")
check("Gen-Prompt (Krümmung diktiert): nur Cobb-Winkel angekündigt", "Cobb-Winkel (die Krümmung hat der Arzt" in p, p)

# ── Ablage-Rückfall (Brücke zu alt) ──
with tempfile.TemporaryDirectory() as d:
    r = dict(roh("fixture"))
    bt_roh = r.pop("befundtext")
    pathlib.Path(d, f"{r['accno']}_squirrel.json").write_text(json.dumps(
        {"format": I.ABLAGE_FORMAT, "accession_number": r["accno"], "version": r["version"],
         "vorbefund": {"befundtext": {"squirrel": bt_roh}}}, ensure_ascii=False), encoding="utf-8")
    liste, geholt = I.text_nachladen([r], d)
    bs = I.aus_liste(liste)
check("Ablage: SQUIRREL-Text aus der Abholer-Datei geholt (gleiche Fassung) + Hinweis „Brücke veraltet“",
      geholt == ["SQUIRREL v1"] and bs[0].befundtext and bs[0].befundtext["saetze"] == [S1, S2, S3]
      and any("Brücke an diesem PC veraltet" in h for h in I.anzeige_hinweise(bs)), (geholt, I.anzeige_hinweise(bs)))

# ── Muster wörtlich wie ris-mods (wenn vorhanden) ──
rm = pathlib.Path.home() / "dev" / "ris-mods" / "ibl" / "squirrel_ergebnis.py"
if rm.exists():
    q = rm.read_text(encoding="utf-8")
    me = (ROOT / "source_code" / "ibl_bausteine.py").read_text(encoding="utf-8")

    def muster(text, name):
        m = re.search(name + r" = re\.compile\(\n(.*?)\)\n", text, re.S)
        return m and m.group(1)
    check("DIKTAT_KRUEMMUNG / VORLAGE_ACHSE_NORMAL wörtlich wie ris-mods ibl/squirrel_ergebnis.py",
          all(muster(q, n) and muster(q, n) == muster(me, n) for n in ("DIKTAT_KRUEMMUNG", "VORLAGE_ACHSE_NORMAL")))
else:
    print("ℹ️  ris-mods nicht da – Muster-Gleichheit übersprungen")

text = "\n\n".join(snap) + "\n"
if "--snapshot-schreiben" in sys.argv:
    SNAP.write_text(text, encoding="utf-8")
    print(f"Snapshot geschrieben: {SNAP.relative_to(ROOT)}")
else:
    check("Snapshot squirrel_befunde.txt unverändert", SNAP.exists() and SNAP.read_text(encoding="utf-8") == text,
          "neu schreiben mit --snapshot-schreiben, wenn gewollt")
print(f"\n{'❌ ' + str(fails) + ' Fehler' if fails else '✅ alle SQUIRREL-Prüfungen grün'}")
sys.exit(1 if fails else 0)
