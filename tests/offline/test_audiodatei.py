"""Gate v3.16.0 „Audio laden“ + WAV-Modus (audiodatei.py und der EXE-Ablauf über exe_stubs, ohne Tk/Mikrofon/Google).
1. Lesen: PCM-WAV 8/16/24 bit, Stereo, 44,1/48/8 kHz → 16 kHz mono int16; ogg/opus + mp3 über soundfile (wenn installiert —
   in der CI immer); m4a ohne Decoder → verständliche Meldung; fehlende Datei → Meldung.
2. Umrechnen: Länge und Frequenz bleiben (Nulldurchgänge), kein Aliasing-Müll bei 48 → 16 kHz.
3. WavQuelle als sounddevice-Ersatz in aufnahme.Aufnahme: Datei-Audio landet vollständig im Puffer, danach Stille.
4. Ablaufskript: Prüfung (unbekannte Taste/Bedingung, zwei Schlüssel, fehlende Datei, relativer Pfad), Läufer mit
   Zeitgrenze → Abbruch + ende(), sprich ohne offene Aufnahme → Fehler.
5. EXE: audio_laden → chirp_3 bekommt das Datei-Audio, Befund rechts zur Kontrolle, nichts eingefügt; mit CAS-Auftrag
   legt EOL Befund + Datei-Audio für die Brücke ab; unlesbare Datei → Fehler-Zustand, kein Befund.
6. EXE im WAV-Modus: Ablauf RECORD → sprich → INS → warte_auf kontrolle → EOL über denselben Tasten-Dekodierer wie das
   Gerät, echtes Aufnahme-Objekt mit WavQuelle; Gast (keine Zwischenablage, kein Strg+V, keine Dialoge); simulierter
   STT-Ausfall → kein Befund, EOL schickt nichts, Schließen meldet „abgebrochen“.
Aufruf: /usr/bin/python3 tests/offline/test_audiodatei.py"""
import json, os, pathlib, sys, tempfile, time, wave
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
AUDIO = pathlib.Path(__file__).resolve().parent / "audio"
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


sys.path.insert(0, str(ROOT / "source_code"))
import audiodatei as ad  # noqa: E402
import aufnahme as af  # noqa: E402

TMP = tempfile.mkdtemp(prefix="rks_audio_")


def wav(name, x, sr, breite=2, kanaele=1):
    p = os.path.join(TMP, name)
    x = np.asarray(x, dtype=np.float64)
    if kanaele == 2:
        x = np.stack([x, x * 0.5], axis=1)
    with wave.open(p, "wb") as w:
        w.setnchannels(kanaele)
        w.setsampwidth(breite)
        w.setframerate(sr)
        if breite == 1:
            roh = (x * 127 + 128).astype(np.uint8).tobytes()
        elif breite == 2:
            roh = (x * 32767).astype("<i2").tobytes()
        else:
            v = (x * (2 ** 23 - 1)).astype(np.int32).reshape(-1)
            b = np.stack([v & 255, (v >> 8) & 255, (v >> 16) & 255], axis=1).astype(np.uint8)
            roh = b.tobytes()
        w.writeframes(roh)
    return p


def sinus(f, sr, s=1.0, a=0.5):
    t = np.arange(int(sr * s)) / sr
    return a * np.sin(2 * np.pi * f * t)


def frequenz(pcm, sr=16000):
    x = pcm.astype(np.float64)
    nd = np.sum((x[:-1] < 0) & (x[1:] >= 0))
    return nd / (len(x) / sr)


# ───────────── 1. Lesen ─────────────
for name, sr, breite, kan in (("16bit_mono_16k.wav", 16000, 2, 1), ("16bit_stereo_44k.wav", 44100, 2, 2),
                              ("8bit_mono_8k.wav", 8000, 1, 1), ("24bit_mono_48k.wav", 48000, 3, 1)):
    p = wav(name, sinus(440, sr, 1.0), sr, breite, kan)
    pcm = ad.lesen(p)
    check(f"WAV {name} → 16 kHz mono int16, 1 s, 440 Hz",
          pcm.dtype == np.int16 and pcm.ndim == 1 and abs(len(pcm) - 16000) <= 2 and abs(frequenz(pcm) - 440) < 5,
          f"{pcm.dtype} {pcm.shape} f={frequenz(pcm):.1f}")
