"""Gate v3.2.3: EXE-Zustandslogik (Gutachten 05.10. P1-1 Zwischenablage, P1-2 F10/F9 während Verarbeitung).
Läuft auf dem Mac ohne Windows: win32clipboard wird gemockt.  Aufruf: /usr/bin/python3 exe_zustand_test.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "source_code"))
import exe_zustand as z

fails = 0
def check(name, ok):
    global fails
    print(("✅" if ok else "❌"), name)
    fails += (not ok)


class MockCB:
    CF_UNICODETEXT = 13
    def __init__(self, busy_first=0, never=False, wrong_readback=False):
        self.busy, self.never, self.wrong = busy_first, never, wrong_readback
        self.data, self.open_calls, self.opened = {}, 0, False
    def OpenClipboard(self):
        self.open_calls += 1
        if self.never or self.busy > 0:
            self.busy -= 1
            raise OSError("Zugriff verweigert (Zwischenablage belegt)")
        self.opened = True
    def CloseClipboard(self):
        self.opened = False
    def EmptyClipboard(self):
        self.data = {}
    def RegisterClipboardFormat(self, n):
        return 49000
    def SetClipboardData(self, fmt, val):
        self.data[fmt] = val
    def GetClipboardData(self, fmt):
        return "ALTER BEFUND" if self.wrong else self.data.get(fmt)


nosleep = lambda s: None
cb = MockCB()
check("Zwischenablage frei → True, Text drin", z.zwischenablage_setzen(cb, b"<html>", "## Befund", sleep=nosleep) and cb.data[13] == "## Befund")
cb = MockCB(busy_first=3)
check("3× belegt, dann frei → Retry greift → True", z.zwischenablage_setzen(cb, b"x", "B", sleep=nosleep))
cb = MockCB(never=True)
check("dauerhaft belegt → False (kein Einfügen)", z.zwischenablage_setzen(cb, b"x", "B", sleep=nosleep) is False and cb.open_calls == z.VERSUCHE)
cb = MockCB(wrong_readback=True)
check("Gegenlesen ≠ Befund → False", z.zwischenablage_setzen(cb, b"x", "B", sleep=nosleep) is False)
cb = MockCB()
check("ohne HTML (Fallback) → True", z.zwischenablage_setzen(cb, None, "B", sleep=nosleep))
check("Clipboard nach Fehler nicht offen gelassen", not MockCB(never=True).opened)

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
check("Strg+V nur nach erfolgreichem Kopieren", "if self.copy_formatted_report():" in src
      and src.count("press_and_release('ctrl+v')") == 1)
check("copy nutzt zwischenablage_setzen", "_zs.zwischenablage_setzen(win32clipboard" in src)
check("kein verschlucktes except: pass im Kopieren", "self.update_status(\"COPIED\", \"ready\")\n        except: pass" not in src)

print("\n" + ("✅ EXE-ZUSTAND PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
