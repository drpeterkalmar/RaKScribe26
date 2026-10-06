"""Gate v3.2.3: EXE-Zustandslogik (Gutachten 05.10. P1-2 F10/F9 während Verarbeitung).
Zwischenablage (P1-1): tests/offline/test_clipboard.py.  Aufruf: /usr/bin/python3 exe_zustand_test.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "source_code"))
import exe_zustand as z

fails = 0
def check(name, ok):
    global fails
    print(("✅" if ok else "❌"), name)
    fails += (not ok)


# Zwischenablage (P1-1): tests/offline/test_clipboard.py
check("F10 bereit → start", z.f10_aktion("READY", False) == "start")
check("F10 bei Aufnahme → stop", z.f10_aktion("RECORDING", True) == "stop")
check("F10 während Verarbeitung → ignorieren", z.f10_aktion("PROCESSING", False) == "ignorieren")
check("F10 nach Fehler → start", z.f10_aktion("ERROR", False) == "start")
check("F10 nach Kopiert → start", z.f10_aktion("COPIED", False) == "start")
check("F9 während Verarbeitung → abbrechen", z.f9_aktion("PROCESSING", False) == "abbrechen")
check("F9 bei Aufnahme → stop_und_reset", z.f9_aktion("RECORDING", True) == "stop_und_reset")
check("F9 bereit → reset", z.f9_aktion("READY", False) == "reset")

lz = z.LaufZaehler()
a = lz.neu()
check("Lauf aktuell", lz.aktuell(a))
lz.neu()  # F9-Abbruch oder neue Aufnahme
check("alter Lauf nach Abbruch nicht mehr aktuell (fügt nichts ein)", not lz.aktuell(a))

# Quelltext-Verdrahtung in RaKScribe.py (die EXE selbst läuft nur unter Windows)
src = (pathlib.Path(__file__).parent / "source_code" / "RaKScribe.py").read_text()
check("toggle_recording nutzt f10_aktion", "_zs.f10_aktion(self._status_raw, self.is_recording)" in src)
check("reset_dictation nutzt f9_aktion", "_zs.f9_aktion(self._status_raw, self.is_recording)" in src)
print("\n" + ("✅ EXE-ZUSTAND PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
