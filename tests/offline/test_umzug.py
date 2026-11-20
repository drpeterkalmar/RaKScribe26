"""Gate kaiscribe-umzug-n1-exe (Peter 20.11.2026: „bitte nenne mal alle rakscribe sachen in kaiscribe um“): Übergang
RaKScribe → KaiScribe ohne Bruch an den Befund-PCs (source_code/umzug.py + Start der EXE mit Attrappen).
- %APPDATA%\\RaKScribe wird beim Start EINMAL nach %APPDATA%\\KaiScribe kopiert (alt bleibt unverändert), Schlüssel heißt
  dort kaiscribe-praxis-key.json; gibt es den neuen Ordner schon, passiert nichts; scheitert die Kopie, bleibt kein halber
  Ordner und die EXE liest weiter den alten.
- X:\\KaiScribe\\… vor X:\\RaKScribe\\… (Lauf-Protokoll, Nutzungszähler), erst beim Schreiben aufgelöst.
- Prozessnamen: KaiScribe.exe + Übergang rakscribe26.exe, aber keine „KaiScribe-Bruecke.exe“.
Nur Dummy-Schlüssel. Aufruf: /usr/bin/python3 tests/offline/test_umzug.py"""
import json, os, pathlib, shutil, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "source_code"))
sys.path.insert(0, str(HERE))
import umzug  # noqa: E402
import nutzung  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


DUMMY = json.dumps({"vertex_api_key": "AQ.dummy-umzug", "stt": {"type": "service_account",
                                                                  "client_email": "dummy@example.invalid",
                                                                  "private_key": "-----DUMMY-----"}})


def altes_profil(basis, schluessel=DUMMY):
    alt = basis / "RaKScribe"
    (alt / "nutzung").mkdir(parents=True)
    (alt / "rakscribe-praxis-key.json").write_text(schluessel, encoding="utf-8")
    (alt / "einstellungen.json").write_text('{"nur_text": true}', encoding="utf-8")
    (alt / "gezeigte_hinweise.json").write_text("[]", encoding="utf-8")
    (alt / "warte_auf_x.vbs").write_bytes(b"\xff\xfe" + "' RaKScribe-Starter 2\r\n".encode("utf-16-le"))
    (alt / "nutzung" / "2026-11_PC.json").write_text("{}", encoding="utf-8")
    return alt


def inhalt(ordner):
    return {str(p.relative_to(ordner)): p.read_bytes() for p in sorted(ordner.rglob("*")) if p.is_file()}


# ── Benutzer-Daten ──
tmp = pathlib.Path(tempfile.mkdtemp(prefix="rks_umzug_"))
env = {"APPDATA": str(tmp)}
alt = altes_profil(tmp)
vorher = inhalt(alt)
neu, alt_pfad = umzug.benutzer_ordner(env)
check("Ordner: neu %APPDATA%\\KaiScribe, alt %APPDATA%\\RaKScribe", neu == str(tmp / "KaiScribe") and alt_pfad == str(alt))
check("vor dem Kopieren: aktiver Ordner = alt (Rückfall)", umzug.benutzer_ordner_aktiv(env) == str(alt))
logs = []
m = umzug.benutzer_daten_uebernehmen(env, log=logs.append)
n = pathlib.Path(neu)
check("Start: alt → neu kopiert, Meldung im Protokoll", m and "kopiert" in m and logs == [m] and n.is_dir(), str(m))
check("… alter Ordner unverändert (nicht verschoben, nichts gelöscht)", inhalt(alt) == vorher)
check("… Schlüssel heißt im neuen Ordner kaiscribe-praxis-key.json (Inhalt gleich), kein alter Name dort",
      (n / "kaiscribe-praxis-key.json").read_text(encoding="utf-8") == DUMMY
      and not (n / "rakscribe-praxis-key.json").exists())
check("… Einstellungen, Hinweis-Merker, Starter, Nutzungszähler mitkopiert",
      all((n / f).read_bytes() == (alt / f).read_bytes() for f in ("einstellungen.json", "gezeigte_hinweise.json",
                                                                    "warte_auf_x.vbs", "nutzung/2026-11_PC.json")))
