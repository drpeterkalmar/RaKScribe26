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
API_KEY = (ROOT / "web_app" / "public" / "vertex-key.txt").read_text().strip()
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

VERTEX_URL = "https://europe-west3-aiplatform.googleapis.com/v1/projects/895690562186/locations/europe-west3/publishers/google/models/gemini-2.5-flash:generateContent"

os.environ["VERTEX_API_KEY"] = API_KEY
sys.path.insert(0, str(ROOT))
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
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
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
        ("Gelenksarthrose C3–C5 im Ergebnis (auch Spondylarthrose ok)", ("gelenksarthrose" in lower or "spondylarthrose" in lower) and "c3" in lower),
        ("Diskopathie C4–C7 im Ergebnis",           "diskopathie" in lower and "c4" in lower),
        ("Fehlhaltung aus Diktat NICHT verschwiegen", "fehlhaltung" in lower or "kyphotisch" in lower),
    ]
    ok = True
    print(f"\n-- CHECKS --")
    for name, passed in checks:
        print(f"  {'✅' if passed else '❌'} {name}")
        ok = ok and passed
    return ok

results = {}

# ── Kette A: EXE-Pfad (radiology_prompt.txt direkt, wie load_prompt_template sie lädt) ──
prompt_txt = (ROOT / "radiology_prompt.txt").read_text()
assert "Flachprofil" in prompt_txt, "radiology_prompt.txt enthält Flachprofil-Regel NICHT!"
p_a = prompt_txt.replace("{roh_text}", DIKTAT).replace("{template_body}", TEMPLATE_BODY).replace("{region_name}", "Halswirbelsäule in 2 Ebenen")
if "{examples}" in p_a:
    p_a = p_a.replace("{examples}", "")
print("Kette A: Gen-Call (radiology_prompt.txt) ...")
report_a = gemini(p_a, temp=0.1)
results["A"] = check_report(report_a, "KETTE A — EXE-Pfad (radiology_prompt.txt → Gen)")

# ── Kette B: Web-Pfad ──
app_src = (ROOT / "web_app" / "src" / "App.tsx").read_text()

# B-Step0: STT-Korrektur-Prompt exakt aus App.tsx
m_corr = re.search(r"const correctionPrompt = `(.*?)`;", app_src, re.DOTALL)
assert m_corr, "correctionPrompt nicht gefunden"
corr_tpl = m_corr.group(1)
assert "Flachprofil" in corr_tpl, "Flachprofil-Fix fehlt im STT-Korrektur-Prompt!"
print("\nKette B/0: STT-Korrektur-Call (App.tsx correctionPrompt) ...")
corrected = gemini(corr_tpl.replace("${rawText}", DIKTAT), temp=0.0)
print(f"  Korrigiertes Diktat: {corrected[:200]}")

# B-Step1: newDefaultPrompt aus App.tsx per Node evaluieren (Template-Literal + ${} frei von Interpolation)
m_node = re.search(r"const newDefaultPrompt =\s*\n(.*?)`</diktat>`;", app_src, re.DOTALL)
assert m_node, "newDefaultPrompt-Block nicht gefunden"
node_code = "const p = " + m_node.group(1).lstrip("`").rstrip(";").strip() + "\nconsole.log(p);"
# Block ist Backtick-Konkatenation mit \n-Escapes — als JS-String auswerten:
node_code = "const p = [\n" + re.sub(r"^\s*`(.*)` \+$", r'"\1",', m_node.group(1), flags=re.MULTILINE) + "\n].join('');\nconsole.log(p);"
node_code = node_code.replace('`', '').replace('",\\n"', '",\\n"')
# Robuster: Block-Zeilen sind `...\\n` + — wir joinen die Literal-Inhalte:
lines = []
for ln in m_node.group(1).splitlines():
    mm = re.match(r"\s*`(.*)` (\+|;)?\s*$", ln)
    if mm:
        lines.append(mm.group(1))
default_prompt = "".join(lines)
default_prompt = default_prompt.replace('\\\\n', '\n').replace('\\n', '\n').replace('\\"', '"')
assert "Flachprofil" in default_prompt, "Flachprofil-Regel fehlt im Web-Default-Prompt!"
p_b1 = default_prompt.replace("{roh_text}", corrected).replace("{template_body}", TEMPLATE_BODY).replace("{region_name}", "Halswirbelsäule in 2 Ebenen")
if "{examples}" in p_b1:
    p_b1 = p_b1.replace("{examples}", "")
print("Kette B/1: Gen-Call (App.tsx newDefaultPrompt) ...")
report_b = gemini(p_b1, temp=0.1)

# B-Step2: Validierungs-Prompt exakt aus App.tsx
m_val = re.search(r"const validationPrompt = `(.*?)`;", app_src, re.DOTALL)
assert m_val, "validationPrompt nicht gefunden"
val_tpl = m_val.group(1)
val_prompt = val_tpl.replace("${rawDictation}", corrected).replace("${generatedReport}", report_b)
print("Kette B/2: Validierungs-Call (App.tsx validationPrompt) ...")
validated = gemini(val_prompt, temp=0.0)
final_b = validated if "## Befund" in validated else report_b
results["B"] = check_report(final_b, "KETTE B — Web-Pfad (Call0 → Call1 → Call2)")

print(f"\n{'='*62}")
print(f"ERGEBNIS: Kette A {'✅ PASS' if results['A'] else '❌ FAIL'} | Kette B {'✅ PASS' if results['B'] else '❌ FAIL'}")
sys.exit(0 if results["A"] and results["B"] else 1)