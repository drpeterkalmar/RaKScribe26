#!/usr/bin/env python3
"""exe_ui_test.py — Automatischer Oberflächen-Test der RaKScribe-Windows-EXE (läuft auf GitHub Actions, windows-latest).

Was geprüft wird (echte EXE aus dem Release, echtes Windows, kein Mikrofon, KEIN echter Praxis-Schlüssel):
  A  Start ohne Schlüssel  → Fenster erscheint, Sperre „Praxis-Schlüssel laden“ sichtbar, Aufnahme-Button gesperrt
  B  F10 ohne Schlüssel    → startet KEINE Aufnahme (Status bleibt „Gesperrt“)
  C  Start mit Test-Schlüssel (selbst erzeugter Dummy, NICHT der Praxis-Schlüssel) im Benutzerprofil
                           → Sperre weg, Aufnahme-Button aktiv, Befund formatiert (## versteckt, Überschriften fett),
                             Kopiertext bleibt Markdown
Die EXE schreibt ihren UI-Zustand per Selbsttest-Modus (RAKSCRIBE_SELFTEST) als JSON; dazu je ein Screenshot.
Ergebnis: <out>/report.md, <out>/results.json, <out>/*.png  — Exit 1 bei FAIL.

Aufruf:  python exe_ui_test.py <pfad/zur/rakscribe26.exe> <ausgabe-ordner> [versions-tag]
"""
import ctypes, json, os, pathlib, shutil, subprocess, sys, tempfile, time

EXE = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
TAG = sys.argv[3] if len(sys.argv) > 3 else "?"
results = []


