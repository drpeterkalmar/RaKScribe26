"""Gate v3.10.0 (CAS-Auftrag der RaKScribe-Brücke, Peter 12.10.2026: „Digitales Diktat“ ohne SpeechMagic).
Teil 1: source_code/cas_auftrag.py (Abholen, Antworten, Widerruf, Ergebnis, Entscheidung bei zweitem Auftrag).
Teil 2: echter EXE-Ablauf aus RaKScribe.py mit Attrappen (exe_stubs): Auftrag annehmen → F10-Diktat → Befund nur zur
Kontrolle (KEIN Strg+V) → EOL schreibt Befund + Aufnahme als Datei und meldet „fertig“; Testbefund-Knopf; F11/F12 nur mit
Auftrag; zweiter Auftrag (ablehnen/ersetzen), Widerruf, Brücke weg, Abbrechen, Fenster zu, Zwischenablage gesperrt.
Teil 3 (nur am Mac, wenn ~/dev/ris-mods da ist): Protokoll gegen die echte Brückenseite bruecke/auftrag.py.
Synthetische Texte, keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_cas_auftrag.py"""
import json, os, pathlib, sys, tempfile, threading, time, wave, io
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: False   # ein Fremdfenster ist vorne — trotzdem darf mit Auftrag nichts eingefügt werden
cas, js = mod._cas, mod._js
NORMAL = "Kniegelenk rechts in 2 Ebenen unauffällig."
mod._chirp3_worker = lambda pcm, sr, loc, token: NORMAL
mod._llm_aufruf = lambda p: "## Kniegelenk rechts\n\n## Befund\nKleiner Gelenkerguss.\n\n## Ergebnis\nKleiner Gelenkerguss."
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


ORDNER = tempfile.mkdtemp(prefix="rks_cas_")
LEBT = {4242, 5151}


def lebt(pid):
    return pid in LEBT


def ablegen(nr, aid, benutzer="kp", pid=4242, zeit=None, protokoll=1, roh=None):
    p = os.path.join(ORDNER, cas.AUFTRAG)
    with open(p, "w", encoding="utf-8") as f:
        f.write(roh if roh is not None else json.dumps(
            {"protokoll": protokoll, "auftrag_id": aid, "nr": nr, "benutzer": benutzer, "bruecke_pid": pid,
             "zeit": time.time() if zeit is None else zeit, "zeit_text": "", "testbefund": False}))


