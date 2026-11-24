"""Gate kaiscribe-live-anzeige-aus-kp-n1 (Peter 24.11.2026 „Ja“ auf Vorschlag 1 + Nachtrag 18:57): für kp KEINE
Live-Anzeige – kein Google-Streaming, keine Abschnitts-Reparatur je SpeechMike-Pause (kein chirp_3-Aufruf je Pause).
Links während der Aufnahme nur das bisherige Diktat (Nachdiktat-Basis) + „● Aufnahme läuft“ (+ Pegel); der Text kommt
nach Stopp/INS aus chirp_3 über die ganze Aufnahme. Rückfall: chirp_3 einmal wiederholen, sonst Audio behalten + rote
Zeile „Spracherkennung nicht verfügbar – bitte erneut diktieren/prüfen“ (nie still leer). Rechts einfügen (Cursor,
Markierung übersprechen, Nachdiktat/Ergänzung) unverändert aus _neuer_text. rg unverändert (Streaming + Reparatur).
Echte RaKScribeApp-Logik mit Attrappen (exe_stubs), synthetische Texte, keine Patientendaten, keine Google-Aufrufe.
Aufruf: python tests/offline/test_live_anzeige_aus.py"""
import os, pathlib, sys, tempfile, threading
HIER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parents[1] / "source_code"))
import exe_stubs as S  # noqa: E402
import aufnahme as af  # noqa: E402
import config as cfgmod  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# 1. config.ini LIVE_ANZEIGE_AUS
TMP = tempfile.mkdtemp(prefix="rks_live_aus_")


def lies(zeile):
    p = os.path.join(TMP, "config.ini")
    with open(p, "w", encoding="utf-8") as f:
        f.write("[SETTINGS]\nLLM_PROVIDER = gemini\n" + zeile)
    return cfgmod.load_config(p)


check("config: Standard (Zeile fehlt) → Live-Anzeige aus nur für kp", lies("").live_anzeige_aus == ["kp"])
check("config: LIVE_ANZEIGE_AUS = aus → niemand (Rollback-Schalter)", lies("LIVE_ANZEIGE_AUS = aus\n").live_anzeige_aus == [])
check("config: LIVE_ANZEIGE_AUS = kp, rg → beide", lies("LIVE_ANZEIGE_AUS = kp, rg\n").live_anzeige_aus == ["kp", "rg"])
check("config: Dataclass-Standard kp", cfgmod.Config().live_anzeige_aus == ["kp"])

# 2. aufnahme.Aufnahme(live=False): Puffer + Pegel wie bisher, kein Streaming-Thread, kein Google-Aufruf
STREAM_AUFRUFE = []


def streaming_zaehlend(reqs):
    STREAM_AUFRUFE.append(1)
    for _ in reqs:
        pass
    return iter(())


sd = type("sd", (), {"InputStream": S.FakeInputStream})
pegel, logs = [], []
a = af.Aufnahme(sd, 16000, 0, streaming=streaming_zaehlend, request_bauen=lambda b: b, on_level=pegel.append,
                log=logs.append, live=False)
a.start()
S_ok = threading.Event()
for _ in range(200):
    if len(a.puffer) >= 5:
        break
    S_ok.wait(0.01)
a.pausieren(); a.fortsetzen()
for _ in range(200):
    if len(a.puffer) >= 8:
        break
    S_ok.wait(0.01)
a.stop(); a.warten()
check("Aufnahme live=False: Puffer gefüllt, Pegel kommt vom Mikrofon", len(a.puffer) >= 8 and len(pegel) >= 8,
      f"{len(a.puffer)} {len(pegel)}")
check("… kein Streaming-Thread, kein Google-Streaming-Aufruf, Warteschlange leer",
      a.stream_thread is None and STREAM_AUFRUFE == [] and a._queue == [] and not a.streaming_aktiv, str(STREAM_AUFRUFE))
check("… Log „kein Streaming gestartet“", any("kein Streaming gestartet" in l for l in logs), str(logs))
check("… Abschnitte (Pause/Weiter) wie bisher", a.abschnitt == 1)

