"""Gate v3.8.0 (SpeechMike, Peter 11.10.): Tastenberichte → Tasten, LED-Bytes, Belegung, Zustandstabelle und EOL-Prüfung
für die EXE (source_code/speechmike.py + jobstate.py) — gegen DIESELBEN Fälle wie die Web-App
(tests/offline/speechmike_faelle.txt, Web: web_app/speechmike_test.mjs, wird hier mit ausgeführt). Dazu der Lese-Thread
mit einem nachgebauten hidapi-Modul: geteilt öffnen, Tasten melden, LED schreiben, Abstecken/Anstecken, ohne Gerät,
ohne hidapi. Läuft ohne Windows und ohne Gerät.  Aufruf: /usr/bin/python3 tests/offline/test_speechmike.py"""
import json, pathlib, subprocess, sys, threading, time
HIER = pathlib.Path(__file__).resolve().parent
ROOT = HIER.parents[1]
sys.path.insert(0, str(ROOT / "source_code"))
import jobstate as js  # noqa: E402
import speechmike as sm  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    if not ok or "-v" in sys.argv:
        print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


F = json.loads((HIER / "speechmike_faelle.txt").read_text(encoding="utf-8"))
bytes_ = lambda h: [int(x, 16) for x in h.split()]  # noqa: E731

# 1. Dekodierung
for fall in F["dekodieren"]:
    d = sm.Dekodierer()
    for i, (zeit, hx, erwartet) in enumerate(fall["berichte"], 1):
        got = [list(e) for e in d.bericht(bytes_(hx), zeit)]
        check(f"dekodieren: {fall['name']} #{i}", got == erwartet, f"{hx} → {got} statt {erwartet}")

# 2. LED, LED je Zustand, Belegung, EOL-Prüfung
for name, hx in F["led"].items():
    check(f"LED {name}", sm.hex_bytes(sm.LED.get(name, [])) == hx, sm.hex_bytes(sm.LED.get(name, [])))
check("LED: keine zusätzlichen Zustände", set(sm.LED) == set(F["led"]))
for z, wartet, led in F["led_fuer"]:
    check(f"LED für {z}/{wartet}", sm.led_fuer(z, wartet) == led, sm.led_fuer(z, wartet))
for taste, ereignis in F["belegung"].items():
    check(f"Belegung {taste}", sm.BELEGUNG.get(taste) == ereignis, str(sm.BELEGUNG.get(taste)))
check("jede Taste steht in der Belegungstabelle", all(t in F["belegung"] for t, _ in sm.TASTEN))
for text, ok in F["sendefaehig"]:
    check(f"sendefähig: {text[:40]!r}", sm.sendefaehig(text) == ok)


# 3. Zustandstabelle = jobstate.vorschau (Web: lauf.ts uiAktion)
def job_in(zustand):
    j = js.JobState()
    weg = {"READY": [], "RECORDING": ["toggle"], "PAUSED": ["toggle", "record"], "PROCESSING": ["toggle", "toggle"],
           "ERROR": ["toggle", "toggle"]}
    for e in weg.get(zustand, []):
        j.ereignis(e)
    if zustand == "ERROR":
        j.ereignis("report_failed", j.gen)
    if zustand == "LOCKED":
        j.sperren()
    assert j.zustand == zustand, (zustand, j.zustand)
    return j


for z, e, aktion in F["zustand"]:
    check(f"Zustand {z} + {e}", job_in(z).vorschau(e) == aktion, f"{job_in(z).vorschau(e)} statt {aktion}")
check("Zustandstabelle vollständig (6 Zustände × 7 Bedien-Ereignisse)", len(F["zustand"]) == 42
      and {(z, e) for z, e, _ in F["zustand"]} == {(z, e) for z in ("READY", "RECORDING", "PAUSED", "PROCESSING", "ERROR",
                                                                     "LOCKED") for e in js.UI_EREIGNISSE})
# Übergänge (vorschau ändert nichts, ereignis schon)
j = job_in("READY")
check("record: bereit → Aufnahme (neue Generation)", j.ereignis("record") == "start" and j.zustand == js.RECORDING and j.gen == 1)
check("record: Aufnahme → Pause (gleiche Generation)", j.ereignis("record") == "pause" and j.zustand == js.PAUSED and j.gen == 1)
check("Streaming-Nachzügler in der Pause noch anzeigen", j.ereignis("stream_final", 1) == "anzeigen")
check("reparierter Abschnitt in der Pause anzeigen", j.ereignis("segment_fertig", 1) == "anzeigen")
check("record: Pause → weiter", j.ereignis("record") == "weiter" and j.zustand == js.RECORDING and j.gen == 1)
check("stop: Aufnahme → Pause", j.ereignis("stop") == "pause" and j.zustand == js.PAUSED)
check("eol in der Pause → nichts", j.ereignis("eol") is None and j.zustand == js.PAUSED)
check("ins in der Pause → Aufnahme beenden, Verarbeitung", j.ereignis("ins") == "stop" and j.zustand == js.PROCESSING and j.gen == 1)
check("ins/record/eol während der Verarbeitung → nichts", j.ereignis("ins") is None and j.ereignis("record") is None
      and j.ereignis("eol") is None and j.zustand == js.PROCESSING)
