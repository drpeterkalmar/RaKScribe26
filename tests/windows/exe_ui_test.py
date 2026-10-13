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
  E  v3.8.0 SpeechMike (ohne Gerät): hidapi im Bündel, Lese-Thread läuft ohne Gerät; Tastenberichte gehen über DENSELBEN
     Weg wie vom Gerät (Selbsttest-Phase sm_<Taste> → Dekodierer → Handler); Mikrofon/Google/chirp_3 als Attrappen
     (RAKSCRIBE_SELFTEST_FAKEAUDIO): Record → Pause (repariert, kein Befund) → EOL (nichts) → Weiter → INS (Befund zur
     Kontrolle, nichts eingefügt) → von Hand ändern → EOL (genau dieser Text in der Windows-Zwischenablage, alles leer);
     F2/Nur Text, F1 = Neu, Play = nichts; gesperrt: Record startet nichts
  F  v3.10.0 CAS-Auftrag der RaKScribe-Brücke: Auftrag (cas_auftrag.json) → Band „CAS-Diktat <Nr> (kp)“ → Testbefund
     → EOL schreibt die Ergebnis-Datei statt Strg+V (Antwort „fertig“, test=true); echtes Attrappen-Diktat Record → INS
     → EOL liefert Text + WAV; Abbrechen-Knopf → „abgebrochen“
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


def fall_e(state):
    """v3.8.0 SpeechMike-Ablauf über die Selbsttest-Phasen sm_<Taste>#n (gleicher Handler-Weg wie das Gerät)."""
    def ph(name, warten=0.0):
        if warten:
            time.sleep(warten)
        pathlib.Path(str(state) + ".trigger").write_text(name, encoding="utf-8")
        return wait_json(state, name, 30)
    e = {}
    e["record1"] = ph("sm_RECORD#1")
    e["pause"] = ph("sm_RECORD#2", 2.0)
    e["eol_pause"] = ph("sm_EOL#1")
    e["weiter"] = ph("sm_RECORD#3")
    e["ins"] = ph("sm_INS#1", 1.5)
    e["geaendert"] = ph("befund_aendern")
    e["eol"] = ph("sm_EOL#2")
    e["f2_an"] = ph("sm_F2#1")
    ph("sm_RECORD#4")
    e["ins_nurtext"] = ph("sm_INS#2", 1.5)
    e["eol_nurtext"] = ph("sm_EOL#3")
    e["f2_aus"] = ph("sm_F2#2")
    ph("sm_RECORD#5")
    e["f1"] = ph("sm_F1#1")
    e["play"] = ph("sm_PLAY#1")
    return e


def fall_f(state, work):
    """v3.10.0 CAS-Auftrag der Brücke über die Datei-Schnittstelle (wie bruecke/auftrag.py) + Selbsttest-Phasen cas_*."""
    ordner = work / "localappdata" / "RaKScribe"
    ordner.mkdir(parents=True, exist_ok=True)

    def auftrag(nr, aid):
        (ordner / "cas_auftrag.json").write_text(json.dumps(
            {"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": "kp", "bruecke_pid": os.getpid(),
             "zeit": time.time(), "zeit_text": "", "testbefund": False}), encoding="utf-8")
        time.sleep(2.0)

    def antwort(aid):
        try:
            return json.loads((ordner / f"cas_antwort_{aid}.json").read_text(encoding="utf-8"))
        except Exception:
            return {}

    def ph(name, warten=0.0):
        if warten:
            time.sleep(warten)
        pathlib.Path(str(state) + ".trigger").write_text(name, encoding="utf-8")
        return wait_json(state, name, 30)
    f = {}
    auftrag("20261013005", "uitest1")
    f["angenommen"] = ph("cas_status#1")
    f["antwort1"] = antwort("uitest1")
    f["testbefund"] = ph("cas_testbefund")
    f["eol_test"] = ph("cas_eol#1")
    f["antwort1_ende"] = antwort("uitest1")
    txt = ordner / "cas_ergebnis_20261013005.txt"
    f["ergebnis_test"] = txt.read_text(encoding="utf-8") if txt.exists() else None
    auftrag("20261013006", "uitest2")
    f["angenommen2"] = ph("cas_status#2")
    ph("sm_RECORD#9")
    f["ins2"] = ph("sm_INS#9", 2.0)
    f["eol2"] = ph("cas_eol#2")
    f["antwort2"] = antwort("uitest2")
    wav = f["antwort2"].get("wav_datei")
    f["wav2_bytes"] = os.path.getsize(wav) if wav and os.path.exists(wav) else 0
    auftrag("20261013007", "uitest3")
    ph("cas_status#3")
    f["abbrechen"] = ph("cas_abbrechen")
    f["antwort3"] = antwort("uitest3")
    return f


