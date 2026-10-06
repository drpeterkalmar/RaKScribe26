#!/usr/bin/env python3
"""exe_ui_test.py — Automatischer Oberflächen-Test der RaKScribe-Windows-EXE (läuft auf GitHub Actions, windows-latest).

Was geprüft wird (echte EXE aus dem Release, echtes Windows, kein Mikrofon, KEIN echter Praxis-Schlüssel):
  A  Start ohne Schlüssel  → Fenster erscheint, Sperre „Praxis-Schlüssel laden“ sichtbar, Aufnahme-Button gesperrt
  B  F10 ohne Schlüssel    → startet KEINE Aufnahme (Status bleibt „Gesperrt“)
  C  Start mit Test-Schlüssel (selbst erzeugter Dummy, NICHT der Praxis-Schlüssel) im Benutzerprofil
                           → Sperre weg, Aufnahme-Button aktiv, Befund formatiert (## versteckt, Überschriften fett),
                             Kopiertext bleibt Markdown
  D  F10 während „Befund wird erstellt" (Selbsttest simuliert die Verarbeitung) → startet KEINE Aufnahme;
     F9 bricht die Verarbeitung ab → Bereit (Umbau Schritt 4, Gutachten P1-2)
Die EXE schreibt ihren UI-Zustand per Selbsttest-Modus (RAKSCRIBE_SELFTEST) als JSON; dazu je ein Screenshot.
Ergebnis: <out>/report.md, <out>/results.json, <out>/*.png  — Exit 1 bei FAIL.

Aufruf:  python exe_ui_test.py <pfad/zur/rakscribe26.exe> <ausgabe-ordner> [versions-tag]
"""
import ctypes, json, os, pathlib, shutil, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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


def rks_windows(title_part="RaKScribe"):
    import win32gui
    hits = []
    win32gui.EnumWindows(lambda h, _: hits.append(h) if win32gui.IsWindowVisible(h) and title_part in win32gui.GetWindowText(h) else None, None)
    return hits


def find_window(title_part, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        hits = rks_windows(title_part)
        if hits:
            return hits[0], time.time() - t0
        time.sleep(0.5)
    return None, timeout


def kill_all(p):
    # PyInstaller-onefile: Bootloader + Kindprozess → ganzen Baum beenden, dann warten bis alle Fenster weg sind
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "rakscribe26.exe"], capture_output=True)
    t0 = time.time()
    while rks_windows() and time.time() - t0 < 20:
        time.sleep(0.5)


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


def press(vk, wait=0.1):
    import win32api, win32con
    win32api.keybd_event(vk, 0, 0, 0); time.sleep(0.1)
    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(wait)


def fall_d(state):
    """F10/F9 während der (simulierten) Verarbeitung. Liefert die drei Zustände oder None."""
    pathlib.Path(str(state) + ".trigger").write_text("simulate_processing", encoding="utf-8")
    sim = wait_json(state, "simulate_processing", 20)
    if sim is None:
        return None
    # Künstliche Tastendrücke erreichen den keyboard-Hook auf GitHub-Windows nie (seit 3.2.2: „0× empfangen“) —
    # deshalb ruft der Selbsttest denselben F10/F9-Handler wie der Hotkey (Phase taste_f10 / taste_f9).
    pathlib.Path(str(state) + ".trigger").write_text("taste_f10", encoding="utf-8")
    nach_f10 = wait_json(state, "taste_f10", 20)
    pathlib.Path(str(state) + ".trigger").write_text("taste_f9", encoding="utf-8")
    nach_f9 = wait_json(state, "taste_f9", 20)
    return {"sim": sim, "nach_f10": nach_f10, "nach_f9": nach_f9}