# 3. EXE-Ablauf
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: True
mod.STT_NEUVERSUCH_S = 0.0
mod.NICHT_ERKANNT_DIR = os.path.join(TMP, "nicht_erkannt")
mod._korr.korrigieren = lambda t, key, block="", log=None: t[:1].upper() + t[1:].rstrip(".") + "."
LOG = []
mod.log = lambda *x: LOG.append(" ".join(str(y) for y in x))
NORMAL = "Kniegelenk rechts in 2 Ebenen unauffällig."
mod._llm_aufruf = lambda p: "## Kniegelenk rechts\n\n## Befund\nKleiner Gelenkerguss.\n\n## Ergebnis\nKleiner Gelenkerguss."
CHIRP = {"aufrufe": [], "antworten": []}


def chirp(pcm, sr, loc, token):
    CHIRP["aufrufe"].append(len(pcm))
    an = CHIRP["antworten"]
    return an.pop(0) if an else NORMAL


mod._chirp3_worker = chirp
STREAMS = []


def streaming_stub(requests):
    STREAMS.append(1)
    for n, _r in enumerate(requests, 1):
        if n == 2:
            yield S.Antwort("Knie live", False)
        elif n == 4:
            yield S.Antwort("Knie live rechts", True)


BEFUND = "## Kniegelenk rechts\n\n## Befund\nKein Erguss. Bänder intakt. Knorpel glatt.\n\n## Ergebnis\nUnauffälliger Befund."


def neue_app(benutzer="kp", befund="", insert=0, sel=None, fokus=True, links=""):
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
    CHIRP["aufrufe"].clear(); STREAMS.clear(); LOG.clear()
    mod.speech_client = S.FakeSpeechClient(streaming_stub)
    app = S.baue_app(mod)
    if befund:
        app.result_text.insert("1.0", befund)
    if links:
        app.transcript_text.insert("1.0", links)
    tb = S.FakeTb(app.result_text, insert, sel)
    app.result_text._textbox = tb
    app.focus_get = (lambda: tb) if fokus else (lambda: None)
    app.status_badge = S.FakeWidget()
    app.repariert_label = S.FakeWidget()
    app.nur_text_var = type("V", (), {"get": lambda self: False})()
    if benutzer is not None:
        app._cas = type("A", (), {"nr": "20261124901", "benutzer": benutzer, "leistungen": None, "kontext": None,
                                  "ibl": None, "auftrag_id": "x"})()
        app._cas_aufnahmen, app._cas_hinweise = [], []
        app._cas_hinweise_zeigen = lambda h: setattr(app, "_cas_hinweise", list(h or []))
        app._ibl_befund_leeren = lambda: None
        app._ibl_nach_lauf = lambda e: None
    return app, tb


def puffer(app, n):
    S.pump(app, lambda: len(app._aufnahme.puffer) >= n)


def ende(app, timeout=8):
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)
    S.pump(app, lambda: False, 0.4)
    app._aufnahme_stoppen()


def label(app):
    return app.repariert_label.cfg.get("text", "")


# 3a. kp: Record → Pause → Weiter → INS
app, tb = neue_app("kp")
app.sm_record()
puffer(app, 6)
S.pump(app, lambda: False, 0.2)
check("kp Record: KEIN Google-Streaming gestartet (Log-Zeile für die Abnahme)", STREAMS == [] and not app._live_an
      and any("Live-Anzeige aus für kp" in l for l in LOG) and any("kein Streaming gestartet" in l for l in LOG), LOG[-6:])
check("… links „● Aufnahme läuft“ (rot), kein Diktattext", label(app) == "● Aufnahme läuft"
      and app.repariert_label.cfg.get("text_color") == mod.RECORDING_RED and app.transcript_text.text == "",
      f"{label(app)!r} {app.transcript_text.text!r}")
