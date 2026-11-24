"""Gate kaiscribe-sammel-2311 (Peter 23.11.2026, Videos „funzt ned“): markierter Text im rechten Befundfeld wird durch
das Diktat ERSETZT – mit SpeechMike RECORD, beim Weiter-Diktieren (gleiche Aufnahme) und nach einem Klick, der eine neue
Markierung setzt. Belege CASWS10 (rakscribe.log 23.11.):
  RH 156  17:35:13 Markierung beim Start erkannt, 17:35:34 PLAY in der Pause → „sel“ weg, Cursor am Markierungsende
          (615, 615) → eingefügt statt ersetzt.
  RH 165  17:24:20 in der Pause markiert (35 Zeichen), danach bis 17:27:03 Text der Markierung verändert → nur noch 2
          Zeichen zwischen den Marken → eingefügt statt ersetzt.
Nur ein echter Einzelklick ohne Auswahl fügt an der Cursor-Stelle ein. Ganz neue Aufnahme / IB-Lab-Gerüst überschreiben
die Markierung nicht. Synthetische Texte, keine Patientendaten.  Aufruf: python tests/offline/test_markierung.py"""
import pathlib, sys
HIER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import exe_stubs as S  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: True
mod.messagebox.askyesno = lambda *a, **k: (_ for _ in ()).throw(AssertionError("Rückfrage beim Ersetzen der Markierung"))
mod._korr.korrigieren = lambda t, key, block="", log=None: "Zusätzlich kleiner Gelenkerguss."
mod._llm_aufruf = lambda p: (_ for _ in ()).throw(AssertionError("Befund-KI beim Ersetzen gerufen"))
LOG = []
mod.log = lambda *a: LOG.append(" ".join(str(x) for x in a))

BEFUND = "## Kniegelenk rechts\n\n## Befund\nKein Erguss. Bänder intakt. Knorpel glatt.\n\n## Ergebnis\nUnauffälliger Befund."
MARK = "Bänder intakt."
A = BEFUND.index(MARK)
SOLL = BEFUND.replace(MARK, "Zusätzlich kleiner Gelenkerguss.")


# 1. markierung_stelle (rein)
f = mod.markierung_stelle
check("Stelle: Text an den Marken unverändert → gleich", f(BEFUND, A, A + len(MARK), MARK) == (A, A + len(MARK), "gleich"))
check("Stelle: Feld neu geschrieben (verschoben) → nächstes wörtliches Vorkommen",
      f("XX" + BEFUND, A, A + len(MARK), MARK) == (A + 2, A + 2 + len(MARK), "wiedergefunden"))
check("Stelle: markierter Text geändert → Stelle der Marken bleibt, art veraendert",
      f(BEFUND.replace(MARK, "ab"), A, A + 2, MARK) == (A, A + 2, "veraendert"))
check("Stelle: Cursor ohne Markierung", f(BEFUND, 5, 5, "") == (5, 5, "stelle"))
zwei = "Kein Erguss. Kein Erguss."
check("Stelle: zwei gleiche Vorkommen → das an den Marken", f(zwei, 13, 25, "Kein Erguss.") == (13, 25, "gleich")
      and f(zwei, 14, 20, "Kein Erguss.")[:2] == (13, 25))


def neue_app(text=BEFUND, insert=0, sel=None, fokus=True):
    S.AUFZ.tasten.clear()
    mod._chirp3_worker = lambda pcm, sr, loc, token: "zusätzlich kleiner Gelenkerguss"
    mod.speech_client = S.FakeSpeechClient(S.streaming_stub())
    app = S.baue_app(mod)
    app.result_text.insert("1.0", text)
    tb = S.FakeTb(app.result_text, insert, sel)
    app.result_text._textbox = tb
    zustand = {"fokus": tb if fokus else None}
    app.focus_get = lambda: zustand["fokus"]
    app.status_badge = S.FakeWidget()
    app.repariert_label = S.FakeWidget()
    app.nur_text_var = type("V", (), {"get": lambda self: False})()
    return app, tb, zustand


def warten_bis_ende(app):
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
    S.pump(app, lambda: False, 0.5)
    app._aufnahme_stoppen()


def status(app):
    return app.status_badge.cfg.get("text", "")


# 2. RH 156: markiert → RECORD → Pause → PLAY (Auswahl weg, Cursor am Markierungsende, kein Klick) → RECORD → INS
LOG.clear()
app, tb, z = neue_app(insert=A + len(MARK), sel=(A, A + len(MARK)))
app.sm_record()
check("RH 156: Start mit Markierung → Status „Ersetzt markierten Text (14 Zeichen)“",
      f"Ersetzt markierten Text ({len(MARK)} Zeichen) · Aufnahme läuft" in status(app), status(app))
