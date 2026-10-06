"""Live-Test Fehler 4 (Gutachten P1-4): echte Google-APIs, echtes aufnahme.Aufnahme, Mikrofon = Sprachdatei in Echtzeit.

A) Langes Diktat (> 5 min): Live-Anzeige muss nach neustart_s neu aufsetzen statt am Google-Limit abzubrechen;
   chirp_3 über den vollen Puffer liefert den ganzen Text.
B) Verbindungsabbruch der Live-Anzeige nach 20 s (gRPC UNAVAILABLE): Aufnahme läuft weiter, Puffer vollständig,
   chirp_3 liefert den ganzen Text.

Aufruf: /usr/bin/python3 tools/aufnahme_live_test.py [A|B|AB]   PRAXIS_KEY=<rakscribe-praxis-key.json>
Sprachdatei: macOS `say` (Anna), wird nach $TMPDIR erzeugt. Dauer A ≈ Diktatlänge in Echtzeit.
"""
import os, pathlib, subprocess, sys, threading, time, wave
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source_code"))
import aufnahme as af  # noqa: E402
import stt  # noqa: E402
from google.oauth2 import service_account  # noqa: E402
from google.cloud import speech_v1 as speech  # noqa: E402
from google.auth.transport.requests import Request  # noqa: E402

# Schlüssel mit Speech-Rechten (chirp_3): Praxis-Schlüssel, Pfad per PRAXIS_KEY (der Hermes-Testschlüssel darf kein STT)
import json  # noqa: E402
creds = service_account.Credentials.from_service_account_info(json.load(open(os.environ["PRAXIS_KEY"]))["stt"],
                                                              scopes=["https://www.googleapis.com/auth/cloud-platform"])
client = speech.SpeechClient(credentials=creds)
CFG = speech.StreamingRecognitionConfig(config=speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, sample_rate_hertz=16000, language_code="de-DE",
    model="latest_long", use_enhanced=True, enable_automatic_punctuation=True), interim_results=True)
TMP = pathlib.Path(os.environ.get("TMPDIR", "/tmp"))

SATZ = ("Sonographie des Oberbauches. Die Leber ist normal groß und homogen strukturiert ohne fokale Läsion. "
        "Die Gallenblase ist zartwandig und steinfrei. Die Gallenwege sind nicht erweitert. Das Pankreas ist "
        "soweit einsehbar unauffällig. Die Milz ist normal groß. Beide Nieren sind orthotop gelegen, normal groß, "
        "ohne Harnstau und ohne Konkrement. Kein freie Flüssigkeit. ")


