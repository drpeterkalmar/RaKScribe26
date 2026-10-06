"""EXE-Zustandslogik ohne UI (v3.2.3, Gutachten 05.10. P1-1/P1-2) — importierbar und auf dem Mac testbar.

P1-1: Zwischenablage robust setzen. Windows-OpenClipboard schlägt fehl, solange ein anderes Programm (RIS, Teams,
      Zwischenablage-Manager) die Zwischenablage hält. Früher wurde der Fehler verschluckt und trotzdem Strg+V
      gedrückt → der VORIGE Befund landete im RIS. Jetzt: mehrere Versuche, Gegenlesen, und nur bei Erfolg einfügen.
P1-2: Aufnahme-Zustand. F10 während „Befund wird erstellt" startete eine neue Aufnahme in den laufenden Job hinein.
      Jetzt: F10 wird während der Verarbeitung ignoriert; F9 bricht die Verarbeitung ab (Ergebnis wird verworfen,
      nichts eingefügt). Jeder Lauf trägt eine Lauf-Nummer; ein veralteter Lauf schreibt nichts mehr.
"""
# Zwischenablage-Logik liegt seit dem Umbau (Schritt 3) in clipboard_win.py — hier nur weitergereicht.
from clipboard_win import VERSUCHE, PAUSE_S, zwischenablage_setzen  # noqa: F401


# ── Aufnahme-Zustand ────────────────────────────────────────────────────────────────────────────────────
# Status-Werte wie in RaKScribe.py (_status_raw): LOCKED, READY, RECORDING, PROCESSING, ERROR, COPIED
def f10_aktion(status, is_recording):
    """Was F10/Aufnahme-Button tun soll: 'start', 'stop' oder 'ignorieren'."""
    if is_recording:
        return "stop"
    if status == "PROCESSING":
        return "ignorieren"
    return "start"


def f9_aktion(status, is_recording):
    """Was F9/Neu tun soll: 'stop_und_reset' (läuft Aufnahme), 'abbrechen' (Verarbeitung läuft), 'reset'."""
    if is_recording:
        return "stop_und_reset"
    if status == "PROCESSING":
        return "abbrechen"
    return "reset"


class LaufZaehler:
    """Lauf-Nummer: jeder Start erhöht sie, ein Abbruch auch. Ein Worker merkt sich seine Nummer und darf nur
    schreiben/einfügen, solange sie noch aktuell ist."""

    def __init__(self):
        self.nr = 0

    def neu(self):
        self.nr += 1
        return self.nr

    def aktuell(self, nr):
        return nr == self.nr
