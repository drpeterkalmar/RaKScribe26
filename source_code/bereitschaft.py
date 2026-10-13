"""Bereitschaft (v3.11.0, Peter 13.10.2026): RaKScribe wartet minimiert auf das nächste CAS-Diktat — ohne Windows
importierbar und testbar (tests/offline/test_bereitschaft.py; echter Ablauf: tests/windows/exe_ui_test.py Fall G).

Peter: „Die EXE braucht immer ein paar Sekunden, um zum ersten Mal in den RAM geladen zu werden. Schön wäre, wenn sie als
Symbol in der Taskleiste wartet, bis der nächste Befund diktiert werden soll.“
  Autostart      Menü ☰ „Mit Windows starten (wartet minimiert)“ legt im Benutzer-Autostart RaKScribe.lnk an. Sie startet
                 NICHT die EXE, sondern den lokalen, unsichtbaren Starter %APPDATA%\\RaKScribe\\warte_auf_x.vbs: X: (dort
                 liegt die gemeinsame EXE) gibt es erst nach dem CAS-Login. Der Starter prüft alle 10 s, ob die EXE
                 erreichbar ist, und startet sie dann mit --minimiert; läuft RaKScribe schon (z. B. von der Brücke
                 gestartet), tut er nichts; nach 4 h gibt er still auf. Er merkt sich den Pfad der EXE, aus der der Haken
                 gesetzt wurde — keine lokale Kopie der EXE (Updates bleiben „eine Datei auf X: tauschen“).
  Einzelinstanz  Benannter Mutex je Windows-Sitzung. Ein zweiter Start holt die laufende RaKScribe nach vorne (Datei
                 nach_vorne.json, die Oberfläche prüft sie im CAS-Takt) und beendet sich; mit --minimiert endet er still.
Wahrheit für „Autostart an“ ist die Verknüpfung im Autostart-Ordner (was dort liegt, startet Windows).
"""
import ntpath
import os
import re
import sys
import time

import cas_auftrag as _cas  # gleicher Ordner und gleiche atomaren JSON-Dateien wie der CAS-Auftrag

MINIMIERT = "--minimiert"
STARTER = "warte_auf_x.vbs"
VERKNUEPFUNG = "RaKScribe.lnk"
HILFSSKRIPT = "verknuepfung_anlegen.vbs"
STARTER_LOG = "starter.log"
STARTER_KENNUNG = "RaKScribe-Starter 1"   # Vorlagen-Stand: ändert sich die Vorlage, zieht RaKScribe den Starter nach
TAKT_S = 10
FRIST_S = 4 * 3600
PROZESS_PRAEFIX = "rakscribe26"           # wie die Brücke (windows.prozesse): trifft auch „rakscribe26 (1).exe“
MUTEX = "Local\\RaKScribe26-Einzelinstanz"
SIGNAL = "nach_vorne.json"
SIGNAL_MAX_ALTER_S = 60
BESCHREIBUNG = "RaKScribe wartet minimiert auf das nächste CAS-Diktat"


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


