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
  G  v3.11.0 Bereitschaft: Start mit --minimiert → nur Taskleisten-Symbol, nicht vorne; Leerlauf (CPU/Speicher, psutil);
     zweiter Start → keine zweite Instanz, laufende nach vorne (mit --minimiert: still); CAS-Auftrag → vorne, Annahme
     < 1 s → EOL → wieder minimiert; Menü-Haken Autostart → Verknüpfung im echten Autostart-Ordner → wscript → Starter;
     „Anmeldung“ (Verknüpfung öffnen) ohne EXE (X: fehlt) → Starter wartet; EXE erscheint nach 30 s → Start minimiert;
     Starter bei laufender RaKScribe → endet still; Haken aus → alles weg; Starter-Frist (12 s statt 4 h) → endet still
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
    if p is not None:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "rakscribe26.exe"], capture_output=True)
    t0 = time.time()
    while rks_windows() and time.time() - t0 < 20:
        time.sleep(0.5)
    try:  # v3.11.0: auch die Prozesse müssen weg sein (Einzelinstanz-Mutex frei, EXE-Datei nicht mehr gesperrt)
        while rks_prozesse() and time.time() - t0 < 30:
            time.sleep(0.5)
    except ImportError:
        pass


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


REPO = pathlib.Path(__file__).resolve().parents[2]


def rks_prozesse():
    import psutil
    return [p for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower().startswith("rakscribe26")]


def starter_prozesse(skript):
    """Laufende wscript.exe mit diesem Starter-Skript."""
    import psutil
    out = []
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            if (p.info["name"] or "").lower() == "wscript.exe" and any(skript in (a or "") for a in p.info["cmdline"] or []):
                out.append(p.pid)
        except Exception:
            pass
    return out


def leerlauf_messen(dauer=30):
    """CPU-Zeit aller rakscribe26-Prozesse über `dauer` s (in % EINES Kerns) und Speicher wie im Task-Manager:
    Arbeitssatz, privater Arbeitssatz (Spalte „Arbeitsspeicher“), zugesicherte private Bytes; dazu Threads."""
    import psutil
    procs = rks_prozesse()
    vorher = {p.pid: sum(p.cpu_times()[:2]) for p in procs}
    time.sleep(dauer)
    erg, cpu = {"dauer_s": dauer, "prozesse": []}, 0.0
    for p in procs:
        try:
            ct = sum(p.cpu_times()[:2]) - vorher[p.pid]
            mi = p.memory_full_info()
            erg["prozesse"].append({"pid": p.pid, "cpu_s": round(ct, 3), "arbeitssatz_mb": round(mi.rss / 2 ** 20, 1),
                                    "privater_arbeitssatz_mb": round(mi.uss / 2 ** 20, 1),
                                    "private_bytes_mb": round(mi.private / 2 ** 20, 1), "threads": p.num_threads()})
            cpu += ct
        except psutil.Error:
            pass
    erg["cpu_prozent_eines_kerns"] = round(cpu / dauer * 100, 2)
    return erg


def verschieben(von, nach, versuche=40):
    """EXE weg-/zurücklegen („X: fehlt“ / „X: ist da“) — kurz gesperrt (Virenscanner, eben beendeter Prozess) → erneut."""
    for i in range(versuche):
        try:
            shutil.move(str(von), str(nach))
            return
        except OSError:
            if i == versuche - 1:
                raise
            time.sleep(0.5)


