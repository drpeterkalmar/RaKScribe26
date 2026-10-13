"""Gate v3.11.0 (Bereitschaft, Peter 13.10.2026: „als Symbol in der Taskleiste warten, bis der nächste Befund diktiert
werden soll“; Nachtrag 1: X: gibt es erst nach dem CAS-Login → lokaler Starter).
Teil 1: source_code/bereitschaft.py — Starter-Skript (wartet auf die EXE, startet --minimiert, Frist), Verknüpfung
anlegen/entfernen/nachziehen mit Attrappe statt Windows Script Host, Signal „nach vorne“, Argumente.
Teil 2: echter Ablauf aus RaKScribe.py mit Attrappen (exe_stubs): nach EOL im CAS-Modus (v3.12.0: nach der Bestätigung) minimieren (nur wenn
nichts Neues begonnen hat, Menü-Option), ohne CAS-Auftrag nichts; zweiter Start → nach vorne; ohne Schlüssel gewartet →
Hinweis beim Auftrag; Menü-Haken Autostart; main(): Einzelinstanz, --minimiert → Taskleisten-Symbol; Prompt-Hinweis
nicht aus dem minimierten Fenster. Den echten Starter auf Windows prüft tests/windows/exe_ui_test.py (Fall G).
Synthetische Texte, keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_bereitschaft.py"""
import json, os, pathlib, re, subprocess, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: False
mod._chirp3_worker = lambda pcm, sr, loc, token: "Kniegelenk rechts in 2 Ebenen unauffällig."
mod._llm_aufruf = lambda p: "## Kniegelenk rechts\n\n## Befund\nKleiner Gelenkerguss.\n\n## Ergebnis\nKleiner Gelenkerguss."
bs, cas, js = mod._bs, mod._cas, mod._js
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


TMP = pathlib.Path(tempfile.mkdtemp(prefix="rks_bereit_"))
X_EXE = "X:\\RaKScribe\\rakscribe26.exe"

# ───────────────────────────── Teil 1: Modul ─────────────────────────────
check("--minimiert erkannt (auch groß/mit Leerzeichen), sonst nicht",
      bs.minimiert_gewuenscht(["--minimiert"]) and bs.minimiert_gewuenscht(["x", " --MINIMIERT "])
      and not bs.minimiert_gewuenscht([]) and not bs.minimiert_gewuenscht(["--minimiert-nicht"]))

st = bs.starter_vbs(X_EXE)
check("Starter: wartet auf genau diese EXE (Const EXE)", 'Const EXE = "X:\\RaKScribe\\rakscribe26.exe"' in st)
check("Starter: Takt 10 s, Frist 4 h", "Const TAKT_S = 10\r\n" in st and "Const FRIST_S = 14400\r\n" in st
      and "WScript.Sleep TAKT_S * 1000" in st and 'DateDiff("s", beginn, Now) >= FRIST_S' in st)
check("Starter: startet minimiert ohne Fokus (--minimiert, Fensterstil 7, nicht warten)",
      'sh.Run """" & EXE & """ --minimiert", 7, False' in st)
check("Starter: prüft vor dem Start, ob RaKScribe schon läuft (Name wie die Brücke, nur eigener Benutzer)",
      "If RaKScribeLaeuft() Then" in st and "Name LIKE 'rakscribe26%' OR Name = 'rakscribe26.exe'" in st
      and "p.GetOwner(benutzer, domaene)" in st and 'CreateObject("WScript.Network").UserName' in st)
check("Starter: endet, wenn der Haken aus ist (Skript gelöscht)", "If Not fso.FileExists(WScript.ScriptFullName) Then" in st)
check("Starter: keine Kopie der EXE, kein anderes Programm", "CopyFile" not in st and st.count("sh.Run") == 1)
check("Starter: nur Windows-Zeilenenden", "\n" not in st.replace("\r\n", ""))
check("Starter: gleicher Pfad = gleicher Text, anderer Pfad = anderer Text",
      bs.starter_vbs(X_EXE) == st and bs.starter_vbs("C:\\RaKScribe\\rakscribe26.exe") != st)


