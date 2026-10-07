"""Gate v3.6.0 (Peter 07.10.): getippten/eingefügten Text im Diktat-Feld per Knopf „Befund aus Text“ strukturieren.
EXE-Ablauf mit Attrappen (kein Mikrofon, kein chirp_3). Aufruf: /usr/bin/python3 tests/offline/test_befund_aus_text.py"""
import pathlib, sys
HIER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import exe_stubs as S  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._fokus_ist_eigenes_fenster = lambda: False
CHIRP = []
mod._chirp3_worker = lambda *a: CHIRP.append(1) or "darf nicht gerufen werden"
PROMPTS = []
BEFUND = ("## Schultergelenk rechts\n\n## Befund\nIm Ansatzbereich der Supraspinatussehne 17 mm messendes Kalkdepot. "
          "Regelrechte Stellung im Glenohumeralgelenk.\n\n## Ergebnis\n1. Tendinosis calcarea der Supraspinatussehne rechts.")
mod._llm_aufruf = lambda p: (PROMPTS.append(p), BEFUND)[1]
mod._korr.korrigieren = lambda *a, **k: (_ for _ in ()).throw(AssertionError("Call 0 bei getipptem Text"))


def neue_app(text):
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear(); PROMPTS.clear(); CHIRP.clear()
    app = S.baue_app(mod)
    app.transcript_text.insert("1.0", text)
    return app


def fertig(app):
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
    S.pump(app, lambda: S.AUFZ.tasten, 1.0)


DIKTAT = "Schulter rechts Tendinosis calcarea mit 17 mm messendem Kalkdepot"
app = neue_app(DIKTAT)
check("Knopf gibt 'break' zurück (Strg+Enter fügt keinen Zeilenumbruch ein)", app.befund_aus_text() == "break")
fertig(app)
check("strukturierter Befund rechts", app.result_text.text == BEFUND, repr(app.result_text.text[:80]))
check("Gemini bekam den getippten Text", len(PROMPTS) == 1 and DIKTAT in PROMPTS[0])
check("kein Mikrofon/chirp_3, kein Call 0", CHIRP == [])
check("kopiert und eingefügt wie nach einer Aufnahme", S.AUFZ.tasten == ["ctrl+v"] and S.CLIPBOARD.data.get(13), str(S.AUFZ.tasten))
check("Diktat-Feld bleibt stehen", app.transcript_text.text == DIKTAT)
check("Zustand wieder Bereit", app._job.zustand == "READY")

app = neue_app("Kniegelenk rechts unauffällig")
app.befund_aus_text(); fertig(app)
check("Normalbefund aus Text → Bypass ohne Gemini", PROMPTS == [] and "## Ergebnis" in app.result_text.text, repr(app.result_text.text[:80]))

app = neue_app(DIKTAT)
app.nur_text_var = type("V", (), {"get": lambda self: True})()
app.befund_aus_text(); fertig(app)
check("auch bei „Nur Text“ ein strukturierter Befund", app.result_text.text == BEFUND, repr(app.result_text.text[:80]))

app = neue_app("   ")
app.befund_aus_text()
check("leeres Diktat-Feld → Hinweis, kein Lauf", S.AUFZ.dialoge and app._job.zustand == "READY" and app._job.gen == 0, str(S.AUFZ.dialoge))

app = neue_app(DIKTAT)
mod.speech_client = S.FakeSpeechClient(S.streaming_stub())
mod._get_stt_access_token = lambda: "token"
app.toggle_recording()
gen = app._job.gen
app.befund_aus_text()
check("während der Aufnahme ignoriert", app._job.zustand == "RECORDING" and app._job.gen == gen and PROMPTS == [])
app.reset_dictation()
app._aufnahme_stoppen()

app = neue_app(DIKTAT)
mod.keys_ready = lambda: False
app.refresh_key_state = lambda: None
app.befund_aus_text()
check("ohne Schlüssel kein Lauf", app._job.gen == 0 and PROMPTS == [])
mod.keys_ready = lambda: True

src = (HIER.parents[1] / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("Knopf + Strg+Enter im Diktat-Feld verdrahtet", 'text="✎  Befund aus Text"' in src
      and 'bind("<Control-Return>", self.befund_aus_text)' in src)

print("FAILS:", fails)
sys.exit(1 if fails else 0)
