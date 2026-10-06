"""Gate (Umbau Schritt 6, Gutachten P1-4): Mikrofon-Aufnahme getrennt von der Streaming-Live-Anzeige.
Gestubbtes sounddevice + Streaming-Stub, der nach 2 Antworten wirft → Puffer trotzdem vollständig.
Der Stopp-Pfad der EXE (chirp_3 über den ganzen Puffer) ist in test_exe_ablauf.py Fall 7 geprüft.
Aufruf: /usr/bin/python3 tests/offline/test_capture.py"""
import pathlib, sys, time
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "source_code"))
import numpy as np  # noqa: E402
import aufnahme as af  # noqa: E402
import exe_stubs as S  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


def warte(bed, timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout and not bed():
        time.sleep(0.005)
    return bed()


class SD:
    InputStream = S.FakeInputStream


def baue(streaming, **kw):
    ev = {"text": [], "stream_fehler": [], "capture_fehler": [], "pakete": [], "angenommen": 0}

    def req(b):
        ev["pakete"].append(len(b) // 2)
        return b
    a = af.Aufnahme(SD, 16000, 0, streaming=streaming, request_bauen=req,
                    on_text=lambda t, f: ev["text"].append((t, f)),
                    on_stream_fehler=lambda e: ev["stream_fehler"].append(e),
                    on_capture_fehler=lambda e: ev["capture_fehler"].append(e), **kw)
    orig = a._callback

    def zaehlend(indata, frames, t, status):
        if a.laeuft:
            ev["angenommen"] += 1
        orig(indata, frames, t, status)
    a._callback = zaehlend
    return a, ev


# 1. Streaming wirft nach 2 Antworten
a, ev = baue(S.streaming_stub(fehler_nach=2))
a.start()
check("Live-Anzeige-Fehler wird gemeldet", warte(lambda: ev["stream_fehler"]))
n_fehler = len(a.puffer)
check("Aufnahme läuft nach dem Fehler weiter", warte(lambda: len(a.puffer) >= n_fehler + 20) and a.laeuft)
a.stop(); a.warten()
check("genau 2 Live-Antworten angezeigt, 1 Fehler", len(ev["text"]) == 2 and len(ev["stream_fehler"]) == 1)
check("Puffer vollständig (jeder angenommene Block drin)", len(a.puffer) == ev["angenommen"] > 0,
      f"{len(a.puffer)} vs {ev['angenommen']}")
pcm = a.samples()
erwartet = np.concatenate([np.full((1600, 1), i, dtype=np.int16) for i in range(len(a.puffer))])
check("samples() = alle Blöcke in Reihenfolge", pcm is not None and np.array_equal(pcm, erwartet))
check("nach Fehler keine Live-Pakete mehr gesammelt", a._queue == [] and not a.streaming_aktiv)

# 2. ohne Fehler: alles geht an die Live-Anzeige, Rest wird nach dem Stopp noch geschickt
a, ev = baue(S.streaming_stub())
a.start()
warte(lambda: len(a.puffer) >= 30)
a.stop(); a.warten()
check("ohne Fehler: jedes Sample an die Live-Anzeige", sum(ev["pakete"]) == 1600 * len(a.puffer) > 0,
      f"{sum(ev['pakete'])} vs {1600 * len(a.puffer)}")
check("Streaming-Thread beendet sich nach dem Stopp", not a.stream_thread.is_alive() and not a.capture_thread.is_alive())

# 3. Neu-Aufsetzen nach Zeitlimit (Google ~5 min; hier 50 ms)
a, ev = baue(S.streaming_stub(), neustart_s=0.05)
a.start()
check("Streaming wird nach dem Zeitlimit neu aufgesetzt", warte(lambda: a.stream_sessions >= 3))
a.stop(); a.warten()
check("… ohne Audio zu verlieren", sum(ev["pakete"]) == 1600 * len(a.puffer), f"{sum(ev['pakete'])} vs {1600 * len(a.puffer)}")
check("Standard-Zeitlimit 240 s", af.STREAM_NEUSTART_S == 240)


# 4. Mikrofon lässt sich nicht öffnen
class SDkaputt:
    @staticmethod
    def InputStream(**k):
        raise OSError("Kein Eingabegerät")


ev2 = {"capture": []}
a = af.Aufnahme(SDkaputt, 16000, 0, streaming=S.streaming_stub(), request_bauen=lambda b: b,
                on_capture_fehler=lambda e: ev2["capture"].append(e))
a.start(); a.warten()
check("Mikrofon-Fehler → on_capture_fehler, Aufnahme beendet", len(ev2["capture"]) == 1 and not a.laeuft)
check("… keine Samples", a.samples() is None)

src = (HERE.parents[1] / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE nutzt aufnahme.Aufnahme, kein gemeinsamer with-Block mehr",
      "_af.Aufnahme(" in src and "def record(" not in src and "with self.stream:" not in src)

print("\n" + ("✅ AUFNAHME PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
