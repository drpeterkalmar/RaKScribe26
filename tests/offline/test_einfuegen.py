"""Gate v3.5.0 (Peter 07.10.): Diktat an der Cursor-Stelle in den Befund einfügen / Markierung überschreiben.
einfuegen.py (= einfuegen.ts über snapshots/einfuegen_faelle.txt) und EXE-Ablauf mit Attrappen.
Aufruf: /usr/bin/python3 tests/offline/test_einfuegen.py"""
import json, pathlib, sys
HIER = pathlib.Path(__file__).resolve().parent
ROOT = HIER.parents[1]
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(ROOT / "source_code"))
import einfuegen as E  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# 1. Gemeinsame Fälle (Web prüft dieselbe Datei in pipeline_test.mjs)
for f in json.loads((HIER / "snapshots" / "einfuegen_faelle.txt").read_text(encoding="utf-8")):
    r = E.einfuegen(f["text"], f["start"], f["ende"], f["neu"], gross=f.get("gross", False))
    check(f"einfuegen: {f['name']}", list(r) == [f["ergebnis"], f["cursor"]], repr(r))


# 2. EXE: Cursor im Befund + F10 → Diktat wird dort eingefügt, Befund bleibt, kein Befund-LLM, kein Strg+V
import exe_stubs as S  # noqa: E402
FakeTb = S.FakeTb  # v3.18.9: nach exe_stubs verschoben (auch test_speechmike_ablauf)
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: True
mod._korr.korrigieren = lambda t, key, block="", log=None: "Zusätzlich kleiner Gelenkerguss."
mod._llm_aufruf = lambda p: (_ for _ in ()).throw(AssertionError("Befund-KI beim Einfügen gerufen"))
BEFUND = "## Kniegelenk rechts\n\n## Befund\nKein Erguss. Bänder intakt.\n\n## Ergebnis\nUnauffälliger Befund."


def lauf(insert=0, sel=None, chirp="zusätzlich kleiner Gelenkerguss", fokus=True, gross=None):
    S.AUFZ.tasten.clear()
    mod._chirp3_worker = lambda pcm, sr, loc, token: chirp
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub())
    app = S.baue_app(mod)
    app.result_text.insert("1.0", BEFUND)
    tb = FakeTb(app.result_text, insert, sel)
    app.result_text._textbox = tb
    app.focus_get = (lambda: tb) if fokus else (lambda: None)
    app.status_badge = S.FakeWidget()
    if gross is not None:
        app.gross_satzanfang_var = type("V", (), {"get": lambda self: gross})()
    app.toggle_recording()
    S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
    app.toggle_recording()
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
    S.pump(app, lambda: False, 0.8)
    app._aufnahme_stoppen()
    return app, tb


pos = BEFUND.index("Bänder")
app, tb = lauf(insert=pos)
erwartet = BEFUND.replace("Kein Erguss. Bänder", "Kein Erguss. Zusätzlich kleiner Gelenkerguss. Bänder")
check("EXE Cursor im Befund: Diktat an der Stelle eingefügt, Rest unverändert", app.result_text.text == erwartet,
      repr(app.result_text.text))
check("EXE: Cursor steht hinter dem eingefügten Text, Fokus im Befund",
      tb.marks["insert"] == pos + len("Zusätzlich kleiner Gelenkerguss.") and tb.fokus, str(tb.marks))
check("EXE: ganzer Befund kopiert, kein Strg+V (RaKScribe vorne)", S.AUFZ.tasten == []
      and "Gelenkerguss" in str(S.CLIPBOARD.data.get(13, "")), str(S.AUFZ.tasten))

a = BEFUND.index("Kein Erguss.")
app, tb = lauf(sel=(a, a + len("Kein Erguss.")))
check("EXE Markierung: wird durch das Diktat ersetzt",
      app.result_text.text == BEFUND.replace("Kein Erguss.", "Zusätzlich kleiner Gelenkerguss."), repr(app.result_text.text))

# v3.7.0: Option „Satzanfang groß“ (Standard an) — Diktat kommt klein, Cursor nach Satzende
mod._korr.korrigieren = lambda t, key, block="", log=None: "zusätzlich kleiner Gelenkerguss."
app, tb = lauf(insert=pos)
check("EXE Satzanfang groß (Standard an): nach Satzende groß eingefügt",
      "Kein Erguss. Zusätzlich kleiner Gelenkerguss. Bänder" in app.result_text.text, repr(app.result_text.text))
