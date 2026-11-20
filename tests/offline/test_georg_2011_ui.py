"""Gate kaiscribe-georg-2011-n1 – Bedienung (Georg Riegler 20.11.2026, Diktiertag), echter EXE-Ablauf mit Attrappen:
   5   „Nur Text“ bei jedem neuen CAS-Auftrag automatisch aus + deutliche Anzeige, solange an (RH 57)
  23   Fall heute schon diktiert (Lauf-Datei) → Warnung + Bestätigung, „Nein“ gibt den Auftrag zurück
  39   „Aufnahme starten“ löscht vorhandenen Text nie ohne Rückfrage, „↶ Rückgängig“ holt den letzten Stand (RH 7),
       Lauf-Sicherung auch im Nur-Text-Weg (RH 7: keine Lauf-Datei)
   3   zurückgestellter Befund: Anzeige im Band (Ablage macht die Brücke)
Synthetische Texte, keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_georg_2011_ui.py"""
import json, os, pathlib, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: False
cas, js = mod._cas, mod._js
mod._chirp3_worker = lambda pcm, sr, loc, token: "Kniegelenk rechts in 2 Ebenen unauffällig."
mod._llm_aufruf = lambda p: "## Kniegelenk rechts\n\n## Befund\nKleiner Gelenkerguss.\n\n## Ergebnis\nKleiner Gelenkerguss."
mod._korr.korrigieren = lambda t, key, block="", log=None: t
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


ORDNER = tempfile.mkdtemp(prefix="rks_georg_")
LAEUFE = os.path.join(tempfile.mkdtemp(prefix="rks_laeufe_"), "laeufe")
mod.CFG.lauf_ordner = LAEUFE
FRAGEN = []


def frage(antwort):
    def f(titel="", text="", **k):
        FRAGEN.append((titel, text))
        return antwort
    mod.messagebox.askyesno = f


def ablegen(nr, aid, **extra):
    d = {"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": "rg", "bruecke_pid": 4242, "zeit": time.time(),
         "zeit_text": "", "testbefund": False}
    d.update(extra)
    with open(os.path.join(ORDNER, cas.AUFTRAG), "w", encoding="utf-8") as f:
        json.dump(d, f)


def antwort(aid):
    try:
        with open(os.path.join(ORDNER, f"cas_antwort_{aid}.json"), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


class Var:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


class W(S.FakeWidget):
    def pack(self, *a, **k):
        pass

    pack_forget = pack


def neue_app():
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub())
    app = S.baue_app(mod)
    app.nur_text_var, app.nur_text_switch, app.rueckgaengig_btn = Var(False), W(), W()
    app.rueckgaengig_btn.configure(state="disabled")
    app.cas_band, app.cas_label, app.main_container = W(), W(), W()
    app._letzter_stand = None
    app._cas, app._cas_aufnahmen, app._cas_test = None, [], False
    app._cas_kanal = cas.Kanal(ORDNER, pid=777, version="3.20.0", prozess_lebt=lambda pid: True)
    app._fensterziel = mod._fz.Fensterziel(None)
    app.destroy = lambda: None
    return app


def bis_ruhe(app, timeout=8):
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)
    S.pump(app, lambda: False, 0.3)


# ───────────────────────────── 5: „Nur Text“ ─────────────────────────────
app = neue_app()
app.nur_text_var.set(True)
app._nur_text_umgeschaltet()
check("5: solange „Nur Text“ an ist, steht es deutlich am Schalter (Bernstein)",
      app.nur_text_switch.cget("text") == app.NUR_TEXT_AN and app.nur_text_switch.cget("text_color") == mod.WARN_AMBER,
      (app.nur_text_switch.cget("text"), app.nur_text_switch.cget("text_color")))
ablegen("20261120057", "n57")
app._cas_einmal()
S.pump(app, lambda: False, 0.5)
check("5: neuer CAS-Auftrag → „Nur Text“ automatisch aus, Schalter wieder normal, Hinweis",
      app._cas is not None and not app.nur_text_aktiv() and app.nur_text_switch.cget("text") == "Nur Text"
      and "Nur Text" in getattr(app, "_letzter_hinweis", ""), (app.nur_text_aktiv(), getattr(app, "_letzter_hinweis", "")))
