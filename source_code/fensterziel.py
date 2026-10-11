"""Einfüge-Ziel für SpeechMike-EOL (v3.8.0, Peter 11.10., Nachtrag 2/3): den Befund ins RICHTIGE Fenster schicken.

Beim Weiterschicken per EOL ist RaKScribe oft selbst vorne (Peter hat den Befund korrigiert). Ziel ist dann das Fenster,
das VOR dem Wechsel zu RaKScribe vorne war (SpeechMagic/RIS): die Oberfläche merkt sich alle 0,5 s das letzte fremde
Vordergrundfenster. Vor Strg+V wird es aktiviert und geprüft, dass es wirklich vorne ist — sonst nur kopieren + Hinweis
(lieber nicht einfügen als ins falsche Fenster). Ist beim EOL ein fremdes Fenster vorne, kommt Strg+V dorthin (wie F10).
Ohne Windows importierbar; Win32 über ctypes, in Tests eine Attrappe (tests/offline/test_speechmike_ablauf.py).
"""
import os
import time

# Taskleiste, Desktop, Startmenü/Suche, Task-Ansicht, Kontextmenüs — nie Einfüge-Ziel
NICHT_ZIEL = frozenset({
    "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "Progman", "WorkerW", "NotifyIconOverflowWindow", "TaskListThumbnailWnd",
    "MultitaskingViewFrame", "ForegroundStaging", "TopLevelWindowForOverflowXamlIsland", "Windows.UI.Core.CoreWindow",
    "XamlExplorerHostIslandWindow", "#32768",
})


class Win32:
    """Die nötigen user32-Aufrufe (eigene WinDLL-Instanz mit 64-Bit-sicheren Typen)."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self._c = ctypes
        u = ctypes.WinDLL("user32", use_last_error=True)
        u.GetForegroundWindow.restype = wintypes.HWND
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        for f in ("IsWindow", "IsWindowVisible", "IsIconic", "SetForegroundWindow"):
            getattr(u, f).argtypes = [wintypes.HWND]
            getattr(u, f).restype = wintypes.BOOL
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self._u, self._dword = u, wintypes.DWORD

    def vordergrund(self):
        return self._u.GetForegroundWindow() or None

    def pid(self, hwnd):
        p = self._dword(0)
        self._u.GetWindowThreadProcessId(hwnd, self._c.byref(p))
        return p.value

    def titel(self, hwnd):
        buf = self._c.create_unicode_buffer(512)
        self._u.GetWindowTextW(hwnd, buf, 512)
        return buf.value

    def klasse(self, hwnd):
        buf = self._c.create_unicode_buffer(256)
        self._u.GetClassNameW(hwnd, buf, 256)
        return buf.value

    def gueltig(self, hwnd):
        return bool(self._u.IsWindow(hwnd)) and bool(self._u.IsWindowVisible(hwnd))

    def aktivieren(self, hwnd):
        if self._u.IsIconic(hwnd):
            self._u.ShowWindow(hwnd, 9)  # SW_RESTORE
        return bool(self._u.SetForegroundWindow(hwnd))


def win32_oder_none():
    try:
        return Win32()
    except Exception:
        return None  # kein Windows (Mac-Tests) → nie einfügen, nur kopieren


class Fensterziel:
    def __init__(self, api=None, eigene_pid=None):
        self.api = api
        self.eigene_pid = os.getpid() if eigene_pid is None else eigene_pid
        self.letztes = None  # (hwnd, titel) des letzten fremden Vordergrundfensters

    def _info(self, hwnd):
        if not hwnd or self.api is None:
            return None
        try:
            return {"hwnd": hwnd, "pid": self.api.pid(hwnd), "titel": self.api.titel(hwnd) or "",
                    "klasse": self.api.klasse(hwnd) or ""}
        except Exception:
            return None

    def _fremd(self, info):
        return bool(info) and info["pid"] != self.eigene_pid and info["klasse"] not in NICHT_ZIEL

    def merken(self):
        """Alle 0,5 s aus der Tk-Schleife: letztes fremdes Vordergrundfenster (mit Titel) merken."""
        if self.api is None:
            return
        info = self._info(self.api.vordergrund())
        if self._fremd(info) and info["titel"].strip():
            self.letztes = (info["hwnd"], info["titel"])

    def ziel(self):
        """(hwnd, titel, aktivieren_noetig) für Strg+V — oder (None, grund, False): dann nur kopieren."""
        if self.api is None:
            return None, "kein Windows", False
        vg = self._info(self.api.vordergrund())
        if self._fremd(vg):
            return vg["hwnd"], vg["titel"], False
        if self.letztes:
            try:
                if self.api.gueltig(self.letztes[0]):
                    return self.letztes[0], self.letztes[1], True
            except Exception:
                pass
            return None, "das gemerkte Fenster ist geschlossen", False
        return None, "kein Zielfenster gemerkt", False

    def ist_vorne(self, hwnd):
        try:
            return self.api is not None and self.api.vordergrund() == hwnd
        except Exception:
            return False

    def aktivieren_und_pruefen(self, hwnd, warten_s=0.6):
        """Fenster nach vorne holen und prüfen, dass es wirklich vorne ist (Windows verweigert das gelegentlich)."""
        try:
            self.api.aktivieren(hwnd)
        except Exception:
            return False
        ende = time.time() + warten_s
        while time.time() < ende:
            if self.ist_vorne(hwnd):
                return True
            time.sleep(0.03)
        return self.ist_vorne(hwnd)
