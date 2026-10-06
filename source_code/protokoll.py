"""Protokoll der EXE (Umbau Schritt 23, Gutachten P2-14) — ohne Tk/Windows importierbar.

- rakscribe.log mit Größenbegrenzung: 5 Dateien × 1 MB (RotatingFileHandler) statt unbegrenzt wachsender Datei.
- Diktatinhalte (können Patientennamen enthalten) nur mit RAKSCRIBE_DEBUG=1 — sonst nur die Länge (diktat()).
- Die Datei wird erst beim ersten Eintrag geöffnet (kein Seiteneffekt beim Import).
"""
import logging
import logging.handlers
import os

MAX_BYTES = 1_000_000
DATEIEN = 5  # rakscribe.log + 4 ältere


def debug_aktiv():
    return os.environ.get("RAKSCRIBE_DEBUG") == "1"


def diktat(text):
    """Diktat-/Befundtext fürs Protokoll: Inhalt nur im Debug-Modus, sonst nur die Länge."""
    text = text or ""
    return repr(text[:200]) if debug_aktiv() else f"<{len(text)} Zeichen>"


_LOGGER = {}


def datei_logger(pfad):
    """Logger mit RotatingFileHandler für pfad (einmal je Pfad, Format „[Zeit] Text“ wie bisher)."""
    lg = _LOGGER.get(pfad)
    if lg is None:
        lg = logging.getLogger(f"rakscribe:{pfad}")
        lg.setLevel(logging.INFO)
        lg.propagate = False
        h = logging.handlers.RotatingFileHandler(pfad, maxBytes=MAX_BYTES, backupCount=DATEIEN - 1,
                                                 encoding="utf-8", delay=True)
        h.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        lg.addHandler(h)
        _LOGGER[pfad] = lg
    return lg