def bloecke_ok(text):
    """grobe VBScript-Prüfung: Blöcke If/Do/Function/Sub sind geschlossen (einzeilige If … Then x zählen nicht)."""
    stapel = []
    for z in text.splitlines():
        z = z.strip()
        if not z or z.startswith("'"):
            continue
        if re.match(r"^If .* Then$", z):
            stapel.append("If")
        elif z in ("Else",) or z.startswith("ElseIf "):
            if not stapel or stapel[-1] != "If":
                return False
        elif z == "End If":
            if not stapel or stapel.pop() != "If":
                return False
        elif z == "Do":
            stapel.append("Do")
        elif z == "Loop":
            if not stapel or stapel.pop() != "Do":
                return False
        elif z.startswith("For Each "):
            stapel.append("For")
        elif z == "Next":
            if not stapel or stapel.pop() != "For":
                return False
        elif z.startswith("Function "):
            stapel.append("Function")
        elif z == "End Function":
            if not stapel or stapel.pop() != "Function":
                return False
        elif z.startswith("Sub "):
            stapel.append("Sub")
        elif z == "End Sub":
            if not stapel or stapel.pop() != "Sub":
                return False
    return not stapel


check("Starter: VBScript-Blöcke vollständig (If/Do/For/Function/Sub)", bloecke_ok(st))
for pfad in ("C:\\Users\\Jürgen Groß\\Downloads\\rakscribe26 (1).exe", "\\\\casmed\\casmed$\\RaKScribe\\rakscribe26.exe",
             "D:\\O'Brien\\RaKScribe.exe"):
    check(f"Starter merkt sich den Pfad: {pfad}", bs.starter_exe_lesen(bs.starter_vbs(pfad)) == pfad)
check("Apostroph im Dateinamen: WQL maskiert", "Name = 'RaKScribe.exe'" in bs.starter_vbs("D:\\O'Brien\\RaKScribe.exe")
      and "Name = 'Rak\\'s.exe'" in bs.starter_vbs("D:\\x\\Rak's.exe"))
kurz = bs.starter_vbs("/tmp/nie_da/rakscribe26.exe", takt_s=2, frist_s=12)
check("Starter für den Frist-Test: Takt 2 s, Frist 12 s", "Const TAKT_S = 2\r\n" in kurz and "Const FRIST_S = 12\r\n" in kurz
      and "Gibt nach 12 s" in kurz and "Gibt nach 4 h" in st)

vk = bs.verknuepfung_vbs("C:\\Users\\Jürgen\\Startup\\RaKScribe.lnk", "C:\\Windows\\System32\\wscript.exe",
                         '//B //Nologo "C:\\Users\\Jürgen\\AppData\\Roaming\\RaKScribe\\warte_auf_x.vbs"',
                         "C:\\Users\\Jürgen\\AppData\\Roaming\\RaKScribe", symbol=X_EXE)
check("Verknüpfung: wscript.exe mit dem Starter (Anführungszeichen verdoppelt), Symbol der EXE, Rückgabe 0/1",
      'sh.CreateShortcut("C:\\Users\\Jürgen\\Startup\\RaKScribe.lnk")' in vk
      and 'v.TargetPath = "C:\\Windows\\System32\\wscript.exe"' in vk
      and 'v.Arguments = "//B //Nologo ""C:\\Users\\Jürgen\\AppData\\Roaming\\RaKScribe\\warte_auf_x.vbs"""' in vk
      and 'v.IconLocation = "X:\\RaKScribe\\rakscribe26.exe,0"' in vk and "v.Save" in vk
      and "WScript.Quit 1" in vk and vk.rstrip().endswith("WScript.Quit 0") and bloecke_ok(vk))
check("wscript.exe aus %SystemRoot%", bs.wscript_pfad({"SystemRoot": "C:\\WINDOWS"}) == "C:\\WINDOWS\\System32\\wscript.exe"
      and bs.wscript_pfad({}) == "C:\\Windows\\System32\\wscript.exe")
check("Autostart-Ordner ohne Windows-API: %APPDATA%\\…\\Startup",
      bs.autostart_ordner({"APPDATA": "/a"}) == os.path.join("/a", "Microsoft", "Windows", "Start Menu", "Programs", "Startup"))

