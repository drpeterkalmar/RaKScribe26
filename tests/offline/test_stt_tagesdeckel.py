"""Gate kaiscribe-stt-tagesdeckel-n1 (Peter 24.11.2026): harter Tagesdeckel für die Google-Spracherkennung in KaiScribe.
Zähler je PC (+ Kürzel), Tageswechsel 00:00 Wien, atomar geschrieben; STT_TAGESDECKEL_MIN (Standard 240); Schleifenbremse
(dieselbe Aufnahme > 3× in 10 min); Grenze erreicht → kein Google-Aufruf, Audio als WAV gesichert, rote Zeile; ab 80 %
Log-Zeile + Tagesbericht-Zeile → Chirp-Warnung legt eine Karte für Hermes an. Gilt für kp und rg.
Keine echten Google-Aufrufe (Attrappen), keine Patientendaten.
Aufruf: python tests/offline/test_stt_tagesdeckel.py"""
import datetime
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import threading

import numpy as np

HIER = pathlib.Path(__file__).resolve().parent
ROOT = HIER.parents[1]
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(ROOT / "source_code"))
import stt_deckel as dk  # noqa: E402
import stt  # noqa: E402
import aufnahme as af  # noqa: E402
import config as cfgmod  # noqa: E402
import nutzung  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


TMP = tempfile.mkdtemp(prefix="rks_deckel_")
WIEN = dk._WIEN


class Uhr:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


# ── 1. Zähler, Datei, Kürzel ──────────────────────────────────────────────────────────────────────────────────────
jetzt = Uhr(datetime.datetime(2026, 11, 24, 10, 0, tzinfo=WIEN))
logs, meldungen = [], []
o1 = os.path.join(TMP, "a")
d = dk.Deckel(o1, pc="CASWS10", limit_min=10, jetzt=jetzt, log=logs.append, melden=lambda a, i: meldungen.append((a, i)))
d.kuerzel = "kp"
d.buchen(60)
d.buchen(30, "streaming")
d.kuerzel = "rg"
d.buchen(90)
datei = os.path.join(o1, "stt_tagesdeckel_CASWS10.json")
inhalt = json.load(open(datei, encoding="utf-8"))
check("Zähler: Datei je PC im Datenordner, Sekunden aller Aufrufe (chirp + Live)", inhalt["s"] == 180.0
      and inhalt["tag"] == "2026-11-24" and inhalt["art"] == {"chirp": 150.0, "streaming": 30.0}, str(inhalt))
check("… je Kürzel (kp/rg) mitgezählt", inhalt["kuerzel"] == {"kp": 90.0, "rg": 90.0}, str(inhalt["kuerzel"]))
check("… atomar geschrieben (kein .tmp übrig), nur Zahlen", os.listdir(o1) == ["stt_tagesdeckel_CASWS10.json"]
      and set(inhalt) <= {"pc", "tag", "s", "art", "kuerzel", "warn80", "grenze", "schleife"}, str(os.listdir(o1)))
d2 = dk.Deckel(o1, pc="CASWS10", limit_min=10, jetzt=jetzt)
check("… Neustart von KaiScribe am selben Tag: Zähler läuft weiter (aus der Datei)", d2.verbraucht_s() == 180.0)
check("… anderer PC: eigene Datei, eigener Zähler", dk.Deckel(o1, pc="CASWS08", jetzt=jetzt).verbraucht_s() == 0.0)

# ── 2. Tageswechsel 00:00 Europe/Vienna ─────────────────────────────────────────────────────────────────────────────
jetzt.t = datetime.datetime(2026, 11, 24, 23, 59, tzinfo=WIEN)
check("Tageswechsel: 23:59 Wien noch derselbe Tag", d.verbraucht_s() == 180.0)
jetzt.t = datetime.datetime(2026, 11, 24, 23, 0, tzinfo=datetime.timezone.utc).astimezone(WIEN)   # = 00:00 Wien
check("… 23:00 UTC = 00:00 Wien → neuer Tag, Zähler 0", d.verbraucht_s() == 0.0, str(jetzt.t))
d.buchen(12)
inhalt = json.load(open(datei, encoding="utf-8"))
check("… Datei beginnt den neuen Tag (gestern überschrieben)", inhalt["tag"] == "2026-11-25" and inhalt["s"] == 12.0, str(inhalt))
check("… wien_jetzt() rechnet in Europe/Vienna", dk.wien_jetzt().utcoffset() in (datetime.timedelta(hours=1),
                                                                                  datetime.timedelta(hours=2)))
