"""Diktat-Anzeige während einer SpeechMike-Aufnahme mit Pausen (v3.8.0, Peter 11.10. Nachtrag 1). Sync: web_app/src/segmente.ts.

Bei jeder Pause wird der Abschnitt seit Start/Weiter sofort mit chirp_3 + Fehlhör-Liste repariert und ersetzt in der
Anzeige den Live-Text (Streaming) dieses Abschnitts. Der Endtext für den Befund kommt weiterhin aus der Transkription der
GANZEN Aufnahme (Messung 11.10.: kurze Abschnitte ohne Zusammenhang verhören sich, z. B. „Befund Nervus ulnaris“ →
„Power Stange Busulnaris“; docs/benchmarks/pause_segmente_2026-10-11.txt) — die Reparatur dient nur der Anzeige.
Ohne Windows/Tk importierbar (tests/offline/test_speechmike_ablauf.py).
"""

MIN_SAMPLES = 8000  # Abschnitte unter 0,5 s (16 kHz) nicht einzeln reparieren — dort steht höchstens ein Wortrest


def live_text(eintrag):
    """[finale Streaming-Abschnitte, letzter Zwischenstand] → Anzeige wie bisher („… [.. Zwischenstand ..]“)."""
    if not eintrag:
        return ""
    final, interim = eintrag
    return (final + " [.. " + interim + " ..]") if interim else final.strip()


def anzeige(basis, abschnitte, live):
    """Text für das Diktat-Feld. basis = bisheriges Diktat (Nachdiktat), abschnitte = reparierter Text je geschlossenem
    Abschnitt (None = Reparatur offen/gescheitert → Live-Text), live = {Abschnitt: [final, interim]}; der laufende
    Abschnitt hat die Nummer len(abschnitte). Ohne Pause und ohne basis = genau die bisherige Live-Anzeige."""
    teile = [(basis or "").strip()]
    for k, rep in enumerate(abschnitte):
        teile.append((rep if rep is not None else live_text(live.get(k))).strip())
    teile.append(live_text(live.get(len(abschnitte))).strip())
    return " ".join(t for t in teile if t)


def rettung(basis, abschnitte, live):
    """Endtext, wenn chirp_3 über die ganze Aufnahme nichts liefert: wie bisher die Streaming-Texte (final, sonst der
    letzte Zwischenstand), je Abschnitt der reparierte Text, falls vorhanden."""
    teile = [(basis or "").strip()]
    for k in range(max([len(abschnitte)] + [i + 1 for i in live])):
        rep = abschnitte[k] if k < len(abschnitte) else None
        final, interim = live.get(k, ["", ""])
        teile.append((rep if rep is not None else (final.strip() or interim.strip())).strip())
    return " ".join(t for t in teile if t)
