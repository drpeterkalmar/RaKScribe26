"""Gate (Umbau Schritt 14): Gemini-Aufruf der EXE (gemini.generate) mit nachgebautem Netz — Request-Inhalt,
Wiederholung bei unvollständigem Befund, Abbruch bei 401, 3 Versuche. Die 28 parts-Join-Fälle prüft
tests/offline/test_parts_join.py (EXE = Web). Aufruf: /usr/bin/python3 tests/offline/test_gemini.py"""
import io, json, pathlib, sys, urllib.error
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import gemini as g  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


VOLL = ("## Kniegelenk rechts in 2 Ebenen\n\n## Befund\nRegelrechte Stellung der artikulierenden Skelettanteile.\n\n"
        "## Ergebnis\n1. Gonarthrose rechts.")


def antwort(parts, fr="STOP"):
    return {"candidates": [{"content": {"parts": parts}, "finishReason": fr}]}


class Netz:
    def __init__(self, folge):
        self.folge, self.requests = list(folge), []

    def __call__(self, req, timeout):
        self.requests.append((req, timeout))
        x = self.folge.pop(0)
        if isinstance(x, Exception):
            raise x
        return io.BytesIO(json.dumps(x).encode())


pausen = []
netz = Netz([antwort([{"text": "## K"}, {"text": VOLL[4:]}])])
t = g.generate("PROMPT", g.SYS_MSG, "AQ.dummy", urlopen=netz, sleep=pausen.append)
req, timeout = netz.requests[0]
body = json.loads(req.data)
check("geteilte Antwort wird zusammengesetzt", t == VOLL)
check("Request: EU-Endpoint, POST, x-goog-api-key, Timeout 120 s", req.full_url == g.VERTEX_ENDPOINT and req.get_method() == "POST"
      and req.get_header("X-goog-api-key") == "AQ.dummy" and timeout == 120)
check("Request: Prompt, systemInstruction = SYS_MSG, temperature 0, thinkingBudget 0",
      body["contents"][0]["parts"][0]["text"] == "PROMPT" and body["systemInstruction"]["parts"][0]["text"] == g.SYS_MSG
      and body["generationConfig"] == {"temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}})
netz = Netz([antwort([{"text": VOLL.split("## Ergebnis")[0]}]), antwort([{"text": "```markdown\n" + VOLL + "\n```"}])])
check("unvollständig → sofort zweiter Versuch, Codezaun entfernt", g.generate("P", "S", "k", urlopen=netz, sleep=pausen.append) == VOLL
      and len(netz.requests) == 2 and pausen == [])
netz = Netz([antwort([{"text": VOLL[:60]}], "MAX_TOKENS"), antwort([{"text": VOLL}])])
check("abgeschnitten (MAX_TOKENS) → neuer Versuch", g.generate("P", "S", "k", urlopen=netz, sleep=pausen.append) == VOLL)
fehler401 = urllib.error.HTTPError(g.VERTEX_ENDPOINT, 401, "Unauthorized", {}, None)
netz = Netz([fehler401, antwort([{"text": VOLL}])])
try:
    g.generate("P", "S", "k", urlopen=netz, sleep=pausen.append)
    check("HTTP 401 → sofort Abbruch (kein zweiter Versuch)", False)
except urllib.error.HTTPError as e:
    check("HTTP 401 → sofort Abbruch (kein zweiter Versuch)", e.code == 401 and len(netz.requests) == 1)
pausen.clear()
netz = Netz([OSError("Netz weg"), {"error": {"message": "RESOURCE_EXHAUSTED"}}, antwort([{"text": "kaputt"}])])
try:
    g.generate("P", "S", "k", urlopen=netz, sleep=pausen.append)
    check("3 Fehlversuche → Ausnahme mit letztem Fehler", False)
except Exception as e:
    check("3 Fehlversuche → Ausnahme mit letztem Fehler", "unvollständig" in str(e) and len(netz.requests) == 3, str(e))
check("Pausen nur nach Fehlern: 2 s, 4 s", pausen == [2, 4], str(pausen))
netz = Netz([OSError("x"), antwort([{"text": VOLL}])])
check("Netzfehler, dann Erfolg → Befund", g.generate("P", "S", "k", urlopen=netz, sleep=lambda s: None) == VOLL)
check("Thinking-parts werden ignoriert", g.join_text(antwort([{"text": "denke", "thought": True}, {"text": VOLL}])["candidates"][0]) == VOLL)

SF = json.loads((ROOT / "sync_fixtures.json").read_text(encoding="utf-8"))
falsch = [t[:40] for t, soll in SF["report_complete"] if g.report_complete(t) != soll]
check(f"report_complete: {len(SF['report_complete'])} gemeinsame Fälle mit der Web-App (sync_fixtures.json)", not falsch, str(falsch))
src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE nutzt gemini.generate (kein eigener Request-Code mehr)", "_gem.generate(prompt, SYS_MSG" in src
      and '"systemInstruction"' not in src and "SYS_MSG = (" not in src)

print("\n" + ("✅ GEMINI PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