def mit_umgebung(werte, fn):
    """fn() mit gesetzten Umgebungsvariablen — os.startfile vererbt sie an wscript und von dort an die EXE."""
    alt = {k: os.environ.get(k) for k in werte}
    os.environ.update(werte)
    try:
        return fn()
    finally:
        for k, v in alt.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def fall_g():
    """v3.11.0 Bereitschaft (eigener Ablauf: Start mit --minimiert, Zweitstarts, Autostart-Starter, Frist)."""
    import win32gui
    import win32com.client
    sys.path.insert(0, str(REPO / "source_code"))
    import bereitschaft  # noqa: E402  (ohne Windows-/UI-Abhängigkeiten; gleiche Vorlage wie in der EXE)
    work = pathlib.Path(tempfile.mkdtemp(prefix="rks_G_"))
    exe = work / EXE.name
    shutil.copy(EXE, exe)
    appdata = work / "appdata"
    (appdata / "RaKScribe").mkdir(parents=True)
    (appdata / "RaKScribe" / "rakscribe-praxis-key.json").write_text(json.dumps(dummy_key()), encoding="utf-8")
    ordner = work / "localappdata" / "RaKScribe"
    ordner.mkdir(parents=True)
    umg = {"APPDATA": str(appdata), "LOCALAPPDATA": str(work / "localappdata")}
    basis = {k: v for k, v in os.environ.items() if not k.startswith("RAKSCRIBE_")}
    vbs = appdata / "RaKScribe" / bereitschaft.STARTER
    starter_log = appdata / "RaKScribe" / bereitschaft.STARTER_LOG
    G = {"exe": str(exe)}

    def ph(state, name, warten=0.0, timeout=30):
        if warten:
            time.sleep(warten)
        pathlib.Path(str(state) + ".trigger").write_text(name, encoding="utf-8")
        return wait_json(state, name, timeout)

    def lies_log(p):
        try:
            return p.read_text(encoding="utf-16")
        except Exception:
            return ""

    def zweiter_start(args):
        t = time.time()
        p2 = subprocess.Popen([str(exe)] + args, cwd=work, env=env1)
        try:
            rc = p2.wait(timeout=120)
        except subprocess.TimeoutExpired:
            rc = "läuft noch"
        return rc, round(time.time() - t, 1)

    # G1: Start mit --minimiert (wie der Starter nach der Anmeldung)
    state = work / "g1.json"
    env1 = dict(basis, **umg, RAKSCRIBE_SELFTEST=str(state))
    p = subprocess.Popen([str(exe), bereitschaft.MINIMIERT], cwd=work, env=env1)
    lnk = None
    try:
        hwnd, t_fenster = find_window("RaKScribe", 90)
        G["start_s"] = round(t_fenster, 1)
        G["start_iconic"] = bool(hwnd and win32gui.IsIconic(hwnd))
        G["ready"] = wait_json(state, "ready", 60)
        G["ready_iconic"] = bool(hwnd and win32gui.IsIconic(hwnd))
        G["ready_vorne"] = bool(hwnd) and win32gui.GetForegroundWindow() == hwnd
        try:
            from PIL import ImageGrab
            bild = ImageGrab.grab(all_screens=True)
            bild.save(OUT / "G_minimiert.png")
            bild.crop((0, max(bild.height - 64, 0), bild.width, bild.height)).save(OUT / "G_taskleiste.png")
        except Exception:
            pass
        if not hwnd or G["ready"] is None:
            return G
        # G2: Leerlauf minimiert
        time.sleep(5)
        G["leerlauf"] = leerlauf_messen(30)
        G["leerlauf_zustand"] = ph(state, "g_leerlauf")
        # G3: zweiter Start (Doppelklick) → keine zweite Instanz, die laufende kommt nach vorne
        n_vor = len(rks_prozesse())
        G["zweit_rc"], G["zweit_s"] = zweiter_start([])
        time.sleep(1.5)
        G["zweit"] = ph(state, "g_zweit")
        G["zweit_fenster"], G["zweit_iconic"] = len(rks_windows()), bool(win32gui.IsIconic(hwnd))
        G["zweit_prozesse"] = [n_vor, len(rks_prozesse())]
        # G4: zweiter Start mit --minimiert (Autostart, während RaKScribe läuft) → still
        ph(state, "minimieren#1")
        G["zweit_min_rc"], G["zweit_min_s"] = zweiter_start([bereitschaft.MINIMIERT])
        time.sleep(1.5)
        G["zweit_min"] = ph(state, "g_zweit_min")
        G["zweit_min_fenster"], G["zweit_min_iconic"] = len(rks_windows()), bool(win32gui.IsIconic(hwnd))
        # G5: CAS-Auftrag wie die Brücke (Vordergrund-Recht weitergeben, Datei ablegen) → vorne → EOL → minimiert
        ctypes.windll.user32.AllowSetForegroundWindow(0xFFFFFFFF)
        aid = "uitestG1"
        ant = ordner / f"cas_antwort_{aid}.json"
        t = time.time()
        (ordner / "cas_auftrag.json").write_text(json.dumps(
            {"protokoll": 1, "auftrag_id": aid, "nr": "20261013201", "benutzer": "kp", "bruecke_pid": os.getpid(),
             "zeit": time.time(), "zeit_text": "", "testbefund": False}), encoding="utf-8")
        while time.time() - t < 10 and not ant.exists():
            time.sleep(0.02)
        G["annahme_s"] = round(time.time() - t, 2) if ant.exists() else None
        time.sleep(1.0)
        G["cas_iconic"] = bool(win32gui.IsIconic(hwnd))
        G["cas_vordergrund"] = win32gui.GetForegroundWindow() == hwnd
        G["cas_vorne"] = ph(state, "cas_status#G")
        try:
            screenshot(hwnd, OUT / "G_cas_vorne.png")
        except Exception:
            pass
        ph(state, "cas_testbefund")
        G["cas_eol"] = ph(state, "cas_eol#G")
        try:
            G["cas_antwort"] = json.loads(ant.read_text(encoding="utf-8"))
        except Exception:
            G["cas_antwort"] = {}
        time.sleep(2.5)
        G["nach_eol"] = ph(state, "g_nach_eol")
        G["nach_eol_iconic"] = bool(win32gui.IsIconic(hwnd))
        # G6: Menü-Haken „Mit Windows starten (wartet minimiert)“
        G["autostart_an"] = ph(state, "autostart_an")
        lnk = pathlib.Path((G["autostart_an"] or {}).get("autostart_lnk")
                           or os.path.join(bereitschaft.autostart_ordner(), bereitschaft.VERKNUEPFUNG))
        G["lnk"], G["lnk_da"] = str(lnk), lnk.exists()
        if lnk.exists():
            sc = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(lnk))
            G["lnk_ziel"], G["lnk_args"] = sc.TargetPath, sc.Arguments
        G["vbs_exe"] = bereitschaft.starter_exe_lesen(bereitschaft.vbs_lesen(str(vbs))) if vbs.exists() else None
        try:  # sys.executable der EXE kann eine andere Schreibweise haben (8.3-Kurzname im Temp-Pfad)
            G["vbs_exe_ist_diese"] = bool(G["vbs_exe"]) and os.path.samefile(G["vbs_exe"], str(exe))
        except OSError:
            G["vbs_exe_ist_diese"] = False
    finally:
        kill_all(p)
    if not G.get("lnk_da"):
        return G
    try:
        # G7: abmelden/anmelden, X: noch nicht verbunden (EXE weg) → Starter wartet; nach 30 s ist sie da → Start minimiert
        weg = work / "x_fehlt"
        weg.mkdir()
        verschieben(exe, weg / exe.name)
        state2 = work / "g2.json"
        mit_umgebung(dict(umg, RAKSCRIBE_SELFTEST=str(state2)), lambda: os.startfile(str(lnk)))  # wie bei der Anmeldung
        time.sleep(3)
        G["starter_laeuft"] = len(starter_prozesse(bereitschaft.STARTER))
        time.sleep(27)
        G["ohne_exe_fenster"] = len(rks_windows())
        t = time.time()
        verschieben(weg / exe.name, exe)
        hwnd2, _ = find_window("RaKScribe", 120)
        G["x_da_bis_fenster_s"] = round(time.time() - t, 1)
        G["autostart_iconic"] = bool(hwnd2 and win32gui.IsIconic(hwnd2))
        G["autostart_ready"] = wait_json(state2, "ready", 60)
        G["autostart_vorne"] = bool(hwnd2) and win32gui.GetForegroundWindow() == hwnd2
        time.sleep(2)
        G["starter_nach_start"] = len(starter_prozesse(bereitschaft.STARTER))
        G["starter_log"] = lies_log(starter_log)
        # G8: Starter, während RaKScribe läuft → endet still, keine zweite Instanz
        mit_umgebung(dict(umg, RAKSCRIBE_SELFTEST=str(work / "g2b.json")), lambda: os.startfile(str(lnk)))
        t = time.time()
        time.sleep(2)
        while starter_prozesse(bereitschaft.STARTER) and time.time() - t < 30:
            time.sleep(0.5)
        G["starter_bei_laufendem_s"] = round(time.time() - t, 1)
        G["starter_bei_laufendem_rest"] = len(starter_prozesse(bereitschaft.STARTER))
        G["starter_bei_laufendem_fenster"] = len(rks_windows())
        G["starter_log2"] = lies_log(starter_log)
    finally:
        kill_all(None)
    # G9: Haken aus (frisch gestartete RaKScribe) → Verknüpfung und Starter weg
    state3 = work / "g3.json"
    p4 = subprocess.Popen([str(exe)], cwd=work, env=dict(basis, **umg, RAKSCRIBE_SELFTEST=str(state3)))
    try:
        find_window("RaKScribe", 90)
        if wait_json(state3, "ready", 60) is not None:
            G["autostart_aus"] = ph(state3, "autostart_aus")
        G["aus_lnk_da"], G["aus_vbs_da"] = lnk.exists(), vbs.exists()
    finally:
        kill_all(p4)
    # G10: Frist — Starter für eine nie erreichbare EXE (Takt 2 s, Frist 12 s statt 10 s/4 h) endet still
    kurz = work / "frist" / "kurz.vbs"
    bereitschaft.vbs_schreiben(str(kurz), bereitschaft.starter_vbs(str(work / "nie_da" / EXE.name), takt_s=2, frist_s=12))
    t = time.time()
    pk = subprocess.Popen([bereitschaft.wscript_pfad(), "//B", "//Nologo", str(kurz)])
    try:
        G["frist_rc"] = pk.wait(timeout=90)
    except subprocess.TimeoutExpired:
        pk.kill()
        G["frist_rc"] = "hängt"
    G["frist_s"] = round(time.time() - t, 1)
    G["frist_log"] = lies_log(kurz.parent / bereitschaft.STARTER_LOG)
    G["frist_fenster"] = len(rks_windows())
    if lnk.exists():  # Aufräumen (echter Autostart-Ordner des Testrechners)
        lnk.unlink()
    return G


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