check("5: Einstellung gespeichert (übersteht Neustart)", mod.einstellung_lesen("nur_text", True) is False)

# ───────────────────────────── 39: Aufnahme starten mit Text ─────────────────────────────
# Merge 3.20.0: steht rechts ein Befund, ergänzt das Diktat ihn (3.19.16) – nichts geht verloren, also keine Rückfrage
app.transcript_text.insert("1.0", "Kniegelenk rechts unauffällig.")
app.result_text.insert("1.0", "## Kniegelenk rechts in 2 Ebenen\n\n## Befund\nWichtig.\n\n## Ergebnis\nX.")
befund = app.result_text.text
n = len(FRAGEN)
frage(False)
app.toggle_recording()
check("39: Befund rechts → Start ohne Rückfrage (Ergänzung 3.19.16), Befund bleibt Zeichen für Zeichen",
      len(FRAGEN) == n and app._job.zustand == "RECORDING" and app.result_text.text == befund,
      (FRAGEN[n:], app._job.zustand, app.result_text.text[:40]))
S.pump(app, lambda: app._aufnahme is not None and len(app._aufnahme.puffer) >= 5)
app.reset_dictation()
S.pump(app, lambda: False, 0.3)
app.transcript_text.delete("1.0", "end")
app.result_text.delete("1.0", "end")
app._rueck = None

# nur links Diktat-Text, rechts leer: der Start würde ihn verwerfen → Rückfrage
app.transcript_text.insert("1.0", "Kniegelenk rechts unauffällig, Erguss im Recessus suprapatellaris.")
vorher = (app.transcript_text.text, app.result_text.text)
frage(False)
app.toggle_recording()
check("39: Text da, Start → Rückfrage; „Nein“ → keine Aufnahme, Text bleibt",
      FRAGEN and FRAGEN[-1][0] == "Aufnahme starten" and app._job.zustand == "READY"
      and (app.transcript_text.text, app.result_text.text) == vorher, (FRAGEN, app._job.zustand))
frage(True)
app.toggle_recording()
check("39: „Ja“ → Aufnahme läuft, Diktatfeld leer, Rückgängig-Knopf aktiv",
      app._job.zustand == "RECORDING" and app.transcript_text.text == "" and app.rueckgaengig_btn.cget("state") == "normal",
      (app._job.zustand, app.transcript_text.text))
check("39: Rückgängig während der Aufnahme wirkungslos", app.rueckgaengig() is False)
S.pump(app, lambda: app._aufnahme is not None and len(app._aufnahme.puffer) >= 5)
app.reset_dictation()   # F9: Aufnahme verwerfen
S.pump(app, lambda: False, 0.3)
check("39: nach F9 holt „↶ Rückgängig“ den Stand vor dem Start zurück",
      app.rueckgaengig() is True and (app.transcript_text.text, app.result_text.text) == vorher
      and app.rueckgaengig_btn.cget("state") == "disabled", (app.transcript_text.text[:40], app.result_text.text[:40]))
n = len(FRAGEN)
app._gesendet = True
frage(False)
app.toggle_recording()
check("39: schon übergebener Text → keine Rückfrage (normaler Ablauf)", len(FRAGEN) == n and app._job.zustand == "RECORDING")
app.reset_dictation()
app._gesendet = False

# Lauf-Sicherung im Nur-Text-Weg
app.nur_text_var.set(True)
app._nur_text_umgeschaltet()
frage(True)
app.toggle_recording()
S.pump(app, lambda: app._aufnahme is not None and len(app._aufnahme.puffer) >= 8)
app.toggle_recording()
bis_ruhe(app)
S.pump(app, lambda: os.path.isdir(LAEUFE) and any(n.startswith("20261120057_") for n in os.listdir(LAEUFE)), 3)
laeufe = sorted(os.listdir(LAEUFE)) if os.path.isdir(LAEUFE) else []
check("39 (RH 7): auch der Nur-Text-Lauf schreibt sofort eine Lauf-Datei <Nr>_<Zeit>.json",
      any(n.startswith("20261120057_") for n in laeufe), laeufe)
