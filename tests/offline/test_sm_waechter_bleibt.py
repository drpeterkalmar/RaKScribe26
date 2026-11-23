"""Gate kaiscribe-sm-waechter-bleibt-n1 (Peter 23.11.2026 09:25): Senf kommt ins SpeechMagic-Diktat, OHNE dass KaiScribe
offen ist. Live 23.11.: 08:13:47 Wächter erkennt SpeechMagic-Diktat 004, 08:13:50 Peter schließt KaiScribe → Prozess samt
Wächter weg, Senf 004 (08:15) nie eingefügt. Jetzt: eigener unsichtbarer Prozess `KaiScribe.exe --sm-waechter` (Mutex je
Windows-Sitzung, kein Fenster), gestartet vom Autostart und von jeder KaiScribe (falls keiner läuft); Fenster zu beendet
ihn nie; neue EXE → Nachfolger. Teil 1: Logik (sm_einfuegen). Teil 2: Autostart (bereitschaft). Teil 3: KaiScribe-Fenster.
Teil 4: Wächter-Prozess ohne KaiScribe-Fenster, echter Thread, Attrappen-SpeechMagic: Senf wird eingefügt.
Synthetische Texte, keine Patientendaten.  Aufruf: python3 tests/offline/test_sm_waechter_bleibt.py"""
import json, os, pathlib, subprocess, sys, tempfile, time, types
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


TMP = tempfile.mkdtemp(prefix="rks_smw_")
os.environ["LOCALAPPDATA"] = os.path.join(TMP, "local")
mod = S.lade_rakscribe()
M, B = mod._sme, mod._bs
LOGS = []
mod.log = lambda *a: LOGS.append(" ".join(str(x) for x in a))

# ───────────────────────────── Teil 1: Logik ─────────────────────────────
check("--sm-waechter / --nachfolger erkannt (Groß/Klein egal), sonst normales Fenster",
      M.waechter_gewuenscht(["--SM-Waechter"]) == (True, False)
      and M.waechter_gewuenscht(["--sm-waechter", "--nachfolger"]) == (True, True)
      and M.waechter_gewuenscht(["--minimiert"]) == (False, False) and M.waechter_gewuenscht([]) == (False, False))
env = M.kind_umgebung({"PATH": "p", "_MEIPASS2": "x", "_PYI_ARCHIVE_FILE": "a", "_PYI_PARENT_PROCESS_LEVEL": "1"})
check("Kind-Umgebung: PyInstaller-Entpackordner nicht vererbt (sonst löscht das Fenster ihn unter dem Wächter weg)",
      env == {"PATH": "p", "PYINSTALLER_RESET_ENVIRONMENT": "1"}, env)
aufrufe = []
ok = M.waechter_starten(r"X:\KaiScribe\Programm\KaiScribe.exe", popen=lambda cmd, **k: aufrufe.append((cmd, k)),
                        umgebung={"PATH": "p", "_MEIPASS2": "x"})
cmd, k = aufrufe[0]
check("waechter_starten: EXE --sm-waechter, losgelöst, ohne Ein-/Ausgabe, ohne PyInstaller-Erbe",
      ok and cmd == [r"X:\KaiScribe\Programm\KaiScribe.exe", "--sm-waechter"] and k["close_fds"]
      and k["stdin"] == subprocess.DEVNULL and "_MEIPASS2" not in k["env"], (cmd, k))
M.waechter_starten("E", nachfolger=True, popen=lambda cmd, **k: aufrufe.append((cmd, k)))
check("… Nachfolger bekommt --nachfolger (wartet auf den Mutex des Vorgängers)",
      aufrufe[-1][0] == ["E", "--sm-waechter", "--nachfolger"])
check("… ohne EXE (Quelltext) / Start scheitert → False",
      not M.waechter_starten(None) and not M.waechter_starten("E", popen=lambda *a, **k: (_ for _ in ()).throw(OSError())))
check("waechter_noetig: Standard kp → ja; SM_SENF = SM_IBL = aus → nein",
      M.waechter_noetig(types.SimpleNamespace(sm_senf=["kp"], sm_ibl=[]))
      and not M.waechter_noetig(types.SimpleNamespace(sm_senf=[], sm_ibl=[])))
check("Mutex je Windows-Sitzung (Local\\); außerhalb Windows: Sperre frei, „läuft?“ unbekannt",
      M.WAECHTER_MUTEX == "Local\\KaiScribe-SM-Waechter" and M.waechter_sperre() is True)
exe = os.path.join(TMP, "KaiScribe.exe")
open(exe, "wb").write(b"3.22.5")
st0 = M.exe_stand(exe)
check("exe_stand: (Größe, Zeit); ohne Pfad/fehlt → None",
      st0 == (6, int(os.stat(exe).st_mtime)) and M.exe_stand(None) is None and M.exe_stand(exe + "x") is None)