check("Config-Standard 240 min (Dataclass + Deckel)", cfgmod.Config().stt_tagesdeckel_min == 240
      and dk.Deckel(o1).limit_min == 240 and dk.Deckel(o1, limit_min=0).limit_min == 240)

# ── 3. Datei kaputt / Ordner fehlt → Deckel zählt trotzdem ─────────────────────────────────────────────────────────
o2 = os.path.join(TMP, "kaputt")
os.makedirs(o2)
open(os.path.join(o2, "stt_tagesdeckel_PC1.json"), "w").write("{kaputt")
d3 = dk.Deckel(o2, pc="PC1", limit_min=1, jetzt=jetzt)
check("kaputte Datei → 0, kein Absturz", d3.verbraucht_s() == 0.0)
d4 = dk.Deckel(lambda: None, pc="PC1", limit_min=1, jetzt=jetzt)
d4.buchen(61)
check("ohne Ordner (Funktion → None): zählt im Speicher, Grenze greift trotzdem", d4.erreicht() and d4.vorher() == "grenze")
d5 = dk.Deckel(lambda: 1 / 0, pc="PC1", limit_min=1, jetzt=jetzt)
d5.buchen(61)
check("Ordner-Funktion wirft → zählt im Speicher", d5.erreicht())

# ── 4. 80 %-Warnung und Grenze ─────────────────────────────────────────────────────────────────────────────────────
jetzt.t = datetime.datetime(2026, 11, 26, 9, 0, tzinfo=WIEN)
logs.clear(); meldungen.clear()
d.limit_min = 10            # 600 s
d.buchen(470)
check("unter 80 %: keine Warnung", not logs and not meldungen, str(logs))
d.buchen(10)                # 480 s = 80 %
d.buchen(10)
check("ab 80 %: genau EINE Log-Zeile „[STT-DECKEL] WARNUNG“ + Meldung warn80",
      sum("[STT-DECKEL] WARNUNG" in l for l in logs) == 1 and [m[0] for m in meldungen] == ["warn80"]
      and meldungen[0][1] == {"min": 8.0, "limit_min": 10}, f"{logs} {meldungen}")
check("… unter der Grenze weiter erlaubt", d.vorher() is None and d.vorher(np.zeros(5, dtype=np.int16)) is None)
d.buchen(110)               # 600 s
check("Grenze erreicht: vorher() → „grenze“, einmal Log + Meldung „grenze“", d.vorher() == "grenze"
      and d.vorher(np.ones(5, dtype=np.int16)) == "grenze" and sum("Tagesgrenze erreicht" in l for l in logs) == 1
      and [m[0] for m in meldungen] == ["warn80", "grenze"], f"{logs} {meldungen}")
jetzt.t = datetime.datetime(2026, 11, 27, 0, 0, 1, tzinfo=WIEN)
check("… nächster Tag 00:00 Wien: wieder frei", d.vorher() is None and not d.erreicht())

# ── 5. Schleifenbremse ─────────────────────────────────────────────────────────────────────────────────────────────
uhr = Uhr(1000.0)
logs.clear(); meldungen.clear()
d6 = dk.Deckel(os.path.join(TMP, "s"), pc="PC1", jetzt=jetzt, uhr=uhr, log=logs.append,
               melden=lambda a, i: meldungen.append(a))
A = np.arange(16000, dtype=np.int16)
B = A.copy(); B[0] = 7
erg = []
for i in range(5):
    uhr.t += 60
    erg.append(d6.vorher(A))
check("Schleifenbremse: dieselbe Aufnahme 3× erlaubt, ab dem 4. Mal in 10 min gestoppt",
      erg == [None, None, None, "schleife", "schleife"], str(erg))
