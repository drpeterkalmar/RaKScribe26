#!/usr/bin/env python3
"""tests/offline/titel_fixtures.py — EINE Quelle der Wahrheit für die derive-Titel-Tests.

K3-Review-Befund 7/8 (v2.10.13-Nacharbeit): Dieses Modul hält die gemeinsamen Cases als Daten
(PY→TS-Paritätsmatrix); tests/offline/test_normalbefunde.py TEIL 4b prüft damit die echte Funktion
source_code/detect.py derive_untersuchungs_titel (Umbau Schritt 12: direkt importiert, kein Klon mehr).
"""

# (raw, display_name) → erwarteter Titel. Abgedeckte K3-Randfälle:
TITEL_FIXTURES = [
    # Peters Dauer-Regression (v2.10.12/13-Kern)
    ("Unterschenkel-Sonographie rechts unauffällig.", "Sonographie (Allgemein)",
     "Unterschenkel-Sonographie rechts"),
    # ae-STT-Variante
    ("Unterschenkel-Sonographie rechts unauffaellig", "Sonographie (Allgemein)",
     "Unterschenkel-Sonographie rechts"),
    # HW→HWS-Korrektur
    ("HW unauffaellig", "Sonographie (Allgemein)", "HWS"),
    # o.B.-Kürzel
    ("Nervensonographie o.B.", "Hochauflösende Nervensonographie (Allgemein)",
     "Nervensonographie"),
    # Doppelpunkt-Rest (K3-Befund 5)
    ("Sono Abdomen: unauffällig", "Sonographie (Allgemein)", "Sono Abdomen"),
    # Negation bleibt (K3-Befund 4)
    ("Knie nicht unauffällig", "Sonographie (Allgemein)", "Knie nicht unauffällig"),
    # Loop über alle Findings (K3-Befund 4)
    ("Knie regelrecht unauffällig", "Sonographie (Allgemein)", "Knie"),
    # Reiner Befund-Wort-Diktat → Fallback = display_name ohne (Allgemein)
    ("unauffällig", "Sonographie (Allgemein)", "Sonographie"),
    # Leak-Check: (Allgemein) im Diktat wird gestrippt (K3-Befund 5)
    ("Sonographie (Allgemein)", "Sonographie (Allgemein)", "Sonographie"),
    # Mehrtlg. Faltung + Cap
    ("Schulter-Sonographie   beidseits  regelrecht.", "Sonographie (Allgemein)",
     "Schulter-Sonographie beidseits"),
    # Konkretes Template: display_name 1:1 (kein derive)
    ("HWS unauffällig", "Halswirbelsäule in 2 Ebenen", "Halswirbelsäule in 2 Ebenen"),
    # Leeres Diktat → Fallback
    ("", "Sonographie (Allgemein)", "Sonographie"),
]

# TS-Paritäts-Matrix: dieselben Cases, für den vitest/TS-Test exportiert.
# App.tsx-Funktion wird manuell gegen dieselbe Tabelle getestet — der
# Kommentar-Verweis verhindert Drift.
def run_fixtures(derive_fn) -> tuple:
    """(ok, fehlerliste) über alle TITEL_FIXTURES gegen eine derive-Implementierung."""
    fails = []
    for raw, dn, want in TITEL_FIXTURES:
        got = derive_fn(raw, dn)
        if got != want:
            fails.append(f"{raw!r} + {dn!r} → {got!r} (erwartet {want!r})")
    return not fails, fails


if __name__ == "__main__":
    import pathlib, sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "source_code"))
    import detect
    ok, fails = run_fixtures(detect.derive_untersuchungs_titel)
    for f in fails:
        print("FAIL:", f)
    print("PARITÄT:", "PASS" if ok else "FAIL")