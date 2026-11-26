"""Gate kaiscribe-ergaenzung-ohne-ins-n1 (Peter 26.11.2026, Diktat 20261126060, CASWS10): Dazudiktieren rechts ohne INS.
Peter wörtlich: „Ich setze den Cursor im rechten Fenster an die Stelle, die falsch autobefundet wurde, und will durch
Darüberdiktieren schnell korrigieren, ohne tippen zu müssen.“ Abnahme = genau dieser Ablauf: Cursor/Markierung rechts →
Record → sprechen → Pause ⇒ der Text steht wörtlich RECHTS an der Stelle (ersetzt die Markierung), links wird NICHTS
angehängt, keine Neustrukturierung, kein INS nötig, EOL schließt danach direkt ab. Ohne „Nur Text“ (und mit: gleich).
Weiter-Diktieren hängt dahinter an; INS danach baut nie neu; EOL während der Aufnahme fügt erst ein (zweites EOL schließt
ab); „Erst INS“ nur ohne Befund rechts; offene Ergänzung geht bei Fenster zu / Befund kopieren nicht still verloren;
Strg+Z holt den Stand vor der ganzen Ergänzung. Gemeinsame Regel befundfeld.eol_aktion ≡ befundfeld.ts eolAktion
(Fälle snapshots/ergaenzung_eol_faelle.txt, Web: pipeline_test.mjs). Echter EXE-Ablauf aus RaKScribe.py mit Attrappen
(exe_stubs), Tasten über den echten SpeechMike-Dekodierer. Synthetische Texte, keine Patientendaten.
Aufruf: python tests/offline/test_ergaenzung_ohne_ins.py   (--schreiben = gemeinsame EOL-Fälle neu erzeugen)"""
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
    S.pump(app, None, 0.6)


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


# 6c. kaiscribe-ergaenzung-ohne-ins-n1 (Peter 26.11.2026, Diktat 20261126060 – Abnahmeablauf wörtlich): ECHTE
# Cursor-Ermittlung (Fokus im Befund, KaiScribe vorne), „Nur Text“ AUS. Cursor rechts → Record → sprechen → Pause ⇒ der
# gesprochene Text steht wörtlich RECHTS an der Stelle, links wird NICHTS angehängt, keine Befund-KI, kein INS nötig;
# EOL schließt danach direkt ab (genau der sichtbare Befund per Strg+V ins zuletzt aktive Fremdfenster).
def cursor_app(nur_text=False, antworten=("Zusätzlich kleiner Gelenkerguss.", "")):
    app = neue_app()
    app._hinweise = []
    kh = app._kurzhinweis
    app._kurzhinweis = lambda t, ms=4000: (app._hinweise.append(t), kh(t, ms))
    druecke(app, "RECORD"); audio(app); druecke(app, "INS"); bis_ruhe(app)
    b = app.result_text.text
    tb = S.FakeTb(app.result_text, insert=len(b))
    app.result_text._textbox = tb
    app.focus_get = lambda: tb
    app.nur_text_var = Var(nur_text)
    mod._fokus_ist_eigenes_fenster = lambda: True      # Peter hat in KaiScribe rechts in den Befund geklickt
    mod._korr.korrigieren = lambda t, key, block="", log=None: t
    CHIRP.update(aufrufe=[], antworten=list(antworten))
    return app, b, tb


def eingefuegt(app, b, text, timeout=4):
    return S.pump(app, lambda: app.result_text.text == b + " " + text, timeout)


