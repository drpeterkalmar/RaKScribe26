"""Gate v3.19.9 – IB Lab LAMA + FROG ohne Normbereiche (Georg Riegler 18.11.2026, Brief kaiscribe-ibl-ohne-norm-n1):
„Die Normalwerte kommen nicht in den Befund und das Ergebnis.“ Messwerte bleiben, „(Norm 0–15°)“, „[−2 bis 4°]“,
„[3 bis 17 mm]“ entfallen. Der Abholer (ris-mods ibl/lama_ergebnis.py, ibl/frog_ergebnis.py) schreibt sie seit 18.11.
nicht mehr; KaiScribe bereinigt Bausteine älterer Abholer beim Lesen (ibl_bausteine.ohne_norm).
Teil 1: die 10 echten LAMA-Fälle vom 17.11.2026 (snapshots/lama10_bausteine.json, erzeugt mit ris-mods vorbefund +
        bruecke.baustein_lesen) → Ergebnis wie nach sofortigem EOL als Snapshot (snapshots/lama10_befunde.txt; neu
        schreiben: LAMA_SNAPSHOT=schreiben).
Teil 2: in keinem der 10+10 Fälle (LAMA, FROG + Beispielbild) ein Normbereich – weder Beschreibung noch Ergebnis.
Teil 3: Baustein eines Abholers ≤ 1.3.8 (mit Norm) → eingesetzt ohne Norm; andere Module unverändert.
Keine Patientendaten (Auftragsnummern erfunden).  Aufruf: /usr/bin/python3 tests/offline/test_ibl_ohne_norm.py"""
import copy, json, os, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402,F401

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
SNAP = ROOT / "tests" / "offline" / "snapshots"
LAMA = json.loads((SNAP / "lama10_bausteine.json").read_text(encoding="utf-8"))["faelle"]
FROG = json.loads((SNAP / "frog10_bausteine.json").read_text(encoding="utf-8"))["faelle"]
NORM = re.compile(r"\(Norm\b|\bNorm\s+[−\d]|\[[−\d]|\d\s*bis\s*[−\d]+\s*(?:°|mm)\]")
GB = "ganzbeinaufnahme_im_stand"
LEISTUNG = [{"kurz": "x-gb", "text": "Ganzbein", "appc": "", "modalitaet": "Röntgen", "seite": None, "vorlage": GB,
             "ohne_vorlage": False, "bekannt": True}]
FROG_CAS = {"fussl": ("fuß_in_2_ebenen", "Fuß links unauffällig."), "fussr": ("fuß_in_2_ebenen", "Fuß rechts unauffällig."),
            "fuss2": ("fuß_in_2_ebenen", "Fuß beidseits unauffällig."),
            "vofu2": ("vorfuß_in_2_ebenen", "Vorfuß beidseits unauffällig."),
            "spruful": ("sprunggelenk_mit_fuss", "Sprunggelenk links mit Fuß unauffällig."),
            "sprufu2": ("sprunggelenk_mit_fuss", "Sprunggelenk beidseits mit Fuß unauffällig.")}
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# ───────────────────────────── Teil 1: LAMA, 10 echte Fälle ─────────────────────────────
check("10 LAMA-Fälle im Snapshot", len(LAMA) == 10, len(LAMA))
zeilen = ["IB Lab LAMA – fester Ergebnistext (Georg Riegler 17.11.2026, ohne Normbereiche seit 18.11.2026): 10 echte "
          "anonyme Fälle.", "Je Fall: das Ergebnis, wie KaiScribe 3.19.9 es ohne Diktat (sofort EOL) als fertigen Befund setzt.",
          ""]
lama_texte = []
for f in LAMA:
    g = I.geruest(I.aus_liste([f["baustein"]]), LEISTUNG, T)
    ok = g is not None and "## Ergebnis\n" in g.report
    erg = g.report.split("## Ergebnis\n", 1)[1].strip() if ok else ""
    lama_texte.append(g.report if g else "")
    zeilen += [f"### Fall {f['nr']} – {g.report.split(chr(10), 1)[0][3:] if g else '?'} ({f['beschreibung']})",
               "Ergebnis:"] + erg.split("\n") + [""]
    check(f"LAMA Fall {f['nr']}: Gerüst mit Ergebnis, Schlussanmerkung zuletzt, Gate ok",
          ok and erg.endswith(f["baustein"]["ergebnis"][-1]) and I.gate(g.report, g.zeilen) == [], g.report if g else None)
snap_datei = SNAP / "lama10_befunde.txt"
snap = "\n".join(zeilen).rstrip() + "\n"
if os.environ.get("LAMA_SNAPSHOT") == "schreiben":
    snap_datei.write_text(snap, encoding="utf-8")
    print("(Snapshot neu geschrieben)")
check("Snapshot der 10 LAMA-Texte unverändert (snapshots/lama10_befunde.txt)",
      snap_datei.exists() and snap_datei.read_text(encoding="utf-8") == snap, snap)
