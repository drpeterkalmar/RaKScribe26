"""Gate v3.8.0 (SpeechMike, Peter 11.10., Nachtrag 1–4): echter EXE-Ablauf aus RaKScribe.py mit Attrappen statt
Windows/Tk/Mikrofon/Google. Tasten gehen über DENSELBEN Weg wie vom Gerät: HID-Bericht → speechmike.Dekodierer →
on_taste → after(0) → speechmike_taste. Geprüft:
  Record→Pause ⇒ nur reparierter Text links (chirp_3 auf dem Abschnitt + Fehlhör-Liste), kein Befund, nichts eingefügt;
  Weiter → INS ⇒ Befund aus der GANZEN Aufnahme rechts, nichts eingefügt/kopiert; von Hand ändern → EOL ⇒ genau der
  geänderte Text kopiert + per Strg+V ins zuletzt aktive Fremdfenster, alles leer; EOL während Aufnahme/Verarbeitung/
  ohne Befund ⇒ nichts; Nachdiktat; „Nur Text“ (INS ⇒ korrigierter Text ohne Überschriften); F1/F2; F10 in der Pause;
  F10-Ablauf mit automatischem Einfügen bleibt (EOL schickt danach nicht doppelt).
Synthetische Diktate, keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_speechmike_ablauf.py"""
import pathlib, sys, threading, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: False  # F10-Fälle: ein Fremdfenster (RIS) ist vorne
sm, fz, js = mod._sm, mod._fz, mod._js
NORMAL = "Kniegelenk rechts in 2 Ebenen unauffällig."
CHIRP = {"aufrufe": [], "tor": None}


def chirp(pcm, sr, loc, token):
    """Antwort je Aufruf-Nummer (1. Aufruf = Reparatur bei der Pause bzw. Endtext, wenn es keine Pause gab)."""
    CHIRP["aufrufe"].append(len(pcm))
    if CHIRP["tor"] is not None:
        CHIRP["tor"].wait(5)
    a = CHIRP["antworten"]
    return a[min(len(CHIRP["aufrufe"]), len(a)) - 1]


mod._chirp3_worker = chirp
LLM = {"prompts": []}


def llm(prompt):
    LLM["prompts"].append(prompt)
    return "## Kniegelenk rechts\n\n## Befund\nKleiner Gelenkerguss.\n\n## Ergebnis\nKleiner Gelenkerguss."


mod._llm_aufruf = llm
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


class FakeFenster:
    """user32-Attrappe: 1 = RaKScribe selbst, 42 = SpeechMagic, 7 = Taskleiste."""
    def __init__(self, vorne=42):
        self.vorne, self.aktiviert, self.klappt = vorne, [], True
        self.fenster = {1: (4711, "RaKScribe 3.8.0", "TkTopLevel"), 42: (999, "SpeechMagic – Befund", "SMWin"),
                        7: (555, "", "Shell_TrayWnd")}

    def vordergrund(self):
        return self.vorne

    def pid(self, h):
        return self.fenster[h][0]

    def titel(self, h):
        return self.fenster[h][1]

    def klasse(self, h):
        return self.fenster[h][2]

    def gueltig(self, h):
        return h in self.fenster

    def aktivieren(self, h):
        self.aktiviert.append(h)
        if self.klappt:
            self.vorne = h
        return self.klappt


class Var:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


ZEIT = [0.0]


def druecke(app, taste):
    """Taste wie vom Gerät: Druck- und Loslass-Bericht durch den echten Dekodierer."""
    bit = dict(sm.TASTEN)[taste]
    ZEIT[0] += 1.0
    app._speechmike.einspeisen([0x80, 0, 0, 0, 0, 0, 0, bit & 0xFF, bit >> 8], ZEIT[0])
    app._speechmike.einspeisen([0x80, 0, 0, 0, 0, 0, 0, 0, 0], ZEIT[0] + 0.1)
    S.pump(app)


