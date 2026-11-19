"""Protokoll der EXE (Umbau Schritt 23, Gutachten P2-14) — ohne Tk/Windows importierbar.

- rakscribe.log mit Größenbegrenzung: 5 Dateien × 1 MB (RotatingFileHandler) statt unbegrenzt wachsender Datei.
- Diktatinhalte (können Patientennamen enthalten) nur mit RAKSCRIBE_DEBUG=1 — sonst nur die Länge (diktat()).
- Die Datei wird erst beim ersten Eintrag geöffnet (kein Seiteneffekt beim Import).
- kaiscribe-frog-einsetzen-n1 (19.11.2026): rakscribe.log liegt auf X: und wird von mehreren PCs/Instanzen zugleich
  beschrieben. Der RotatingFileHandler hielt die Datei offen; unter Windows scheitert dann das Umbenennen beim Rotieren,
  und ab 1 MB schrieb KEINE Instanz mehr (19.11. ab 11:32 still). Jetzt: Datei nur je Eintrag kurz öffnen, Rotieren
  scheitert → weiter anhängen (die Datei wird vorübergehend größer) und frühestens nach 60 s erneut versuchen.
"""
import logging
import os
import time

MAX_BYTES = 1_000_000
DATEIEN = 5  # rakscribe.log + 4 ältere


def debug_aktiv():
    return os.environ.get("RAKSCRIBE_DEBUG") == "1"


def diktat(text):
    """Diktat-/Befundtext fürs Protokoll: Inhalt nur im Debug-Modus, sonst nur die Länge."""
    text = text or ""
    return repr(text[:200]) if debug_aktiv() else f"<{len(text)} Zeichen>"


WIEDER_S = 60     # nach einem gescheiterten Rotieren frühestens so viel später erneut


class TeilbareDatei(logging.Handler):
    """Log-Datei mit Rotation (pfad, pfad.1 … pfad.<anzahl-1>), die mehrere Prozesse zugleich beschreiben dürfen: offen
    nur während eines Eintrags; scheitert das Rotieren (Datei gerade woanders offen), wird trotzdem angehängt."""

    def __init__(self, pfad, max_bytes=MAX_BYTES, anzahl=DATEIEN, uhr=time.monotonic, ersetzen=os.replace):
        super().__init__()
        self.pfad, self.max_bytes, self.anzahl = pfad, max_bytes, anzahl
        self._uhr, self._ersetzen, self._naechster = uhr, ersetzen, 0.0
        self.fehlversuche = 0

    def _rotieren(self):
        for i in range(self.anzahl - 1, 0, -1):
            alt = self.pfad if i == 1 else f"{self.pfad}.{i - 1}"
            if os.path.exists(alt):
                self._ersetzen(alt, f"{self.pfad}.{i}")

    def emit(self, record):
        try:
            zeile = self.format(record) + "\n"
            try:
                groesse = os.path.getsize(self.pfad)
            except OSError:
                groesse = 0
            if groesse and groesse + len(zeile.encode("utf-8")) > self.max_bytes and self._uhr() >= self._naechster:
                try:
                    self._rotieren()
                except OSError:
                    self.fehlversuche += 1
                    self._naechster = self._uhr() + WIEDER_S
            with open(self.pfad, "a", encoding="utf-8") as f:
                f.write(zeile)
        except Exception:
            self.handleError(record)


_LOGGER = {}


def datei_logger(pfad):
    """Logger mit TeilbareDatei für pfad (einmal je Pfad, Format „[Zeit] Text“ wie bisher)."""
    lg = _LOGGER.get(pfad)
    if lg is None:
        lg = logging.getLogger(f"rakscribe:{pfad}")
        lg.setLevel(logging.INFO)
        lg.propagate = False
        h = TeilbareDatei(pfad)
        h.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        lg.addHandler(h)
        _LOGGER[pfad] = lg
    return lg