app.nur_text_var.set(False)
app._nur_text_umgeschaltet()
app._cas_beenden()
app.reset_dictation()

# ───────────────────────────── 23: heute schon diktiert ─────────────────────────────
check("23: heute_diktiert findet die Lauf-Datei von heute, nicht die anderer Nummern/Tage",
      cas.heute_diktiert(LAEUFE, "20261120057") and cas.heute_diktiert(LAEUFE, "20261120058") == []
      and cas.heute_diktiert(LAEUFE, "20261120057", jetzt=lambda: time.time() - 86400 * 2) == []
      and cas.heute_diktiert("aus", "20261120057") == [] and cas.heute_diktiert(LAEUFE + "-fehlt", "1") == [])
FRAGEN.clear()
frage(False)
ablegen("20261120057", "n57b")
app._cas_einmal()
check("23: schon diktiert + „Nein“ → Warnung, Auftrag an die Brücke zurück (abgelehnt, Grund)",
      FRAGEN and FRAGEN[-1][0] == "Bereits diktiert" and "20261120057" in FRAGEN[-1][1] and app._cas is None
      and antwort("n57b").get("status") == "abgelehnt" and antwort("n57b").get("grund") == "bereits diktiert",
      (FRAGEN, antwort("n57b")))
frage(True)
ablegen("20261120057", "n57c")
app._cas_einmal()
check("23: „Ja“ → Auftrag angenommen", app._cas is not None and antwort("n57c").get("status") == "angenommen")
app._cas_beenden()
FRAGEN.clear()
ablegen("20261120059", "n59", zurueckgestellt=True)
app._cas_einmal()
check("23: noch nicht diktierter Fall → keine Warnung", app._cas is not None and not FRAGEN, FRAGEN)

# ───────────────────────────── 3: zurückgestellt ─────────────────────────────
check("3: zurückgestellter Befund steht im Band (Ablage macht die Brücke)",
      app._cas.zurueckgestellt and cas.ZURUECKGESTELLT in app._cas.band_text()
      and cas.ZURUECKGESTELLT in app.cas_label.cget("text"), app._cas.band_text())
a = cas.Auftrag({"auftrag_id": "x", "nr": "1"})
check("3: ohne Feld wie bisher", not a.zurueckgestellt and cas.ZURUECKGESTELLT not in a.band_text())

# ───────────────────────────── 17: Titel robust (RH 67) ─────────────────────────────
roh = "Finger rechts in 2 Ebenen\n\n## Befund\nNormale Form.\n\n## Ergebnis\nX.\n\n\n# Hand links\n## Befund\nY.\n\n## Ergebnis\nZ."
check("17: erste Zeile = Titel, auch ohne „## “ (bzw. „# “) – vor der Übergabe an CAS ergänzt",
      cas.titel_sichern(roh) == roh.replace("Finger rechts", "## Finger rechts").replace("# Hand links", "## Hand links"),
      cas.titel_sichern(roh))
ok = "## Knie\n\n## Befund\nA.\n\n## Ergebnis\nB."
check("17: korrekte Überschriften und Sätze vor „## Befund“ bleiben unverändert",
      cas.titel_sichern(ok) == ok and cas.titel_sichern("Ein Satz.\n## Befund\nA.") == "Ein Satz.\n## Befund\nA.")
app.reset_dictation()
app.transcript_text.insert("1.0", "Kniegelenk rechts: kleiner Gelenkerguss.")
app.befund_aus_text(kontrolle=True)
bis_ruhe(app)
t = app.result_text.text
app.result_text.delete("1.0", "end")
app.result_text.insert("1.0", t.replace("## Kniegelenk rechts", "Kniegelenk rechts", 1))   # von Hand bearbeitet (RH 67)
app._cas_taste("eol")
gesendet = [n for n in os.listdir(ORDNER) if n.endswith(".txt")]
inhalt = open(os.path.join(ORDNER, gesendet[-1]), encoding="utf-8").read() if gesendet else ""
check("17: EOL schickt den Titel mit „## “ an die Brücke", inhalt.startswith("## Kniegelenk rechts\n"), (gesendet, inhalt[:60]))

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