def neue_app(vorne=42, antworten=(NORMAL,)):
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
    S.CLIPBOARD.gesperrt = False
    S.CLIPBOARD.data = {13: "ALTER INHALT"}
    CHIRP.update(aufrufe=[], tor=None, antworten=list(antworten))
    LLM["prompts"].clear()
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub(antworten=[("Knie", False), ("Knie rechts", True)] * 3))
    app = S.baue_app(mod)
    app._speechmike = sm.SpeechMikeLeser(on_taste=lambda t, g, roh: app.after(0, app.speechmike_taste, t, g, roh),
                                         log=lambda *a: None)
    app.repariert_label = S.FakeWidget()
    app.nur_text_var = Var(False)
    api = FakeFenster(vorne)
    app._fensterziel = fz.Fensterziel(api, eigene_pid=4711)
    app._fensterziel.merken()        # SpeechMagic war vorne …
    api.vorne = 1                    # … dann wechselt Peter zu RaKScribe
    app._fensterziel.merken()
    app._api = api
    return app


def audio(app, mehr=12):
    n0 = len(app._aufnahme.puffer)
    S.pump(app, lambda: len(app._aufnahme.puffer) >= n0 + mehr)


def bis_ruhe(app, timeout=8):
    ok = S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)
    S.pump(app, lambda: False, 0.4)
    return ok


def led(app):
    return app._speechmike.led_soll


# 1. Record → Pause: nur reparierter Text links, kein Befund, nichts eingefügt
app = neue_app(antworten=["Kniegelenk rechts pinnatus Sehne", NORMAL])
druecke(app, "RECORD")
check("Record startet die Aufnahme, LED rot", app._job.zustand == "RECORDING" and app.is_recording and led(app) == "aufnahme",
      f"{app._job.zustand} / {led(app)}")
S.pump(app, lambda: "Knie rechts" in app.transcript_text.text)
audio(app)
druecke(app, "RECORD")
n_abschnitt = 1600 * len(app._aufnahme.puffer)
check("Record in der Aufnahme → Pause, LED rot blinkend, Aufnahme bleibt offen",
      app._job.zustand == "PAUSED" and app._status_raw == "PAUSED" and led(app) == "pause" and app.is_recording,
      f"{app._job.zustand} / {app._status_raw} / {led(app)}")
S.pump(app, lambda: app._abschnitte and app._abschnitte[0])
check("Pause repariert sofort den Abschnitt (chirp_3 auf genau diesem Audio)",
      CHIRP["aufrufe"] and CHIRP["aufrufe"][0] == n_abschnitt, f"{CHIRP['aufrufe']} vs {n_abschnitt}")
check("… mit Fehlhör-Liste („pinnatus Sehne“ → „Supraspinatussehne“), links angezeigt, als repariert markiert",
      app.transcript_text.text == "Kniegelenk rechts Supraspinatussehne"
      and "repariert" in app.repariert_label.cfg.get("text", ""), repr(app.transcript_text.text))
check("Pause: KEIN Befund, nichts kopiert, kein Strg+V", app.result_text.text == "" and S.AUFZ.tasten == []
      and S.CLIPBOARD.data.get(13) == "ALTER INHALT")
n_pause = len(app._aufnahme.puffer)
time.sleep(0.2); S.pump(app)
check("in der Pause wird nichts aufgenommen", len(app._aufnahme.puffer) == n_pause)
druecke(app, "EOL")
check("EOL in der Pause → nichts gesendet, Hinweis „Erst INS …“", app._job.zustand == "PAUSED" and S.AUFZ.tasten == []
      and getattr(app, "_letzter_hinweis", "") == "Erst INS, Befund prüfen, dann EOL")

# 2. Weiter → INS: Befund aus der GANZEN Aufnahme rechts, nichts eingefügt
druecke(app, "RECORD")
check("Record in der Pause → weiter (gleiche Aufnahme, gleicher Lauf), LED rot",
      app._job.zustand == "RECORDING" and led(app) == "aufnahme" and app._aufnahme.abschnitt == 1)
S.pump(app, lambda: app.transcript_text.text.startswith("Kniegelenk rechts Supraspinatussehne Knie"))
check("Anzeige: reparierter Abschnitt + Live-Text des neuen Abschnitts",
      app.transcript_text.text.startswith("Kniegelenk rechts Supraspinatussehne Knie"), repr(app.transcript_text.text))