check("… Log-Zeile + Meldung „schleife“ (einmal)", sum("Schleifenbremse" in l for l in logs) == 1
      and meldungen == ["schleife"], f"{logs} {meldungen}")
check("… andere Aufnahme bleibt erlaubt", d6.vorher(B) is None)
uhr.t += 3600
check("… gesperrte Aufnahme bleibt gesperrt (auch nach 10 min)", d6.vorher(A) == "schleife" and d6.gesperrt_aufnahme(A))
C = A.copy(); C[1] = 9
erg = []
for _ in range(6):
    uhr.t += 301           # alle 5 min: nie mehr als 2 im 10-min-Fenster
    erg.append(d6.vorher(C))
check("… dieselbe Aufnahme, aber nur alle 5 min → nie gestoppt (gleitendes 10-min-Fenster)", erg == [None] * 6, str(erg))

# ── 6. stt.chirp3_worker mit Deckel (Attrappe statt Google) ─────────────────────────────────────────────────────────
REQ = []


def req(token, loc, b64, **kw):
    REQ.append(len(b64))
    return "Text"


jetzt.t = datetime.datetime(2026, 11, 28, 8, 0, tzinfo=WIEN)
d7 = dk.Deckel(os.path.join(TMP, "w"), pc="PC1", limit_min=2, jetzt=jetzt, uhr=uhr)
stt.DECKEL = d7
try:
    pcm = np.arange(16000 * 30, dtype=np.int16)          # 30 s
    t = stt.chirp3_worker(pcm, 16000, "eu", "tok", request=req)
    check("chirp_3 normal: Aufruf geht durch, 30 s gebucht, keine Sperre", t == "Text" and len(REQ) == 1
          and d7.verbraucht_s() == 30.0 and stt.letzte_sperre() is None, f"{t} {REQ} {d7.verbraucht_s()}")

    def kaputt(token, loc, b64, **kw):
        REQ.append(-1)
        raise OSError("Netz weg")
    try:
        stt.chirp3_worker(pcm + 1, 16000, "eu", "tok", request=kaputt)
    except OSError:
        pass
    check("… Fehlversuch (Ausnahme) zählt trotzdem (Google hat das Audio bekommen)", d7.verbraucht_s() == 60.0,
          str(d7.verbraucht_s()))
    lang = np.arange(16000 * 140, dtype=np.int16) % 3000   # 140 s → Stücke 50/50/48 s; Grenze 120 s
    REQ.clear()
    t = stt.chirp3_worker(lang, 16000, "eu", "tok", request=req)
    check("langes Diktat über die Grenze: Stücke bis zur Grenze, dann kein weiterer Aufruf → None + „grenze“",
          t is None and len(REQ) == 2 and stt.letzte_sperre() == "grenze" and d7.verbraucht_s() == 160.0,
          f"{t} {REQ} {d7.verbraucht_s()} {stt.letzte_sperre()}")
    REQ.clear()
    t = stt.chirp3_worker(np.ones(16000 * 5, dtype=np.int16), 16000, "eu", "tok", request=req)
    check("Grenze erreicht: KEIN Google-Aufruf mehr, None, letzte_sperre „grenze“",
          t is None and REQ == [] and stt.letzte_sperre() == "grenze", f"{t} {REQ}")
    andere = []
    th = threading.Thread(target=lambda: andere.append(stt.letzte_sperre()))
    th.start(); th.join()
    check("… Sperrgrund gilt nur im eigenen Thread", andere == [None], str(andere))

    jetzt.t = datetime.datetime(2026, 11, 29, 8, 0, tzinfo=WIEN)
    REQ.clear()
    neu = pcm + 5                                          # frische Aufnahme (pcm ging oben schon 1× raus)
    erg = [stt.chirp3_worker(neu, 16000, "eu", "tok", request=req) for _ in range(5)]
    check("Schleife (EXE ruft dieselbe Aufnahme 5×): nur 3 Google-Aufrufe, danach None + „schleife“",
          erg == ["Text"] * 3 + [None, None] and len(REQ) == 3 and stt.letzte_sperre() == "schleife", f"{erg} {REQ}")
