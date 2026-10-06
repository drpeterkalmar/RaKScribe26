#!/usr/bin/env python3
"""Live-Verifikation v2.10.3 — Flachprofil-Case (Peter 07.09., Screenshots):
Rohdiktat (EXE v2.9.10, Engine GOOGLE): 'HWS Doppelpunkt neue Zeile flachprofile nach links
komplexes Coyote Fehlhaltung Punkt neue Zeile Osteochondrose C2 bis c4. Und alle gelenksarthrose
Z3 c5. Hochgradige diskopathie C4 bis C7'

Kette A (EXE-Pfad): radiology_prompt.txt → Call1 Gen. Erwartung: KEIN 'Flachprofil', KEIN 'Coyote',
'flachbogig' + 'kyphotisch' im Befundtext, alle 3 Degenerationen im Ergebnis.
Kette B (Web-Pfad): Call0 STT-Korrektur (Prompt exakt aus App.tsx, mit Flachprofil-Fixes) →
Call1 Gen (newDefaultPrompt aus App.tsx, per Node evaluiert) → Call2 Validierung (Prompt exakt aus App.tsx).
"""
import os, re, sys, json, pathlib, urllib.request, urllib.error, subprocess, time

ROOT = pathlib.Path.home() / "dev" / "RaKScribe26"
API_KEY = ""  # v3.2.3: alte vertex-key.txt gelöscht (rotiert) → harness nutzt den Hermes-SA-Bearer (vertex-sa-key.json)
# Bearer-Fallback: Hermes-SA (AQ.-Key in vertex-key.txt ist rotiert/401)
from google.oauth2 import service_account
import google.auth.transport.requests as _tr
_sa_creds = service_account.Credentials.from_service_account_file(
    str(pathlib.Path.home() / ".hermes" / "secrets" / "vertex-sa-key.json"),
    scopes=["https://www.googleapis.com/auth/cloud-platform"])
_sa_creds.refresh(_tr.Request())

def _sa_token():
    if not _sa_creds.valid:
        _sa_creds.refresh(_tr.Request())
    return _sa_creds.token

VERTEX_URL = "https://aiplatform.eu.rep.googleapis.com/v1/projects/895690562186/locations/eu/publishers/google/models/gemini-3.5-flash:generateContent"

os.environ["VERTEX_API_KEY"] = API_KEY
sys.path.insert(0, str(ROOT / "tools"))
from test_all_regions import build_gen_prompt, build_val_prompt, call_gemini, TEMPLATES

DIKTAT = ("HWS Doppelpunkt neue Zeile flachprofile nach links komplexes Coyote Fehlhaltung Punkt "
          "neue Zeile Osteochondrose C2 bis c4. Und alle gelenksarthrose Z3 c5. Hochgradige diskopathie C4 bis C7")
TEMPLATE_KEY = "halswirbelsäule_in_2_ebenen"
TEMPLATE_BODY = TEMPLATES[TEMPLATE_KEY]["body"]

def gemini(prompt, temp=0.0, tries=4):
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temp, "thinkingConfig": {"thinkingBudget": 0}},
    }).encode()
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(VERTEX_URL, data=body, headers={
                "Content-Type": "application/json", "x-goog-api-key": API_KEY})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                req = urllib.request.Request(VERTEX_URL, data=body, headers={
                    "Content-Type": "application/json", "Authorization": "Bearer " + _sa_token()})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())
            elif e.code in (429, 500, 503) and attempt < tries - 1:
                time.sleep(20 * (attempt + 1)); continue
            else:
                raise
        if "error" in data:
            raise Exception(f"Gemini API error: {data['error'].get('message', data['error'])}")
        return "".join(p.get("text", "") for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", []) if not p.get("thought")).strip()
    raise Exception("Gemini: keine Antwort nach Retries")

def check_report(final, label):
    print(f"\n{'='*62}\n{label}\n{'='*62}")
    print(final[:800])
    lower = final.lower()
    checks = [
        ("KEIN 'Flachprofil' im Report",            "flachprofil" not in lower),
        ("KEIN 'Coyote' im Report",                 "coyote" not in lower),
        ("'flachbogig' im Befundtext",              "flachbogig" in lower),
        ("Osteochondrose C2–C4 im Ergebnis",        "osteochondrose" in lower and "c2" in lower),
        # Roh-STT "Und alle gelenksarthrose" = verhörte "Unkovertebralgelenksarthrose" → Unkovertebral-Lesart ist korrekt
        ("Gelenksarthrose C3–C5 im Ergebnis (auch Spondylarthrose/Unkovertebralarthrose ok)", ("gelenksarthrose" in lower or "spondylarthrose" in lower or "unkovertebral" in lower or "uncovertebral" in lower) and "c3" in lower),
        ("Diskopathie C4–C7 im Ergebnis",           ("diskopathie" in lower or "discopathie" in lower) and "c4" in lower),
        ("Fehlhaltung aus Diktat NICHT verschwiegen", "fehlhaltung" in lower or "kyphotisch" in lower),
    ]
    ok = True
    print(f"\n-- CHECKS --")
    for name, passed in checks:
        print(f"  {'✅' if passed else '❌'} {name}")
        ok = ok and passed
    return ok

results = {}
# v3.2: beide Ketten = ECHTE Produktionsketten über tools/prod_pipeline.py (Gen-Prompt aus radiology_prompt.txt — EINE
# Quelle für EXE + Web —, SYS_MSG, Web-Call-0/Validator aus App.tsx, Regionen-Trenner + Ergebnis-Nummerierung).
# Läufe: erstes Argument (Default 1); grün nur, wenn ALLE Läufe je Kette grün sind.
import prod_pipeline as pp
assert "Kellgren" in pp.GEN_PROMPT, "K&L-Regel fehlt in radiology_prompt.txt!"
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1
results = {"A": True, "B": True}
for _run in range(RUNS):
    print(f"\n── Lauf {_run + 1}/{RUNS} ──")
    print("Kette A: EXE-Pfad (misheard → Trenner → radiology_prompt.txt + SYS_MSG → Nummerierung) ...")
    report_a = pp.exe_kette(DIKTAT)
    results["A"] &= check_report(report_a, "KETTE A — EXE-Pfad")
    print("Kette B: Web-Pfad (Call 0 → Trenner → Gen → Call 2 → Nummerierung) ...")
    final_b = pp.web_kette(DIKTAT)
    results["B"] &= check_report(final_b, "KETTE B — Web-Pfad (Call0 → Call1 → Call2)")

print(f"\n{'='*62}")
print(f"ERGEBNIS: Kette A {'✅ PASS' if results['A'] else '❌ FAIL'} | Kette B {'✅ PASS' if results['B'] else '❌ FAIL'}")
sys.exit(0 if results["A"] and results["B"] else 1)