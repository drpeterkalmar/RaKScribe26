"""Gate 3.19.16 (Peter 20.11.2026, kaiscribe-befundfeld-sicher-n1): rechtes Befundfeld nie mehr still überschreiben.
„Wenn schon was rechts steht und ich dazudiktieren möchte, wird manchmal alles gelöscht oder der Titel ändert sich,
irgendwie random.“
1. befundfeld.py = befundfeld.ts über die gemeinsamen Fälle snapshots/befundfeld_faelle.txt (Web: pipeline_test.mjs),
   inkl. Restructure mit fester KI-Antwort (pipeline.befund_umbauen ≡ pipeline.ts befundUmbauen).
2. EXE-Abläufe mit Attrappen: Ergänzung ohne Fokus (Titel/Text bleiben), mit Cursor, mit Markierung, IB-Lab-Gerüst +
   Diktat, leeres Feld, F1 Neu, Clear all, Reset nach 2 Ergänzungen, Restructure-Knopf, Strg+Z, doppeltes INS.
Aufruf: python tests/offline/test_befundfeld.py   (--schreiben = Fälle neu erzeugen, danach Web-Test laufen lassen)
"""
import json, pathlib, sys
HIER = pathlib.Path(__file__).resolve().parent
ROOT = HIER.parents[1]
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(ROOT / "source_code"))
import befundfeld as bf  # noqa: E402
import pipeline as pl  # noqa: E402
import befund_regeln as br  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
FAELLE = HIER / "snapshots" / "befundfeld_faelle.txt"


def koerper(key):
    return "\n".join(T[key]["body"].split("\n")[1:]).strip()


KNIE = ("## Kniegelenk links in 2 Ebenen\n\n## Befund\n" + koerper("kniegelenk_in_2_ebenen")
        + "\n\n## Ergebnis\n" + T["kniegelenk_in_2_ebenen"]["ergebnis"])
KNIE_SPONG = KNIE.replace("Mineralgehalt und Knochenstruktur sind regelrecht.",
                          "Unauffällige Spongiosa. Mineralgehalt und Knochenstruktur sind regelrecht.")
LWS = ("## Lendenwirbelsäule in 2 Ebenen\n\n## Befund\nRegelrechte Stellung der Wirbelkörper. Bandscheibenfächer normal "
       "hoch. Mineralgehalt und Knochenstruktur sind regelrecht.\n\n## Ergebnis\nRegelrechte Darstellung der LWS.")
KL2 = ("## Kniegelenk rechts in 2 Ebenen\n\n## Befund\nNormale Form und Stellung. " + br.KL_TABELLE[2]
       + " Patella in regelrechter Position. Unauffällige Weichteile.\n\n## Ergebnis\n"
       "Geringgradige Gonarthrose rechts (Arthrose Grad 2 nach Kellgren & Lawrence).")
KIND = ("## Hand links in 2 Ebenen\n\n## Befund\nAltersentsprechend offene Wachstumsfugen. Regelrechte Stellung. Keine "
        "Fraktur.\n\n## Ergebnis\nAltersentsprechender Befund der linken Hand ohne Fraktur.")


def erg(text, neu):
    return bf.ergaenzen(text, neu)[0]