p = TMP / "umlaut.vbs"
bs.vbs_schreiben(str(p), "' Grüße\nZeile 2\r\n")
roh = p.read_bytes()
check("Skripte als UTF-16 mit BOM und CRLF (Windows Script Host liest Umlaute)", roh[:2] == b"\xff\xfe"
      and roh[2:].decode("utf-16-le") == "' Grüße\r\nZeile 2\r\n" and bs.vbs_lesen(str(p)) == "' Grüße\r\nZeile 2\r\n")


class WshAttrappe:
    """Statt wscript.exe: liest das Einmal-Skript wie der Windows Script Host und „speichert“ die Verknüpfung als JSON."""
    def __init__(self, code=0, anlegen=True, fehler=None):
        self.code, self.anlegen, self.fehler, self.aufrufe = code, anlegen, fehler, []

    def __call__(self, skript):
        text = bs.vbs_lesen(skript)
        self.aufrufe.append(text)
        if self.fehler:
            raise self.fehler

        def wert(feld):
            m = re.search(r'^' + feld + r' = "((?:[^"]|"")*)"', text, re.M)
            return m.group(1).replace('""', '"') if m else None
        lnk = re.search(r'CreateShortcut\("((?:[^"]|"")*)"\)', text).group(1).replace('""', '"')
        if self.anlegen:
            pathlib.Path(lnk).write_text(json.dumps({f: wert("v." + f) for f in (
                "TargetPath", "Arguments", "WorkingDirectory", "IconLocation", "Description")}), encoding="utf-8")
        return self.code


DATEN, STARTUP = TMP / "appdata" / "RaKScribe", TMP / "Startup"
wsh = WshAttrappe()
au = bs.Autostart(str(DATEN), startup_ordner=str(STARTUP), ausfuehren=wsh, wscript="C:\\Windows\\System32\\wscript.exe")
check("Autostart anfangs aus", not au.an() and au.ziel() is None)
ok, text = au.einrichten(None)
check("Start aus dem Quelltext (kein EXE-Pfad): kein Autostart, nichts geschrieben", not ok and "nur in der EXE" in text
      and not DATEN.exists() and wsh.aufrufe == [])
ok, text = au.einrichten(X_EXE)
lnk = json.loads((STARTUP / "RaKScribe.lnk").read_text(encoding="utf-8"))
check("Haken an: Verknüpfung im Autostart → wscript.exe → lokaler Starter", ok and au.an()
      and lnk["TargetPath"] == "C:\\Windows\\System32\\wscript.exe"
      and lnk["Arguments"] == f'//B //Nologo "{DATEN / "warte_auf_x.vbs"}"' and lnk["WorkingDirectory"] == str(DATEN)
      and lnk["IconLocation"] == X_EXE + ",0", str(lnk))
check("… Starter merkt sich die EXE, aus der der Haken gesetzt wurde; Einmal-Skript wieder gelöscht",
      au.ziel() == X_EXE and bs.vbs_lesen(str(DATEN / "warte_auf_x.vbs")) == bs.starter_vbs(X_EXE)
      and not (DATEN / "verknuepfung_anlegen.vbs").exists() and "Autostart an" in text, text)
check("… keine Kopie der EXE im Profil", sorted(f.name for f in DATEN.iterdir()) == ["warte_auf_x.vbs"],
      str(sorted(f.name for f in DATEN.iterdir())))

for name, attrappe in (("Windows Script Host gesperrt (Rückgabe 1, keine Verknüpfung)", WshAttrappe(code=1, anlegen=False)),
                       ("wscript hängt (Zeitüberschreitung)", WshAttrappe(fehler=subprocess.TimeoutExpired("wscript", 30)))):
    au2 = bs.Autostart(str(DATEN), startup_ordner=str(STARTUP), ausfuehren=attrappe, wscript="w.exe")
    ok, text = au2.einrichten("C:\\Neu\\rakscribe26.exe")
    check(f"Fehlschlag: {name} → gemeldet, alte Verknüpfung + Starter weg (kein halber Autostart)",
          not ok and "nicht eingerichtet" in text and not au2.an() and not (DATEN / "warte_auf_x.vbs").exists()
          and not (DATEN / "verknuepfung_anlegen.vbs").exists(), text)

au.einrichten(X_EXE)
ok, text = au.entfernen()
check("Haken aus: Verknüpfung und Starter weg", ok and not au.an() and not (DATEN / "warte_auf_x.vbs").exists()
      and "Autostart aus" in text, text)
check("… zweimal aus ist kein Fehler", au.entfernen()[0])