check("… Log nennt die Markierung (keine Ergänzung)", any("Ersetzt markierten Text (14 Zeichen)" in l for l in LOG), LOG[-5:])
S.pump(app, lambda: len(app._aufnahme.puffer) >= 6)
app.sm_record()                                       # Pause
S.pump(app, lambda: False, 0.2)
check("… Pause zeigt weiter „Ersetzt markierten Text“", "Ersetzt markierten Text (14 Zeichen) · Pause" in status(app), status(app))
tb.sel = None                                         # PLAY / Fokuswechsel: Auswahl weg, Cursor am Ende
tb.marks["insert"] = A + len(MARK)
z["fokus"] = None
app.sm_record()                                       # weiter
check("… Weiter diktieren: Markierung bleibt (kein „In der Pause geklickt“)",
      app._einfuegen_ziel == (A, A + len(MARK)) and not any("In der Pause in den Befund geklickt" in l for l in LOG)
      and any("Markierung (14 Zeichen) bleibt" in l for l in LOG), f"{app._einfuegen_ziel} {LOG[-4:]}")
S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
app.sm_ins()
warten_bis_ende(app)
check("… INS: markierter Text ERSETZT, Rest Zeichen für Zeichen gleich, nichts ins RIS",
      app.result_text.text == SOLL and S.AUFZ.tasten == [], repr(app.result_text.text))
check("… Hinweis „Markierten Text ersetzt (14 Zeichen)“, Ziel verbraucht",
      app._letzter_hinweis.startswith("Markierten Text ersetzt (14 Zeichen)") and app._einfuegen_ziel is None
      and app._ziel_text == "", app._letzter_hinweis)

# 3. RH 165: Start ohne Ziel (Fokus woanders) → Pause → markieren → weiter → Pause → Auswahl weg (EOL/Knöpfe) → weiter → INS
LOG.clear()
app, tb, z = neue_app(insert=0, fokus=False)
app.sm_record()
check("RH 165: Start ohne Markierung/Fokus → Ergänzung (kein Ziel)", app._einfuegen_ziel is None
      and "Ergänzung · Aufnahme läuft" in status(app), status(app))
S.pump(app, lambda: len(app._aufnahme.puffer) >= 6)
app.sm_record()                                       # Pause
tb.sel = (A, A + len(MARK))                           # in der Pause markiert (Maus)
tb.marks["insert"] = A + len(MARK)
z["fokus"] = tb
app._markierung_merken()                              # <<Selection>>
app.sm_record()                                       # weiter
check("… weiter: neue Markierung gilt (Status „Ersetzt markierten Text“)", app._einfuegen_ziel == (A, A + len(MARK))
      and "Ersetzt markierten Text (14 Zeichen) · Aufnahme läuft" in status(app), f"{app._einfuegen_ziel} {status(app)}")
S.pump(app, lambda: len(app._aufnahme.puffer) >= 10)
app.sm_record()                                       # Pause
tb.sel = None                                         # Knöpfe Reset/Clear all, EOL-Hinweise: Auswahl/Fokus weg
z["fokus"] = None
app.befund_leeren()                                   # „Clear all: erst Aufnahme/Verarbeitung abschließen“
check("… Clear all während der Pause ändert nichts", app.result_text.text == BEFUND)
app.sm_record()                                       # weiter
S.pump(app, lambda: len(app._aufnahme.puffer) >= 14)
app.sm_ins()
warten_bis_ende(app)
check("… INS: die Markierung ist ersetzt (nicht an den Rand eingefügt)", app.result_text.text == SOLL,
      repr(app.result_text.text))

# 4. Echter Einzelklick ohne Auswahl in der Pause → Cursor gilt, Markierung weg
LOG.clear()
app, tb, z = neue_app(insert=A + len(MARK), sel=(A, A + len(MARK)))
app.sm_record()
S.pump(app, lambda: len(app._aufnahme.puffer) >= 6)
app.sm_record()
P = BEFUND.index("Knorpel")
tb.sel = None
tb.marks["insert"] = P
app._befund_klick()                                   # <ButtonRelease-1> ohne Auswahl
check("Klick ohne Auswahl hebt die gemerkte Markierung auf", app._markierung() is None)
app.sm_record()
check("… weiter: Diktat an der Klick-Stelle (Cursor), Status „Ergänzung an Cursor-Stelle“",
      app._einfuegen_ziel == (P, P) and app._ziel_text == "" and "Ergänzung an Cursor-Stelle · Aufnahme läuft" in status(app),
      f"{app._einfuegen_ziel} {status(app)}")
S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
app.sm_ins()
warten_bis_ende(app)
check("… INS: eingefügt, markierter Text bleibt stehen",
      app.result_text.text == BEFUND.replace("Knorpel", "Zusätzlich kleiner Gelenkerguss. Knorpel"), repr(app.result_text.text))

# 5. Klick, der eine NEUE Markierung setzt (Doppelklick/Ziehen) → die neue wird ersetzt
app, tb, z = neue_app(insert=A + len(MARK), sel=(A, A + len(MARK)))
app.sm_record()
S.pump(app, lambda: len(app._aufnahme.puffer) >= 6)
app.sm_record()
B2 = BEFUND.index("Knorpel glatt.")
tb.sel = (B2, B2 + len("Knorpel glatt."))
app._befund_klick()                                   # Loslassen mit Auswahl = neue Markierung
app.sm_record()
check("Neue Markierung in der Pause → sie ist das Ziel", app._einfuegen_ziel == (B2, B2 + len("Knorpel glatt."))
      and "Ersetzt markierten Text (14 Zeichen)" in status(app), f"{app._einfuegen_ziel} {status(app)}")
