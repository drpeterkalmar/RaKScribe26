"""Diktat an der Cursor-Stelle in den Befund einfügen (v3.5.0, Peter 07.10.).

Peter: „Cursor in den Befund setzen und an der Stelle mit Nur Text etwas diktieren oder eine Textstelle markieren und
überschreiben.“ Reine Funktion auf Zeichen-Offsets — Sync: web_app/src/einfuegen.ts (gemeinsame Fälle:
tests/offline/snapshots/einfuegen_faelle.txt).
"""

_SATZZEICHEN = ".,;:!?)"


def einfuegen(text, start, ende, neu):
    """text[start:ende] durch neu ersetzen (start == ende: einfügen). Leerzeichen an den Rändern werden ergänzt,
    ein doppelter Schlusspunkt vermieden. Gibt (neuer_text, cursor_nach_dem_eingefügten) zurück."""
    text = text or ""
    start = max(0, min(start, len(text)))
    ende = max(start, min(ende, len(text)))
    neu = (neu or "").strip()
    vor, nach = text[:start], text[ende:]
    if not neu:
        return vor + nach, len(vor)
    if nach[:1] in (".", ",", ";", ":") and neu.endswith("."):
        neu = neu[:-1].rstrip()  # „… Befund| .“ → kein „..“ / „.,“
    if vor and not vor[-1].isspace() and neu[0] not in _SATZZEICHEN:
        neu = " " + neu
    if nach and not nach[0].isspace() and nach[0] not in _SATZZEICHEN:
        neu = neu + " "
    return vor + neu + nach, len(vor) + len(neu.rstrip(" "))