check("LAMA Fall 10 wörtlich wie Georgs Beispiel",
      "Varusfehlstellung rechts (HKA 5,0°, MAD 20,3 mm). Regelrechte Beinachse links (HKA 3,0°, MAD 12,0 mm)."
      in lama_texte[[f["nr"] for f in LAMA].index(10)], lama_texte[-1])

# ───────────────────────────── Teil 2: nie ein Normbereich (10 + 10 + Beispielbild) ─────────────────────────────
for f in LAMA:
    b = I.aus_liste([f["baustein"]])
    texte = b[0].ergebnis + I.anzeige_hinweise(b)
    check(f"LAMA Fall {f['nr']}: kein Normbereich in Ergebnis und Hinweisen", not [t for t in texte if NORM.search(t)], texte)
for f in FROG:
    vorlage, diktat = FROG_CAS[f["cas_code"]]
    alt = pl.bypass_befund(diktat, T[vorlage])
    e = I.einsetzen(alt, I.aus_liste([f["baustein"]]), diktat=diktat)
    check(f"FROG Fall {f['nr']}: kein Normbereich in Beschreibung und Ergebnis", not NORM.search(e.report), e.report)

# ───────────────────────────── Teil 3: Baustein eines älteren Abholers (mit Norm) ─────────────────────────────
L10 = next(f["baustein"] for f in LAMA if f["nr"] == 10)
ALT_PUNKT = ("Varusfehlstellung rechts (HKA 5,0° [−2 bis 4°], MAD 20,3 mm [3 bis 17 mm]). Regelrechte Beinachse links "
             "(HKA 3,0° [−2 bis 4°], MAD 12,0 mm [3 bis 17 mm]).")
alt_lama = dict(copy.deepcopy(L10), ergebnis=[L10["ergebnis"][0], ALT_PUNKT, L10["ergebnis"][-1]],
                hinweise=["IB Lab LAMA rechts: HKA und MAD weisen in verschiedene Richtungen (HKA 5,0° [−2 bis 4°], MAD "
                          "−8,0 mm [3 bis 17 mm]) – keine Beinachse ins Ergebnis, bitte am KI-Bild beurteilen."])
b = I.aus_liste([alt_lama])
check("alter LAMA-Baustein: Punkte und Hinweise ohne Norm, Messwerte bleiben",
      b[0].ergebnis == L10["ergebnis"] and b[0].hinweise == [
          "IB Lab LAMA rechts: HKA und MAD weisen in verschiedene Richtungen (HKA 5,0°, MAD −8,0 mm) – keine Beinachse ins "
          "Ergebnis, bitte am KI-Bild beurteilen."], (b[0].ergebnis, b[0].hinweise))
g_alt, g_neu = I.geruest(b, LEISTUNG, T), I.geruest(I.aus_liste([L10]), LEISTUNG, T)
check("   … Gerüst bit-gleich wie mit dem neuen Abholer", g_alt.report == g_neu.report, g_alt.report)
F7 = next(f for f in FROG if f["nr"] == 7)
alt_frog = copy.deepcopy(F7["baustein"])
alt_frog["befundtext"]["stellung"] = [
    "Valgusstellung der Großzehe beidseits mit einem Hallux-valgus-Winkel von rechts 31° und links 30° (Norm 0–15°) bei "
    "vergrößertem Intermetatarsalwinkel I/II von rechts 16° und links 16° (Norm 0–10°)."]
alt_frog["befundtext"]["gewoelbe"] = ["Erhöhtes Längsgewölbe mit einer Calcaneusneigung von 34° (Norm 20–30°)."]
vorlage, diktat = FROG_CAS[F7["cas_code"]]
basis = pl.bypass_befund(diktat, T[vorlage])
e_alt = I.einsetzen(basis, I.aus_liste([alt_frog]), diktat=diktat)
e_neu = I.einsetzen(basis, I.aus_liste([F7["baustein"]]), diktat=diktat)
check("alter FROG-Baustein (Norm in den Sätzen) → Befund bit-gleich wie mit dem neuen Abholer",
      e_alt.report == e_neu.report and not NORM.search(e_alt.report), e_alt.report)
check("ohne_norm: Meary negativ, Tibial Slope, nichts anderes angefasst",
      I.ohne_norm("Meary-Winkel von −12° (Norm −4 bis 4°).") == "Meary-Winkel von −12°."
      and I.ohne_norm("Tibial Slope rechts 7,0° [5 bis 10°].") == "Tibial Slope rechts 7,0°."
      and I.ohne_norm("Hüfte (rechts) [Seite] im Normbereich.") == "Hüfte (rechts) [Seite] im Normbereich.")
hippo = {"accno": "T-0099", "ziffer": 1, "modul": "hippo", "name": "HIPPO", "version": 1,
         "befundteil": ["LCE-Winkel rechts 30° (IB Lab HIPPO)."], "ergebnis": ["Wert [3 bis 17 mm] bleibt."]}
check("andere Module unverändert (nur LAMA und FROG werden bereinigt)",
      I.aus_liste([hippo])[0].ergebnis == ["Wert [3 bis 17 mm] bleibt."])

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
