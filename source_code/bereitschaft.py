"""Bereitschaft (v3.11.0, Peter 13.10.2026): KaiScribe wartet minimiert auf das nächste CAS-Diktat — ohne Windows
importierbar und testbar (tests/offline/test_bereitschaft.py; echter Ablauf: tests/windows/exe_ui_test.py Fall G).

Peter: „Die EXE braucht immer ein paar Sekunden, um zum ersten Mal in den RAM geladen zu werden. Schön wäre, wenn sie als
Symbol in der Taskleiste wartet, bis der nächste Befund diktiert werden soll.“
  Autostart      Menü ☰ „Mit Windows starten (wartet minimiert)“ legt im Benutzer-Autostart KaiScribe.lnk an. Sie startet
                 NICHT die EXE, sondern den lokalen, unsichtbaren Starter %APPDATA%\\KaiScribe\\warte_auf_x.vbs: X: (dort
                 liegt die gemeinsame EXE) gibt es erst nach dem CAS-Login. Der Starter prüft alle 10 s, ob die EXE
                 erreichbar ist, und startet sie dann mit --minimiert; läuft KaiScribe schon (z. B. von der Brücke
                 gestartet), tut er nichts; nach 4 h gibt er still auf. Er merkt sich den Pfad der EXE, aus der der Haken
                 gesetzt wurde — keine lokale Kopie der EXE (Updates bleiben „eine Datei auf X: tauschen“).
                 v3.18.12 (Starter 2): meldet sich CAS gerade an, wartet er auf das CAS-Hauptfenster (höchstens 120 s),
                 dann 15 s Ruhe (CasmedNeu.bat verbindet X: beim CAS-Start neu); läuft KaiScribe 90 s nach dem Start
                 nicht, startet er sie bis zu 3× neu. Jeder Schritt steht in starter.log.
  Einzelinstanz  Benannter Mutex je Windows-Sitzung. Ein zweiter Start holt die laufende KaiScribe nach vorne (Datei
                 nach_vorne.json, die Oberfläche prüft sie im CAS-Takt) und beendet sich; mit --minimiert endet er still.
Wahrheit für „Autostart an“ ist die Verknüpfung im Autostart-Ordner (was dort liegt, startet Windows).
  Umzug          kaiscribe-umzug-n1-exe (20.11.2026): Verknüpfung bis 3.19 „RaKScribe.lnk“ → beim Start (nachziehen) durch
                 KaiScribe.lnk ersetzt; der Starter erkennt KaiScribe.exe und rakscribe26.exe. Der Mutex bleibt gleich,
                 damit alte und neue EXE nie zugleich in einer Sitzung laufen.
"""
import ntpath
import os
import re
import sys
import time

import cas_auftrag as _cas  # gleicher Ordner und gleiche atomaren JSON-Dateien wie der CAS-Auftrag
import umzug as _umzug  # kaiscribe-umzug-n1-exe: Prozessnamen alt + neu

MINIMIERT = "--minimiert"
STARTER = "warte_auf_x.vbs"
VERKNUEPFUNG = "KaiScribe.lnk"
ALT_VERKNUEPFUNG = "RaKScribe.lnk"        # bis 3.19; nachziehen() ersetzt sie durch KaiScribe.lnk
HILFSSKRIPT = "verknuepfung_anlegen.vbs"
STARTER_LOG = "starter.log"
STARTER_KENNUNG = "KaiScribe-Starter 3"   # Vorlagen-Stand: ändert sich die Vorlage, zieht KaiScribe den Starter nach
TAKT_S = 10
FRIST_S = 4 * 3600
# v3.18.12 (Starter 2, Büro-PC-Neustart 14.11.2026): rakscribe26 startete 13:40:23 von X:, eine Sekunde danach verband der
# CAS-Start X: neu (CasmedNeu.bat: net use x: /d /y) – KaiScribe war ohne Fehler weg. Darum: CAS-Anmeldung abwarten,
# Ruhe, nach dem Start prüfen und bis NACHSTARTS-mal neu starten.
CAS_PROZESSE = ("CasMed", "Cas")
CAS_FENSTER = "CAS - *"                   # Hauptfenster nach der Anmeldung („CAS - Med“); davor heißt es „Login“
CAS_MAX_S = 120
RUHE_S = 15
PRUEF_S = 90
NACHSTARTS = 3
PROZESS_MUSTER = _umzug.PROZESS_MUSTER   # KaiScribe.exe, „KaiScribe (1).exe“, rakscribe26*.exe (wie die Brücke)
MUTEX = "Local\\RaKScribe26-Einzelinstanz"
SIGNAL = "nach_vorne.json"
SIGNAL_MAX_ALTER_S = 60
BESCHREIBUNG = "KaiScribe wartet minimiert auf das nächste CAS-Diktat"