for nt in (False, True):
    wo = "Nur Text an" if nt else "Nur Text aus"
    app, B, tb = cursor_app(nur_text=nt)
    LINKS = app.transcript_text.text
    n_llm = len(LLM["prompts"])
    druecke(app, "RECORD")
    check(f"6c Cursor im Befund + Record ({wo}): Statuszeile „Ergänzung an Cursor-Stelle … der übrige Befund bleibt“",
          app._einfuegen_ziel == (len(B), len(B)) and "Ergänzung an Cursor-Stelle · Aufnahme läuft" in app.status_badge.cfg["text"]
          and "der übrige Befund bleibt" in app.status_badge.cfg["text"], f"{app._einfuegen_ziel} / {app.status_badge.cfg.get('text')}")
    audio(app); druecke(app, "RECORD")                    # Pause
    ok = eingefuegt(app, B, "Zusätzlich kleiner Gelenkerguss.")
    check(f"6c Pause ({wo}): Text steht SOFORT wörtlich rechts an der Stelle – ohne INS, keine Befund-KI, nichts ins RIS",
          ok and len(LLM["prompts"]) == n_llm and S.AUFZ.tasten == [] and app._job.zustand == "PAUSED",
          repr(app.result_text.text[len(B):]))
    check(f"6c … links wird NICHTS angehängt ({wo})", app.transcript_text.text == LINKS, repr(app.transcript_text.text))
    check(f"6c … Statuszeile „Pause – steht rechts · Record: weiter · EOL: abschließen“ ({wo})",
          "Pause – steht rechts" in app.status_badge.cfg["text"] or "Ergänzung an Cursor-Stelle eingefügt" in app.status_badge.cfg["text"],
          app.status_badge.cfg.get("text"))
    mod._fokus_ist_eigenes_fenster = lambda: False
    SICHTBAR = app.result_text.text
    druecke(app, "EOL")
    S.pump(app, lambda: S.AUFZ.tasten, 2)
    check(f"6c EOL direkt in der Pause ({wo}): genau der sichtbare Befund, SpeechMagic aktiviert, genau einmal Strg+V, leer",
          S.CLIPBOARD.data.get(13) == SICHTBAR.strip() and app._api.aktiviert == [42] and S.AUFZ.tasten == ["ctrl+v"]
          and app.result_text.text == "" and app._einfuegen_ziel is None and app._job.zustand == "READY"
          and "Erst INS" not in str(getattr(app, "_letzter_hinweis", "")),
          f"{app._api.aktiviert} / {S.AUFZ.tasten} / {getattr(app, '_letzter_hinweis', '')}")
    check(f"6c … „Nur Text“ unverändert ({wo})", app.nur_text_var.get() is nt)
druecke(app, "RECORD")
check("6c nächster Patient: Record ohne Befund → normales Diktat, keine Ergänzungs-Anzeige",
      app._einfuegen_ziel is None and "Ergänzung" not in app.status_badge.cfg["text"], app.status_badge.cfg.get("text"))
app.reset_dictation()

# 6d. Weiter-Diktieren hängt dahinter an; INS danach baut NIE neu (nur der Rest, hier Stille), EOL schließt ab
app, B, tb = cursor_app(antworten=("Kleiner Erguss.", "Plica mediopatellaris.", ""))
n_llm = len(LLM["prompts"])
druecke(app, "RECORD"); audio(app); druecke(app, "RECORD")
eingefuegt(app, B, "Kleiner Erguss.")
druecke(app, "RECORD")                                    # weiter
check("6d Record in der Pause = weiter (gleiche Aufnahme), Ziel hinter dem Eingefügten",
      app._job.zustand == "RECORDING" and app._einfuegen_ziel == (len(B) + 16, len(B) + 16), str(app._einfuegen_ziel))
audio(app); druecke(app, "RECORD")
ok = eingefuegt(app, B, "Kleiner Erguss. Plica mediopatellaris.")
check("6d zweite Pause: Abschnitt hängt hinter dem ersten an, Rest unverändert", ok, repr(app.result_text.text[len(B):]))
druecke(app, "INS"); bis_ruhe(app)
check("6d INS danach: KEIN Neuaufbau (keine Befund-KI), Befund unverändert, Status Kontrolle, nichts eingefügt",
      app.result_text.text == B + " Kleiner Erguss. Plica mediopatellaris." and len(LLM["prompts"]) == n_llm
      and app._status_raw == "KONTROLLE" and S.AUFZ.tasten == [], repr(app.result_text.text[len(B):]))
check("6d … Strg+Z holt den Stand vor der GANZEN Ergänzung (beide Abschnitte) zurück",
      app._rueckgaengig() == "break" and app.result_text.text == B and app._rueckgaengig() == "break")