try:
    import soundfile  # noqa: F401
    HAT_SF = True
except Exception:
    HAT_SF = False
if HAT_SF:
    for name in ("ton_440.ogg", "ton_440.mp3"):
        pcm = ad.lesen(str(AUDIO / name))
        check(f"{name} (Telegram = ogg/opus, mp3) → 16 kHz, ~1,5 s, 440 Hz",
              abs(len(pcm) / 16000 - 1.5) < 0.12 and abs(frequenz(pcm[2000:-2000]) - 440) < 8,
              f"{len(pcm) / 16000:.2f} s, f={frequenz(pcm[2000:-2000]):.1f}")
else:
    print("ℹ️  soundfile nicht installiert – ogg/mp3 prüft die CI (pip install soundfile)")
kaputt = os.path.join(TMP, "sprachmemo.m4a")
open(kaputt, "wb").write(b"\x00\x00\x00\x18ftypM4A kein echtes audio")
try:
    ad.lesen(kaputt)
    check("m4a ohne Decoder → AudioFehler", False)
except ad.AudioFehler as e:
    check("m4a ohne Decoder → AudioFehler mit Tipp (mp3/ogg/wav oder Web-App)", "m4a" in str(e) and "Web-App" in str(e), str(e))
try:
    ad.lesen(os.path.join(TMP, "gibtsnicht.wav"))
    check("fehlende Datei → AudioFehler", False)
except ad.AudioFehler as e:
    check("fehlende Datei → AudioFehler „nicht gefunden“", "nicht gefunden" in str(e), str(e))

# ───────────── 2. Umrechnen ─────────────
x48 = sinus(1000, 48000, 1.0) + 0.3 * sinus(11000, 48000, 1.0)       # 11 kHz liegt über der 8-kHz-Grenze
y = ad.umrechnen(x48, 48000, 16000)
spek = np.abs(np.fft.rfft(y * np.hanning(len(y))))
f = np.fft.rfftfreq(len(y), 1 / 16000)
alias = spek[(f > 4500) & (f < 5500)].max() / spek[(f > 900) & (f < 1100)].max()   # 11 kHz spiegelt sich auf 5 kHz
check("48 → 16 kHz: Länge stimmt, 1 kHz bleibt, 11 kHz wird nicht auf 5 kHz gespiegelt (< 5 %)",
      len(y) == 16000 and alias < 0.05, f"len {len(y)} alias {alias:.3f}")
y8 = ad.umrechnen(sinus(300, 8000, 0.5), 8000, 16000)
check("8 → 16 kHz: doppelte Länge", len(y8) == 8000)

# ───────────── 3. WavQuelle in der echten Aufnahme ─────────────
q = ad.WavQuelle(echtzeit=False)
daten = (np.arange(4000) % 1000 + 1).astype(np.int16)
q.einspielen(daten)
gesehen = []
a = af.Aufnahme(q, 16000, 0, streaming=lambda reqs: (gesehen.append(len(r)) for r in reqs if False),
                request_bauen=lambda b: b)
a.start()
t0 = time.time()
while q.rest_s() > 0 and time.time() - t0 < 3:
    time.sleep(0.01)
time.sleep(0.05)
a.stop()
a.warten(timeout_stream=1)
s = a.samples().reshape(-1)
check("WavQuelle: Datei-Audio steht vollständig und in Reihenfolge im Aufnahme-Puffer (für chirp_3), danach Stille",
      np.array_equal(s[:4000], daten) and not s[4000:].any() and len(s) % 1600 == 0 and abs(q.gespielt_s - 0.25) < 1e-6,
      f"{len(s)} {q.gespielt_s}")
