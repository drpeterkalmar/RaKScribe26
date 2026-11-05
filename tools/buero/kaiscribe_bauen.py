"""KaiScribe-EXE am Büro-PC bauen und testen – Ersatz für build-exe.yml + test-exe-windows.yml (GitHub Actions), seit
das Repo privat wird (kaiscribe-privat-n1, 05.11.2026; Peter-Regel: private Repos ohne Cloud-CI, Muster ci-ohne-runner).

Läuft am Büro-PC mit `py -3.12` (nur Standardbibliothek; die Bau-venv legt es selbst an) auf einem Quellstand, den der
Ordi-Hermes vom Mac geholt hat (https://mac-mini…:8451/quelle/kaiscribe/quelle.zip, Prüfsumme laut quelle-stand):

  py -3.12 Q\\tools\\buero\\kaiscribe_bauen.py --quelle Q --arbeit W --commit <sha> --tag <VERSION|test-…>
                                              [--abgabe https://mac-mini…:8451/quelle/kaiscribe/ablage] [--ohne-ui-test]

1. venv %LOCALAPPDATA%\\KaiScribe-Bau\\venv (bleibt für den nächsten Bau), pip install -r requirements.txt + Testwerkzeuge
2. PyInstaller mit GENAU den Argumenten aus .github/workflows/build-exe.yml (eine Quelle, kein zweites Rezept)
3. Windows-UI-Test tests/windows/exe_ui_test.py gegen die gebaute EXE (wie test-exe-windows.yml). Schutz am echten PC:
   läuft schon eine rakscribe26.exe in dieser Sitzung (gleicher Einzelinstanz-Mutex) oder liegt die echte
   Autostart-Verknüpfung RaKScribe.lnk (Fall G legt sie an und löscht sie wieder) → nicht testen, KSBAU=belegt.
4. Abgabe an den Mac (POST, nur Tailnet): EXE + report.md; der Mac legt daraus das GitHub-Release an (angemeldet,
   ~/.hermes/scripts/kaiscribe_bau.py). Kein Token am Büro-PC.
Letzte Zeile:  KSBAU=<ok|fehler|belegt> COMMIT=<sha> TAG=<tag> SHA256=<exe|-> UITEST=<pass>/<gesamt> DAUER=<s> GRUND=<…>
"""
import argparse
import hashlib
import os
import pathlib
import re
import shlex
import subprocess
import sys
import time
import urllib.request

WF = pathlib.Path(".github") / "workflows" / "build-exe.yml"
TESTWERKZEUGE = ["pillow", "pywin32", "cryptography", "psutil"]   # wie test-exe-windows.yml


def pyinstaller_args(workflow_text):
    """Die PyInstaller-Argumente aus build-exe.yml (Zeile `pyinstaller --onefile …`), ohne das Programm selbst."""
    for zeile in workflow_text.splitlines():
        z = zeile.strip()
        if z.startswith("pyinstaller ") and "--onefile" in z:
            return shlex.split(z)[1:]
    raise ValueError("keine pyinstaller-Zeile in build-exe.yml")


def autostart_lnk():
    """Echter Autostart-Ordner dieses Benutzers (wie bereitschaft.autostart_ordner, ohne API-Aufruf)."""
    return pathlib.Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" \
        / "RaKScribe.lnk"


def laeuft_rakscribe():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq rakscribe26.exe", "/NH"], capture_output=True, text=True,
                       timeout=60)
    return "rakscribe26.exe" in r.stdout.lower()


def ui_zaehlen(text):
    return len(re.findall(r"^PASS ", text, re.M)), len(re.findall(r"^(?:PASS|FAIL) ", text, re.M))


def lauf(cmd, log, cwd=None, frist=1800, env=None):
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        p = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, timeout=frist, env=env)
    return p.returncode


