"""Gate (kaiscribe-privat-n1, 05.11.2026): EXE-Bau am Büro-PC (tools/buero/kaiscribe_bauen.py) baut mit GENAU den
PyInstaller-Argumenten aus build-exe.yml, der Peer-Auftrag hat alle Platzhalter, und nichts unter tools/buero holt
anonym von GitHub (das Repo wird privat).
Aufruf: /usr/bin/python3 tests/offline/test_buero_bau.py"""
import importlib.util, pathlib, re, shlex, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


sp = importlib.util.spec_from_file_location("kaiscribe_bauen", ROOT / "tools" / "buero" / "kaiscribe_bauen.py")
B = importlib.util.module_from_spec(sp)
sp.loader.exec_module(B)

wf = (ROOT / ".github" / "workflows" / "build-exe.yml").read_text(encoding="utf-8")
args = B.pyinstaller_args(wf)
zeile = next(z.strip() for z in wf.splitlines() if z.strip().startswith("pyinstaller --onefile"))
check("Argumente = Workflow-Zeile ohne 'pyinstaller'", args == shlex.split(zeile)[1:])
check("Name rakscribe26, eine Datei, ohne Konsole", "--name=rakscribe26" in args and "--onefile" in args
      and "--noconsole" in args)
check("Icon und Einstieg RaKScribe.py", "--icon=../rakscribe.ico" in args and args[-1] == "RaKScribe.py")
daten = [args[i + 1] for i, x in enumerate(args) if x == "--add-data"]
for d in ("../VERSION;.", "../templates.json;.", "../misheard_words.json;.", "../radiology_prompt.txt;.",
          "../masken.json;.", "../ordi_bausteine.json;.", "../phrases.json;.", "../vorlagen_vorrang.json;."):
    check(f"bündelt {d.split(';')[0]}", d in daten, str(daten))
imports = {x.split("=", 1)[1] for x in args if x.startswith("--hidden-import=")}
module = {p.stem for p in (ROOT / "source_code").glob("*.py") if p.stem != "RaKScribe"}
check("jedes EXE-Modul als hidden-import", module <= imports, str(sorted(module - imports)))
try:
    B.pyinstaller_args("steps:\n  - run: echo\n")
    check("ohne pyinstaller-Zeile → Fehler", False)
except ValueError:
    check("ohne pyinstaller-Zeile → Fehler", True)

check("UI-Test zählen", B.ui_zaehlen("PASS [A] a\nFAIL [B] b\nx PASS\nPASS [C] c\n") == (2, 3))
check("Autostart-Pfad = RaKScribe.lnk (Name wie bereitschaft.VERKNUEPFUNG)", B.autostart_lnk().name == "RaKScribe.lnk"
      and 'VERKNUEPFUNG = "RaKScribe.lnk"' in (ROOT / "source_code" / "bereitschaft.py").read_text(encoding="utf-8"))

auf = (ROOT / "tools" / "buero" / "auftrag_exe_bauen.txt").read_text(encoding="utf-8")
platz = set(re.findall(r"\{([A-Z_]+)\}", auf))
check("Auftrag: Platzhalter vollständig", platz == {"COMMIT", "KURZ", "SHA_ZIP", "SHA_SKRIPT", "TAG", "PFAD", "UI"}, str(platz))
check("Auftrag ruft kaiscribe_bauen.py mit Abgabe", "tools\\buero\\kaiscribe_bauen.py" in auf and "--abgabe" in auf
      and "/kaiscribe/ablage" in auf)
check("Auftrag: letzte Zeile KSBAU=", "KSBAU=<fehler|belegt> COMMIT={COMMIT} TAG={TAG}" in auf)

anonym = re.compile(r"raw\.githubusercontent\.com|github\.com/drpeterkalmar|api\.github\.com|github\.io")
for p in sorted((ROOT / "tools" / "buero").iterdir()):
    if p.suffix in (".py", ".txt", ".ps1", ".cmd"):
        check(f"{p.name}: kein anonymer GitHub-Abruf", not anonym.search(p.read_text(encoding="utf-8")))

print("\n" + ("✅ BÜRO-BAU PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