check("WavQuelle: query_devices/default wie sounddevice", q.query_devices()[0]["max_input_channels"] == 1
      and q.default.device[0] == 0)
qe = ad.WavQuelle(echtzeit=True)
qe.einspielen(np.ones(8000, dtype=np.int16))
zeiten = []
with qe.InputStream(callback=lambda b, n, t, st: zeiten.append(time.monotonic())):
    time.sleep(0.55)
check("WavQuelle Echtzeit: 100-ms-Blöcke (0,5 s ≈ 5–6 Blöcke)", 4 <= len(zeiten) <= 7, str(len(zeiten)))

# ───────────── 4. Ablaufskript ─────────────
lws = wav("lws.wav", sinus(200, 16000, 0.3), 16000)
fehler_faelle = [([{"taste": "XYZ"}], "unbekannte Taste"), ([{"warte_auf": "irgendwas"}], "unbekannte Bedingung"),
                 ([{"taste": "RECORD", "warte_s": 1}], "genau einer"), ([{"sprich": "fehlt.wav"}], "Audio-Datei fehlt"),
                 ([], "leer"), ([{"fehler": "strom"}], "fehler =")]
for schritte, erwartet in fehler_faelle:
    try:
        ad.ablauf_pruefen({"schritte": schritte}, TMP)
        check(f"Ablauf-Prüfung: {erwartet}", False)
    except ad.AblaufFehler as e:
        check(f"Ablauf-Prüfung meldet: {erwartet}", erwartet in str(e), str(e))
ab_pfad = os.path.join(TMP, "ablauf.json")
json.dump({"schritte": [{"taste": "record"}, {"sprich": "lws.wav"}, {"warte_auf": "kontrolle", "timeout_s": 5},
                        {"ende": True}], "max_s": 60}, open(ab_pfad, "w", encoding="utf-8"))
ab = ad.ablauf_laden(ab_pfad)
check("Ablauf laden: Taste groß, Pfad relativ zum Skript, timeout_s, max_s",
      ab["schritte"][0] == ("taste", "RECORD", {}) and ab["schritte"][1][1] == lws
      and ab["schritte"][2][2]["timeout_s"] == 5.0 and ab["max_s"] == 60.0, str(ab))


class Uhr:
    def __init__(self):
        self.t = 0.0

    def jetzt(self):
        return self.t

    def schlafen(self, s):
        self.t += max(s, 0.01)


uhr = Uhr()
spur = []
qa = ad.WavQuelle(echtzeit=False)
lf = ad.AblaufLaeufer(ad.ablauf_pruefen({"schritte": [{"taste": "RECORD"}, {"warte_auf": "kontrolle", "timeout_s": 3},
                                                      {"taste": "EOL"}]}, TMP), qa,
                      {"taste": spur.append, "trigger": spur.append, "merke": spur.append,
                       "bedingung": lambda n: False, "fehler": spur.append, "ende": lambda: spur.append("ENDE")},
                      jetzt=uhr.jetzt, schlafen=uhr.schlafen)
lf.lauf()
check("Läufer: Zeitgrenze bei warte_auf → Abbruch (EOL nicht gedrückt), ende() aufgerufen, Protokoll mit Zeiten",
      spur == ["RECORD", "ENDE"] and "Zeitgrenze" in lf.fehler and lf.fertig and lf.protokoll[1]["ok"] is False
      and lf.protokoll[1]["dauer_s"] >= 3, f"{spur} {lf.fehler} {lf.protokoll}")
spur.clear()
lf2 = ad.AblaufLaeufer(ad.ablauf_pruefen({"schritte": [{"sprich": lws}, {"taste": "EOL"}]}, TMP), ad.WavQuelle(echtzeit=False),
                       {"taste": spur.append, "trigger": spur.append, "merke": spur.append, "bedingung": lambda n: True,
                        "fehler": spur.append, "ende": lambda: spur.append("ENDE")}, jetzt=uhr.jetzt, schlafen=uhr.schlafen)
