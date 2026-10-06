"""Gate (Umbau Schritt 4, Gutachten P1-2/P2-5): Zustandsmaschine der EXE — F10/F9 während der Verarbeitung,
Generationsnummer je Lauf, verspätete Streaming-Antworten. Läuft ohne Windows/Tk.
Aufruf: /usr/bin/python3 tests/offline/test_jobstate.py"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import jobstate as js  # noqa: E402

fails = 0


def check(name, ok):
    global fails
    print(("✅" if ok else "❌"), name)
    fails += (not ok)


def job_in(zustand):
    j = js.JobState()
    if zustand == js.RECORDING:
        j.ereignis("toggle")
    elif zustand == js.PROCESSING:
        j.ereignis("toggle"); j.ereignis("toggle")
    elif zustand == js.ERROR:
        j.ereignis("toggle"); j.ereignis("toggle"); j.ereignis("report_failed", j.gen)
    elif zustand == js.LOCKED:
        j.sperren()
    assert j.zustand == zustand, (zustand, j.zustand)
    return j


# F10 / F9 (Verhalten wie v3.2.3)
j = job_in(js.READY)
check("F10 bereit → start, Aufnahme, neue Generation", j.ereignis("toggle") == "start" and j.zustand == js.RECORDING and j.gen == 1)
check("F10 bei Aufnahme → stop, Verarbeitung (gleiche Generation)", j.ereignis("toggle") == "stop" and j.zustand == js.PROCESSING and j.gen == 1)
logs = []
j._log = logs.append
check("F10 während Verarbeitung → ignoriert (None), kein Übergang, geloggt",
      j.ereignis("toggle") is None and j.zustand == js.PROCESSING and j.gen == 1 and logs)
check("vorschau ändert nichts", j.vorschau("toggle") is None and j.vorschau("reset") == "abbrechen" and j.zustand == js.PROCESSING)
check("F9 während Verarbeitung → abbrechen, bereit, Lauf ungültig",
      j.ereignis("reset") == "abbrechen" and j.zustand == js.READY and not j.aktuell(1))
j = job_in(js.RECORDING)
g = j.gen
check("F9 bei Aufnahme → stop_und_reset, bereit, Lauf ungültig",
      j.ereignis("reset") == "stop_und_reset" and j.zustand == js.READY and not j.aktuell(g))
check("F9 bereit → reset", job_in(js.READY).ereignis("reset") == "reset")
j = job_in(js.ERROR)
check("neue Aufnahme nach Fehler möglich (ERROR + F10 → start)", j.ereignis("toggle") == "start" and j.zustand == js.RECORDING)
j = job_in(js.ERROR)
check("F9 nach Fehler → bereit", j.ereignis("reset") == "reset" and j.zustand == js.READY)
j = job_in(js.LOCKED)
check("gesperrt: F10 → nichts", j.ereignis("toggle") is None and j.zustand == js.LOCKED)
check("gesperrt: F9 bleibt gesperrt", j.ereignis("reset") == "reset" and j.zustand == js.LOCKED)
j.entsperren()
check("entsperren → bereit", j.zustand == js.READY)
j = job_in(js.PROCESSING)
j.sperren()
check("sperren während Verarbeitung würgt den Lauf nicht ab", j.zustand == js.PROCESSING)

# Generationsnummer: verspätete Ereignisse aus altem Lauf
j = job_in(js.RECORDING)
alt = j.gen
check("Streaming der laufenden Aufnahme wird angezeigt", j.ereignis("stream_final", alt) == "anzeigen")
j.ereignis("toggle")  # Stopp → Verarbeitung
check("Streaming-Nachzügler nach Stopp (Endtext noch offen) → noch anzeigen", j.ereignis("stream_final", alt) == "anzeigen")
check("chirp_done → Endtext steht", j.ereignis("chirp_done", alt) == "uebernehmen" and j.text_fix)
check("stream_final NACH chirp_3-Endtext → verworfen (kein Anhängen, P2-5)", j.ereignis("stream_final", alt) is None)
check("stream_interim NACH chirp_3-Endtext → verworfen", j.ereignis("stream_interim", alt) is None)
j.ereignis("reset")
j.ereignis("toggle")  # neue Aufnahme
check("verspätetes stream_final ALTER Generation während neuer Aufnahme → verworfen",
      j.ereignis("stream_final", alt) is None and j.zustand == js.RECORDING)
check("report_done ALTER Generation → kein Einfügen", j.ereignis("report_done", alt) is None and j.zustand == js.RECORDING)
check("capture_failed ALTER Generation würgt neue Aufnahme nicht ab", j.ereignis("capture_failed", alt) is None
      and j.zustand == js.RECORDING)
check("capture_failed laufende Aufnahme → Fehler", j.ereignis("capture_failed", j.gen) == "fehler" and j.zustand == js.ERROR)

j = job_in(js.PROCESSING)
check("report_done aktueller Lauf → einfügen, bereit", j.ereignis("report_done", j.gen) == "einfuegen" and j.zustand == js.READY)
check("zweites report_done → nichts (nur einmal einfügen)", j.ereignis("report_done", j.gen) is None)
j = job_in(js.PROCESSING)
check("kein_text → bereit", j.ereignis("kein_text", j.gen) == "kein_text" and j.zustand == js.READY)
j = job_in(js.PROCESSING)
check("report_failed → Fehler", j.ereignis("report_failed", j.gen) == "fehler" and j.zustand == js.ERROR)
check("Ereignis ohne Generationsnummer aus Thread → verworfen", job_in(js.PROCESSING).ereignis("report_done") is None)
try:
    js.JobState().ereignis("quatsch", 0)
    check("unbekanntes Ereignis → Fehler", False)
except ValueError:
    check("unbekanntes Ereignis → Fehler", True)
j = js.JobState()
g = j.simuliere_verarbeitung()
check("Selbsttest-Simulation: PROCESSING, F10 ignoriert, F9 bricht ab",
      j.zustand == js.PROCESSING and j.vorschau("toggle") is None and j.ereignis("reset") == "abbrechen" and not j.aktuell(g))

# Verdrahtung in RaKScribe.py (die EXE selbst läuft nur unter Windows)
src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("toggle_recording fragt die Zustandsmaschine", 'aktion = self._job.vorschau("toggle")' in src and 'self._job.ereignis("toggle")' in src)
check("reset_dictation fragt die Zustandsmaschine", 'aktion = self._job.ereignis("reset")' in src)
check("Streaming nur in stream_transcript, nie in final_transcript",
      "self.final_transcript +=" not in src and "self.stream_transcript += transcript" in src)
check("Streaming-Callback trägt Generationsnummer", "self.update_interim_text, text, is_final, gen)" in src)
check("Einfügen nur für aktuellen Lauf", 'self._job.ereignis("report_done", gen) is None' in src
      and "self._job.aktuell(gen) and self._einfuegen()" in src)
check("Selbsttest kennt simulate_processing (Fall D)", '"simulate_processing"' in src)
wt = (ROOT / "tests" / "windows" / "exe_ui_test.py").read_text(encoding="utf-8")
check("Windows-UI-Test hat Fall D (F10 während Verarbeitung)", "simulate_processing" in wt and '"D_verarbeitung"' in wt)

print("\n" + ("✅ ZUSTANDSMASCHINE PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