audio(app)
druecke(app, "EOL")
check("EOL während der Aufnahme → nichts gesendet, Aufnahme läuft weiter", app._job.zustand == "RECORDING"
      and S.AUFZ.tasten == [] and app.result_text.text == "")
CHIRP["tor"] = threading.Event()  # Endtext kurz aufhalten, um „Befund wird erstellt“ zu sehen
druecke(app, "INS")
check("INS → Aufnahme beendet, Befund wird erstellt, LED gelb", app._job.zustand == "PROCESSING" and not app.is_recording
      and led(app) == "verarbeitung", f"{app._job.zustand} / {led(app)}")
CHIRP["tor"].set()
bis_ruhe(app)
CHIRP["tor"] = None
check("chirp_3 für den Endtext über die GANZE Aufnahme (beide Abschnitte)",
      CHIRP["aufrufe"][-1] == 1600 * len(app._aufnahme.puffer) > n_abschnitt, str(CHIRP["aufrufe"]))
check("Befund rechts (Normalbefund-Bypass), Status „Befund prüfen“, LED grün",
      app.result_text.text.startswith("## Kniegelenk") and app._status_raw == "KONTROLLE" and led(app) == "befund_bereit"
      and app._job.zustand == "READY", f"{app.result_text.text[:40]!r} / {app._status_raw} / {led(app)}")
check("INS: NICHTS eingefügt und nichts kopiert", S.AUFZ.tasten == [] and S.CLIPBOARD.data.get(13) == "ALTER INHALT",
      str(S.AUFZ.tasten))
druecke(app, "INS")
check("INS in Ruhe mit Diktat → Befund erneut aus dem Diktat-Feld (nichts eingefügt)", bis_ruhe(app)
      and app._status_raw == "KONTROLLE" and S.AUFZ.tasten == [])

# 3. von Hand ändern → EOL: genau der geänderte Text, ins zuletzt aktive Fremdfenster, danach alles leer
GEAENDERT = app.result_text.text + "\nVon Hand ergänzt."
app.result_text.text = GEAENDERT
druecke(app, "EOL")
S.pump(app, lambda: S.AUFZ.tasten, 2)
check("EOL: genau der sichtbare, geänderte Befund in der Zwischenablage", S.CLIPBOARD.data.get(13) == GEAENDERT.strip(),
      repr(S.CLIPBOARD.data.get(13))[:80])
check("… SpeechMagic-Fenster aktiviert und genau einmal Strg+V", app._api.aktiviert == [42] and S.AUFZ.tasten == ["ctrl+v"],
      f"{app._api.aktiviert} / {S.AUFZ.tasten}")
check("… danach alles leer, bereit, LED aus", app.transcript_text.text == "" and app.result_text.text == ""
      and app._job.zustand == "READY" and led(app) == "aus" and app._basis == "" and not app._befund_wartet)
druecke(app, "EOL")
check("EOL ohne Befund → nichts (kein zweites Strg+V), Hinweis", S.AUFZ.tasten == ["ctrl+v"]
      and app._letzter_hinweis == "Erst INS, Befund prüfen, dann EOL")

# 4. Fensterziel: Aktivieren scheitert → nur kopieren + Hinweis; Fremdfenster vorne → direkt dorthin
for fall in ("scheitert", "fremd_vorne", "keins"):
    app = neue_app()
    druecke(app, "RECORD"); audio(app); druecke(app, "INS"); bis_ruhe(app)
    if fall == "scheitert":
        app._api.klappt = False
    elif fall == "fremd_vorne":
        app._api.vorne = 42
    else:
        app._fensterziel.letztes = None
    druecke(app, "EOL")
    S.pump(app, lambda: False, 0.9)
    kopiert = S.CLIPBOARD.data.get(13, "").startswith("## Kniegelenk")
    if fall == "fremd_vorne":
        check("Fremdfenster vorne → Strg+V dorthin, ohne Umschalten", kopiert and S.AUFZ.tasten == ["ctrl+v"]
              and app._api.aktiviert == [], f"{S.AUFZ.tasten} / {app._api.aktiviert}")
    else:
        check(f"Fensterziel {fall} → nur kopiert + Hinweis, KEIN Strg+V ins falsche Fenster", kopiert and S.AUFZ.tasten == []
              and app._letzter_hinweis.startswith("Befund kopiert"), f"{S.AUFZ.tasten} / {app._letzter_hinweis}")