def minimiert_gewuenscht(argv):
    return any(str(a).strip().lower() == MINIMIERT for a in (argv or ()))


def exe_pfad():
    """Pfad der laufenden EXE — beim Start aus dem Quelltext None (dann gibt es keinen Autostart)."""
    return os.path.abspath(sys.executable) if getattr(sys, "frozen", False) else None


def gleicher_pfad(a, b):
    return bool(a) and bool(b) and ntpath.normcase(ntpath.normpath(a)) == ntpath.normcase(ntpath.normpath(b))


def wscript_pfad(umgebung=None):
    umgebung = os.environ if umgebung is None else umgebung
    return ntpath.join(umgebung.get("SystemRoot") or umgebung.get("windir") or "C:\\Windows", "System32", "wscript.exe")


def _startup_api():
    """shell:startup über SHGetKnownFolderPath (stimmt auch bei umgeleiteten Ordnern); außerhalb von Windows None."""
    try:
        import ctypes
        from ctypes import wintypes
        shell32, ole32 = ctypes.WinDLL("shell32"), ctypes.WinDLL("ole32")
    except (ImportError, AttributeError, OSError):
        return None

    class GUID(ctypes.Structure):
        _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD), ("d3", wintypes.WORD), ("d4", ctypes.c_ubyte * 8)]
    folderid_startup = GUID(0xB97D20BB, 0xF46A, 0x4C97, (ctypes.c_ubyte * 8)(0xBA, 0x10, 0x5E, 0x36, 0x08, 0x43, 0x08, 0x54))
    shell32.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE,
                                             ctypes.POINTER(ctypes.c_void_p)]
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    ptr = ctypes.c_void_p()
    hr = shell32.SHGetKnownFolderPath(ctypes.byref(folderid_startup), 0, None, ctypes.byref(ptr))
    try:
        return ctypes.wstring_at(ptr.value) if hr == 0 and ptr.value else None
    finally:
        if ptr.value:
            ole32.CoTaskMemFree(ptr)