def run_case(case, with_key, demo, send_f10, old_prompt=False, mit_fall_d=False):
    work = pathlib.Path(tempfile.mkdtemp(prefix=f"rks_{case}_"))
    shutil.copy(EXE, work / EXE.name)
    if old_prompt:
        # v3.2: alte Prompt-Datei ohne Versionsmarker neben der EXE (wie in Georgs Ordner) — darf NICHT gewinnen
        (work / "radiology_prompt_v4.txt").write_text("<role>alter v4-Prompt</role>\n{template_body}\n{roh_text}", encoding="utf-8")
    appdata = work / "appdata"; appdata.mkdir()
    if with_key:
        (appdata / "RaKScribe").mkdir()
        (appdata / "RaKScribe" / "rakscribe-praxis-key.json").write_text(json.dumps(dummy_key()), encoding="utf-8")
    state = work / "selftest.json"
    env = dict(os.environ, APPDATA=str(appdata), RAKSCRIBE_SELFTEST=str(state),
               RAKSCRIBE_SELFTEST_GEOMETRY="zoomed", RAKSCRIBE_SELFTEST_DEMO="1" if demo else "0")
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
            time.sleep(2.5)
            # falls Windows F10 als Menütaste behandelt hat: Menümodus mit ESC verlassen
            win32api.keybd_event(win32con.VK_ESCAPE, 0, 0, 0); time.sleep(0.1)
            win32api.keybd_event(win32con.VK_ESCAPE, 0, win32con.KEYEVENTF_KEYUP, 0)
            pathlib.Path(str(state) + ".trigger").write_text("after_f10", encoding="utf-8")
            after = wait_json(state, "after_f10", 20)
        d = fall_d(state) if mit_fall_d else None
        return {"state": st, "after_f10": after, "fall_d": d, "screenshot": f"{case}.png", "size": size,
                "t_start": round(t_start, 1)}
    finally:
        kill_all(p)


print(f"RaKScribe EXE-UI-Test {TAG} — Bildschirm {screen_size()}", flush=True)

# A + B: ohne Schlüssel
a = run_case("A_gesperrt", with_key=False, demo=False, send_f10=True)
if a:
    s = a["state"]
    # Titel muss den Release-Tag tragen (TAG kommt vom Workflow, z. B. "3.1.0"); Test-Build (test-<Lauf>) oder ohne
    # Tag: die Version aus der Datei VERSION im ausgecheckten Repo (Umbau Schritt 21)
    _version_datei = pathlib.Path(__file__).resolve().parents[2] / "VERSION"
    if TAG in ("?", "") or TAG.startswith("test-"):
        exp_ver = _version_datei.read_text(encoding="utf-8").strip() if _version_datei.exists() else "3."
    else:
        exp_ver = TAG.lstrip("v")
    check("A_gesperrt", f"Titel enthält Version {exp_ver}", exp_ver in s["title"], s["title"])
    check("A_gesperrt", "Sperre sichtbar", s["gate_visible"])
    check("A_gesperrt", "Aufnahme-Button gesperrt", s["record_btn_state"] == "disabled", s["record_btn_state"])
    check("A_gesperrt", "Status = Gesperrt", s["status"] == "LOCKED", s["status"])
    check("A_gesperrt", "Schlüssel-Anzeige = Kein Schlüssel", "Kein" in s["key_chip"], s["key_chip"])
    af = a["after_f10"]
    check("B_F10", "F10 ohne Schlüssel startet keine Aufnahme", af is not None and af["status"] == "LOCKED",
          (f"Status {af['status']}, F10-Hotkey {af['toggle_calls']}× empfangen") if af else "kein Zustand nach F10")
    check("A_gesperrt", "Mikrofon-Auswahl nicht leer", bool(s.get("mic_dropdown")), s.get("mic_dropdown", ""))

