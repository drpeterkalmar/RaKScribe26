"""Aufnahme getrennt von der Streaming-Live-Anzeige (Umbau Schritt 6, Gutachten P1-4).

Vorher liefen Mikrofon-Stream und Google-Antwortschleife im selben with-Block: jeder Fehler der Live-Anzeige
(Netzwerk-Hänger, gRPC-Abbruch, spätestens das ~5-Minuten-Limit eines Streaming-Requests) schloss das Mikrofon und
verwarf das Diktat. Jetzt:
- Capture-Thread: nur sounddevice → Puffer (vollständig, für chirp_3 beim Stopp).
- Streaming-Thread: nur Live-Anzeige. Fehler → on_stream_fehler (Log + Hinweis), die Aufnahme läuft weiter.
  Nach STREAM_NEUSTART_S Sekunden wird der Streaming-Request neu aufgesetzt (Google-Limit ~5 min).

v3.8.0 (SpeechMike-Pause, Peter 11.10.): pausieren() verwirft ab sofort das Audio (das Mikrofon bleibt offen → „Weiter“
ohne Anlaufzeit, kein abgeschnittenes erstes Wort) und beendet die Streaming-Sitzung, sobald ihr Rest verschickt ist
(Google bricht eine Sitzung nach ~10 s ohne Audio ab). fortsetzen() beginnt einen neuen Abschnitt mit eigener Sitzung.
Der Puffer enthält nur die aufgenommenen Abschnitte, lückenlos hintereinander → chirp_3 über die ganze Aufnahme wie bisher.

Ohne Windows/Google importierbar: sounddevice, Streaming-Aufruf und Request-Bau werden übergeben
(tests/offline/test_capture.py stubbt sie).
"""
import threading
import time

import numpy as np

STREAM_NEUSTART_S = 240