check("… Pegelbalken läuft (vom Mikrofon)", app.level_indicator.cfg.get("width", 0) > 0, str(app.level_indicator.cfg))
app.sm_record()   # Pause
S.pump(app, lambda: False, 0.3)
check("kp Pause: KEINE Abschnitts-Reparatur (kein chirp_3-Aufruf), links weiter leer, Hinweis „pausiert“",
      CHIRP["aufrufe"] == [] and app.transcript_text.text == "" and "pausiert" in label(app),
      f"{CHIRP['aufrufe']} {app.transcript_text.text!r} {label(app)!r}")
app.sm_record()   # Weiter
puffer(app, 12)
check("kp Weiter: „● Aufnahme läuft“, noch immer kein Streaming", label(app) == "● Aufnahme läuft" and STREAMS == [])
app.sm_ins()
ende(app)
check("kp INS: chirp_3 genau EINMAL über die ganze Aufnahme, Text links, Befund rechts",
      CHIRP["aufrufe"] == [1600 * len(app._aufnahme.puffer)] and app.transcript_text.text == NORMAL
      and app.result_text.text.startswith("## Kniegelenk") and app._status_raw == "KONTROLLE",
      f"{CHIRP['aufrufe']} {app.transcript_text.text!r} {app.result_text.text[:30]!r} {app._status_raw}")
check("… Log „chirp_3 OK“ + Messwert „Text links nach … s ab Stopp (Live-Anzeige aus)“",
      any(l.startswith("[CHIRP3] OK") for l in LOG) and any("Text links nach" in l and "Live-Anzeige aus" in l for l in LOG),
      LOG[-8:])
check("… Statuszeile links nach dem Lauf leer, nichts ins RIS", label(app) == "" and S.AUFZ.tasten == [])

# 3b. rg unverändert: Streaming + Reparatur je Pause
CHIRP["antworten"] = ["Kniegelenk rechts", NORMAL]
app, tb = neue_app("rg")
app.sm_record()
S.pump(app, lambda: "Knie live" in app.transcript_text.text)
check("rg Record: Google-Streaming läuft, Live-Text links", STREAMS and app._live_an
      and "Knie live" in app.transcript_text.text, f"{STREAMS} {app.transcript_text.text!r}")
puffer(app, 6)
app.sm_record()   # Pause
S.pump(app, lambda: app._abschnitte and app._abschnitte[0])
app.sm_record()   # weiter
puffer(app, 12)
check("rg Pause: Abschnitt repariert (chirp_3 je Pause wie bisher)", len(CHIRP["aufrufe"]) == 1
      and app.transcript_text.text == "Kniegelenk rechts" and "repariert" in label(app), f"{CHIRP['aufrufe']} {label(app)!r}")
app.sm_ins()
ende(app)
check("rg INS: Befund wie bisher", app.result_text.text.startswith("## Kniegelenk") and len(CHIRP["aufrufe"]) == 2,
      f"{app.result_text.text[:30]!r} {CHIRP['aufrufe']} {app._status_raw}")

# 3c'. kp: Aufnahme unter 1 s → wie bisher „Kein Text diktiert“ (kein Ausfall, keine rote Zeile)
app, tb = neue_app("kp")
app.sm_record(); puffer(app, 3); app.sm_ins(); ende(app)
check("kp unter 1 s Audio: wie bisher „Kein Text diktiert“, keine rote Zeile, kein chirp_3",
      any("Kein Text" in str(d) for d in S.AUFZ.dialoge) and "nicht verfügbar" not in label(app) and CHIRP["aufrufe"] == [],
      f"{S.AUFZ.dialoge} {label(app)!r}")

# 3c. ohne CAS-Auftrag (Kürzel unbekannt): Live-Anzeige an wie bisher
app, tb = neue_app(None)
app._cas = None
app.toggle_recording()
puffer(app, 6)
check("ohne CAS-Auftrag: Live-Anzeige an (Streaming) wie bisher", STREAMS and app._live_an)
app._aufnahme_stoppen(); app._job.ereignis("reset")