def antwort(aid):
    try:
        with open(os.path.join(ORDNER, f"cas_antwort_{aid}.json"), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


# ───────────────────────────── Teil 1: Modul ─────────────────────────────
k = cas.Kanal(ORDNER, pid=777, version="3.10.0", prozess_lebt=lebt)
check("leerer Eingang → kein Auftrag", k.abholen() is None)
ablegen("20261013005", "a1")
a = k.abholen()
check("Auftrag abgeholt (Nr, Benutzer, Brücken-PID)", a is not None and (a.nr, a.benutzer, a.bruecke_pid) == ("20261013005", "kp", 4242))
check("Eingang danach leer", not os.path.exists(os.path.join(ORDNER, cas.AUFTRAG)) and k.abholen() is None)
check("Bandtext", a.band_text() == "CAS-Diktat 20261013005 (kp)", a.band_text())
ablegen("20261013006", "alt", zeit=time.time() - 3600)
check("veralteter Auftrag (Brücke längst weg) wird verworfen", k.abholen() is None)
ablegen("20261013006", "p2", protokoll=2)
check("fremde Protokollversion wird verworfen", k.abholen() is None)
ablegen("20261013006", "tot", pid=9999)
check("Auftrag einer beendeten Brücke wird verworfen", k.abholen() is None)
ablegen("", "", roh='{"auftrag_id": "ha')
check("halb geschriebener Auftrag: nicht abgeholt, bleibt für den nächsten Takt",
      k.abholen() is None and os.path.exists(os.path.join(ORDNER, cas.AUFTRAG)))
os.remove(os.path.join(ORDNER, cas.AUFTRAG))
k.antworten(a, "angenommen")
an = antwort("a1")
check("Antwort angenommen (mit PID + Version)", an.get("status") == "angenommen" and an.get("rakscribe_pid") == 777
      and an.get("version") == "3.10.0" and an.get("protokoll") == 1, str(an))
check("kein Widerruf → Auftrag gilt", k.zurueckgezogen(a) is None)
with open(os.path.join(ORDNER, "cas_widerruf_a1.json"), "w", encoding="utf-8") as f:
    json.dump({"auftrag_id": "a1", "grund": "timeout"}, f)
check("Widerruf der Brücke wird erkannt", k.zurueckgezogen(a) == "timeout")
os.remove(os.path.join(ORDNER, "cas_widerruf_a1.json"))
LEBT.discard(4242)
check("Brücke beendet wird erkannt", k.zurueckgezogen(a) == "bruecke_beendet")
LEBT.add(4242)
txt, wav = k.ergebnis_schreiben(a, "## T\n\n## Befund\nX.\n\n## Ergebnis\nY.", b"\x01\x00" * 1600)
an = antwort("a1")
with wave.open(wav, "rb") as w:
    wav_ok = (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 16000, 1600)
check("EOL-Ergebnis: Text + WAV (PCM 16 bit mono 16 kHz), danach „fertig“ mit Dateinamen",
      open(txt, encoding="utf-8").read().startswith("## T") and wav_ok and an.get("status") == "fertig"
      and an.get("text_datei") == txt and an.get("wav_datei") == wav, str(an))
check("Entscheidung ohne offenen Auftrag: annehmen", cas.entscheidung(None, True) == "annehmen")
check("Entscheidung: offener Auftrag ohne Inhalt → ersetzen", cas.entscheidung(a, False) == "ersetzen")
check("Entscheidung: offener Auftrag mit Diktat → ablehnen (nie bei falschem Patienten landen)",
      cas.entscheidung(a, True) == "ablehnen")
for f in os.listdir(ORDNER):
    os.remove(os.path.join(ORDNER, f))


# ───────────────────────────── Teil 2: EXE-Ablauf ─────────────────────────────
def neue_app():
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
    S.CLIPBOARD.gesperrt = False
    S.CLIPBOARD.data = {13: "ALTER INHALT"}
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub(antworten=[("Knie", False), ("Knie rechts", True)] * 3))
    app = S.baue_app(mod)
    app._cas, app._cas_aufnahmen, app._cas_test = None, [], False
    app._cas_kanal = cas.Kanal(ORDNER, pid=777, version="3.10.0", prozess_lebt=lebt)
    app._fensterziel = mod._fz.Fensterziel(None)
    app.destroy = lambda: None
    return app


def bis_ruhe(app, timeout=8):
    ok = S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)
    S.pump(app, lambda: False, 0.3)
    return ok


def ergebnis(nr):
    p = os.path.join(ORDNER, f"cas_ergebnis_{nr}.txt")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


app = neue_app()
app._cas_einmal()
check("ohne Auftrag: nichts passiert, F11/F12 wirkungslos", app._cas is None and app._cas_taste("eol") is None
      and app._cas_taste("ins") is None and S.AUFZ.tasten == [])

# 1. Auftrag annehmen → F10-Diktat → Befund nur zur Kontrolle → EOL schreibt Datei
ablegen("20261013007", "b1")
app._cas_einmal()
check("Auftrag angenommen, Antwort an die Brücke", app._cas is not None and app._cas.nr == "20261013007"
      and antwort("b1").get("status") == "angenommen")
app.toggle_recording()
check("F10 startet die Aufnahme", app._job.zustand == "RECORDING" and app.is_recording)
n0 = 0
S.pump(app, lambda: app._aufnahme is not None and len(app._aufnahme.puffer) >= 15)
app.toggle_recording()
bis_ruhe(app)
check("F10-Stopp mit CAS-Auftrag: Befund rechts zur Kontrolle, KEIN Strg+V, nichts kopiert",
      app.result_text.text.startswith("## Kniegelenk") and app._status_raw == "KONTROLLE" and S.AUFZ.tasten == []
      and S.CLIPBOARD.data.get(13) == "ALTER INHALT", f"{app._status_raw} / {S.AUFZ.tasten}")