# C: mit Test-Schlüssel + Demo-Befund
c = run_case("C_entsperrt", with_key=True, demo=True, send_f10=False, old_prompt=True, mit_fall_d=True)
if c:
    s = c["state"]
    check("C_entsperrt", "Sperre weg", not s["gate_visible"])
    check("C_entsperrt", "Aufnahme-Button aktiv", s["record_btn_state"] == "normal", s["record_btn_state"])
    check("C_entsperrt", "Status = Bereit", s["status"] == "READY", s["status"])
    check("C_entsperrt", "Schlüssel-Anzeige = aktiv", "aktiv" in s["key_chip"], s["key_chip"])
    check("C_entsperrt", "Befund: 3 Überschriften formatiert", s["report_heading_tags"] == 3, str(s["report_heading_tags"]))
    check("C_entsperrt", "Befund: ## ausgeblendet", s["report_hidden_hash_tags"] == 3, str(s["report_hidden_hash_tags"]))
    check("C_entsperrt", "Kopiertext bleibt Markdown", s["report_text_keeps_markdown"])
    # v3.2: gebündelter versionierter Prompt gewinnt gegen alte radiology_prompt_v4.txt; Regel-Modul im Bundle
    check("C_entsperrt", "Alte radiology_prompt_v4.txt ignoriert (eingebauter Prompt)",
          s.get("prompt_quelle") == "eingebaut" and bool(s.get("prompt_version")),
          f"{s.get('prompt_quelle')} / {s.get('prompt_version')}")
    check("C_entsperrt", "Mehrere Regionen → 2 Befunde", s.get("multi_region_segmente") == 2, str(s.get("multi_region_segmente")))
    check("C_entsperrt", "Vorlagen-Vorrang gebündelt (Vorfuß)", s.get("vorlage_vorfuss") == "vorfuß_in_2_ebenen", str(s.get("vorlage_vorfuss")))
    check("C_entsperrt", "Vorlagen-Vorrang gebündelt (MRT Knie)", s.get("vorlage_mrt_knie") == "mr_des_kniegelenkes:", str(s.get("vorlage_mrt_knie")))
    check("C_entsperrt", "F10 während Verarbeitung wird ignoriert", s.get("f10_waehrend_verarbeitung") == "ignorieren", str(s.get("f10_waehrend_verarbeitung")))
    check("C_entsperrt", "Ergebnis wird nummeriert", s.get("ergebnis_nummeriert") is True, str(s.get("ergebnis_nummeriert")))
    check("C_entsperrt", "Phrasenlisten gebündelt (292 Streaming, 68 chirp_3)", s.get("phrasen") == [292, 68], str(s.get("phrasen")))
    sw_, sh_ = s["screen"]
    gw, gh_ = [int(x) for x in s["geometry"].split("+")[0].split("x")]
    check("C_entsperrt", "Fenster passt auf den Bildschirm", gw <= sw_ and gh_ <= sh_, f"{gw}×{gh_} auf {sw_}×{sh_}")
    # D (Umbau Schritt 4, Gutachten P1-2): F10 während „Befund wird erstellt" startet keine Aufnahme, F9 bricht ab
    d = c.get("fall_d") or {}
    sim, f10, f9 = d.get("sim"), d.get("nach_f10"), d.get("nach_f9")
    check("D_verarbeitung", "Verarbeitung simuliert", bool(sim) and sim.get("status") == "PROCESSING",
          str(sim and sim.get("status")))
    check("D_verarbeitung", "F10 während Verarbeitung startet keine Aufnahme",
          bool(sim and f10) and f10["status"] == "PROCESSING" and not f10.get("is_recording")
          and f10["toggle_calls"] > sim["toggle_calls"],
          (f"Status {f10['status']}, Aufnahme {f10.get('is_recording')}, F10-Hotkey "
           f"{f10['toggle_calls'] - sim['toggle_calls']}× empfangen") if (sim and f10) else "kein Zustand nach F10")
    check("D_verarbeitung", "F9 bricht die Verarbeitung ab → Bereit", bool(f9) and f9["status"] == "READY"
          and f9.get("job_zustand") == "READY", str(f9 and (f9["status"], f9.get("job_zustand"))))

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