# Nachziehen beim Start (gemerkte EXE bleibt Ziel — außer sie ist umgezogen)
DA = set()
au3 = bs.Autostart(str(DATEN), startup_ordner=str(STARTUP), ausfuehren=WshAttrappe(), wscript="w.exe",
                   existiert=lambda p: p in DA, ordner_da=lambda o: any(x.startswith(o + "\\") for x in DA) or o in DA)
DL = "C:\\Users\\kp\\Downloads\\rakscribe26.exe"
check("Nachziehen ohne Autostart: nichts", au3.nachziehen(DL) is None and not (DATEN / "warte_auf_x.vbs").exists())
au3.einrichten(X_EXE)
check("Nachziehen ohne EXE-Pfad (Quelltext): nichts", au3.nachziehen(None) is None and au3.ziel() == X_EXE)
DA.update({X_EXE})
check("gemerkte EXE erreichbar, RaKScribe läuft aus Downloads → Ziel bleibt X:", au3.nachziehen(DL) is None and au3.ziel() == X_EXE)
DA.clear()
check("X: noch nicht verbunden (Ordner nicht erreichbar) → Ziel bleibt X:", au3.nachziehen(DL) is None and au3.ziel() == X_EXE)
check("gleiche EXE (andere Schreibweise) → nichts", au3.nachziehen("x:\\raKScribe\\RAKSCRIBE26.EXE") is None)
au3.einrichten(DL)
DA.update({"C:\\Users\\kp\\Downloads\\anderes.txt", X_EXE})
m = au3.nachziehen(X_EXE)
check("EXE umgezogen (Downloads-Datei weg, Ordner da) → Starter wartet jetzt auf die laufende EXE",
      au3.ziel() == X_EXE and m and "nachgezogen" in m, str(m))
bs.vbs_schreiben(str(DATEN / "warte_auf_x.vbs"), bs.starter_vbs(X_EXE, takt_s=30))
m = au3.nachziehen(X_EXE)
check("älterer Starter (andere Vorlage) → auf die aktuelle Vorlage gebracht, Ziel gleich",
      m and "Vorlage" in m and bs.vbs_lesen(str(DATEN / "warte_auf_x.vbs")) == bs.starter_vbs(X_EXE), str(m))
os.remove(DATEN / "warte_auf_x.vbs")
m = au3.nachziehen(X_EXE)
check("Starter fehlt, Verknüpfung da → neu angelegt", au3.ziel() == X_EXE and m and "fehlte" in m, str(m))
au3.entfernen()

check("Einzelinstanz außerhalb von Windows: immer erste Instanz", bs.einzelinstanz_sichern() is True)
SIG = TMP / "localappdata" / "RaKScribe"
uhr = [1000.0]
bs.nach_vorne_bitten(str(SIG), exe=DL, version="3.11.0", pid=4711, jetzt=lambda: uhr[0])
d = bs.nach_vorne_abholen(str(SIG), jetzt=lambda: uhr[0] + 0.4)
check("Zweiter Start: Bitte „nach vorne“ (PID, EXE, Version) abgeholt und gelöscht",
      d == {"pid": 4711, "exe": DL, "version": "3.11.0", "zeit": 1000.0} and not (SIG / "nach_vorne.json").exists()
      and bs.nach_vorne_abholen(str(SIG)) is None, str(d))
bs.nach_vorne_bitten(str(SIG), exe=DL, jetzt=lambda: uhr[0])
check("… veraltete Bitte (> 60 s) wird verworfen und gelöscht",
      bs.nach_vorne_abholen(str(SIG), jetzt=lambda: uhr[0] + 61) is None and not (SIG / "nach_vorne.json").exists())
(SIG / "nach_vorne.json").write_text("kaputt", encoding="utf-8")
check("… unlesbare Datei wird verworfen", bs.nach_vorne_abholen(str(SIG)) is None and not (SIG / "nach_vorne.json").exists())


# ───────────────────────────── Teil 2: EXE-Ablauf ─────────────────────────────
class Var:
    def __init__(self, v=False):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


ORDNER = str(TMP / "cas")
os.makedirs(ORDNER, exist_ok=True)


