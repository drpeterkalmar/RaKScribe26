#!/usr/bin/env python3
"""Live-Verifikation v2.10.6 — Peters Knie-Case (08.09., Screenshot):
Diktat: 'Kniegelenk links, Röntgen, maßgradige Gonarthrose des medialen Femorotibialkompartiments,
geringgradige Retropatellararthrose. Ansonsten unauffällig.'
Erwartung: Überschrift 'Kniegelenk links in 2 Ebenen' (NICHT nacktes 'Kniegelenk'),
Ergebnis mit beiden Kompartimenten, Grad-Adjektiven und K&L zum Adjektiv (v3.18.5: Grad 3 + Grad 2).
Kette A = EXE-Pfad (radiology_prompt.txt + <untersuchung>), Kette B = Web-Pfad (Call0→Call1→Call2,
Prompts exakt aus App.tsx extrahiert).
"""
import os, re, sys, json, pathlib, urllib.request, urllib.error, time

ROOT = pathlib.Path(__file__).resolve().parents[1]  # Repo-Root (v3.18.4: nicht mehr fest ~/dev)
sys.path.insert(0, str(ROOT / "tools"))
import testkosten  # noqa: E402  (kaiscribe-testkosten-n1: Testprojekt, Kostenbuch, Obergrenze)


sys.path.insert(0, str(ROOT / "tools"))
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
    return testkosten.gemini(prompt, temperature=temp)

def check_report(final, label):
    print(f"\n{'='*62}\n{label}\n{'='*62}")
    print(final[:900])
    befund = final.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in final else ""
    ergebnis = final.split("## Ergebnis")[1] if "## Ergebnis" in final else ""
    # seit v2.10.8 steht die Untersuchungsart als '## …'-Zeile VOR '## Befund'
    pre = final.split("## Befund")[0] if "## Befund" in final else final
    header = next((l.strip().lstrip("#").strip() for l in pre.splitlines() if l.strip().startswith("##")), "")
    lower = final.lower()
    checks = [
        ("Überschrift = 'Kniegelenk … in 2 Ebenen'", "kniegelenk" in header.lower() and "in 2 ebenen" in header.lower()),
        ("Überschrift mit diktierter Seite (links)", "links" in header.lower()),
        ("Nackte Kurzform 'Kniegelenk' als Überschrift beseitigt", header.strip() != "Kniegelenk"),
        # v3.18.5 (Nachtrag RH 99): diktierte Arthrosen mit Adjektiv → K&L zum Adjektiv (maßgradig 3, geringgradig 2)
        ("K&L Grad 3 + Grad 2 im Ergebnis", "grad 3 nach kellgren" in ergebnis.lower() and "grad 2 nach kellgren" in ergebnis.lower()),
        ("Grad-Adjektive bleiben (mäßig/gering)", "geringgradig" in ergebnis.lower() and ("mäßig" in ergebnis.lower() or "maßgradig" in ergebnis.lower())),
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