# 5. Während der Verarbeitung: INS, EOL, Record → nichts (Record: Hinweis)
app = neue_app()
CHIRP["tor"] = threading.Event()
druecke(app, "RECORD"); audio(app); druecke(app, "INS")
S.pump(app, lambda: CHIRP["aufrufe"])
druecke(app, "INS"); druecke(app, "EOL"); druecke(app, "RECORD")
check("INS/EOL/Record während „Befund wird erstellt“ → ignoriert", app._job.zustand == "PROCESSING" and not app.is_recording
      and S.AUFZ.tasten == [] and app._letzter_hinweis == "Befund wird erstellt – bitte kurz warten")
CHIRP["tor"].set()
bis_ruhe(app)
check("… danach steht der Befund zur Kontrolle (nichts eingefügt)", app._status_raw == "KONTROLLE" and S.AUFZ.tasten == [])

# 6. Nachdiktat: Record nach INS hängt an, nächstes INS = neuer Befund aus dem Gesamtdiktat
ALT = app.result_text.text
CHIRP["antworten"] = ["Zusätzlich kleiner Gelenkerguss."]
druecke(app, "RECORD")
check("Record nach INS: bisheriges Diktat bleibt links, alter Befund bleibt rechts (bis zum nächsten INS)",
      app._job.zustand == "RECORDING" and app._basis == NORMAL and app.transcript_text.text.startswith(NORMAL)
      and app.result_text.text == ALT, repr(app.transcript_text.text))
audio(app); druecke(app, "INS"); bis_ruhe(app)
check("nächstes INS: Befund aus dem Gesamtdiktat (bisher + neu), nichts eingefügt",
      LLM["prompts"] and NORMAL in LLM["prompts"][-1] and "Zusätzlich kleiner Gelenkerguss." in LLM["prompts"][-1]
      and "Gelenkerguss" in app.result_text.text and app.transcript_text.text == NORMAL + " Zusätzlich kleiner Gelenkerguss."
      and S.AUFZ.tasten == [], repr(app.transcript_text.text))

# 6b. Cursor im Befund + Record (Nachdiktat) → INS: NUR das neu Diktierte an der Cursor-Stelle (v3.5.0-Logik)
app = neue_app()
druecke(app, "RECORD"); audio(app); druecke(app, "INS"); bis_ruhe(app)
B = app.result_text.text
mod._korr.korrigieren = lambda t, key, block="", log=None: t
app._einfuege_ziel_ermitteln = lambda: (len(B), len(B))  # Cursor am Befund-Ende (wie Klick + Fokus im Befund)
CHIRP["antworten"] = ["Zusätzlich kleiner Gelenkerguss."]
druecke(app, "RECORD")
check("Cursor im Befund: Nachdiktat startet, links bleibt das bisherige Diktat", app._job.zustand == "RECORDING"
      and app._basis == NORMAL and app._einfuegen_ziel == (len(B), len(B)))
audio(app); druecke(app, "INS"); bis_ruhe(app)
neu = app.result_text.text[len(B):]
check("INS: nur das NEU Diktierte an der Cursor-Stelle, alter Befund bleibt, nichts eingefügt",
      app.result_text.text.startswith(B) and "Zusätzlich kleiner Gelenkerguss." in neu and NORMAL not in neu
      and S.AUFZ.tasten == [] and app._status_raw == "KONTROLLE", repr(neu))
check("… links das Gesamtdiktat (bisher + neu)", app.transcript_text.text == NORMAL + " Zusätzlich kleiner Gelenkerguss.",
      repr(app.transcript_text.text))
del app._einfuege_ziel_ermitteln