def ablegen(nr, aid):
    with open(os.path.join(ORDNER, cas.AUFTRAG), "w", encoding="utf-8") as f:
        json.dump({"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": "kp", "bruecke_pid": 4242,
                   "zeit": time.time(), "testbefund": False}, f)


def antwort(aid):
    try:
        with open(os.path.join(ORDNER, f"cas_antwort_{aid}.json"), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


def neue_app(minimieren=True, exe=X_EXE):
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
    S.CLIPBOARD.gesperrt = False
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub(antworten=[("Knie", False), ("Knie rechts", True)] * 3))
    app = S.baue_app(mod)
    app.verzoegert = []  # (ms, Funktion) — welche after()-Aufrufe mit welcher Wartezeit kamen
    app.after = lambda ms, fn=None, *a: (app.verzoegert.append((ms, getattr(fn, "__name__", ""))), app._queue.append((fn, a)))
    app._cas, app._cas_aufnahmen, app._cas_test = None, [], False
    app._cas_kanal = cas.Kanal(ORDNER, pid=777, version="3.11.0", prozess_lebt=lambda pid: True)
    app._fensterziel = mod._fz.Fensterziel(None)
    app.destroy = lambda: None
    app._minimiert_gestartet, app._zweitstarts, app._exe_pfad = False, 0, exe
    app._autostart = bs.Autostart(str(DATEN), startup_ordner=str(STARTUP), ausfuehren=WshAttrappe(), wscript="w.exe")
    app.autostart_var, app.nach_cas_minimieren_var = Var(False), Var(minimieren)
    app.fenster = []  # Fenster-Aufrufe (iconify, deiconify …)
    app.zustand_fenster = "normal"

    def iconify():
        app.fenster.append("iconify")
        app.zustand_fenster = "iconic"

    def deiconify():
        app.fenster.append("deiconify")
        app.zustand_fenster = "normal"
    app.iconify, app.deiconify = iconify, deiconify
    app.lift = app.focus_force = lambda *a: None
    app.attributes = lambda *a: None
    app.state = lambda *a: app.zustand_fenster
    return app


def bis_ruhe(app, timeout=8):
    return S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)


# 1. CAS-Auftrag → Testbefund → EOL → Bestätigung → danach minimiert
app = neue_app()
ablegen("20261013101", "m1")
app._cas_einmal()
check("Auftrag angenommen, Fenster nach vorne geholt", app._cas is not None and "deiconify" in app.fenster
      and antwort("m1").get("status") == "angenommen")
app.cas_testbefund()
app.verzoegert.clear()
app.befund_fertig()
check("EOL im CAS-Modus: Befund an CAS, grüne Bestätigung, Minimieren erst danach vorgemerkt (v3.12.0: 4,6 s)",
      antwort("m1").get("status") == "fertig" and (mod.MINIMIEREN_NACH_EOL_MS, "_minimieren_wenn_ruhig") in app.verzoegert
      and mod.MINIMIEREN_NACH_EOL_MS > mod.BESTAETIGUNG_MS >= 4000 and (mod.BESTAETIGUNG_MS, "<lambda>") in app.verzoegert
      and "An CAS übergeben: 20261013101" in getattr(app, "_bestaetigung_text", "") and "iconify" not in app.fenster,
      str(app.verzoegert))
S.pump(app, lambda: False, 0.3)
check("… danach als Symbol in der Taskleiste (iconify), Felder leer", app.fenster.count("iconify") == 1
      and app.zustand_fenster == "iconic" and app.result_text.text == "", str(app.fenster))

# 2. Menü-Option aus → kein Minimieren
app = neue_app(minimieren=False)
ablegen("20261013102", "m2")
app._cas_einmal()
app.cas_testbefund()
app.befund_fertig()
S.pump(app, lambda: False, 0.3)
check("Option „Nach CAS-Befund minimieren“ aus → Fenster bleibt", antwort("m2").get("status") == "fertig"
      and "iconify" not in app.fenster, str(app.fenster))