S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
app.sm_ins()
warten_bis_ende(app)
check("… INS: die neue Markierung ersetzt, die alte Stelle unverändert",
      app.result_text.text == BEFUND.replace("Knorpel glatt.", "Zusätzlich kleiner Gelenkerguss."), repr(app.result_text.text))

# 6. Markierter Text in der Pause verändert (getippt) → Stelle der Marken, Hinweis „bitte prüfen“, Strg+Z zurück
app, tb, z = neue_app(insert=A + len(MARK), sel=(A, A + len(MARK)))
app.sm_record()
S.pump(app, lambda: len(app._aufnahme.puffer) >= 6)
app.sm_record()
GETIPPT = BEFUND.replace(MARK, "xy")
app.result_text.text = GETIPPT                        # Tk: Auswahl überschrieben, Marken jetzt um „xy“
tb.sel = None
tb.marks["diktat_a"], tb.marks["diktat_b"] = A, A + 2
tb.tags.pop(mod.MARKIERUNG_TAG, None)
app.sm_record()
S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
app.sm_ins()
warten_bis_ende(app)
check("Markierung inzwischen verändert → nur die Stelle der Marken ersetzt, nichts sonst gelöscht",
      app.result_text.text == GETIPPT.replace("xy", "Zusätzlich kleiner Gelenkerguss."), repr(app.result_text.text))
check("… Hinweis „bitte prüfen (Strg+Z = zurück)“, Strg+Z holt den Stand davor",
      "bitte prüfen" in app._letzter_hinweis and app._rueckgaengig() == "break" and app.result_text.text == GETIPPT,
      app._letzter_hinweis)

# 7. IB-Lab-Gerüst: Markierung darin wird ersetzt – kein neuer Befund aus dem Gerüst, Rest bleibt wörtlich
GERUEST = "## Röntgen linke Hand\n\n## Befund\nKnochenalter nach Greulich-Pyle 10 Jahre (IB Lab).\n\n## Ergebnis\n"
app, tb, z = neue_app(text=GERUEST, insert=0, fokus=False)
app._ibl_geruest_text = GERUEST
G = GERUEST.index("10 Jahre")
tb.sel = (G, G + len("10 Jahre"))
app._markierung_merken()
tb.sel = None                                         # Fokus ins CAS gewechselt – nur der Tag hält die Markierung
app.sm_record()
check("Gerüst mit Markierung: Ziel = Markierung, Einbau Cursor (nicht „Neuer Befund (IB-Lab-Gerüst)“)",
      app._einfuegen_ziel == (G, G + len("10 Jahre")) and app._einbau == mod._bf.CURSOR, f"{app._einfuegen_ziel} {app._einbau}")
S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
app.sm_ins()
warten_bis_ende(app)
check("… INS: nur die Markierung ersetzt, Gerüst sonst Zeichen für Zeichen gleich, keine Befund-KI",
      app.result_text.text == GERUEST.replace("10 Jahre", "Zusätzlich kleiner Gelenkerguss."), repr(app.result_text.text))
app, tb, z = neue_app(text=GERUEST, insert=0, fokus=True)
app._ibl_geruest_text = GERUEST
check("Gerüst ohne Markierung (nur Cursor) → wie bisher kein Ziel (normales Diktat ins Gerüst)",
      app._einfuege_ziel_ermitteln() is None)

# 8. Feld wird neu geschrieben (IB-Lab-Werte nachgekommen) → Markierung bleibt auf demselben Text
app, tb, z = neue_app(insert=0)
tb.sel = (A, A + len(MARK))
app._markierung_merken()
tb.sel = None
g = app._markierung_sichern()
app.result_text.text = "Vorspann.\n" + BEFUND
app._markierung_wiederherstellen(g)
check("Neuschreiben des Felds: Markierung wandert mit dem Text", app._markierung() == (A + 10, A + 10 + len(MARK)),
      str(app._markierung()))
app.result_text.text = BEFUND.replace(MARK, "")
app._markierung_wiederherstellen(g)
check("… fehlt der Text danach, ist nichts markiert (nie fremden Text ersetzen)", app._markierung() is None)

# 9. Quelltext: Tk-Bindungen + Selbsttest-Phasen für den EXE-Lauf
src = (HIER.parents[1] / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE bindet <<Selection>> und <ButtonRelease-1> im Befundfeld, Tag sichtbar",
      'tb.bind("<<Selection>>", self._markierung_merken, add="+")' in src
      and 'tb.bind("<ButtonRelease-1>", self._befund_klick, add="+")' in src
      and "tb.tag_configure(MARKIERUNG_TAG, background=MARKIERUNG_FARBE)" in src)
check("Selbsttest-Phasen befund_klick# / befund_sel_weg vorhanden", '"befund_klick#"' in src and '"befund_sel_weg"' in src)

print("FAILS:", fails)
sys.exit(1 if fails else 0)