check("Lauf fertig → bereit", j.ereignis("report_done", 1) == "einfuegen" and j.zustand == js.READY)
check("eol in Ruhe → senden, neue Generation (alte Läufe ungültig)", j.ereignis("eol") == "senden" and j.zustand == js.READY
      and j.gen == 2 and not j.aktuell(1))
j = job_in("PAUSED")
check("F10 in der Pause → Stopp (Befund + Einfügen wie heute)", j.ereignis("toggle") == "stop" and j.zustand == js.PROCESSING)
j = job_in("PAUSED")
g = j.gen
check("F9/F1 in der Pause → Aufnahme verwerfen, bereit", j.ereignis("reset") == "stop_und_reset" and j.zustand == js.READY
      and not j.aktuell(g))
j = job_in("PAUSED")
check("Mikrofon-Fehler in der Pause → Fehler", j.ereignis("capture_failed", j.gen) == "fehler" and j.zustand == js.ERROR)
j = job_in("READY")
check("ins in Ruhe → Befund aus dem Diktat-Feld (text_start)", j.ereignis("ins") == "text_start" and j.zustand == js.PROCESSING
      and j.text_fix)


# 4. Lese-Thread mit nachgebautem hidapi
class FakeDev:
    def __init__(self, hid):
        self.hid, self.offen, self.geschrieben = hid, False, []

    def open_path(self, p):
        if self.hid.exklusiv:
            raise OSError("open failed")
        self.offen, self.pfad = True, p
        self.hid.oeffnungen += 1

    def read(self, n, timeout_ms=0):
        if not self.hid.angesteckt:
            raise OSError("read error")
        if self.hid.berichte:
            return self.hid.berichte.pop(0)
        time.sleep(timeout_ms / 1000)
        return []

    def write(self, daten):
        if self.hid.write_fehler:
            raise OSError("write error")
        self.geschrieben.append(list(daten))
        self.hid.geschrieben.append(list(daten))
        return len(daten)

    def close(self):
        self.offen = False


class FakeHid:
    def __init__(self):
        self.angesteckt, self.exklusiv, self.write_fehler = True, False, False
        self.berichte, self.geschrieben, self.oeffnungen = [], [], 0
        self.geraete = [
            {"vendor_id": 0x0911, "product_id": 0x0C1C, "usage_page": 0x000C, "usage": 1, "path": b"consumer",
             "product_string": "SpeechMike Premium"},
            {"vendor_id": 0x0911, "product_id": 0x0C1C, "usage_page": 0xFFA0, "usage": 1, "path": b"vendor",
             "product_string": "SpeechMike Premium"},
            {"vendor_id": 0x046D, "product_id": 0xC52B, "usage_page": 0xFFA0, "usage": 1, "path": b"fremd"},
        ]

    def enumerate(self, vid=0, pid=0):
        return [d for d in self.geraete if self.angesteckt and (not vid or d["vendor_id"] == vid)]

    def device(self):
        return FakeDev(self)


def warte(bed, timeout=3.0):
    t0 = time.time()
    while time.time() - t0 < timeout and not bed():
        time.sleep(0.01)
    return bed()


hid = FakeHid()
tasten, status, logs = [], [], []
leser = sm.SpeechMikeLeser(on_taste=lambda t, g, roh: tasten.append((t, g, roh)), log=logs.append,
                           on_verbindung=status.append, hid_modul=hid, scan_s=0.05)
leser.starten()
check("Lese-Thread: SpeechMike (Usage-Page 0xFFA0) gefunden und geöffnet", warte(lambda: leser.verbunden)
      and leser.verbunden == "SpeechMike Premium (0911:0c1c)" and status[-1] == leser.verbunden, str(status))
check("… die Vendor-Schnittstelle, nicht Consumer/fremde Geräte", hid.oeffnungen == 1
      and any("Verbunden" in z for z in logs))
check("… LED-Zustand nach dem Verbinden gesendet (aus, mit Report-ID 0)",
      warte(lambda: hid.geschrieben) and hid.geschrieben[0] == [0] + bytes_(F["led"]["aus"]), str(hid.geschrieben))
hid.berichte += [bytes_("80 00 00 00 00 00 00 00 01"), bytes_("80 00 00 00 00 00 00 00 00")]
check("Tastenbericht → on_taste(RECORD gedrückt/losgelassen, raw)", warte(lambda: len(tasten) == 2)
      and tasten == [("RECORD", True, "80 00 00 00 00 00 00 00 01"), ("RECORD", False, "80 00 00 00 00 00 00 00 00")],
      str(tasten))
check("Protokollzeile [SPEECHMIKE] Taste RECORD gedrückt (raw …)",
      any(z == "[SPEECHMIKE] Taste RECORD gedrückt (raw 80 00 00 00 00 00 00 00 01)" for z in logs), str(logs[-3:]))