check("Aufnahme des Diktats gesammelt", len(app._cas_aufnahmen) == 1 and app._cas_aufnahmen[0] is app._aufnahme)
app.result_text.text += "\nVon Hand ergänzt."
sichtbar = app.result_text.text.strip()
erg = app._cas_taste("eol")
an = antwort("b1")
check("F12 = EOL: Ergebnis-Datei = sichtbarer (geänderter) Befund", erg == "break" and ergebnis("20261013007") == sichtbar,
      repr(ergebnis("20261013007")))
wavp = an.get("wav_datei") or ""
with wave.open(wavp, "rb") as w:
    n_wav = w.getnframes()
check("… mit Aufnahme als WAV (ganze Aufnahme)", n_wav == 1600 * len(app._aufnahme.puffer) > 0, f"{n_wav}")
check("… Antwort „fertig“, kein TEST", an.get("status") == "fertig" and an.get("test") is False, str(an))
check("… KEIN Strg+V, Text zusätzlich in der Zwischenablage, Felder leer, Band weg",
      S.AUFZ.tasten == [] and S.CLIPBOARD.data.get(13) == sichtbar and app.result_text.text == ""
      and app.transcript_text.text == "" and app._cas is None and app._job.zustand == "READY")
check("… Hinweis „An CAS übergeben“", "An CAS übergeben" in getattr(app, "_letzter_hinweis", ""))

# 2. Testbefund-Knopf (Fern-Test ohne Mikrofon)
ablegen("20261013008", "b2")
app._cas_einmal()
app.cas_testbefund()
check("Testbefund rechts, Status „Befund prüfen“", app.result_text.text == cas.TESTBEFUND and app._status_raw == "KONTROLLE")
app.befund_fertig()
an = antwort("b2")
check("EOL: TEST-Text an CAS, Antwort test=true, ohne Aufnahme", ergebnis("20261013008") == cas.TESTBEFUND
      and an.get("test") is True and an.get("wav_datei") is None and app._cas is None, str(an))

# 3. zweiter Auftrag, während der erste Inhalt hat → abgelehnt; ohne Inhalt → ersetzt
ablegen("20261013009", "c1")
app._cas_einmal()
app.cas_testbefund()
ablegen("20261013010", "c2", pid=5151)
app._cas_einmal()
check("zweiter Auftrag bei offenem Diktat → abgelehnt (offen_nr), erster bleibt",
      antwort("c2").get("status") == "abgelehnt" and antwort("c2").get("offen_nr") == "20261013009"
      and app._cas.nr == "20261013009" and "abgelehnt" in getattr(app, "_letzter_hinweis", ""), str(antwort("c2")))
app.reset_dictation()
check("F9 leert das Diktat, der CAS-Auftrag bleibt offen", app._cas is not None and app.result_text.text == "")
ablegen("20261013011", "c3", pid=5151)
app._cas_einmal()
check("neuer Auftrag, erster ohne Inhalt → erster „ersetzt“, neuer aktiv",
      antwort("c1").get("status") == "ersetzt" and app._cas.nr == "20261013011" and antwort("c3").get("status") == "angenommen")

# 4. Widerruf / Brücke beendet → Band weg, Text bleibt
app.cas_testbefund()
with open(os.path.join(ORDNER, "cas_widerruf_c3.json"), "w", encoding="utf-8") as f:
    json.dump({"auftrag_id": "c3", "grund": "timeout"}, f)
app._cas_einmal()
check("Widerruf (Zeitgrenze der Brücke) → Auftrag weg, Text bleibt stehen",
      app._cas is None and app.result_text.text == cas.TESTBEFUND)
app.reset_dictation()
ablegen("20261013012", "d1", pid=5151)
app._cas_einmal()
LEBT.discard(5151)
app._cas_einmal()
check("Brücke beendet → Auftrag weg", app._cas is None)
LEBT.add(5151)

# 5. Abbrechen-Knopf und Fenster schließen → „abgebrochen“
ablegen("20261013013", "e1")
app._cas_einmal()
app.cas_abbrechen()
check("Knopf Abbrechen → abgebrochen (knopf), Band weg", antwort("e1").get("status") == "abgebrochen"
      and antwort("e1").get("grund") == "knopf" and app._cas is None)