# 3d. Rückfall kp: chirp_3 leer → einmal wiederholt → Text
CHIRP["antworten"] = [None, NORMAL]
app, tb = neue_app("kp")
app.sm_record(); puffer(app, 14); app.sm_ins(); ende(app)
check("kp Rückfall: chirp_3 erst leer → EIN zweiter Versuch über dasselbe Audio → Befund",
      len(CHIRP["aufrufe"]) == 2 and CHIRP["aufrufe"][0] == CHIRP["aufrufe"][1] and app.transcript_text.text == NORMAL
      and app.result_text.text.startswith("## Kniegelenk"), f"{CHIRP['aufrufe']} {app.result_text.text[:30]!r}")
check("… Log nennt die Wiederholung", any("chirp_3 wird einmal wiederholt" in l for l in LOG)
      and any("chirp_3-Wiederholung OK" in l for l in LOG), LOG[-8:])

# 3e. Rückfall kp: beide Versuche leer → rote Zeile, Audio als WAV, kein Befund, links bleibt das bisherige Diktat
CHIRP["antworten"] = [None, ""]
app, tb = neue_app("kp", befund="", links="")
app.sm_record(); puffer(app, 14); app.sm_ins(); ende(app)
wavs = os.listdir(mod.NICHT_ERKANNT_DIR) if os.path.isdir(mod.NICHT_ERKANNT_DIR) else []
check("kp Ausfall: genau 2 chirp_3-Versuche, kein Befund, kein Dialog „Kein Text“",
      len(CHIRP["aufrufe"]) == 2 and app.result_text.text == "" and not any("Kein Text" in str(d) for d in S.AUFZ.dialoge),
      f"{CHIRP['aufrufe']} {S.AUFZ.dialoge}")
check("… nie still leer: rote Zeile „Spracherkennung nicht verfügbar – bitte erneut diktieren/prüfen“, Status Fehler",
      label(app) == "⚠ Spracherkennung nicht verfügbar – bitte erneut diktieren/prüfen"
      and app.repariert_label.cfg.get("text_color") == mod.RECORDING_RED and app._status_raw == "ERROR",
      f"{label(app)!r} {app._status_raw}")
check("… Audio behalten (WAV mit Diktat-Nr.) und in der CAS-Aufnahme", any(w.endswith("_20261124901.wav") for w in wavs)
      and app._cas_aufnahmen and app._cas_pcm(), str(wavs))
check("… Hinweis sichtbar", "Spracherkennung nicht verfügbar" in getattr(app, "_letzter_hinweis", ""))
app.sm_record()
puffer(app, 2)
check("… nächste Aufnahme: rote Zeile weg, „● Aufnahme läuft“", label(app) == "● Aufnahme läuft", label(app))
app._aufnahme_stoppen(); app._job.ereignis("reset")

# 3f. Nachdiktat kp mit Ausfall: bisheriges Diktat bleibt links unverändert stehen
CHIRP["antworten"] = [None, None]
app, tb = neue_app("kp")
app._aufnahme_umschalten("record", "start", basis="Knie rechts bisher.")
puffer(app, 2)
check("kp Nachdiktat: links während der Aufnahme nur das bisherige Diktat", app.transcript_text.text == "Knie rechts bisher."
      and label(app) == "● Aufnahme läuft", repr(app.transcript_text.text))
puffer(app, 14)
app._aufnahme_umschalten("ins", "stop", kontrolle=True)
ende(app)
check("… Ausfall: bisheriges Diktat bleibt, rote Zeile", app.transcript_text.text == "Knie rechts bisher."
      and "Spracherkennung nicht verfügbar" in label(app), f"{app.transcript_text.text!r} {label(app)!r}")

# 4. Rechts diktieren mit kp (Text aus _neuer_text = chirp_3)
mod._llm_aufruf = lambda p: (_ for _ in ()).throw(AssertionError("Befund-KI beim Einfügen gerufen"))
ZUSATZ = "zusätzlich kleiner Gelenkerguss"
pos = BEFUND.index("Bänder")
CHIRP["antworten"] = [ZUSATZ]
app, tb = neue_app("kp", befund=BEFUND, insert=pos, links="Knie rechts unauffällig")
app.sm_record(); puffer(app, 14)
check("kp Cursor im Befund: Status „Ergänzung an Cursor-Stelle“, kein Streaming",
      "Cursor" in app.status_badge.cfg.get("text", "") and STREAMS == [], app.status_badge.cfg.get("text", ""))