# G (v3.11.0): Bereitschaft — minimiert warten, Einzelinstanz, nach CAS-EOL minimieren, Autostart über den Starter
try:
    G = fall_g()
except Exception as e:  # Abbruch im Ablauf → als Fehler in den Bericht, die übrigen Fälle bleiben stehen
    import traceback
    traceback.print_exc()
    G = {"abbruch": f"{type(e).__name__}: {e}"}


def cg(name, ok, detail=""):
    check("G_bereitschaft", name, ok, detail)


def gg(k, feld, default=None):
    return (G.get(k) or {}).get(feld, default)


L = G.get("leerlauf") or {}
speicher = "; ".join(f"PID {q['pid']}: Arbeitssatz {q['arbeitssatz_mb']} MB, privat {q['privater_arbeitssatz_mb']} MB, "
                     f"zugesichert {q['private_bytes_mb']} MB, {q['threads']} Threads, CPU {q['cpu_s']} s"
                     for q in L.get("prozesse", []))
cg("Ablauf vollständig", "abbruch" not in G, G.get("abbruch", ""))
cg("Start mit --minimiert: nur Symbol in der Taskleiste (minimiert), nicht im Vordergrund",
   G.get("start_iconic") is True and G.get("ready_iconic") is True and G.get("ready_vorne") is False
   and gg("ready", "fenster") == "iconic" and gg("ready", "minimiert_gestartet") is True,
   f"{G.get('start_s')} s bis zum Symbol, Zustand {gg('ready', 'fenster')}, vorne {G.get('ready_vorne')}")
