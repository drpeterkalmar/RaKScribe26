"""Gate (Umbau Schritt 16, Gutachten P2-1): RaKScribe.py ist ohne Windows/Tk-Fenster importierbar und der Import
hat keine Seiteneffekte (keine config.ini, kein Log, kein Dialog, kein Google-Client); erst init_runtime() (= main)
initialisiert. Windows-Module werden gestubbt (wie exe_ui_smoke.py). Aufruf: /usr/bin/python3 tests/offline/test_import.py"""
import importlib, os, pathlib, shutil, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import exe_stubs as S  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# Kopie der Quellen in einen leeren Ordner …/source_code → BASE_DIR = dieser leere Ordner (wie neben der EXE)
tmp = pathlib.Path(tempfile.mkdtemp(prefix="rks_import_"))
src = tmp / "source_code"
src.mkdir()
for f in (ROOT / "source_code").glob("*.py"):
    shutil.copy(f, src / f.name)
os.environ["APPDATA"] = str(tmp / "appdata")
mods, mb = S.stubs()
sys.modules.update(mods)
sys.modules["tkinter.messagebox"] = mb
import tkinter  # noqa: E402
tkinter.messagebox = mb
sys.path.insert(0, str(src))
vorher = sorted(p.name for p in tmp.iterdir())
dialoge_vorher = len(S.AUFZ.dialoge)
_out = sys.__stdout__
sys.__stdout__ = open(os.devnull, "w")
try:
    rks = importlib.import_module("RaKScribe")
finally:
    sys.__stdout__ = _out
check("import RaKScribe ohne Windows/Tk-Fenster", rks is not None and hasattr(rks, "main") and hasattr(rks, "RaKScribeApp"))
check("BASE_DIR = Ordner über source_code", rks.BASE_DIR == str(tmp))
check("Import schreibt nichts (keine config.ini, kein rakscribe.log)", sorted(p.name for p in tmp.iterdir()) == vorher,
      str(sorted(p.name for p in tmp.iterdir())))
check("Import zeigt keinen Dialog", len(S.AUFZ.dialoge) == dialoge_vorher)
check("Import startet keinen Google-Client und lädt nichts", rks.speech_client is None and rks.speech is None
      and rks.RADIOLOGY_TEMPLATES == {} and rks.INITIAL_PROMPT_CONTENT == "")

for f in ("templates.json", "radiology_prompt.txt", "misheard_words.json", "vorlagen_vorrang.json", "phrases.json"):
    shutil.copy(ROOT / f, tmp / f)  # wie die gebündelten Dateien
sys.__stdout__ = open(os.devnull, "w")
try:
    rks.init_runtime()
finally:
    sys.__stdout__ = _out
check("init_runtime(): config.ini angelegt, Log geschrieben", (tmp / "config.ini").exists() and (tmp / "rakscribe.log").exists())
check("init_runtime(): Vorlagen, Prompt, Fehlhör-Liste geladen", len(rks.RADIOLOGY_TEMPLATES) > 100
      and "RAKSCRIBE_PROMPT_VERSION" in rks.INITIAL_PROMPT_CONTENT and rks.MISHEARD_COMPILED)
check("init_runtime(): ohne Schlüssel kein Speech-Client, App gesperrt", rks.speech_client is None and not rks.keys_ready())
check("init_runtime(): gebündelte phrases.json ladbar (292 / 68)", rks._selbsttest_phrasen() == [292, 68], str(rks._selbsttest_phrasen()))
check("Vorlagen-Erkennung nach init_runtime", rks.detect_template("Vorfuß rechts in 2 Ebenen unauffällig") == "vorfuß_in_2_ebenen")

code = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("main() ruft init_runtime() vor dem Fenster", "def main():\n    init_runtime()" in code
      and 'if __name__ == "__main__":\n    main()' in code)

wf = (ROOT / ".github" / "workflows" / "build-exe.yml").read_text(encoding="utf-8")
module = sorted(p.stem for p in (ROOT / "source_code").glob("*.py") if p.stem != "RaKScribe")
fehlend = [m for m in module if f"--hidden-import={m}" not in wf]
check("build-exe.yml: --hidden-import für jedes Modul aus source_code", not fehlend, str(fehlend))

print("\n" + ("✅ IMPORT PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
