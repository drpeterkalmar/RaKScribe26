"""Gate v3.4.0 (Peter 07.10.): Schalter „Nur Text“ — rechts nur die korrigierte Spracherkennung, kein Befund.
EXE: korrektur.py (Call 0 wortgleich zur Web-App), pipeline.nur_text_aus_diktat, Ablauf in RaKScribe.py mit Attrappen.
Synthetische Diktate.  Aufruf: /usr/bin/python3 tests/offline/test_nur_text.py"""
import io, json, pathlib, sys
HIER = pathlib.Path(__file__).resolve().parent
ROOT = HIER.parents[1]
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(ROOT / "source_code"))
import korrektur as K  # noqa: E402
import pipeline as P  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# 1. Prompt wortgleich zur Web-App (gleicher Snapshot wie gemini.ts correctionPrompt)
snap = (HIER / "snapshots" / "call0_prompt.txt").read_text(encoding="utf-8")
check("Call-0-Prompt der EXE = Snapshot der Web-App",
      K.prompt("${MISHEARD_PROMPT_BLOCK}", "${rawText}") == snap)
src = (ROOT / "web_app" / "src" / "gemini.ts").read_text(encoding="utf-8")
check("gemini.ts correctionPrompt enthält dieselbe Regel 7 (Baustein)", "Baustein" in src and "Baustein" in K.KORREKTUR_PROMPT)


# 2. korrigieren(): Antwort übernehmen, bei Fehler/Verkürzung Rohtext
class Antwort:
    def __init__(self, daten):
        self.b = json.dumps(daten).encode()

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def netz(text, finish="STOP", fehler=None):
    gesehen = {}

    def urlopen(req, timeout=0):
        gesehen["body"] = json.loads(req.data)
        gesehen["key"] = req.headers.get("X-goog-api-key")
        if fehler:
            raise OSError(fehler)
        return Antwort({"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": finish}]})
    return urlopen, gesehen


roh = "Kniegelenk rechts Gelenkspalt medial verschmelert, ansonsten unauffällig"
u, g = netz("Kniegelenk rechts: Gelenkspalt medial verschmälert, ansonsten unauffällig")
erg = K.korrigieren(roh, "KEY", "BLOCK", urlopen=u)
check("Korrektur übernommen", erg == "Kniegelenk rechts: Gelenkspalt medial verschmälert, ansonsten unauffällig", erg)
p = g["body"]["contents"][0]["parts"][0]["text"]
check("Prompt enthält Fehlhör-Block und Rohtext, Temperatur 0, kein Thinking",
      "BLOCK" in p and p.rstrip().endswith("Korrigiert:") and roh in p
      and g["body"]["generationConfig"] == {"temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}, p[-200:])
u, _ = netz("Kniegelenk rechts")
check("verkürzte Antwort (< 60 %) → Rohtext", K.korrigieren(roh, "KEY", urlopen=u) == roh)
u, _ = netz("x" * 200, finish="MAX_TOKENS")
check("abgeschnittene Antwort (finishReason ≠ STOP) → Rohtext", K.korrigieren(roh, "KEY", urlopen=u) == roh)
u, _ = netz("", fehler="Netz weg")
check("Netzfehler → Rohtext", K.korrigieren(roh, "KEY", urlopen=u) == roh)
check("ohne Schlüssel → Rohtext, kein Aufruf", K.korrigieren(roh, "", urlopen=None) == roh)
u, _ = netz("```\nKniegelenk rechts: Gelenkspalt medial verschmälert, ansonsten unauffällig\n```")
check("Codezäune entfernt", K.korrigieren(roh, "KEY", urlopen=u).startswith("Kniegelenk"))

# 3. pipeline.nur_text_aus_diktat
B = json.loads((ROOT / "ordi_bausteine.json").read_text(encoding="utf-8"))["bausteine"]
ctx = P.Kontext(templates={}, display_names=[], prompt="", llm=lambda p: (_ for _ in ()).throw(AssertionError("kein Befund-LLM!")),
                misheard=lambda t: t.replace("Wasser-Sip-Test", "Wasser-Siphon-Test"),
                korrektur=lambda t: t + " [korrigiert]", bausteine=B)
e = P.nur_text_aus_diktat("  Reflux im Wasser-Sip-Test  ", ctx)
check("Fehlhör-Liste → Korrektur, kein Befund-LLM, kein ## Befund",
      e.report == "Reflux im Wasser-Siphon-Test [korrigiert]" and "## " not in e.report and e.vollstaendig is False, e.report)
check("leeres Diktat → leer", P.nur_text_aus_diktat("   ", ctx).leer)
satz = [k for k, v in B.items() if isinstance(v, dict) and v.get("art") == "satz"]
if satz:
    ctx.korrektur = None
    e = P.nur_text_aus_diktat("Knochendichte: Baustein A1", ctx)
    check("Satz-Bausteine werden auch im Nur-Text-Modus eingesetzt", "Baustein A1" not in e.report, e.report[:120])
    snap_a1 = (HIER / "snapshots" / "nur_text_a1.txt").read_text(encoding="utf-8")  # .txt: *.json ist gitignored
    check("EXE = Web-Snapshot (pipeline_test.mjs prüft dieselbe Datei)", e.report == snap_a1, e.report[:120])

# 4. EXE-Ablauf: Schalter an → rechts der korrigierte Text, kopiert + eingefügt, Befund-KI nie gerufen
import exe_stubs as S  # noqa: E402
import threading  # noqa: E402
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._chirp3_worker = lambda pcm, sr, loc, token: "Lendenwirbelsäule Osteochondrose L4 L5"
gerufen = []
mod._korr.korrigieren = lambda t, key, block="", log=None: (gerufen.append(t), "Lendenwirbelsäule: Osteochondrose L4/L5.")[1]
mod._llm_aufruf = lambda p: (_ for _ in ()).throw(AssertionError("Befund-KI im Nur-Text-Modus gerufen"))
mod.speech_client = S.FakeSpeechClient(S.streaming_stub())
S.AUFZ.tasten.clear()
app = S.baue_app(mod)
app.nur_text_var = type("V", (), {"get": lambda self: True})()
mod._fokus_ist_eigenes_fenster = lambda: False
app.toggle_recording()
S.pump(app, lambda: len(app._aufnahme.puffer) >= 12)
app.toggle_recording()
S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
S.pump(app, lambda: S.AUFZ.tasten, 1.5)
check("EXE Nur Text: rechts nur der korrigierte Text", app.result_text.text == "Lendenwirbelsäule: Osteochondrose L4/L5.",
      app.result_text.text)
check("EXE Nur Text: Call 0 einmal mit dem chirp_3-Text", gerufen == ["Lendenwirbelsäule Osteochondrose L4 L5"], str(gerufen))
check("EXE Nur Text: kopiert und eingefügt", S.AUFZ.tasten == ["ctrl+v"] and S.CLIPBOARD.data.get(13), str(S.AUFZ.tasten))
app._aufnahme_stoppen()
check("EXE: ohne Schalter (Attrappe ohne nur_text_var) ist Nur Text aus", S.baue_app(mod).nur_text_aktiv() is False)

# 5. Einstellung überlebt Neustart (%APPDATA%\RaKScribe\einstellungen.json)
mod.einstellung_schreiben("nur_text", True)
check("Einstellung gespeichert und gelesen", mod.einstellung_lesen("nur_text", False) is True)
mod.einstellung_schreiben("nur_text", False)
check("Einstellung zurückgesetzt", mod.einstellung_lesen("nur_text", True) is False)

print("FAILS:", fails)
sys.exit(1 if fails else 0)