p = M.Pruefung(st0)
st1 = (99, st0[1] + 60)
r = [p.pruefen(st0, True, False), p.pruefen(st1, True, False), p.pruefen(st1, True, True), p.pruefen(st1, True, False)]
check("Pruefung: neue EXE erst beim zweiten gleichen Blick (Kopie fertig), nie bei offenem SpeechMagic-Diktat → Nachfolger",
      r[:3] == [(None, ""), (None, ""), (None, "")] and r[3][0] == "nachfolger", r)
check("… X: kurz weg → nichts; SM_SENF/SM_IBL aus → Ende (nicht während eines Diktats)",
      M.Pruefung(st0).pruefen(None, True, False) == (None, "") and M.Pruefung(st0).pruefen(st0, False, False)[0] == "ende"
      and M.Pruefung(st0).pruefen(st0, False, True) == (None, ""))
check("diktat_offen: nur erkannte kp-Diktate zählen (ignorierte Fenster = None nicht)",
      M.diktat_offen(types.SimpleNamespace(sitzungen={1: object()}))
      and not M.diktat_offen(types.SimpleNamespace(sitzungen={1: None})))

# ───────────────────────────── Teil 2: Autostart ─────────────────────────────
vbs = B.waechter_starter_vbs(r"X:\KaiScribe\Programm\KaiScribe.exe")
check("Starter: wartet auf die EXE (X: nach CAS-Login), startet sie unsichtbar (Fensterstil 0) mit --sm-waechter",
      r'Const EXE = "X:\KaiScribe\Programm\KaiScribe.exe"' in vbs and 'sh.Run """" & EXE & """ --sm-waechter", 0, False'
      in vbs and "Do Until fso.FileExists(EXE)" in vbs and "--minimiert" not in vbs, vbs)
daten, start = os.path.join(TMP, "appdata"), os.path.join(TMP, "Startup")
skripte = []


def wsh(skript):
    skripte.append(B.vbs_lesen(skript))
    open(os.path.join(start, B.WAECHTER_LNK), "w").write("lnk")
    return 0


a = B.WaechterAutostart(daten, startup_ordner=start, ausfuehren=wsh, wscript="wscript.exe")
m1 = a.sichern(r"X:\KaiScribe\Programm\KaiScribe.exe")
check("Autostart: Starter + eigene Verknüpfung „KaiScribe SM-Waechter.lnk“ angelegt (wscript //B → Starter)",
      os.path.exists(a.lnk) and os.path.exists(a.starter) and "angelegt" in m1 and "Starter neu" in m1
      and '//B //Nologo' in skripte[0] and B.WAECHTER_STARTER in skripte[0], (m1, skripte))
check("… zweiter Lauf: alles da → nichts zu tun", a.sichern(r"X:\KaiScribe\Programm\KaiScribe.exe") is None
      and len(skripte) == 1)
m3 = a.sichern(r"X:\KaiScribe\Programm\KaiScribe (1).exe")
check("… andere EXE → Starter nachgezogen, Verknüpfung bleibt", m3 and "nachgezogen" in m3 and len(skripte) == 1, m3)
check("… unabhängig vom Menü-Autostart des Fensters (KaiScribe.lnk bleibt unberührt)",
      B.WAECHTER_LNK != B.VERKNUEPFUNG and not os.path.exists(os.path.join(start, B.VERKNUEPFUNG)))
check("… ohne EXE (Quelltext) → nichts", B.WaechterAutostart(daten, startup_ordner=start).sichern(None) is None)

# ───────────────────────────── Teil 3: KaiScribe-Fenster ─────────────────────────────
gestartet = []
laeuft = {"v": False}
alt = (M.win32_oder_none, M.waechter_laeuft, M.waechter_starten, B.exe_pfad)
M.win32_oder_none = lambda: object()
M.waechter_laeuft = lambda: laeuft["v"]
M.waechter_starten = lambda exe, nachfolger=False: (gestartet.append((exe, nachfolger)), True)[1]
B.exe_pfad = lambda: r"X:\KaiScribe\Programm\KaiScribe.exe"
os.environ.pop("RAKSCRIBE_SELFTEST", None)
app = S.baue_app(mod)
spaet = []
app.after = lambda ms, fn=None, *a: spaet.append((ms, fn))
mod.CFG.sm_senf, mod.CFG.sm_ibl = ["kp"], ["kp"]
LOGS.clear()
app._sm_start()
check("Fenster (EXE) startet den Wächter-Prozess, wenn keiner läuft – kein Wächter-Thread im Fenster",
      gestartet == [(r"X:\KaiScribe\Programm\KaiScribe.exe", False)] and app._sm_thread is None
      and any("Wächter-Prozess gestartet" in l for l in LOGS), (gestartet, LOGS))