def abgeben(url, datei, commit, tag, sha, name):
    req = urllib.request.Request(url, data=datei.read_bytes(), method="POST", headers={
        "Content-Type": "application/octet-stream", "X-Commit": commit, "X-Tag": tag, "X-Sha256": sha, "X-Datei": name})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.status


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quelle", required=True)
    ap.add_argument("--arbeit", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--abgabe", default="")
    ap.add_argument("--ohne-ui-test", action="store_true")
    a = ap.parse_args(argv)
    q, w = pathlib.Path(a.quelle).resolve(), pathlib.Path(a.arbeit).resolve()
    w.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    erg = {"KSBAU": "fehler", "SHA256": "-", "UITEST": "0/0", "GRUND": ""}

    def ende(e, grund=""):
        erg["KSBAU"], erg["GRUND"] = e, grund
        print("KSBAU=%s COMMIT=%s TAG=%s SHA256=%s UITEST=%s DAUER=%d GRUND=%s" % (
            erg["KSBAU"], a.commit, a.tag, erg["SHA256"], erg["UITEST"], time.time() - t0, erg["GRUND"] or "-"), flush=True)
        return 0 if e == "ok" else (3 if e == "belegt" else 1)

    if not re.fullmatch(r"(\d+\.\d+\.\d+|test-[0-9A-Za-z-]+)", a.tag):
        return ende("fehler", "Tag ungültig")
    version = (q / "VERSION").read_text(encoding="utf-8").strip()
    if not a.tag.startswith("test-") and a.tag != version:
        return ende("fehler", "Tag %s passt nicht zu VERSION %s" % (a.tag, version))
    if not a.ohne_ui_test:
        if laeuft_rakscribe():
            return ende("belegt", "eine rakscribe26.exe läuft in dieser Sitzung (UI-Test teilt ihren Mutex)")
        if autostart_lnk().exists():
            return ende("belegt", "echte Autostart-Verknüpfung RaKScribe.lnk vorhanden (UI-Test Fall G würde sie löschen)")

    print("1/4 Bau-venv", flush=True)
    venv = pathlib.Path(os.environ["LOCALAPPDATA"]) / "KaiScribe-Bau" / "venv"
    py = venv / "Scripts" / "python.exe"
    if not py.exists():
        if lauf([sys.executable, "-m", "venv", str(venv)], w / "venv.log", frist=600):
            return ende("fehler", "venv anlegen")
    if lauf([str(py), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", str(q / "requirements.txt")]
            + TESTWERKZEUGE, w / "pip.log", frist=1800):
        return ende("fehler", "pip install (siehe pip.log)")

    print("2/4 PyInstaller", flush=True)
    args = pyinstaller_args((q / WF).read_text(encoding="utf-8"))
    if lauf([str(venv / "Scripts" / "pyinstaller.exe"), "--noconfirm", *args], w / "pyinstaller.log",
            cwd=q / "source_code", frist=2400):
        return ende("fehler", "PyInstaller (siehe pyinstaller.log)")
    exe = q / "source_code" / "dist" / "rakscribe26.exe"
    if not exe.exists():
        return ende("fehler", "dist\\rakscribe26.exe fehlt")
    erg["SHA256"] = hashlib.sha256(exe.read_bytes()).hexdigest()

    bericht = w / "ui-report" / "report.md"
    if a.ohne_ui_test:
        erg["UITEST"] = "ausgelassen"
    else:
        print("3/4 Windows-UI-Test", flush=True)
        code = lauf([str(py), str(q / "tests" / "windows" / "exe_ui_test.py"), str(exe), str(w / "ui-report"), a.tag],
                    w / "ui-test.log", cwd=q, frist=2400)
        n_ok, n = ui_zaehlen((w / "ui-test.log").read_text(encoding="utf-8", errors="replace"))
        erg["UITEST"] = "%d/%d" % (n_ok, n)
        if autostart_lnk().exists():   # Fall G hat aufgeräumt – sonst sofort melden
            return ende("fehler", "UI-Test hat RaKScribe.lnk im Autostart hinterlassen")
        if code != 0 or n == 0 or n_ok != n:
            return ende("fehler", "UI-Test rot (Exit %d, %s)" % (code, erg["UITEST"]))

    if a.abgabe:
        print("4/4 Abgabe an den Mac", flush=True)
        try:
            abgeben(a.abgabe, exe, a.commit, a.tag, erg["SHA256"], "rakscribe26.exe")
            if bericht.exists():
                abgeben(a.abgabe, bericht, a.commit, a.tag, hashlib.sha256(bericht.read_bytes()).hexdigest(), "report.md")
        except Exception as ex:  # noqa: BLE001
            return ende("fehler", "Abgabe an den Mac: %s" % str(ex)[:120])
    return ende("ok")


if __name__ == "__main__":
    sys.exit(main())