finally:
    stt.DECKEL = None
REQ.clear()
check("ohne Deckel (stt.DECKEL = None) wie bisher", stt.chirp3_worker(pcm, 16000, "eu", "tok", request=req) == "Text"
      and len(REQ) == 1 and stt.letzte_sperre() is None)

# ── 7. Live-Anzeige (aufnahme.py) ─────────────────────────────────────────────────────────────────────────────────
import exe_stubs as S  # noqa: E402

STREAM = []


def streaming(reqs):
    STREAM.append(1)
    for _ in reqs:
        pass
    return iter(())


def aufnehmen(n_bloecke):
    sd = type("sd", (), {"InputStream": S.FakeInputStream})
    lg = []
    a = af.Aufnahme(sd, 16000, 0, streaming=streaming, request_bauen=lambda b: b, log=lg.append, live=True)
    a.start()
    ev = threading.Event()
    for _ in range(400):
        if len(a.puffer) >= n_bloecke:
            break
        ev.wait(0.01)
    a.stop(); a.warten()
    return a, lg


jetzt.t = datetime.datetime(2026, 11, 30, 8, 0, tzinfo=WIEN)
d8 = dk.Deckel(os.path.join(TMP, "live"), pc="PC1", limit_min=1, jetzt=jetzt)
af.DECKEL = d8
try:
    a, lg = aufnehmen(8)
    check("Live-Anzeige unter der Grenze: Streaming läuft, Sekunden als „streaming“ gebucht",
          STREAM and d8.verbraucht_s() > 0 and (d8._mem or {}).get("art", {}).get("streaming", 0) > 0, str(d8._mem))
    d8.buchen(60)
    STREAM.clear()
    vor = d8.verbraucht_s()
    a, lg = aufnehmen(8)
    check("Grenze erreicht: KEINE Streaming-Sitzung, Aufnahme (Puffer) läuft weiter, Log-Zeile",
          STREAM == [] and len(a.puffer) >= 8 and not a.streaming_aktiv and d8.verbraucht_s() == vor
          and any("[STT-DECKEL]" in l for l in lg), f"{STREAM} {len(a.puffer)} {lg[-3:]}")
finally:
    af.DECKEL = None

# ── 8. config.ini STT_TAGESDECKEL_MIN ───────────────────────────────────────────────────────────────────────────────


def lies(zeile):
    p = os.path.join(TMP, "config.ini")
    with open(p, "w", encoding="utf-8") as f:
        f.write("[SETTINGS]\nLLM_PROVIDER = gemini\n" + zeile)
    return cfgmod.load_config(p)


check("config: Zeile fehlt → 240", lies("").stt_tagesdeckel_min == 240)
check("config: STT_TAGESDECKEL_MIN = 360 → 360", lies("STT_TAGESDECKEL_MIN = 360\n").stt_tagesdeckel_min == 360)
c0 = lies("STT_TAGESDECKEL_MIN = 0\n")
check("config: 0 (kein „aus“) → 240 + Warnung", c0.stt_tagesdeckel_min == 240 and any("STT_TAGESDECKEL_MIN" in w for w in c0.warnungen))
cx = lies("STT_TAGESDECKEL_MIN = viel\n")
check("config: keine Zahl → 240 + Warnung", cx.stt_tagesdeckel_min == 240 and cx.warnungen)
check("config.ini im Repo dokumentiert die Zeile (auskommentiert)",
      "# STT_TAGESDECKEL_MIN = 240" in (ROOT / "config.ini").read_text(encoding="utf-8"))