# 7. „Nur Text“ (Nachtrag 4): INS ⇒ korrigierter Text ohne Überschriften, EOL ⇒ genau dieser Text
app = neue_app(antworten=["kniegelenk rechts kleiner erguss"])
mod._korr.korrigieren = lambda t, key, block="", log=None: "Kniegelenk rechts: kleiner Erguss."
druecke(app, "F2")
check("F2 schaltet „Nur Text“ ein (Hinweis)", app.nur_text_var.get() is True and app._letzter_hinweis == "Nur Text: an")
druecke(app, "RECORD"); audio(app); druecke(app, "RECORD")
S.pump(app, lambda: app._abschnitte and app._abschnitte[0])
check("Nur Text, Pause: links repariert, rechts nichts", app.result_text.text == "" and app._job.zustand == "PAUSED")
druecke(app, "INS"); bis_ruhe(app)
check("Nur Text, INS: rechts der korrigierte Fließtext ohne Überschriften, nichts eingefügt",
      app.result_text.text == "Kniegelenk rechts: kleiner Erguss." and "##" not in app.result_text.text
      and S.AUFZ.tasten == [] and app._status_raw == "KONTROLLE", repr(app.result_text.text))
druecke(app, "F2")
check("F2 mit fertigem Ergebnis: Text bleibt unverändert (wirkt erst beim nächsten INS)",
      app.nur_text_var.get() is False and app.result_text.text == "Kniegelenk rechts: kleiner Erguss.")
app.result_text.text = "Kniegelenk rechts: kleiner Erguss, Rezessus frei."
druecke(app, "EOL")
S.pump(app, lambda: S.AUFZ.tasten, 2)
check("Nur Text, EOL: genau der sichtbare Text weitergeschickt, danach leer",
      S.CLIPBOARD.data.get(13) == "Kniegelenk rechts: kleiner Erguss, Rezessus frei." and S.AUFZ.tasten == ["ctrl+v"]
      and app.result_text.text == "" and app.transcript_text.text == "")

# 8. F1 = Neu (auch in der Pause), F10 in der Pause = Stopp mit Einfügen wie heute
app = neue_app()
druecke(app, "RECORD"); audio(app); druecke(app, "RECORD")
druecke(app, "F1")
time.sleep(0.2); S.pump(app)
check("F1 in der Pause → Aufnahme verworfen, alles leer, bereit, LED aus", app._job.zustand == "READY"
      and not app.is_recording and app.transcript_text.text == "" and led(app) == "aus" and S.AUFZ.tasten == [])
app = neue_app()
druecke(app, "RECORD"); audio(app); druecke(app, "RECORD")
app.toggle_recording()  # F10
bis_ruhe(app)
S.pump(app, lambda: S.AUFZ.tasten, 2)
check("F10 in der Pause → Stopp, Befund + automatisch eingefügt (F10 wie heute)",
      app.result_text.text.startswith("## Kniegelenk") and S.AUFZ.tasten == ["ctrl+v"] and app._status_raw == "COPIED")
druecke(app, "EOL")
check("EOL nach F10-Einfügen: nicht doppelt einfügen, nur Felder leeren", S.AUFZ.tasten == ["ctrl+v"]
      and app.result_text.text == "" and "schon eingefügt" in app._letzter_hinweis)
druecke(app, "RECORD")
check("Record nach F10-Einfügen: frisches Diktat (kein Nachdiktat)", app._basis == "" and app._job.zustand == "RECORDING")
app.reset_dictation()

# 9. Play/Spulen/INSTR/F3/F4/Command: nur Protokoll; Loslassen ändert nichts
app = neue_app()
for t in ("PLAY", "FF", "REW", "INSTR", "F3", "F4", "COMMAND"):
    druecke(app, t)
check("unbelegte Tasten ändern nichts", app._job.zustand == "READY" and app.transcript_text.text == "" and S.AUFZ.tasten == [])
check("… stehen im Diagnose-Verlauf", sum("gedrückt" in z for z in app._speechmike.verlauf) == 7, str(list(app._speechmike.verlauf)))
druecke(app, "STOP")
check("Stop in Ruhe → nichts", app._job.zustand == "READY")
druecke(app, "RECORD"); audio(app); druecke(app, "STOP")
check("Stop während der Aufnahme → Pause", app._job.zustand == "PAUSED")
app.reset_dictation()

print("\n" + ("✅ SPEECHMIKE-ABLAUF PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
