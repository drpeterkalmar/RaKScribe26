#!/usr/bin/env python3
"""titel_fixtures.py — EINE Quelle der Wahrheit für die derive-Titel-Tests.

K3-Review-Befund 7/8 (v2.10.13-Nacharbeit): Die drei Implementierungen
(RaKScribe.py, App.tsx + 2 Test-Klone) testen bisher ihre eigenen Klone.
Dieses Modul hält die gemeinsamen Cases als Daten (PY→TS-Paritätsmatrix);
test_normalbefunde.py TEIL 4b konsumiert sie tabellengetrieben.

Die PY-Semantik hier ist bewusst identisch mit source_code/RaKScribe.py
derive_untersuchungs_titel (v2.10.13). Bei Änderung dort: HIER MITSYNCEN
(und den Kommentar-Bump beachten).
"""
import re

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


def derive_titel_py(raw: str, dn: str) -> str:
    """Gemeinsame PY-Referenzimplementierung (Sync mit RaKScribe.py v2.10.13)."""
    if not re.search(r"\(allgemein\)", dn or "", re.I):
        return dn
    t = re.sub(r"\bHW\b", "HWS", (raw or "").strip())
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[.?!]\s*$", "", t).strip()
    for _ in range(3):
        stripped = False
        for f in (r"unauff(?:ae|ä)?llig", r"o\.?\s?B\.?", r"ohne pathologischen Befund",
                  r"ohne pathologischem Befund", r"kein pathologischer Befund",
                  r"regelrecht", r"normal"):
            m = re.search(r"(?:^|[\s,])" + f + r"\s*$", t, re.I)
            if m:
                pre = t[:m.start()].strip()
                if re.search(r"\bnicht\s*$", pre, re.I):
                    continue
                t = pre.strip()
                stripped = True
        if not stripped:
            break
    t = re.sub(r"[.,?!:]+$", "", t).strip()
    t = re.sub(r"\(\s*allgemein\s*\)", "", t, flags=re.I).strip()
    if len(t) > 80:
        t = t[:80].strip()
    return t or re.sub(r"\s*\(Allgemein\)", "", dn, flags=re.I).strip()


if __name__ == "__main__":
    ok, fails = run_fixtures(derive_titel_py)
    for f in fails:
        print("FAIL:", f)
    print("PARITÄT:", "PASS" if ok else "FAIL")