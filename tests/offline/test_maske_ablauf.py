"""Gate v3.15.0 Mammo-Maske im EXE-Ablauf (exe_stubs: echte RaKScribeApp-Logik ohne Tk-Fenster, Mikrofon, Google).
CAS-Auftrag mit Mammographie-Leistung (+ Mamma-Sono) und Mammo-Vorbefund aus der Datenbank → Maske mit Vorschlägen;
Vorspulen/Rückspulen/F3/F4 über speechmike_taste (gleicher Weg wie das Gerät), Record diktiert ins aktive Feld (ein
Abschnitt je Feld, Mikrofon bleibt offen), INS mit offenen Vorschlägen → Warnung, zweites INS → ohne sie, INS → Befund,
EOL → Datei an die Brücke; Maske geändert nach INS → EOL nicht; F4 = freies Diktat; F9 = Neu; Rückfall ohne Datenbank
(kein Kontext) → Maske ohne Vorbefund; Nicht-Mammo und Menü aus → keine Maske; neuer Auftrag bei Inhalt → abgelehnt;
Spulen ohne Maske wie bisher (nichts). Datenschutz: KI (Korrektur) bekommt nur Peters Diktat, nie den Vorbefund; kein
Befund-Prompt (LLM) beim Masken-Befund. Synthetische Daten.  Aufruf: /usr/bin/python3 tests/offline/test_maske_ablauf.py"""
import json, os, pathlib, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
FAELLE = json.loads((pathlib.Path(__file__).resolve().parent / "maske_faelle.txt").read_text(encoding="utf-8"))
fails = 0
GEHEIM = "VORBEFUND-GEHEIM-0815"
VB_TEXT = FAELLE["zerlegen"][0]["text"].replace("Mastopathie", f"{GEHEIM} Mastopathie")


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: False
cas_mod = mod._cas
CHIRP, KORR, LLM = [], [], []


def chirp(pcm, sr, loc, token):
    return CHIRP.pop(0) if CHIRP else ""


def korr(text, key, block="", log=None):
    KORR.append(text)
    return text.strip().rstrip(".") + "."


mod._chirp3_worker = chirp
mod._korr.korrigieren = korr
mod._llm_aufruf = lambda p: LLM.append(p) or "## X\n\n## Befund\nx\n\n## Ergebnis\nx"
ORDNER = tempfile.mkdtemp(prefix="rks_maske_exe_")


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


class FakeMaskeUI:
    """Statt MaskePanel (Tk): merkt sich, was gezeigt würde."""
    def __init__(self):
        self.sichtbar, self.aufrufe, self.letzt = False, 0, {}
        self.kopf = FakeBand()

    def zeigen(self):
        self.sichtbar = True

    def verstecken(self):
        self.sichtbar = False

    def aktualisieren(self, m, live=None, kopf="", hilfe="", warnung="", gesperrt=False):
        self.aufrufe += 1
        self.kopf.configure(text=kopf)
        self.letzt = {"live": dict(live or {}), "kopf": kopf, "hilfe": hilfe, "warnung": warnung, "gesperrt": gesperrt}


def ablegen(nr, aid):
    with open(os.path.join(ORDNER, cas_mod.AUFTRAG), "w", encoding="utf-8") as f:
        json.dump({"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": "kp", "bruecke_pid": 4242,
                   "zeit": time.time(), "zeit_text": "", "testbefund": False}, f)


