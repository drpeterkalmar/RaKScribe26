"""Gate (Umbau Schritte 4–6): echter EXE-Ablauf aus RaKScribe.py mit Attrappen statt Windows/Tk/Mikrofon/Google.
Aufnahme → Streaming-Anzeige → Stopp → chirp_3 → Befund (Normalbefund-Bypass, ohne Gemini) → Kopieren → Strg+V,
dazu F10/F9 während der Verarbeitung, verspätete Streaming-Antworten, gesperrte Zwischenablage, chirp_3-Ausfall.
Synthetische Diktate, keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_exe_ablauf.py"""
import pathlib, sys, threading, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import exe_stubs as S  # noqa: E402

mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod.speech_client = object()
mod._get_stt_access_token = lambda: "token"
CHIRP = {"text": "Kniegelenk rechts in 2 Ebenen unauffällig.", "tor": None, "aufrufe": 0}


def chirp(pcm, sr, loc, token):
    CHIRP["aufrufe"] += 1
    CHIRP["samples"] = len(pcm)
    if CHIRP["tor"] is not None:
        CHIRP["tor"].wait(5)
    return CHIRP["text"]


mod._chirp3_worker = chirp
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


def fake_record(app):
    """Ersetzt record(gen): eine Sekunde Audio + Streaming-Anzeige, dann warten bis Stopp."""
    def record(gen):
        app.recorded_audio_chunks_all.append(np.zeros((16000, 1), dtype=np.int16))
        app.recorded_audio_chunks_all.append(np.ones((8000, 1), dtype=np.int16))
        app.after(0, app.update_interim_text, "Knie rechts", False, gen)
        app.after(0, app.update_interim_text, "Knie rechts unauffällig", True, gen)
        while app.is_recording:
            time.sleep(0.005)
    app.record = record


def neue_app():
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
    S.CLIPBOARD.gesperrt = False
    CHIRP.update(text="Kniegelenk rechts in 2 Ebenen unauffällig.", tor=None, aufrufe=0)
    app = S.baue_app(mod)
    fake_record(app)
    return app


def bis_fertig(app, timeout=8):
    return S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)


# 1. Normaler Ablauf
app = neue_app()
app.toggle_recording()
check("F10 startet Aufnahme", app.is_recording and app._job.zustand == "RECORDING" and app._status_raw == "RECORDING")
S.pump(app, lambda: "unauffällig" in app.transcript_text.text)
check("Streaming nur in der Anzeige (stream_transcript), final_transcript leer",
      app.stream_transcript.strip() == "Knie rechts unauffällig" and app.final_transcript == "")
app.toggle_recording()
check("F10 stoppt → Verarbeitung", not app.is_recording and app._job.zustand == "PROCESSING")
bis_fertig(app)
S.pump(app, lambda: S.AUFZ.tasten)
time.sleep(0.05); S.pump(app)
check("chirp_3 bekommt die ganze Aufnahme", CHIRP["samples"] == 24000, str(CHIRP.get("samples")))
check("Endtext = chirp_3", app.final_transcript == CHIRP["text"] and app.transcript_text.text == CHIRP["text"])
check("Befund (Bypass) erstellt", app.result_text.text.startswith("## Kniegelenk") and "## Ergebnis" in app.result_text.text,
      app.result_text.text[:80])
check("kopiert + genau einmal Strg+V", S.CLIPBOARD.data.get(13) == app.result_text.text.strip() and S.AUFZ.tasten == ["ctrl+v"],
      str(S.AUFZ.tasten))
check("Status Kopiert, Zustand bereit", app._status_raw == "COPIED" and app._job.zustand == "READY")
gen1 = app._job.gen
app.update_interim_text("Schulter links", True, gen1)
check("verspätetes stream_final nach chirp_3 wird verworfen", app.final_transcript == CHIRP["text"]
      and app.transcript_text.text == CHIRP["text"])

# 2. F10 während der Verarbeitung → ignoriert, Befund kommt trotzdem
app = neue_app()
CHIRP["tor"] = threading.Event()
app.toggle_recording(); S.pump(app, lambda: app.stream_transcript); app.toggle_recording()
S.pump(app, lambda: CHIRP["aufrufe"] == 1)
app.toggle_recording()
check("F10 während Verarbeitung startet keine Aufnahme", not app.is_recording and app._job.zustand == "PROCESSING"
      and app._status_raw == "PROCESSING")
CHIRP["tor"].set()
bis_fertig(app); S.pump(app, lambda: S.AUFZ.tasten)
check("… und der Befund wird danach normal eingefügt", S.AUFZ.tasten == ["ctrl+v"] and app._job.zustand == "READY")

# 3. F9 während der Verarbeitung → abgebrochen, nichts eingefügt
app = neue_app()
CHIRP["tor"] = threading.Event()
app.toggle_recording(); S.pump(app, lambda: app.stream_transcript); app.toggle_recording()
S.pump(app, lambda: CHIRP["aufrufe"] == 1)
app.reset_dictation()
check("F9 während Verarbeitung → sofort bereit", app._job.zustand == "READY" and app._status_raw == "READY")
CHIRP["tor"].set()
time.sleep(0.3); S.pump(app)
check("abgebrochener Lauf schreibt nichts und fügt nichts ein", S.AUFZ.tasten == [] and app.result_text.text == ""
      and app.transcript_text.text == "")
app.toggle_recording()
check("danach neue Aufnahme möglich", app.is_recording and app._job.zustand == "RECORDING")
app.reset_dictation()
check("F9 während Aufnahme → Mikrofon zu, keine Verarbeitung", not app.is_recording and app._job.zustand == "READY")
time.sleep(0.2); S.pump(app)
check("… kein chirp_3-Aufruf", CHIRP["aufrufe"] == 1, str(CHIRP["aufrufe"]))

# 4. Zwischenablage gesperrt → kein Strg+V, Fehler sichtbar
app = neue_app()
S.CLIPBOARD.gesperrt = True
app.toggle_recording(); S.pump(app, lambda: app.stream_transcript); app.toggle_recording()
bis_fertig(app); time.sleep(0.05); S.pump(app)
check("gesperrte Zwischenablage → kein Strg+V", S.AUFZ.tasten == [])
check("… Status Fehler + Fehlerdialog", app._status_raw == "ERROR" and any(d[0] == "showerror" for d in S.AUFZ.dialoge),
      str(S.AUFZ.dialoge))

# 5. chirp_3 liefert nichts → Rettung aus der Streaming-Anzeige
app = neue_app()
CHIRP["text"] = ""
app.toggle_recording(); S.pump(app, lambda: app.stream_transcript); app.toggle_recording()
bis_fertig(app); S.pump(app, lambda: S.AUFZ.tasten)
check("chirp_3 leer → Streaming-Text gerettet, Befund eingefügt", app.final_transcript == "Knie rechts unauffällig"
      and S.AUFZ.tasten == ["ctrl+v"], app.final_transcript)

print("\n" + ("✅ EXE-ABLAUF PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