def run_case(case, with_key, demo, send_f10, old_prompt=False, mit_fall_d=False, fake_audio=False, mit_fall_e=False,
             sm_gesperrt=False, mit_fall_f=False):
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
    env = dict(os.environ, APPDATA=str(appdata), LOCALAPPDATA=str(work / "localappdata"), RAKSCRIBE_SELFTEST=str(state),
               RAKSCRIBE_SELFTEST_GEOMETRY="zoomed", RAKSCRIBE_SELFTEST_DEMO="1" if demo else "0",
               RAKSCRIBE_SELFTEST_FAKEAUDIO="1" if fake_audio else "0")
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
        sm = None
        if sm_gesperrt:  # v3.8.0: SpeechMike-Record ohne Schlüssel
            pathlib.Path(str(state) + ".trigger").write_text("sm_RECORD#0", encoding="utf-8")
            sm = wait_json(state, "sm_RECORD#0", 20)
        e = fall_e(state) if mit_fall_e else None
        f = fall_f(state, work) if mit_fall_f else None
        if e:
            try:
                screenshot(hwnd, OUT / f"{case}_ende.png")
            except Exception:
                pass
        return {"state": st, "after_f10": after, "fall_d": d, "sm_gesperrt": sm, "fall_e": e, "fall_f": f,
                "screenshot": f"{case}.png",
                "size": size, "t_start": round(t_start, 1)}
    finally:
        kill_all(p)


print(f"RaKScribe EXE-UI-Test {TAG} — Bildschirm {screen_size()}", flush=True)

# A + B: ohne Schlüssel
a = run_case("A_gesperrt", with_key=False, demo=False, send_f10=True, sm_gesperrt=True)
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
    # v3.8.0 SpeechMike: hidapi im Bündel, Lese-Thread läuft ohne Gerät ohne Fehler, Record ohne Schlüssel startet nichts
    check("A_gesperrt", "hidapi im EXE-Bündel (import hid)", str(s.get("hid", "")).startswith("hidapi"), str(s.get("hid")))
    check("A_gesperrt", "SpeechMike-Leser läuft ohne Gerät (sucht weiter)", s.get("speechmike_thread") is True
          and s.get("speechmike_verbunden") is None, f"{s.get('speechmike_thread')} / {s.get('speechmike_verbunden')}")
    smg = a.get("sm_gesperrt")
    check("A_gesperrt", "SpeechMike-Record ohne Schlüssel startet keine Aufnahme", bool(smg) and smg["status"] == "LOCKED"
          and not smg.get("is_recording"), str(smg and smg["status"]))

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

# E (v3.8.0): SpeechMike-Ablauf mit Attrappen für Mikrofon/Google/chirp_3 (Tasten über denselben Handler-Weg)
e_lauf = run_case("E_speechmike", with_key=True, demo=False, send_f10=False, fake_audio=True, mit_fall_e=True,
                  mit_fall_f=True)
E = (e_lauf or {}).get("fall_e") or {}
NORMAL = "Kniegelenk rechts in 2 Ebenen unauffällig."


def ce(name, ok, detail=""):
    check("E_speechmike", name, ok, detail)


def g(k, f, default=None):
    return (E.get(k) or {}).get(f, default)


