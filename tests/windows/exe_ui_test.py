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
     v3.12.0: CAS-Leistungen (cas_leistungen_<id>.json) → Band „… · HWS · Schulter re. (Sono)“, Diktat widerspricht →
     Hinweise, gemischtes Diktat Fuß + LWS → zwei Befunde (ohne KI), „Unauffällig.“ + HWS → HWS-Normalbefund, grüne
     Bestätigung nach EOL, Kopfzeile bei 1240/900 px ohne Überdeckung
     v3.13.0: IB-Lab-Bausteine (cas_ibl_<id>.json der Brücke 1.2.0) → Band-Zeile „IB Lab: FROG links ✓“ (hervorgehoben),
     INS „Fuß links unauffällig.“ → Messwerte wörtlich im Befund, Diagnose nicht ins unauffällige Ergebnis (Hinweis),
     neue Fassung nach dem Befund → v3.14.0: automatisch sichtbar eingefügt (alte Fassung ersetzt, Hinweis)
  H  v3.13.0: Selbsttest mit RAKSCRIBE_SELFTEST_ENDE endet von selbst (für den Ordi-Probelauf am Büro-PC)
  E  v3.16.0: Knopf „Audio laden“ (Phase audio_laden#<Pfad>) mit ogg/opus (Telegram) und mp3 → soundfile im Bündel,
     Befund zur Kontrolle; m4a ohne Decoder → Meldung
  W  v3.16.0 WAV-Modus: rakscribe26.exe --wav-ablauf <json> (Attrappen für Google, Mikrofon = WavQuelle): Record →
     ogg einspielen → INS → Befund → endet von selbst (Exit 0), Ablauf-Protokoll ok, keine Dialoge offen
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
AUDIO = pathlib.Path(__file__).resolve().parents[1] / "offline" / "audio"   # v3.16.0: ton_440.ogg / .mp3
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
    # v3.16.0: Knopf „Audio laden“ (gleicher Handler) mit Telegram-ogg/opus und mp3 aus dem Repo (Sinuston, kein Diktat)
    for art in ("ogg", "mp3"):
        e[f"audio_{art}"] = ph("audio_laden#" + str(AUDIO / f"ton_440.{art}"), 0.5)
        time.sleep(3)
        e[f"audio_{art}_fertig"] = ph(f"audio_{art}_fertig")
        ph(f"sm_F1#{art}")
    return e


# v3.12.0: CAS-Leistungen wie von der Brücke 1.1.0 (bruecke/leistungen.py datei_inhalt) — Kurztexte/Vorlagen der Zuordnung
def _l(kurz, text, mod, vorlage, seite=None, ohne=False):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": mod, "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": ohne, "bekannt": True}


L_HWS = _l("x-hws", "HWS", "Röntgen", "halswirbelsäule_in_2_ebenen")
L_LWS = _l("x-lws", "LWS", "Röntgen", "lendenwirbelsäule_in_2_ebenen")
L_FUSSL = _l("x-fuss-li", "Fuß links", "Röntgen", "fuß_in_2_ebenen", "links")
L_SOSUR = _l("x-sono-schulter-re", "Sonographie der Schulter re.", "Sono", "sonografie_schultergelenk", "rechts")
L_KOORD = _l("x-zuschlag", "Zuschlag", "sonstige", None, ohne=True)
# v3.13.0: IB-Lab-Bausteine wie von der Brücke 1.2.0 (bruecke/ibl_bausteine.py Beobachter.datei_inhalt), synthetisch
IBL_FROG_LI = {"accno": "T-0101", "ziffer": 1, "modul": "frog", "name": "FROG", "modul_name": "IB Lab FROG",
               "version": 1, "aktualisiert": "2026-10-13T18:00:00", "seiten": ["links"],
               "befundteil": ["Calcaneusneigungswinkel links 12,4° (IB Lab FROG)."],
               "ergebnis": ["Pes planus links (Calcaneusneigungswinkel 12,4°)."], "hinweise": [], "nicht_zugeordnet": []}
IBL_FROG_LI_V2 = dict(IBL_FROG_LI, version=2, aktualisiert="2026-10-13T18:05:00",
                      befundteil=["Calcaneusneigungswinkel links 12,4° (IB Lab FROG).",
                                  "Hallux-valgus-Winkel links 18,2° (IB Lab FROG)."],
                      ergebnis=["Pes planus links (Calcaneusneigungswinkel 12,4°).",
                                "Geringgradiger Hallux valgus links (Hallux-valgus-Winkel 18,2°)."])


def fall_f(state, work, hwnd=None):
    """v3.10.0 CAS-Auftrag der Brücke über die Datei-Schnittstelle (wie bruecke/auftrag.py) + Selbsttest-Phasen cas_*.
    v3.12.0: CAS-Leistungen (cas_leistungen_<id>.json) → Band, Vorlagenwahl (auch gemischt, ohne KI über den
    Normalbefund-Weg), Hinweise, grüne Bestätigung nach EOL, Kopfzeile bei zwei Fensterbreiten."""
    ordner = work / "localappdata" / "RaKScribe"
    ordner.mkdir(parents=True, exist_ok=True)

    def leistungen(aid, nr, liste):
        (ordner / f"cas_leistungen_{aid}.json").write_text(json.dumps(
            {"protokoll": 1, "auftrag_id": aid, "nr": nr, "roh": "Untersuchung: …", "leistungen": liste,
             "quelle": "CASSpeechMagic.DBModule.GetExaminationsText", "katalog": "UI-Test", "ms": 2700,
             "zeit": time.time()}, ensure_ascii=False), encoding="utf-8")

    def ibl(aid, nr, liste):
        p = ordner / f"cas_ibl_{aid}.json"
        tmp = ordner / f"cas_ibl_{aid}.json.tmp"
        tmp.write_text(json.dumps({"protokoll": 1, "auftrag_id": aid, "nr": nr, "quelle": "ibl-abholer/1",
                                   "bausteine": liste, "zeit": time.time()}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)

    def bild(name):
        try:
            if hwnd:
                screenshot(hwnd, OUT / name)
        except Exception:
            pass

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
    leistungen("uitest1", "20261013005", [L_HWS, L_SOSUR, L_KOORD])      # kommt Sekunden nach dem Auftrag
    f["leistungen1"] = ph("cas_status#1b", 1.5)
    bild("F_cas_leistungen.png")
    f["testbefund"] = ph("cas_testbefund")
    f["eol_test"] = ph("cas_eol#1")
    bild("F_bestaetigung.png")
    f["antwort1_ende"] = antwort("uitest1")
    txt = ordner / "cas_ergebnis_20261013005.txt"
    f["ergebnis_test"] = txt.read_text(encoding="utf-8") if txt.exists() else None
    auftrag("20261013006", "uitest2")
    leistungen("uitest2", "20261013006", [L_HWS])
    f["angenommen2"] = ph("cas_status#2", 1.0)
    ph("sm_RECORD#9")
    f["ins2"] = ph("sm_INS#9", 2.0)        # Attrappe diktiert „Kniegelenk rechts in 2 Ebenen unauffällig.“
    bild("F_cas_hinweise.png")
    f["eol2"] = ph("cas_eol#2")
    f["antwort2"] = antwort("uitest2")
    wav = f["antwort2"].get("wav_datei")
    f["wav2_bytes"] = os.path.getsize(wav) if wav and os.path.exists(wav) else 0
    f["nach_bestaetigung2"] = ph("cas_status#2b", 5.0)
    # gemischtes Diktat ohne KI (Normalbefund je Abschnitt): Fuß links + LWS
    auftrag("20261013008", "uitest4")
    leistungen("uitest4", "20261013008", [L_FUSSL, L_LWS])
    ph("cas_status#4", 1.0)
    f["gemischt"] = ph("text_ins#1|Fuß links unauffällig. LWS unauffällig.")
    bild("F_cas_gemischt.png")
    ph("cas_abbrechen#4")
    # „Unauffällig.“ allein + CAS HWS → HWS-Normalbefund aus der Vorlage
    auftrag("20261013009", "uitest5")
    leistungen("uitest5", "20261013009", [L_HWS])
    ph("cas_status#5", 1.0)
    f["nur_unauffaellig"] = ph("text_ins#2|Unauffällig.")
    ph("cas_abbrechen#5")
    # v3.13.0: IB-Lab-Bausteine — kommen nach dem Auftrag, INS ohne KI (Normalbefund-Weg), neue Fassung → v3.14.0 automatisch
    auftrag("20261013010", "uitest6")
    leistungen("uitest6", "20261013010", [L_FUSSL])
    f["ibl_ohne"] = ph("cas_status#6", 1.0)
    ibl("uitest6", "20261013010", [IBL_FROG_LI])
    f["ibl_band"] = ph("cas_status#6b", 1.5)
    bild("F_ibl_band.png")
    f["ibl_ins"] = ph("text_ins#3|Fuß links unauffällig.")
    bild("F_ibl_befund.png")
    ibl("uitest6", "20261013010", [IBL_FROG_LI_V2])
    f["ibl_neu"] = ph("cas_status#6c", 1.5)
    bild("F_ibl_knopf.png")
    f["ibl_eingefuegt"] = ph("cas_ibl_einfuegen#6")
    ph("cas_abbrechen#6")
    auftrag("20261013007", "uitest3")
    ph("cas_status#3")
    f["abbrechen"] = ph("cas_abbrechen")
    f["antwort3"] = antwort("uitest3")
    # Kopfzeile (Peter 13.10.: „Bereit“ überdeckte „SpeechMike verbunden“) bei zwei Fensterbreiten
    f["kopf1240"] = ph("kopfzeile#1240")
    bild("F_kopfzeile_1240.png")
    f["kopf900"] = ph("kopfzeile#900")
    bild("F_kopfzeile_900.png")
    return f


# v3.15.0 Mammo-Maske (Fall M): CAS-Auftrag mit Mammographie-Screening (+ Mamma-Sono), Mammo-Vorbefund im Kontext
# (synthetischer Text aus tests/offline/maske_faelle.txt) — Felder, Feldsprung, Warnung, F3, Diktat je Feld, INS, EOL
L_MAMS = dict(_l("x-mammo-scr", "Mammographie bds. Screening", "Röntgen", "mammographie_beidseits"), mammo="screening")
L_MAMMASONO = _l("x-mamma-sono", "Ultraschall der Mamma o.V.", "Sono", "mammasonographie_beidseits")
_MF = json.loads((pathlib.Path(__file__).resolve().parents[1] / "offline" / "maske_faelle.txt").read_text(encoding="utf-8"))
MAMMO_VB = {"nr": "20241012001", "datum": "2024-06-05", "untersuchung": "Mammographie bds. Screening",
            "text": _MF["zerlegen"][0]["text"], "zeichen": 900, "gekuerzt": False, "werte": {"acr": "2", "birads": "2"}}
SCREENING_12 = ("Verlaufskontrolle bei unverändertem klinischem Befund nach den Vorgaben des österreichischen "
                "Brustkrebsfrüherkennungsprogrammes in zwei Jahren empfehlenswert.")


def fall_m(state, work, hwnd=None):
    ordner = work / "localappdata" / "RaKScribe"
    ordner.mkdir(parents=True, exist_ok=True)

    def datei(name, d):
        tmp = ordner / (name + ".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, ordner / name)

    def auftrag(nr, aid):
        datei("cas_auftrag.json", {"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": "kp", "bruecke_pid": os.getpid(),
                                   "zeit": time.time(), "zeit_text": "", "testbefund": False})
        time.sleep(2.0)

    def leistungen(aid, nr, liste):
        datei(f"cas_leistungen_{aid}.json", {"protokoll": 1, "auftrag_id": aid, "nr": nr, "roh": "Datenbank",
                                             "leistungen": liste, "quelle": "CAS-Datenbank", "katalog": "UI-Test",
                                             "ms": 300, "zeit": time.time()})

    def kontext(aid, nr, vb):
        datei(f"cas_kontext_{aid}.json", {"protokoll": 1, "auftrag_id": aid, "nr": nr, "quelle": "CAS-Datenbank",
                                          "zuweiser": "", "info": "", "befunder": "kp", "vorbefund": vb, "zeit": time.time()})

    def antwort(aid):
        try:
            return json.loads((ordner / f"cas_antwort_{aid}.json").read_text(encoding="utf-8"))
        except Exception:
            return {}

    def bild(name):
        try:
            if hwnd:
                screenshot(hwnd, OUT / name)
        except Exception:
            pass

    def ph(name, warten=0.0):
        if warten:
            time.sleep(warten)
        pathlib.Path(str(state) + ".trigger").write_text(name, encoding="utf-8")
        return wait_json(state, name, 40)
    m = {}
    auftrag("20261015011", "uitestm1")
    leistungen("uitestm1", "20261015011", [L_MAMS, L_MAMMASONO])
    kontext("uitestm1", "20261015011", MAMMO_VB)
    m["offen"] = ph("cas_status#m1", 1.5)
    bild("M_maske.png")
    m["ff"] = ph("sm_FF#m1")
    m["rew"] = ph("sm_REW#m1")
    m["ins_warn"] = ph("sm_INS#m1", 0.5)
    bild("M_warnung.png")
    m["f3"] = ph("sm_F3#m1")
    ph("sm_FF#m2")
    ph("chirp#unverändert|keine suspekten Herde|unverändert ACR 2 BIRADS 2")
    m["rec"] = ph("sm_RECORD#m1")
    m["ff_rec"] = ph("sm_FF#m3", 1.5)
    bild("M_aufnahme.png")
    ph("sm_FF#m4", 1.5)
    m["ins"] = ph("sm_INS#m2", 1.5)
    bild("M_befund.png")
    m["eol"] = ph("cas_eol#m1")
    m["antwort1"] = antwort("uitestm1")
    txt = ordner / "cas_ergebnis_20261015011.txt"
    m["ergebnis1"] = txt.read_text(encoding="utf-8") if txt.exists() else None
    # Rückfall ohne Datenbank: kein Kontext, Leistung ohne Tarif-Kennzeichen → Maske ohne Vorbefund, Sono eingeklappt
    auftrag("20261015012", "uitestm2")
    leistungen("uitestm2", "20261015012", [dict(L_MAMS, mammo=None)])
    m["ohne_db"] = ph("cas_status#m2", 1.5)
    bild("M_ohne_vorbefund.png")
    m["f4_aus"] = ph("sm_F4#m1")
    m["f4_an"] = ph("sm_F4#m2")
    m["klick"] = ph("maske_klick#3#m")
    m["tippen"] = ph("maske_tippen#3#m|Unauffälliger Befund.\nACR: 1\nBIRADS: 1")
    m["knopf"] = ph("maske_knopf#1#m")
    m["ins2"] = ph("sm_INS#m3", 1.0)
    bild("M_befund_ohne_vorbefund.png")
    m["abbrechen"] = ph("cas_abbrechen#m2")
    # v3.15.4 (Peter 15.10.): SpeechMike Ambient ohne F1–F4 (Play/Command), Markieren + Drüberdiktieren, Tippen in der
    # Pause, F3/F4 auf der Tastatur — derselbe Weg wie Gerät/Tastatur (Dekodierer bzw. bind_all-Handler)
    ph("taste_f9")   # Befund des abgebrochenen Auftrags weg (sonst bleibt die Maske „bereit“, nicht gezeigt — wie 3.15.1)
    auftrag("20261015013", "uitestm3")
    leistungen("uitestm3", "20261015013", [L_MAMS, L_MAMMASONO])
    kontext("uitestm3", "20261015013", MAMMO_VB)
    m["a_offen"] = ph("cas_status#m4", 1.5)
    m["a_geraet"] = ph("geraet#ambient")
    m["a_play"] = ph("sm_PLAY#a1")
    m["a_cmd_aus"] = ph("sm_COMMAND#a1")
    m["a_cmd_an"] = ph("sm_COMMAND#a2")
    ph("sm_FF#a1")
    m["a_markiert"] = ph("maske_markieren#1|109|160")
    ph("chirp#neu aufgetretener Herd links oben außen")
    m["a_rec"] = ph("sm_RECORD#a1")
    m["a_pause"] = ph("sm_RECORD#a2", 1.5)
    bild("M_markiert_ersetzt.png")
    m["a_tippen_pause"] = ph("maske_tippen#2|Keine suspekten Herde.")
    ph("sm_FF#a2")
    ph("sm_FF#a3")
    m["a_kb_f3"] = ph("kb_F3#a1")
    m["a_ins"] = ph("sm_INS#a1", 1.0)
    bild("M_ambient_befund.png")
    m["a_kb_f4_aus"] = ph("kb_F4#a1")
    m["a_kb_f4_an"] = ph("kb_F4#a2")
    m["a_premium"] = ph("geraet#premium")
    m["a_abbrechen"] = ph("cas_abbrechen#m4")
    ph("geraet#auto")
    # v3.15.4 (Peter 15.10.: „warum kann ich nicht mehr rechts mit nur text in den Befund reindiktieren?“): Record →
    # Pause → in den Befund geklickt → Record (weiter) → INS: das Diktat steht an der Stelle; mit „Nur Text“ ersetzt es
    # die Markierung — beides im CAS-Band, nichts geht an CAS vor EOL
    auftrag("20261015014", "uitestm5")
    leistungen("uitestm5", "20261015014", [_l("x-hg-bds", "Handgelenk bds.", "Röntgen", "handgelenk_in_2_ebenen",
                                              seite="beidseits")])
    m["e_offen"] = ph("cas_status#m5", 1.5)
    m["e_test"] = ph("cas_testbefund#e1")
    ph("diktat_setzen#Handgelenk links SL-Spalt erweitert")
    ph("befund_fokus_weg#e1")
    ph("chirp#zusätzlich kleiner Gelenkerguss|zusätzlich kleiner Gelenkerguss")   # Pause-Reparatur + Endtext
    ph("sm_RECORD#e1")
    ph("sm_RECORD#e2", 1.0)
    m["e_klick"] = ph("befund_markieren#" + str(TESTBEFUND.index("Dieser Text")))
    m["e_weiter"] = ph("sm_RECORD#e3")
    m["e_ins"] = ph("sm_INS#e1", 1.5)
    bild("E_befund_eingefuegt.png")
    m["e_nt"] = ph("nur_text_an#e1")
    ph("chirp#ersetzt|ersetzt")
    ph("befund_fokus_weg#e2")
    ph("sm_RECORD#e4")
    ph("sm_RECORD#e5", 1.0)
    i0 = TESTBEFUND.index("TESTBEFUND ohne")
    m["e_mark"] = ph(f"befund_markieren#{i0}|{i0 + len('TESTBEFUND')}")
    ph("sm_RECORD#e6")
    m["e_ins2"] = ph("sm_INS#e2", 1.5)
    ph("nur_text_aus#e1")
    m["e_abbrechen"] = ph("cas_abbrechen#m5")
    m["e_antwort"] = antwort("uitestm5")
    # v3.15.4 (Peter 15.10.: Häkchen im Optionen-Menü schwarz auf dunkelblau): ☰ anklicken, Menü fotografieren, ESC
    m["menu"] = menu_foto(m["a_abbrechen"], hwnd)
    m["nach_menu"] = ph("cas_status#nach_menu", 0.5)
    return m


def menu_foto(zustand, hwnd):
    """☰-Menü der echten EXE öffnen (Mausklick), Bildschirmbereich fotografieren (O_menu_haekchen.png) und die hellen
    Pixel in der Häkchen-Spalte zählen (weiße Häkchen ≠ schwarz auf dunkel); danach ESC."""
    out = {"ok": False}
    try:
        import win32api
        import win32con
        from PIL import ImageGrab
        x, y, w, h = (zustand or {}).get("menu_btn_xy") or (0, 0, 0, 0)
        if not w:
            return out
        win32api.SetCursorPos((x + w // 2, y + h // 2))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(1.5)
        breite = win32api.GetSystemMetrics(0)
        oben = y + h
        img = ImageGrab.grab(bbox=(0, oben, breite, oben + 760), all_screens=True).convert("RGB")
        px = img.load()
        # linke Kante des Menüs = Spalte mit langem hellem Rahmen (Windows zeichnet ihn (240, 240, 240))
        x0 = next((xx for xx in range(img.size[0]) if sum(1 for yy in range(img.size[1])
                                                          if px[xx, yy] == (240, 240, 240)) >= 250), None)
        out["menu_links"] = x0
        if x0 is None:
            img.save(OUT / "O_menu_haekchen.png")
            return out
        img.crop((x0, 0, min(img.size[0], x0 + 560), img.size[1])).save(OUT / "O_menu_haekchen.png")
        spalte = img.convert("L").crop((x0 + 2, 0, x0 + 20, img.size[1]))   # Häkchen-Spalte (vor den Beschriftungen)
        out["helle_pixel_haekchen_spalte"] = sum(1 for v in spalte.getdata() if v > 200)
        out["ok"] = True
    except Exception as e:
        out["fehler"] = f"{type(e).__name__}: {e}"
    finally:
        try:
            import win32api
            import win32con
            win32api.keybd_event(win32con.VK_ESCAPE, 0, 0, 0)
            win32api.keybd_event(win32con.VK_ESCAPE, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.8)
        except Exception:
            pass
    return out


REPO = pathlib.Path(__file__).resolve().parents[2]
TESTBEFUND = ("## TEST RaKScribe-Brücke – bitte nicht vidieren\n\n## Befund\nTESTBEFUND ohne Diktat und ohne Patientenbezug. "
              "Dieser Text prüft nur die Übergabe von RaKScribe an CAS.\n\n## Ergebnis\nTEST – bitte nicht vidieren.")


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
        time.sleep(5.0)   # v3.12.0: erst grünes Band (4,5 s), dann Taskleiste
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
             sm_gesperrt=False, mit_fall_f=False, mit_fall_m=False):
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
        f = fall_f(state, work, hwnd) if mit_fall_f else None
        mm = fall_m(state, work, hwnd) if mit_fall_m else None
        if e:
            try:
                screenshot(hwnd, OUT / f"{case}_ende.png")
            except Exception:
                pass
        return {"state": st, "after_f10": after, "fall_d": d, "sm_gesperrt": sm, "fall_e": e, "fall_f": f, "fall_m": mm,
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
for _art in ("ogg", "mp3"):   # v3.16.0 Knopf „Audio laden“
    _ad = g(f"audio_{_art}_fertig", "audio_datei") or {}
    ce(f"Audio laden {_art} (soundfile im Bündel): ≈ 1,5 s gelesen, Befund rechts zur Kontrolle, nichts eingefügt",
       not _ad.get("fehler") and 1.3 <= (_ad.get("sekunden") or 0) <= 1.7 and str(g(f"audio_{_art}_fertig", "result", "")).startswith("## Kniegelenk")
       and g(f"audio_{_art}_fertig", "status") == "KONTROLLE",
       f"{_ad} / {g(f'audio_{_art}_fertig', 'status')}")

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
# v3.12.0: CAS-Leistungen
cf("v3.12.0 Leistungen kommen nach: Band „CAS-Diktat 20261013005 (kp) · HWS · Schulter re. (Sono)“ (ohne Abrechnungsposten)",
   "CAS-Diktat 20261013005 (kp) · HWS · Schulter re. (Sono)" in str(gf("leistungen1", "cas_band", ""))
   and gf("leistungen1", "cas_leistungen") == ["HWS", "Schulter re. (Sono)"],
   f"{gf('leistungen1', 'cas_band')!r} / {gf('leistungen1', 'cas_leistungen')}")
cf("v3.12.0 EOL → grünes Band „An CAS übergeben: <Nr> · <Titel>“ sichtbar, blaues Band weg",
   gf("eol_test", "bestaetigung_sichtbar") is True
   and str(gf("eol_test", "bestaetigung", "")).startswith("✓  An CAS übergeben: 20261013005")
   and "TEST RaKScribe-Brücke" in str(gf("eol_test", "bestaetigung", "")) and gf("eol_test", "cas_band_sichtbar") is False,
   f"{gf('eol_test', 'bestaetigung_sichtbar')} / {gf('eol_test', 'bestaetigung')!r}")
cf("v3.12.0 Diktat (Knie) widerspricht CAS (HWS) → Diktat gewinnt, Hinweise im Band",
   str(gf("ins2", "result", "")).startswith("## Kniegelenk rechts in 2 Ebenen")
   and gf("ins2", "cas_hinweise") == ["Kniegelenk in 2 Ebenen: nicht in den CAS-Leistungen", "HWS laut CAS, nicht diktiert"]
   and "HWS laut CAS, nicht diktiert" in str(gf("ins2", "cas_hinweis_label", "")),
   f"{str(gf('ins2', 'result', ''))[:40]!r} / {gf('ins2', 'cas_hinweise')}")
cf("v3.12.0 Bestätigung mit Titel, nach ~5 s wieder weg (dann Taskleiste)",
   "An CAS übergeben: 20261013006  ·  Kniegelenk rechts in 2 Ebenen" in str(gf("eol2", "bestaetigung", ""))
   and gf("nach_bestaetigung2", "bestaetigung_sichtbar") is False,
   f"{gf('eol2', 'bestaetigung')!r} / danach {gf('nach_bestaetigung2', 'bestaetigung_sichtbar')}")
cf("v3.12.0 gemischtes Diktat Fuß links + LWS → zwei Befunde in Diktat-Reihenfolge (Normalbefund-Weg, ohne KI)",
   gf("gemischt", "befund_titel") == "Fuß links in 2 Ebenen · Lendenwirbelsäule in 2 Ebenen"
   and gf("gemischt", "cas_hinweise") == [], f"{gf('gemischt', 'befund_titel')!r} / {gf('gemischt', 'cas_hinweise')}")
cf("v3.12.0 „Unauffällig.“ + CAS HWS → HWS-Normalbefund aus der Vorlage",
   str(gf("nur_unauffaellig", "result", "")).startswith("## Halswirbelsäule in 2 Ebenen"),
   repr(str(gf("nur_unauffaellig", "result", ""))[:60]))
# v3.13.0: IB-Lab-Bausteine
cf("v3.13.0 ohne IB-Lab-Datei: keine IB-Lab-Zeile, Menü „IB-Lab-Bausteine übernehmen“ an (Standard)",
   gf("ibl_ohne", "ibl_band") == "" and gf("ibl_ohne", "ibl_band_sichtbar") is False
   and gf("ibl_ohne", "ibl_uebernehmen") is True, f"{gf('ibl_ohne', 'ibl_band')!r} / {gf('ibl_ohne', 'ibl_uebernehmen')}")
cf("v3.13.0 Baustein kommt nach: Band-Zeile „IB Lab: FROG links ✓“ sichtbar, hervorgehoben",
   gf("ibl_band", "ibl_band") == "IB Lab: FROG links ✓" and gf("ibl_band", "ibl_band_sichtbar") is True
   and (gf("ibl_band", "ibl_hervorgehoben") or 0) >= 1 and gf("ibl_band", "ibl_knopf_sichtbar") is False,
   f"{gf('ibl_band', 'ibl_band')!r} / sichtbar {gf('ibl_band', 'ibl_band_sichtbar')} / {gf('ibl_band', 'ibl_hervorgehoben')}")
cf("v3.13.0 INS „Fuß links unauffällig.“: Messwert wörtlich im Befund, Diagnose nicht ins unauffällige Ergebnis + Hinweis",
   str(gf("ibl_ins", "result", "")).startswith("## Fuß links in 2 Ebenen")
   and "Calcaneusneigungswinkel links 12,4° (IB Lab FROG)." in str(gf("ibl_ins", "result_ende", ""))
   and "Pes planus" not in str(gf("ibl_ins", "result_ende", ""))
   and any("nicht ins Ergebnis übernommen" in h for h in gf("ibl_ins", "ibl_hinweise", []) or [])
   and str(gf("ibl_ins", "ibl_hinweis_label", "")).startswith("⚠") and gf("ibl_ins", "ibl_im_befund") == {"frog": 1},
   f"{str(gf('ibl_ins', 'result_ende', ''))[-220:]!r} / {gf('ibl_ins', 'ibl_hinweise')}")
cf("v3.14.0 neue Fassung nach dem Befund (vor EOL): automatisch SICHTBAR eingefügt (Hinweis), kein Knopf nötig",
   gf("ibl_neu", "ibl_auto_n") == 1 and gf("ibl_neu", "ibl_knopf_sichtbar") is False
   and "Hallux-valgus-Winkel links 18,2° (IB Lab FROG)." in str(gf("ibl_neu", "result_ende", ""))
   and "neu, nicht im Befund" not in str(gf("ibl_neu", "ibl_band", "")),
   f"{gf('ibl_neu', 'ibl_band')!r} / Knopf {gf('ibl_neu', 'ibl_knopf_sichtbar')} / auto {gf('ibl_neu', 'ibl_auto_n')}")
cf("v3.13.0/3.14.0 neue Fassung im Befund (alte Zeilen ersetzt, nichts doppelt), Knopf weg",
   "Hallux-valgus-Winkel links 18,2° (IB Lab FROG)." in str(gf("ibl_eingefuegt", "result_ende", ""))
   and str(gf("ibl_eingefuegt", "result_ende", "")).count("Calcaneusneigungswinkel links 12,4° (IB Lab FROG).") == 1
   and gf("ibl_eingefuegt", "ibl_knopf_sichtbar") is False and gf("ibl_eingefuegt", "ibl_im_befund") == {"frog": 2},
   f"{str(gf('ibl_eingefuegt', 'result_ende', ''))[-260:]!r} / {gf('ibl_eingefuegt', 'ibl_im_befund')}")


def _ueberlappt(a, b):
    return a and b and a[1] > 1 and b[1] > 1 and a[0] < b[0] + b[1] and b[0] < a[0] + a[1]


for breite, sm_text in ((1240, "SpeechMike verbunden"), (900, "SpeechMike ✓")):
    kopf = gf(f"kopf{breite}", "kopf") or {}
    st = kopf.get("status_badge")
    andere = {k: v for k, v in kopf.items() if k in ("sm_chip", "key_chip", "device_dropdown", "menu_btn")}
    cf(f"v3.12.0 Kopfzeile {breite} px: Status lesbar (≥ 120 px) und überdeckt „{sm_text}“ und die rechten Elemente nicht",
       bool(st) and st[1] >= 120 and (kopf.get("sm_chip") or [0, 0, ""])[2] == sm_text
       and not any(_ueberlappt(st, v) for v in andere.values()), json.dumps(kopf, ensure_ascii=False))

# M (v3.15.0): Mammo-Maske — eigener Lauf (volles Fenster), Attrappen für Mikrofon/Google/chirp_3, Tasten über den Handler
m_lauf = run_case("M_maske", with_key=True, demo=False, send_f10=False, fake_audio=True, mit_fall_m=True)
MM = (m_lauf or {}).get("fall_m") or {}


def cm(name, ok, detail=""):
    check("M_maske", name, ok, detail)


def gm(k, feld=None, default=None):
    z = (MM.get(k) or {}).get("maske") or {}
    return z if feld is None else z.get(feld, default)


def gq(k):
    return [f.get("quelle") for f in gm(k, "felder", []) or []]


cm("Mammographie-Auftrag (+ Mamma-Sono, Vorbefund aus der Datenbank) → Maske gezeigt, links „MAMMO-MASKE“, 4 Felder mit "
   "Vorbefund-Vorschlag", gm("offen", "offen") is True and gm("offen", "sichtbar") is True and gm("offen", "an") is True
   and gm("offen", "titel_links") == "MAMMO-MASKE" and gq("offen") == ["vorbefund"] * 4 and gm("offen", "erkannt") == 4
   and "Vorbefund 05.06.2024" in str(gm("offen", "kopf")), json.dumps(gm("offen"), ensure_ascii=False)[:600])
cm("Vorspulen → Feld 2, Rückspulen → Feld 1", gm("ff", "aktiv") == 1 and gm("rew", "aktiv") == 0,
   f"{gm('ff', 'aktiv')} / {gm('rew', 'aktiv')}")
cm("INS mit offenen Vorschlägen → kein Befund, Warnung nennt die Felder",
   "Noch nicht übernommen" in str(gm("ins_warn", "warnung")) and (MM.get("ins_warn") or {}).get("result") == ""
   and (MM.get("ins_warn") or {}).get("job_zustand") == "READY", str(gm("ins_warn", "warnung")))
cm("F3 → Inspektion übernommen", gq("f3")[:1] == ["uebernommen"], str(gq("f3")))
cm("Record im Feld Mammographie → Aufnahme, Abschnitt angemeldet", (MM.get("rec") or {}).get("job_zustand") == "RECORDING"
   and gm("rec", "aktiv") == 1 and (gm("rec", "felder") or [{}, {}])[1].get("wartet") is True, str(gm("rec", "zustand")))
cm("Vorspulen während der Aufnahme → Sono-Feld, Aufnahme läuft weiter", gm("ff_rec", "aktiv") == 2
   and (MM.get("ff_rec") or {}).get("job_zustand") == "RECORDING", str(gm("ff_rec", "zustand")))
r = str((MM.get("ins") or {}).get("result_voll") or "")
cm("INS → Befund aus den Feldern: Titel Screening, Inspektion übernommen, Mammographie „unverändert“ mit Vergleichsdatum, "
   "Sono diktiert, Ergebnis + ACR/BIRADS, Screening-Text BI-RADS 2",
   r.startswith("## Mammographie beidseits – Screening\n\n## Befund\nInspektion und Palpation: Unauffällig.\n\n"
                "Mammographie: Verglichen mit 05.06.2024 beidseits unverändert vereinzelte insuspekte Verkalkungen")
   and "Sonographie: Keine suspekten Herde." in r and "## Ergebnis\nMastopathie mit insuspekten Verkalkungen.\nACR: 2\n"
   "BIRADS: 2\n\n" + SCREENING_12 in r and (MM.get("ins") or {}).get("status") == "KONTROLLE", r[:900])
cm("EOL → genau dieser Befund an die Brücke („fertig“), Maske zu", (MM.get("antwort1") or {}).get("status") == "fertig"
   and MM.get("ergebnis1") == r and gm("eol", "offen") is False, str(MM.get("antwort1")))
cm("ohne Datenbank (kein Kontext): Maske ohne Vorbefund, Mammographie = Normalbaustein, Sono eingeklappt",
   gm("ohne_db", "offen") is True and gm("ohne_db", "vorbefund") is None and gq("ohne_db") == ["leer", "vorlage", "leer", "leer"]
   and (gm("ohne_db", "felder") or [{}] * 3)[2].get("sichtbar") is False, str(gm("ohne_db", "zustand")))
cm("F4 → Maske aus (Diktat-Feld), F4 → wieder an", gm("f4_aus", "an") is False and gm("f4_aus", "sichtbar") is False
   and gm("f4_aus", "titel_links") == "DIKTAT" and gm("f4_an", "an") is True and gm("f4_an", "sichtbar") is True)
cm("Klick ins Ergebnis-Feld, getippt (Werte erkannt), Knopf „übernehmen“ am Normalbaustein",
   gm("klick", "aktiv") == 3 and gq("tippen")[3:] == ["getippt"] and (gm("tippen", "felder") or [{}] * 4)[3].get("werte")
   == {"acr": "1", "birads": "1"} and gq("knopf")[1:2] == ["uebernommen"], str(gm("knopf", "zustand")))
r2 = str((MM.get("ins2") or {}).get("result_voll") or "")
cm("INS → Befund ohne Vorbefund: Normalbaustein, getipptes Ergebnis, ACR/BIRADS 1, Screening-Text BI-RADS 1",
   r2.startswith("## Mammographie beidseits – Screening") and "Mammographie: Kleinfleckig strukturierter Drüsenkörper." in r2
   and "## Ergebnis\nUnauffälliger Befund.\nACR: 1\nBIRADS: 1" in r2 and SCREENING_12 in r2, r2[:700])

A_MAMMO = ("Verglichen mit 05.06.2024 beidseits unverändert vereinzelte insuspekte Verkalkungen sowie Gefäßverkalkungen. "
           "Neu aufgetretener Herd links oben außen. Cutis und Subcutis unauffällig.")
cm("v3.15.4 SpeechMike Ambient erkannt → Hilfezeile „Play = übernehmen · Command = Maske aus“ (ohne F3/F4)",
   "Vorspulen/Rückspulen = Feld · Play = übernehmen · Command = Maske aus" in str(gm("a_geraet", "hilfe"))
   and "F3" not in str(gm("a_geraet", "hilfe")), str(gm("a_geraet", "hilfe")))
cm("Ambient: Play → Inspektion übernommen; Command → Maske aus, Command → wieder an",
   gq("a_play")[:1] == ["uebernommen"] and gm("a_cmd_aus", "an") is False and gm("a_cmd_an", "an") is True,
   f"{gq('a_play')} / {gm('a_cmd_aus', 'an')} / {gm('a_cmd_an', 'an')}")
fa = (gm("a_pause", "felder") or [{}, {}])[1]
cm("Markierung im grauen Vorbefund + Record → nur die Markierung ersetzt, Rest bleibt (getippt, ohne KI); Pause",
   fa.get("quelle") == "getippt" and str(fa.get("text", "")).startswith(A_MAMMO[:200])
   and (MM.get("a_pause") or {}).get("job_zustand") == "PAUSED", json.dumps(fa, ensure_ascii=False)[:400])
cm("In der Pause tippen → getippt (Felder nicht gesperrt)", (gm("a_tippen_pause", "felder") or [{}] * 3)[2].get("quelle")
   == "getippt" and (MM.get("a_tippen_pause") or {}).get("job_zustand") == "PAUSED", str(gm("a_tippen_pause", "zustand")))
cm("F3 auf der Tastatur → Ergebnis übernommen", gq("a_kb_f3")[3:] == ["uebernommen"], str(gq("a_kb_f3")))
ra = str((MM.get("a_ins") or {}).get("result_voll") or "")
cm("INS → Befund mit eingesetztem Satz und getippter Sonographie", "Mammographie: " + A_MAMMO in ra
   and "Sonographie: Keine suspekten Herde." in ra and "ACR: 2\nBIRADS: 2" in ra, ra[:900])
cm("F4 auf der Tastatur → Maske aus/an; SpeechMike III/Premium → Hilfezeile wieder F3/F4",
   gm("a_kb_f4_aus", "an") is False and gm("a_kb_f4_an", "an") is True
   and "F3 = übernehmen · F4 = Maske aus" in str(gm("a_premium", "hilfe")), str(gm("a_premium", "hilfe")))

re1 = str((MM.get("e_ins") or {}).get("result_voll") or "")
cm("v3.15.4 CAS-Band: Record → Pause → in den Befund geklickt → Record (weiter) → INS: Diktat an der Stelle, Rest bleibt",
   (MM.get("e_weiter") or {}).get("einfuegen_ziel") is not None and "ohne Patientenbezug. Zusätzlich kleiner Gelenkerguss "
   "Dieser Text prüft nur" in re1 and re1.startswith("## TEST RaKScribe-Brücke") and (MM.get("e_ins") or {}).get("status")
   == "KONTROLLE", re1[:400])
re2 = str((MM.get("e_ins2") or {}).get("result_voll") or "")
cm("… mit „Nur Text“: die Markierung im Befund wird durch das Diktat ersetzt (kein Befundumbau), nichts an CAS vor EOL",
   "## Befund\nErsetzt ohne Diktat und ohne Patientenbezug. Zusätzlich kleiner Gelenkerguss" in re2
   and (MM.get("e_nt") or {}).get("nur_text") is True and (MM.get("e_antwort") or {}).get("status") != "fertig", re2[:400])
mf = MM.get("menu") or {}
cm("v3.15.4 ☰-Menü: Häkchen weiß (selectcolor), Foto O_menu_haekchen.png; „Nur Text“-Schalter mit hellem Knopf und Rahmen",
   (MM.get("offen") or {}).get("menu_haken") == "#FFFFFF" and str(((MM.get("offen") or {}).get("nur_text_switch") or {})
   .get("border_width")) == "2" and mf.get("ok") is True and (mf.get("helle_pixel_haekchen_spalte") or 0) > 0
   and (MM.get("nach_menu") or {}).get("status") is not None, json.dumps(mf, ensure_ascii=False))

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
cg("EOL im CAS-Modus: Befund an CAS („fertig“), grünes Band zu sehen (noch nicht minimiert), danach minimiert",
   (G.get("cas_antwort") or {}).get("status") == "fertig" and gg("cas_eol", "bestaetigung_sichtbar") is True
   and gg("cas_eol", "fenster") == "normal" and G.get("nach_eol_iconic") is True
   and gg("nach_eol", "fenster") == "iconic" and gg("nach_eol", "cas") is None,
   f"{(G.get('cas_antwort') or {}).get('status')} / Band {gg('cas_eol', 'bestaetigung_sichtbar')} "
   f"{gg('cas_eol', 'fenster')} → {gg('nach_eol', 'fenster')}")
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


# H (v3.13.0): Selbsttest endet von selbst (RAKSCRIBE_SELFTEST_ENDE) — für den Ordi-Probelauf am Büro-PC
def fall_h():
    work = pathlib.Path(tempfile.mkdtemp(prefix="rks_H_"))
    shutil.copy(EXE, work / EXE.name)
    state = work / "selftest.json"
    env = dict(os.environ, APPDATA=str(work / "appdata"), LOCALAPPDATA=str(work / "localappdata"),
               RAKSCRIBE_SELFTEST=str(state), RAKSCRIBE_SELFTEST_ENDE="12")
    t = time.time()
    p = subprocess.Popen([str(work / EXE.name), "--minimiert"], cwd=work, env=env)
    try:
        rc = p.wait(timeout=120)
    except subprocess.TimeoutExpired:
        kill_all(p)
        rc = "hängt"
    try:
        z = json.loads(state.read_text(encoding="utf-8"))
    except Exception:
        z = {}
    return {"rc": rc, "s": round(time.time() - t, 1), "ende": z.get("ende") or {}, "ready": z.get("ready") or {}}


H = fall_h()
check("H_ende", "RAKSCRIBE_SELFTEST_ENDE=12: Selbsttest endet von selbst (Zustand „ende“, Exit 0, minimiert gestartet)",
      H.get("rc") == 0 and bool(H.get("ende")) and H["ende"].get("minimiert_gestartet") is True
      and 12 <= (H.get("s") or 0) <= 90, f"Exit {H.get('rc')} nach {H.get('s')} s, Titel {H['ende'].get('title')!r}")



# W (v3.16.0): WAV-Modus der echten EXE — Kommandozeile, WavQuelle statt Mikrofon, Ablaufskript, endet von selbst
def fall_w():
    work = pathlib.Path(tempfile.mkdtemp(prefix="rks_W_"))
    shutil.copy(EXE, work / EXE.name)
    appdata = work / "appdata"
    (appdata / "RaKScribe").mkdir(parents=True)
    key = work / "schluessel" / "rakscribe-praxis-key.json"
    key.parent.mkdir()
    key.write_text(json.dumps(dummy_key()), encoding="utf-8")
    shutil.copy(AUDIO / "ton_440.ogg", work / "diktat.ogg")
    ablauf = work / "ablauf.json"
    ablauf.write_text(json.dumps({"max_s": 120, "schritte": [
        {"taste": "RECORD"}, {"sprich": "diktat.ogg"}, {"taste": "INS"},
        {"warte_auf": "kontrolle", "timeout_s": 60}, {"merke": "nach_ins"}, {"taste": "EOL"}, {"merke": "nach_eol"},
        {"ende": True}]}), encoding="utf-8")
    env = dict(os.environ, APPDATA=str(appdata), LOCALAPPDATA=str(work / "localappdata"), RAKSCRIBE_SELFTEST_FAKEAUDIO="1")
    env.pop("RAKSCRIBE_SELFTEST", None)
    t = time.time()
    p = subprocess.Popen([str(work / EXE.name), "--wav-ablauf", str(ablauf), "--schluessel", str(key)], cwd=work, env=env)
    try:
        rc = p.wait(timeout=180)
    except subprocess.TimeoutExpired:
        kill_all(p)
        rc = "hängt"
    try:
        z = json.loads((work / "ablauf.zustand.json").read_text(encoding="utf-8"))
    except Exception:
        z = {}
    return {"rc": rc, "s": round(time.time() - t, 1), "z": z}


W = fall_w()
WZ = W.get("z") or {}
wa = (WZ.get("ende") or {}).get("wav_ablauf") or {}


def cw(name, ok_, detail=""):
    check("W_wavmodus", name, ok_, detail)


cw("--wav-ablauf: endet von selbst (Exit 0), Zustand neben dem Ablauf (ablauf.zustand.json), Gast, Schlüssel per --schluessel",
   W.get("rc") == 0 and bool(WZ.get("ende")) and (WZ.get("ende") or {}).get("wav_modus") is True
   and (WZ.get("ende") or {}).get("keys_ready") is True, f"Exit {W.get('rc')} nach {W.get('s')} s")
cw("Ablauf: alle 7 Schritte ok (Record, ogg einspielen, INS, Kontrolle, merken, EOL, merken), Zeiten je Schritt",
   not wa.get("fehler") and len(wa.get("protokoll") or []) == 7 and all(x.get("ok") for x in wa.get("protokoll") or []),
   json.dumps(wa.get("protokoll"), ensure_ascii=False)[:300] + " " + str(wa.get("fehler")))
cw("WavQuelle spielte die Datei (≈ 1,5 s) in Echtzeit-Blöcken ein", 1.3 <= (wa.get("gespielt_s") or 0) <= 1.7,
   str(wa.get("gespielt_s")))
cw("INS → Befund zur Kontrolle; EOL ohne CAS-Auftrag fügt nichts ein (kein Strg+V, Zwischenablage unberührt)",
   (WZ.get("nach_ins") or {}).get("status") == "KONTROLLE"
   and str((WZ.get("nach_ins") or {}).get("result", "")).startswith("## Kniegelenk")
   and (WZ.get("nach_eol") or {}).get("einfuegungen") == 0,
   f"{(WZ.get('nach_ins') or {}).get('status')} / {(WZ.get('nach_eol') or {}).get('einfuegungen')}")

ok = all(r["ok"] for r in results) and a and c and e_lauf and m_lauf
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
          "`G_minimiert.png` / `G_taskleiste.png` (RaKScribe nur als Taskleisten-Symbol), `G_cas_vorne.png` (nach CAS-Auftrag), "
          "`F_ibl_band.png` / `F_ibl_befund.png` / `F_ibl_knopf.png` (v3.13.0 IB-Lab-Zeile, Werte im Befund, Knopf), "
          "`M_maske.png` / `M_warnung.png` / `M_aufnahme.png` / `M_befund.png` / `M_ohne_vorbefund.png` / "
          "`M_befund_ohne_vorbefund.png` (v3.15.0 Mammo-Maske)."]
(OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
sys.exit(0 if ok else 1)