lf2.lauf()
check("Läufer: sprich ohne offene Aufnahme → Fehler „erst RECORD“, Rest übersprungen", spur == ["ENDE"]
      and "erst RECORD" in lf2.fehler, f"{spur} {lf2.fehler}")

# ───────────── 5. EXE: Audio laden ─────────────
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: False
CHIRP = []


def chirp(pcm, sr, loc, token):
    CHIRP.append(len(pcm))
    return "Lendenwirbelsäule in 2 Ebenen unauffällig"


mod._chirp3_worker = chirp
mod._llm_aufruf = lambda p: "## Lendenwirbelsäule in 2 Ebenen\n\n## Befund\nRegelrecht.\n\n## Ergebnis\nUnauffällig."
ORDNER = tempfile.mkdtemp(prefix="rks_audio_cas_")
cas_mod = mod._cas


class Band(S.FakeWidget):
    sichtbar = False

    def pack(self, **k):
        self.sichtbar = True

    def pack_forget(self):
        self.sichtbar = False

    def winfo_ismapped(self):
        return self.sichtbar


class Var:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


def neue_app():
    app = S.baue_app(mod)
    app._cas, app._cas_aufnahmen, app._cas_test = None, [], False
    app._cas_kanal = cas_mod.Kanal(ORDNER, pid=777, version="3.16.0", prozess_lebt=lambda pid: True)
    app._fensterziel = mod._fz.Fensterziel(None)
    for n in ("cas_label", "cas_hinweis_label", "bestaetigung_label", "repariert_label", "diktat_titel"):
        setattr(app, n, S.FakeWidget())
    for n in ("cas_band", "bestaetigung_band", "cas_kopf_label", "vorbefund_knopf", "ibl_label", "ibl_hinweis_label",
              "ibl_zeile", "ibl_knopf"):
        setattr(app, n, Band())
    app.main_container = None
    app.ibl_var, app.maske_var, app.nach_cas_minimieren_var, app.nur_text_var = Var(True), Var(True), Var(False), Var(False)
    app._speechmike = None
    app.destroy = lambda: None
    app.iconify = app.deiconify = lambda: None
    app._maske_leeren()
    return app


app = neue_app()
S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
datei = wav("diktat.wav", sinus(300, 22050, 2.0, 0.3), 22050)
app.audio_laden(datei)
S.pump(app, lambda: app._job.zustand == "READY" and app._befund_wartet, 10)
check("Audio laden: chirp_3 bekommt das Datei-Audio (2 s bei 16 kHz)", CHIRP == [32000], str(CHIRP))
check("… Diktat links, Befund rechts zur Kontrolle (nichts eingefügt, kein Strg+V)",
      app.transcript_text.get("1.0", "end-1c").startswith("Lendenwirbelsäule") and "## Befund" in app.result_text.text
      and app._befund_wartet and S.AUFZ.tasten == [] and app._status_raw == "KONTROLLE",
      f"{app.transcript_text.text!r} {app._status_raw} {S.AUFZ.tasten}")
check("… Info für den Selbsttest (Name, Sekunden)", app._audio_datei_info == {"name": "diktat.wav", "sekunden": 2.0,
                                                                               "fehler": ""}, str(app._audio_datei_info))
CHIRP.clear()
app2 = neue_app()
with open(os.path.join(ORDNER, cas_mod.AUFTRAG), "w", encoding="utf-8") as f:
    json.dump({"protokoll": 1, "auftrag_id": "a1", "nr": "20261015900", "benutzer": "kp", "bruecke_pid": 4242,
               "zeit": time.time(), "zeit_text": "", "testbefund": False}, f)
