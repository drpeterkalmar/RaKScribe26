#!/usr/bin/env python3
"""tools/exe_speechmike_smoke.py — macOS-Vorprobe für Fall E des Windows-UI-Tests (v3.8.0 SpeechMike): echte
Tk-Oberfläche aus RaKScribe.py, Windows-Module gestubbt, Dummy-Schlüssel, Selbsttest-Modus mit FAKEAUDIO (Attrappen für
Mikrofon/Google/chirp_3). SpeechMike-Tasten gehen wie im Windows-Test über Trigger-Dateien (sm_RECORD#1 …) → Bericht →
Dekodierer → Handler. Der echte Nachweis bleibt der Windows-UI-Test (tests/windows/exe_ui_test.py, Fall E).
  ~/dev/RaKScribe26-work/.venv-exe/bin/python tools/exe_speechmike_smoke.py
"""
import faulthandler, importlib.util, json, os, pathlib, sys, tempfile, threading, time, types
faulthandler.dump_traceback_later(150, exit=True)
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "offline"))
import exe_stubs as S  # noqa: E402  (MockCB = Zwischenablage-Attrappe)
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402

TASTEN = []
kb = types.ModuleType("keyboard")
kb.add_hotkey = lambda *a, **k: None
kb.press_and_release = lambda k: TASTEN.append(k)
sys.modules.update({"keyboard": kb, "win32clipboard": S.CLIPBOARD, "pyperclip": types.ModuleType("pyperclip")})
sd = types.ModuleType("sounddevice")
sd.default = type("D", (), {"device": [0, 0]})()
sd.query_devices = lambda: [{"name": "Testmikrofon", "max_input_channels": 1}]
sys.modules["sounddevice"] = sd
oa = types.ModuleType("openai"); oa.OpenAI = lambda **k: None; sys.modules["openai"] = oa

tmp = pathlib.Path(tempfile.mkdtemp(prefix="rks_sm_smoke_"))
os.chdir(tmp)
os.environ["APPDATA"] = str(tmp / "appdata")
(tmp / "appdata" / "RaKScribe").mkdir(parents=True)
pem = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
(tmp / "appdata" / "RaKScribe" / "rakscribe-praxis-key.json").write_text(json.dumps(
    {"vertex_api_key": "AQ.smoke-dummy-key-not-valid", "stt": {"type": "service_account", "project_id": "x", "private_key": pem,
     "client_email": "smoke@x.iam.gserviceaccount.com", "token_uri": "https://oauth2.googleapis.com/token"}}))
STATE = tmp / "selftest.json"
os.environ.update(RAKSCRIBE_SELFTEST=str(STATE), RAKSCRIBE_SELFTEST_FAKEAUDIO="1", RAKSCRIBE_SELFTEST_GEOMETRY="1240x820+40+40")

src = ROOT / "source_code" / "RaKScribe.py"
mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("rks", loader=None))
mod.__file__ = str(tmp / "RaKScribe.py")
sys.path.insert(0, str(ROOT / "source_code"))
for f in ("templates.json", "radiology_prompt.txt", "misheard_words.json", "vorlagen_vorrang.json", "phrases.json", "VERSION"):
    (tmp / f).write_bytes((ROOT / f).read_bytes())
exec(compile(src.read_text(encoding="utf-8").replace('if __name__ == "__main__":', 'if False:'), str(src), "exec"), mod.__dict__)
mod.init_runtime()
mod.ctk.set_appearance_mode("dark")
app = mod.RaKScribeApp()
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅ " if ok else "❌ ") + name + ("" if ok else f"  ({detail})"), flush=True)
    fails += (not ok)


def phase(name, timeout=25):
    (tmp / "selftest.json.trigger").write_text(name, encoding="utf-8")
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            d = json.loads(STATE.read_text(encoding="utf-8"))
            if name in d:
                return d[name]
        except Exception:
            pass
        time.sleep(0.2)
    return None


