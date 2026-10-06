"""Attrappen für die Windows-/UI-Module der EXE, damit RaKScribe.py auf dem Mac importiert und sein Ablauf
(Aufnahme → chirp_3 → Befund → Kopieren → Strg+V) ohne Windows, Tk-Fenster, Mikrofon und Google getestet werden kann.
Muster wie exe_ui_smoke.py. Nur für Tests."""
import importlib.util, os, pathlib, sys, tempfile, types, warnings

warnings.filterwarnings("ignore")  # Python-3.9-Hinweise der Google-Bibliotheken (Mac)

ROOT = pathlib.Path(__file__).resolve().parents[2]


class Aufzeichnung:
    """Sammelt Aufrufe der gestubbten Module (Strg+V, Dialoge)."""
    def __init__(self):
        self.tasten, self.dialoge = [], []


AUFZ = Aufzeichnung()


class MockCB:
    """win32clipboard-Ersatz; gesperrt=True simuliert ein anderes Programm, das die Zwischenablage hält."""
    CF_UNICODETEXT = 13

    def __init__(self):
        self.data, self.gesperrt = {}, False

    def OpenClipboard(self):
        if self.gesperrt:
            raise OSError("Zwischenablage belegt")

    def CloseClipboard(self):
        pass

    def EmptyClipboard(self):
        self.data = {}

    def RegisterClipboardFormat(self, n):
        return 49000

    def SetClipboardData(self, fmt, val):
        self.data[fmt] = val

    def GetClipboardData(self, fmt):
        return self.data.get(fmt)


CLIPBOARD = MockCB()


class FakeInputStream:
    """sounddevice.InputStream-Ersatz: liefert im eigenen Thread Blöcke à 1600 Samples (Block i = Wert i)."""
    geliefert = 0

    def __init__(self, device=None, samplerate=16000, channels=1, dtype="int16", callback=None):
        self.cb, self._run, self.t = callback, False, None

    def __enter__(self):
        import threading, time
        import numpy as np
        self._run = True

        def loop():
            i = 0
            while self._run:
                self.cb(np.full((1600, 1), i % 30000, dtype=np.int16), 1600, None, None)
                i += 1
                FakeInputStream.geliefert = i
                time.sleep(0.002)
        self.t = threading.Thread(target=loop, daemon=True)
        self.t.start()
        return self

    def __exit__(self, *a):
        self._run = False
        self.t.join()


class Antwort:
    """Google-StreamingRecognizeResponse-Ersatz."""
    def __init__(self, text, is_final):
        alt = type("Alt", (), {"transcript": text})()
        self.results = [type("Res", (), {"alternatives": [alt], "is_final": is_final})()]


def streaming_stub(antworten=(("Knie rechts", False), ("Knie rechts unauffällig", True)), fehler_nach=None):
    """streaming(requests): beantwortet die ersten Pakete mit `antworten`, wirft optional nach `fehler_nach` Paketen."""
    def streaming(requests):
        for n, _req in enumerate(requests, 1):
            if fehler_nach is not None and n > fehler_nach:
                raise RuntimeError("gRPC: Verbindung abgebrochen (Test)")
            if n <= len(antworten):
                yield Antwort(*antworten[n - 1])
    return streaming


class FakeSpeechClient:
    def __init__(self, streaming):
        self.streaming = streaming

    def streaming_recognize(self, requests, config=None):
        return self.streaming(requests)


def stubs():
    kb = types.ModuleType("keyboard")
    kb.add_hotkey = lambda *a, **k: None
    kb.press_and_release = lambda k: AUFZ.tasten.append(k)
    md = types.ModuleType("markdown")
    md.markdown = lambda t: "<p>" + t + "</p>"
    sd = types.ModuleType("sounddevice")

    class _D:
        device = [0, 0]
    sd.default = _D()
    sd.query_devices = lambda: [{"name": "Testmikrofon", "max_input_channels": 1}]
    sd.InputStream = FakeInputStream
    oa = types.ModuleType("openai")
    oa.OpenAI = lambda **k: None
    ctk = types.ModuleType("customtkinter")

    class _W:
        def __init__(self, *a, **k):
            pass
    for n in ["CTk", "CTkFrame", "CTkLabel", "CTkButton", "CTkTextbox", "CTkComboBox", "CTkToplevel"]:
        setattr(ctk, n, type(n, (_W,), {}))
    ctk.set_appearance_mode = lambda *a: None
    mb = types.ModuleType("tkinter.messagebox")
    for n in ("showerror", "showwarning", "showinfo"):
        setattr(mb, n, (lambda name: lambda *a, **k: AUFZ.dialoge.append((name,) + a))(n))
    mb.askyesno = lambda *a, **k: False
    return {"keyboard": kb, "win32clipboard": CLIPBOARD, "pyperclip": types.ModuleType("pyperclip"),
            "markdown": md, "sounddevice": sd, "openai": oa, "customtkinter": ctk}, mb