app.sm_ins(); ende(app)
check("kp Cursor: Diktat an der Cursor-Stelle eingefügt, Rest Zeichen für Zeichen gleich",
      app.result_text.text == BEFUND[:pos] + "Zusätzlich kleiner Gelenkerguss. " + BEFUND[pos:]
      and app._neuer_text == ZUSATZ and S.AUFZ.tasten == [], repr(app.result_text.text))

MARK = "Bänder intakt."
A = BEFUND.index(MARK)
CHIRP["antworten"] = [ZUSATZ]
app, tb = neue_app("kp", befund=BEFUND, insert=A + len(MARK), sel=(A, A + len(MARK)))
app.sm_record(); puffer(app, 6)
app.sm_record(); S.pump(app, lambda: False, 0.2)      # Pause: keine Reparatur
n_pause = len(CHIRP["aufrufe"])
app.sm_record(); puffer(app, 12)                      # weiter, Markierung bleibt
app.sm_ins(); ende(app)
check("kp Markierung übersprechen (mit Pause): markierter Text ersetzt, Pause ohne chirp_3",
      app.result_text.text == BEFUND.replace(MARK, "Zusätzlich kleiner Gelenkerguss.") and n_pause == 0
      and len(CHIRP["aufrufe"]) == 1, f"{app.result_text.text!r} {CHIRP['aufrufe']}")

CHIRP["antworten"] = [ZUSATZ]
app, tb = neue_app("kp", befund=BEFUND, fokus=False)
app.sm_record(); puffer(app, 14); app.sm_ins(); ende(app)
check("kp Nachdiktat/Ergänzung (Befund steht, kein Cursor): ans Ende des Befundteils, Titel bleibt",
      app.result_text.text.split("\n", 1)[0] == "## Kniegelenk rechts"
      and "Zusätzlich kleiner Gelenkerguss." in app.result_text.text.split("## Ergebnis")[0]
      and app.result_text.text.replace("\nZusätzlich kleiner Gelenkerguss.", "", 1).replace(
          " Zusätzlich kleiner Gelenkerguss.", "", 1) == BEFUND, repr(app.result_text.text))

# 5. Mammo-Maske ohne Live-Anzeige: Feld-Text kommt aus chirp_3 je Feld-Abschnitt (wie bisher); scheitert chirp_3,
# wird einmal wiederholt, sonst Audio behalten + rote Zeile (der bisherige Rückfall „Live-Text des Abschnitts“ fehlt)
import numpy as np  # noqa: E402
FELD = []


class AufnahmeOhneLive:
    live = False

    def samples(self):
        return np.ones(32000, dtype=np.int16)


for antworten, soll, name in (([None, "keine suspekten Herde"], "keine suspekten Herde", "Wiederholung liefert"),
                              ([None, None], "", "beide leer")):
    CHIRP["antworten"] = list(antworten)
    app, tb = neue_app("kp")
    FELD.clear(); CHIRP["aufrufe"].clear()
    app._maske_abschnitt_text = lambda k, text: FELD.append((k, text))
    app._job.ereignis("toggle")
    app._maske_abschnitt_thread(app._job.gen, AufnahmeOhneLive(), 0, 0, 32000)
    S.pump(app, lambda: FELD, 3)
    check(f"Maske kp, chirp_3 je Feld erst leer, {name}: 2 Versuche, Feld bekommt {soll!r}",
          len(CHIRP["aufrufe"]) == 2 and FELD == [(0, soll)], f"{CHIRP['aufrufe']} {FELD}")
    if not soll:
        check("… Maske: rote Zeile + Audio behalten", app._stt_fehler and "nicht verfügbar" in getattr(app, "_letzter_hinweis", ""))
    app._job.ereignis("reset")

print("\n" + ("✅ LIVE-ANZEIGE-AUS PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