def sprachdatei(minuten):
    wav = TMP / f"aufnahme_live_{minuten}.wav"
    if not wav.exists():
        n = max(1, int(minuten * 60 / 22))  # ein Absatz ≈ 22 s
        txt = TMP / "aufnahme_live.txt"
        txt.write_text(" ".join(f"Absatz {i + 1}. {SATZ}" for i in range(n)))
        subprocess.run(["say", "-v", "Anna", "-f", str(txt), "-o", str(wav), "--data-format=LEI16@16000"], check=True)
    with wave.open(str(wav)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


class DateiMikro:
    """sounddevice-Ersatz: spielt die Sprachdatei in Echtzeit in 100-ms-Blöcken ein, danach Stille."""
    audio = None

    class InputStream:
        def __init__(self, device=None, samplerate=16000, channels=1, dtype="int16", callback=None):
            self.cb, self.run = callback, False

        def __enter__(self):
            self.run = True

            def loop():
                a, i, t0 = DateiMikro.audio, 0, time.time()
                while self.run:
                    blk = a[i:i + 1600] if i < len(a) else np.zeros(1600, np.int16)
                    if len(blk) < 1600:
                        blk = np.pad(blk, (0, 1600 - len(blk)))
                    self.cb(blk.reshape(-1, 1), 1600, None, None)
                    i += 1600
                    time.sleep(max(0, t0 + i / 16000 - time.time()))
            self.t = threading.Thread(target=loop, daemon=True)
            self.t.start()
            return self

        def __exit__(self, *a):
            self.run = False
            self.t.join()


def lauf(name, minuten, abbruch_nach=None, neustart_s=af.STREAM_NEUSTART_S):
    audio = sprachdatei(minuten)
    DateiMikro.audio = audio
    dauer = len(audio) / 16000
    ev = {"final": [], "interims": 0, "fehler": [], "cap": []}
    t_start = time.time()

    def streaming(reqs):
        it = client.streaming_recognize(requests=reqs, config=CFG)
        if abbruch_nach is None:
            return it

        def kaputt():
            for r in it:
                if time.time() - t_start > abbruch_nach:
                    from google.api_core.exceptions import ServiceUnavailable
                    raise ServiceUnavailable("simulierter Verbindungsabbruch (Test)")
                yield r
        return kaputt()

    a = af.Aufnahme(DateiMikro, 16000, None, streaming=streaming,
                    request_bauen=lambda b: speech.StreamingRecognizeRequest(audio_content=b),
                    on_text=lambda t, f: ev["final"].append(t) if f else ev.__setitem__("interims", ev["interims"] + 1),
                    on_stream_fehler=lambda e: ev["fehler"].append((round(time.time() - t_start), repr(e)[:120])),
                    on_capture_fehler=lambda e: ev["cap"].append(repr(e)),
                    log=lambda m: print(f"  {time.time() - t_start:6.1f}s {m}", flush=True), neustart_s=neustart_s)
    print(f"== {name}: Diktat {dauer:.0f} s, Neustart alle {neustart_s} s, Abbruch nach {abbruch_nach} s", flush=True)
    a.start()
    while time.time() - t_start < dauer + 1.5:
        time.sleep(0.5)
    a.stop()
    a.warten(timeout_stream=6.0)
    pcm = a.samples()
    aufgenommen = len(pcm) / 16000 if pcm is not None else 0
    creds.refresh(Request())
    t0 = time.time()
    chirp = stt.chirp3_worker(pcm, 16000, "eu", creds.token) or ""
    absaetze = sum(f"absatz {i + 1}" in chirp.lower() or f"absatz {i + 1}." in chirp.lower()
                   for i in range(int(minuten * 60 / 22) or 1))
    soll = max(1, int(minuten * 60 / 22))
    live = " ".join(ev["final"])
    print(f"   Aufnahme {aufgenommen:.0f}/{dauer:.0f} s · Live-Sessions {a.stream_sessions} · Live-Fehler {ev['fehler']} "
          f"· Mikrofon-Fehler {ev['cap']} · Live-Text {len(live)} Z.", flush=True)
    print(f"   chirp_3: {len(chirp)} Z. in {time.time() - t0:.0f} s · Absatz-Nummern erkannt {absaetze}/{soll} · Ende: "
          f"…{chirp[-90:]!r}", flush=True)
    ok = not ev["cap"] and aufgenommen >= dauer - 0.5 and len(chirp) > 0.8 * len(SATZ) * soll and absaetze >= soll - 1
    ok = ok and (bool(ev["fehler"]) if abbruch_nach else (not ev["fehler"] and (dauer < neustart_s or a.stream_sessions >= 2)))
    print(("✅" if ok else "❌"), name, flush=True)
    return ok


if __name__ == "__main__":
    welche = sys.argv[1] if len(sys.argv) > 1 else "AB"
    erg = []
    if "B" in welche:
        erg.append(lauf("B Verbindungsabbruch der Live-Anzeige", 1.5, abbruch_nach=20))
    if "A" in welche:
        erg.append(lauf("A langes Diktat über das Google-Limit", 6.5))
    print("ERGEBNIS:", "PASS" if all(erg) else "FAIL")
    sys.exit(0 if all(erg) else 1)
