"""Gate kaiscribe-senf-anzeige-n1 (Peter 20.11.2026): Opus-Senf als schreibgeschützter Hinweis im KaiScribe-Fenster.
Teil 1: source_code/senf_anzeige.py (Kürzel, Ablage lesen, Anzeige je Status, Nachladen 15 s / max. 10 min, Frist 1 s).
Teil 2: echter EXE-Ablauf (exe_stubs): kp sieht das Feld, rg nicht; Diktat + EOL → Befund, CAS-Datei und Zwischenablage
ohne Senf; KaiScribe kopiert den Senf nie von sich aus, nur auf Knopf/Strg+C (Nachtrag 20.11.: markier-/kopierbar);
das Feld ist kein Einfügeziel; Ablage fehlt/hängt → kein Hänger.
Teil 3 (nur am Mac, wenn ~/dev/ris-mods da ist): echte Ablage-Datei aus opus_senf/vm_senf.py (Format 1.7.0).
Synthetische Texte, keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_senf_anzeige.py"""
import json, os, pathlib, sys, tempfile, threading, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: True      # KaiScribe vorne (Peter hat ins Senf-Feld geklickt)
cas, senf = mod._cas, mod._senf
mod._chirp3_worker = lambda pcm, sr, loc, token: "Kniegelenk rechts in 2 Ebenen unauffällig."
mod._llm_aufruf = lambda p: "## Kniegelenk rechts\n\n## Befund\nKleiner Gelenkerguss.\n\n## Ergebnis\nKleiner Gelenkerguss."
mod._korr.korrigieren = lambda t, key, block="", log=None: t
fails = 0


def check(name, ok, detail=""):
    global fails
    if not ok and "app" in globals() and getattr(globals()["app"], "_senf", None) is not None:
        v = globals()["app"]._senf
        detail = f"{detail} [senf: zustand={v.zustand} lesungen={v.lesungen} frist={v.zeitueberschreitungen}]"
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


SENF_ZEILE = "RH 12 · Knie re · Gelenkerguss, Verdacht auf Chondrokalzinose"
SENF_ZEILE2 = "RH 12 · Knie re · Fabella"

# ───────────────────────────── Teil 1: Modul ─────────────────────────────
check("Kürzel: kp / 'kp, MH' / [kp] / aus / leer / None=Standard",
      senf.kuerzel_liste("kp") == ["kp"] and senf.kuerzel_liste("kp, MH") == ["kp", "mh"]
      and senf.kuerzel_liste("[kp]") == ["kp"] and senf.kuerzel_liste("aus") == [] and senf.kuerzel_liste("") == []
      and senf.kuerzel_liste(None) == ["kp"])
check("nur Kürzel aus der Liste: kp ja (auch KP), rg nein, leer nein, Liste leer → niemand",
      senf.aktiv("kp", ["kp"]) and senf.aktiv("KP ", ["kp"]) and not senf.aktiv("rg", ["kp"])
      and not senf.aktiv("", ["kp"]) and not senf.aktiv("kp", []))
check("Ordner + Zwilling (RaKScribe ↔ KaiScribe), aus → keiner",
      senf.ordner_kandidaten("X:\\RaKScribe\\Daten\\senf") == ["X:\\RaKScribe\\Daten\\senf", "X:\\KaiScribe\\Daten\\senf"]
      and senf.ordner_kandidaten("aus") == [] and senf.ordner_kandidaten("/tmp/s") == ["/tmp/s"])