# Restructure-Fälle: aktuell, stand, feste KI-Antwort (für JEDEN KI-Aufruf; Web: Call 1 und Call 2)
UMBAU = [
    {"name": "Enostose dazudiktiert → „Unauffällige Spongiosa“ fliegt raus, Ergebnis nennt Enostose",
     "stand": KNIE_SPONG, "aktuell": erg(KNIE_SPONG, "Enostose im distalen Femur von 6 mm"),
     "llm": "## Kniegelenk links\n\n## Befund\nNormale Form und Stellung der dargestellten Skelettabschnitte. Unauffällige "
            "Spongiosa. Enostose im distalen Femur von 6 mm. Glatte und scharfe Kontur der Kortikalis ohne pathologische "
            "Konturunterbrechung. Der Gelenkspalt ist allseits normal weit. Unauffällige Weichteile.\n\n## Ergebnis\n"
            "Enostose im distalen Femur links."},
    {"name": "Ergänzung ändert das Ergebnis (Erguss), KI passt es an",
     "stand": KNIE, "aktuell": erg(KNIE, "kleiner Gelenkerguss im Recessus suprapatellaris"),
     "llm": "## Kniegelenk in 2 Ebenen\n\n## Befund\nNormale Form und Stellung der dargestellten Skelettabschnitte. Der "
            "Gelenkspalt ist allseits normal weit. Kleiner Gelenkerguss im Recessus suprapatellaris.\n\n## Ergebnis\n"
            "Kleiner Gelenkerguss im Recessus suprapatellaris links."},
    {"name": "Ergänzung mit Befund, KI lässt das Ergebnis normal → rote Prüfzeile",
     "stand": KNIE, "aktuell": erg(KNIE, "kleiner Gelenkerguss im Recessus suprapatellaris"),
     "llm": "## Kniegelenk in 2 Ebenen\n\n## Befund\nNormale Form und Stellung der dargestellten Skelettabschnitte. "
            "Kleiner Gelenkerguss im Recessus suprapatellaris.\n\n## Ergebnis\nRegelrechte Darstellung des Kniegelenkes."},
    {"name": "KI verliert Peters Angabe → wörtlich nachgetragen + Prüfzeile",
     "stand": KNIE, "aktuell": erg(KNIE, "alte knöcherne Absprengung am Fibulaköpfchen von 4 mm"),
     "llm": "## Kniegelenk links\n\n## Befund\nNormale Form und Stellung der dargestellten Skelettabschnitte.\n\n"
            "## Ergebnis\nRegelrechte Darstellung des Kniegelenkes."},
    {"name": "Mehrfachbefund: nur der geänderte Abschnitt wird umgebaut, Knie (K&L-Tabelle) bleibt Zeichen für Zeichen",
     "stand": KL2 + "\n\n\n" + LWS, "aktuell": KL2 + "\n\n\n" + erg(LWS, "Osteochondrose L5/S1"),
     "llm": "## LWS\n\n## Befund\nRegelrechte Stellung der Wirbelkörper. Osteochondrose L5/S1 mit Höhenminderung des "
            "Bandscheibenfachs. Im Übrigen normal hohe Bandscheibenfächer.\n\n## Ergebnis\nOsteochondrose L5/S1."},
    {"name": "K&L-Befund + Ergänzung: Tabellensatz und Grad bleiben",
     "stand": KL2, "aktuell": erg(KL2, "zusätzlich kleiner Gelenkerguss"),
     "llm": "## Kniegelenk rechts\n\n## Befund\nNormale Form und Stellung. " + br.KL_TABELLE[2] + " Kleiner Gelenkerguss. "
            "Patella in regelrechter Position. Unauffällige Weichteile.\n\n## Ergebnis\n1. Geringgradige Gonarthrose "
            "rechts (Arthrose Grad 2 nach Kellgren & Lawrence).\n2. Kleiner Gelenkerguss rechts."},
    {"name": "Kinder-Befund + Ergänzung: Wachstumsfugen-Satz bleibt",
     "stand": KIND, "aktuell": erg(KIND, "Weichteilschwellung dorsal über dem Handgelenk"),
     "llm": "## Hand links\n\n## Befund\nAltersentsprechend offene Wachstumsfugen. Regelrechte Stellung. Keine Fraktur. "
            "Weichteilschwellung dorsal über dem Handgelenk.\n\n## Ergebnis\n1. Weichteilschwellung dorsal über dem "
            "Handgelenk links.\n2. Keine Fraktur."},
    {"name": "KI verliert eine eigene (nicht aus der Vorlage stammende) Angabe → Prüfzeile",
     "stand": KIND, "aktuell": erg(KIND, "Weichteilschwellung dorsal"),
     "llm": "## Hand links\n\n## Befund\nRegelrechte Stellung. Keine Fraktur. Weichteilschwellung dorsal.\n\n## Ergebnis\n"
            "Weichteilschwellung dorsal links."},
    {"name": "Fraktur ergänzt: „Kein Hinweis auf eine Fraktur.“ fällt gewollt weg, ohne Prüfzeile",
     "stand": KIND, "aktuell": erg(KIND, "Wulstfraktur des distalen Radius"),
     "llm": "## Hand links\n\n## Befund\nAltersentsprechend offene Wachstumsfugen. Regelrechte Stellung. Wulstfraktur des "
            "distalen Radius.\n\n## Ergebnis\nWulstfraktur des distalen Radius links."},
    {"name": "nichts geändert → nichts umzubauen (kein KI-Aufruf)", "stand": KNIE, "aktuell": KNIE, "llm": ""},
    {"name": "ohne KaiScribe-Stand (getippter Text) → alles hat Vorrang", "stand": "",
     "aktuell": "Knie links: kleine Enostose im Femurkondylus, sonst unauffällig.",
     "llm": "## Kniegelenk links in 2 Ebenen\n\n## Befund\nKleine Enostose im Femurkondylus. Der Gelenkspalt ist allseits "
            "normal weit.\n\n## Ergebnis\nKleine Enostose im Femurkondylus links."},
]


