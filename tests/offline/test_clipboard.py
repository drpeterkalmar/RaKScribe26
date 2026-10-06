"""Gate (Umbau Schritt 3, Gutachten P1-1): Befund in die Windows-Zwischenablage — Wiederholung, Gegenlesen,
Strg+V nur nach Erfolg. Läuft auf dem Mac: win32clipboard wird gemockt.
Aufruf: /usr/bin/python3 tests/offline/test_clipboard.py"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import clipboard_win as c  # noqa: E402

fails = 0


def check(name, ok):
    global fails
    print(("✅" if ok else "❌"), name)
    fails += (not ok)


class MockCB:
    """win32clipboard-Ersatz: busy_first = so oft wirft OpenClipboard zuerst (anderes Programm hält sie)."""
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
md = lambda t: "<p>" + t + "</p>"
BEFUND = "## Kniegelenk rechts in 2 Ebenen\n\n## Befund\nRegelrecht.\n\n## Ergebnis\nRegelrechte Darstellung."

cb = MockCB()
check("Zwischenablage frei → True, Text + HTML drin",
      c.clipboard_set(BEFUND, cb=cb, md_to_html=md, sleep=nosleep) and cb.data[13] == BEFUND and 49000 in cb.data)
cb = MockCB(busy_first=1)
check("1. Versuch wirft → Retry greift → True", c.clipboard_set(BEFUND, cb=cb, md_to_html=md, sleep=nosleep)
      and cb.open_calls >= 2)
cb = MockCB(busy_first=3)
check("3× belegt, dann frei → True", c.clipboard_set(BEFUND, cb=cb, md_to_html=md, sleep=nosleep))
cb = MockCB(never=True)
pausen = []
check("dauerhaft belegt → False nach genau 5 Versuchen (je 100 ms Pause)",
      c.clipboard_set(BEFUND, cb=cb, md_to_html=md, sleep=pausen.append) is False
      and cb.open_calls == c.VERSUCHE == 5 and pausen == [0.1] * 4)
check("Zwischenablage nach Fehler nicht offen gelassen", not cb.opened)
cb = MockCB(wrong_readback=True)
check("Gegenlesen ≠ Befund → False", c.clipboard_set(BEFUND, cb=cb, md_to_html=md, sleep=nosleep) is False)
cb = MockCB()
check("leerer Befund → False, Zwischenablage unberührt", c.clipboard_set("", cb=cb, md_to_html=md) is False
      and cb.open_calls == 0)


def kaputt(_t):
    raise RuntimeError("markdown fehlt")


cb, logs = MockCB(), []
check("HTML-Aufbereitung scheitert → nur Text, trotzdem True",
      c.clipboard_set(BEFUND, cb=cb, md_to_html=kaputt, sleep=nosleep, log=logs.append) and 49000 not in cb.data
      and cb.data[13] == BEFUND and logs)
cb = MockCB()
check("CRLF beim Gegenlesen toleriert", c.zwischenablage_setzen(cb, None, "A\r\nB", sleep=nosleep))

# CF_HTML-Header: Offsets zeigen auf <html> bzw. den Body-Inhalt (ASCII-Befund)
raw = c.html_format_bytes("Befund", md).decode("utf-8")
hdr = dict(l.split(":", 1) for l in raw.split("\r\n")[:6])
sh, eh, sf, ef = (int(hdr[k]) for k in ("StartHTML", "EndHTML", "StartFragment", "EndFragment"))
check("CF_HTML: StartHTML → '<html>', EndHTML = Ende", raw[sh:].startswith("<html>") and eh == len(raw))
check("CF_HTML: Fragment = Body-Inhalt", raw[sf:ef] == "<p>Befund</p>")

# Verdrahtung in RaKScribe.py (die EXE selbst läuft nur unter Windows)
src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("Strg+V nur nach erfolgreichem Kopieren", "if self.copy_formatted_report():" in src
      and src.count("press_and_release('ctrl+v')") == 1)
check("Kopieren über clipboard_win.clipboard_set", "_cb.clipboard_set(md_text, cb=win32clipboard" in src)
check("Fehlschlag → Status ERROR + Fehlerdialog", 'messagebox.showerror("Nicht eingefügt"' in src
      and "ZWISCHENABLAGE_GESPERRT" in src)
check("Knopf „Befund kopieren“ meldet Fehlschlag", "copy_formatted_report(aus_knopf=True)" in src)
check("kein verschlucktes except: pass im Kopieren", "except: pass" not in src[src.index("def copy_formatted_report"):
                                                                               src.index("def register_hotkey")])

print("\n" + ("✅ ZWISCHENABLAGE PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