check("… kein Zwischenordner liegen geblieben", sorted(p.name for p in tmp.iterdir()) == ["KaiScribe", "RaKScribe"])
check("… aktiver Ordner = neu", umzug.benutzer_ordner_aktiv(env) == neu)
(n / "einstellungen.json").write_text('{"nur_text": false}', encoding="utf-8")
check("zweiter Start: nichts mehr kopiert (neuer Stand bleibt, alter wird nicht mehr gelesen)",
      umzug.benutzer_daten_uebernehmen(env) is None and (n / "einstellungen.json").read_text() == '{"nur_text": false}')

tmp2 = pathlib.Path(tempfile.mkdtemp(prefix="rks_umzug2_"))
check("frischer PC (kein alter Ordner): nichts zu tun, kein Ordner angelegt",
      umzug.benutzer_daten_uebernehmen({"APPDATA": str(tmp2)}) is None and list(tmp2.iterdir()) == []
      and umzug.benutzer_ordner_aktiv({"APPDATA": str(tmp2)}) == str(tmp2 / "KaiScribe"))

tmp3 = pathlib.Path(tempfile.mkdtemp(prefix="rks_umzug3_"))
altes_profil(tmp3)
echt = shutil.copytree


def kaputt(*a, **k):
    echt(*a, **k)
    raise OSError(28, "Kein Speicherplatz")


shutil.copytree = kaputt
try:
    m = umzug.benutzer_daten_uebernehmen({"APPDATA": str(tmp3)})
finally:
    shutil.copytree = echt
check("Kopie scheitert → gemeldet, kein halber neuer Ordner, EXE liest weiter den alten",
      m and "nicht" in m and sorted(p.name for p in tmp3.iterdir()) == ["RaKScribe"]
      and umzug.benutzer_ordner_aktiv({"APPDATA": str(tmp3)}) == str(tmp3 / "RaKScribe"), str(m))

# ── X:-Pfade ──
ORDNER = set()


def da(pfad):   # Windows: Groß/klein egal
    return pfad.lower() in {o.lower() for o in ORDNER}
check("X: ohne beide Ordner (bzw. nicht verbunden) → Pfad unverändert",
      umzug.x_pfad("X:\\KaiScribe\\Daten\\laeufe", da) == "X:\\KaiScribe\\Daten\\laeufe")
ORDNER.add("X:\\RaKScribe")
check("nur X:\\RaKScribe da → Rückfall auf den alten Ordner (Standard und config.ini-Eintrag)",
      umzug.x_pfad("X:\\KaiScribe\\Daten\\laeufe", da) == "X:\\RaKScribe\\Daten\\laeufe"
      and umzug.x_pfad("X:\\RaKScribe\\Daten\\nutzung", da) == "X:\\RaKScribe\\Daten\\nutzung")
ORDNER.add("X:\\KaiScribe")
check("X:\\KaiScribe da → immer neu (auch für einen alten Eintrag in config.ini)",
      umzug.x_pfad("X:\\RaKScribe\\Daten\\laeufe", da) == "X:\\KaiScribe\\Daten\\laeufe"
      and umzug.x_pfad("x:\\rakscribe\\Daten", da) == "x:\\KaiScribe\\Daten"
      and umzug.x_pfad("X:\\RaKScribe", da) == "X:\\KaiScribe")
check("andere Pfade bleiben (IB-Lab-Ablage, Y:, Ordner mit ähnlichem Namen, aus)",
      umzug.x_pfad("X:\\IBL-Vorbefunde", da) == "X:\\IBL-Vorbefunde"
      and umzug.x_pfad("Y:\\Protokoll", da) == "Y:\\Protokoll"
      and umzug.x_pfad("X:\\RaKScribe-alt\\x", da) == "X:\\RaKScribe-alt\\x" and umzug.x_pfad("aus", da) == "aus"
      and umzug.x_pfad("", da) == "")

# ── Prozessnamen ──
check("Prozess: KaiScribe.exe, Kopien und Übergang rakscribe26 erkannt",
      all(umzug.ist_kaiscribe_prozess(x) for x in ("KaiScribe.exe", "kaiscribe.exe", "KaiScribe (1).exe",
                                                   "rakscribe26.exe", "rakscribe26 (1).exe")))