def ablage(ordner, nr, **d):
    os.makedirs(ordner, exist_ok=True)
    d = {"v": 1, "nr": nr, "zeit": "2026-11-21T10:00:00", "weitere_laufen": False, "eintraege": [], **d}
    with open(os.path.join(ordner, nr + ".json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=True)


A = tempfile.mkdtemp(prefix="rks_senf_")
check("lesen: Ordner fehlt → aus; Nummer unbrauchbar → aus",
      senf.lesen(A + "-fehlt", "20261121001")[0] == "aus" and senf.lesen(A, "../x")[0] == "aus"
      and senf.lesen(A, "")[0] == "aus")
check("lesen: Ordner da, Datei fehlt → fehlt", senf.lesen(A, "20261121001") == ("fehlt", None))
with open(os.path.join(A, "20261121002.json"), "w") as f:
    f.write('{"v": 1, "nr": "2026')
check("lesen: halb geschriebene Datei → fehlt (beim Nachladen wieder)", senf.lesen(A, "20261121002") == ("fehlt", None))
ablage(A, "20261121003", status="fertig", befund="auffaellig", zeilen=[SENF_ZEILE])
art, d = senf.lesen(A, "20261121003")
check("lesen: Datei da → da + Inhalt", art == "da" and d["zeilen"] == [SENF_ZEILE])
vorher = sorted(os.listdir(A)), os.path.getmtime(os.path.join(A, "20261121003.json"))
senf.lesen(A, "20261121003")
check("lesen schreibt/löscht nichts in der Ablage",
      (sorted(os.listdir(A)), os.path.getmtime(os.path.join(A, "20261121003.json"))) == vorher)

T = senf.anzeige
check("Anzeige laeuft → „Senf läuft…“", T({"status": "laeuft"}) == ("laeuft", "Senf läuft…"))
check("Anzeige unauffällig → „Senf: unauffällig“",
      T({"status": "fertig", "befund": "unauffaellig", "zeilen": ["RH 5 · Knie · unauffällig"]})
      == ("fertig", "Senf: unauffällig"))
check("Anzeige auffällig → die Zeile(n)",
      T({"status": "fertig", "befund": "auffaellig", "zeilen": [SENF_ZEILE, SENF_ZEILE2]})
      == ("fertig", SENF_ZEILE + "\n" + SENF_ZEILE2))
check("Anzeige fehler / uebersprungen → „Senf: kein Ergebnis“",
      T({"status": "fehler"}) == ("kein", "Senf: kein Ergebnis")
      and T({"status": "uebersprungen"}) == ("kein", "Senf: kein Ergebnis"))
check("Anzeige nicht beurteilbar + weitere Serie läuft",
      T({"status": "fertig", "befund": "nicht_beurteilbar", "zeilen": ["RH 3 · HWS · Bild unscharf"],
         "weitere_laufen": True}) == ("fertig", "Senf: nicht beurteilbar\nRH 3 · HWS · Bild unscharf\n"
                                                "(weitere Serie läuft…)"))


def sofort(ziel):          # Lese-„Thread“, der sofort fertig ist (Takt-Logik ohne Zeitverhalten)
    ziel()


class Lese:
    def __init__(self, *antworten):
        self.antworten, self.n = list(antworten), 0

    def __call__(self, ordner, nr):
        self.n += 1
        return self.antworten.pop(0) if len(self.antworten) > 1 else self.antworten[0]


def lauf(v, t0=1000.0, schritte=200):
    """Takte bis Ende; liefert [(zeit, anzeige)] und die Endzeit (weiter_ms als Zeitfortschritt)."""
    t, out = t0, []
    for _ in range(schritte):
        a, w = v.takt(t)
        if a is not None:
            out.append((round(t - t0, 1), a))
        if w is None:
            return out, t - t0
        t += w / 1000.0
    return out, None


v = senf.Verfolgung("a", "20261121003", A, 1000.0, lese=Lese(("da", {"status": "fertig", "befund": "auffaellig",
                                                                   "zeilen": [SENF_ZEILE]})), starte=sofort)
out, ende = lauf(v)
check("Verfolgung: Ergebnis gleich da → Zeile, fertig (kein Nachladen)",
      out == [(0, ("fertig", SENF_ZEILE))] and ende == 0, (out, ende))
le = Lese(("fehlt", None), ("da", {"status": "laeuft"}), ("da", {"status": "laeuft"}),
          ("da", {"status": "fertig", "befund": "unauffaellig", "zeilen": []}))
v = senf.Verfolgung("a", "20261121004", A, 1000.0, lese=le, starte=sofort)
out, ende = lauf(v)
check("Verfolgung: keine Datei → „läuft“, alle 15 s nachladen, Ergebnis eingeblendet, dann Schluss",
      out == [(0, ("laeuft", "Senf läuft…")), (45.0, ("fertig", "Senf: unauffällig"))] and ende == 45.0 and le.n == 4,
      (out, ende, le.n))
le = Lese(("da", {"status": "laeuft"}))
v = senf.Verfolgung("a", "20261121005", A, 1000.0, lese=le, starte=sofort)
out, ende = lauf(v)
check("Verfolgung: läuft länger als 10 min → aufhören, „Senf: kein Ergebnis“, höchstens 41 Lesungen",
      out[0] == (0, ("laeuft", "Senf läuft…")) and out[-1][1] == ("kein", "Senf: kein Ergebnis")
      and ende is not None and ende <= 600 and le.n <= 41, (out, ende, le.n))
le = Lese(("aus", None))
v = senf.Verfolgung("a", "20261121006", A, 1000.0, lese=le, starte=sofort)
out, ende = lauf(v)
check("Verfolgung: keine Ablage/kein Laufwerk → Feld aus, sofort Schluss", out == [(0, ("aus", ""))] and ende == 0
      and le.n == 1, (out, ende, le.n))
v = senf.Verfolgung("a", "20261121007", A, 1000.0, lese=Lese(("da", {"status": "fehler"})), starte=sofort)
check("Verfolgung: fehler → „kein Ergebnis“, Schluss", lauf(v) == ([(0, ("kein", "Senf: kein Ergebnis"))], 0))

# hängendes Netz: Thread kommt nie zurück → nach 1 s Feld aus, kein zweiter Thread, solange er hängt
gestartet = []
v = senf.Verfolgung("a", "20261121008", A, 1000.0, lese=Lese(("da", {})), starte=lambda z: gestartet.append(z))
a1 = v.takt(1000.0)
a2 = v.takt(1000.5)
a3 = v.takt(1001.2)
a4 = v.takt(1016.2)
check("Frist 1 s: Lesen hängt → erst warten (100 ms), dann Feld aus, Nachladen in 15 s",
      a1 == (None, senf.PRUEF_MS) and a2 == (None, senf.PRUEF_MS) and a3 == (("aus", ""), 15000), (a1, a2, a3))
check("… hängt der erste Versuch noch, startet kein zweiter (kein Thread-Stau)", len(gestartet) == 1 and a4[1] == 15000,
      (len(gestartet), a4))
gestartet[0]()                         # Netz wieder da: der alte Thread kommt zurück (Ergebnis verworfen)
v.takt(1031.2)
check("… danach wird neu gelesen", len(gestartet) == 2)

# echt nebenläufig: lesen dauert 3 s → takt() kehrt sofort zurück (Diktieren nie verzögert)
halt = threading.Event()


def langsam(o, n):
    halt.wait(3)
    return "fehlt", None


v = senf.Verfolgung("a", "20261121009", A, time.time(), lese=langsam)
t0 = time.time()
r = [v.takt(time.time()) for _ in range(5)]
dauer = time.time() - t0
check("takt() blockiert nie (5 Takte bei hängendem Lesen < 50 ms)", dauer < 0.05 and r[0] == (None, senf.PRUEF_MS),
      (dauer, r[0]))
time.sleep(1.1)
check("… nach 1 s Frist: Feld aus", v.takt(time.time())[0] == ("aus", ""))
halt.set()

# ───────────────────────────── Teil 2: EXE-Ablauf ─────────────────────────────
ORDNER = tempfile.mkdtemp(prefix="rks_cas_senf_")
SENF = os.path.join(tempfile.mkdtemp(prefix="rks_senfablage_"), "senf")
mod.CFG.senf_ordner = SENF
mod.CFG.senf_anzeige = ["kp"]
mod.CFG.lauf_ordner = os.path.join(tempfile.mkdtemp(prefix="rks_laeufe_"), "laeufe")


class FakeSenfTb:
    """tk.Text im Senf-Feld: Bindungen, Markierung, Fokus."""
    def __init__(self, box):
        self.box, self.binds, self.cfg, self.sel, self.fokus = box, {}, {}, None, False

    def configure(self, **k):
        self.cfg.update(k)

    def bind(self, seq, fn, add=None):
        self.binds[seq] = fn

    def focus_set(self):
        self.fokus = True

    def tag_ranges(self, tag):
        return ("a", "b") if tag == "sel" and self.sel else ()

    def tag_add(self, tag, a, b):
        if tag == "sel":
            self.sel = (0, len(self.box.text))

    def get(self, a, b):
        return self.box.text[self.sel[0]:self.sel[1]]


class FakeSenfBox(S.FakeWidget):
    """CTkTextbox: im Zustand disabled verwirft insert/delete (wie Tk)."""
    def __init__(self):
        super().__init__()
        self.text, self.cfg["state"] = "", "normal"
        self._textbox = FakeSenfTb(self)

    def insert(self, pos, t):
        if self.cfg.get("state") == "normal":
            self.text += t

    def delete(self, a, b=None):
        if self.cfg.get("state") == "normal":
            self.text = ""

    def get(self, a, b=None):
        return self.text


class Zeile(S.FakeWidget):
    def __init__(self):
        super().__init__()
        self.sichtbar = False

    def pack(self, *a, **k):
        self.sichtbar = True

    def pack_forget(self):
        self.sichtbar = False

    def winfo_ismapped(self):
        return self.sichtbar


def ablegen(nr, aid, benutzer="kp"):
    with open(os.path.join(ORDNER, cas.AUFTRAG), "w", encoding="utf-8") as f:
        json.dump({"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": benutzer, "bruecke_pid": 4242,
                   "zeit": time.time(), "zeit_text": "", "testbefund": False}, f)


def antwort(aid):
    try:
        with open(os.path.join(ORDNER, f"cas_antwort_{aid}.json"), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


def ergebnis(nr):
    p = os.path.join(ORDNER, f"cas_ergebnis_{nr}.txt")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def neue_app():
    S.AUFZ.tasten.clear()
    S.CLIPBOARD.gesperrt = False
    S.CLIPBOARD.data = {13: "ALTER INHALT"}
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub(antworten=[("Knie", False), ("Knie rechts", True)] * 3))
    app = S.baue_app(mod)
    # Nachladen nach 15 s nicht sofort (pump() kennt keine Zeit) → eigene Liste, nachladen(app) spielt sie ab
    app._spaet = []
    # 100-ms-Takt: kurz warten wie die Tk-Hauptschleife – pump() würde sonst ohne Pause kreisen und den Lese-Thread
    # aushungern (GIL), was es im echten Fenster nicht gibt
    def after(ms, fn=None, *a):
        if ms == senf.PRUEF_MS:
            time.sleep(0.005)
        (app._spaet if ms == senf.NACHLADEN_S * 1000 else app._queue).append((fn, a))
    app.after = after
    app._cas, app._cas_aufnahmen, app._cas_test = None, [], False
    app._cas_kanal = cas.Kanal(ORDNER, pid=777, version="3.20.6", prozess_lebt=lambda pid: True)
    app._fensterziel = mod._fz.Fensterziel(None)
    app.destroy = lambda: None
    app.cas_band, app.cas_label, app.main_container = Zeile(), S.FakeWidget(), S.FakeWidget()
    app.senf_zeile, app.senf_box = Zeile(), FakeSenfBox()
    app._senf_box_einrichten()
    app.focus_get = lambda: app.senf_box._textbox     # Peter hat ins Senf-Feld geklickt
    return app


def nachladen(app):
    """15 s sind um: die vorgemerkten Senf-Takte laufen."""
    app._queue.extend(app._spaet)
    app._spaet.clear()


def bis_ruhe(app, timeout=8):
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)
    S.pump(app, lambda: False, 0.3)


app = neue_app()
tb = app.senf_box._textbox
check("Feld eingerichtet: schreibgeschützt (disabled), Tab springt nicht hinein",
      tb.cfg.get("state") == "disabled" and tb.cfg.get("takefocus") == 0, tb.cfg)
check("Feld ist kein Einfügeziel: Einfügen/Ausschneiden/Löschen per Taste wirkungslos (break)",
      all(tb.binds[k](None) == "break" for k in ("<<Paste>>", "<<Cut>>", "<<Clear>>", "<Control-v>", "<Control-x>")))
check("Klick ins Feld gibt ihm den Fokus (für Strg+A/Strg+C)", tb.binds["<Button-1>"](None) is None and tb.fokus)

# kp, auffällig
ablage(SENF, "20261121011", status="fertig", befund="auffaellig", zeilen=[SENF_ZEILE, SENF_ZEILE2])
ablegen("20261121011", "s1")
app._cas_einmal()
S.pump(app, lambda: app.senf_zeile.sichtbar, 3)
check("kp öffnet Diktat → Senf-Feld sichtbar mit den Zeilen, Band bleibt",
      app._cas is not None and app.senf_zeile.sichtbar and app.senf_box.text == SENF_ZEILE + "\n" + SENF_ZEILE2
      and app.senf_box.cget("state") == "disabled", (app.senf_zeile.sichtbar, app.senf_box.text))
check("Senf nicht im Diktat- oder Befundfeld, Zwischenablage unberührt",
      SENF_ZEILE not in app.transcript_text.text and SENF_ZEILE not in app.result_text.text
      and S.CLIPBOARD.data.get(13) == "ALTER INHALT", (app.transcript_text.text, S.CLIPBOARD.data))
check("Fokus springt beim Laden nicht ins Feld", not FakeSenfTb(app.senf_box).fokus)

# Diktat mit Fokus im Senf-Feld → Text landet im Befund, nie im Senf-Feld
app.toggle_recording()
S.pump(app, lambda: app._aufnahme is not None and len(app._aufnahme.puffer) >= 15)
app.toggle_recording()
bis_ruhe(app)
check("Diktat (Fokus im Senf-Feld): Befund rechts, Senf-Feld unverändert, Befund ohne Senf",
      app.result_text.text.startswith("## Kniegelenk") and app.senf_box.text == SENF_ZEILE + "\n" + SENF_ZEILE2
      and "RH 12" not in app.result_text.text and "RH 12" not in app.transcript_text.text,
      (app.result_text.text[:60], app.senf_box.text))
check("… und nichts davon in der Zwischenablage", S.CLIPBOARD.data.get(13) == "ALTER INHALT", S.CLIPBOARD.data)
befund = app.result_text.text.strip()
app.befund_fertig()                       # EOL
erg = ergebnis("20261121011") or ""
check("EOL: CAS-Ergebnis = Befund, KEINE Senf-Zeile darin", erg == befund and "RH 12" not in erg
      and "Senf" not in erg and "Fabella" not in erg, repr(erg[:200]))
an = antwort("s1")
check("EOL: Antwort/Nachvollzug an die Brücke ohne Senf", an.get("status") == "fertig"
      and "RH 12" not in json.dumps(an, ensure_ascii=False), str(an)[:300])
laeufe = mod.CFG.lauf_ordner
lauf_text = "".join(open(os.path.join(laeufe, n), encoding="utf-8").read() for n in os.listdir(laeufe)) \
    if os.path.isdir(laeufe) else ""
check("Lauf-Datei ohne Senf", lauf_text and "RH 12" not in lauf_text, lauf_text[:100])
check("EOL-Zwischenablage = Befund, ohne Senf", S.CLIPBOARD.data.get(13) == befund and "RH 12" not in befund)
check("nach EOL: Auftrag zu, Senf-Feld weg", app._cas is None and not app.senf_zeile.sichtbar)

# Kopieren nur auf Peters Aktion
app = neue_app()
ablage(SENF, "20261121012", status="fertig", befund="auffaellig", zeilen=[SENF_ZEILE, SENF_ZEILE2])
ablegen("20261121012", "s2")
app._cas_einmal()
S.pump(app, lambda: app.senf_zeile.sichtbar, 3)
app.cas_testbefund()
app.copy_formatted_report(aus_knopf=True)     # „Befund kopieren“
check("„Befund kopieren“ kopiert den Befund, nie den Senf", "RH 12" not in (S.CLIPBOARD.data.get(13) or "")
      and S.CLIPBOARD.data.get(13) == cas.TESTBEFUND.strip(), S.CLIPBOARD.data)
tb = app.senf_box._textbox
tb.binds["<Control-a>"](None)
tb.binds["<Control-c>"](None)
check("Strg+A + Strg+C im Senf-Feld → ganzer Senf in der Zwischenablage (Nachtrag 20.11.)",
      S.CLIPBOARD.data.get(13) == SENF_ZEILE + "\n" + SENF_ZEILE2, S.CLIPBOARD.data)
tb.sel = (0, len(SENF_ZEILE))
r = tb.binds["<Control-c>"](None)
check("Markierung + Strg+C → nur die markierte Zeile, Tk-Standard unterdrückt (break)",
      S.CLIPBOARD.data.get(13) == SENF_ZEILE and r == "break", S.CLIPBOARD.data)
tb.sel = None
S.CLIPBOARD.data = {13: "x"}
check("Knopf „Kopieren“ → ganzer Senf, Hinweis „Senf kopiert“",
      app.senf_kopieren(aus_knopf=True) and S.CLIPBOARD.data.get(13) == SENF_ZEILE + "\n" + SENF_ZEILE2
      and getattr(app, "_letzter_hinweis", "") == "Senf kopiert")
check("Kopieren ändert das Feld nicht, Befundfeld ohne Senf",
      app.senf_box.text == SENF_ZEILE + "\n" + SENF_ZEILE2 and "RH 12" not in app.result_text.text)
S.CLIPBOARD.gesperrt = True
check("Zwischenablage gesperrt → False + Hinweis, kein Absturz",
      app.senf_kopieren(aus_knopf=True) is False and "gesperrt" in app._letzter_hinweis)
S.CLIPBOARD.gesperrt = False
app.befund_fertig()
check("EOL nach Kopieren: CAS-Ergebnis ohne Senf", "RH 12" not in (ergebnis("20261121012") or "RH 12"))

# rg sieht nichts
app = neue_app()
ablage(SENF, "20261121013", status="fertig", befund="auffaellig", zeilen=[SENF_ZEILE])
ablegen("20261121013", "s3", benutzer="rg")
app._cas_einmal()
S.pump(app, lambda: False, 0.3)
check("rg öffnet Diktat (Senf liegt vor) → kein Feld, kein Lesen", app._cas is not None and not app.senf_zeile.sichtbar
      and app.senf_box.text == "" and getattr(app, "_senf", None) is None)
app._cas_beenden()
mod.CFG.senf_anzeige = []
ablegen("20261121013", "s3b", benutzer="kp")
app._cas_einmal()
S.pump(app, lambda: False, 0.3)
check("SENF_ANZEIGE = aus → auch kp sieht nichts", app._cas is not None and not app.senf_zeile.sichtbar)
app._cas_beenden()
mod.CFG.senf_anzeige = ["kp"]

# Status je Fall im echten Ablauf
for nr, d, soll in (("20261121014", {"status": "fertig", "befund": "unauffaellig", "zeilen": ["RH 1 · Knie · unauffällig"]},
                     "Senf: unauffällig"),
                    ("20261121015", {"status": "uebersprungen"}, "Senf: kein Ergebnis"),
                    ("20261121016", {"status": "fehler", "grund": "zeit"}, "Senf: kein Ergebnis"),
                    ("20261121017", {"status": "laeuft"}, "Senf läuft…"),
                    ("20261121018", None, "Senf läuft…")):
    app = neue_app()
    if d is not None:
        ablage(SENF, nr, **d)
    ablegen(nr, "st" + nr[-2:])
    app._cas_einmal()
    S.pump(app, lambda: app.senf_box.text == soll, 3)
    check(f"Status {(d or {}).get('status', 'keine Datei')} → „{soll}“", app.senf_zeile.sichtbar
          and app.senf_box.text == soll, app.senf_box.text)
    if nr == "20261121018":
        ablage(SENF, nr, status="fertig", befund="auffaellig", zeilen=[SENF_ZEILE])
        S.pump(app, lambda: False, 0.2)
        check("… vor Ablauf der 15 s bleibt „läuft“ stehen (kein Dauerlesen)", app.senf_box.text == "Senf läuft…"
              and len(app._spaet) == 1, (app.senf_box.text, len(app._spaet)))
        nachladen(app)
        S.pump(app, lambda: app.senf_box.text == SENF_ZEILE, 3)
        check("… Ergebnis kommt nach → wird eingeblendet", app.senf_box.text == SENF_ZEILE, app.senf_box.text)
    app._cas_beenden()
    check("… Auftrag zu → Feld weg, keine Verfolgung mehr", not app.senf_zeile.sichtbar and app._senf is None)
    S.pump(app, lambda: False, 0.1)

# Ablage fehlt / hängt → kein Hänger
mod.CFG.senf_ordner = SENF + "-gibt-es-nicht"
app = neue_app()
ablegen("20261121019", "s9")
t0 = time.time()
app._cas_einmal()
S.pump(app, lambda: False, 0.3)
check("Ablage fehlt → Feld aus, Auftrag normal angenommen, Diktat startbar",
      app._cas is not None and not app.senf_zeile.sichtbar and antwort("s9").get("status") == "angenommen")
app.toggle_recording()
check("… F10 startet sofort", app._job.zustand == "RECORDING")
app.reset_dictation()
S.pump(app, lambda: False, 0.2)
app._cas_beenden()

mod.CFG.senf_ordner = SENF
haengt = threading.Event()
echt = senf.lesen
senf.lesen = lambda o, n, **k: (haengt.wait(5), ("fehlt", None))[1]
alt_init = senf.Verfolgung.__init__   # lese=lesen ist zur Definitionszeit gebunden → Klasse patchen


def init_haengt(self, *a, **k):
    k["lese"] = senf.lesen
    alt_init(self, *a, **k)


senf.Verfolgung.__init__ = init_haengt
app = neue_app()
ablegen("20261121020", "s10")
t0 = time.time()
app._cas_einmal()
annahme = time.time() - t0
app.toggle_recording()
check("Netz hängt beim Lesen → Annahme + F10 trotzdem sofort (< 0,3 s)",
      annahme < 0.3 and app._job.zustand == "RECORDING", (annahme, app._job.zustand))
app.reset_dictation()
S.pump(app, lambda: app._senf is not None and app._senf.zeitueberschreitungen >= 1, 3)
check("… und Nachladen erst in 15 s (vorgemerkt)", len(app._spaet) == 1, len(app._spaet))
check("… nach 1 s Frist: Feld aus (kein „läuft“ ohne Netz)", not app.senf_zeile.sichtbar
      and app._senf.zeitueberschreitungen >= 1)
haengt.set()
senf.Verfolgung.__init__, senf.lesen = alt_init, echt
app._cas_beenden()

# Band wird nach dem Senf neu gepackt → Senf-Zeile bleibt darunter (Reihenfolge)
app = neue_app()
reihe = []
app.cas_band.pack = lambda *a, **k: (reihe.append(("band", k)), setattr(app.cas_band, "sichtbar", True))
app.senf_zeile.pack = lambda *a, **k: (reihe.append(("senf", k)), setattr(app.senf_zeile, "sichtbar", True))
app.cas_band.winfo_ismapped = lambda: True
ablage(SENF, "20261121021", status="fertig", befund="unauffaellig", zeilen=[])
ablegen("20261121021", "s11")
app._cas_einmal()
S.pump(app, lambda: app.senf_zeile.sichtbar, 3)
reihe.clear()
app._cas_band_zeigen()
check("Band neu gezeigt (Leistungen kommen nach) → Senf-Zeile direkt danach wieder unter das Band",
      [r[0] for r in reihe] == ["band", "senf"] and reihe[-1][1].get("after") is app.cas_band, reihe)
app._cas_beenden()

# config.ini
import config as _c  # noqa: E402
d = tempfile.mkdtemp(prefix="rks_cfg_senf_")
for inhalt, soll_k, soll_o in (("", ["kp"], "X:\\RaKScribe\\Daten\\senf"),
                               ("SENF_ANZEIGE = kp, mh\nSENF_ORDNER = \\\\casmed\\x\\senf\n", ["kp", "mh"],
                                "\\\\casmed\\x\\senf"),
                               ("SENF_ANZEIGE = aus\n", [], "X:\\RaKScribe\\Daten\\senf")):
    p = os.path.join(d, "config.ini")
    with open(p, "w", encoding="utf-8") as f:
        f.write("[SETTINGS]\n" + inhalt)
    c = _c.load_config(p)
    check(f"config.ini {inhalt.strip()[:30]!r} → {soll_k}", c.senf_anzeige == soll_k and c.senf_ordner == soll_o,
          (c.senf_anzeige, c.senf_ordner))

# Quelle: nur senf_kopieren() fasst mit dem Senf die Zwischenablage an; Senf-Text wird nie in Befund/Diktat geschrieben
q = (S.ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
a = q.index("def _senf_box_einrichten")
b = q.index("def _band_hoehe")
block = q[a:b]
check("Senf-Block schreibt nie in result_text/transcript_text und ruft nur in senf_kopieren die Zwischenablage",
      "result_text" not in block and "transcript_text" not in block and block.count("zwischenablage_setzen") == 1
      and "clipboard_set" not in block and "_strg_v" not in block)
aufrufe = [z.strip() for z in q.splitlines() if "senf_kopieren(" in z and "def senf_kopieren" not in z
           and not z.strip().startswith("#")]
check("senf_kopieren nur vom Knopf und von Strg+C im Feld aufgerufen", len(aufrufe) == 2
      and all("aus_knopf=True" in z or "<Control-c>" in z or "self.senf_kopieren(), \"break\"" in z for z in aufrufe),
      aufrufe)

# ───────────────────────────── Teil 3: echtes Format aus ris-mods ─────────────────────────────
RIS = pathlib.Path.home() / "dev" / "ris-mods" / "opus_senf"
if (RIS / "vm_senf.py").exists():
    import subprocess
    vm = tempfile.mkdtemp(prefix="rks_vm_")
    code = ("import sys, pathlib; sys.path.insert(0, %r); import vm_senf as v; b = pathlib.Path(%r); "
            "a = v.Ablage(b, ziele=[]); "
            "a.eintragen('20261121031', 'f_0123456789ab', 'laeuft', art='rf'); "
            "a.eintragen('20261121031', 'f_0123456789ab', 'fertig', ['RH 7 · Knie · Erguss'], 'auffaellig', art='rf')") % (str(RIS), vm)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    dateien = [p for p in pathlib.Path(vm).rglob("20261121031.json")]
    if r.returncode == 0 and dateien:
        art, d = senf.lesen(str(dateien[0].parent), "20261121031")
        check("Teil 3: echte Ablage-Datei von vm_senf.Ablage → „RH 7 · Knie · Erguss“",
              art == "da" and senf.anzeige(d) == ("fertig", "RH 7 · Knie · Erguss"), (art, d))
    else:
        print("(Teil 3 übersprungen: vm_senf.Ablage hier nicht aufrufbar –", (r.stderr or "").strip()[-200:], ")")
else:
    print("(Teil 3 übersprungen: ~/dev/ris-mods fehlt)")

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
