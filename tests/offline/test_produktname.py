"""Gate v3.17.0 (Peter 22.10.2026: „RaKScribe ist ein furchtbarer Name“ → KaiScribe): Alles, was ein Benutzer sieht,
heißt KaiScribe. Technische Namen bleiben bis zu einem eigenen Umzugs-Job (rakscribe26.exe, Repo/Pages-Pfad RaKScribe26,
X:\\RaKScribe, %APPDATA%\\RaKScribe, rakscribe-praxis-key.json, Drive-Ordner „RaKScribe“, RaKScribe.lnk, Mutex, Brücke,
Protokoll-Zeilen, Modul-/Klassennamen) — Einspiel-Wächter, Brücke und Download-Links hängen an ihnen.
Teil 1: feste Anzeigestellen (EXE-Titel/Kopf/Dialoge, Web-Titel/Kopf/Sperre, Release-Titel).
Teil 2: kein weiterer Text in EXE-Code/App.tsx mit „RaKScribe“ außer den erlaubten technischen Stellen.
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

# ── NICHT umbenannt (sonst brechen Einspielen, Brücke, Downloads) ──
check("EXE-Dateiname bleibt rakscribe26", "--name=rakscribe26 " in wf)
check("Download-Link bleibt releases/latest/download/rakscribe26.exe",
      "https://github.com/drpeterkalmar/RaKScribe26/releases/latest/download/rakscribe26.exe" in app)
check("Ordner/Schlüssel/Verknüpfung/Mutex bleiben", 'VERKNUEPFUNG = "RaKScribe.lnk"' in bs
      and 'MUTEX = "Local\\\\RaKScribe26-Einzelinstanz"' in bs and 'PROZESS_PRAEFIX = "rakscribe26"' in bs
      and "'RaKScribe')" in (ROOT / "source_code" / "keys.py").read_text(encoding="utf-8")
      and 'return os.path.join(basis, "RaKScribe")' in (ROOT / "source_code" / "cas_auftrag.py").read_text(encoding="utf-8"))

# ── Teil 2: übrige Texte ──
# Erlaubt: Pfade/Dateien/Ordner, Protokollzeilen („[…]“, „---“), VBS-Starter (eigene Kennung, Benutzer sieht ihn nicht),
# Testbefund der Brücke (heißt „RaKScribe-Brücke“, ris-mods), WAV-Ablauf-Protokoll.
ERLAUBT = re.compile(r"Drive-Ordner „?RaKScribe|RaKScribe26|RaKScribe\.lnk|RaKScribe-Starter|RaKScribe-Brücke|"
                     r"RaKScribeLaeuft|^f?[\"']?\[|^f?[\"']?---|^f?[\"']'|Notiz \"RaKScribe|"
                     r"^[\"']RaKScribe[\"']$|s – RaKScribe wird geschlossen|von RaKScribe an CAS|angelegt von RaKScribe \(Menü")


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