def umbau_lauf(f):
    prompts = []

    def llm(p):
        prompts.append(p)
        return f["llm"]
    ctx = pl.Kontext(templates=T, display_names=[t["display_name"] for t in T.values()], prompt=PROMPT, llm=llm,
                     log=lambda *a: None)
    e = pl.befund_umbauen(f["aktuell"], f["stand"], ctx)
    return e, prompts


def faelle_bauen():
    out = []
    for name, text, neu in [
        ("Knie: Ergänzung ans Ende des Befundteils", KNIE, "zusätzlich kleiner Gelenkerguss"),
        ("Mehrfachbefund: Ergänzung zur LWS (Region im Diktat)", KL2 + "\n\n\n" + LWS, "LWS: Osteochondrose L5/S1"),
        ("Mehrfachbefund ohne Region: in den letzten Abschnitt", LWS + "\n\n\n" + KL2, "kleiner Erguss"),
        ("Seite entscheidet bei zwei Knien", KL2 + "\n\n\n" + KNIE, "Knie rechts zusätzlich Erguss"),
        ("Nur-Text-Inhalt: angehängt", "Kniegelenk rechts unauffällig.", "zusätzlich kleiner Erguss"),
        ("Fließtext mit Ergebnis-Zeile: davor", "Knie rechts: Erguss.\nErgebnis: Erguss.", "Bänder intakt"),
        ("leeres Feld", "", "Knie rechts unauffällig"),
        ("nur Ergebnis-Abschnitt", "## Knie\n\n## Ergebnis\nUnauffällig.", "kleiner Erguss"),
        ("Satzzeichen bleibt, klein → groß", KNIE, "Erguss?"),
    ]:
        r = bf.ergaenzen(text, neu)
        out.append({"art": "ergaenzen", "name": name, "text": text, "neu": neu, "ergebnis": r[0], "cursor": r[1]})
    for name, stand, akt in [("Ergänzung + getippte Änderung", KNIE, erg(KNIE, "Erguss").replace("Patella in regelrechter",
                                                                                                   "Patella leicht hochstehend in"
                                                                                                   " regelrechter")),
                             ("Ergebnis-Nummer zählt nicht", "## A\n\n## Ergebnis\n1. Erguss.", "## A\n\n## Ergebnis\nErguss.")]:
        out.append({"art": "vorrang", "name": name, "stand": stand, "aktuell": akt, "ergebnis": bf.vorrang(stand, akt)})
    for f in UMBAU[:1] + UMBAU[4:5]:
        v = bf.vorrang(f["stand"], f["aktuell"])
        seg, weg = bf.umbau_segment(f["aktuell"], v)
        out.append({"art": "umbau_segment", "name": f["name"], "text": f["aktuell"], "vor": v, "ergebnis": [seg, weg],
                    "block": bf.umbau_block(v, weg)})
    out.append({"art": "umbau_block", "name": "ohne Stand", "vor": [], "ohne_stand": True,
                "ergebnis": bf.umbau_block([], [], True)})
    out.append({"art": "titel", "name": "Titel bleiben", "neu": "## X\n\n## Befund\na.\n\n\n## Y\n\n## Befund\nb.",
                "alt": ["Knie links", "LWS"],
                "ergebnis": bf.titel_uebernehmen("## X\n\n## Befund\na.\n\n\n## Y\n\n## Befund\nb.", ["Knie links", "LWS"])})
    for f in UMBAU:
        e, prompts = umbau_lauf(f)
        out.append({"art": "umbau", "name": f["name"], "stand": f["stand"], "aktuell": f["aktuell"], "llm": f["llm"],
                    "ergebnis": {"report": e.report, "hinweise": list(e.cas_hinweise), "leer": e.leer,
                                 "aufrufe": len(prompts)}})
    return out