app, tb = lauf(insert=pos, gross=False)
check("EXE Option aus: bleibt klein", "Kein Erguss. zusätzlich kleiner Gelenkerguss. Bänder" in app.result_text.text,
      repr(app.result_text.text))
src = (HIER.parents[1] / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE Menü-Option „Satzanfang groß“ wird gespeichert", 'add_checkbutton(label="Diktat in den Befund: Satzanfang groß"' in src
      and 'einstellung_schreiben("gross_satzanfang"' in src)
mod._korr.korrigieren = lambda t, key, block="", log=None: "Zusätzlich kleiner Gelenkerguss."

NEU = "## Schultergelenk links\n\n## Befund\nRegelrecht.\n\n## Ergebnis\nUnauffälliger Befund."
mod._llm_aufruf = lambda p: NEU
app, tb = lauf(insert=pos, fokus=False, chirp="Schulter links Tendinopathie der Supraspinatussehne")
check("EXE ohne Cursor im Befund: normaler Ablauf, neuer Befund ersetzt den alten", "Kniegelenk" not in app.result_text.text
      and "Schultergelenk links" in app.result_text.text, repr(app.result_text.text[:80]))
app.reset_dictation()
check("EXE F9 löscht das Einfüge-Ziel", app._einfuegen_ziel is None)

# v3.15.4 (Peter 15.10., Ordi-Protokoll: Record → Pause → in den Befund geklickt → Record = „weiter“ → die Stelle wurde
# nie gelesen, INS baute einen neuen Befund): SpeechMike-Ablauf mit Klick in der Pause, mit und ohne „Nur Text“, im CAS-Band
mod._llm_aufruf = lambda p: (_ for _ in ()).throw(AssertionError("Befund-KI beim Einfügen gerufen"))


def lauf_pause(sel=None, insert=0, nur_text=False, cas=False):
    mod._chirp3_worker = lambda pcm, sr, loc, token: "zusätzlich kleiner Gelenkerguss"
    app = S.baue_app(mod)
    app.result_text.insert("1.0", BEFUND)
    app.transcript_text.insert("1.0", "Knie rechts unauffällig")      # bisheriges Diktat (Nachdiktat-Basis)
    tb = FakeTb(app.result_text, insert, sel)
    app.result_text._textbox = tb
    fokus = {"tb": None}
    app.focus_get = lambda: fokus["tb"]
    app.status_badge = S.FakeWidget()
    app.repariert_label = S.FakeWidget()
    app.nur_text_var = type("V", (), {"get": lambda self: nur_text})()
    if cas:
        app._cas = type("A", (), {"nr": "20261015901", "leistungen": None, "kontext": None})()
        app._cas_aufnahmen, app._cas_hinweise = [], []
        app._cas_hinweise_zeigen = lambda h: None
        app._ibl_befund_leeren = lambda: None
        app._ibl_nach_lauf = lambda e: None
    app.sm_record()                                   # Record: Aufnahme startet (noch nicht in den Befund geklickt)
    S.pump(app, lambda: len(app._aufnahme.puffer) >= 6)
    app.sm_record()                                   # Pause
    S.pump(app, lambda: False, 0.3)
    fokus["tb"] = tb                                  # … jetzt in den Befund geklickt bzw. markiert
    app.sm_record()                                   # Record = weiter
    S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
    app.sm_ins()
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
    S.pump(app, lambda: False, 0.8)
    app._aufnahme_stoppen()
    return app, tb


app, tb = lauf_pause(insert=pos)
check("SpeechMike: in der Pause in den Befund geklickt → Diktat an der Stelle eingefügt, Rest bleibt, nichts eingefügt "
      "ins RIS", app.result_text.text == erwartet and S.AUFZ.tasten == [] and app._status_raw == "KONTROLLE",
      repr(app.result_text.text))
app, tb = lauf_pause(sel=(a, a + len("Kein Erguss.")), nur_text=True)
check("… mit „Nur Text“: Markierung durch den korrigierten Text ersetzt (kein Befundumbau)",
      app.result_text.text == BEFUND.replace("Kein Erguss.", "Zusätzlich kleiner Gelenkerguss."), repr(app.result_text.text))
app, tb = lauf_pause(insert=pos, cas=True)
check("… mit offenem CAS-Auftrag (blaues Band): ebenso eingefügt, wartet auf EOL", app.result_text.text == erwartet
      and app._status_raw == "KONTROLLE", repr(app.result_text.text))


