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


def aufnehmen(app, bloecke=12):
    """F10, warten bis Live-Text sichtbar und > 1 s Audio im Puffer, F10."""
    app.toggle_recording()
    S.pump(app, lambda: app.stream_transcript and len(app._aufnahme.puffer) >= bloecke)
    app.toggle_recording()


def neue_app():
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
    S.CLIPBOARD.gesperrt = False
    CHIRP.update(text="Kniegelenk rechts in 2 Ebenen unauffällig.", tor=None, aufrufe=0)
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub())
    return S.baue_app(mod)


def bis_fertig(app, timeout=8):
    return S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)


# 1. Normaler Ablauf
app = neue_app()
app.toggle_recording()
check("F10 startet Aufnahme", app.is_recording and app._job.zustand == "RECORDING" and app._status_raw == "RECORDING")
S.pump(app, lambda: "unauffällig" in app.transcript_text.text and len(app._aufnahme.puffer) >= 12)
check("Streaming nur in der Anzeige (stream_transcript), final_transcript leer",
      app.stream_transcript.strip() == "Knie rechts unauffällig" and app.final_transcript == "")
app.toggle_recording()
check("F10 stoppt → Verarbeitung", not app.is_recording and app._job.zustand == "PROCESSING")
bis_fertig(app)
S.pump(app, lambda: S.AUFZ.tasten)
time.sleep(0.05); S.pump(app)
check("chirp_3 bekommt die ganze Aufnahme", CHIRP["samples"] == 1600 * len(app._aufnahme.puffer) > 16000,
      f"{CHIRP.get('samples')} vs {len(app._aufnahme.puffer)} Blöcke")
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
aufnehmen(app)
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
aufnehmen(app)
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
aufnehmen(app)
bis_fertig(app); time.sleep(0.05); S.pump(app)
check("gesperrte Zwischenablage → kein Strg+V", S.AUFZ.tasten == [])
check("… Status Fehler + Fehlerdialog", app._status_raw == "ERROR" and any(d[0] == "showerror" for d in S.AUFZ.dialoge),
      str(S.AUFZ.dialoge))

# 5. chirp_3 liefert nichts → Rettung aus der Streaming-Anzeige
app = neue_app()
CHIRP["text"] = ""
aufnehmen(app)
bis_fertig(app); S.pump(app, lambda: S.AUFZ.tasten)
check("chirp_3 leer → Streaming-Text gerettet, Befund eingefügt", app.final_transcript == "Knie rechts unauffällig"
      and S.AUFZ.tasten == ["ctrl+v"], app.final_transcript)

# 6. Mehr-Regionen-Diktat, eine Region scheitert (Gutachten P2-6) → fertige Region sichtbar, Hinweis, kein Strg+V
app = neue_app()
CHIRP["text"] = "Schulter rechts unauffällig. Ellbogen rechts Punkt Ellbogengelenksarthrose Punkt"
def llm_stub(prompt):  # Ellbogen-Region braucht Gemini (Pathologie) → Gemini fällt aus
    raise RuntimeError("Gemini: HTTP 503")


mod._llm_aufruf = llm_stub
aufnehmen(app)
bis_fertig(app); time.sleep(0.05); S.pump(app)
check("Mehr-Regionen: fertige Region steht im Befund-Feld", app.result_text.text.startswith("## Schultergelenk"),
      app.result_text.text[:60])
check("… gescheiterte Region benannt", "Befund für Region Ellbogen rechts konnte nicht erstellt werden" in app.result_text.text)
check("… Fehlerdialog, Status Fehler, kein Strg+V", S.AUFZ.tasten == [] and app._status_raw == "ERROR"
      and any(d[0] == "showerror" and "Ellbogen rechts" in d[2] for d in S.AUFZ.dialoge), str(S.AUFZ.dialoge))

# 7. Live-Anzeige bricht ab (Gutachten P1-4) → Aufnahme läuft weiter, chirp_3 bekommt alles, Befund wird eingefügt
app = neue_app()
mod.speech_client = S.FakeSpeechClient(S.streaming_stub(fehler_nach=2))
app.toggle_recording()
S.pump(app, lambda: app._live_aus)
n0 = len(app._aufnahme.puffer)
S.pump(app, lambda: len(app._aufnahme.puffer) >= n0 + 15)
check("Streaming-Fehler: Aufnahme läuft weiter, Hinweis im Status", app.is_recording and app._job.zustand == "RECORDING"
      and "Live-Anzeige ausgefallen" in app.status_badge.cfg.get("text", "") and not S.AUFZ.dialoge, str(S.AUFZ.dialoge))
app.toggle_recording()
bis_fertig(app); S.pump(app, lambda: S.AUFZ.tasten)
check("… chirp_3 über den vollständigen Puffer, Befund eingefügt",
      CHIRP["samples"] == 1600 * len(app._aufnahme.puffer) and len(app._aufnahme.puffer) > n0 and S.AUFZ.tasten == ["ctrl+v"],
      f"{CHIRP.get('samples')} / {len(app._aufnahme.puffer)}")

print("\n" + ("✅ EXE-ABLAUF PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