cg("Taskleisten-Symbol = RaKScribe-Symbol der EXE (nicht das CustomTkinter-Symbol)", gg("ready", "symbol") is True,
   str(gg("ready", "symbol")))
cg("… lädt wie sonst (Schlüssel aktiv, bereit), kein Mikrofon offen", gg("ready", "status") == "READY"
   and gg("leerlauf_zustand", "aufnahme_offen") is False and gg("leerlauf_zustand", "is_recording") is False,
   f"{gg('ready', 'status')} / Aufnahme offen {gg('leerlauf_zustand', 'aufnahme_offen')}")
cg("Leerlauf minimiert: unter 2 % eines CPU-Kerns", L.get("cpu_prozent_eines_kerns", 99) < 2.0,
   f"{L.get('cpu_prozent_eines_kerns')} % über {L.get('dauer_s')} s — {speicher}")
cg("Zweiter Start (Doppelklick): keine zweite Instanz, das laufende Fenster kommt nach vorne",
   G.get("zweit_rc") == 0 and G.get("zweit_fenster") == 1 and G.get("zweit_iconic") is False
   and gg("zweit", "zweitstarts") == 1 and gg("zweit", "fenster") == "normal",
   f"Rückgabe {G.get('zweit_rc')} nach {G.get('zweit_s')} s, Fenster {G.get('zweit_fenster')}, "
   f"Prozesse {G.get('zweit_prozesse')}, Zustand {gg('zweit', 'fenster')}")
