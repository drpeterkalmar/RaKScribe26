"""Gate (Umbau Schritt 23, Gutachten P2-14): rakscribe.log begrenzt (5 × 1 MB) und ohne Diktatinhalt — außer mit
RAKSCRIBE_DEBUG=1. Web-Konsole analog (nur Längen). Synthetische Diktate. Aufruf: /usr/bin/python3 tests/offline/test_logging.py"""
import os, pathlib, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import exe_stubs as S  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


os.environ.pop("RAKSCRIBE_DEBUG", None)
mod = S.lade_rakscribe(ruhig=False)
mod.keys_ready = lambda: True
tmp = pathlib.Path(tempfile.mkdtemp(prefix="rks_log_"))
_out = sys.__stdout__
sys.__stdout__ = open(os.devnull, "w")  # Konsolen-Spiegel der EXE stumm


def protokolliere(log_name):
    mod.LOG_FILE_PATH = str(tmp / log_name)
    DIKTAT = "Musterpatientin Erika Mustermann Knie rechts unauffällig"
    mod.apply_misheard("Wasser-Sip-Test bei Musterpatientin Erika Mustermann unauffällig")
    ctx = mod._pipeline_kontext()
    ctx.llm = lambda p: "## X\n\n## Befund\nBeschreibung mit ausreichend Länge für den Test.\n\n## Ergebnis\nGonarthrose."
    mod._pl.befund_aus_diktat(DIKTAT, ctx)
    mod._pl.befund_aus_diktat("Knie rechts Erika Mustermann mäßiggradige Gonarthrose", ctx)
    mod._pl.befund_aus_diktat("Kniegelenk links unauffällig", ctx)  # Normalbefund → [BYPASS]-Zeile
    for h in mod._prot.datei_logger(mod.LOG_FILE_PATH).handlers:
        h.flush()
    return (tmp / log_name).read_text(encoding="utf-8")


try:
    text = protokolliere("ohne_debug.log")
    check("ohne RAKSCRIBE_DEBUG: kein Diktattext im Log", "Mustermann" not in text and "Erika" not in text and "Wasser" not in text
          and "Kniegelenk links unauffällig" not in text, text[:500])
    check("… stattdessen Längen", "Zeichen>" in text and "[MISHEARD]" in text and "[BYPASS]" in text, text[:500])
    check("Log-Format wie bisher „[Zeit] Text“", text.startswith("[20") and "] [" in text.splitlines()[0])
    os.environ["RAKSCRIBE_DEBUG"] = "1"
    text = protokolliere("mit_debug.log")
    check("mit RAKSCRIBE_DEBUG=1: Diktattext im Log (Fehlersuche)", "Mustermann" in text, text[:300])
    os.environ.pop("RAKSCRIBE_DEBUG")

    # Rotation: > 6 MB schreiben → höchstens 5 Dateien, keine über 1 MB
    mod.LOG_FILE_PATH = str(tmp / "rotation" / "rakscribe.log")
    (tmp / "rotation").mkdir()
    zeile = "x" * 1000
    for _ in range(6500):
        mod.log(zeile)
    dateien = sorted((tmp / "rotation").iterdir())
    groessen = [d.stat().st_size for d in dateien]
    check("Rotation: höchstens 5 Dateien (rakscribe.log + .1 … .4)", len(dateien) == 5
          and {d.name for d in dateien} == {"rakscribe.log"} | {f"rakscribe.log.{i}" for i in range(1, 5)}, str([d.name for d in dateien]))
    check("Rotation: keine Datei über 1 MB", max(groessen) <= 1_000_000, str(groessen))

    # kaiscribe-frog-einsetzen-n1 (19.11.2026): rakscribe.log auf X: ist an anderen PCs offen → Umbenennen scheitert
    # (Windows). Früher schrieb ab 1 MB niemand mehr; jetzt wird weiter angehängt und später erneut rotiert.
    import logging
    P = mod._prot
    (tmp / "geteilt").mkdir()
    pfad = str(tmp / "geteilt" / "rakscribe.log")
    jetzt = [0.0]
    gesperrt = [True]

    def ersetzen(a, b):
        if gesperrt[0]:
            raise PermissionError(32, "Der Prozess kann nicht auf die Datei zugreifen", a)
        os.replace(a, b)

    h = P.TeilbareDatei(pfad, max_bytes=5000, anzahl=3, uhr=lambda: jetzt[0], ersetzen=ersetzen)
    h.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    lg = logging.getLogger("test-geteilt")
    lg.propagate = False
    lg.addHandler(h)
    lg.setLevel(logging.INFO)
    for i in range(200):
        lg.info(f"Zeile {i:03d} " + "y" * 40)
    inhalt = pathlib.Path(pfad).read_text(encoding="utf-8")
    check("geteilte Datei, Rotieren gesperrt: jede Zeile trotzdem geschrieben", all(f"Zeile {i:03d}" in inhalt for i in range(200))
          and not os.path.exists(pfad + ".1"), f"{len(inhalt)} Zeichen")
    check("… nur ein Rotationsversuch je 60 s (kein Dauerversuch je Zeile)", h.fehlversuche == 1, str(h.fehlversuche))
    gesperrt[0] = False
    jetzt[0] = 61.0
    lg.info("nach der Sperre")
    check("… nach 60 s frei: rotiert, neue Zeile in frischer Datei", os.path.exists(pfad + ".1")
          and pathlib.Path(pfad).read_text(encoding="utf-8").count("\n") == 1
          and "nach der Sperre" in pathlib.Path(pfad).read_text(encoding="utf-8"))
    for i in range(400):
        lg.info(f"weiter {i:03d} " + "z" * 40)
    namen = sorted(d.name for d in (tmp / "geteilt").iterdir())
    check("… danach wieder höchstens 3 Dateien (anzahl=3)", namen == ["rakscribe.log", "rakscribe.log.1", "rakscribe.log.2"], str(namen))
    lg.removeHandler(h)
    # zweiter Schreiber (anderer PC) hängt an dieselbe Datei: nichts geht verloren, die Datei bleibt nicht offen
    h2 = P.TeilbareDatei(pfad, max_bytes=10**6)
    lg.addHandler(h2)
    lg.info("von PC 2")
    os.replace(pfad, pfad + ".weg")   # klappt nur, weil kein Handler die Datei offen hält (unter Windows entscheidend)
    lg.info("nach Umbenennen")
    check("Datei nur je Eintrag offen: nach Umbenennen schreibt der Logger in die neue Datei",
          pathlib.Path(pfad).read_text(encoding="utf-8").strip().endswith("nach Umbenennen")
          and "von PC 2" in pathlib.Path(pfad + ".weg").read_text(encoding="utf-8"))
    lg.removeHandler(h2)
finally:
    sys.__stdout__ = _out

src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE schreibt nicht mehr direkt per open(..., 'a') ins Log", "open(LOG_FILE_PATH, 'a'" not in src)
web = "".join((ROOT / "web_app" / "src" / f).read_text(encoding="utf-8") for f in ("gemini.ts", "pipeline.ts", "stt.ts"))
check("Web-Konsole: Diktat nur über diktatLog (Länge)", "rawText.substring(0" not in web and "corrected.substring(0" not in web
      and "x.slice(0, 40)" not in web and "diktatLog(rawText)" in web)

print("\n" + ("✅ PROTOKOLL PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