app2._cas_einmal()
app2.audio_laden(datei)
S.pump(app2, lambda: app2._befund_wartet, 10)
app2.befund_fertig()
S.pump(app2, None, 0.3)
erg_wav = os.path.join(ORDNER, "cas_ergebnis_20261015900.wav")
ant = json.load(open(os.path.join(ORDNER, "cas_antwort_a1.json"), encoding="utf-8"))
with wave.open(erg_wav) as w:
    sek = w.getnframes() / w.getframerate()
check("Audio laden mit CAS-Auftrag: EOL → Befund-Datei + <Nr>.wav mit dem Datei-Audio (2 s), Antwort „fertig“",
      ant.get("status") == "fertig" and abs(sek - 2.0) < 0.01
      and "Lendenwirbelsäule" in open(os.path.join(ORDNER, "cas_ergebnis_20261015900.txt"), encoding="utf-8").read(),
      f"{ant} {sek}")
CHIRP.clear()
app3 = neue_app()
app3.audio_laden(kaputt)
S.pump(app3, lambda: app3._job.zustand == "ERROR", 5)
check("Audio laden: unlesbare Datei → Fehler-Zustand mit Meldung, kein Befund, chirp_3 nicht gerufen",
      app3._job.zustand == "ERROR" and not app3.result_text.text and CHIRP == []
      and S.AUFZ.dialoge[-1][:2] == ("showerror", "Audio-Datei") and "m4a" in S.AUFZ.dialoge[-1][2], f"{app3._job.zustand} {S.AUFZ.dialoge[-1:]}")

# ───────────── 6. EXE im WAV-Modus ─────────────
ZUSTAND = os.path.join(TMP, "zustand.json")
os.environ["RAKSCRIBE_SELFTEST"] = ZUSTAND
os.environ["RAKSCRIBE_WAV_ABLAUF"] = os.path.join(TMP, "wav_ablauf.json")
check("WAV-Modus nur mit Selbsttest-Gerüst, immer Gast", mod.wav_modus() and mod.gast_selbsttest())
STREAM = []


def streaming(requests, config=None):
    for n, r in enumerate(requests, 1):
        STREAM.append(len(r))
        if n == 3:
            yield S.Antwort("Lendenwirbelsäule", False)


mod.speech_client = type("C", (), {"streaming_recognize": lambda self, requests, config=None: streaming(requests)})()
CHIRP_TEXT = ["Lendenwirbelsäule in 2 Ebenen unauffällig"]
mod._chirp3_worker = lambda pcm, sr, loc, tok: CHIRP.append(len(pcm)) or (CHIRP_TEXT[0] if CHIRP_TEXT else "")
quelle = mod._wav_modus_einrichten()
check("WAV-Modus: sounddevice → WavQuelle, Dialoge still", mod.sd is quelle and isinstance(mod.messagebox, mod._StilleDialoge))
quelle.echtzeit = False


def wav_app(schritte, nr, aid):
    a = neue_app()
    a._speechmike = mod._sm.SpeechMikeLeser(on_taste=lambda t, g, roh: a.after(0, a.speechmike_taste, t, g, roh),
                                            log=lambda *x: None, hid_modul=None)
    gesichert = []
    a._st_dump = lambda name: gesichert.append((name, a.result_text.text, a._job.zustand))
    a._st_phase = lambda ph: gesichert.append(("phase", ph))
    a._schliessen_echt = a._schliessen
    a.geschlossen = []
    a._schliessen = lambda: (a.geschlossen.append(True), a._schliessen_echt())
    json.dump({"schritte": schritte, "max_s": 60}, open(os.environ["RAKSCRIBE_WAV_ABLAUF"], "w", encoding="utf-8"))
    with open(os.path.join(ORDNER, cas_mod.AUFTRAG), "w", encoding="utf-8") as f:
        json.dump({"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": "kp", "bruecke_pid": 4242,
                   "zeit": time.time(), "zeit_text": "", "testbefund": False}, f)
    a._cas_einmal()
    a._wav_ablauf_starten()
    S.pump(a, lambda: bool(a.geschlossen), 30)
    return a, gesichert