def starter_vbs(exe, takt_s=TAKT_S, frist_s=FRIST_S):
    """Der lokale Starter. Nur der EXE-Pfad (+ Takt/Frist für Tests) ist veränderlich — gleicher Pfad = gleicher Text."""
    wql = (f"SELECT * FROM Win32_Process WHERE Name LIKE '{PROZESS_PRAEFIX}%' "
           f"OR Name = '{_wql(ntpath.basename(exe))}'")
    zeilen = [
        f"' {STARTER_KENNUNG} – angelegt von RaKScribe (Menü ☰ „Mit Windows starten (wartet minimiert)“).",
        "' Nicht von Hand ändern: Haken im Menü aus = diese Datei und die Verknüpfung im Autostart werden gelöscht.",
        "' Wartet nach der Windows-Anmeldung, bis die RaKScribe-EXE erreichbar ist (X: gibt es erst nach dem CAS-Login),",
        "' und startet sie dann minimiert (nur Symbol in der Taskleiste). Läuft RaKScribe schon: nichts tun.",
        f"' Gibt nach {_dauer(frist_s)} still auf. Protokoll: {STARTER_LOG} im selben Ordner.",
        "Option Explicit",
        f'Const EXE = "{_vbs(exe)}"',
        f"Const TAKT_S = {int(takt_s)}",
        f"Const FRIST_S = {int(frist_s)}",
        f'Const WQL = "{_vbs(wql)}"',
        "Dim fso, sh, beginn",
        'Set fso = CreateObject("Scripting.FileSystemObject")',
        'Set sh = CreateObject("WScript.Shell")',
        "beginn = Now",
        "Do",
        "  If Not fso.FileExists(WScript.ScriptFullName) Then",
        '    Notiz "Autostart im Menü ausgeschaltet – Starter beendet"',
        "    WScript.Quit 0",
        "  End If",
        "  If fso.FileExists(EXE) Then",
        "    If RaKScribeLaeuft() Then",
        '      Notiz "RaKScribe läuft schon – nichts zu tun"',
        "    Else",
        "      On Error Resume Next",
        '      sh.Run """" & EXE & """ ' + MINIMIERT + '", 7, False',
        "      If Err.Number <> 0 Then",
        '        Notiz "Start fehlgeschlagen: " & EXE & " (" & Err.Description & ")"',
        "      Else",
        '        Notiz "gestartet (minimiert): " & EXE & " – " & DateDiff("s", beginn, Now) & " s nach dem Start"',
        "      End If",
        "    End If",
        "    WScript.Quit 0",
        "  End If",
        '  If DateDiff("s", beginn, Now) >= FRIST_S Then',
        '    Notiz "aufgegeben: " & EXE & " nach " & FRIST_S & " s nicht erreichbar"',
        "    WScript.Quit 0",
        "  End If",
        "  WScript.Sleep TAKT_S * 1000",
        "Loop",
        "",
        "Function RaKScribeLaeuft()",
        "  ' nur Prozesse dieses Benutzers; im Zweifel False — dann verhindert die EXE selbst eine zweite Instanz",
        "  Dim wmi, p, rc, benutzer, domaene, ich",
        "  RaKScribeLaeuft = False",
        "  On Error Resume Next",
        '  ich = ""',
        '  ich = LCase(CreateObject("WScript.Network").UserName)',
        r'  Set wmi = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2")',
        "  If Err.Number <> 0 Then Exit Function",
        "  For Each p In wmi.ExecQuery(WQL)",
        '    benutzer = ""',
        "    rc = -1",
        "    rc = p.GetOwner(benutzer, domaene)",
        '    If rc = 0 And ich <> "" And LCase(benutzer) = ich Then RaKScribeLaeuft = True',
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
        "' RaKScribe: Autostart-Verknüpfung anlegen (läuft einmal, wird danach gelöscht)",
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
        self.daten_ordner = daten_ordner                              # %APPDATA%\RaKScribe (wie Schlüssel/Einstellungen)
        self.ordner = startup_ordner or autostart_ordner()
        self.log = log or (lambda *a: None)
        self.wscript = wscript or wscript_pfad()
        self.ausfuehren = ausfuehren or (lambda skript: _wscript_ausfuehren(skript, self.wscript))
        self.existiert, self.ordner_da = existiert, ordner_da

    @property
    def lnk(self):
        return os.path.join(self.ordner, VERKNUEPFUNG)

    @property
    def starter(self):
        return os.path.join(self.daten_ordner, STARTER)

    def an(self):
        return os.path.exists(self.lnk)

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
        if not self.an():
            _weg(self.starter)
            return False, ("Autostart konnte nicht eingerichtet werden — die Verknüpfung im Autostart-Ordner fehlt "
                           f"(Windows Script Host gesperrt?, Rückgabe {code}{fehler}).")
        self.log(f"[AUTOSTART] an: {self.lnk} → {self.starter} → {exe} {MINIMIERT}")
        return True, f"Autostart an – nach der Windows-Anmeldung wartet RaKScribe minimiert ({ntpath.basename(exe)})"

    def entfernen(self):
        """Haken aus: Verknüpfung und Starter löschen (ein noch wartender Starter endet beim nächsten Takt)."""
        fehler = []
        for p in (self.lnk, self.starter):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass
            except OSError as e:
                fehler.append(f"{p}: {e}")
        if fehler:
            return False, "Autostart nicht vollständig entfernt: " + "; ".join(fehler)
        self.log("[AUTOSTART] aus: Verknüpfung und Starter entfernt")
        return True, "Autostart aus – RaKScribe startet nicht mehr mit Windows"

    def nachziehen(self, exe_jetzt):
        """Beim Start, wenn der Autostart an ist: den Starter auf Stand halten. Die gemerkte EXE bleibt das Ziel — außer
        sie ist weg, während ihr Ordner erreichbar ist (umgezogen/umbenannt): dann wartet der Starter ab jetzt auf die
        laufende EXE. Ordner nicht erreichbar (X: noch nicht verbunden) → nichts ändern. Fehlender Starter oder ältere
        Vorlage → neu schreiben. Rückgabe: Text fürs Protokoll oder None. Kann auf X: warten → nicht im UI-Thread."""
        if not exe_jetzt or not self.an():
            return None
        text = self._starter_text()
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


# ── Einzelinstanz ──────────────────────────────────────────────────────────────────────────────────────────────────────
_MUTEX = []


def einzelinstanz_sichern(name=MUTEX):
    """True = diese RaKScribe ist die erste in dieser Windows-Sitzung (Mutex gehört ihr bis zum Prozessende), False =
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
    """Wir wurden gerade vom Benutzer gestartet und dürfen nach vorne — dieses Recht der laufenden RaKScribe geben
    (wie die Brücke: AllowSetForegroundWindow(ASFW_ANY))."""
    try:
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(0xFFFFFFFF)
    except Exception:
        pass


def nach_vorne_bitten(ordner, exe=None, version="?", pid=None, jetzt=time.time):
    """Zweiter Start: die laufende RaKScribe bitten, sich nach vorne zu holen (sie prüft alle 0,5 s im CAS-Takt)."""
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
