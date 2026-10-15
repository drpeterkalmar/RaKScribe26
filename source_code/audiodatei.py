"""v3.16.0 (Peter 15.10.2026): Audio-Datei statt Mikrofon — ohne Windows/Tk importierbar (tests/offline/test_audiodatei.py).

1. „Audio laden“ (Knopf im Diktat-Kopf): wav/mp3/m4a/ogg/opus (auch Telegram-Sprachnachrichten) → 16 kHz mono int16 →
   DIESELBE Kette wie nach einer Aufnahme (chirp_3 → Fehlhör-Liste → Befund mit Gemini), Ergebnis rechts zur Kontrolle,
   EOL wie gewohnt (mit CAS-Auftrag geht die Datei als <Nr>.wav an die Brücke). Wie der Upload der Web-App
   (web_app/src/App.tsx audioUploadRef/decodeFileToWavBlob).
2. WAV-Modus für die Automation (rakscribe26.exe --wav-ablauf <ablauf.json> [--schluessel <key.json>]): statt des
   Mikrofons spielt WavQuelle Audio-Dateien in Echtzeit-Blöcken (100 ms) ein, sonst Stille; Google-Streaming, chirp_3 und
   Gemini bleiben ECHT. Die SpeechMike-Tasten drückt ein Ablaufskript (Ablauf/AblaufLaeufer) über denselben Dekodierer
   wie das Gerät; RaKScribe beendet sich am Ende selbst. Läuft immer als Gast (eigener Mutex, kein Gerät, keine globalen
   Tasten, kein Autostart, keine Zwischenablage, kein Strg+V, keine Dialoge) — eine laufende RaKScribe bleibt unberührt.

Ablaufskript (JSON): {"schritte": [...], "max_s": 900}, je Schritt GENAU ein Schlüssel:
  {"taste": "RECORD"}                SpeechMike-Taste (RECORD, STOP, PLAY, FF, REW, EOL, INS, COMMAND, F1–F4, INSTR)
  {"sprich": "lws.wav"}              Datei einspielen (Pfad relativ zum Ablaufskript) und warten, bis sie gespielt ist
  {"warte_s": 2}                     warten
  {"warte_auf": "kontrolle", "timeout_s": 180}   Zustand abwarten (BEDINGUNGEN); Zeitgrenze → Ablauf bricht ab
  {"trigger": "maske_markieren#0|0|7"}           Selbsttest-Phase (wie <state>.trigger: markieren, Gerät, Tippen …)
  {"merke": "nach_ins"}              Zustand der Oberfläche unter diesem Namen festhalten (Selbsttest-JSON)
  {"fehler": "stt" | "ki" | "aus"}   Netz-/Spracherkennungs- bzw. KI-Ausfall simulieren (E2E-Fehlerfall)
  {"ende": true}                     RaKScribe schließen (offener CAS-Auftrag → „abgebrochen“ wie mit X)
"""
import json
import os
import threading
import time
import types
import wave

import numpy as np

ZIEL_SR = 16000
BLOCK_S = 0.1
ENDUNGEN = (".wav", ".mp3", ".m4a", ".mp4", ".aac", ".ogg", ".oga", ".opus", ".flac", ".webm")
DATEI_TYPEN = [("Audio (wav, mp3, m4a, ogg, opus)", " ".join("*" + e for e in ENDUNGEN)), ("Alle Dateien", "*.*")]
TASTEN = ("RECORD", "STOP", "PLAY", "FF", "REW", "EOL", "INS", "COMMAND", "F1", "F2", "F3", "F4", "INSTR")
BEDINGUNGEN = ("cas", "leistungen", "kontext", "maske", "aufnahme", "bereit", "kontrolle", "kein_cas", "fertig")
ARTEN = ("taste", "sprich", "warte_s", "warte_auf", "trigger", "merke", "fehler", "ende")
FEHLER_ARTEN = ("stt", "ki", "aus")


class AudioFehler(Exception):
    """Datei nicht lesbar — der Text geht so in die Meldung an den Benutzer."""