if "--schreiben" in sys.argv:
    FAELLE.write_text(json.dumps(faelle_bauen(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("geschrieben:", FAELLE)

# ── 1. Gemeinsame Fälle (Web prüft dieselbe Datei) ────────────────────────────────────────────────────────────
gespeichert = json.loads(FAELLE.read_text(encoding="utf-8"))
jetzt = faelle_bauen()
check("Fälle-Datei aktuell (sonst: --schreiben)", len(gespeichert) == len(jetzt))
for g, j in zip(gespeichert, jetzt):
    check(f"{g['art']}: {g['name']}", g == j, json.dumps(j.get("ergebnis"), ensure_ascii=False)[:400])

U = {f["name"]: f for f in jetzt if f["art"] == "umbau"}
r = U[UMBAU[0]["name"]]["ergebnis"]
befund = r["report"].split("## Ergebnis")[0]
check("Restructure Enostose: Enostose im Befund UND Ergebnis, „Unauffällige Spongiosa“ gestrichen, Titel bleibt",
      "Enostose im distalen Femur von 6 mm" in befund and "Spongiosa" not in r["report"]
      and "enostose" in bf.ergebnis_text(r["report"]).lower()
      and r["report"].startswith("## Kniegelenk links in 2 Ebenen\n"), r["report"])
r = U[UMBAU[1]["name"]]["ergebnis"]
check("Restructure Erguss: Ergebnis angepasst, keine Prüfzeile", "erguss" in bf.ergebnis_text(r["report"]).lower()
      and not r["hinweise"], str(r))
r = U[UMBAU[2]["name"]]["ergebnis"]
check("Restructure: Pathologie fehlt im Ergebnis → rote Prüfzeile (bzw. vom Widerspruchs-Wächter ergänzt)",
      any("bitte prüfen" in h for h in r["hinweise"]) or "erguss" in bf.ergebnis_text(r["report"]).lower(), str(r))
r = U[UMBAU[3]["name"]]["ergebnis"]
check("Restructure: verlorene Angabe von Peter wörtlich nachgetragen + Prüfzeile",
      "Alte knöcherne Absprengung am Fibulaköpfchen von 4 mm." in r["report"].split("## Ergebnis")[0]
      and any("Fibulaköpfchen" in h and "bitte prüfen" in h for h in r["hinweise"]), str(r))
r = U[UMBAU[4]["name"]]["ergebnis"]
check("Restructure Mehrfachbefund: Knie-Abschnitt (K&L-Tabelle) Zeichen für Zeichen, LWS-Titel bleibt",
      r["report"].startswith(KL2 + "\n\n\n## Lendenwirbelsäule in 2 Ebenen\n") and "Osteochondrose L5/S1" in r["report"]
      and r["aufrufe"] == 1, r["report"][:200])
r = U[UMBAU[5]["name"]]["ergebnis"]
check("Restructure K&L: Tabellensatz Grad 2 und Grad im Ergebnis bleiben", br.KL_TABELLE[2] in r["report"]
      and "Grad 2 nach Kellgren" in r["report"] and "Gelenkerguss" in r["report"], r["report"])
r = U[UMBAU[6]["name"]]["ergebnis"]
check("Restructure Kinder: „Altersentsprechend offene Wachstumsfugen.“ bleibt, keine Prüfzeile",
      "Altersentsprechend offene Wachstumsfugen." in r["report"] and not r["hinweise"], str(r))
r = U[UMBAU[7]["name"]]["ergebnis"]
check("Restructure: verlorene eigene Angabe (Wachstumsfugen) → Prüfzeile",
      any("Wachstumsfugen" in h for h in r["hinweise"]), str(r))
r = U[UMBAU[8]["name"]]["ergebnis"]
check("Restructure Fraktur ergänzt: alter Verneinungssatz weg, keine Prüfzeile", "Keine Fraktur" not in r["report"]
      and "Wulstfraktur" in bf.ergebnis_text(r["report"]) and not r["hinweise"], str(r))
r = U[UMBAU[9]["name"]]["ergebnis"]
check("Restructure ohne Änderung: leer, kein KI-Aufruf", r["leer"] and r["aufrufe"] == 0, str(r))
e, prompts = umbau_lauf(UMBAU[0])
p = prompts[0]
check("Restructure-Prompt: Vorrang-Hinweis + Widerspruchsblock, voller Regel-Prompt, Diktat = aktueller Text",
      "<umbau>" in p and "„Enostose im distalen Femur von 6 mm.“" in p and "Unauffällige Spongiosa" in p.split("<umbau>")[1]
      and br.strip_prompt_marker(PROMPT).split("{roh_text}")[0][:2000] in p and "Enostose im distalen Femur" in p
      and "Kniegelenk links in 2 Ebenen:" in p, p[p.index("<umbau>"):p.index("<umbau>") + 300])
e, prompts = umbau_lauf(UMBAU[10])
check("Restructure ohne Stand: Prompt sagt „ganzer Text vom Arzt“", "Der ganze Text stammt vom Arzt" in prompts[0])
check("modus(): leer → neu, Text → Ergänzung, Cursor, Gerüst, Maske, schon hinausgegangen → neu (Cursor bleibt Cursor)",
      [bf.modus(""), bf.modus("x"), bf.modus("x", cursor=True), bf.modus("x", geruest=True), bf.modus("", maske=True),
       bf.modus("x", abgeschlossen=True), bf.modus("x", cursor=True, abgeschlossen=True)]
      == ["neu", "ergaenzung", "cursor", "geruest", "maske", "neu", "cursor"])

# ── 2. EXE-Abläufe ────────────────────────────────────────────────────────────────────────────────────────────
import exe_stubs as S  # noqa: E402
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: True
KORR = {"t": "Zusätzlich kleiner Gelenkerguss."}
mod._korr.korrigieren = lambda t, key, block="", log=None: KORR["t"]
LLM = {"antwort": None, "prompts": []}


def llm(p):
    LLM["prompts"].append(p)
    if LLM["antwort"] is None:
        raise AssertionError("Befund-KI gerufen")
    return LLM["antwort"]


mod._llm_aufruf = llm
BEFUND = "## Kniegelenk rechts\n\n## Befund\nKein Erguss. Bänder intakt.\n\n## Ergebnis\nUnauffälliger Befund."


class Var:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


def neue_app(rechts="", links="", fokus=False, insert=0, sel=None):
    app = S.baue_app(mod)
    if rechts:
        app.result_text.insert("1.0", rechts)
    if links:
        app.transcript_text.insert("1.0", links)
    tb = S.FakeTb(app.result_text, insert, sel)
    app.result_text._textbox = tb
    app.focus_get = (lambda: tb) if fokus else (lambda: None)
    app.status_badge = S.FakeWidget()
    app.repariert_label = S.FakeWidget()
    app.nur_text_var = Var(False)
    app._stand_erst = app._stand_ks = app._transkript_ks = app._fehl_stand = app._rueck = app._vor_lauf = None
    app._stand_erst_geruest, app._einbau = False, None
    return app, tb


def diktat(app, chirp="zusätzlich kleiner Gelenkerguss", taste="sm"):
    S.AUFZ.tasten.clear()
    mod._chirp3_worker = lambda pcm, sr, loc, token: chirp
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub())
    stati = []
    if taste == "sm":
        app.sm_record()
    else:
        app.toggle_recording()
    stati.append(app.status_badge.cfg.get("text", ""))
    S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
    if taste == "sm":
        app.sm_ins()
    else:
        app.toggle_recording()
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
    S.pump(app, lambda: False, 0.6)
    app._aufnahme_stoppen()
    return stati


# 2a. Ohne Fokus, Befund rechts (der Fall von Peter): Ergänzung, Titel + Text bleiben, keine Befund-KI
LLM["antwort"] = None
app, tb = neue_app(BEFUND, "Knie rechts unauffällig")
stati = diktat(app)
check("Ohne Fokus + Befund rechts → Ergänzung vor „## Ergebnis“, Titel und Text bleiben Zeichen für Zeichen, keine KI",
      app.result_text.text == BEFUND.replace("Bänder intakt.", "Bänder intakt.\nZusätzlich kleiner Gelenkerguss.")
      and not LLM["prompts"] and app._status_raw == "KONTROLLE" and S.AUFZ.tasten == [], repr(app.result_text.text))
check("… Statuszeile beim Record „Ergänzung“", "Ergänzung · Aufnahme läuft" in stati[0], str(stati))
check("… Strg+Z holt den Befund davor zurück", app._rueckgaengig() == "break" and app.result_text.text == BEFUND)

# 2b. F10 ohne CAS: auch Ergänzung (Befund danach wie immer kopiert, RaKScribe vorne → kein Strg+V)
app, tb = neue_app(BEFUND)
diktat(app, taste="f10")
check("F10 ohne Fokus + Befund rechts → Ergänzung, ganzer Befund kopiert", "Zusätzlich kleiner Gelenkerguss." in
      app.result_text.text and app.result_text.text.startswith("## Kniegelenk rechts")
      and "Gelenkerguss" in str(S.CLIPBOARD.data.get(13, "")), repr(app.result_text.text))

# 2b'. F10-Ablauf ohne CAS: der Befund ging automatisch hinaus (kopiert + Strg+V) → nächstes F10 = neuer Patient =
# neuer Befund (wie nach EOL), NICHT Ergänzung in den alten; Strg+Z holt ihn zurück
NEUF10 = ("## Schultergelenk links in 2 Ebenen\n\n## Befund\nKalkdepot im Verlauf der Supraspinatussehne. Sonst regelrecht."
          "\n\n## Ergebnis\nKalkdepot links.")
LLM["antwort"], LLM["prompts"] = NEUF10, []
app, tb = neue_app()
diktat(app, chirp="Schulter links Kalkdepot", taste="f10")
erster_f10 = app.result_text.text
LLM["antwort"] = NEUF10.replace("links", "rechts")
stati = diktat(app, chirp="Schulter rechts Kalkdepot", taste="f10")
check("F10 ohne CAS: nach automatischem Kopieren ist der Befund fertig → nächstes F10 = „Neuer Befund“, Strg+Z da",
      "Neuer Befund" in stati[0] and len(LLM["prompts"]) == 2 and app._rueck == erster_f10, f"{stati} {len(LLM['prompts'])}")
LLM["antwort"] = None

# 2c. Mit Cursor / Markierung: wie bisher an der Stelle
pos = BEFUND.index("Bänder")
app, tb = neue_app(BEFUND, fokus=True, insert=pos)
stati = diktat(app)
check("Mit Cursor → an der Stelle (Statuszeile „Ergänzung an Cursor-Stelle“)",
      app.result_text.text == BEFUND.replace("Kein Erguss. Bänder", "Kein Erguss. Zusätzlich kleiner Gelenkerguss. Bänder")
      and "Ergänzung an Cursor-Stelle" in stati[0], repr(app.result_text.text))
a = BEFUND.index("Kein Erguss.")
app, tb = neue_app(BEFUND, fokus=True, sel=(a, a + len("Kein Erguss.")))
diktat(app)
check("Mit Markierung → ersetzt", app.result_text.text == BEFUND.replace("Kein Erguss.", "Zusätzlich kleiner Gelenkerguss."))

# 2d. Leeres Feld → neuer Befund (Statuszeile „Neuer Befund“), erster Stand gemerkt
NEU1 = "## Kniegelenk rechts in 2 Ebenen\n\n## Befund\nKein Erguss. Bänder intakt.\n\n## Ergebnis\nRegelrechte Darstellung des Kniegelenkes."
LLM["antwort"], LLM["prompts"] = NEU1, []
app, tb = neue_app()
stati = diktat(app, chirp="Knie rechts Erguss nein Bänder intakt")
check("Leeres Feld → neuer Befund, Statuszeile „Neuer Befund“", "Kniegelenk rechts" in app.result_text.text
      and len(LLM["prompts"]) == 1 and "Neuer Befund · Aufnahme läuft" in stati[0], f"{stati} {app.result_text.text[:60]!r}")
erster = app.result_text.text
check("… erster und letzter KaiScribe-Stand gemerkt", app._stand_erst == erster and app._stand_ks == erster)

# 2e. Zwei Ergänzungen, dann Reset → erster Vorschlag; Strg+Z → Stand davor
LLM["antwort"] = None
KORR["t"] = "Kleiner Gelenkerguss."
diktat(app, chirp="kleiner Gelenkerguss")
KORR["t"] = "Meniskusverkalkung medial."
diktat(app, chirp="Meniskusverkalkung medial")
nach2 = app.result_text.text
check("Zwei Ergänzungen: beide im Befundteil, Titel und erster Text bleiben", "Kleiner Gelenkerguss." in nach2
      and "Meniskusverkalkung medial." in nach2 and nach2.startswith(erster.split("\n\n## Ergebnis")[0]), repr(nach2))
app.befund_zuruecksetzen()
check("Reset → erster Befundvorschlag dieses Falls", app.result_text.text == erster, repr(app.result_text.text))
check("… Strg+Z → Stand mit beiden Ergänzungen", app._rueckgaengig() == "break" and app.result_text.text == nach2)

# 2f. Restructure-Knopf: Peters Ergänzungen als Vorrang, Ergebnis nur zur Kontrolle, Strg+Z zurück
UMB = ("## Kniegelenk rechts\n\n## Befund\nKleiner Gelenkerguss. Meniskusverkalkung medial. Bänder intakt.\n\n"
       "## Ergebnis\n1. Kleiner Gelenkerguss rechts.\n2. Chondrokalzinose medial rechts.")
LLM["antwort"], LLM["prompts"] = UMB, []
app.befund_umbauen()
S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
check("Restructure: KI mit Vorrang-Hinweis (beide Ergänzungen), Titel bleibt, wartet auf EOL (nichts eingefügt)",
      LLM["prompts"] and "„Kleiner Gelenkerguss.“" in LLM["prompts"][0] and "„Meniskusverkalkung medial.“" in LLM["prompts"][0]
      and app.result_text.text.startswith("## Kniegelenk rechts in 2 Ebenen\n") and "Chondrokalzinose" in app.result_text.text
      and app._status_raw == "KONTROLLE" and S.AUFZ.tasten == [], repr(app.result_text.text[:120]))
umgebaut = app.result_text.text
check("… danach ist der umgebaute Text der KaiScribe-Stand, Strg+Z holt den Stand davor",
      app._stand_ks == umgebaut and app._rueckgaengig() == "break" and app.result_text.text == nach2)
app._rueckgaengig()
LLM["prompts"] = []
app.befund_umbauen()
S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
check("Restructure ohne neue Änderung → nichts umgebaut, kein KI-Aufruf", not LLM["prompts"]
      and app.result_text.text == umgebaut, repr(app.result_text.text[:80]))

# 2g. Clear all: Feld leer, Fall bleibt, nächstes Diktat = neuer Befund; Strg+Z holt den Befund
app.befund_leeren()
check("Clear all: Befundfeld und Diktat leer, Strg+Z-Stand gemerkt", app.result_text.text == ""
      and app.transcript_text.text == "" and app._rueck == umgebaut)
LLM["antwort"], LLM["prompts"] = NEU1, []
stati = diktat(app, chirp="Knie rechts kleiner Erguss")
check("… nächstes Diktat = neuer Befund (aus dem neuen Diktat allein)", "Kniegelenk rechts" in app.result_text.text
      and len(LLM["prompts"]) == 1 and "Neuer Befund" in stati[0] and "Meniskus" not in LLM["prompts"][0],
      f"{stati} {len(LLM['prompts'])} {app.result_text.text[:80]!r}")
check("… Reset holt weiterhin den ersten Vorschlag des Falls", app._stand_erst == erster)

# 2h. F1/F9 Neu: alles leer, Stände verworfen
app.reset_dictation()
check("F1 Neu: Feld leer, Reset-Stand und Strg+Z verworfen", app.result_text.text == "" and app._stand_erst is None
      and app._rueck is None and app._stand_ks is None)

# 2i. SpeechMike-INS ohne neue Aufnahme baut einen stehenden Befund nicht still neu
LLM["antwort"], LLM["prompts"] = NEU1, []
app, tb = neue_app()
diktat(app, chirp="Knie rechts kleiner Erguss")
LLM["prompts"] = []
vor_ins = app.result_text.text
app.sm_ins()
S.pump(app, lambda: False, 0.3)
check("Zweites INS (nichts geändert) → kein neuer Befund, Hinweis", not LLM["prompts"] and app.result_text.text == vor_ins
      and "steht schon" in getattr(app, "_letzter_hinweis", ""), getattr(app, "_letzter_hinweis", ""))
app.result_text.text = vor_ins.replace("Bänder intakt.", "Bänder intakt. Getippt.")
app.sm_ins()
S.pump(app, lambda: False, 0.3)
check("INS nach Handänderung rechts → nicht überschrieben, Hinweis auf Restructure", not LLM["prompts"]
      and "Getippt." in app.result_text.text and "Restructure" in getattr(app, "_letzter_hinweis", ""))

# 2j. IB-Lab-Gerüst + Diktat: Gerüst bleibt beim Record stehen, der Befund kommt mit den IB-Lab-Texten (Pipeline),
# das Diktat löscht sie nicht. Danach: weiteres Diktat = Ergänzung.
GER = "## Kniegelenk links in 2 Ebenen\n\n## Befund\nKOALA-Text Gelenkspalt medial 3,1 mm.\n\n## Ergebnis\nKOALA-Ergebnis."
app, tb = neue_app(GER)
app._ibl_geruest_text = GER
app._stand_ks = app._stand_erst = GER
app._stand_erst_geruest = True
app._cas = type("A", (), {"nr": "20261120901", "leistungen": None, "kontext": None, "ibl": None, "auftrag_id": "x"})()
app._cas_aufnahmen, app._cas_hinweise = [], []
app._cas_hinweise_zeigen = lambda h: None
app._ibl_befund_leeren = lambda: None
app._ibl_nach_lauf = lambda e: None
app._nachvollzug_merken = lambda *a: None
app._lauf_protokollieren = lambda *a, **k: None
app._ibl_fuer_lauf = lambda: None
app._cas_hinweis_fuer_lauf = lambda: None
GER_BEFUND = GER.replace("3,1 mm.", "3,1 mm. Kleiner Erguss.").replace("KOALA-Ergebnis.", "1. KOALA-Ergebnis.\n2. Kleiner Erguss.")
LLM["antwort"], LLM["prompts"] = GER_BEFUND, []
seen = {}
mod_rec = app.result_text


def beobachten():
    seen["beim_record"] = app.result_text.text
    return False


mod.speech_client = S.FakeSpeechClient(S.streaming_stub())
mod._chirp3_worker = lambda pcm, sr, loc, token: "Knie links kleiner Erguss"
app.sm_record()
beobachten()
st0 = app.status_badge.cfg.get("text", "")
S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
app.sm_ins()
S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
app._aufnahme_stoppen()
check("IB-Lab-Gerüst: beim Record bleibt das Gerüst sichtbar (nicht gelöscht), Statuszeile „Neuer Befund (IB-Lab-Gerüst)“",
      seen["beim_record"] == GER and "IB-Lab-Gerüst" in st0, f"{st0} / {seen['beim_record'][:40]!r}")
check("… INS: Befund aus Diktat + Gerüst, KOALA-Text bleibt im passenden Befund",
      app.result_text.text == GER_BEFUND and len(LLM["prompts"]) == 1, repr(app.result_text.text))
check("… Reset-Stand ist jetzt der erste Befund (nicht mehr das Gerüst)", app._stand_erst == GER_BEFUND
      and not app._stand_erst_geruest)
LLM["antwort"] = None
KORR["t"] = "Baker-Zyste."
diktat(app, chirp="Baker-Zyste")
check("… nächstes Diktat ergänzt den Befund, KOALA-Text bleibt", "KOALA-Text Gelenkspalt medial 3,1 mm." in app.result_text.text
      and "Baker-Zyste." in app.result_text.text.split("## Ergebnis")[0], repr(app.result_text.text))

# 2k. Fehler während „Befund wird geladen“: das Gerüst kommt zurück statt des Platzhalters
app, tb = neue_app(GER)
app._ibl_geruest_text = GER
LLM["antwort"] = None
mod._llm_aufruf = lambda p: (_ for _ in ()).throw(RuntimeError("KI weg"))
diktat(app, chirp="Knie links kleiner Erguss")
check("Fehler bei der Befund-KI: Platzhalter verschwindet, Gerüst steht wieder da", app.result_text.text == GER,
      repr(app.result_text.text))
mod._llm_aufruf = llm

src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("Knöpfe Clear all / Reset / Restructure im BEFUND-Kopf, Strg+Z am Befundfeld",
      'text="Clear all"' in src and 'text="Reset"' in src and 'text="Restructure"' in src and '"<Control-z>"' in src)
check("SpeechMike-Belegung unverändert (keine neue Taste für die Knöpfe)",
      "befund_leeren" not in (ROOT / "source_code" / "speechmike.py").read_text(encoding="utf-8"))

print("FAILS:", fails)
sys.exit(1 if fails else 0)