def autostart_ordner(umgebung=None):
    """Benutzer-Autostart (shell:startup, ohne Admin) — sonst %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup."""
    try:
        pfad = _startup_api()
    except Exception:
        pfad = None
    if pfad:
        return pfad
    umgebung = os.environ if umgebung is None else umgebung
    basis = umgebung.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    return os.path.join(basis, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


# ── Skripte für den Windows Script Host (UTF-16 mit BOM, damit Umlaute in Pfaden und Texten ankommen) ──────────────────
def _vbs(text):
    """VBScript-Zeichenkette: Anführungszeichen verdoppeln."""
    return str(text).replace('"', '""')


def _wql(text):
    """WQL-Zeichenkette in einfachen Anführungszeichen."""
    return str(text).replace("\\", "\\\\").replace("'", "\\'")


def _dauer(s):
    return f"{s // 3600} h" if s >= 3600 and s % 3600 == 0 else f"{s} s"


def _cas_ps():
    """PowerShell-Einzeiler für den Starter (nur einfache Anführungszeichen): Rückgabe 0 = kein CAS in dieser Sitzung,
    1 = CAS läuft ohne Hauptfenster (Anmeldung), 2 = Hauptfenster „CAS - …“ da."""
    return ("$s=(Get-Process -Id $PID).SessionId; "
            f"$c=@(Get-Process -Name {','.join(CAS_PROZESSE)} -ErrorAction SilentlyContinue | "
            "Where-Object {$_.SessionId -eq $s}); "
            "if(-not $c){exit 0}; "
            f"if($c | Where-Object {{$_.MainWindowTitle -like '{CAS_FENSTER}'}}){{exit 2}}; exit 1")


def starter_vbs(exe, takt_s=TAKT_S, frist_s=FRIST_S, cas_max_s=CAS_MAX_S, ruhe_s=RUHE_S, pruef_s=PRUEF_S,
                nachstarts=NACHSTARTS):
    """Der lokale Starter. Nur der EXE-Pfad (+ Zeiten für Tests) ist veränderlich — gleicher Pfad = gleicher Text."""
    wql = ("SELECT * FROM Win32_Process WHERE " + " OR ".join(f"Name LIKE '{_wql(m)}'" for m in PROZESS_MUSTER)
           + f" OR Name = '{_wql(ntpath.basename(exe))}'")
    ps = ("powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -Command "
          f'"{_cas_ps()}"')
    zeilen = [
        f"' {STARTER_KENNUNG} – angelegt von KaiScribe (Menü ☰ „Mit Windows starten (wartet minimiert)“).",
        "' Nicht von Hand ändern: Haken im Menü aus = diese Datei und die Verknüpfung im Autostart werden gelöscht.",
        "' Wartet nach der Windows-Anmeldung, bis die KaiScribe-EXE erreichbar ist (X: gibt es erst nach dem CAS-Login),",
        "' und startet sie dann minimiert (nur Symbol in der Taskleiste). Läuft KaiScribe schon: nichts tun.",
        f"' Meldet sich CAS gerade an (CAS läuft, Hauptfenster „{CAS_FENSTER}“ noch nicht da): bis {_dauer(cas_max_s)} warten,",
        f"' danach {_dauer(ruhe_s)} Ruhe – CasmedNeu.bat trennt X: beim CAS-Start und verbindet neu (net use x: /d /y).",
        f"' Läuft KaiScribe {_dauer(pruef_s)} nach dem Start nicht: bis {nachstarts}× neu starten.",
        f"' Gibt nach {_dauer(frist_s)} still auf. Protokoll: {STARTER_LOG} im selben Ordner.",
        "Option Explicit",
        f'Const EXE = "{_vbs(exe)}"',
        f"Const TAKT_S = {int(takt_s)}",
        f"Const FRIST_S = {int(frist_s)}",
        f"Const CAS_MAX_S = {int(cas_max_s)}",
        f"Const RUHE_S = {int(ruhe_s)}",
        f"Const PRUEF_S = {int(pruef_s)}",
        f"Const NACHSTARTS = {int(nachstarts)}",
        f'Const WQL = "{_vbs(wql)}"',
        f'Const CAS_PS = "{_vbs(ps)}"',
        "Dim fso, sh, beginn, versuch",
        'Set fso = CreateObject("Scripting.FileSystemObject")',
        'Set sh = CreateObject("WScript.Shell")',
        "beginn = Now",
        "versuch = 0",
        "Do",
        "  WarteAufExe",
        "  If KaiScribeLaeuft() Then",
        "    If versuch = 0 Then",
        '      Notiz "KaiScribe läuft schon – nichts zu tun"',
        "    Else",
        '      Notiz "KaiScribe läuft inzwischen – nichts zu tun"',
        "    End If",
        "    WScript.Quit 0",
        "  End If",
        "  WarteAufCas",
        "  WScript.Sleep RUHE_S * 1000",
        "  WarteAufExe",
        "  If KaiScribeLaeuft() Then",
        '    Notiz "KaiScribe läuft inzwischen – nichts zu tun"',
        "    WScript.Quit 0",
        "  End If",
        "  On Error Resume Next",
        "  Err.Clear",
        '  sh.Run """" & EXE & """ ' + MINIMIERT + '", 7, False',
        "  If Err.Number <> 0 Then",
        '    Notiz "Start fehlgeschlagen: " & EXE & " (" & Err.Description & ")"',
        "  Else",
        '    Notiz "gestartet (minimiert): " & EXE & " – " & DateDiff("s", beginn, Now) & " s nach dem Start"'
        ' & Versuchstext()',
        "  End If",
        "  On Error GoTo 0",
        "  WScript.Sleep PRUEF_S * 1000",
        "  If KaiScribeLaeuft() Then",
        '    Notiz "läuft " & PRUEF_S & " s nach dem Start" & Versuchstext()',
        "    WScript.Quit 0",
        "  End If",
        "  versuch = versuch + 1",
        "  If versuch > NACHSTARTS Then",
        '    Notiz "aufgegeben: läuft auch nach " & NACHSTARTS & " Nachstarts nicht"',
        "    WScript.Quit 0",
        "  End If",
        '  Notiz "läuft " & PRUEF_S & " s nach dem Start nicht – Nachstart " & versuch & "/" & NACHSTARTS',
        "Loop",
        "",
        "Sub WarteAufExe()",
        "  ' X: kann nach dem Start wieder fehlen (CAS verbindet neu) → Frist je Runde",
        "  Dim runde",
        "  runde = Now",
        "  Do",
        "    If Not fso.FileExists(WScript.ScriptFullName) Then",
        '      Notiz "Autostart im Menü ausgeschaltet – Starter beendet"',
        "      WScript.Quit 0",
        "    End If",
        "    If fso.FileExists(EXE) Then Exit Sub",
        '    If DateDiff("s", runde, Now) >= FRIST_S Then',
        '      Notiz "aufgegeben: " & EXE & " nach " & FRIST_S & " s nicht erreichbar"',
        "      WScript.Quit 0",
        "    End If",
        "    WScript.Sleep TAKT_S * 1000",
        "  Loop",
        "End Sub",
        "",
        "Sub WarteAufCas()",
        "  ' kein CAS → sofort weiter; CAS ohne Hauptfenster (Anmeldung läuft) → bis CAS_MAX_S warten",
        "  Dim t, z",
        "  t = Now",
        "  z = CasZustand()",
        "  If z <> 1 Then Exit Sub",
        '  Notiz "CAS meldet sich gerade an – warte auf das Hauptfenster (höchstens " & CAS_MAX_S & " s)"',
        "  Do",
        '    If DateDiff("s", t, Now) >= CAS_MAX_S Then',
        '      Notiz "CAS-Hauptfenster nach " & CAS_MAX_S & " s nicht da – starte trotzdem"',
        "      Exit Sub",
        "    End If",
        "    WScript.Sleep 3000",
        "    z = CasZustand()",
        "    If z <> 1 Then",
        "      If z = 2 Then",
        '        Notiz "CAS angemeldet nach " & DateDiff("s", t, Now) & " s – noch " & RUHE_S & " s Ruhe"',
        "      Else",
        '        Notiz "CAS beendet nach " & DateDiff("s", t, Now) & " s"',
        "      End If",
        "      Exit Sub",
        "    End If",
        "  Loop",
        "End Sub",
        "",
        "Function CasZustand()",
        "  ' 0 = kein CAS, 1 = CAS ohne Hauptfenster, 2 = Hauptfenster da; PowerShell fehlt/gesperrt → 0 (nicht blockieren)",
        "  Dim rc",
        "  CasZustand = 0",
        "  On Error Resume Next",
        "  rc = sh.Run(CAS_PS, 0, True)",
        "  If Err.Number = 0 Then",
        "    If rc = 1 Or rc = 2 Then CasZustand = rc",
        "  End If",
        "End Function",
        "",
        "Function Versuchstext()",
        '  Versuchstext = ""',
        '  If versuch > 0 Then Versuchstext = " (Nachstart " & versuch & "/" & NACHSTARTS & ")"',
        "End Function",
        "",
        "Function KaiScribeLaeuft()",
        "  ' nur Prozesse dieses Benutzers; im Zweifel False — dann verhindert die EXE selbst eine zweite Instanz",
        "  Dim wmi, p, rc, benutzer, domaene, ich",
        "  KaiScribeLaeuft = False",
        "  On Error Resume Next",
        '  ich = ""',
        '  ich = LCase(CreateObject("WScript.Network").UserName)',
        r'  Set wmi = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2")',
        "  If Err.Number <> 0 Then Exit Function",
        "  For Each p In wmi.ExecQuery(WQL)",
        '    benutzer = ""',
        "    rc = -1",
        "    rc = p.GetOwner(benutzer, domaene)",
        '    If rc = 0 And ich <> "" And LCase(benutzer) = ich Then KaiScribeLaeuft = True',
        "  Next",
        "End Function",
        "",
        "Sub Notiz(text)",
        "  Dim pfad, f",
        "  On Error Resume Next",
        f'  pfad = fso.GetParentFolderName(WScript.ScriptFullName) & "\\{STARTER_LOG}"',
        "  If fso.FileExists(pfad) Then",
        "    If fso.GetFile(pfad).Size > 65536 Then fso.DeleteFile pfad",
        "  End If",
        "  Set f = fso.OpenTextFile(pfad, 8, True, -1)",
        '  f.WriteLine Now & "  " & text',
        "  f.Close",
        "End Sub",
    ]
    return "\r\n".join(zeilen) + "\r\n"


def verknuepfung_vbs(lnk, ziel, argumente, arbeitsordner, symbol=None, beschreibung=BESCHREIBUNG):
    """Einmal-Skript: Verknüpfung über WScript.Shell anlegen (Rückgabe 0 = gespeichert)."""
    zeilen = [
        "' KaiScribe: Autostart-Verknüpfung anlegen (läuft einmal, wird danach gelöscht)",
        "Option Explicit",
        "Dim sh, v",
        "On Error Resume Next",
        'Set sh = CreateObject("WScript.Shell")',
        f'Set v = sh.CreateShortcut("{_vbs(lnk)}")',
        f'v.TargetPath = "{_vbs(ziel)}"',
        f'v.Arguments = "{_vbs(argumente)}"',
        f'v.WorkingDirectory = "{_vbs(arbeitsordner)}"',
        f'v.Description = "{_vbs(beschreibung)}"',
    ]
    if symbol:
        zeilen.append(f'v.IconLocation = "{_vbs(symbol)},0"')
    zeilen += ["v.Save", "If Err.Number <> 0 Then WScript.Quit 1", "WScript.Quit 0"]
    return "\r\n".join(zeilen) + "\r\n"


def vbs_schreiben(pfad, text):
    os.makedirs(os.path.dirname(pfad) or ".", exist_ok=True)
    roh = b"\xff\xfe" + text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-16-le")
    tmp = f"{pfad}.{os.getpid()}.tmp"
    with open(tmp, "wb") as f:
        f.write(roh)
    os.replace(tmp, pfad)


def vbs_lesen(pfad):
    with open(pfad, "rb") as f:
        roh = f.read()
    if roh.startswith(b"\xff\xfe"):
        return roh[2:].decode("utf-16-le", errors="replace")
    return roh.decode("utf-8", errors="replace")


def starter_exe_lesen(text):
    """EXE-Pfad aus einem Starter (Zeile Const EXE = "…"), sonst None."""
    m = re.search(r'^Const EXE = "((?:[^"]|"")*)"\s*$', text or "", re.M)
    return m.group(1).replace('""', '"') if m else None


def _wscript_ausfuehren(skript, wscript=None, timeout=30):
    import subprocess
    r = subprocess.run([wscript or wscript_pfad(), "//B", "//Nologo", skript], timeout=timeout,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.returncode


def _weg(pfad):
    try:
        os.remove(pfad)
    except OSError:
        pass


class Autostart:
    """Verknüpfung im Benutzer-Autostart → wscript.exe → lokaler Starter → EXE --minimiert. Pfade und der Aufruf des
    Windows Script Host sind einspeisbar (Tests ohne Windows)."""

    def __init__(self, daten_ordner, startup_ordner=None, log=None, ausfuehren=None, wscript=None,
                 existiert=os.path.exists, ordner_da=os.path.isdir):
        self.daten_ordner = daten_ordner                              # %APPDATA%\KaiScribe (wie Schlüssel/Einstellungen)
        self.ordner = startup_ordner or autostart_ordner()
        self.log = log or (lambda *a: None)
        self.wscript = wscript or wscript_pfad()
        self.ausfuehren = ausfuehren or (lambda skript: _wscript_ausfuehren(skript, self.wscript))
        self.existiert, self.ordner_da = existiert, ordner_da

    @property
    def lnk(self):
        return os.path.join(self.ordner, VERKNUEPFUNG)

    @property
    def alt_lnk(self):
        return os.path.join(self.ordner, ALT_VERKNUEPFUNG)

    @property
    def starter(self):
        return os.path.join(self.daten_ordner, STARTER)

    def an(self):
        return os.path.exists(self.lnk) or os.path.exists(self.alt_lnk)

    def _starter_text(self):
        try:
            return vbs_lesen(self.starter)
        except OSError:
            return None

    def ziel(self):
        """EXE, auf die der Starter wartet — None, wenn kein Starter da ist."""
        return starter_exe_lesen(self._starter_text())

    def einrichten(self, exe):
        """Haken an: Starter für DIESE EXE schreiben, Verknüpfung (neu) anlegen. Rückgabe (ok, Meldung)."""
        if not exe:
            return False, "Autostart gibt es nur in der EXE (nicht beim Start aus dem Quelltext)."
        hilfe = os.path.join(self.daten_ordner, HILFSSKRIPT)
        alt_da = os.path.exists(self.alt_lnk)
        code, fehler = None, ""
        try:
            vbs_schreiben(self.starter, starter_vbs(exe))
            vbs_schreiben(hilfe, verknuepfung_vbs(self.lnk, self.wscript, f'//B //Nologo "{self.starter}"',
                                                  self.daten_ordner, symbol=exe))
            os.makedirs(self.ordner, exist_ok=True)
            _weg(self.lnk)  # sonst bliebe ein Fehlschlag unbemerkt (alte Verknüpfung wäre noch da)
            code = self.ausfuehren(hilfe)
        except Exception as e:  # OSError, subprocess.TimeoutExpired …
            fehler = f": {e}"
        finally:
            _weg(hilfe)
        if not os.path.exists(self.lnk):
            if not alt_da:
                _weg(self.starter)
            return False, ("Autostart konnte nicht eingerichtet werden — die Verknüpfung im Autostart-Ordner fehlt "
                           f"(Windows Script Host gesperrt?, Rückgabe {code}{fehler}).")
        _weg(self.alt_lnk)   # bis 3.19: RaKScribe.lnk → zeigte auf den Starter im alten Ordner; sonst zwei Starter
        self.log(f"[AUTOSTART] an: {self.lnk} → {self.starter} → {exe} {MINIMIERT}")
        return True, f"Autostart an – nach der Windows-Anmeldung wartet KaiScribe minimiert ({ntpath.basename(exe)})"

    def entfernen(self):
        """Haken aus: Verknüpfung und Starter löschen (ein noch wartender Starter endet beim nächsten Takt)."""
        fehler = []
        for p in (self.lnk, self.alt_lnk, self.starter):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass
            except OSError as e:
                fehler.append(f"{p}: {e}")
        if fehler:
            return False, "Autostart nicht vollständig entfernt: " + "; ".join(fehler)
        self.log("[AUTOSTART] aus: Verknüpfung und Starter entfernt")
        return True, "Autostart aus – KaiScribe startet nicht mehr mit Windows"

    def nachziehen(self, exe_jetzt):
        """Beim Start, wenn der Autostart an ist: den Starter auf Stand halten. Die gemerkte EXE bleibt das Ziel — außer
        sie ist weg, während ihr Ordner erreichbar ist (umgezogen/umbenannt): dann wartet der Starter ab jetzt auf die
        laufende EXE. Ordner nicht erreichbar (X: noch nicht verbunden) → nichts ändern. Fehlender Starter oder ältere
        Vorlage → neu schreiben. Rückgabe: Text fürs Protokoll oder None. Kann auf X: warten → nicht im UI-Thread."""
        if not exe_jetzt or not self.an():
            return None
        text = self._starter_text()
        if not os.path.exists(self.lnk):
            # kaiscribe-umzug-n1-exe: nur die alte RaKScribe.lnk da → KaiScribe.lnk + Starter im neuen Ordner (Ziel wie gemerkt)
            gemerkt = starter_exe_lesen(text)
            ziel = gemerkt if gemerkt and (self.existiert(gemerkt) or not self.ordner_da(ntpath.dirname(gemerkt))) \
                else exe_jetzt
            ok, meldung = self.einrichten(ziel)
            return (f"[AUTOSTART] umgestellt: {ALT_VERKNUEPFUNG} → {VERKNUEPFUNG} ({ziel})" if ok
                    else f"[AUTOSTART] Umstellung {ALT_VERKNUEPFUNG} → {VERKNUEPFUNG} gescheitert: {meldung}")
        gemerkt = starter_exe_lesen(text)
        ziel = gemerkt or exe_jetzt
        umgezogen = bool(gemerkt) and not gleicher_pfad(gemerkt, exe_jetzt) and not self.existiert(gemerkt) \
            and self.ordner_da(ntpath.dirname(gemerkt))
        if umgezogen:
            ziel = exe_jetzt
        soll = starter_vbs(ziel)
        if text == soll:
            return None
        vbs_schreiben(self.starter, soll)
        if umgezogen:
            return f"[AUTOSTART] nachgezogen: {gemerkt} ist nicht mehr da → Starter wartet jetzt auf {ziel}"
        if not gemerkt:
            return f"[AUTOSTART] Starter fehlte – neu angelegt für {ziel}"
        return f"[AUTOSTART] Starter auf die aktuelle Vorlage gebracht ({ziel})"


# ── kaiscribe-sm-waechter-bleibt-n1: Autostart des SpeechMagic-Wächters (eigener Prozess, kein Fenster) ─────────────
WAECHTER_LNK = "KaiScribe SM-Waechter.lnk"
WAECHTER_STARTER = "sm_waechter_start.vbs"
WAECHTER_KENNUNG = "KaiScribe-SM-Waechter-Starter 1"
WAECHTER_BESCHREIBUNG = "KaiScribe: Senf/IB Lab ins SpeechMagic-Diktat (unsichtbarer Wächter)"


def waechter_starter_vbs(exe, takt_s=TAKT_S, frist_s=FRIST_S, ruhe_s=RUHE_S, arg="--sm-waechter"):
    """Wartet nach der Anmeldung, bis die EXE erreichbar ist (X: erst nach dem CAS-Login), dann Ruhe (CasmedNeu.bat
    verbindet X: neu) und startet sie unsichtbar als Wächter. Läuft schon einer, endet der neue sofort (Mutex)."""
    zeilen = [
        f"' {WAECHTER_KENNUNG} – angelegt vom KaiScribe-SpeechMagic-Wächter (SM_SENF/SM_IBL in config.ini).",
        "' Startet nach der Windows-Anmeldung den unsichtbaren Wächter, sobald die KaiScribe-EXE erreichbar ist.",
        f"' Gibt nach {_dauer(frist_s)} still auf. Protokoll: {STARTER_LOG} im selben Ordner.",
        "Option Explicit",
        f'Const EXE = "{_vbs(exe)}"',
        f"Const TAKT_S = {int(takt_s)}",
        f"Const FRIST_S = {int(frist_s)}",
        f"Const RUHE_S = {int(ruhe_s)}",
        "Dim fso, sh, beginn",
        'Set fso = CreateObject("Scripting.FileSystemObject")',
        'Set sh = CreateObject("WScript.Shell")',
        "beginn = Now",
        "Do Until fso.FileExists(EXE)",
        "  If DateDiff(\"s\", beginn, Now) > FRIST_S Then",
        '    Notiz "SM-Wächter: EXE nicht erreichbar – aufgegeben"',
        "    WScript.Quit 0",
        "  End If",
        "  WScript.Sleep TAKT_S * 1000",
        "Loop",
        "WScript.Sleep RUHE_S * 1000",
        "Do Until fso.FileExists(EXE)",
        "  WScript.Sleep TAKT_S * 1000",
        "  If DateDiff(\"s\", beginn, Now) > FRIST_S Then WScript.Quit 0",
        "Loop",
        f'sh.Run """" & EXE & """ {arg}", 0, False',
        'Notiz "SM-Wächter gestartet"',
        "",
        "Sub Notiz(text)",
        "  On Error Resume Next",
        "  Dim pfad, f",
        f'  pfad = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "{STARTER_LOG}")',
        "  Set f = fso.OpenTextFile(pfad, 8, True, -1)",
        '  f.WriteLine Now & "  " & text',
        "  f.Close",
        "End Sub",
    ]
    return "\r\n".join(zeilen) + "\r\n"


class WaechterAutostart:
    """Verknüpfung „KaiScribe SM-Waechter.lnk“ im Benutzer-Autostart → wscript → sm_waechter_start.vbs → EXE --sm-waechter.
    Unabhängig vom Menü-Haken „Mit Windows starten“ (der startet das Fenster minimiert)."""

    def __init__(self, daten_ordner, startup_ordner=None, log=None, ausfuehren=None, wscript=None):
        self.daten_ordner = daten_ordner
        self.ordner = startup_ordner or autostart_ordner()
        self.log = log or (lambda *a: None)
        self.wscript = wscript or wscript_pfad()
        self.ausfuehren = ausfuehren or (lambda skript: _wscript_ausfuehren(skript, self.wscript))

    @property
    def lnk(self):
        return os.path.join(self.ordner, WAECHTER_LNK)

    @property
    def starter(self):
        return os.path.join(self.daten_ordner, WAECHTER_STARTER)

    def sichern(self, exe):
        """Starter auf DIESE EXE und Verknüpfung anlegen, falls nötig. → Text fürs Protokoll oder None (alles da)."""
        if not exe:
            return None
        soll = waechter_starter_vbs(exe)
        try:
            ist = vbs_lesen(self.starter)
        except OSError:
            ist = None
        meldungen = []
        if ist != soll:
            vbs_schreiben(self.starter, soll)
            meldungen.append(f"Starter {'neu' if ist is None else 'nachgezogen'} ({exe})")
        if not os.path.exists(self.lnk):
            hilfe = os.path.join(self.daten_ordner, "sm_" + HILFSSKRIPT)
            code = None
            try:
                vbs_schreiben(hilfe, verknuepfung_vbs(self.lnk, self.wscript, f'//B //Nologo "{self.starter}"',
                                                      self.daten_ordner, symbol=exe, beschreibung=WAECHTER_BESCHREIBUNG))
                os.makedirs(self.ordner, exist_ok=True)
                code = self.ausfuehren(hilfe)
            except Exception as e:
                code = f"{type(e).__name__}"
            finally:
                _weg(hilfe)
            meldungen.append(f"Verknüpfung {'angelegt' if os.path.exists(self.lnk) else f'NICHT angelegt (Rückgabe {code})'}"
                             f": {self.lnk}")
        return ("[SM] Autostart Wächter: " + "; ".join(meldungen)) if meldungen else None

    def entfernen(self):
        for p in (self.lnk, self.starter):
            _weg(p)


# ── Einzelinstanz ──────────────────────────────────────────────────────────────────────────────────────────────────────
_MUTEX = []


def einzelinstanz_sichern(name=MUTEX):
    """True = diese KaiScribe ist die erste in dieser Windows-Sitzung (Mutex gehört ihr bis zum Prozessende), False =
    läuft schon. Außerhalb von Windows (Tests) immer True; kann der Mutex nicht angelegt werden: lieber starten."""
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except (ImportError, AttributeError, OSError):
        return True
    k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    k32.CreateMutexW.restype = wintypes.HANDLE
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k32.CreateMutexW(None, False, name)
    schon_da = ctypes.get_last_error() == 183   # ERROR_ALREADY_EXISTS
    if not h:
        return True
    if schon_da:
        k32.CloseHandle(h)
        return False
    _MUTEX.append(h)  # halten — Windows gibt ihn beim Prozessende frei
    return True


def vordergrund_erlauben():
    """Wir wurden gerade vom Benutzer gestartet und dürfen nach vorne — dieses Recht der laufenden KaiScribe geben
    (wie die Brücke: AllowSetForegroundWindow(ASFW_ANY))."""
    try:
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(0xFFFFFFFF)
    except Exception:
        pass


def nach_vorne_bitten(ordner, exe=None, version="?", pid=None, jetzt=time.time):
    """Zweiter Start: die laufende KaiScribe bitten, sich nach vorne zu holen (sie prüft alle 0,5 s im CAS-Takt)."""
    _cas._json_schreiben(os.path.join(ordner, SIGNAL), {"pid": os.getpid() if pid is None else pid, "exe": exe,
                                                         "version": version, "zeit": jetzt()})
    vordergrund_erlauben()


def nach_vorne_abholen(ordner, jetzt=time.time):
    """Bitte eines zweiten Starts abholen (Datei wird gelöscht). None, wenn keine da/unlesbar/veraltet."""
    pfad = os.path.join(ordner, SIGNAL)
    if not os.path.exists(pfad):
        return None
    d = _cas._json_lesen(pfad)
    _weg(pfad)
    if d is None:
        return None
    try:
        alt = jetzt() - float(d.get("zeit") or 0)
    except (TypeError, ValueError):
        return None
    return d if alt <= SIGNAL_MAX_ALTER_S else None