check("Diagnose-Verlauf füllt sich", len(leser.verlauf) == 2 and "RECORD gedrückt" in leser.verlauf[0])
leser.led("aufnahme")
check("LED Aufnahme geschrieben", warte(lambda: hid.geschrieben[-1] == [0] + bytes_(F["led"]["aufnahme"])), str(hid.geschrieben[-1]))
hid.write_fehler = True
leser.led("pause")
check("LED-Fehler: nur eine Protokollzeile, Tasten gehen weiter", warte(lambda: any("LED nicht gesetzt" in z for z in logs)))
hid.berichte.append(bytes_("80 00 00 00 00 00 00 00 40"))
check("… INS kommt trotzdem an", warte(lambda: tasten[-1][0] == "INS"))
hid.write_fehler = False
hid.angesteckt = False
check("Abstecken → getrennt gemeldet", warte(lambda: leser.verbunden is None and status[-1] is None), str(status))
hid.angesteckt = True
hid.berichte.clear()
check("Wieder anstecken → wieder verbunden", warte(lambda: leser.verbunden is not None) and hid.oeffnungen == 2)
check("… aktueller LED-Zustand erneut gesendet (pause)", warte(lambda: hid.geschrieben[-1] == [0] + bytes_(F["led"]["pause"])),
      str(hid.geschrieben[-1]))
tasten.clear()
hid.berichte += [bytes_("80 00 00 00 00 00 00 00 20")]
check("… Tasten nach dem Wiederverbinden (EOL)", warte(lambda: tasten and tasten[-1][:2] == ("EOL", True)), str(tasten))
leser.beenden()
check("beenden → LED aus, Thread endet", hid.geschrieben[-1] == [0] + bytes_(F["led"]["aus"]) and not leser._thread.is_alive())


class Kaputt:
    def on_taste(self, *a):
        raise RuntimeError("Oberfläche kaputt")


hid2 = FakeHid()
logs2 = []
l2 = sm.SpeechMikeLeser(on_taste=Kaputt().on_taste, log=logs2.append, hid_modul=hid2, scan_s=0.05)
l2.einspeisen(bytes_("80 00 00 00 00 00 00 00 01"), 0)
check("Fehler in der Oberfläche beendet den Leser nicht (nur Protokoll)", any("Fehler bei Taste RECORD" in z for z in logs2))

hid3 = FakeHid()
hid3.angesteckt = False
logs3 = []
l3 = sm.SpeechMikeLeser(on_taste=lambda *a: None, log=logs3.append, hid_modul=hid3, scan_s=0.02)
l3.starten()
time.sleep(0.2)
check("ohne Gerät: EINE Protokollzeile, keine Ausnahme, sucht weiter", sum("Kein SpeechMike" in z for z in logs3) == 1
      and l3._thread.is_alive())
hid3.angesteckt, hid3.exklusiv = True, True
check("Gerät exklusiv belegt → verständliche Protokollzeile", warte(lambda: any("exklusiv" in z for z in logs3)))
l3.beenden()


class OhneHid(sm.SpeechMikeLeser):
    def _lauf(self):
        import builtins
        orig = builtins.__import__

        def imp(name, *a, **k):
            if name == "hid":
                raise ImportError("No module named 'hid'")
            return orig(name, *a, **k)
        builtins.__import__ = imp
        try:
            super()._lauf()
        finally:
            builtins.__import__ = orig


logs4 = []
l4 = OhneHid(on_taste=lambda *a: None, log=logs4.append)
l4.starten()
l4._thread.join(2)
check("ohne hidapi: Protokollzeile, Thread endet still, F10/F9 unberührt",
      not l4._thread.is_alive() and any("hidapi nicht verfügbar" in z for z in logs4), str(logs4))

# 5. Verdrahtung in der EXE (die EXE selbst läuft nur unter Windows)
src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("RaKScribe startet den SpeechMike-Leser", "_sm.SpeechMikeLeser(" in src and ".starten()" in src)
check("Tasten laufen über after(0) in die Oberfläche", "self.after(0, self.speechmike_taste" in src)
check("zentrale Funktion befund_fertig() für EOL", "def befund_fertig(self" in src)
wf = (ROOT / ".github" / "workflows" / "build-exe.yml").read_text(encoding="utf-8")
check("build-exe.yml bündelt hidapi (--hidden-import=hid)", "--hidden-import=hid " in wf)
req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
check("requirements.txt: hidapi mit fester Version", any(z.startswith("hidapi==") for z in req.splitlines()))

# 6. Dieselben Fälle durch die Web-App (TypeScript)
ts = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", "speechmike_test.mjs"], cwd=ROOT / "web_app",
                    capture_output=True, text=True, timeout=120)
print("[TS]", (ts.stdout.strip().splitlines() or ["(keine Ausgabe)"])[-1])
if ts.returncode != 0:
    print(ts.stdout, ts.stderr)
    fails += 1

print("\n" + ("✅ SPEECHMIKE PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
