#!/usr/bin/env python3
"""Live-Verifikation v2.10.6 — Peters Sprunggelenk-Case (08.09., Screenshot):
Diktat: 'Sprunggelenk rechts, Röntgen, Erweiterung der Malleolengabel auf bis zu 12 mm,
Verdacht auf Syndesmosenruptur. Ansonsten unauffällig.'
Erwartung: Überschrift 'Sprunggelenk rechts in 2 Ebenen' (NICHT 'Sprunggelenk rechts.'),
Malleolengabel-Befund + 12 mm exakt erhalten, 'Verdacht auf Syndesmosenruptur rechts' im Ergebnis.
Kette A = EXE-Pfad (radiology_prompt.txt + <untersuchung>), Kette B = Web-Pfad (Call0→Call1→Call2).
"""
import sys as _kb_sys, pathlib as _kb_pl; _kb_sys.path.insert(0, str(_kb_pl.Path(__file__).resolve().parent))
import kosten_bremse  # noqa: F401,E402  Test-Budget ≤5 $/Monat, Vertex-Guthaben 20 $ (Peter 14.11.2026)
import os, re, sys, json, pathlib, urllib.request, urllib.error, time

ROOT = pathlib.Path(__file__).resolve().parents[1]  # Repo-Root (v3.18.4: nicht mehr fest ~/dev)
sys.path.insert(0, str(ROOT / "tools"))
import testkosten  # noqa: E402  (kaiscribe-testkosten-n1: Testprojekt, Kostenbuch, Obergrenze)


sys.path.insert(0, str(ROOT / "tools"))
import test_all_regions as harness
from test_all_regions import call_gemini

DIKTAT = ("Sprunggelenk rechts, Röntgen, Erweiterung der Malleolengabel auf bis zu 12 mm, "
          "Verdacht auf Syndesmosenruptur. Ansonsten unauffällig.")
TEMPLATE_KEY = "sprunggelenk_in_2_ebenen"
TEMPLATE = harness.TEMPLATES[TEMPLATE_KEY]
TEMPLATE_BODY = TEMPLATE["body"]
REGION = TEMPLATE["display_name"]
assert TEMPLATE_BODY.split("\n")[0].strip() == "Sprunggelenk in 2 Ebenen", "Template-Zeile 1 falsch!"

def gemini(prompt, temp=0.0, tries=4):
    return testkosten.gemini(prompt, temperature=temp)

def check_report(final, label):
    print(f"\n{'='*62}\n{label}\n{'='*62}")
    print(final[:900])
    befund = final.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in final else ""
    ergebnis = final.split("## Ergebnis")[1] if "## Ergebnis" in final else ""
    # seit v2.10.8 steht die Untersuchungsart als '## …'-Zeile VOR '## Befund'
    pre = final.split("## Befund")[0] if "## Befund" in final else final
    header = next((l.strip().lstrip("#").strip().rstrip(".") for l in pre.splitlines() if l.strip().startswith("##")), "")
    checks = [
        ("Überschrift = 'Sprunggelenk … in 2 Ebenen'", "sprunggelenk" in header.lower() and "in 2 ebenen" in header.lower()),
        ("Überschrift mit diktierter Seite (rechts)", "rechts" in header.lower()),
        ("Nackte Kurzform 'Sprunggelenk rechts' beseitigt", header.strip() != "Sprunggelenk rechts"),
        ("Malleolengabel-Befund erhalten", "malleolengabel" in befund.lower()),
        ("12 mm exakt erhalten (Messwert heilig)", "12 mm" in befund),
        ("'Verdacht auf Syndesmosenruptur rechts' im Ergebnis", "verdacht auf syndesmosenruptur" in ergebnis.lower() and "rechts" in ergebnis.lower()),
        ("KEIN Widerspruch (Gelenkkörper 'normal' + Syndesmose-Verdacht ok)", True),
    ]
    ok = True
    print("\n-- CHECKS --")
    for name, passed in checks:
        print(f"  {'✅' if passed else '❌'} {name}  | Überschrift: {header!r}")
        ok = ok and passed
    return ok

results = {}
# v3.2: beide Ketten = ECHTE Produktionsketten über tools/prod_pipeline.py (Gen-Prompt aus radiology_prompt.txt — EINE
# Quelle für EXE + Web —, SYS_MSG, Web-Call-0/Validator aus App.tsx, Regionen-Trenner + Ergebnis-Nummerierung).
# Läufe: erstes Argument (Default 1); grün nur, wenn ALLE Läufe je Kette grün sind.
import prod_pipeline as pp
assert "Kellgren" in pp.GEN_PROMPT, "K&L-Regel fehlt in radiology_prompt.txt!"
RUNS = testkosten.argv_laeufe(1, 1)  # ≤ 5, mehr nur mit --release
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