def ablauf():
    try:
        t0 = time.time()
        st = None
        while st is None and time.time() - t0 < 30:
            time.sleep(0.3)
            try:
                st = json.loads(STATE.read_text(encoding="utf-8")).get("ready")
            except Exception:
                pass
        err = pathlib.Path(str(STATE) + ".err")
        if err.exists():
            print("SELBSTTEST-FEHLER:", err.read_text(encoding="utf-8"))
        check("bereit, Schlüssel aktiv, SpeechMike-Leser ohne Gerät/ohne hidapi ohne Fehler",
              st["status"] == "READY" and st["keys_ready"] and st["led"] in ("aus", None), str(st.get("hid")))
        s = phase("sm_RECORD#1")
        check("E1 Record → Aufnahme, LED rot", s and s["job_zustand"] == "RECORDING" and s["led"] == "aufnahme", str(s and (s["job_zustand"], s["led"])))
        time.sleep(2)
        s = phase("sm_RECORD#2")
        check("E2 Record → Pause, LED rot blinkend, Abschnitt repariert, kein Befund",
              s and s["job_zustand"] == "PAUSED" and s["led"] == "pause" and s["transcript"] == "Kniegelenk rechts in 2 Ebenen unauffällig."
              and "repariert" in s["repariert"] and s["result"] == "", str(s and (s["job_zustand"], s["transcript"], s["repariert"])))
        s = phase("sm_EOL#1")
        check("E3 EOL in der Pause → nichts, Hinweis", s and s["job_zustand"] == "PAUSED" and "Erst INS" in s["hinweis"]
              and s["einfuegungen"] == 0, str(s and s["hinweis"]))
        s = phase("sm_RECORD#3")
        check("E4 Record → weiter", s and s["job_zustand"] == "RECORDING")
        time.sleep(1.5)
        s = phase("sm_INS#1")
        check("E5 INS → Befund rechts zur Kontrolle, nichts eingefügt/kopiert, LED grün",
              s and s["job_zustand"] == "READY" and s["status"] == "KONTROLLE" and s["result"].startswith("## Kniegelenk")
              and s["befund_wartet"] and s["led"] == "befund_bereit" and s["einfuegungen"] == 0
              and not s["zwischenablage"].startswith("## "), str(s and (s["status"], s["result"][:30], s["led"], s["zwischenablage"][:30])))
        s = phase("befund_aendern")
        geaendert = s["result"]
        check("E6 Befund von Hand geändert", geaendert.endswith("Von Hand ergänzt."))
        s = phase("sm_EOL#2")
        check("E7 EOL → genau der geänderte Befund in der Zwischenablage, alles leer, LED aus",
              s and s["zwischenablage"] == geaendert.strip() and s["result"] == "" and s["transcript"] == "" and s["led"] == "aus"
              and ("Befund kopiert" in s["hinweis"] or "eingefügt in" in s["hinweis"]), str(s and (s["zwischenablage"][-30:], s["hinweis"])))
        s = phase("sm_F2#1")
        check("E8 F2 → Nur Text an", s and s["nur_text"] is True)
        phase("sm_RECORD#4"); time.sleep(1.5)
        s = phase("sm_INS#2")
        check("E9 Nur Text, INS → korrigierter Text ohne Überschriften, nichts eingefügt",
              s and s["result"] == "Kniegelenk rechts in 2 Ebenen unauffällig." and s["einfuegungen"] == 0, str(s and s["result"]))
        s = phase("sm_EOL#3")
        check("E10 Nur Text, EOL → genau dieser Text weitergeschickt, leer",
              s and s["zwischenablage"] == "Kniegelenk rechts in 2 Ebenen unauffällig." and s["result"] == "")
        s = phase("sm_F2#2")
        check("E11 F2 → Nur Text aus", s and s["nur_text"] is False)
        phase("sm_RECORD#5")
        s = phase("sm_F1#1")
        check("E12 F1 → Neu: Aufnahme verworfen, bereit, LED aus", s and s["job_zustand"] == "READY" and s["transcript"] == ""
              and s["led"] == "aus")
        s = phase("sm_PLAY#1")
        check("E13 Play → nichts (nur Protokoll)", s and s["job_zustand"] == "READY")
    except Exception as e:
        check("Ablauf ohne Ausnahme", False, repr(e))
    finally:
        app.after(0, app.destroy)


threading.Thread(target=ablauf, daemon=True).start()
app.mainloop()
print(f"Strg+V-Aufrufe: {TASTEN}")
print("FAILS:", fails)
sys.exit(1 if fails else 0)
