"""Gate kaiscribe-ohne-gemini-n1 (Peter 23.11.2026 „no gemini please derzeit“): EXE-Ablauf mit KI_RUECKFALL = aus und
einer Befund-KI, die zweimal ausfällt (Zeitüberschreitung). Erwartet: kein Gemini-Aufruf (Spione), das Diktat steht
unverändert im Befundfeld, rote Prüfzeile, nichts eingefügt/kopiert, ein vorher stehender Text bleibt erhalten,
Restructure behält den Text. Aufruf: python3 tests/offline/test_ohne_ki_ui.py (braucht tkinter-freie Attrappen)."""
import pathlib
import socket
import sys

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
mod._fokus_ist_eigenes_fenster = lambda: False
GEMINI = []
mod._gem.generate = lambda *a, **k: (GEMINI.append("gen"), "## X\n\n## Befund\nGemini.\n\n## Ergebnis\nG.")[1]
mod._korr.korrigieren = lambda *a, **k: (GEMINI.append("korr"), "GEMINI")[1]
SENDUNGEN, LOG = [], []


def ausfall(body, frist):
    SENDUNGEN.append(frist)
    raise socket.timeout("timed out")


mod.CFG.ki_rueckfall = False
mod.KI_GEN = mod._la.Weiche("anthropic", mod.CFG.anthropic_modell, sender=ausfall, log=LOG.append, frist=mod.CFG.anthropic_frist,
                            gemini_fn=lambda p, s: (GEMINI.append("weiche"), "GEMINI")[1], schlafen=lambda s: None)
check("Standard der EXE: KI_RUECKFALL aus, Frist 45 s", mod.CFG.anthropic_frist == 45 and mod.KI_GEN.rueckfall_text() == "Rückfall: aus")


def neue_app(text, rechts=""):
    S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear(); SENDUNGEN.clear(); LOG.clear(); GEMINI.clear()
    app = S.baue_app(mod)
    app.transcript_text.insert("1.0", text)
    if rechts:
        app.result_text.insert("1.0", rechts)
    return app


def fertig(app):
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
    S.pump(app, lambda: S.AUFZ.tasten, 0.5)


DIKTAT = "Schulter rechts Tendinosis calcarea mit 17 mm messendem Kalkdepot, Bursitis subacromialis"
app = neue_app(DIKTAT)
app.befund_aus_text()
fertig(app)
check("zweimal Claude (Frist 45 s), kein Gemini", SENDUNGEN == [45, 45] and GEMINI == [], (SENDUNGEN, GEMINI))
check("Befundfeld = Diktat unverändert", app.result_text.text == DIKTAT, repr(app.result_text.text[:120]))
check("rote Prüfzeile „KI nicht verfügbar …“", mod._la.OHNE_KI_ZEILE in (getattr(app, "_cas_hinweise", None) or [])
      and "bitte prüfen" in mod._la.OHNE_KI_ZEILE, getattr(app, "_cas_hinweise", None))
check("nichts eingefügt (kein Strg+V), kein Fehlerdialog", S.AUFZ.tasten == [] and not S.AUFZ.dialoge,
      (S.AUFZ.tasten, S.AUFZ.dialoge))
check("Logzeile ohne KI (kein Rückfall), ohne Diktat-Inhalt",
      any(z == "[KI] gen: Anthropic nicht verwendet — Frist → ohne KI (kein Rückfall)" for z in LOG)
      and not any("Kalkdepot" in z for z in LOG), LOG)
check("unformatiertes Diktat ist kein KaiScribe-Stand (Restructure baut es später neu)",
      getattr(app, "_stand_ks", None) is None, getattr(app, "_stand_ks", None))

# Stand vorher schon ein Text rechts (z. B. Gerüst), bleibt er stehen – das Diktat kommt darunter
VOR = "## Kniegelenk rechts\n\n## Befund\nGerüst.\n\n## Ergebnis\nUnauffällig."
app = neue_app(DIKTAT, rechts=VOR)
app.befund_aus_text()
fertig(app)
t = app.result_text.text
check("vorher stehender Text bleibt, Diktat darunter (nie Löschen ohne Rückfrage)",
      t.startswith(VOR) and t.endswith(DIKTAT) and GEMINI == [], repr(t[:200]))

# Restructure ohne KI: Text bleibt, Hinweis statt Gemini
app = neue_app("", rechts=VOR + "\nZusatz von Hand.")
app.befund_umbauen()
fertig(app)
check("Restructure ohne KI: Text unverändert, Hinweis „KI nicht verfügbar“, kein Gemini",
      app.result_text.text == VOR + "\nZusatz von Hand." and GEMINI == []
      and any("KI nicht verfügbar" in str(d) for d in S.AUFZ.dialoge), (app.result_text.text[-40:], S.AUFZ.dialoge))

# Zweiter Versuch klappt → normaler Claude-Befund, eingefügt
BEFUND = ("## Schultergelenk rechts\n\n## Befund\nIm Ansatzbereich der Supraspinatussehne 17 mm messendes Kalkdepot. "
          "Bursitis subacromialis.\n\n## Ergebnis\n1. Tendinosis calcarea der Supraspinatussehne rechts.\n"
          "2. Bursitis subacromialis rechts.")


def einmal_aus(body, frist):
    SENDUNGEN.append(frist)
    if len(SENDUNGEN) == 1:
        raise socket.timeout("timed out")
    return {"type": "message", "stop_reason": "end_turn", "content": [{"type": "text", "text": BEFUND}], "usage": {}}


mod.KI_GEN.sender = einmal_aus
app = neue_app(DIKTAT)
app.befund_aus_text()
fertig(app)
check("Frist im 1. Versuch, 2. Versuch gut → Claude-Befund eingefügt, kein Gemini",
      len(SENDUNGEN) == 2 and "## Ergebnis" in app.result_text.text and S.AUFZ.tasten == ["ctrl+v"] and GEMINI == []
      and mod._modell_name() == "anthropic/claude-sonnet-5-5", (SENDUNGEN, S.AUFZ.tasten, app.result_text.text[:80]))

print(f"\n{'❌ ' + str(fails) + ' Fehler' if fails else '✅ alle grün'}")
sys.exit(1 if fails else 0)