# ── 9. Meldeweg: Nutzungszähler → Tagesbericht „STT-DECKEL“ → Chirp-Warnung → Karte für Hermes ─────────────────────
no = os.path.join(TMP, "nutzung")
z = nutzung.Zaehler(no, pc="CASWS10", jetzt=lambda: datetime.datetime(2026, 11, 24, 15, 0))
z.stt_deckel("warn80", {"min": 192.4, "limit_min": 240})
txt = open(os.path.join(no, "tagesbericht_2026-11-24.txt"), encoding="utf-8").read()
zeile = [l for l in txt.splitlines() if l.startswith("STT-DECKEL")]
check("Nutzungszähler: Tagesbericht-Zeile „STT-DECKEL CASWS10: 80 % … 192 von 240 min“",
      zeile == ["STT-DECKEL CASWS10: 80 % der Tagesgrenze erreicht – 192 von 240 min Audio"], txt)
check("… kein „WARNUNG“-Alarm an Peter (nur die Deckel-Zeile)", "WARNUNG" not in txt)

spec = importlib.util.spec_from_file_location("cw", ROOT / "tools" / "mac" / "kaiscribe_chirp_warnung.py")
cw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cw)
spec = importlib.util.spec_from_file_location("kl", ROOT / "tools" / "vm" / "kaiscribe_nutzung_lesen.py")
kl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kl)
daten = os.path.join(TMP, "Daten")
os.makedirs(os.path.join(daten, "laeufe"))
os.rename(no, os.path.join(daten, "nutzung"))
import io  # noqa: E402
from contextlib import redirect_stdout  # noqa: E402
buf = io.StringIO()
with redirect_stdout(buf):
    kl.main(["--tage", "2026-11-23,2026-11-24", "--ordner", daten])
e = cw.auswerten(buf.getvalue(), "2026-11-24")
check("Chirp-Warnung liest die Deckel-Zeile über den VM-Leser", e["deckel"] and e["deckel"][0][0] == "2026-11-24"
      and e["deckel"][0][1].startswith("STT-DECKEL CASWS10"), str(e.get("deckel")))
cw.ZUSTAND = os.path.join(TMP, "zustand.json")
aufrufe = os.path.join(TMP, "aufrufe.txt")
fake = os.path.join(TMP, "kanban.py")
pathlib.Path(fake).write_text("import sys\nopen(%r, 'a', encoding='utf-8').write(repr(sys.argv[1:]) + '\\n')\n"
                              "print('#902 [tun] ' + sys.argv[2])\n" % aufrufe, encoding="utf-8")
cw.KANBAN = fake
neu1, neu2 = cw.deckel_karten(e), cw.deckel_karten(e)
args = [eval(l) for l in open(aufrufe, encoding="utf-8")]
check("… genau EINE Karte je Tag und PC, Spalte tun (Hermes), nicht Peter",
      neu1 == ["2026-11-24 CASWS10"] and neu2 == [] and len(args) == 1 and "--tun" in args[0] and "--peter" not in args[0]
      and "--grund" not in args[0], str(args))
check("… Karte nennt Zähler-Datei und gesicherte Aufnahmen", "stt_tagesdeckel_" in " ".join(args[0])
      and "nicht_erkannt" in " ".join(args[0]))

# ── 10. EXE-Ablauf (kp ohne Live-Anzeige, rg mit): Grenze erreicht → kein Google-Aufruf, WAV, rote Zeile ─────────────
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: True
mod.STT_NEUVERSUCH_S = 0.0
mod.NICHT_ERKANNT_DIR = os.path.join(TMP, "nicht_erkannt")
mod._korr.korrigieren = lambda t, key, block="", log=None: t
LOG = []
mod.log = lambda *x: LOG.append(" ".join(str(y) for y in x))
mod._llm_aufruf = lambda p: "## Kniegelenk rechts\n\n## Befund\nKleiner Gelenkerguss.\n\n## Ergebnis\nKleiner Gelenkerguss."
GOOGLE = []


def google_request(token, loc, b64, **kw):
    GOOGLE.append(len(b64))
    return "Kniegelenk rechts in 2 Ebenen unauffällig."


mod._chirp3_worker = lambda pcm, sr, loc, token: stt.chirp3_worker(pcm, sr, loc, token, request=google_request)
STREAMS = []


def streaming_stub(requests):
    STREAMS.append(1)
    for _ in requests:
        pass
    return iter(())