# v3.18.9 (Peter 12.11., kaiscribe-cursor-record-n1: „ins rechte Fenster direkte Ergänzungen dazu diktieren“, Wahl b):
# Ordi-Protokoll 12.11. 09:36: Peter schaltete „Nur Text“ VOR dem Record ein (und danach wieder aus). Nötig ist das
# nicht: Cursor/Markierung im Befund + Record (SpeechMike, ohne Pause) → wörtlich dort, Nur Text bleibt AUS,
# Statuszeile „Ergänzung an Cursor-Stelle“ von der Aufnahme bis zum Einfügen.
def lauf_direkt(sel=None, insert=0, cas=False, fokus=True):
    S.AUFZ.tasten.clear()
    mod._chirp3_worker = lambda pcm, sr, loc, token: "zusätzlich kleiner Gelenkerguss"
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub())
    app = S.baue_app(mod)
    app.result_text.insert("1.0", BEFUND)
    app.transcript_text.insert("1.0", "Knie rechts unauffällig")
    tb = FakeTb(app.result_text, insert, sel)
    app.result_text._textbox = tb
    app.focus_get = (lambda: tb) if fokus else (lambda: None)
    app.status_badge = S.FakeWidget()
    app.repariert_label = S.FakeWidget()
    nur_text = S_Var(False)
    app.nur_text_var = nur_text
    if cas:
        app._cas = type("A", (), {"nr": "20261112901", "leistungen": None, "kontext": None})()
        app._cas_aufnahmen, app._cas_hinweise = [], []
        app._cas_hinweise_zeigen = lambda h: None
        app._ibl_befund_leeren = lambda: None
        app._ibl_nach_lauf = lambda e: None
    stati = []
    app.sm_record()                                   # Record mit Cursor im Befund
    stati.append(app.status_badge.cfg.get("text", ""))
    S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
    app.sm_ins()
    stati.append(app.status_badge.cfg.get("text", ""))
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
    S.pump(app, lambda: False, 0.8)
    app._aufnahme_stoppen()
    return app, tb, stati, nur_text


class S_Var:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


for cas in (False, True):
    wo = "im CAS-Band" if cas else "ohne CAS"
    app, tb, stati, nt = lauf_direkt(insert=pos, cas=cas)
    check(f"Record direkt mit Cursor im Befund ({wo}), Nur Text AUS → wörtlich an der Stelle, Rest unverändert, "
          "nichts ins RIS", app.result_text.text == erwartet and S.AUFZ.tasten == [] and app._status_raw == "KONTROLLE",
          repr(app.result_text.text))
    check(f"… Statuszeile „Ergänzung an Cursor-Stelle“ bei Aufnahme und Verarbeitung ({wo})",
          "Ergänzung an Cursor-Stelle · Aufnahme läuft" in stati[0] and "Ergänzung an Cursor-Stelle wird eingefügt" in stati[1],
          str(stati))
    check(f"… danach Hinweis „Ergänzung an Cursor-Stelle eingefügt“, Nur Text bleibt aus, Ziel verbraucht ({wo})",
          app._letzter_hinweis == "Ergänzung an Cursor-Stelle eingefügt" and nt.get() is False
          and app._einfuegen_ziel is None, f"{app._letzter_hinweis} / {nt.get()} / {app._einfuegen_ziel}")
    check(f"… Cursor hinter der Ergänzung ({wo})", tb.marks["insert"] == pos + len("Zusätzlich kleiner Gelenkerguss."))
app, tb, stati, nt = lauf_direkt(sel=(a, a + len("Kein Erguss.")), cas=True)
check("Record direkt mit Markierung (Nur Text AUS) → Markierung wörtlich ersetzt",
      app.result_text.text == BEFUND.replace("Kein Erguss.", "Zusätzlich kleiner Gelenkerguss."), repr(app.result_text.text))
mod._llm_aufruf = lambda p: NEU
app, tb, stati, nt = lauf_direkt(insert=pos, fokus=False)
check("Record ohne Cursor im Befund → normaler Befund (Nachdiktat), keine Ergänzungs-Anzeige",
      "Schultergelenk links" in app.result_text.text and "Ergänzung" not in "".join(stati)
      and getattr(app, "_letzter_hinweis", "") != "Ergänzung an Cursor-Stelle eingefügt", f"{stati} / {app.result_text.text[:40]!r}")

print("FAILS:", fails)
sys.exit(1 if fails else 0)
