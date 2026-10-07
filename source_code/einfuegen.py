"""Diktat an der Cursor-Stelle in den Befund einfügen (v3.5.0, Peter 07.10.).

Peter: „Cursor in den Befund setzen und an der Stelle mit Nur Text etwas diktieren oder eine Textstelle markieren und
überschreiben.“ Reine Funktion auf Zeichen-Offsets — Sync: web_app/src/einfuegen.ts (gemeinsame Fälle:
tests/offline/snapshots/einfuegen_faelle.txt).
"""

_SATZZEICHEN = ".,;:!?)"
# v3.7.0: Abkürzungen, nach deren Punkt KEIN Satz beginnt (klein geschrieben verglichen, ohne Schlusspunkt)
_ABKUERZUNGEN = {"ca", "bzw", "evtl", "ggf", "z.b", "zb", "d.h", "u.a", "v.a", "z.n", "st.p", "i.v", "vs", "dr", "re",
                 "li", "bds", "lt", "inkl", "max", "min", "mind", "usw", "etc", "bzgl", "insb", "vgl", "zust", "pat"}


def satzanfang(vor):
    """v3.7.0 (Peter 07.10.): Beginnt an dieser Stelle ein neuer Satz? Ja am Textanfang, in einer neuen Zeile
    (nur Leerzeichen davor) oder nach . ! ? (nicht nach Abkürzungen wie „ca.“, „z. B.“)."""
    v = (vor or "").rstrip(" \t")
    if not v or v.endswith("\n"):
        return True
    if v[-1] in "!?":
        return True
    if v[-1] != ".":
        return False
    wort = v[:-1].split()[-1].lower() if v[:-1].split() else ""
    if wort in _ABKUERZUNGEN or (len(wort) == 1 and wort.isalpha()):
        return False  # „ca.“, „bzw.“, „z. B.“ (einzelner Buchstabe)
    return True


def einfuegen(text, start, ende, neu, gross=False):
    """text[start:ende] durch neu ersetzen (start == ende: einfügen). Leerzeichen an den Rändern werden ergänzt,
    ein doppelter Schlusspunkt vermieden. gross=True (v3.7.0, Option): am Satzanfang groß beginnen.
    Gibt (neuer_text, cursor_nach_dem_eingefügten) zurück."""
    text = text or ""
    start = max(0, min(start, len(text)))
    ende = max(start, min(ende, len(text)))
    neu = (neu or "").strip()
    vor, nach = text[:start], text[ende:]
    if not neu:
        return vor + nach, len(vor)
    if gross and neu[0].isalpha() and neu[0].islower() and satzanfang(vor):
        neu = neu[0].upper() + neu[1:]
    if nach[:1] in (".", ",", ";", ":") and neu.endswith("."):
        neu = neu[:-1].rstrip()  # „… Befund| .“ → kein „..“ / „.,“
    if vor and not vor[-1].isspace() and neu[0] not in _SATZZEICHEN:
        neu = " " + neu
    if nach and not nach[0].isspace() and nach[0] not in _SATZZEICHEN:
        neu = neu + " "
    return vor + neu + nach, len(vor) + len(neu.rstrip(" "))