# ── Lesen + Umrechnen ──────────────────────────────────────────────────────────────────────────────────────────────
def _wav_lesen(pfad):
    """PCM-WAV (8/16/24/32 bit, auch WAVE_FORMAT_EXTENSIBLE) → (float32 [Samples, Kanäle], Rate) oder None."""
    try:
        with wave.open(pfad, "rb") as w:
            kanaele, breite, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            roh = w.readframes(n)
    except (wave.Error, EOFError):
        return None             # z. B. Float-WAV oder Philips-CELP → nächster Leser
    if breite == 1:
        x = (np.frombuffer(roh, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif breite == 2:
        x = np.frombuffer(roh, dtype="<i2").astype(np.float32) / 32768.0
    elif breite == 3:
        b = np.frombuffer(roh, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        x = (np.where(v >= 1 << 23, v - (1 << 24), v)).astype(np.float32) / float(1 << 23)
    elif breite == 4:
        x = np.frombuffer(roh, dtype="<i4").astype(np.float32) / float(1 << 31)
    else:
        return None
    return x.reshape(-1, kanaele), sr


def _soundfile_lesen(pfad):
    """ogg/opus/mp3/flac (und Float-WAV) über libsndfile (Paket soundfile, in der EXE gebündelt)."""
    try:
        import soundfile as sf
    except Exception:
        return None
    try:
        x, sr = sf.read(pfad, dtype="float32", always_2d=True)
    except Exception:
        return None
    return x, sr


def _av_lesen(pfad):
    """m4a/mp4/aac/webm, falls PyAV installiert ist (in der EXE nicht gebündelt — Web-App kann m4a immer)."""
    try:
        import av
    except Exception:
        return None
    try:
        teile, sr = [], None
        with av.open(pfad) as c:
            s = c.streams.audio[0]
            res = av.AudioResampler(format="flt", layout="mono", rate=ZIEL_SR)
            for frame in c.decode(s):
                for f in res.resample(frame):
                    teile.append(f.to_ndarray().reshape(-1))
            sr = ZIEL_SR
        if not teile:
            return None
        return np.concatenate(teile).astype(np.float32).reshape(-1, 1), sr
    except Exception:
        return None


def umrechnen(x, sr, ziel=ZIEL_SR):
    """float32 mono, Rate sr → ziel. Abwärts mit Tiefpass (gefenstertes sinc), dann lineare Interpolation."""
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if sr == ziel or len(x) == 0:
        return x
    if sr > ziel:
        grenze = 0.45 * ziel / sr                      # Grenzfrequenz relativ zur Abtastrate (knapp unter Nyquist)
        taps = int(min(129, 16 * sr / ziel)) | 1
        n = np.arange(taps) - (taps - 1) / 2
        h = 2 * grenze * np.sinc(2 * grenze * n) * np.hamming(taps)
        x = np.convolve(x, (h / h.sum()).astype(np.float32), mode="same")
    laenge = int(round(len(x) * ziel / sr))
    t = np.arange(laenge, dtype=np.float64) * (sr / ziel)
    return np.interp(t, np.arange(len(x), dtype=np.float64), x).astype(np.float32)


def lesen(pfad, ziel_sr=ZIEL_SR):
    """Audio-Datei → int16-Array (mono, ziel_sr). Wirft AudioFehler mit verständlichem Text."""
    if not pfad or not os.path.isfile(pfad):
        raise AudioFehler(f"Audio-Datei nicht gefunden:\n{pfad}")
    endung = os.path.splitext(pfad)[1].lower()
    erg = _wav_lesen(pfad) if endung == ".wav" else None
    for leser in (_soundfile_lesen, _av_lesen):
        if erg is None:
            erg = leser(pfad)
    if erg is None:
        tipp = (" m4a/AAC kann die Desktop-App nicht öffnen — bitte als mp3, ogg oder wav speichern oder die Web-App "
                "nehmen." if endung in (".m4a", ".mp4", ".aac") else "")
        raise AudioFehler(f"Audio-Datei nicht lesbar ({endung or 'ohne Endung'}).{tipp}")
    x, sr = erg
    if x.size == 0:
        raise AudioFehler("Die Audio-Datei ist leer.")
    mono = x.mean(axis=1) if x.ndim == 2 else x
    y = umrechnen(mono, sr, ziel_sr)
    return (np.clip(y, -1.0, 1.0) * 32767.0).astype(np.int16)


def wav_schreiben(pfad, pcm, sr=ZIEL_SR):
    """int16 mono → PCM-WAV (für Tests und das Ablage-Format der Brücke)."""
    with wave.open(pfad, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.asarray(pcm, dtype="<i2").tobytes())


class DateiAufnahme:
    """Geladene Datei an Stelle einer aufnahme.Aufnahme (für chirp_3 und die <Nr>.wav der Brücke)."""

    def __init__(self, pcm):
        self._pcm = np.asarray(pcm, dtype=np.int16).reshape(-1, 1)

    def samples(self):
        return self._pcm

    def warten(self, timeout_stream=0.0):
        return None

    def stop(self):
        return None


# ── WAV-Modus: Mikrofon-Ersatz ─────────────────────────────────────────────────────────────────────────────────────
class WavQuelle:
    """sounddevice-Ersatz (InputStream, default, query_devices): spielt eingereihte Audio-Blöcke in Echtzeit, sonst Stille.
    Die Blöcke laufen genau so durch aufnahme.Aufnahme (Puffer für chirp_3, Live-Anzeige mit Google-Streaming)."""

    def __init__(self, sr=ZIEL_SR, block_s=BLOCK_S, echtzeit=True, log=None):
        self.sr, self.block = sr, max(1, int(round(sr * block_s)))
        self.block_s, self.echtzeit = block_s, echtzeit
        self.log = log or (lambda *a: None)
        self.default = types.SimpleNamespace(device=[0, 0])
        self._lock = threading.Lock()
        self._rest = []               # eingereihte int16-Arrays
        self.gespielt_s = 0.0         # nur Datei-Audio, ohne Stille
        self.offen = 0                # laufende InputStreams

    def query_devices(self):
        return [{"name": "WAV-Modus (Audio-Datei statt Mikrofon)", "max_input_channels": 1}]

    def einspielen(self, pcm):
        with self._lock:
            self._rest.append(np.asarray(pcm, dtype=np.int16).reshape(-1))

    def rest_s(self):
        with self._lock:
            return sum(len(a) for a in self._rest) / float(self.sr)

    def leeren(self):
        with self._lock:
            self._rest = []

    def naechster_block(self):
        out = np.zeros(self.block, dtype=np.int16)
        n = 0
        with self._lock:
            while n < self.block and self._rest:
                a = self._rest[0]
                k = min(self.block - n, len(a))
                out[n:n + k] = a[:k]
                n += k
                if k == len(a):
                    self._rest.pop(0)
                else:
                    self._rest[0] = a[k:]
            self.gespielt_s += n / float(self.sr)
        return out

    def InputStream(self, device=None, samplerate=ZIEL_SR, channels=1, dtype="int16", callback=None):  # noqa: N802
        return _Strom(self, callback)


class _Strom:
    def __init__(self, quelle, callback):
        self.q, self.cb, self._an, self._t = quelle, callback, False, None

    def __enter__(self):
        self._an = True
        self.q.offen += 1

        def lauf():
            t0, i = time.monotonic(), 0
            while self._an:
                b = self.q.naechster_block()
                try:
                    self.cb(b.reshape(-1, 1), len(b), None, None)
                except Exception as e:      # wie sounddevice: Fehler im Callback beenden den Strom nicht still
                    self.q.log(f"[WAV] Fehler im Audio-Callback: {e}")
                i += 1
                if self.q.echtzeit:
                    warte = t0 + i * self.q.block_s - time.monotonic()
                    if warte > 0:
                        time.sleep(warte)
        self._t = threading.Thread(target=lauf, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *a):
        self._an = False
        if self._t is not None:
            self._t.join(timeout=2.0)
        self.q.offen = max(0, self.q.offen - 1)


# ── Ablaufskript ───────────────────────────────────────────────────────────────────────────────────────────────────
class AblaufFehler(Exception):
    pass


def ablauf_pruefen(daten, basis=""):
    """JSON-Inhalt prüfen und normalisieren → {"schritte": [(art, wert, extra)], "max_s": float}. Wirft AblaufFehler."""
    if isinstance(daten, list):
        daten = {"schritte": daten}
    if not isinstance(daten, dict) or not isinstance(daten.get("schritte"), list) or not daten["schritte"]:
        raise AblaufFehler("Ablauf: Liste „schritte“ fehlt oder ist leer")
    out = []
    for i, s in enumerate(daten["schritte"], 1):
        if not isinstance(s, dict):
            raise AblaufFehler(f"Schritt {i}: kein Objekt")
        arten = [k for k in s if k in ARTEN]
        if len(arten) != 1:
            raise AblaufFehler(f"Schritt {i}: genau einer von {', '.join(ARTEN)} erwartet, nicht {sorted(s)}")
        art = arten[0]
        wert = s[art]
        extra = {k: v for k, v in s.items() if k != art}
        if art == "taste":
            wert = str(wert).upper()
            if wert not in TASTEN:
                raise AblaufFehler(f"Schritt {i}: unbekannte Taste {s[art]!r}")
        elif art == "sprich":
            wert = str(wert)
            if not os.path.isabs(wert):
                wert = os.path.join(basis, wert)
            if not os.path.isfile(wert):
                raise AblaufFehler(f"Schritt {i}: Audio-Datei fehlt: {wert}")
        elif art == "warte_s":
            wert = float(wert)
        elif art == "warte_auf":
            if wert not in BEDINGUNGEN:
                raise AblaufFehler(f"Schritt {i}: unbekannte Bedingung {wert!r} (bekannt: {', '.join(BEDINGUNGEN)})")
            extra["timeout_s"] = float(extra.get("timeout_s", 120))
        elif art == "fehler":
            if wert not in FEHLER_ARTEN:
                raise AblaufFehler(f"Schritt {i}: fehler = {' | '.join(FEHLER_ARTEN)}")
        elif art in ("trigger", "merke"):
            wert = str(wert)
        out.append((art, wert, extra))
    return {"schritte": out, "max_s": float(daten.get("max_s", 900))}


def ablauf_laden(pfad):
    try:
        with open(pfad, encoding="utf-8-sig") as f:
            daten = json.load(f)
    except (OSError, ValueError) as e:
        raise AblaufFehler(f"Ablauf nicht lesbar: {e}")
    return ablauf_pruefen(daten, os.path.dirname(os.path.abspath(pfad)))


class AblaufLaeufer:
    """Arbeitet ein geprüftes Ablaufskript ab (eigener Thread). aktionen = Rückrufe der App, alle synchron:
    taste(name), trigger(phase), merke(name), bedingung(name) → bool, fehler(art), ende(). Jede Datei wird vor dem
    Einspielen gelesen (lesen()), d. h. auch mp3/ogg gehen. protokoll = je Schritt {nr, art, wert, t_s, dauer_s, ok}."""

    def __init__(self, ablauf, quelle, aktionen, log=None, jetzt=time.monotonic, schlafen=time.sleep, takt_s=0.2):
        self.ablauf, self.q, self.a = ablauf, quelle, aktionen
        self.log = log or (lambda *a: None)
        self.jetzt, self.schlafen, self.takt_s = jetzt, schlafen, takt_s
        self.protokoll, self.fehler, self.fertig = [], "", False
        self._t0 = None

    def _warte_bis(self, bed, timeout_s):
        ende = self.jetzt() + timeout_s
        while True:
            if bed():
                return True
            if self.jetzt() >= ende:
                return False
            self.schlafen(self.takt_s)

    def _schritt(self, art, wert, extra):
        if art == "taste":
            self.a["taste"](wert)
            self.schlafen(float(extra.get("danach_s", 0.6)))   # Taste drücken wie ein Mensch, Oberfläche reagiert
            return True, ""
        if art == "sprich":
            pcm = lesen(wert, self.q.sr)
            if not self.q.offen:
                return False, "keine Aufnahme offen (erst RECORD)"
            self.q.einspielen(pcm)
            dauer = len(pcm) / float(self.q.sr)
            ok = self._warte_bis(lambda: self.q.rest_s() <= 0 or not self.q.offen, dauer + 30)
            self.schlafen(float(extra.get("danach_s", 0.8)))   # Ausklang (Stille), wie eine Atempause vor der Taste
            return ok, f"{dauer:.1f} s" + ("" if ok else " – nicht zu Ende gespielt")
        if art == "warte_s":
            self.schlafen(wert)
            return True, ""
        if art == "warte_auf":
            ok = self._warte_bis(lambda: self.a["bedingung"](wert), extra["timeout_s"])
            return ok, "" if ok else f"Zeitgrenze {extra['timeout_s']:g} s"
        if art == "trigger":
            self.a["trigger"](wert)
            self.schlafen(float(extra.get("danach_s", 0.8)))
            return True, ""
        if art == "merke":
            self.a["merke"](wert)
            return True, ""
        if art == "fehler":
            self.a["fehler"](wert)
            return True, ""
        return True, ""                        # ende: am Schluss

    def lauf(self):
        self._t0 = self.jetzt()
        ende_bei = self._t0 + self.ablauf["max_s"]
        try:
            for nr, (art, wert, extra) in enumerate(self.ablauf["schritte"], 1):
                if art == "ende":
                    break
                if self.jetzt() > ende_bei:
                    self.fehler = f"max_s {self.ablauf['max_s']:g} s überschritten vor Schritt {nr}"
                    break
                t = self.jetzt()
                try:
                    ok, info = self._schritt(art, wert, extra)
                except Exception as e:
                    ok, info = False, f"{type(e).__name__}: {e}"
                anzeige = os.path.basename(wert) if art == "sprich" else wert
                self.protokoll.append({"nr": nr, "art": art, "wert": anzeige, "t_s": round(t - self._t0, 2),
                                       "dauer_s": round(self.jetzt() - t, 2), "ok": ok, "info": info})
                self.log(f"[WAV] Schritt {nr} {art} {anzeige}: {'ok' if ok else 'FEHLER'}"
                         + (f" ({info})" if info else "") + f" – {self.jetzt() - t:.1f} s")
                if not ok:
                    self.fehler = f"Schritt {nr} ({art} {anzeige}): {info}"
                    break
        finally:
            self.fertig = True
            self.log("[WAV] Ablauf " + ("fertig" if not self.fehler else "abgebrochen: " + self.fehler)
                     + f" nach {self.jetzt() - self._t0:.1f} s – RaKScribe wird geschlossen.")
            self.a["ende"]()