class Aufnahme:
    def __init__(self, sd, samplerate, device, streaming, request_bauen, on_level=None, on_text=None,
                 on_stream_fehler=None, on_capture_fehler=None, log=None, neustart_s=STREAM_NEUSTART_S):
        self.sd, self.samplerate, self.device = sd, samplerate, device
        self.streaming, self.request_bauen = streaming, request_bauen
        self.on_level = on_level or (lambda rms: None)
        self.on_text = on_text or (lambda text, is_final: None)
        self.on_stream_fehler = on_stream_fehler or (lambda e: None)
        self.on_capture_fehler = on_capture_fehler or (lambda e: None)
        self.log = log or (lambda *a: None)
        self.neustart_s = neustart_s
        self.puffer = []            # ALLE Audio-Blöcke (int16) — Grundlage für chirp_3
        self._queue = []            # (Abschnitt, Block) noch nicht an die Live-Anzeige geschickt
        self._n = 0                 # Samples im Puffer
        self.pausiert = False       # v3.8.0: SpeechMike-Pause — Audio wird verworfen
        self.abschnitt = 0          # Nummer des laufenden Abschnitts (steigt bei fortsetzen())
        self._abschnitt_start = 0   # Sample-Index, an dem der laufende Abschnitt beginnt
        self.stream_abschnitt = 0   # Abschnitt der laufenden Streaming-Sitzung (für die Anzeige)
        self._lock = threading.Lock()
        self.laeuft = False         # Mikrofon soll aufnehmen
        self.streaming_aktiv = True  # Live-Anzeige läuft (False nach Fehler)
        self.stream_sessions = 0
        self.capture_thread = None
        self.stream_thread = None
        self._erster_callback = False

    # ── Steuerung ──────────────────────────────────────────────────────────────────────────────────────────
    def start(self):
        self.laeuft = True
        self.capture_thread = threading.Thread(target=self._capture, daemon=True)
        self.stream_thread = threading.Thread(target=self._streaming, daemon=True)
        self.capture_thread.start()
        self.stream_thread.start()

    def stop(self):
        """Mikrofon zu (der Capture-Thread schließt den Stream); die Live-Anzeige schickt den Rest noch ab."""
        self.laeuft = False

    def pausieren(self):
        """SpeechMike-Pause: ab jetzt nichts mehr aufnehmen. Rückgabe (abschnitt, start, ende) des eben beendeten
        Abschnitts als Sample-Indizes im Puffer (für die sofortige Reparatur des bisherigen Diktats)."""
        with self._lock:
            self.pausiert = True
            return self.abschnitt, self._abschnitt_start, self._n

    def fortsetzen(self):
        """Weiter diktieren in dieselbe Aufnahme: neuer Abschnitt, neue Streaming-Sitzung."""
        with self._lock:
            if not self.pausiert:
                return
            self.abschnitt += 1
            self._abschnitt_start = self._n
            self.pausiert = False

    def warten(self, timeout_stream=6.0):
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        if self.stream_thread:
            self.stream_thread.join(timeout=timeout_stream)

    def samples(self):
        """Vollständige Aufnahme als int16-Array (oder None)."""
        with self._lock:
            bloecke = list(self.puffer)
        return np.concatenate(bloecke, axis=0) if bloecke else None

    # ── Capture-Thread ─────────────────────────────────────────────────────────────────────────────────────
    def _callback(self, indata, frames, time_info, status):
        if not self.laeuft:
            return
        block = indata.copy()
        with self._lock:
            if self.pausiert:
                return  # v3.8.0: Pause — Mikrofon offen, Audio verwerfen
            self.puffer.append(block)
            self._n += len(block)
            if self.streaming_aktiv:
                self._queue.append((self.abschnitt, block))
        rms = float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))
        if not self._erster_callback:
            self._erster_callback = True
            self.log(f"[AUDIO] Erster Audio-Callback empfangen. RMS-Pegel: {rms:.2f}")
        self.on_level(rms)

    def _capture(self):
        try:
            self.log(f"[RECORD] Öffne sounddevice InputStream. Device Index: {self.device}")
            stream = self.sd.InputStream(device=self.device, samplerate=self.samplerate, channels=1, dtype='int16',
                                         callback=self._callback)
            with stream:
                self.log("[RECORD] Mikrofon aktiv.")
                while self.laeuft:
                    time.sleep(0.02)
            self.log("[RECORD] Mikrofon geschlossen.")
        except Exception as e:
            self.laeuft = False
            self.on_capture_fehler(e)

    # ── Streaming-Thread (nur Live-Anzeige) ────────────────────────────────────────────────────────────────
    def _requests(self, ende, abschnitt=0):
        """Pakete EINES Abschnitts. Ende: Zeitlimit (Rest geht in die nächste Sitzung), Stopp oder Pause (eigener Rest
        ist verschickt). Blöcke eines späteren Abschnitts bleiben für dessen Sitzung in der Warteschlange."""
        n = 0
        while True:
            aktiv = self.laeuft and not self.pausiert and self.abschnitt == abschnitt
            if aktiv and time.time() >= ende:
                break
            with self._lock:
                i = 0
                while i < len(self._queue) and self._queue[i][0] == abschnitt:
                    i += 1
                bloecke = [b for _, b in self._queue[:i]]
                del self._queue[:i]
            if bloecke:
                n += 1
                yield self.request_bauen(np.concatenate(bloecke, axis=0).tobytes())
            elif not aktiv:
                break
            else:
                time.sleep(0.02)
        self.log(f"[GOOGLE] Streaming-Request beendet ({n} Pakete).")

    def _streaming(self):
        while self.streaming_aktiv and (self.laeuft or self._queue):
            if not self._queue and self.pausiert:
                time.sleep(0.05)  # v3.8.0: in der Pause keine leere Sitzung offen halten
                continue
            with self._lock:
                abschnitt = self._queue[0][0] if self._queue else self.abschnitt
            self.stream_abschnitt = abschnitt
            self.stream_sessions += 1
            try:
                for response in self.streaming(self._requests(time.time() + self.neustart_s, abschnitt)):
                    if not response.results:
                        continue
                    result = response.results[0]
                    if not result.alternatives:
                        continue
                    self.on_text(result.alternatives[0].transcript, result.is_final)
            except Exception as e:
                with self._lock:
                    self.streaming_aktiv = False
                    self._queue = []
                self.on_stream_fehler(e)
                return
            if self.laeuft and not self.pausiert and self.abschnitt == abschnitt:
                self.log(f"[GOOGLE] Live-Anzeige nach {self.neustart_s}s neu aufgesetzt (Google-Limit ~5 min).")
