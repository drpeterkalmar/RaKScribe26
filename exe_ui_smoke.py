#!/usr/bin/env python3
"""exe_ui_smoke.py — macOS-Smoke-Test der EXE-Oberfläche v3.0 (Windows-Module gestubbt).
Rendert: (a) gesperrt ohne Schlüssel, (b) entsperrt mit Befund-Formatierung. Screenshots via PIL.ImageGrab."""
import sys, types, os, time, pathlib, importlib.util, json, faulthandler
faulthandler.dump_traceback_later(60, exit=True)
SHOTS = pathlib.Path.home() / "dev/RaKScribe26-work/shots"
MODE = sys.argv[1]  # locked | ready
for name in ["keyboard", "win32clipboard", "pyperclip"]:
    m = types.ModuleType(name); m.add_hotkey = lambda *a, **k: None; m.press_and_release = lambda *a, **k: None
    sys.modules[name] = m
sd = types.ModuleType("sounddevice")
class _D: device = [0, 0]
sd.default = _D(); sd.query_devices = lambda: [{"name": "Mikrofon (Realtek USB Audio)", "max_input_channels": 1}]
sys.modules["sounddevice"] = sd
oa = types.ModuleType("openai"); oa.OpenAI = lambda **k: None; sys.modules["openai"] = oa
src = pathlib.Path.home() / "dev/RaKScribe26/source_code/RaKScribe.py"
tmpdir = pathlib.Path("/tmp/rks_exe_smoke"); tmpdir.mkdir(exist_ok=True)
os.chdir(tmpdir)
os.environ["APPDATA"] = str(tmpdir / "appdata")
code = src.read_text()
# BASE_DIR auf Temp-Ordner zwingen (kein Key neben der "EXE")
spec = importlib.util.spec_from_loader("rks", loader=None)
mod = importlib.util.module_from_spec(spec)
mod.__file__ = str(tmpdir / "RaKScribe.py")
sys.argv = [str(tmpdir / "RaKScribe.py")]
if MODE == "ready":
    (tmpdir / "appdata" / "RaKScribe").mkdir(parents=True, exist_ok=True)
    (tmpdir / "appdata" / "RaKScribe" / "rakscribe-praxis-key.json").write_text(pathlib.Path(os.environ["PRAXIS_KEY"]).read_text())
code = code.replace('if __name__ == "__main__":', 'if False:')
exec(compile(code, str(src), "exec"), mod.__dict__)
ctk = mod.ctk
ctk.set_appearance_mode("dark")
app = mod.RaKScribeApp()
app.geometry("1240x820+40+40")
def shot():
    app.update_idletasks()
    import subprocess
    out = SHOTS / f"exe_{MODE}.png"
    x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
    r = subprocess.run(["screencapture", "-x", "-R", f"{x},{y},{w},{h}", str(out)], capture_output=True, timeout=15)
    print("SHOT", out, r.returncode, out.exists() and out.stat().st_size)
    print("STATE gate=", app.gate is not None, "record_btn=", app.record_btn.cget("state"), "status=", app._status_raw,
          "keys_ready=", mod.keys_ready())
    if MODE == "ready":
        tb = app.result_text._textbox
        print("hidden-tags:", len(tb.tag_ranges("md_hidden")) // 2, "title-tags:", len(tb.tag_ranges("md_title")) // 2,
              "head-tags:", len(tb.tag_ranges("md_head")) // 2)
        print("text keeps markdown:", app.result_text.get("1.0", "end").startswith("## "))
    app.destroy()
def fill():
    app.transcript_text.insert("1.0", "Röntgen und Sonographie des linken Schultergelenkes: Tenosynovitis der langen Bizepssehne, "
                                      "Tendinopathie und Tendinosis calcarea der Supraspinatussehne mit Begleitbursitis, ansonsten unauffällig.")
    app.result_text.insert("1.0", "## Röntgen und Sonographie des Schultergelenkes links\n\n## Befund\nFlüssigkeitsansammlung in der Sehnenscheide "
                                   "des Caput longum des M. biceps brachii. Supraspinatussehne echoarm verdickt mit intratendinösen Verkalkungen. "
                                   "Bursa subacromialis-subdeltoidea verdickt.\n\n## Ergebnis\n1. Tenosynovitis der langen Bizepssehne links.\n"
                                   "2. Tendinopathie und Tendinosis calcarea der Supraspinatussehne.\n3. Begleitbursitis subacromialis-subdeltoidea.")
    app.update_level_bar(4500)
app.after(600, lambda: (fill() if MODE == "ready" else None, app.after(900, shot)))
app.mainloop()