# 3. bis zum Minimieren beginnt Neues → Fenster bleibt
for name, dazwischen in (
        ("neuer CAS-Auftrag", lambda a: (ablegen("20261013104", "m4"), a._cas_einmal())),
        ("F10-Aufnahme", lambda a: a.toggle_recording()),
        ("Text links eingetippt", lambda a: a.transcript_text.insert("end", "Schulter links"))):
    app = neue_app()
    ablegen("20261013103", "m3")
    app._cas_einmal()
    app.cas_testbefund()
    app.befund_fertig()
    dazwischen(app)
    S.pump(app, lambda: False, 0.3)
    check(f"EOL, dann {name} vor dem Minimieren → nicht minimieren", "iconify" not in app.fenster, str(app.fenster))
    if app.is_recording:
        app.reset_dictation()
        S.pump(app, lambda: False, 0.3)
    if app._cas is not None:
        app.cas_abbrechen()

# 4. ohne CAS-Auftrag ändert sich nichts
app = neue_app()
app.result_text.text = "## Knie\n\n## Befund\nX.\n\n## Ergebnis\nY."
app.befund_fertig()
S.pump(app, lambda: False, 0.3)
check("ohne CAS-Auftrag: EOL kopiert wie bisher, kein Minimieren", S.CLIPBOARD.data.get(13, "").startswith("## Knie")
      and "iconify" not in app.fenster and not any(f == "_minimieren_wenn_ruhig" for _, f in app.verzoegert))
app = neue_app()
app.toggle_recording()
S.pump(app, lambda: app._aufnahme is not None and len(app._aufnahme.puffer) >= 15)
app.toggle_recording()
bis_ruhe(app)
S.pump(app, lambda: False, 0.3)
check("ohne CAS-Auftrag: F10-Diktat fügt ein wie bisher, kein Minimieren", S.AUFZ.tasten == ["ctrl+v"]
      and "iconify" not in app.fenster, f"{S.AUFZ.tasten} {app.fenster}")

# 5. zweiter Start → dieses Fenster nach vorne
app = neue_app()
app.zustand_fenster = "iconic"
bs.nach_vorne_bitten(ORDNER, exe=X_EXE, version="3.11.0", pid=999)
app._cas_einmal()
check("zweiter Start derselben EXE → minimiertes Fenster nach vorne, kein Hinweis", app._zweitstarts == 1
      and app.fenster == ["deiconify"] and app.zustand_fenster == "normal" and not getattr(app, "_letzter_hinweis", ""))
app._cas_einmal()
check("… Bitte nur einmal ausgeführt", app._zweitstarts == 1 and app.fenster == ["deiconify"])
bs.nach_vorne_bitten(ORDNER, exe=DL, version="3.12.0", pid=999)
app._cas_einmal()
check("zweiter Start einer anderen EXE → nach vorne + Hinweis „erst dieses Fenster schließen“", app._zweitstarts == 2
      and "läuft schon" in getattr(app, "_letzter_hinweis", ""), getattr(app, "_letzter_hinweis", ""))

# 6. minimiert ohne Schlüssel gewartet → beim Auftrag Sperre + Hinweis
app = neue_app()
mod.keys_ready = lambda: False
app._show_gate = lambda: setattr(app, "gate", "SPERRE")
ablegen("20261013105", "m5")
app._cas_einmal()
check("ohne Schlüssel: Auftrag angenommen, Fenster vorne, Sperre + Hinweis „Praxis-Schlüssel laden“",
      antwort("m5").get("status") == "angenommen" and "deiconify" in app.fenster and app.gate == "SPERRE"
      and app._status_raw == "LOCKED" and "Praxis-Schlüssel" in getattr(app, "_letzter_hinweis", ""),
      f"{app._status_raw} {getattr(app, '_letzter_hinweis', '')}")
mod.keys_ready = lambda: True
app.cas_abbrechen()

# 7. Menü-Haken „Mit Windows starten (wartet minimiert)“
app = neue_app()
app.autostart_var.set(True)
app._autostart_umschalten()
check("Haken an → Verknüpfung + Starter für diese EXE, Einstellung gespeichert, Hinweis",
      app._autostart.an() and app._autostart.ziel() == X_EXE and mod.einstellung_lesen("autostart") is True
      and "Autostart an" in getattr(app, "_letzter_hinweis", "") and app.autostart_var.get() is True)
app2 = neue_app(exe=DL)
app2._autostart_umstellen()
check("„auf diese EXE umstellen“ → Starter wartet auf die laufende EXE", app2._autostart.ziel() == DL)
app.autostart_var.set(False)
app._autostart_umschalten()
check("Haken aus → Verknüpfung + Starter weg, Einstellung aus", not app._autostart.an()
      and mod.einstellung_lesen("autostart") is False and app.autostart_var.get() is False)