cg("Zweiter Start mit --minimiert (Autostart bei laufender RaKScribe): endet still, Fenster bleibt minimiert",
   G.get("zweit_min_rc") == 0 and G.get("zweit_min_iconic") is True and G.get("zweit_min_fenster") == 1
   and gg("zweit_min", "zweitstarts") == 1, f"Rückgabe {G.get('zweit_min_rc')} nach {G.get('zweit_min_s')} s")
cg("CAS-Auftrag: Annahme unter 1 s, Fenster vorne (nicht mehr minimiert), Band sichtbar",
   (G.get("annahme_s") or 99) < 1.0 and G.get("cas_iconic") is False and gg("cas_vorne", "fenster") == "normal"
   and gg("cas_vorne", "cas_band_sichtbar") is True,
   f"Annahme {G.get('annahme_s')} s, Vordergrund {G.get('cas_vordergrund')}, Band {gg('cas_vorne', 'cas_band')!r}")
cg("EOL im CAS-Modus: Befund an CAS („fertig“), nach ~1,5 s wieder minimiert",
   (G.get("cas_antwort") or {}).get("status") == "fertig" and G.get("nach_eol_iconic") is True
   and gg("nach_eol", "fenster") == "iconic" and gg("nach_eol", "cas") is None,
   f"{(G.get('cas_antwort') or {}).get('status')} / {gg('nach_eol', 'fenster')}")
cg("Menü „Mit Windows starten“: Verknüpfung im Autostart → wscript.exe → lokaler Starter, der auf diese EXE wartet",
   G.get("lnk_da") is True and str(G.get("lnk_ziel", "")).lower().endswith("wscript.exe")
   and "warte_auf_x.vbs" in str(G.get("lnk_args", "")) and G.get("vbs_exe_ist_diese") is True
   and gg("autostart_an", "autostart") is True,
   f"{G.get('lnk')} → {G.get('lnk_ziel')} {G.get('lnk_args')}; Starter wartet auf {G.get('vbs_exe')}")
cg("Anmeldung ohne erreichbare EXE (X: fehlt): Starter wartet unsichtbar, startet nichts",
   G.get("starter_laeuft", 0) >= 1 and G.get("ohne_exe_fenster") == 0,
   f"Starter-Prozesse {G.get('starter_laeuft')}, Fenster {G.get('ohne_exe_fenster')}")