def datei(name, d):
    p = os.path.join(ORDNER, name)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def antwort(aid):
    try:
        with open(os.path.join(ORDNER, f"cas_antwort_{aid}.json"), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


L_MAMS = {"kurz": "s-mammo", "text": "Mammographie bds. Screening", "modalitaet": "Röntgen", "vorlage": "mammographie_beidseits",
          "mammo": "screening", "ziffer": 1, "ohne_vorlage": False, "bekannt": True}
L_SONO = {"kurz": "s-sono", "text": "Ultraschall der Mamma o.V.", "modalitaet": "Sono", "vorlage": "mammasonographie_beidseits",
          "ziffer": 2, "ohne_vorlage": False, "bekannt": True}
L_LWS = {"kurz": "x-lws", "text": "LWS", "modalitaet": "Röntgen", "vorlage": "lendenwirbelsäule_in_2_ebenen",
         "ohne_vorlage": False, "bekannt": True}
VB = {"nr": "20241012001", "datum": "2024-06-05", "untersuchung": "Mammographie bds. Screening", "text": VB_TEXT,
      "zeichen": len(VB_TEXT), "gekuerzt": False, "werte": {"acr": "2", "birads": "2"}}


def leistungen(aid, nr, liste):
    datei(f"cas_leistungen_{aid}.json", {"protokoll": 1, "auftrag_id": aid, "nr": nr, "roh": "Datenbank", "leistungen": liste,
                                         "quelle": "CAS-Datenbank"})


def kontext(aid, nr, vb=VB):
    datei(f"cas_kontext_{aid}.json", {"protokoll": 1, "auftrag_id": aid, "nr": nr, "quelle": "CAS-Datenbank", "zuweiser": "",
                                      "info": "", "vorbefund": vb, "zeit": time.time()})


S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
app = S.baue_app(mod)
app._cas, app._cas_aufnahmen, app._cas_test = None, [], False
app._cas_kanal = cas_mod.Kanal(ORDNER, pid=777, version="3.15.0", prozess_lebt=lambda pid: True)
app._fensterziel = mod._fz.Fensterziel(None)
app.cas_label, app.cas_hinweis_label, app.bestaetigung_label = S.FakeWidget(), S.FakeWidget(), S.FakeWidget()
app.cas_band, app.bestaetigung_band, app.main_container = FakeBand(), FakeBand(), None
app.cas_kopf_label, app.vorbefund_knopf = FakeBand(), FakeBand()
app.ibl_label, app.ibl_hinweis_label, app.ibl_zeile, app.ibl_knopf = FakeBand(), FakeBand(), FakeBand(), FakeBand()
app.repariert_label = S.FakeWidget()
app.ibl_var, app.maske_var, app.nach_cas_minimieren_var = Var(True), Var(True), Var(False)
app.diktat_titel = S.FakeWidget()
app._speechmike = None
app.destroy = lambda: None
app._maske_leeren()
app._maske_ui = FakeMaskeUI()
M = mod._mk


def warte(bis, timeout=8):
    return S.pump(app, bis, timeout)


def ruhe(timeout=10):
    warte(lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)
    S.pump(app, lambda: False, 0.2)


def taste(t):
    app.speechmike_taste(t, True, "")
    app.speechmike_taste(t, False, "")
    S.pump(app, lambda: False, 0.05)


def sprechen(sek=0.15):
    t0 = time.time()
    S.pump(app, lambda: time.time() - t0 > sek, sek + 1)


# ───────────── 1. Mammo-Auftrag mit Datenbank: Maske mit Vorbefund ─────────────
ablegen("20261015001", "m1")
app._cas_einmal()
check("Auftrag ohne Leistungen: noch keine Maske", app._maske is None)
leistungen("m1", "20261015001", [L_MAMS, L_SONO])
kontext("m1", "20261015001")
app._cas_einmal()
m = app._maske
check("Mammographie-Leistung → Maske offen und gezeigt, Titel links „MAMMO-MASKE“",
      m is not None and app._maske_an and app._maske_ui.sichtbar and app.diktat_titel.cget("text") == "MAMMO-MASKE")
check("Screening, Sono-Leistung da → 4 Felder, alle mit Vorbefund-Vorschlag vom 05.06.2024",
      m.art == "screening" and m.sono and [f.quelle for f in m.felder] == ["vorbefund"] * 4 and m.datum == "05.06.2024",
      m.zustand())
check("Kopf: Screening · mit Sono · Vorbefund 05.06.2024 (Nr) – 4 von 4 Feldern", "Screening" in app._maske_ui.letzt["kopf"]
      and "Vorbefund 05.06.2024 (20241012001) – 4 von 4 Feldern erkannt" in app._maske_ui.letzt["kopf"], app._maske_ui.letzt)
check("Hilfezeile: aktives Feld + Tasten", app._maske_ui.letzt["hilfe"].startswith("Feld 1/4: Inspektion und Palpation")
      and "Vorspulen/Rückspulen = Feld · F3 = übernehmen" in app._maske_ui.letzt["hilfe"], app._maske_ui.letzt["hilfe"])
taste("FF")
check("Vorspulen → Feld 2 (Mammographie)", m.aktiv == 1 and "Feld 2/4: Mammographie" in app._maske_ui.letzt["hilfe"])
taste("REW")
check("Rückspulen → Feld 1", m.aktiv == 0)
app._maske_tastatur(+1)
app._maske_tastatur(-1)
check("Bild↓/Bild↑ (Fern-Test) springen ebenso", m.aktiv == 0)
app.sm_ins()
S.pump(app, lambda: False, 0.2)
check("INS mit 4 offenen Vorschlägen → kein Befund, Warnung nennt sie, bereit", app.result_text.text == ""
      and "Noch nicht übernommen: Inspektion und Palpation (Vorbefund)" in app._maske_warnung_text()
      and app._job.zustand == "READY", app._maske_warnung_text())
taste("F3")
check("F3 → Inspektion übernommen", m.felder[0].quelle == "uebernommen" and m.felder[0].text == "Unauffällig.")
check("Warnung zeigt nur noch die offenen Felder (Inspektion erledigt)", "Inspektion" not in app._maske_warnung_text()
      and "Mammographie (Vorbefund)" in app._maske_warnung_text(), app._maske_warnung_text())
taste("FF")
CHIRP[:] = ["unverändert", "keine suspekten Herde", "unverändert ACR 2 BIRADS 2"]
app.sm_record()
sprechen()
check("Record → Aufnahme ins Feld Mammographie (Abschnitt angemeldet, Feld noch Vorschlag)",
      app._job.zustand == "RECORDING" and app._maske_lauf and m.felder[1].wartet and m.felder[1].quelle == "vorbefund")
taste("FF")
sprechen()
check("Vorspulen während der Aufnahme: Abschnitt ans Mammographie-Feld, weiter im Sono-Feld (Aufnahme läuft)",
      app._job.zustand == "RECORDING" and m.aktiv == 2 and m.felder[2].wartet, m.zustand())
warte(lambda: not m.felder[1].wartet)
check("… Mammographie „unverändert“ → Vergleichssatz mit 05.06.2024 (ohne KI)",
      M.vorschau(m.felder[1], m).startswith("Verglichen mit 05.06.2024 beidseits unverändert vereinzelte"), M.vorschau(m.felder[1], m))
taste("FF")
sprechen()
app.sm_ins()
ruhe()
r = app.result_text.text
SOLL_ANFANG = ("## Mammographie beidseits – Screening\n\n## Befund\nInspektion und Palpation: Unauffällig.\n\n"
               "Mammographie: Verglichen mit 05.06.2024 beidseits unverändert vereinzelte insuspekte Verkalkungen sowie "
               "Gefäßverkalkungen. Im Übrigen unauffällig strukturierter Drüsenkörper. Cutis und Subcutis unauffällig.\n\n"
               "Sonographie: Keine suspekten Herde.\n\n## Ergebnis\n" + GEHEIM + " Mastopathie mit insuspekten Verkalkungen.\n"
               "ACR: 2\nBIRADS: 2\n\nVerlaufskontrolle bei unverändertem klinischem Befund")
check("INS → Befund aus den Feldern rechts zur Kontrolle (Titel, Labels, Ergebnis, ACR/BIRADS, Screening-Text)",
      r.startswith(SOLL_ANFANG) and app._status_raw == "KONTROLLE" and app._befund_wartet, r)
check("KI (Korrektur) nur fürs frei diktierte Sono-Feld, nie mit dem Vorbefund; kein Befund-Prompt",
      KORR == ["keine suspekten Herde"] and not any(GEHEIM in k for k in KORR) and LLM == [], f"{KORR} / {len(LLM)}")
check("eine Aufnahme für den CAS-Auftrag (WAV)", len(app._cas_aufnahmen) == 1)
app.befund_fertig()
S.pump(app, lambda: False, 0.2)
a1 = antwort("m1")
ergebnis = pathlib.Path(ORDNER, "cas_ergebnis_20261015001.txt")
check("EOL → genau dieser Befund als Datei an die Brücke („fertig“), Maske zu", a1.get("status") == "fertig"
      and ergebnis.read_text(encoding="utf-8") == r and app._maske is None and not app._maske_ui.sichtbar
      and app.diktat_titel.cget("text") == "DIKTAT", a1)

# ───────────── 2. Rückfall ohne Datenbank: kein Kontext → Maske ohne Vorbefund ─────────────
ablegen("20261015002", "m2")
app._cas_einmal()
leistungen("m2", "20261015002", [dict(L_MAMS, mammo=None)])     # alter Weg: ohne Tarif-Kennzeichen, nur Vorlage/Text
app._cas_einmal()
m = app._maske
check("ohne Datenbank: Maske über Vorlage/Text (Screening am Text), ohne Sono-Leistung Sonographie eingeklappt",
      m is not None and m.art == "screening" and not m.sono and not m.felder[2].sichtbar, m and m.zustand())
check("… kein Vorbefund: Mammographie mit Normalbaustein „Mammo 1“ (ohne Vergleich), sonst leer",
      [f.quelle for f in m.felder] == ["leer", "vorlage", "leer", "leer"]
      and m.felder[1].vorschlag.startswith("Kleinfleckig strukturierter Drüsenkörper"), m.zustand())
kontext("m2", "20261015002")
app._cas_einmal()
check("Kontext (Vorbefund) kommt später → Vorschläge ergänzt", [f.quelle for f in m.felder] == ["vorbefund", "vorbefund",
      "vorbefund", "vorbefund"] and not m.felder[2].sichtbar, m.zustand())
taste("F4")
check("F4 → Maske aus (freies Diktat, Diktat-Feld wieder da)", not app._maske_an and not app._maske_ui.sichtbar
      and app.diktat_titel.cget("text") == "DIKTAT")
taste("FF")
check("… Spulen ohne gezeigte Maske: nichts", m.aktiv == 0)
taste("F4")
check("F4 → Maske wieder an (Stand bleibt)", app._maske_an and app._maske_ui.sichtbar and m.felder[0].quelle == "vorbefund")
CHIRP[:] = ["unauffällig"]
app.sm_record()
sprechen()
taste("F4")
check("F4 während der Aufnahme → nicht umgeschaltet (Hinweis)", app._maske_an and "erst die Aufnahme" in app._letzter_hinweis)
app.reset_dictation()
S.pump(app, lambda: False, 0.3)
check("F9/F1 (Neu) → Aufnahme verworfen, alle Felder wieder Vorschlag", app._job.zustand == "READY"
      and [f.quelle for f in m.felder] == ["vorbefund"] * 4 and not app._maske_abschnitte, m.zustand())
for i in (0, 1, 3):
    app._maske_knopf(i)
check("Knöpfe „übernehmen“ (Klick) → übernommen", [f.quelle for f in m.felder] == ["uebernommen", "uebernommen",
      "vorbefund", "uebernommen"])
app.sm_ins()
ruhe()
check("INS ohne Sono-Leistung → Befund ohne Sonographie, ohne Warnung", "Sonographie" not in app.result_text.text
      and app.result_text.text.startswith("## Mammographie beidseits – Screening") and app._status_raw == "KONTROLLE",
      app.result_text.text[:300])
app._maske_knopf(2)
check("Klick „＋ zuschalten“ am eingeklappten Sono-Feld → sichtbar, mit Vorbefund-Vorschlag", m.felder[2].sichtbar
      and m.felder[2].offen)
app.befund_fertig()
check("Maske nach INS geändert → EOL schickt nicht (Hinweis)", antwort("m2").get("status") == "angenommen"
      and "Maske seit dem Befund geändert" in app._letzter_hinweis, antwort("m2"))
app.sm_ins()
S.pump(app, lambda: False, 0.2)
check("INS → Warnung (Sonographie offen)", "Sonographie (Vorbefund)" in app._maske_warnung_text(), app._maske_warnung_text())
app.sm_ins()
ruhe()
check("zweites INS ohne Änderung → Befund ohne Sonographie + Hinweis im Band",
      "Sonographie" not in app.result_text.text and any("Nicht im Befund" in h for h in app._cas_hinweise),
      app._cas_hinweise)
ablegen("20261015003", "m3")
app._cas_einmal()
check("neuer Auftrag, während die Maske Inhalt hat → abgelehnt (Patientensicherheit)",
      antwort("m3").get("status") == "abgelehnt" and app._cas.nr == "20261015002")
app.befund_fertig()
S.pump(app, lambda: False, 0.2)
check("EOL → an die Brücke, Maske zu", antwort("m2").get("status") == "fertig" and app._maske is None)

# ───────────── 2b. Abbrechen mit Maske: interner Live-Text weg, Befund rechts bleibt; nächster Auftrag übernimmt nichts still
ablegen("20261015007", "m7")
app._cas_einmal()
leistungen("m7", "20261015007", [L_MAMS, L_SONO])
kontext("m7", "20261015007")
app._cas_einmal()
m = app._maske
CHIRP[:] = ["unverändert"]
app.sm_record()
sprechen()
app.sm_ins()
ruhe()
for i in (1, 2, 3):
    app._maske_knopf(i)
app.sm_ins()
ruhe()
befund_m7 = app.result_text.text
check("Maske mit Aufnahme + Befund (Vorbereitung)", befund_m7.startswith("## Mammographie") and app.transcript_text.text != "",
      repr(app.transcript_text.text[:40]))
app.cas_abbrechen()
check("Abbrechen mit Maske → interner Live-Text im Diktat-Feld weg, Befund rechts bleibt (wie seit 3.10)",
      app.transcript_text.text == "" and app.result_text.text == befund_m7 and app._maske is None)
ablegen("20261015008", "m8")
app._cas_einmal()
leistungen("m8", "20261015008", [L_MAMS])
app._cas_einmal()
check("… nächster Mammo-Auftrag: Maske bereit, nicht gezeigt (Text steht da), Hinweis „F4“",
      app._maske is not None and not app._maske_an and "es steht schon Text da" in app._letzter_hinweis, app._letzter_hinweis)
app.sm_ins()
S.pump(app, lambda: False, 0.2)
check("… INS ohne Maske und ohne Diktat → kein Befund aus fremdem Text (Hinweis „Kein Diktat“)",
      app.result_text.text == befund_m7 and "Kein Diktat" in app._letzter_hinweis, app._letzter_hinweis)
app.reset_dictation()
app.cas_abbrechen()

# ───────────── 3. keine Maske: Röntgen, Menü aus; Spulen wie bisher ─────────────
ablegen("20261015004", "m4")
app._cas_einmal()
leistungen("m4", "20261015004", [L_LWS])
app._cas_einmal()
check("Röntgen-Auftrag → keine Maske", app._maske is None and app.diktat_titel.cget("text") == "DIKTAT")
taste("FF"); taste("F3"); taste("F4")
check("… Vorspulen/F3/F4 ohne Maske: nichts (wie bisher)", app._job.zustand == "READY" and app._maske is None)
app.cas_abbrechen()
app.maske_var.set(False)
ablegen("20261015005", "m5")
app._cas_einmal()
leistungen("m5", "20261015005", [L_MAMS])
app._cas_einmal()
check("Menü „Mammo-Maske“ aus → keine Maske (freies Diktat wie bisher)", app._maske is None)
app.cas_abbrechen()
app.maske_var.set(True)

# ───────────── 4. freies Diktat läuft schon → Maske bereit (F4) statt mitten hinein ─────────────
ablegen("20261015006", "m6")
app._cas_einmal()
app.transcript_text.text = "Mammographie beidseits unauffällig"
leistungen("m6", "20261015006", [L_MAMS])
app._cas_einmal()
check("Text steht schon im Diktat-Feld → Maske offen, aber nicht gezeigt (Hinweis F4)", app._maske is not None
      and not app._maske_an and not app._maske_ui.sichtbar and "F4" in app._letzter_hinweis, app._letzter_hinweis)
app.cas_abbrechen()
check("Abbrechen → Maske zu", app._maske is None)

# ───────────── 5. Tastenbelegung im Protokoll/Konfig ─────────────
check("Konfig: Belegung aus masken.json (FF/REW/F3/F4)", mod.MASKE_TASTEN == {"FF": "naechstes_feld", "REW": "voriges_feld",
      "F3": "uebernehmen", "F4": "maske_umschalten"}, mod.MASKE_TASTEN)
check("eingeübte Tasten unverändert (BELEGUNG)", mod._sm.BELEGUNG == {"RECORD": "record", "INS": "ins", "EOL": "eol",
      "STOP": "stop", "F1": "reset", "F2": "nur_text"})

print("\n" + ("✅ MASKE-ABLAUF PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