check("… prüft jede Minute wieder", any(ms == M.PRUEF_S * 1000 and fn == app._sm_prozess_sichern for ms, fn in spaet))
laeuft["v"] = True
app._sm_prozess_sichern()
check("… läuft schon einer → kein zweiter Start", len(gestartet) == 1)
laeuft["v"] = False
app._sm_prozess_sichern()
check("… ist er weg (abgestürzt) → beim nächsten Minuten-Takt wieder gestartet", len(gestartet) == 2)
mod.CFG.sm_senf, mod.CFG.sm_ibl = [], []
app._sm_prozess_sichern()
check("… SM_SENF = SM_IBL = aus → kein Wächter-Prozess", len(gestartet) == 2)
mod.CFG.sm_senf, mod.CFG.sm_ibl = ["kp"], ["kp"]
src = (ROOT / "source_code/RaKScribe.py").read_text(encoding="utf-8")
i = src.index("    def _schliessen(self):")
schliessen = src[i:src.index("\n    # ──", i)]
check("Fenster zu (kp) beendet den Wächter-Prozess nie (_schliessen fasst nur den Fenster-Thread an)",
      "waechter" not in schliessen.lower().replace("_sm_thread", "") and "_sm_prozess" not in schliessen, schliessen)
check("Selbsttest/Quelltext: Wächter wie bisher im Fenster-Thread, aber nur mit freier Sitzungs-Sperre",
      'if exe and not os.environ.get("RAKSCRIBE_SELFTEST"):' in src and "if not _sme.waechter_sperre():" in src)
check("main(): --sm-waechter vor der Fenster-Einzelinstanz (Wächter und Fenster laufen nebeneinander)",
      src.index("_sme.waechter_gewuenscht(sys.argv[1:])") < src.index("erste = (_bs.einzelinstanz_sichern"))
check("EXE-Bau: Modul dabei", "--hidden-import=sm_einfuegen" in (ROOT / ".github/workflows/build-exe.yml").read_text())
M.win32_oder_none, M.waechter_laeuft, M.waechter_starten, B.exe_pfad = alt

# ───────────────────────────── Teil 4: Wächter-Prozess, KaiScribe-Fenster ganz zu ─────────────────────────────
NR = "20261123004"
CMD = r'"C:\casmed\SpeechExec4\CASSpeechMagic.exe" -p 451898 -d 20261123 -n 4 -u kp -h wnd_x -nodevexpress -a i'
TITEL = "CASOnline Diktat - Testpatient *** User: kp"
senf_ordner = os.path.join(TMP, "senf")
schalter = os.path.join(TMP, "Bruecke")
os.makedirs(senf_ordner)
os.makedirs(schalter)
open(os.path.join(schalter, M.SM_FREIGABE_DATEI), "w").write("an")
M.MERKER_X_STANDARD = os.path.join(TMP, "X-speechmagic")


class Api:
    """SpeechMagic-Attrappe: ein Fenster, Textfeld, Einfügen hängt ans Ende."""
    def __init__(self):
        self.procs, self.wins, self.texte, self.einfuege = [], [], {}, []

    def sm_pids(self):
        return [p[0] for p in self.procs]

    def prozess_info(self, pid):
        return next(((p[1], p[2]) for p in self.procs if p[0] == pid), None)

    def fenster(self):
        return list(self.wins)

    def textfeld(self, hwnd):
        return f"E{hwnd}"

    def text(self, edit):
        return self.texte.get(edit)

    def mikrofon(self):
        return "frei"

    def einfuegen(self, edit, text):
        self.einfuege.append(text)
        self.texte[edit] = self.texte.get(edit, "") + text
        return True, ""

    def marken_entfernen(self, edit, marken):
        return True, 0, ""


class Root:
    def __init__(self):
        self.afters, self.zu, self.prot, self.sichtbar = [], False, {}, True

    def withdraw(self):
        self.sichtbar = False

    def title(self, t):
        pass

    def after(self, ms, fn):
        self.afters.append((ms, fn))

    def protocol(self, n, fn):
        self.prot[n] = fn

    def mainloop(self):
        pass

    def destroy(self):
        self.zu = True


api = Api()
roots, autostarts, starts = [], [], []
cfg = types.SimpleNamespace(sm_senf=["kp"], sm_ibl=["kp"], senf_ordner=senf_ordner, ibl_ablage=os.path.join(TMP, "ibl"),
                            sm_schalter_ordner=schalter, sm_uebernehmen_taste="ctrl+alt+s")