jetzt.t = datetime.datetime(2026, 12, 1, 18, 0, tzinfo=WIEN)
DK = mod._deckel_einrichten(os.path.join(TMP, "exe"), 1)
DK.jetzt = jetzt
check("EXE: Deckel in stt und aufnahme eingehängt", stt.DECKEL is DK and af.DECKEL is DK and mod.DECKEL is DK)


def neue_app(benutzer):
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
    GOOGLE.clear(); STREAMS.clear(); LOG.clear()
    mod.speech_client = S.FakeSpeechClient(streaming_stub)
    app = S.baue_app(mod)
    app.result_text._textbox = S.FakeTb(app.result_text, 0, None)
    app.focus_get = lambda: app.result_text._textbox
    app.status_badge = S.FakeWidget()
    app.repariert_label = S.FakeWidget()
    app.nur_text_var = type("V", (), {"get": lambda self: False})()
    app._cas = type("A", (), {"nr": "20261201901", "benutzer": benutzer, "leistungen": None, "kontext": None,
                              "ibl": None, "auftrag_id": "x"})()
    app._cas_aufnahmen, app._cas_hinweise = [], []
    app._cas_hinweise_zeigen = lambda h: setattr(app, "_cas_hinweise", list(h or []))
    app._ibl_befund_leeren = lambda: None
    app._ibl_nach_lauf = lambda e: None
    return app


def diktat(app, n=14):
    app.sm_record()
    S.pump(app, lambda: len(app._aufnahme.puffer) >= n)
    app.sm_ins()
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
    S.pump(app, lambda: False, 0.4)
    app._aufnahme_stoppen()


app = neue_app("kp")
diktat(app)
check("EXE kp unter der Grenze: chirp_3 geht an Google (1×), Befund rechts, Kürzel kp gezählt",
      len(GOOGLE) == 1 and app.result_text.text.startswith("## Kniegelenk") and "kp" in (DK._mem or {}).get("kuerzel", {}),
      f"{GOOGLE} {app.result_text.text[:30]!r} {DK._mem}")
DK.buchen(60)
for benutzer in ("kp", "rg"):
    app = neue_app(benutzer)
    diktat(app)
    wavs = sorted(os.listdir(mod.NICHT_ERKANNT_DIR)) if os.path.isdir(mod.NICHT_ERKANNT_DIR) else []
    lbl = app.repariert_label.cfg.get("text", "")
    check(f"EXE {benutzer} Grenze erreicht: KEIN Google-Aufruf (chirp_3 und Live-Anzeige), keine Wiederholung",
          GOOGLE == [] and STREAMS == [] and not any("wird einmal wiederholt" in l for l in LOG), f"{GOOGLE} {STREAMS} {LOG[-6:]}")
    check(f"… {benutzer}: Audio gesichert (WAV mit Diktat-Nr.) + CAS-Aufnahme bleibt",
          any(w.endswith("_20261201901.wav") for w in wavs) and app._cas_aufnahmen, str(wavs))
    check(f"… {benutzer}: rote Zeile „Tagesgrenze Spracherkennung erreicht – Aufnahme gesichert, bitte Hermes melden“",
          lbl == "⚠ " + dk.GRENZE_TEXT and app.repariert_label.cfg.get("text_color") == mod.RECORDING_RED,
          f"{lbl!r} {app._status_raw}")
    check(f"… {benutzer}: kein Befund, nichts ins RIS", app.result_text.text == "" and S.AUFZ.tasten == [],
          repr(app.result_text.text[:40]))
    for w in wavs:
        os.remove(os.path.join(mod.NICHT_ERKANNT_DIR, w))
check("EXE: Log-Zeilen [STT-DECKEL] im KaiScribe-Log", any("Tagesgrenze Spracherkennung erreicht" in l for l in LOG), LOG[-6:])
stt.DECKEL = af.DECKEL = None
check("EXE-Bau nimmt das Modul mit", "--hidden-import=stt_deckel" in (ROOT / ".github/workflows/build-exe.yml").read_text(encoding="utf-8"))

print(f"\n{'ALLE GRÜN' if not fails else f'{fails} ROT'}")
sys.exit(1 if fails else 0)