def lade_rakscribe():
    """Führt source_code/RaKScribe.py als Modul aus (BASE_DIR = Temp-Ordner, keine Schlüssel)."""
    mods, mb = stubs()
    sys.modules.update(mods)
    sys.path.insert(0, str(ROOT / "source_code"))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="rks_test_"))
    import shutil
    for f in ("templates.json", "radiology_prompt.txt", "misheard_words.json", "vorlagen_vorrang.json", "phrases.json"):
        shutil.copy(ROOT / f, tmp / f)  # wie die gebündelten Dateien der EXE
    os.environ["APPDATA"] = str(tmp / "appdata")
    spec = importlib.util.spec_from_loader("rks_test", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(tmp / "RaKScribe.py")
    code = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
    code = code.replace('if __name__ == "__main__":', 'if False:')
    _out = sys.__stdout__
    sys.__stdout__ = open(os.devnull, "w")  # Start-Log der EXE nicht in die Testausgabe
    try:
        exec(compile(code, str(ROOT / "source_code" / "RaKScribe.py"), "exec"), mod.__dict__)
        mod.init_runtime()  # Umbau Schritt 16: Start-Initialisierung wie main()
    finally:
        sys.__stdout__ = _out
    mod.messagebox = mb
    mod.log = mod.print = lambda *a: None  # Testausgabe ruhig halten
    mod.speech = type("speech", (), {"StreamingRecognizeRequest": staticmethod(lambda audio_content: audio_content)})
    mod.speech_client = FakeSpeechClient(streaming_stub())
    return mod


class FakeText:
    def __init__(self):
        self.text = ""

    def delete(self, a, b=None):
        self.text = ""

    def insert(self, pos, t):
        self.text = t + self.text if pos == "1.0" else self.text + t

    def get(self, a, b=None):
        return self.text if b == "end-1c" else self.text + "\n"


class FakeWidget:
    def __init__(self):
        self.cfg = {}

    def configure(self, **k):
        self.cfg.update(k)

    def cget(self, k):
        return self.cfg.get(k, "")

    def winfo_width(self):
        return 200


def baue_app(mod):
    """RaKScribeApp ohne Tk-Fenster: Widgets als Attrappen, after() sammelt Aufrufe für pump()."""
    app = object.__new__(mod.RaKScribeApp)
    app._queue = []
    app.after = lambda ms, fn=None, *a: app._queue.append((fn, a))
    app._status_raw = "READY"
    app.gate = None
    app._job = mod._js.JobState()
    app.samplerate = 16000
    app.is_recording = False
    app.final_transcript = app.stream_transcript = app.stream_interim = ""
    app._aufnahme = None
    app._live_aus = False
    app.selected_device_index = 0
    app.transcript_text, app.result_text = FakeText(), FakeText()
    for n in ("record_btn", "level_indicator", "level_container", "status_badge", "key_chip"):
        setattr(app, n, FakeWidget())
    app.update_recording_timer = lambda: None
    app.update_processing_timer = lambda: None
    return app


def pump(app, bis=None, timeout=5.0):
    """Arbeitet after()-Aufrufe im Test-Thread ab (wie die Tk-Hauptschleife), bis bis() wahr ist."""
    import time
    t0 = time.time()
    while time.time() - t0 < timeout:
        while app._queue:
            fn, a = app._queue.pop(0)
            if fn:
                fn(*a)
        if bis is None or bis():
            if bis is None:
                time.sleep(0.05)
                if not app._queue:
                    return True
            else:
                return True
        time.sleep(0.01)
    return False