check("… Brücke/Formatierer/Python NICHT", not any(umzug.ist_kaiscribe_prozess(x) for x in (
    "KaiScribe-Bruecke.exe", "RaKScribe-Bruecke.exe", "KaiScribe-Formatierer.exe", "python.exe", "", None)))

# ── Nutzungszähler: Ordner erst beim Schreiben auflösen ──
z_ordner = [str(tmp / "zaehler_a")]
z = nutzung.Zaehler(lambda: z_ordner[0], pc="PC1")
z.ki({"rolle": "gen", "anbieter": "anthropic"})
z_ordner[0] = str(tmp / "zaehler_b")
z.ki({"rolle": "gen", "anbieter": "anthropic"})
check("Nutzungszähler mit Ordner-Funktion: schreibt jeweils in den aktuell aufgelösten Ordner",
      any((tmp / "zaehler_a").glob("*_PC1.json")) and any((tmp / "zaehler_b").glob("*_PC1.json"))
      and z.ordner == str(tmp / "zaehler_b"))

# ── EXE-Start (RaKScribe.py mit Attrappen): Kopie vor dem ersten Schlüssel-/Einstellungs-Zugriff ──
import exe_stubs as S  # noqa: E402
start = pathlib.Path(tempfile.mkdtemp(prefix="rks_umzug_exe_"))
altes_profil(start / "appdata", json.dumps({"vertex_api_key": "AQ.dummy-umzug"}))   # ohne STT-Teil (kein Google-Client)
alt_vorher = inhalt(start / "appdata" / "RaKScribe")
_mk = S.tempfile.mkdtemp
S.tempfile.mkdtemp = lambda prefix="": str(start)
try:
    rks = S.lade_rakscribe()
finally:
    S.tempfile.mkdtemp = _mk
NEU = start / "appdata" / "KaiScribe"
check("EXE-Start: %APPDATA%\\RaKScribe → KaiScribe kopiert, USER_KEY_DIR/USER_KEY_PATH zeigen auf neu",
      NEU.is_dir() and rks.USER_KEY_DIR == str(NEU) and rks.USER_KEY_PATH == str(NEU / "kaiscribe-praxis-key.json"),
      f"{rks.USER_KEY_DIR} {rks.USER_KEY_PATH}")
check("… geladen wird der kopierte Schlüssel (neuer Name, neuer Ordner); alter Ordner unverändert",
      rks._praxis_key_path() == str(NEU / "kaiscribe-praxis-key.json") and rks._load_vertex_key() == "AQ.dummy-umzug"
      and inhalt(start / "appdata" / "RaKScribe") == alt_vorher, str(rks._praxis_key_path()))
check("… Einstellungen kommen aus dem neuen Ordner", rks._einstellungen_pfad() == str(NEU / "einstellungen.json"))
src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
ir = src[src.index("def init_runtime():"):src.index("def _wav_argumente(")]
check("init_runtime(): erst kopieren, dann Benutzer-Pfade neu, dann config.ini/Schlüssel",
      -1 < ir.find("_umzug.benutzer_daten_uebernehmen(") < ir.find("USER_KEY_DIR, USER_KEY_PATH = _keys.user_key_paths()")
      < ir.find("_cfg.load_config(") < ir.find("init_google_speech()"))
check("Lauf-Protokoll und Nutzungszähler lösen X:\\KaiScribe/X:\\RaKScribe beim Schreiben auf",
      "_cas.lauf_schreiben(_umzug.x_pfad(ordner), daten)" in src
      and "_nutz.Zaehler(lambda: _umzug.x_pfad(_nutz.ordner_aus(CFG.lauf_ordner)))" in src)
wf = (ROOT / ".github" / "workflows" / "build-exe.yml").read_text(encoding="utf-8")
check("build-exe.yml bündelt umzug.py", "--hidden-import=umzug " in wf)

print(f"\n{'❌ ' + str(fails) + ' Fehler' if fails else '✅ alle grün'}")
sys.exit(1 if fails else 0)