def check(case, name, ok, detail=""):
    results.append({"case": case, "check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + f"[{case}] {name}" + (f"  ({detail})" if detail else ""), flush=True)


def screen_size():
    u = ctypes.windll.user32
    u.SetProcessDPIAware()
    return u.GetSystemMetrics(0), u.GetSystemMetrics(1)


def find_window(title_part, timeout=60):
    import win32gui
    t0 = time.time()
    while time.time() - t0 < timeout:
        hits = []
        win32gui.EnumWindows(lambda h, _: hits.append(h) if win32gui.IsWindowVisible(h) and title_part in win32gui.GetWindowText(h) else None, None)
        if hits:
            return hits[0], time.time() - t0
        time.sleep(0.5)
    return None, timeout


def screenshot(hwnd, path):
    import win32gui
    from PIL import ImageGrab
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.8)
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    img = ImageGrab.grab(bbox=(max(l, 0), max(t, 0), r, b), all_screens=True)
    img.save(path)
    return img.size


def wait_json(path, phase, timeout=40):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
            if phase in d:
                return d[phase]
        except Exception:
            pass
        time.sleep(0.5)
    return None


def dummy_key():
    """Selbst erzeugter Test-Schlüssel (Form wie praxis-key.json, aber wertlos: zufälliger RSA-Key, Dummy-Projekt)."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    pem = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return {"vertex_api_key": "AQ.selftest-dummy-key-not-valid",
            "stt": {"type": "service_account", "project_id": "selftest-dummy", "private_key_id": "0" * 40,
                    "private_key": pem, "client_email": "selftest@selftest-dummy.iam.gserviceaccount.com",
                    "client_id": "0", "token_uri": "https://oauth2.googleapis.com/token"}}


def run_case(case, with_key, demo, send_f10):
    work = pathlib.Path(tempfile.mkdtemp(prefix=f"rks_{case}_"))
    shutil.copy(EXE, work / EXE.name)
    appdata = work / "appdata"; appdata.mkdir()
    if with_key:
        (appdata / "RaKScribe").mkdir()
        (appdata / "RaKScribe" / "rakscribe-praxis-key.json").write_text(json.dumps(dummy_key()), encoding="utf-8")
    state = work / "selftest.json"
    sw, sh = screen_size()
    w, h = min(1240, sw - 40), min(820, sh - 80)
    env = dict(os.environ, APPDATA=str(appdata), RAKSCRIBE_SELFTEST=str(state),
               RAKSCRIBE_SELFTEST_GEOMETRY=f"{w}x{h}+10+10", RAKSCRIBE_SELFTEST_DEMO="1" if demo else "0",
               RAKSCRIBE_SELFTEST_F10_DUMP_MS="12000")
    p = subprocess.Popen([str(work / EXE.name)], cwd=work, env=env)
    try:
        hwnd, t_start = find_window("RaKScribe", 90)
        check(case, "Fenster erscheint", hwnd is not None, f"{t_start:.1f} s bis zum Fenster")
        if not hwnd:
            return None
        st = wait_json(state, "ready")
        check(case, "Selbsttest-Zustand gemeldet", st is not None)
        if st is None:
            err = pathlib.Path(str(state) + ".err")
            if err.exists():
                print(err.read_text())
            return None
        size = screenshot(hwnd, OUT / f"{case}.png")
        after = None
        if send_f10:
            import win32api, win32con
            win32api.keybd_event(win32con.VK_F10, 0, 0, 0); time.sleep(0.1)
            win32api.keybd_event(win32con.VK_F10, 0, win32con.KEYEVENTF_KEYUP, 0)
            after = wait_json(state, "after_f10", 20)
        return {"state": st, "after_f10": after, "screenshot": f"{case}.png", "size": size, "t_start": round(t_start, 1)}
    finally:
        p.kill()
        time.sleep(1)


print(f"RaKScribe EXE-UI-Test {TAG} — Bildschirm {screen_size()}", flush=True)

# A + B: ohne Schlüssel
a = run_case("A_gesperrt", with_key=False, demo=False, send_f10=True)
if a:
    s = a["state"]
    check("A_gesperrt", "Titel enthält Version 3", "3.0" in s["title"], s["title"])
    check("A_gesperrt", "Sperre sichtbar", s["gate_visible"])
    check("A_gesperrt", "Aufnahme-Button gesperrt", s["record_btn_state"] == "disabled", s["record_btn_state"])
    check("A_gesperrt", "Status = Gesperrt", s["status"] == "LOCKED", s["status"])
    check("A_gesperrt", "Schlüssel-Anzeige = Kein Schlüssel", "Kein" in s["key_chip"], s["key_chip"])
    af = a["after_f10"]
    check("B_F10", "F10 ohne Schlüssel startet keine Aufnahme", af is not None and af["status"] == "LOCKED",
          af["status"] if af else "kein Zustand nach F10")

# C: mit Test-Schlüssel + Demo-Befund
c = run_case("C_entsperrt", with_key=True, demo=True, send_f10=False)
if c:
    s = c["state"]
    check("C_entsperrt", "Sperre weg", not s["gate_visible"])
    check("C_entsperrt", "Aufnahme-Button aktiv", s["record_btn_state"] == "normal", s["record_btn_state"])
    check("C_entsperrt", "Status = Bereit", s["status"] == "READY", s["status"])
    check("C_entsperrt", "Schlüssel-Anzeige = aktiv", "aktiv" in s["key_chip"], s["key_chip"])
    check("C_entsperrt", "Befund: 3 Überschriften formatiert", s["report_heading_tags"] == 3, str(s["report_heading_tags"]))
    check("C_entsperrt", "Befund: ## ausgeblendet", s["report_hidden_hash_tags"] == 3, str(s["report_hidden_hash_tags"]))
    check("C_entsperrt", "Kopiertext bleibt Markdown", s["report_text_keeps_markdown"])

ok = all(r["ok"] for r in results) and a and c
(OUT / "results.json").write_text(json.dumps({"tag": TAG, "ok": bool(ok), "results": results, "A": a, "C": c},
                                             ensure_ascii=False, indent=1), encoding="utf-8")
lines = [f"## Windows-UI-Test RaKScribe {TAG}", "",
         f"Echtes Windows (GitHub Actions, `{os.environ.get('ImageOS', 'windows')}`), Bildschirm {screen_size()[0]}×{screen_size()[1]}, "
         f"getestet {time.strftime('%d.%m.%Y %H:%M')} UTC. Test-Schlüssel ist ein selbst erzeugter Dummy — kein Praxis-Schlüssel, "
         "kein Mikrofon, keine Google-Aufrufe.", "",
         f"**Ergebnis: {'✅ alle Prüfungen bestanden' if ok else '❌ Fehler — siehe Tabelle'}** "
         f"({sum(r['ok'] for r in results)}/{len(results)})", "",
         "| Fall | Prüfung | Ergebnis | Detail |", "|---|---|---|---|"]
lines += [f"| {r['case']} | {r['check']} | {'✅' if r['ok'] else '❌'} | {r['detail']} |" for r in results]
lines += ["", "Screenshots: `A_gesperrt.png` (ohne Schlüssel), `C_entsperrt.png` (mit Test-Schlüssel + Demo-Befund)."]
(OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
sys.exit(0 if ok else 1)