ce("Record → Aufnahme, LED rot", g("record1", "job_zustand") == "RECORDING" and g("record1", "led") == "aufnahme",
   f"{g('record1', 'job_zustand')} / {g('record1', 'led')}")
ce("Record → Pause (LED rot blinkend), Abschnitt sofort repariert, kein Befund",
   g("pause", "job_zustand") == "PAUSED" and g("pause", "led") == "pause" and g("pause", "transcript") == NORMAL
   and "repariert" in str(g("pause", "repariert", "")) and g("pause", "result") == "",
   f"{g('pause', 'job_zustand')} / {g('pause', 'transcript')!r} / {g('pause', 'repariert')!r}")
ce("EOL in der Pause → nichts gesendet, Hinweis", g("eol_pause", "job_zustand") == "PAUSED"
   and "Erst INS" in str(g("eol_pause", "hinweis", "")) and g("eol_pause", "einfuegungen") == 0, str(g("eol_pause", "hinweis")))
ce("Record → weiter", g("weiter", "job_zustand") == "RECORDING")
ce("INS → Befund rechts zur Kontrolle, nichts eingefügt/kopiert, LED grün",
   g("ins", "status") == "KONTROLLE" and str(g("ins", "result", "")).startswith("## Kniegelenk") and g("ins", "led") == "befund_bereit"
   and g("ins", "einfuegungen") == 0 and not str(g("ins", "zwischenablage", "")).startswith("## "),
   f"{g('ins', 'status')} / {str(g('ins', 'result', ''))[:30]!r} / {g('ins', 'led')} / {str(g('ins', 'zwischenablage', ''))[:30]!r}")
geaendert = str(g("geaendert", "result", ""))
ce("Befund von Hand geändert", geaendert.endswith("Von Hand ergänzt."), geaendert[-30:])
ce("EOL → genau der geänderte Befund in der Windows-Zwischenablage, alles leer, LED aus",
   g("eol", "zwischenablage") == geaendert.strip() and g("eol", "result") == "" and g("eol", "transcript") == ""
   and g("eol", "led") == "aus", f"{str(g('eol', 'zwischenablage', ''))[-30:]!r} / {g('eol', 'hinweis')}")
ce("… Einfügen nur ins sicher aktivierte Fremdfenster, sonst nur kopiert (Hinweis)",
   "eingefügt in" in str(g("eol", "hinweis", "")) or "Befund kopiert" in str(g("eol", "hinweis", "")), str(g("eol", "hinweis")))
ce("F2 → Nur Text an", g("f2_an", "nur_text") is True)
ce("Nur Text: INS → korrigierter Text ohne Überschriften, nichts eingefügt", g("ins_nurtext", "result") == NORMAL
   and g("ins_nurtext", "status") == "KONTROLLE", repr(g("ins_nurtext", "result")))
ce("Nur Text: EOL → genau dieser Text weitergeschickt, leer", g("eol_nurtext", "zwischenablage") == NORMAL
   and g("eol_nurtext", "result") == "")
ce("F2 → Nur Text aus", g("f2_aus", "nur_text") is False)
ce("F1 → Neu: Aufnahme verworfen, bereit, LED aus", g("f1", "job_zustand") == "READY" and g("f1", "transcript") == ""
   and g("f1", "led") == "aus")
ce("Play → nichts (nur Protokoll)", g("play", "job_zustand") == "READY")

# F (v3.10.0): CAS-Auftrag der RaKScribe-Brücke — EOL schreibt eine Datei statt Strg+V
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "source_code"))
import cas_auftrag  # noqa: E402  (ohne Windows-/UI-Abhängigkeiten)
F = (e_lauf or {}).get("fall_f") or {}


def cf(name, ok, detail=""):
    check("F_cas", name, ok, detail)


def gf(k, feld, default=None):
    return (F.get(k) or {}).get(feld, default)


