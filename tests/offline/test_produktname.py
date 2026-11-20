"""Gate v3.17.0 (Peter 22.10.2026: „RaKScribe ist ein furchtbarer Name“ → KaiScribe): Alles, was ein Benutzer sieht,
heißt KaiScribe. Umzugs-Job kaiscribe-umzug-n1-exe (Peter 20.11.2026): auch technisch KaiScribe — KaiScribe.exe (Release
zusätzlich rakscribe26.exe als Übergang), %APPDATA%\\KaiScribe, kaiscribe-praxis-key.json, KaiScribe.lnk, X:\\KaiScribe vor
X:\\RaKScribe. Erlaubt bleiben nur Rückfall-Namen und bewusst gelassene Protokoll-Namen (Repo/Pages-Pfad RaKScribe26,
Mutex, %LOCALAPPDATA%\\RaKScribe als Austausch mit der Brücke, Testbefund-Kopf der Brücke, RAKSCRIBE_*-Variablen,
Modul-/Klassennamen).
Teil 1: feste Anzeigestellen (EXE-Titel/Kopf/Dialoge, Web-Titel/Kopf/Sperre, Release-Titel) + Umzugs-Namen.
Teil 2: kein weiterer Text in EXE-Code/App.tsx mit „RaKScribe“ außer den erlaubten Stellen.
Aufruf: /usr/bin/python3 tests/offline/test_produktname.py"""
import io, pathlib, re, sys, tokenize
ROOT = pathlib.Path(__file__).resolve().parents[1].parent

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


exe = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
bs = (ROOT / "source_code" / "bereitschaft.py").read_text(encoding="utf-8")
app = (ROOT / "web_app" / "src" / "App.tsx").read_text(encoding="utf-8")
html = (ROOT / "web_app" / "index.html").read_text(encoding="utf-8")
wf = (ROOT / ".github" / "workflows" / "build-exe.yml").read_text(encoding="utf-8")

# ── Teil 1: feste Anzeigestellen ──
check("EXE-Fenstertitel „KaiScribe <Version> – Röntgen am Kai“",
      'self.title(f"KaiScribe {app_version()} – Röntgen am Kai")' in exe)
check("EXE-Kopfzeile „KaiScribe“", 'ctk.CTkLabel(names, text="KaiScribe",' in exe)
check("EXE-Sperre und Schlüssel-Dialog sagen KaiScribe",
      '"KaiScribe ist gesperrt, bis der Schlüssel geladen ist.' in exe and "KaiScribe ist bereit." in exe)
check("EXE-Hinweis „läuft schon“ sagt KaiScribe", 'f"KaiScribe {app_version()} läuft schon' in exe)
check("Autostart-Texte sagen KaiScribe", 'BESCHREIBUNG = "KaiScribe wartet minimiert' in bs
      and "wartet KaiScribe minimiert" in bs and "KaiScribe startet nicht mehr mit Windows" in bs)
check("Web-Seitentitel + App-Name KaiScribe", "<title>KaiScribe __RAKSCRIBE_VERSION__" in html
      and 'name="application-name" content="KaiScribe"' in html and 'apple-mobile-web-app-title" content="KaiScribe"' in html)
check("Web-Kopfzeile + Sperre KaiScribe", '<span className="brand-name">KaiScribe</span>' in app
      and "KaiScribe ist gesperrt, bis der Schlüssel geladen ist." in app)
check("Release-Titel „KaiScribe <Tag>“", "name: KaiScribe ${{ steps.version.outputs.tag }}" in wf)

# ── kaiscribe-umzug-n1-exe: technisch KaiScribe, mit Übergang ──
keys = (ROOT / "source_code" / "keys.py").read_text(encoding="utf-8")
umz = (ROOT / "source_code" / "umzug.py").read_text(encoding="utf-8")
check("EXE heißt KaiScribe.exe; Release liefert zusätzlich rakscribe26.exe (identisch)", "--name=KaiScribe " in wf
      and "cp source_code/dist/KaiScribe.exe release/rakscribe26.exe" in wf and "--icon=../kaiscribe.ico" in wf)
