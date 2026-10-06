"""Befund-Pipeline der EXE ohne Oberfläche (Umbau Schritt 5; wird in Schritt 15 zur ganzen Kette ausgebaut).

Ohne Windows/Tk importierbar und testbar (tests/offline/test_regionen.py)."""
import re

import befund_regeln as br

FEHLTEXT = "Befund für Region {region} konnte nicht erstellt werden — bitte erneut diktieren."


def region_name(segment):
    """Kurzname eines Diktat-Segments für Hinweise: erster Satz (z. B. „Ellbogen rechts“), höchstens 40 Zeichen.
    Satzende auch gesprochen („Punkt“, „neue Zeile“, „Absatz“) — so kommt es aus chirp_3."""
    erster = re.split(r"[.:;,\n]|(?<!\w)(?:punkt|neue\s+zeile|neuzeile|absatz)(?!\w)", (segment or "").strip(),
                      maxsplit=1, flags=re.I)[0].strip()
    return erster[:40].strip() or "?"


def assemble_regions(segmente, teile, ist_vollstaendig):
    """Mehr-Regionen-Befund zusammensetzen (Gutachten P2-6). teile[i] = Befundtext oder Exception (bzw. None).
    Gescheiterte/unvollständige Regionen stehen als Hinweistext an ihrer Stelle, fertige Befunde bleiben sichtbar.
    Rückgabe: (report, [Namen der gescheiterten Regionen]) — report wird bei Fehlern NIE eingefügt."""
    bloecke, fehler = [], []
    for seg, teil in zip(segmente, teile):
        if isinstance(teil, str) and ist_vollstaendig(teil):
            bloecke.append(teil)
        else:
            name = region_name(seg)
            fehler.append(name)
            bloecke.append(FEHLTEXT.format(region=name))
    return br.befunde_zusammenfuegen(bloecke), fehler