mod._fokus_ist_eigenes_fenster = lambda: False
druecke(app, "EOL"); S.pump(app, lambda: S.AUFZ.tasten, 2)
check("6d EOL nach INS: abgeschlossen (Strg+V)", S.AUFZ.tasten == ["ctrl+v"] and app.result_text.text == "")

# 6e. EOL während der Aufnahme (Cursor): erst einfügen, nichts senden, Hinweis; zweites EOL schließt ab
app, B, tb = cursor_app()
druecke(app, "RECORD"); audio(app)
druecke(app, "EOL")
check("6e EOL während der Ergänzungs-Aufnahme: nicht „Erst INS“, Hinweis „… danach EOL nochmals“, nichts gesendet",
      app._letzter_hinweis in (mod.ERGAENZUNG_EOL, mod.ERGAENZUNG_EOL_FERTIG) and S.AUFZ.tasten == []
      and app._job.zustand == "PAUSED" and "Erst INS" not in "".join(app._hinweise),
      f"{app._letzter_hinweis} / {app._job.zustand}")
ok = eingefuegt(app, B, "Zusätzlich kleiner Gelenkerguss.")
S.pump(app, lambda: False, 0.3)
check("6e … Ergänzung eingefügt, Hinweis „Ergänzung eingefügt – EOL nochmals zum Abschließen“",
      ok and app._letzter_hinweis == mod.ERGAENZUNG_EOL_FERTIG, app._letzter_hinweis)
mod._fokus_ist_eigenes_fenster = lambda: False
SICHTBAR = app.result_text.text
druecke(app, "EOL"); S.pump(app, lambda: S.AUFZ.tasten, 2)
check("6e zweites EOL: genau der sichtbare Befund mit Ergänzung weitergeschickt",
      S.CLIPBOARD.data.get(13) == SICHTBAR.strip() and S.AUFZ.tasten == ["ctrl+v"] and app.result_text.text == "")

# 6f. Ergänzung OHNE Cursor (Befund steht, Record, Pause): EOL baut die Ergänzung erst ein, zweites EOL schließt ab
app = neue_app()
druecke(app, "RECORD"); audio(app); druecke(app, "INS"); bis_ruhe(app)
B = app.result_text.text
mod._korr.korrigieren = lambda t, key, block="", log=None: t
CHIRP.update(aufrufe=[], antworten=["Kleiner Erguss."])
n_llm = len(LLM["prompts"])
druecke(app, "RECORD"); audio(app); druecke(app, "RECORD")
S.pump(app, lambda: False, 0.3)
druecke(app, "EOL")
check("6f EOL in der Pause einer Ergänzung (ohne Cursor): kein „Erst INS“, nichts gesendet", S.AUFZ.tasten == []
      and app._letzter_hinweis in (mod.ERGAENZUNG_EOL, mod.ERGAENZUNG_EOL_FERTIG), app._letzter_hinweis)
bis_ruhe(app)
check("6f … Ergänzung eingebaut (Titel/Text bleiben, keine Befund-KI), Hinweis „EOL nochmals“",
      "Kleiner Erguss." in app.result_text.text and app.result_text.text.startswith(B.split("\n")[0])
      and len(LLM["prompts"]) == n_llm and app._letzter_hinweis == mod.ERGAENZUNG_EOL_FERTIG,
      f"{app._letzter_hinweis} / {app.result_text.text[-80:]!r}")
druecke(app, "EOL"); S.pump(app, lambda: S.AUFZ.tasten, 2)
check("6f zweites EOL schließt ab", S.AUFZ.tasten == ["ctrl+v"] and app.result_text.text == "")

# 6g. Neuer Befund (rechts leer): EOL in der Pause bleibt „Erst INS“ (die Sperre gilt nur ohne Befund rechts)
app = neue_app()
druecke(app, "RECORD"); audio(app); druecke(app, "RECORD"); druecke(app, "EOL")
check("6g Neuer Befund, EOL in der Pause → „Erst INS …“, nichts gesendet",
      app._letzter_hinweis == "Erst INS, Befund prüfen, dann EOL" and S.AUFZ.tasten == [] and app._job.zustand == "PAUSED")
