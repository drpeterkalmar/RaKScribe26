"""Gate (Umbau Schritt 21, Gutachten P2-12): Versionsnummer nur in der Datei VERSION — EXE-Titel und -Badge,
Web-Badge, Seitentitel und Release-Tag lesen sie; Build-Paketliste nur in requirements.txt (feste Versionen).
Aufruf: /usr/bin/python3 tests/offline/test_version_sync.py"""
import pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


V = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
check(f"VERSION = {V} (Form x.y.z)", bool(re.fullmatch(r"\d+\.\d+\.\d+", V)), V)

exe = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE-Titel und -Badge aus app_version()", 'self.title(f"RaKScribe {app_version()} – Röntgen am Kai")' in exe
      and 'text=f" v{app_version()} "' in exe)
check("EXE: keine fest eingetragene Version in Titel/Badge", not re.search(r'title\("RaKScribe \d', exe) and 'text=" v3' not in exe)
import exe_stubs as S  # noqa: E402
mod = S.lade_rakscribe()
check("EXE app_version() liefert VERSION", mod.app_version() == V, mod.app_version())

app = (ROOT / "web_app" / "src" / "App.tsx").read_text(encoding="utf-8")
check("Web-Badge aus VERSION (?raw)", "import appVersionRaw from '../../VERSION?raw';" in app and "v{APP_VERSION}" in app
      and not re.search(r'version-chip">v\d', app))
html = (ROOT / "web_app" / "index.html").read_text(encoding="utf-8")
vite = (ROOT / "web_app" / "vite.config.ts").read_text(encoding="utf-8")
check("Seitentitel: Platzhalter, vite.config.ts setzt VERSION ein",
      "<title>RaKScribe __RAKSCRIBE_VERSION__ – Befundungsassistent</title>" in html and "'../VERSION'" in vite
      and "replaceAll('__RAKSCRIBE_VERSION__', VERSION)" in vite and "versionImTitel()" in vite)
check("… ergibt den Titel „RaKScribe <VERSION>“", f"<title>RaKScribe {V} – Befundungsassistent</title>"
      in html.replace("__RAKSCRIBE_VERSION__", V))

wf = (ROOT / ".github" / "workflows" / "build-exe.yml").read_text(encoding="utf-8")
check("Release-Tag aus VERSION, kein fester Tag im Workflow", "< VERSION)" in wf and not re.search(r'tag=\d+\.\d+', wf))
check("manueller Lauf ohne Tag → Vorabversion test-<Lauf>", "tag=test-${{ github.run_id }}" in wf
      and "prerelease: ${{ steps.version.outputs.prerelease }}" in wf)
check("EXE bündelt VERSION", '--add-data "../VERSION;."' in wf)
check("Build installiert requirements.txt", "pip install -r requirements.txt" in wf)
req = [l.strip() for l in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
check("requirements.txt: alle Pakete fest (==)", req and all("==" in l for l in req), str([l for l in req if "==" not in l]))
pakete = {re.split(r"[=;<> ]", l)[0].lower() for l in req}
check("requirements.txt enthält die Build-Pakete", {"pyinstaller", "customtkinter", "keyboard", "markdown", "numpy", "openai",
                                                   "pillow", "pywin32", "sounddevice", "google-cloud-speech", "google-api-core",
                                                   "grpcio-status"} <= pakete, str(sorted(pakete)))
check("kein build.bat mehr", not (ROOT / "source_code" / "build.bat").exists())
ui = (ROOT / "tests" / "windows" / "exe_ui_test.py").read_text(encoding="utf-8")
check("Windows-UI-Test erwartet bei Test-Builds die VERSION", 'TAG.startswith("test-")' in ui and '"VERSION"' in ui)

print("\n" + ("✅ VERSION PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
