"""Gate v3.5.0 (Peter 07.10.): Diktat an der Cursor-Stelle in den Befund einfügen / Markierung überschreiben.
einfuegen.py (= einfuegen.ts über snapshots/einfuegen_faelle.txt) und EXE-Ablauf mit Attrappen.
Aufruf: /usr/bin/python3 tests/offline/test_einfuegen.py"""
import json, pathlib, sys
HIER = pathlib.Path(__file__).resolve().parent
ROOT = HIER.parents[1]
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(ROOT / "source_code"))
import einfuegen as E  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# 1. Gemeinsame Fälle (Web prüft dieselbe Datei in pipeline_test.mjs)
for f in json.loads((HIER / "snapshots" / "einfuegen_faelle.txt").read_text(encoding="utf-8")):
    r = E.einfuegen(f["text"], f["start"], f["ende"], f["neu"])
    check(f"einfuegen: {f['name']}", list(r) == [f["ergebnis"], f["cursor"]], repr(r))


# 2. EXE: Cursor im Befund + F10 → Diktat wird dort eingefügt, Befund bleibt, kein Befund-LLM, kein Strg+V
class FakeTb:
    """Minimaler tk.Text: Indizes als '1.0+Nc', Marken als Offsets."""
    def __init__(self, box, insert=0, sel=None):
        self.box, self.marks, self.sel = box, {"insert": insert}, sel
        self.fokus = False

    def _o(self, i):
        if isinstance(i, int):
            return i
        if i in self.marks:
            return self.marks[i]
        if i == "sel.first":
            return self.sel[0]
        if i == "sel.last":
            return self.sel[1]
        if i.startswith("1.0+") and i.endswith("c"):
            return int(i[4:-1])
        return 0 if i == "1.0" else len(self.box.text)

    def tag_ranges(self, tag):
        return ("a", "b") if tag == "sel" and self.sel else ()

    def index(self, i):
        return f"1.0+{self._o(i)}c"

    def mark_set(self, name, i):
        self.marks[name] = self._o(i)

    def mark_gravity(self, *a):
        pass

    def count(self, a, b, what):
        return (self._o(b) - self._o(a),)

    def see(self, i):
        pass

    def focus_set(self):
        self.fokus = True


import exe_stubs as S  # noqa: E402
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: True
mod._korr.korrigieren = lambda t, key, block="", log=None: "Zusätzlich kleiner Gelenkerguss."
mod._llm_aufruf = lambda p: (_ for _ in ()).throw(AssertionError("Befund-KI beim Einfügen gerufen"))
BEFUND = "## Kniegelenk rechts\n\n## Befund\nKein Erguss. Bänder intakt.\n\n## Ergebnis\nUnauffälliger Befund."


def lauf(insert=0, sel=None, chirp="zusätzlich kleiner Gelenkerguss", fokus=True):
    S.AUFZ.tasten.clear()
    mod._chirp3_worker = lambda pcm, sr, loc, token: chirp
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub())
    app = S.baue_app(mod)
    app.result_text.insert("1.0", BEFUND)
    tb = FakeTb(app.result_text, insert, sel)
    app.result_text._textbox = tb
    app.focus_get = (lambda: tb) if fokus else (lambda: None)
    app.status_badge = S.FakeWidget()
    app.toggle_recording()
    S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
    app.toggle_recording()
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
    S.pump(app, lambda: False, 0.8)
    app._aufnahme_stoppen()
    return app, tb


pos = BEFUND.index("Bänder")
app, tb = lauf(insert=pos)
erwartet = BEFUND.replace("Kein Erguss. Bänder", "Kein Erguss. Zusätzlich kleiner Gelenkerguss. Bänder")
check("EXE Cursor im Befund: Diktat an der Stelle eingefügt, Rest unverändert", app.result_text.text == erwartet,
      repr(app.result_text.text))
check("EXE: Cursor steht hinter dem eingefügten Text, Fokus im Befund",
      tb.marks["insert"] == pos + len("Zusätzlich kleiner Gelenkerguss.") and tb.fokus, str(tb.marks))
check("EXE: ganzer Befund kopiert, kein Strg+V (RaKScribe vorne)", S.AUFZ.tasten == []
      and "Gelenkerguss" in str(S.CLIPBOARD.data.get(13, "")), str(S.AUFZ.tasten))

a = BEFUND.index("Kein Erguss.")
app, tb = lauf(sel=(a, a + len("Kein Erguss.")))
check("EXE Markierung: wird durch das Diktat ersetzt",
      app.result_text.text == BEFUND.replace("Kein Erguss.", "Zusätzlich kleiner Gelenkerguss."), repr(app.result_text.text))

NEU = "## Schultergelenk links\n\n## Befund\nRegelrecht.\n\n## Ergebnis\nUnauffälliger Befund."
mod._llm_aufruf = lambda p: NEU
app, tb = lauf(insert=pos, fokus=False, chirp="Schulter links Tendinopathie der Supraspinatussehne")
check("EXE ohne Cursor im Befund: normaler Ablauf, neuer Befund ersetzt den alten", "Kniegelenk" not in app.result_text.text
      and "Schultergelenk links" in app.result_text.text, repr(app.result_text.text[:80]))
app.reset_dictation()
check("EXE F9 löscht das Einfüge-Ziel", app._einfuegen_ziel is None)

print("FAILS:", fails)
sys.exit(1 if fails else 0)