cg("EXE nach 30 s erreichbar → Starter startet sie minimiert, nicht im Vordergrund, und endet",
   G.get("autostart_iconic") is True and G.get("autostart_vorne") is False and G.get("starter_nach_start") == 0
   and "gestartet (minimiert)" in G.get("starter_log", "") and gg("autostart_ready", "minimiert_gestartet") is True,
   f"{G.get('x_da_bis_fenster_s')} s vom Erscheinen der EXE bis zum Symbol; Protokoll: "
   f"{G.get('starter_log', '').strip().splitlines()[-1:] }")
cg("Starter bei laufender RaKScribe: endet still, keine zweite Instanz",
   G.get("starter_bei_laufendem_rest") == 0 and G.get("starter_bei_laufendem_fenster") == 1
   and "läuft schon" in G.get("starter_log2", ""), f"{G.get('starter_bei_laufendem_s')} s")
cg("Haken aus: Verknüpfung und Starter entfernt", gg("autostart_aus", "autostart") is False
   and G.get("aus_lnk_da") is False and G.get("aus_vbs_da") is False,
   f"Verknüpfung {G.get('aus_lnk_da')}, Starter {G.get('aus_vbs_da')}")
cg("Starter-Frist: EXE nie erreichbar → endet still nach der Frist (Test 12 s statt 4 h)",
   G.get("frist_rc") == 0 and 11 <= (G.get("frist_s") or 0) <= 40 and "aufgegeben" in G.get("frist_log", "")
   and G.get("frist_fenster") == 0, f"{G.get('frist_s')} s, Rückgabe {G.get('frist_rc')}")

ok = all(r["ok"] for r in results) and a and c and e_lauf
(OUT / "results.json").write_text(json.dumps({"tag": TAG, "ok": bool(ok), "results": results, "A": a, "C": c, "E": e_lauf,
                                              "G": G}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
lines = [f"## Windows-UI-Test RaKScribe {TAG}", "",
         f"Echtes Windows (GitHub Actions, `{os.environ.get('ImageOS', 'windows')}`), Bildschirm {screen_size()[0]}×{screen_size()[1]}, "
         f"getestet {time.strftime('%d.%m.%Y %H:%M')} UTC. Test-Schlüssel ist ein selbst erzeugter Dummy — kein Praxis-Schlüssel, "
         "kein Mikrofon, keine Google-Aufrufe.", "",
         f"**Ergebnis: {'✅ alle Prüfungen bestanden' if ok else '❌ Fehler — siehe Tabelle'}** "
         f"({sum(r['ok'] for r in results)}/{len(results)})", "",
         "| Fall | Prüfung | Ergebnis | Detail |", "|---|---|---|---|"]
lines += [f"| {r['case']} | {r['check']} | {'✅' if r['ok'] else '❌'} | {r['detail']} |" for r in results]
if L.get("prozesse"):
    lines += ["", f"**Leerlauf minimiert (Fall G, {L.get('dauer_s')} s gemessen):** "
                  f"{L.get('cpu_prozent_eines_kerns')} % eines CPU-Kerns", "",
              "| PID | CPU-Zeit | Arbeitssatz | privater Arbeitssatz (Task-Manager) | zugesichert | Threads |",
              "|---|---|---|---|---|---|"]
    lines += [f"| {q['pid']} | {q['cpu_s']} s | {q['arbeitssatz_mb']} MB | {q['privater_arbeitssatz_mb']} MB | "
              f"{q['private_bytes_mb']} MB | {q['threads']} |" for q in L["prozesse"]]
lines += ["", "Screenshots: `A_gesperrt.png` (ohne Schlüssel), `C_entsperrt.png` (mit Test-Schlüssel + Demo-Befund), "
          "`E_speechmike.png` / `E_speechmike_ende.png` (SpeechMike-Ablauf mit Attrappen, danach Fall F CAS-Auftrag), "
          "`G_minimiert.png` / `G_taskleiste.png` (RaKScribe nur als Taskleisten-Symbol), `G_cas_vorne.png` (nach CAS-Auftrag)."]
(OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
sys.exit(0 if ok else 1)
