"""Gemini-Aufruf der EXE (Umbau Schritt 14) — ohne Tk/Windows importierbar, Netz austauschbar (Tests).

Vertex AI REST (gemini-3.5-flash, EU-Multi-Region-Endpoint), Auth per x-goog-api-key.
v2.11.1: ALLE Text-parts zusammensetzen (Gemini 3.5 teilt Antworten, z. B. '## L' | 'endenwirbel…'), Thinking-parts
weglassen; ein Befund gilt nur als fertig mit Befundtext + nicht-leerem '## Ergebnis' und finishReason STOP;
bis zu 3 Versuche, bei HTTP 401 (Schlüssel ungültig) sofort Abbruch.
Sync: web_app/src/App.tsx joinGeminiText / isCompleteReport / SYS_MSG (Tests: test_parts_join.py, befund_regeln_test.py).
"""
import json
import re
import time
import urllib.request

# v2.11.0: gemini-3.5-flash am EU-Multi-Region-Endpoint (EU-Datenresidenz), Web-Parität
VERTEX_ENDPOINT = (
    "https://aiplatform.eu.rep.googleapis.com/v1/projects/895690562186/"
    "locations/eu/publishers/google/models/gemini-3.5-flash:generateContent"
)

# v3.2: systemInstruction — WORTGLEICH zu SYS_MSG in web_app/src/App.tsx (befund_regeln_test.py prüft das)
SYS_MSG = (
    "Du bist ein präziser Radiologie-Assistent der Praxis 'Röntgen am Kai' – Dr. P. Kalmar / Dr. G. Riegler. "
    "Strukturiere das Diktat nach den Regeln im Prompt mit dem Normalbefund-Template als vollständigem Gerüst. "
    "Ausgabe: zuerst '## ' + kanonische Untersuchungsbezeichnung mit diktierter Seite, dann '## Befund' als Fließtext "
    "ohne Labels und '## Ergebnis' nummeriert (1. 2. 3.) mit den diktierten Begriffen 1:1 inklusive Grad und Messwerten. "
    "Gib ausschließlich den fertigen Befundtext aus – keine Kommentare, keine Einleitung."
)


def report_complete(t):
    """v2.11.1: vollständig = Befundtext (> 20 Zeichen, mit oder ohne '## Befund') + nicht-leeres '## Ergebnis'."""
    t = t or ""
    if "## Ergebnis" not in t or len(t.split("## Ergebnis")[1].strip()) <= 5:
        return False
    pre = t.split("## Ergebnis")[0]
    body = pre.split("## Befund")[1] if "## Befund" in pre else "\n".join(l for l in pre.splitlines() if not l.strip().startswith("#"))
    return len(body.strip()) > 20


def join_text(cand):
    """Alle Text-parts eines Kandidaten (ohne Thinking-parts) zusammensetzen."""
    return "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", [])
                   if isinstance(p.get("text"), str) and not p.get("thought"))


def finish_ok(cand):
    return cand.get("finishReason", "STOP") == "STOP"


def strip_fences(txt):
    txt = re.sub(r'^```[a-zA-Z]*\s*\n?', '', txt)
    return re.sub(r'\n?```\s*$', '', txt).strip()


def request_body(prompt, sys_msg):
    return json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": sys_msg}]},
        # v2.10.15: thinkingBudget 0 (Web-Parität seit v2.10.1) — ohne denkt
        # Gemini dynamisch mit: Befund 7 s → ~1,5 s, gleiche Qualität (90-Fall-A/B).
        "generationConfig": {"temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}},
    }).encode()


def generate(prompt, sys_msg, key, endpoint=VERTEX_ENDPOINT, urlopen=None, sleep=time.sleep, log=None, versuche=3):
    """Befund-Text von Gemini (vollständig) oder Ausnahme (letzter Fehler)."""
    urlopen = urlopen or urllib.request.urlopen
    log = log or (lambda *a: None)
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    body = request_body(prompt, sys_msg)
    last_err = None
    for attempt in range(versuche):
        try:
            req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
            with urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
            if "error" in result:
                raise Exception(result["error"].get("message", result["error"]))
            cand = result["candidates"][0]
            txt = strip_fences(join_text(cand).strip())
            if report_complete(txt) and finish_ok(cand):
                return txt
            last_err = Exception("Befund unvollständig (## Ergebnis fehlt)")
            log(f"[GEN] Versuch {attempt + 1}: Befund unvollständig — neuer Versuch")
        except Exception as e:
            last_err = e
            if "401" in str(e) or "Unauthorized" in str(e):
                break
            log(f"[GEN] Versuch {attempt + 1} fehlgeschlagen: {e}")
            sleep(2 * (attempt + 1))
    raise last_err or Exception("Gemini lieferte keinen Befund")