cf("Auftrag angenommen, Band „CAS-Diktat 20261013005 (kp)“ sichtbar",
   gf("angenommen", "cas") == "20261013005" and "CAS-Diktat 20261013005 (kp)" in str(gf("angenommen", "cas_band", ""))
   and gf("angenommen", "cas_band_sichtbar") is True and (F.get("antwort1") or {}).get("status") == "angenommen",
   f"{gf('angenommen', 'cas')} / {gf('angenommen', 'cas_band')!r} / {gf('angenommen', 'cas_band_sichtbar')}")
cf("Testbefund-Knopf → TEST-Text rechts, „Befund prüfen“",
   gf("testbefund", "result") == cas_auftrag.TESTBEFUND and gf("testbefund", "status") == "KONTROLLE",
   f"{str(gf('testbefund', 'result', ''))[:40]!r} / {gf('testbefund', 'status')}")
cf("EOL → Ergebnis-Datei = Testbefund, Antwort fertig (test), kein Strg+V, Band weg, alles leer",
   F.get("ergebnis_test") == cas_auftrag.TESTBEFUND and (F.get("antwort1_ende") or {}).get("status") == "fertig"
   and (F.get("antwort1_ende") or {}).get("test") is True and gf("eol_test", "einfuegungen") == gf("testbefund", "einfuegungen")
   and gf("eol_test", "cas") is None and gf("eol_test", "cas_band_sichtbar") is False and gf("eol_test", "result") == "",
   f"{F.get('antwort1_ende')} / Strg+V {gf('testbefund', 'einfuegungen')}→{gf('eol_test', 'einfuegungen')}")
cf("Attrappen-Diktat: Record → INS → Befund zur Kontrolle (nichts eingefügt)",
   gf("ins2", "status") == "KONTROLLE" and str(gf("ins2", "result", "")).startswith("## Kniegelenk")
   and gf("ins2", "einfuegungen") == gf("eol_test", "einfuegungen"), f"{gf('ins2', 'status')} / {str(gf('ins2', 'result', ''))[:30]!r}")
cf("EOL → Text + WAV an die Brücke (Antwort fertig)", (F.get("antwort2") or {}).get("status") == "fertig"
   and F.get("wav2_bytes", 0) > 44 and gf("eol2", "einfuegungen") == gf("ins2", "einfuegungen"),
   f"{F.get('antwort2')} / WAV {F.get('wav2_bytes')} Byte")
cf("Abbrechen-Knopf → „abgebrochen“, Band weg", (F.get("antwort3") or {}).get("status") == "abgebrochen"
   and gf("abbrechen", "cas") is None, str(F.get("antwort3")))

ok = all(r["ok"] for r in results) and a and c and e_lauf
(OUT / "results.json").write_text(json.dumps({"tag": TAG, "ok": bool(ok), "results": results, "A": a, "C": c, "E": e_lauf},
                                             ensure_ascii=False, indent=1), encoding="utf-8")
lines = [f"## Windows-UI-Test RaKScribe {TAG}", "",
         f"Echtes Windows (GitHub Actions, `{os.environ.get('ImageOS', 'windows')}`), Bildschirm {screen_size()[0]}×{screen_size()[1]}, "
         f"getestet {time.strftime('%d.%m.%Y %H:%M')} UTC. Test-Schlüssel ist ein selbst erzeugter Dummy — kein Praxis-Schlüssel, "
         "kein Mikrofon, keine Google-Aufrufe.", "",
         f"**Ergebnis: {'✅ alle Prüfungen bestanden' if ok else '❌ Fehler — siehe Tabelle'}** "
         f"({sum(r['ok'] for r in results)}/{len(results)})", "",
         "| Fall | Prüfung | Ergebnis | Detail |", "|---|---|---|---|"]
lines += [f"| {r['case']} | {r['check']} | {'✅' if r['ok'] else '❌'} | {r['detail']} |" for r in results]
lines += ["", "Screenshots: `A_gesperrt.png` (ohne Schlüssel), `C_entsperrt.png` (mit Test-Schlüssel + Demo-Befund), "
          "`E_speechmike.png` / `E_speechmike_ende.png` (SpeechMike-Ablauf mit Attrappen, danach Fall F CAS-Auftrag)."]
(OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
sys.exit(0 if ok else 1)
