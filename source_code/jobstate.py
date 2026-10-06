"""Aufnahme- und Verarbeitungszustand der EXE als reine Zustandsmaschine (Umbau Schritt 4; Gutachten P1-2, P2-5).

Ohne UI und ohne Windows-Module importierbar (tests/offline/test_jobstate.py). RaKScribe.py fragt die Maschine, bevor
es auf F10/F9 reagiert, und jeder Hintergrund-Thread (Streaming-Anzeige, chirp_3, Befund) trägt die Generationsnummer
seines Laufs mit. Ereignisse mit alter Nummer werden verworfen: ein abgebrochener oder überholter Lauf schreibt nichts
mehr in die Oberfläche und fügt nichts ein.

Regeln (v3.2.3, Peter 06.10.):
- F10 (toggle) während „Befund wird erstellt" (PROCESSING) → ignorieren.
- F9 (reset) während der Verarbeitung → Lauf abbrechen (Ergebnis wird verworfen), sofort wieder bereit.
- Streaming-Text (Live-Anzeige) wird nur angenommen, solange der chirp_3-Endtext noch nicht feststeht.
"""

READY = "READY"
RECORDING = "RECORDING"
PROCESSING = "PROCESSING"
ERROR = "ERROR"
LOCKED = "LOCKED"

# Ereignisse aus der Oberfläche (ohne Generationsnummer)
UI_EREIGNISSE = ("toggle", "reset")
# Ereignisse aus Hintergrund-Threads (immer mit Generationsnummer)
LAUF_EREIGNISSE = ("stream_interim", "stream_final", "chirp_done", "report_done", "report_failed", "kein_text",
                   "capture_failed")


class JobState:
    def __init__(self, log=None):
        self.zustand = READY
        self.gen = 0            # Generationsnummer des aktuellen Laufs (Aufnahme + Verarbeitung)
        self.text_fix = False   # Endtext steht (chirp_3 oder gerettet) → keine Streaming-Antworten mehr übernehmen
        self._log = log or (lambda *a: None)

    def aktuell(self, gen):
        return gen == self.gen

    def vorschau(self, name, gen=None):
        """Aktion, die ereignis(name, gen) auslösen würde — ohne den Zustand zu ändern. None = ignorieren."""
        z = self.zustand
        if name == "toggle":
            if z in (PROCESSING, LOCKED):
                return None
            return "stop" if z == RECORDING else "start"
        if name == "reset":
            return {RECORDING: "stop_und_reset", PROCESSING: "abbrechen"}.get(z, "reset")
        if name not in LAUF_EREIGNISSE:
            raise ValueError(f"unbekanntes Ereignis {name!r}")
        if gen is None or gen != self.gen:
            return None
        if name in ("stream_interim", "stream_final"):
            return "anzeigen" if z in (RECORDING, PROCESSING) and not self.text_fix else None
        if name == "capture_failed":
            return "fehler" if z == RECORDING else None
        if z != PROCESSING:
            return None
        return {"chirp_done": "uebernehmen", "report_done": "einfuegen", "report_failed": "fehler",
                "kein_text": "kein_text"}[name]

    def ereignis(self, name, gen=None):
        """Wendet ein Ereignis an. Rückgabe = Aktion für die Oberfläche oder None (= ignorieren, wird geloggt)."""
        aktion = self.vorschau(name, gen)
        if aktion is None:
            if name in UI_EREIGNISSE or gen == self.gen:
                self._log(f"[JOB] {name} im Zustand {self.zustand} ignoriert.")
            else:
                self._log(f"[JOB] {name} aus altem Lauf {gen} (aktuell {self.gen}) verworfen.")
            return None
        if aktion == "start":
            self.gen += 1
            self.zustand, self.text_fix = RECORDING, False
        elif aktion == "stop":
            self.zustand = PROCESSING
        elif name == "reset":
            self.gen += 1  # laufende Aufnahme/Verarbeitung wird ungültig
            self.text_fix = False
            if self.zustand != LOCKED:
                self.zustand = READY
        elif aktion == "uebernehmen":
            self.text_fix = True
        elif aktion in ("einfuegen", "kein_text"):
            self.zustand = READY
        elif aktion == "fehler":
            self.zustand = ERROR
        return aktion

    def sperren(self):
        """Schlüssel fehlt: nur im Ruhezustand sperren (laufende Aufnahme/Verarbeitung nicht abwürgen)."""
        if self.zustand in (READY, ERROR):
            self.zustand = LOCKED

    def entsperren(self):
        if self.zustand == LOCKED:
            self.zustand = READY

    def simuliere_verarbeitung(self):
        """Nur für den Windows-Selbsttest (RAKSCRIBE_SELFTEST): Zustand „Befund wird erstellt" ohne Aufnahme."""
        self.gen += 1
        self.zustand, self.text_fix = PROCESSING, False
        return self.gen