ablegen("20261013014", "e2")
app._cas_einmal()
app._schliessen()
check("Fenster schließen mit offenem Auftrag → abgebrochen (fenster_zu)",
      antwort("e2").get("status") == "abgebrochen" and antwort("e2").get("grund") == "fenster_zu")

# 6. Zwischenablage gesperrt → Datei trotzdem geschrieben
app = neue_app()
ablegen("20261013015", "f1")
app._cas_einmal()
app.cas_testbefund()
S.CLIPBOARD.gesperrt = True
app.befund_fertig()
check("Zwischenablage gesperrt: Ergebnis trotzdem an CAS (Datei + fertig), kein Dialog",
      ergebnis("20261013015") == cas.TESTBEFUND and antwort("f1").get("status") == "fertig" and S.AUFZ.dialoge == [],
      str(S.AUFZ.dialoge))
S.CLIPBOARD.gesperrt = False

# 7. schon eingefügter Befund (F10 vor dem Auftrag) gehört zum vorigen Patienten → Felder leer
app = neue_app()
app.result_text.text = "## Alt\n\n## Befund\nVoriger Patient.\n\n## Ergebnis\nAlt."
app._gesendet = True
ablegen("20261013016", "g1")
app._cas_einmal()
check("Auftrag nach schon eingefügtem Befund → Felder leer, nichts vom vorigen Patienten",
      app._cas is not None and app.result_text.text == "")
app.befund_fertig()
check("EOL ohne Befund → Hinweis, nichts an CAS", ergebnis("20261013016") is None
      and "Erst INS" in getattr(app, "_letzter_hinweis", "") and app._cas is not None)

# 8. ohne Auftrag bleibt EOL wie bisher (kopieren, keine CAS-Datei)
app = neue_app()
app.result_text.text = "## Knie\n\n## Befund\nX.\n\n## Ergebnis\nY."
vorher = set(os.listdir(ORDNER))
app.befund_fertig()
check("ohne Auftrag: EOL kopiert wie bisher, schreibt keine CAS-Datei",
      S.CLIPBOARD.data.get(13) == "## Knie\n\n## Befund\nX.\n\n## Ergebnis\nY." and set(os.listdir(ORDNER)) == vorher)

# ───────────────────────────── Teil 3: gegen die echte Brückenseite (nur Mac) ─────────────────────────────
BR = pathlib.Path.home() / "dev" / "ris-mods" / "bruecke"
if (BR / "auftrag.py").exists():
    sys.path.insert(0, str(BR))
    import auftrag as br_auftrag  # noqa: E402
    import importlib
    br = importlib.import_module("bruecke") if (BR / "bruecke.py").exists() else None
    check("Testbefund-Text identisch mit der Brücke", br is None or br.TESTBEFUND == cas.TESTBEFUND)
    o2 = tempfile.mkdtemp(prefix="rks_cas_bruecke_")
    seite = cas.Kanal(o2, pid=888, version="3.10.0", prozess_lebt=lambda pid: True)
    schritte = {"n": 0}

    def rak_schritt():
        schritte["n"] += 1
        a2 = seite.abholen()
        if a2:
            seite.antworten(a2, "angenommen")
            schritte["a"] = a2
        elif schritte.get("a") and schritte["n"] == 4:
            seite.ergebnis_schreiben(schritte["a"], "## B\n\n## Befund\nZ.", b"\x00\x00" * 800, test=True)
    uhr = [time.time()]   # Brückenzeit = echte Zeit, sonst gilt der Auftrag als veraltet
    kanal = br_auftrag.Kanal(o2, jetzt=lambda: uhr[0], schlafen=lambda s: (uhr.__setitem__(0, uhr[0] + s), rak_schritt()), pid=4242)
    aid = kanal.senden("20261013099", "kp")
    r = kanal.warten(aid, 15, 600, rakscribe_lebt=lambda pid: True)
    text, wavb = kanal.ergebnis_holen("20261013099", r.antwort)
    check("Protokoll gegen bruecke/auftrag.py: fertig, Text + WAV kommen an",
          r.status == "fertig" and text == "## B\n\n## Befund\nZ." and wavb[:4] == b"RIFF" and r.antwort.get("test") is True,
          f"{r.status} {r.antwort}")
else:
    print("(Teil 3 übersprungen: ~/dev/ris-mods/bruecke nicht vorhanden)")

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