app._autostart.ausfuehren = WshAttrappe(code=1, anlegen=False)
app.autostart_var.set(True)
app._autostart_umschalten()
check("Haken an, aber Windows Script Host gesperrt → Fehlermeldung, Haken wieder aus",
      app.autostart_var.get() is False and S.AUFZ.dialoge and S.AUFZ.dialoge[-1][0] == "showerror"
      and "nicht eingerichtet" in S.AUFZ.dialoge[-1][2], str(S.AUFZ.dialoge))
app._exe_pfad = None
app._autostart_nachziehen()
check("Nachziehen im Hintergrund ohne EXE-Pfad: still", True)

# 8. Prompt-Hinweis nicht aus dem minimierten Fenster
mod.PROMPT_HINWEIS = "Alte Datei radiology_prompt_v4.txt ohne Versionsmarker (Test)"
app = neue_app()
app.zustand_fenster = "iconic"
app._prompt_hinweis()
check("Prompt-Hinweis bei minimiertem Fenster: kein Dialog, später erneut prüfen", S.AUFZ.dialoge == []
      and (3000, "_prompt_hinweis") in app.verzoegert, str(app.verzoegert))
app.zustand_fenster = "normal"
app._cas = cas.Auftrag({"auftrag_id": "x", "nr": "20261013106"})
app._prompt_hinweis()
check("… Fenster sichtbar, aber CAS-Diktat offen: kein Dialog mitten ins Diktat", S.AUFZ.dialoge == [])
app._cas = None
app._prompt_hinweis()
app._prompt_hinweis()
check("… Fenster sichtbar → Hinweis genau einmal", [d[0] for d in S.AUFZ.dialoge] == ["showinfo"], str(S.AUFZ.dialoge))
mod.PROMPT_HINWEIS = ""

# 9. main(): Einzelinstanz und --minimiert
os.environ["LOCALAPPDATA"] = str(TMP / "lad")
aufrufe = []


class FakeApp:
    def __init__(self, minimiert=False):
        aufrufe.append(("app", minimiert))

    def iconify(self):
        aufrufe.append("iconify")

    def after(self, ms, fn=None, *a):
        aufrufe.append(("after", ms, getattr(fn, "__name__", "")))

    def mainloop(self):
        aufrufe.append("mainloop")


orig = (mod._bs.einzelinstanz_sichern, mod.init_runtime, mod.RaKScribeApp, list(sys.argv))
mod.RaKScribeApp = FakeApp
mod.init_runtime = lambda: aufrufe.append("init")
signal = TMP / "lad" / "RaKScribe" / "nach_vorne.json"
try:
    mod._bs.einzelinstanz_sichern = lambda: False
    sys.argv[:] = ["rakscribe26.exe", "--minimiert"]
    mod.main()
    check("main(): läuft schon + --minimiert (Autostart) → still beenden, nichts geladen, keine Bitte",
          aufrufe == [] and not signal.exists(), str(aufrufe))
    sys.argv[:] = ["rakscribe26.exe"]
    mod.main()
    d = json.loads(signal.read_text(encoding="utf-8")) if signal.exists() else {}
    check("main(): läuft schon + normaler Start → Bitte „nach vorne“ an die laufende, nichts geladen",
          aufrufe == [] and d.get("version") == mod.app_version() and "zeit" in d, str(d))
    mod._bs.einzelinstanz_sichern = lambda: True
    sys.argv[:] = ["rakscribe26.exe", "--minimiert"]
    mod.main()
    check("main(): --minimiert → laden, Fenster minimiert anlegen, iconify vor und nach dem CTk-Verstecken",
          aufrufe == ["init", ("app", True), "iconify", ("after", 0, "iconify"), "mainloop"], str(aufrufe))
    aufrufe.clear()
    sys.argv[:] = ["rakscribe26.exe"]
    mod.main()
    check("main(): normaler Start → Fenster wie bisher (kein iconify)", aufrufe == ["init", ("app", False), "mainloop"],
          str(aufrufe))
finally:
    mod._bs.einzelinstanz_sichern, mod.init_runtime, mod.RaKScribeApp, sys.argv[:] = orig[0], orig[1], orig[2], orig[3]

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