CHIRP.clear(); S.AUFZ.tasten.clear(); S.CLIPBOARD.data = {}
diktat_wav = wav("e1.wav", sinus(250, 16000, 1.2, 0.4), 16000)
a, ges = wav_app([{"warte_auf": "cas", "timeout_s": 5}, {"taste": "RECORD", "danach_s": 0.1}, {"sprich": diktat_wav, "danach_s": 0.2},
                  {"taste": "INS", "danach_s": 0.1}, {"warte_auf": "kontrolle", "timeout_s": 10}, {"merke": "nach_ins"},
                  {"taste": "EOL", "danach_s": 0.2}, {"warte_auf": "kein_cas", "timeout_s": 5}, {"ende": True}],
                 "20261015901", "w1")
lf = a._wav_laeufer
ant = json.load(open(os.path.join(ORDNER, "cas_antwort_w1.json"), encoding="utf-8"))
with wave.open(os.path.join(ORDNER, "cas_ergebnis_20261015901.wav")) as w:
    sek = w.getnframes() / w.getframerate()
check("WAV-Ablauf: alle Schritte ok, Protokoll mit Zeiten, „ende“ festgehalten, RaKScribe geschlossen",
      not lf.fehler and len(lf.protokoll) == 8 and all(p["ok"] for p in lf.protokoll) and ges[-1][0] == "ende"
      and a.geschlossen, f"{lf.fehler} {lf.protokoll} {ges}")
check("… Tasten über den Geräte-Dekodierer: Aufnahme mit WavQuelle, Streaming bekam Pakete, chirp_3 das ganze Audio",
      STREAM and CHIRP and CHIRP[0] >= 1.2 * 16000, f"{len(STREAM)} {CHIRP}")
check("… nach INS Befund rechts (merke nach_ins), EOL → Brücke „fertig“, <Nr>.wav ≥ 1,2 s",
      any(n == "nach_ins" and "## Befund" in t for n, t, _z in ges) and ant.get("status") == "fertig" and sek >= 1.2,
      f"{ges} {ant} {sek}")
check("… Gast: Zwischenablage unberührt, kein Strg+V, kein Dialog", S.CLIPBOARD.data == {} and S.AUFZ.tasten == []
      and mod._WAV_DIALOGE == [], f"{S.CLIPBOARD.data} {S.AUFZ.tasten} {mod._WAV_DIALOGE}")
check("… Stand für das Selbsttest-JSON (Protokoll, gespielte Sekunden)", a._wav_stand()["fertig"]
      and a._wav_stand()["gespielt_s"] >= 1.2, str(a._wav_stand()))

CHIRP.clear()
a, ges = wav_app([{"warte_auf": "cas", "timeout_s": 5}, {"fehler": "stt"}, {"taste": "RECORD", "danach_s": 0.1},
                  {"sprich": diktat_wav, "danach_s": 0.2}, {"taste": "INS", "danach_s": 0.1},
                  {"warte_auf": "fertig", "timeout_s": 10}, {"merke": "nach_ins"}, {"taste": "EOL", "danach_s": 0.2},
                  {"merke": "nach_eol"}, {"ende": True}], "20261015902", "w2")
ant = json.load(open(os.path.join(ORDNER, "cas_antwort_w2.json"), encoding="utf-8"))
check("WAV-Ablauf mit STT-Ausfall: kein Befund, EOL schickt nichts, Schließen → Brücke „abgebrochen“, keine Ergebnis-Datei",
      not os.path.exists(os.path.join(ORDNER, "cas_ergebnis_20261015902.txt")) and ant.get("status") == "abgebrochen"
      and all(not t for n, t, _z in ges if n in ("nach_ins", "nach_eol")), f"{ant} {ges}")
check("… Dialog „Kein Text diktiert“ nur protokolliert", any("Kein Text" in d for d in mod._WAV_DIALOGE), str(mod._WAV_DIALOGE))
mod._WAV_FEHLER = "aus"

print("\n" + ("✅ AUDIO-DATEI PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