alt4 = (M.win32_oder_none, mod._cfg.load_config, mod.tk.Tk, B.WaechterAutostart, B.exe_pfad, M.waechter_starten)
M.win32_oder_none = lambda: api
mod._cfg.load_config = lambda p: cfg
mod.tk.Tk = lambda: (roots.append(Root()), roots[-1])[1]
B.WaechterAutostart = lambda d, log=None: types.SimpleNamespace(sichern=lambda exe: autostarts.append(exe))
B.exe_pfad = lambda: exe
M.waechter_starten = lambda e, nachfolger=False: (starts.append((e, nachfolger)), True)[1]
LOGS.clear()
mod.sm_waechter_main()
root = roots[0]
check("Wächter-Prozess: nur ein verstecktes Tk (kein KaiScribe-Fenster, keine Taskleiste), Log mit pid",
      not root.sichtbar and any("Wächter-Prozess" in l and "gestartet (pid" in l for l in LOGS), LOGS)
time.sleep(0.2)
check("… richtet seinen Autostart selbst ein (für die laufende EXE)", autostarts == [exe], autostarts)
check("… Windows-Abmeldung beendet ihn", "WM_SAVE_YOURSELF" in root.prot)
# Peter hat KaiScribe ganz zu (kein RaKScribeApp in diesem Prozess) und öffnet das SpeechMagic-Diktat
api.procs.append((7, time.time(), CMD))
api.wins.append((100, 7, TITEL))
api.texte["E100"] = "Diktat."
time.sleep(1.5)
with open(os.path.join(senf_ordner, NR + ".json"), "w", encoding="utf-8") as f:       # Senf kommt erst danach
    json.dump({"v": 1, "nr": NR, "status": "fertig", "zeit": "2026-11-23T08:15:00", "befund": "auffaellig",
               "zeilen": ["RH 4 · Knie re · Gelenkerguss"], "weitere_laufen": False}, f)
t0 = time.time()
while time.time() - t0 < 12 and not api.einfuege:
    time.sleep(0.2)
check("KaiScribe-Fenster ganz zu → SpeechMagic-Diktat → [SENF] eingefügt (Senf kam nach dem Öffnen)",
      len(api.einfuege) == 1 and "[SENF] Gelenkerguss" in api.texte["E100"], (api.einfuege, LOGS))
check("… Log: erkannt + eingefügt (nur Nummer/Zeilenzahl)",
      any(NR in l and "erkannt" in l for l in LOGS) and any(NR in l and "eingefügt" in l for l in LOGS), LOGS)
merker = json.load(open(os.path.join(M.MERKER_X_STANDARD, NR + ".json"), encoding="utf-8"))
check("… Merker auf X: (instanzübergreifend) hat „senf“", "senf" in merker["eingefuegt"], merker)
time.sleep(1.2)
check("… einmal je Diktatnummer", len(api.einfuege) == 1)
# neue EXE während das Diktat offen ist → bleibt; Diktat zu → Nachfolger
pruef = [fn for ms, fn in root.afters if ms == M.PRUEF_S * 1000][0]
open(exe, "wb").write(b"3.22.6-neuer")
pruef()
pruef = [fn for ms, fn in root.afters if ms == M.PRUEF_S * 1000][-1]
pruef()
check("neue EXE, SpeechMagic-Diktat offen → Wächter bleibt", not root.zu and starts == [], starts)
api.wins.clear()
time.sleep(1.2)
pruef = [fn for ms, fn in root.afters if ms == M.PRUEF_S * 1000][-1]
pruef()
check("… Diktat zu → Nachfolger (--nachfolger) gestartet, alter Wächter endet",
      starts == [(exe, True)] and root.zu and any("Wächter-Prozess endet: neue KaiScribe-EXE" in l for l in LOGS),
      (starts, root.zu, LOGS[-3:]))
M.win32_oder_none, mod._cfg.load_config, mod.tk.Tk, B.WaechterAutostart, B.exe_pfad, M.waechter_starten = alt4
time.sleep(0.8)

# SM_SENF = SM_IBL = aus → Wächter-Prozess endet sofort
mod._cfg.load_config = lambda p: types.SimpleNamespace(sm_senf=[], sm_ibl=[])
M._SPERRE.clear()
LOGS.clear()
mod.sm_waechter_main()
check("SM_SENF = SM_IBL = aus → Wächter-Prozess endet sofort", any("SM_SENF und SM_IBL aus – endet" in l for l in LOGS),
      LOGS)
mod._cfg.load_config = alt4[1]

print(f"\n{'ALLE GRÜN' if not fails else f'{fails} FEHLER'}")
sys.exit(1 if fails else 0)
