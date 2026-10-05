#!/usr/bin/env python3
"""
Vollständiger Widerspruchstest für alle Regionen/Modalitäten.
Testet Generierung + Validierung mit pathologischen Diktaten pro Region.
"""

import json
import os
import re
import urllib.request
import urllib.error
import time
import sys
from pathlib import Path

API_KEY = os.environ.get("VERTEX_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
VERTEX_URL = "https://aiplatform.eu.rep.googleapis.com/v1/projects/895690562186/locations/eu/publishers/google/models/gemini-3.5-flash:generateContent"

# Templates laden
TEMPLATES_PATH = Path(__file__).parent / "templates.json"
with open(TEMPLATES_PATH) as f:
    TEMPLATES = json.load(f)

# v3.2: KEINE Prompt-Kopie mehr im Harness — Gen-Prompt = radiology_prompt.txt (eine Quelle für EXE + Web),
# Validator = App.tsx validationPrompt, systemInstruction = SYS_MSG aus RaKScribe.py (siehe prod_pipeline.py).
import prod_pipeline as _pp  # noqa: E402
CONFLICT_RULES = _pp.GEN_PROMPT[_pp.GEN_PROMPT.index("## KONFLIKT-REGELN"):_pp.GEN_PROMPT.index("## STILBEISPIELE")]

# ─── Testfälle ───
TEST_CASES = [
    # (name, template_key, diktat, erwartete_pathologien)
    ("HWS Streckhaltung+Skoliose+Osteochondrose", "halswirbelsäule_in_2_ebenen",
     "HWS, Röntgen, Streckhaltung, flachbogige Konvexität, Skoliose, degenerative Antelisthese C5 gegenüber C6, bei Osteochondrose, bei Unkovertebralgelenksarthrosen und Spondylosis deformans in diesen Segmenten. Ansonsten unauffällig.",
     ["Streckhaltung", "Skoliose", "Antelisthese", "Osteochondrose", "Unkovertebralgelenksarthrose", "Spondylosis deformans"]),

    ("LWS Osteochondrose+Spondylose+Facettenarthrose", "lendenwirbelsäule_in_2_ebenen",
     "Lendenwirbelsäule, Röntgen, Skoliose, flachbogig linkskonvex, Osteochondrose L4/L5 sowie L5/S1, Spondylosis deformans L3 bis L5, Facettengelenksarthrosen L3 bis S1, Retrolisthese L4 gegenüber L5. Ansonsten unauffällig.",
     ["Skoliose", "Osteochondrose", "Spondylosis deformans", "Facettengelenksarthrose", "Retrolisthese"]),

    ("BWS Morbus Scheuermann", "brustwirbelsäule_in_2_ebenen",
     "Brustwirbelsäule, Röntgen, vermehrte Kyphose, Morbus Scheuermann, Keilwirbel Th7 bis Th9, Schmorl-Knoten Th6 bis Th10. Ansonsten unauffällig.",
     ["Kyphose", "Morbus Scheuermann", "Keilwirbel", "Schmorl"]),

    ("Schulter Omarthrose+Tendinosis calcarea", "schultergelenk_in_2_ebenen",
     "Schulter rechts, Röntgen, Omarthrose, Kalzifikation Supraspinatussehne, Humeruskopfhochstand. Ansonsten unauffällig.",
     ["Omarthrose", "Kalzifikation", "Humeruskopfhochstand"]),

    ("Schulter Fraktur", "schultergelenk_in_2_ebenen",
     "Schulter links, Röntgen, dislozierte Fraktur des Collum chirurgicum humeri. Ansonsten unauffällig.",
     ["Fraktur", "Collum chirurgicum"]),

    ("Hüfte Coxarthrose", "hüftgelenk_in_2_ebenen",
     "Hüfte links, Röntgen, Coxarthrose links, Gelenkspaltverschmälerung, subchondrale Sklerosierung, osteophytäre Randwülste. Ansonsten unauffällig.",
     ["Coxarthrose"]),

    ("Hüfte Schenkelhalsfraktur", "hüftgelenk_in_2_ebenen",
     "Hüfte rechts, Röntgen, nicht dislozierte Schenkelhalsfraktur rechts, Garden I. Ansonsten unauffällig.",
     ["Schenkelhalsfraktur", "Garden"]),

    ("Knie Gonarthrose", "kniegelenk_in_2_ebenen",
     "Knie rechts, Röntgen, Gonarthrose rechts, medialbetonte Gelenkspaltverschmälerung, subchondrale Sklerosierung, Osteophyten. Ansonsten unauffällig.",
     ["Gonarthrose", "Kellgren"]),

    ("Knie Gonarthrose K&L (Peter 08.09., Screenshot-Case)", "kniegelenk_in_2_ebenen",
     "Kniegelenk links, Röntgen, maßgradige Gonarthrose des medialen Femorotibialkompartiments, geringgradige Retropatellararthrose. Ansonsten unauffällig.",
     ["Gonarthrose", "Kellgren"]),

    ("Ellbogen Fraktur", "ellbogengelenk_in_2_ebenen",
     "Ellbogen rechts, Röntgen, dislozierte Fraktur des Radiusköpfchens. Ansonsten unauffällig.",
     ["Fraktur", "Radiusköpfchen"]),

    ("Hand Fraktur", "hand_in_2_ebenen",
     "Hand links, Röntgen, nicht dislozierte Fraktur der Kahnbeintaille links. Ansonsten unauffällig.",
     ["Fraktur", "Kahnbein"]),

    ("Handgelenk SLAC", "handgelenk_in_2_ebenen",
     "Handgelenk rechts, Röntgen, SLAC wrist, Scapholunäre Dissoziation, Arthrose radioscaphoid. Ansonsten unauffällig.",
     ["SLAC", "Dissoziation", "Arthrose"]),

    ("Beckenübersicht Coxarthrose+Beckenschiefstand", "beckenübersicht_stehend",
     "Beckenübersicht stehend, Röntgen, Beckenschiefstand nach links um 4 mm, Beinlängendifferenz links -4 mm, Coxarthrose links. Ansonsten unauffällig.",
     ["Beckenschiefstand", "Beinlängendifferenz", "Coxarthrose"]),

    ("Sprunggelenk Arthrose", "sprunggelenk_in_2_ebenen",
     "Sprunggelenk links, Röntgen, Arthrose des oberen Sprunggelenkes, Gelenkspaltverschmälerung, subchondrale Sklerosierung, Osteophyten. Ansonsten unauffällig.",
     ["Arthrose"]),

    ("HWS Discopathiezeichen (Peter 07.09., Regression)", "halswirbelsäule_in_2_ebenen",
     "HWS: Osteochondrose C3/C4, deformierende Spondylose C2–C7, Discopathiezeichen C4–C7.",
     ["Osteochondrose", "Spondylose", "Discopathiezeichen"]),

    ("HWS Flachprofil-STT + kyphotische Fehlhaltung (Peter 07.09., Screenshot-Case)", "halswirbelsäule_in_2_ebenen",
     "HWS: flachprofile nach links, komplexe kyphotische Fehlhaltung. Osteochondrose C2 bis C4. Gelenksarthrose C3 bis C5. Hochgradige Diskopathie C4 bis C7.",
     ["flachbogig", "Fehlhaltung", "Osteochondrose", "Gelenksarthrose", "Diskopathie"]),

    ("Schädel Fraktur", "schädel_in_2_ebenen",
     "Schädel, Röntgen, undislozierte Fraktur des Os parietale links. Ansonsten unauffällig.",
     ["Fraktur", "Os parietale"]),

    ("Nasennebenhöhlen Sinusitis", "nasennebenhöhlen",
     "Nasennebenhöhlen, Röntgen, Schleimhautschwellung und Verlegung des Sinus maxillaris bds., Spiegelbildung links. Ansonsten unauffällig.",
     ["Schleimhautschwellung", "Spiegelbildung"]),
]


def _get_sa_token():
    """Bearer-Fallback: SA-JSON (Hermes-Key, gleiches GCP-Projekt) wenn kein/ungültiger AQ.-Key."""
    global _SA_TOKEN_CACHE
    if _SA_TOKEN_CACHE:
        return _SA_TOKEN_CACHE
    from google.oauth2 import service_account
    import google.auth.transport.requests as _tr
    sa_path = os.environ.get("VERTEX_SA_KEY", str(Path.home() / ".hermes" / "secrets" / "vertex-sa-key.json"))
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(_tr.Request())
    _SA_TOKEN_CACHE = creds.token
    return _SA_TOKEN_CACHE

_SA_TOKEN_CACHE = None

def call_gemini(prompt, token=None, temperature=0.0, timeout=120, system=None):
    headers = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "thinkingConfig": {"thinkingBudget": 0}}
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(VERTEX_URL, data=body, headers=headers, method="POST")
    _retries = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                # Fallback: SA-Bearer (AQ.-Key fehlt/rotiert)
                req = urllib.request.Request(VERTEX_URL, data=body, headers={
                    "Content-Type": "application/json", "Authorization": "Bearer " + _get_sa_token()}, method="POST")
            elif e.code in (429, 500, 503) and _retries < 3:
                _retries += 1
                time.sleep(30 * _retries)
            else:
                raise
    if "error" in data:
        raise Exception(f"Gemini API error: {data['error'].get('message', data['error'])}")
    return "".join(p.get("text", "") for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", []) if not p.get("thought")).strip()


def derive_titel_harness(raw, display_name):
    """Wie derive_untersuchungs_titel in RaKScribe.py (sync!) — generische
    '(Allgemein)'-Templates bekommen den Titel aus dem Diktat."""
    if not re.search(r"\(allgemein\)", display_name or "", re.I):
        return display_name
    # v2.10.13-Sync: Negations-Guard, Loop statt break, ':'-Strip, Leak, Cap.
    t = re.sub(r"\bHW\b", "HWS", (raw or "").strip())
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[.?!]\s*$", "", t).strip()
    for _ in range(3):
        stripped = False
        for f in (r"unauff(?:ae|ä)?llig", r"o\.?\s?B\.?", r"ohne pathologischen Befund",
                  r"ohne pathologischem Befund", r"kein pathologischer Befund",
                  r"regelrecht", r"normal"):
            m = re.search(r"(?:^|[\s,])" + f + r"\s*$", t, re.I)
            if m:
                pre = t[:m.start()].strip()
                if re.search(r"\bnicht\s*$", pre, re.I):
                    continue
                t = pre.strip()
                stripped = True
        if not stripped:
            break
    t = re.sub(r"[.,?!:]+$", "", t).strip()
    t = re.sub(r"\(\s*allgemein\s*\)", "", t, flags=re.I).strip()
    if len(t) > 80:
        t = t[:80].strip()
    return t or re.sub(r"\s*\(Allgemein\)", "", display_name, flags=re.I).strip()


def build_gen_prompt(raw_text, template_body, region_name=None):
    """Gen-Prompt wie die EXE (radiology_prompt.txt + <untersuchung>) — Web nutzt dieselbe Datei."""
    p = (_pp.GEN_PROMPT.replace("{roh_text}", raw_text).replace("{template_body}", template_body)
         .replace("{region_name}", region_name or "").replace("{examples}", ""))
    return p + (f"\n<untersuchung>{region_name}</untersuchung>\n" if region_name else "")


def build_val_prompt(raw_dictation, generated_report):
    """Validator (Web Call 2) exakt aus App.tsx."""
    return _pp.val_prompt(raw_dictation, generated_report)


def check_contradictions(report, template_body):
    """Checkt ob Normalbefund-Sätze trotz Pathologie im Befund stehen geblieben sind.

    Kontextbewusst: Wörter wie "übrigen", "ansonsten", "übrige" qualifizieren
    eine Phrase als bewusste Einschränkung auf nicht-pathologische Bereiche.
    Solche qualifizierten Phrasen sind KEINE Widersprüche.
    """
    contradictions = []
    befund = report.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in report else ""
    befund_lower = befund.lower()

    # Liste von Normalbefund-Phrasen, die bei Pathologie nicht bleiben dürfen
    contradiction_checks = [
        ("Bandscheibenräume normal hoch", "Osteochondrose", ["Verschmälerung", "Intervertebralraums"]),
        ("Kein Nachweis von Discopathien", "Osteochondrose", ["Verschmälerung", "Intervertebralraums"]),
        ("Kein Nachweis von Facettengelenksarthrosen", "Facettengelenksarthrose", ["Degenerative Veränderungen", "Facetten"]),
        ("Gelenkflächen glatt und kongruent", "Arthrose", ["Gelenkspaltverschmälerung", "Sklerosierung", "Osteophyt"]),
        ("Gelenkränder unauffällig", "Arthrose", ["Osteophyt", "Sklerosierung", "Randwulst"]),
        ("Gelenksspalten normal weit", "Arthrose", ["Gelenkspaltverschmälerung", "Gelenksspaltenverschmälerung"]),
        ("Normale Form und Struktur der Gelenkkörper", "Fraktur", ["Fraktur", "Frakturlinie", "Dislokation"]),
        ("Normaler Achsenverlauf", "Skoliose", ["Skoliose", "skoliotisch"]),
        ("Normaler Achsenverlauf", "Streckhaltung", ["Streckhaltung"]),
        ("achsengerechte Stellung", "Skoliose", ["Skoliose", "skoliotisch"]),
        ("achsengerechte Stellung", "Streckhaltung", ["Streckhaltung"]),
        ("Knochenstruktur unauffällig", "Fraktur", ["Fraktur"]),
        ("Alle Wirbelkörper von normaler Form", "Fraktur", ["Fraktur"]),
    ]

    # Qualifikatoren, die eine Phrase als bewusste Einschränkung markieren
    qualifiers = ["übrigen", "übrige", "ansonsten", "anderen", "restlichen"]

    def is_qualified(phrase, text_lower):
        """Prüft ob die Phrase durch einen Qualifikator eingeschränkt ist."""
        idx = text_lower.find(phrase.lower())
        if idx == -1:
            return False
        # Schaue 60 Zeichen vor der Phrase nach Qualifikatoren
        window_before = text_lower[max(0, idx - 60):idx]
        # Und 60 Zeichen nach der Phrase (falls der Qualifikator danach kommt)
        window_after = text_lower[idx:idx + len(phrase) + 60]
        combined = window_before + " " + window_after
        return any(q in combined for q in qualifiers)

    for normal_phrase, pathology, expected_descriptors in contradiction_checks:
        if normal_phrase.lower() in befund_lower:
            # Skip wenn qualifiziert (z.B. "die übrigen Bandscheibenräume normal hoch")
            if is_qualified(normal_phrase, befund_lower):
                continue
            # Check if the pathology or its descriptors are also in the befund
            has_pathology = pathology.lower() in befund_lower or \
                           any(d.lower() in befund_lower for d in expected_descriptors)
            if has_pathology:
                contradictions.append(f"❌ '{normal_phrase}' noch im Befund trotz {pathology}")

    return contradictions


def run_test_case(name, template_key, diktat, expected_pathologies, token):
    template_body = TEMPLATES.get(template_key, {}).get("body", "")
    if not template_body:
        return {"name": name, "status": "ERROR", "issues": [f"Template '{template_key}' nicht gefunden"]}

    print(f"\n{'─'*60}")
    print(f"TEST: {name}")
    print(f"{'─'*60}")

    # Call #1: Generation
    try:
        gen_prompt = build_gen_prompt(diktat, template_body, region_name=derive_titel_harness(diktat, TEMPLATES[template_key].get("display_name", "")))
        t0 = time.time()
        report = call_gemini(gen_prompt, token, temperature=0.0, system=_pp.SYS_MSG)
        gen_time = time.time() - t0
    except Exception as e:
        return {"name": name, "status": "ERROR", "issues": [f"Gen call failed: {e}"]}

    # Call #2: Validation
    try:
        val_prompt = build_val_prompt(diktat, report)
        t0 = time.time()
        validated = call_gemini(val_prompt, token, temperature=0.0)
        val_time = time.time() - t0
    except Exception as e:
        return {"name": name, "status": "ERROR", "issues": [f"Val call failed: {e}"]}

    final = validated if validated and "## Befund" in validated else report
    final = _pp.br.nachbearbeiten(final)  # v3.2: wie Produktion (EXE + Web)
    was_corrected = validated.strip() != report.strip()

    # Checks
    issues = []
    befund = final.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in final else ""
    ergebnis = final.split("## Ergebnis")[1] if "## Ergebnis" in final else ""

    # 1. Widerspruchs-Check
    contradictions = check_contradictions(final, template_body)
    issues.extend(contradictions)

    # 2. Vollständigkeit: jede erwartete Pathologie im Ergebnis?
    for exp in expected_pathologies:
        if exp.lower() not in ergebnis.lower():
            issues.append(f"⚠️ '{exp}' fehlt im Ergebnis")

    # 3. Diagnosen im Befundtext?
    diagnosis_words = ["Osteochondrose", "Omarthrose", "Coxarthrose", "Gonarthrose",
                       "Spondylosis deformans", "Facettengelenksarthrose", "Morbus Scheuermann"]
    for dw in diagnosis_words:
        if dw.lower() in befund.lower() and dw.lower() not in template_body.lower():
            issues.append(f"⚠️ Diagnose '{dw}' im Befundtext statt Deskriptor")

    # 4. Erfundene Begriffe? (nur wenn NICHT im Diktat genannt — "Fehlhaltung" kann diktiert sein)
    invented = [inv for inv in ["Fehlhaltung"] if inv.lower() not in diktat.lower()]
    for inv in invented:
        if inv.lower() in ergebnis.lower():
            issues.append(f"⚠️ Erfundener Begriff '{inv}' im Ergebnis")
    # 4b. "Flachprofil" darf NIE im Report stehen (existiert radiologisch nicht)
    if "flachprofil" in final.lower():
        issues.append(f"❌ 'Flachprofil' im Befund — existiert radiologisch nicht (korrekt: flachbogige Skoliose)")

    # 5. Wurde korrigiert?
    if was_corrected:
        issues.append("📝 Call #2 hat korrigiert")

    status = "✅ PASS" if not contradictions and not any("❌" in i for i in issues) else "❌ FAIL"
    if issues and "❌" not in " ".join(issues):
        status = "⚠️ WARN"

    print(f"  Gen: {gen_time:.1f}s | Val: {val_time:.1f}s | Status: {status}")
    if issues:
        for i in issues:
            print(f"  {i}")
    else:
        print("  Keine Widersprüche gefunden ✅")

    # Print final result
    print(f"\n--- {name} FINALES ERGEBNIS ---")
    print(final[:600])

    return {"name": name, "status": status, "issues": issues, "report": final}


def main():
    print("=" * 70)
    print("VOLLSTÄNDIGER WIDERSPRUCHSTEST — Alle Regionen")
    print("=" * 70)

    results = []

    for name, tkey, diktat, expected in TEST_CASES:
        r = run_test_case(name, tkey, diktat, expected, None)
        results.append(r)
        time.sleep(1)  # Rate limit

    # Summary
    print(f"\n{'='*70}")
    print("ZUSAMMENFASSUNG")
    print(f"{'='*70}")
    passes = sum(1 for r in results if r["status"] == "✅ PASS")
    warns = sum(1 for r in results if r["status"] == "⚠️ WARN")
    fails = sum(1 for r in results if r["status"] == "❌ FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print(f"\n✅ PASS: {passes} | ⚠️ WARN: {warns} | ❌ FAIL: {fails} | ERROR: {errors}")
    print(f"Total: {len(results)}")

    print(f"\n{'─'*70}")
    for r in results:
        icon = {"✅ PASS": "✅", "⚠️ WARN": "⚠️", "❌ FAIL": "❌", "ERROR": "💥"}.get(r["status"], "?")
        print(f"{icon} {r['name']}")
        for issue in r.get("issues", []):
            print(f"    {issue}")


if __name__ == "__main__":
    main()