app.reset_dictation()

# 6h. Offene Ergänzung geht bei Fenster zu / Befund kopieren nicht still verloren (Peter 26.11., Fall 20261126060)
app, B, tb = cursor_app()
druecke(app, "RECORD"); audio(app)
FRAGEN = []
mod.messagebox.askyesno = lambda titel, text, **k: (FRAGEN.append(titel), True)[1]
app.befund_kopieren_knopf()
check("6h „Befund kopieren“ bei laufender Ergänzung: nicht kopiert, erst eingefügt, Hinweis",
      S.CLIPBOARD.data.get(13) != B and "Befund kopieren" in app._letzter_hinweis and app._job.zustand == "PAUSED",
      app._letzter_hinweis)
eingefuegt(app, B, "Zusätzlich kleiner Gelenkerguss.")
druecke(app, "RECORD"); audio(app)
_selbsttest = mod.os.environ.pop("RAKSCRIBE_SELFTEST", None)
app._schliessen()
check("6h Fenster schließen bei offener Ergänzung → Rückfrage, „Ja“ = einfügen, Fenster bleibt offen",
      FRAGEN == ["Fenster schließen"] and app._job.zustand == "PAUSED", f"{FRAGEN} / {app._job.zustand}")
mod.messagebox.askyesno = lambda *a, **k: False
app.reset_dictation()


# Gemeinsame Regel EXE ≡ Web: was tut EOL (befundfeld.eol_aktion), wann fügt die Pause ein (pause_fuegt_ein)
import json  # noqa: E402
bf = mod._bf
FAELLE = pathlib.Path(__file__).resolve().parent / "snapshots" / "ergaenzung_eol_faelle.txt"
faelle = []
for z in ("READY", "ERROR", "RECORDING", "PAUSED", "PROCESSING", "LOCKED"):
    for einbau in ("neu", "geruest", "maske", "ergaenzung", "cursor", None):
        for ziel in (False, True):
            for offen in (0, 1):
                faelle.append({"zustand": z, "einbau": einbau, "ziel": ziel, "offen": offen,
                               "aktion": bf.eol_aktion(z, einbau, ziel, offen),
                               "pause_fuegt_ein": bf.pause_fuegt_ein(ziel, einbau == "maske")})
if "--schreiben" in sys.argv:
    FAELLE.write_text(json.dumps(faelle, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
gespeichert = json.loads(FAELLE.read_text(encoding="utf-8"))
check("gemeinsame EOL-Fälle (snapshots/ergaenzung_eol_faelle.txt) = befundfeld.py", gespeichert == faelle,
      f"{len(gespeichert)} vs {len(faelle)}")
d = {(f["zustand"], f["einbau"], f["ziel"], f["offen"]): f["aktion"] for f in faelle}
check("Regel: Pause mit allem rechts → EOL schließt ab; Aufnahme → erst einfügen; wird eingefügt → warten",
      d[("PAUSED", "cursor", True, 0)] == "abschliessen" and d[("RECORDING", "cursor", True, 0)] == "einfuegen"
      and d[("PAUSED", "cursor", True, 1)] == "warten" and d[("PAUSED", "ergaenzung", False, 0)] == "einfuegen")
check("Regel: „Erst INS“ nur ohne Befund rechts (Neuer Befund / Gerüst / Maske), in Ruhe senden",
      all(d[(z, e, False, 0)] == "sperre" for z in ("RECORDING", "PAUSED", "PROCESSING") for e in ("neu", "geruest", "maske"))
      and d[("READY", "neu", False, 0)] == "senden")

# Quelltext: Statuszeile, Rückfragen, Knopf
src = (pathlib.Path(__file__).resolve().parents[2] / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE: „Befund kopieren“ läuft über befund_kopieren_knopf, Schließen/Abbrechen fragen bei offener Ergänzung",
      "command=self.befund_kopieren_knopf" in src and src.count("self._ergaenzung_offen_fragen(") == 2)

print("FAILS:", fails)
sys.exit(1 if fails else 0)
