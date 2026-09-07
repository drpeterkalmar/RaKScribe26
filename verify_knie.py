#!/usr/bin/env python3
"""Live-Verifikation v2.10.6 — Peters Knie-Case (08.09., Screenshot):
Diktat: 'Kniegelenk links, Röntgen, maßgradige Gonarthrose des medialen Femorotibialkompartiments,
geringgradige Retropatellararthrose. Ansonsten unauffällig.'
Erwartung: Überschrift 'Kniegelenk links in 2 Ebenen' (NICHT nacktes 'Kniegelenk'),
Ergebnis mit Kellgren-&-Lawrence-Graduierung (Femorotibial + Patellofemoral getrennt).
Kette A = EXE-Pfad (radiology_prompt.txt + <untersuchung>), Kette B = Web-Pfad (Call0→Call1→Call2,
Prompts exakt aus App.tsx extrahiert).
"""
import os, re, sys, json, pathlib, urllib.request, urllib.error, time

ROOT = pathlib.Path.home() / "dev" / "RaKScribe26"
API_KEY = (ROOT / "web_app" / "public" / "vertex-key.txt").read_text().strip()
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

VERTEX_URL = "https://europe-west3-aiplatform.googleapis.com/v1/projects/895690562186/locations/europe-west3/publishers/google/models/gemini-2.5-flash:generateContent"

os.environ["VERTEX_API_KEY"] = API_KEY
sys.path.insert(0, str(ROOT))
import test_all_regions as harness
from test_all_regions import call_gemini

DIKTAT = ("Kniegelenk links, Röntgen, maßgradige Gonarthrose des medialen Femorotibialkompartiments, "
          "geringgradige Retropatellararthrose. Ansonsten unauffällig.")
TEMPLATE_KEY = "kniegelenk_in_2_ebenen"
TEMPLATE = harness.TEMPLATES[TEMPLATE_KEY]
TEMPLATE_BODY = TEMPLATE["body"]
REGION = TEMPLATE["display_name"]
assert TEMPLATE_BODY.split("\n")[0].strip() == "Kniegelenk in 2 Ebenen", "Template-Zeile 1 falsch!"

def gemini(prompt, temp=0.0, tries=4):
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temp, "thinkingConfig": {"thinkingBudget": 0}},
    }).encode()
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
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
    raise Exception("Gemini: keine Antwort nach Retries")

def check_report(final, label):
    print(f"\n{'='*62}\n{label}\n{'='*62}")
    print(final[:900])
    befund = final.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in final else ""
    ergebnis = final.split("## Ergebnis")[1] if "## Ergebnis" in final else ""
    header = next((l.strip() for l in befund.splitlines() if l.strip()), "")
    lower = final.lower()
    checks = [
        ("Überschrift = 'Kniegelenk … in 2 Ebenen'", "kniegelenk" in header.lower() and "in 2 ebenen" in header.lower()),
        ("Überschrift mit diktierter Seite (links)", "links" in header.lower()),
        ("Nackte Kurzform 'Kniegelenk' als Überschrift beseitigt", header.strip() != "Kniegelenk"),
        ("K&L-Graduierung im Ergebnis", "kellgren" in ergebnis.lower() and "grad" in ergebnis.lower()),
        ("Femorotibial + Patellofemoral beide im Ergebnis",
         ("femorotibial" in ergebnis.lower() or "medial" in ergebnis.lower()) and
         ("patellofemoral" in ergebnis.lower() or "retropatellar" in ergebnis.lower() or "patella" in ergebnis.lower())),
        ("KEIN Normalbefund-Widerspruch (Gelenkkörper 'normal' + Arthrose)",
         "normale form und struktur der gelenkkörper" not in lower),
        ("KEIN 'Flachprofil' (Regression)", "flachprofil" not in lower),
    ]
    ok = True
    print("\n-- CHECKS --")
    for name, passed in checks:
        print(f"  {'✅' if passed else '❌'} {name}  | Überschrift: {header!r}")
        ok = ok and passed
    return ok

results = {}

# ── Kette A: EXE-Pfad (radiology_prompt.txt + <untersuchung> wie in RaKScribe.py process_dictation) ──
prompt_txt = (ROOT / "radiology_prompt.txt").read_text()
assert "Kellgren" in prompt_txt, "K&L-Regel fehlt in radiology_prompt.txt!"
p_a = prompt_txt.replace("{roh_text}", DIKTAT).replace("{template_body}", TEMPLATE_BODY).replace("{region_name}", REGION)
p_a = p_a.replace("{examples}", "") + f"\n<untersuchung>{REGION}</untersuchung>\n"
print("Kette A: Gen-Call (radiology_prompt.txt + <untersuchung>) ...")
report_a = gemini(p_a, temp=0.1)
results["A"] = check_report(report_a, "KETTE A — EXE-Pfad")

# ── Kette B: Web-Pfad ──
app_src = (ROOT / "web_app" / "src" / "App.tsx").read_text()
assert "Kellgren" in app_src, "K&L-Regel fehlt in App.tsx!"
assert "untersuchung>" in app_src, "<untersuchung>-Block fehlt in App.tsx!"

# B-0: STT-Korrektur
m_corr = re.search(r"const correctionPrompt = `(.*?)`;", app_src, re.DOTALL)
corr_tpl = m_corr.group(1)
print("\nKette B/0: STT-Korrektur ...")
corrected = gemini(corr_tpl.replace("${rawText}", DIKTAT), temp=0.0)
print(f"  → {corrected[:160]}")

# B-1: newDefaultPrompt aus App.tsx + <untersuchung> (wie callGeminiLLM)
m_node = re.search(r"const newDefaultPrompt =\s*\n(.*?)`</diktat>`;", app_src, re.DOTALL)
assert m_node, "newDefaultPrompt nicht gefunden"
lines = []
for ln in m_node.group(1).splitlines():
    mm = re.match(r"\s*`(.*)` (\+|;)?\s*$", ln)
    if mm:
        lines.append(mm.group(1))
default_prompt = "".join(lines).replace('\\\\n', '\n').replace('\\n', '\n').replace('\\"', '"')
assert "Kellgren" in default_prompt and "UNTERSUCHUNGS-ÜBERSCHRIFT" in default_prompt
p_b1 = (default_prompt
        .replace("{roh_text}", corrected)
        .replace("{template_body}", TEMPLATE_BODY)
        .replace("{region_name}", REGION)
        .replace("{examples}", "")
        + f"\n<untersuchung>{REGION}</untersuchung>\n")
print("Kette B/1: Gen-Call (App.tsx Default-Prompt + <untersuchung>) ...")
report_b = gemini(p_b1, temp=0.1)

# B-2: Validierung (Prompt exakt aus App.tsx)
m_val = re.search(r"const validationPrompt = `(.*?)`;", app_src, re.DOTALL)
val_tpl = m_val.group(1)
val_prompt = val_tpl.replace("${rawDictation}", corrected).replace("${generatedReport}", report_b)
print("Kette B/2: Validierungs-Call ...")
validated = gemini(val_prompt, temp=0.0)
final_b = validated if "## Befund" in validated else report_b
results["B"] = check_report(final_b, "KETTE B — Web-Pfad (Call0 → Call1 → Call2)")

print(f"\n{'='*62}")
print(f"ERGEBNIS: Kette A {'✅ PASS' if results['A'] else '❌ FAIL'} | Kette B {'✅ PASS' if results['B'] else '❌ FAIL'}")
sys.exit(0 if results["A"] and results["B"] else 1)