check("Download-Link der Web-App: releases/latest/download/KaiScribe.exe",
      "https://github.com/drpeterkalmar/RaKScribe26/releases/latest/download/KaiScribe.exe" in app)
check("Benutzer-Ordner/Schlüssel/Verknüpfung neu, alt nur als Rückfall",
      'NAME = "KaiScribe"' in umz and 'ALT = "RaKScribe"' in umz
      and 'PRAXIS_KEY_NAME = "kaiscribe-praxis-key.json"' in keys and 'ALT_KEY_NAME = "rakscribe-praxis-key.json"' in keys
      and 'VERKNUEPFUNG = "KaiScribe.lnk"' in bs and 'ALT_VERKNUEPFUNG = "RaKScribe.lnk"' in bs
      and 'STARTER_KENNUNG = "KaiScribe-Starter 3"' in bs)
# ── bewusst NICHT umbenannt (sonst brechen alte/neue EXE nebeneinander bzw. die Brücken je PC) ──
check("Mutex und %LOCALAPPDATA%\\RaKScribe (Austausch mit der Brücke) bleiben",
      'MUTEX = "Local\\\\RaKScribe26-Einzelinstanz"' in bs
      and 'return os.path.join(basis, "RaKScribe")' in (ROOT / "source_code" / "cas_auftrag.py").read_text(encoding="utf-8"))

# ── Teil 2: übrige Texte ──
# Erlaubt (kaiscribe-umzug-n1-exe, nur noch Rückfall-/Protokoll-Namen): Repo/Pages-Pfad + Mutex „RaKScribe26“, alte
# Verknüpfung „RaKScribe.lnk“ (wird ersetzt), Ordnername "RaKScribe" (umzug.ALT, %LOCALAPPDATA%-Austausch mit der Brücke),
# Testbefund der Brücke („TEST RaKScribe-Brücke“, steht wortgleich in ris-mods/bruecke).
ERLAUBT = re.compile(r"RaKScribe26|^[\"']RaKScribe\.lnk[\"']$|^[\"']RaKScribe[\"']$|TEST RaKScribe-Brücke|"
                     r"Übergabe von RaKScribe an CAS")


def texte(pfad):
    """Text-Konstanten mit „RaKScribe“ (ohne Docstrings und Kommentare) → [(Zeile, Text)]."""
    quelle = pfad.read_text(encoding="utf-8")
    toks = list(tokenize.generate_tokens(io.StringIO(quelle).readline))
    arten = {tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", -1)}
    raus = []
    for i, t in enumerate(toks):
        if t.type not in arten or "RaKScribe" not in t.string:
            continue
        vor = [x for x in toks[:i] if x.type not in (tokenize.NL, tokenize.COMMENT)][-1:]
        if t.string.startswith(('"""', "'''")) and (not vor or vor[0].type in (tokenize.NEWLINE, tokenize.INDENT,
                                                                             tokenize.DEDENT, tokenize.ENCODING)):
            continue                                       # Docstring
        raus.append((t.start[0], t.string))
    return raus


uebrig = []
for f in sorted((ROOT / "source_code").glob("*.py")):
    for zeile, s in texte(f):
        if not ERLAUBT.search(s):
            uebrig.append(f"{f.name}:{zeile}: {s[:90]}")
for nr, z in enumerate(app.splitlines(), 1):
    code = z.split("//")[0] if "://" not in z else z   # TS-Kommentar abschneiden (URLs bleiben ganz)
    if "RaKScribe" in code and not z.lstrip().startswith(("//", "/*", "*", "{/*")) and not ERLAUBT.search(code):
        uebrig.append(f"App.tsx:{nr}: {z.strip()[:90]}")
check("kein weiterer sichtbarer Text mit „RaKScribe“ (EXE-Code + App.tsx)", not uebrig, "\n   " + "\n   ".join(uebrig))

print(f"\n{'❌ ' + str(fails) + ' rot' if fails else '✅ alle grün'}")
sys.exit(1 if fails else 0)
