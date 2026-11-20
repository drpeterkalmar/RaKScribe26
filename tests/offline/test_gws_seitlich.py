"""Gate kaiscribe-gws-seitlich-vorlage-n1 (Georg Riegler 20.11.2026 „A“): Vorlage der Ganzwirbelsäule nach CAS-Leistung.
Leistungskatalog der Praxis (ris-mods auditor/regeln/pflicht_ebenen.toml, nur Kürzel/Kurztext): gws „WS Ganzaufn. ap + stl.
geteilt“, gesws2 „WS Ganzaufn.im Stehen ap+seitl“, wsg2 „WS Ganzaufn.steh.ap u.seitl.“ – die Brücke ordnet alle drei der
Vorlage „Ganzaufnahme der Wirbelsäule a.-p.“ zu (ohne HWS/BWS/LWS-Abschnitte). Jetzt:
  - GWS mit Seitaufnahme laut Leistungstext → „Gesamte Wirbelsäule“ (cas_vorlagen.gws_vorlage), auch wenn das Diktat
    keine Region nennt oder nur „Ganzaufnahme …“ bzw. einen Abschnitt („LWS: …“) sagt (abgleich, WS_TEILE).
  - Nur a.p. laut Leistung → wie bisher „Ganzaufnahme der Wirbelsäule a.-p.“.
  - Rückfall ohne/unklare Leistung: Stichwort im Diktat („in 2 Ebenen“, „a.p. und seitlich“, „seitlich“) bei Ganzaufnahme
    → „Gesamte Wirbelsäule“ (vorlagen_vorrang.json, EXE = Web; Parität über detect_fixtures.json).
  - SQUIRREL (Cobb 44°) mit Diktat „flachbogige skoliotische Asymmetrie“ auf der Gesamt-Vorlage: Wortwahl bleibt, nur
    Cobb-Satz, HWS-/LWS-Achsensatz entfällt, „Harmonische Kyphose“ bleibt.
  - Mehrfach GWS + Becken: zwei Befunde, Trennung bleibt; hws_und_lws ohne CAS unverändert.
Synthetische Diktate, keine Patientendaten.  Aufruf: python3 tests/offline/test_gws_seitlich.py"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import cas_vorlagen as cv  # noqa: E402
import detect  # noqa: E402
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
SQ = json.loads((ROOT / "tests" / "offline" / "squirrel_bausteine.json").read_text(encoding="utf-8"))
erkennen = lambda t: detect.detect_template(t, T)  # noqa: E731
AP, GESAMT = "ganzaufnahme_der_wirbelsäule_a-p", "wirbelsäule_gesamt"
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def L(kurz, text, vorlage):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": "Röntgen", "seite": None, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True}


# wie die Praxis-Zuordnung (ris-mods katalog/kuerzel_vorlage.tsv, Stand 13.10.2026)
GWS = L("gws", "WS Ganzaufn. ap + stl. geteilt", AP)
GESWS2 = L("gesws2", "WS Ganzaufn.im Stehen ap+seitl", AP)
WSG2 = L("wsg2", "WS Ganzaufn.steh.ap u.seitl.", AP)
GWS2 = L("gws2", "Ges.Wirbelsäule steh.ap+stl.", GESAMT)
GWS1 = L("gws1", "Gesamte Wirbelsäule stehend", GESAMT)
WS_AP = L("wsap", "Wirbelsäule ap.", None)                       # Zuordnung „?“
GWS_AP = L("gwsap", "WS Ganzaufnahme a.p.", AP)                   # synthetisch: reine a.p.-Leistung
BUE = L("bü", "Becken", "beckenübersicht_stehend")
FLWS = L("flws", "Funktionsaufnahmen LWS", "funktionsaufnahmen_der_lendenwirbelsäule")


def wahl(diktat, leistungen):
    c = cv.CasHinweis(leistungen, T)
    segs = cv.aufteilen(br.split_regionen(diktat), c, T, erkennen)
    segs, _, _ = cv.inhalt_zuordnen(segs, c, T, erkennen)
    return [cv.wahl(br.rho_erkennen(s)[0], c, T, erkennen).vorlage for s in segs]


# ───────────────────────────── 1. CAS-Leistung → Vorlage ─────────────────────────────
for l in (GWS, GESWS2, WSG2):
    c = cv.CasHinweis([l], T)
    check(f"CAS {l['kurz']} „{l['text']}“ → Gesamte Wirbelsäule", c.vorlagen() == [GESAMT] and c.alle[0].gws_seitlich,
          c.vorlagen())
check("CAS gws2 (Brücke schon Gesamt) bleibt Gesamt", cv.CasHinweis([GWS2], T).vorlagen() == [GESAMT])
check("CAS reine a.p.-Leistung → wie bisher Ganzaufnahme a.-p.", cv.CasHinweis([GWS_AP], T).vorlagen() == [AP])
check("CAS „Wirbelsäule ap.“ ohne Zuordnung bleibt ohne Vorlage", cv.CasHinweis([WS_AP], T).alle[0].vorlage is None)
check("Muster: „seitl“/„stl.“/„u.seitl.“ ja, „Stehen“/„geteilt“ allein nein",
      all(cv.gws_vorlage(AP, t, T) == GESAMT for t in ("WS Ganzaufn. ap + stl. geteilt", "WS Ganzaufn.im Stehen ap+seitl",
                                                       "WS Ganzaufn.steh.ap u.seitl.", "Ganzaufnahme WS a.p. lateral"))
      and all(cv.gws_vorlage(AP, t, T) == AP for t in ("WS Ganzaufn. im Stehen", "WS geteilt", "WS Ganzaufnahme a.p."))
      and cv.gws_vorlage("lendenwirbelsäule_in_2_ebenen", "WS Ganzaufn. ap + stl.", T) == "lendenwirbelsäule_in_2_ebenen")

# GWS a.p.-Leistung: Diktat „Ganzaufnahme …“ → a.p.
check("GWS a.p.-Leistung + Diktat „Ganzaufnahme der Wirbelsäule: flachbogige Skoliose“ → a.p.",
      wahl("Ganzaufnahme der Wirbelsäule: flachbogige Skoliose.", [GWS_AP]) == [AP])
check("GWS a.p.-Leistung + Diktat ohne Region → a.p.", wahl("Flachbogige Skoliose, sonst unauffällig.", [GWS_AP]) == [AP])
# GWS+seitlich-Leistung ohne Regionsnennung
for d in ("Flachbogige skoliotische Asymmetrie, sonst unauffällig.", "Osteochondrose L5/S1.", "Unauffällig.",
          "Ganzaufnahme der Wirbelsäule: Osteochondrose L5/S1.", "LWS: Osteochondrose L5/S1.",
          "HWS: Osteochondrose C5/C6. LWS: Spondylose L4.", "Ganzaufnahme der Wirbelsäule a.-p. unauffällig"):
    check(f"CAS gws + Diktat „{d}“ → Gesamte Wirbelsäule", wahl(d, [GWS]) == [GESAMT], wahl(d, [GWS]))
check("CAS gws1 „Gesamte Wirbelsäule stehend“ (ohne „seitlich“) + Diktat „Ganzaufnahme …“ → Diktat a.p. wie bisher",
      wahl("Ganzaufnahme der Wirbelsäule: unauffällig.", [GWS1]) == [AP])
check("CAS gws + flws, Diktat „LWS Funktion …“ → Funktions-Vorlage bleibt",
      wahl("Funktionsaufnahmen der LWS: keine Instabilität.", [GWS, FLWS]) == ["funktionsaufnahmen_der_lendenwirbelsäule"])
h = cv.hinweise(["Unauffällig."], [cv.wahl("Unauffällig.", cv.CasHinweis([GWS], T), T, erkennen)],
                cv.CasHinweis([GWS], T), T)
check("CAS gws + Diktat „Unauffällig.“: kein „nicht diktiert“-Hinweis", h == [], h)

# ───────────────────────────── 2. Stichwort-Rückfall (ohne CAS) ─────────────────────────────
for d, soll in (("Ganzaufnahme der Wirbelsäule a.-p. unauffällig", AP),
                ("Ganzaufnahme der Wirbelsäule unauffällig", AP),
                ("Ganzaufnahme der Wirbelsäule in 2 Ebenen unauffällig", GESAMT),
                ("Ganzaufnahme der Wirbelsäule a.p. und seitlich, flachbogige skoliotische Asymmetrie", GESAMT),
                ("Ganzaufnahme mit seitlich: Osteochondrose L5/S1", GESAMT),
                ("Wirbelsäulenganzaufnahme seitlich: Hyperkyphose", GESAMT),
                ("Ganzaufnahme der Wirbelsäule ohne seitliche Aufnahme, unauffällig", AP),
                ("Röntgen der Wirbelsäule im Stehen als Ganzaufnahme, flachbogige Skoliose", AP),
                ("Gesamte Wirbelsäule unauffällig", GESAMT),
                ("HWS: Osteochondrose C5/C6. LWS: Spondylose.", "hws_und_lws")):
    check(f"ohne CAS „{d}“ → {soll}", erkennen(d) == soll, erkennen(d))
check("Unklare Leistung „Wirbelsäule ap.“ + Diktat „Ganzaufnahme in 2 Ebenen …“ → Stichwort gilt",
      wahl("Ganzaufnahme der Wirbelsäule in 2 Ebenen: unauffällig.", [WS_AP]) == [GESAMT])

# ───────────────────────────── 3. SQUIRREL (Cobb 44°) auf der Gesamt-Vorlage ─────────────────────────────
B = I.aus_liste([next(f["baustein"] for f in SQ if f["fall"] == "einzeln")])
body = T[GESAMT]["body"].split("\n", 2)[2]
ki = "Flachbogige skoliotische Asymmetrie.\n\n" + body      # KI: Diktat-Satz an den Anfang (wie Vorlage + Diktat)
e = I.einsetzen(f"## Gesamte Wirbelsäule\n\n## Befund\n{ki}\n\n## Ergebnis\nFlachbogige skoliotische Asymmetrie.", B,
                diktat="Flachbogige skoliotische Asymmetrie, sonst unauffällig.", cas_leistungen=[GWS], templates=T)
bef = e.report.split("## Befund\n")[1].split("\n\n## Ergebnis")[0]
check("SQUIRREL Gesamt: Diktat wörtlich am Anfang, dahinter nur der Cobb-Satz 44°",
      bef.startswith("Flachbogige skoliotische Asymmetrie. Cobb-Winkel 44° (Th5–Th12).") and "Skoliose" not in e.report, bef)
check("SQUIRREL Gesamt: „Normaler Achsenverlauf“ (HWS) und „Annähernd achsengerechte Stellung“ (LWS) entfallen",
      "Normaler Achsenverlauf" not in bef and "Annähernd achsengerechte Stellung" not in bef, bef)
check("SQUIRREL Gesamt: „Harmonische Kyphose“ bleibt, Abschnitte HWS/BWS/LWS bleiben",
      "Harmonische Kyphose." in bef and all(x in bef for x in ("HWS:", "BWS:", "LWS:")), bef)
g = I.geruest(B, [GWS], T)
check("IB-Lab-Gerüst mit CAS gws: Titel „Gesamte Wirbelsäule“", g is not None and g.report.startswith(
    "## Gesamte Wirbelsäule"), g.report if g else None)


# ───────────────────────────── 4. ganze EXE-Kette: GWS + Becken ─────────────────────────────
def ki_attrappe(prompts):
    def llm(p):
        prompts.append(p)
        titel = p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0]
        key = next(k for k, v in T.items() if v.get("display_name") == titel)
        return f"## {titel}\n\n## Befund\n" + T[key]["body"].split("\n", 2)[2] + "\n\n## Ergebnis\n" + T[key]["ergebnis"]
    return llm


for name, diktat in (("mit Überschriften", "Ganzaufnahme der Wirbelsäule: Osteochondrose L5/S1. Beckenübersicht: "
                                            "Geringgradige Coxarthrose links."),
                     ("ohne Regionsnennung", "Osteochondrose L5/S1, geringe Coxarthrose links, Spondylophyten L3 bis L5")):
    prompts = []
    ctx = pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=ki_attrappe(prompts), log=lambda *a: None,
                     cas=cv.CasHinweis([GWS, BUE], T))
    erg = pl.befund_aus_diktat(diktat, ctx)
    check(f"GWS + Becken {name}: zwei Befunde Gesamte Wirbelsäule + Becken",
          sorted(erg.vorlagen) == sorted([GESAMT, "beckenübersicht_stehend"]) and "## Gesamte Wirbelsäule" in erg.report
          and "Ganzaufnahme der Wirbelsäule a.-p." not in erg.report, f"{erg.vorlagen}\n{erg.report}")
    check(f"GWS + Becken {name}: kein „nicht diktiert“-Hinweis", not any("nicht diktiert" in x for x in erg.cas_hinweise),
          erg.cas_hinweise)
prompts = []
ctx = pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=ki_attrappe(prompts), log=lambda *a: None)
erg = pl.befund_aus_diktat("Ganzaufnahme der Wirbelsäule a.-p. und seitlich: unauffällig.", ctx)
check("EXE-Kette ohne CAS, Diktat „a.-p. und seitlich“ → Befund „Gesamte Wirbelsäule“ mit HWS/BWS/LWS",
      erg.report.startswith("## Gesamte Wirbelsäule") and all(x in erg.report for x in ("HWS:", "BWS:", "LWS:")), erg.report)

print(f"\n{'✅ alle grün' if not fails else f'❌ {fails} rot'}")
sys.exit(1 if fails else 0)
