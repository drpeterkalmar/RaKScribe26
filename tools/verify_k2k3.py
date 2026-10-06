#!/usr/bin/env python3
"""tools/verify_k2k3.py — v2.11.1-Gate für Prüfbericht K2/K3 (Web-Kette Call1→Call2 mit ECHTEN App.tsx-Prompts,
gemini-3.5-flash @ EU). App-Guard wird nachgebildet: Befundteil nach Call2 < 70 % von Call1 → Call1 verwenden.
K2: Nervensono (N. medianus / N. ulnaris) — Normalbefund bleibt, 'Bild wie bei' bleibt, keine CSA im Ergebnis.
K3: 'Gelenksarthrose C3 bis C5' bleibt wörtlich im Ergebnis (nicht Facetten-/Uncovertebral-).
Aufruf: python3 tools/verify_k2k3.py [runs]"""
import json, re, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]  # Repo-Root (Skript liegt in tools/)
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
sys.argv = sys.argv[:1]
import test_all_regions as H
assert "gemini-3.5-flash" in H.VERTEX_URL
gem_ts = (ROOT / "web_app/src/gemini.ts").read_text()  # Umbau Schritt 18: Validator liegt in gemini.ts
import prod_pipeline as pp  # v3.2: Gen-Prompt = radiology_prompt.txt (eine Quelle EXE + Web), SYS_MSG wie Produktion
GEN = pp.GEN_PROMPT
VAL = pp.VAL_TEMPLATE
assert "restoreBildWieBei" in gem_ts and "NORMALBEFUND ERHALTEN" in VAL and "DIAGNOSEBEGRIFFE NIE ERSETZEN" in VAL


def befund(t):
    pre = t.split("## Ergebnis")[0]
    return (pre.split("## Befund")[1] if "## Befund" in pre else pre).strip()


def ergebnis(t):
    return t.split("## Ergebnis")[1] if "## Ergebnis" in t else ""


def chain(diktat, tkey):
    t = H.TEMPLATES[tkey]
    p1 = GEN.replace("{roh_text}", diktat).replace("{template_body}", t["body"]).replace("{region_name}", t["display_name"]).replace("{examples}", "")
    p1 += "\n<untersuchung>" + t["display_name"] + "</untersuchung>\n"
    c1 = re.sub(r"^```[a-z]*\s*|\s*```$", "", H.call_gemini(p1, temperature=0.0, system=pp.SYS_MSG).strip())
    c2 = re.sub(r"^```[a-z]*\s*|\s*```$", "", H.call_gemini(VAL.replace("${rawDictation}", diktat).replace("${generatedReport}", c1), temperature=0.0).strip())
    ratio = len(befund(c2)) / max(len(befund(c1)), 1)
    final = c1 if (ratio < 0.7 or "## Ergebnis" not in c2) else c2  # = App-Guard
    if final is c2:  # = restoreBildWieBei (App.tsx)
        oe, ve = ergebnis(c1), ergebnis(c2)
        for d in [x.strip() for x in re.findall(r"Bild wie bei ([^.\n]+)", oe)]:
            if d and ("Bild wie bei " + d) not in ve and d in ve:
                i = ve.find(d); ve = ve[:i] + "Bild wie bei " + ve[i:]
        final = c2.split("## Ergebnis")[0] + "## Ergebnis" + ve
    return c1, c2, final, ratio


CASES = [
    ("K2 N. medianus", "sonografie_nerv_medianus",
     "Hochauflösende Sonographie des N. medianus rechts: spindelförmige Auftreibung des N. medianus am Karpaltunneleingang, "
     "Querschnittsfläche 14 mm², vereinbar mit Karpaltunnelsyndrom. Ansonsten unauffällig.",
     lambda f, c1: [("Normalbefund erhalten (Befund ≥ 70 % Call1)", len(befund(f)) >= 0.7 * len(befund(c1))),
                    ("'Bild wie bei' im Ergebnis", "bild wie bei" in ergebnis(f).lower()),
                    ("kein 'vereinbar mit' im Ergebnis", "vereinbar" not in ergebnis(f).lower()),
                    ("keine CSA/mm² im Ergebnis", "mm²" not in ergebnis(f) and "querschnitt" not in ergebnis(f).lower())]),
    ("K2 N. ulnaris", "sonografie_nerv_ulnaris",
     "Hochauflösende Sonographie des N. ulnaris links: Auftreibung des Nervs im Sulcus nervi ulnaris mit Querschnittsfläche 13 mm², "
     "kompatibel mit Sulcus-nervi-ulnaris-Syndrom. Ansonsten unauffällig.",
     lambda f, c1: [("Normalbefund erhalten (Befund ≥ 70 % Call1)", len(befund(f)) >= 0.7 * len(befund(c1))),
                    ("'Bild wie bei' im Ergebnis", "bild wie bei" in ergebnis(f).lower()),
                    ("keine CSA/mm² im Ergebnis", "mm²" not in ergebnis(f) and "querschnitt" not in ergebnis(f).lower())]),
    ("K3 Gelenksarthrose", "halswirbelsäule_in_2_ebenen",
     "HWS: Osteochondrose C2 bis C4. Gelenksarthrose C3 bis C5. Hochgradige Diskopathie C4 bis C7.",
     lambda f, c1: [("'Gelenksarthrose C3' wörtlich im Ergebnis", re.search(r"(?<![a-zäöü])gelenksarthrose c3", ergebnis(f).lower()) is not None),
                    ("keine Facetten-/Uncovertebral-Umdeutung", not re.search(r"facetten|uncovertebral|unkovertebral", ergebnis(f).lower()))]),
]
fails, guard_hits, val_short = 0, 0, 0
for name, tk, dk, checks in CASES:
    for r in range(RUNS):
        c1, c2, f, ratio = chain(dk, tk)
        guard_hits += f is c1 and c1 != c2
        val_short += ratio < 0.7
        res = checks(f, c1)
        bad = [n for n, ok in res if not ok]
        fails += bool(bad)
        print(f"{'✅' if not bad else '❌'} {name} run{r+1}  Call2/Call1-Befund={ratio:.2f}  {'; '.join(bad)}")
        if bad:
            print("   ERGEBNIS:", ergebnis(f).strip().replace("\n", " | ")[:300])
print(f"\nFAILS={fails}  Validator-Kürzung<70 %: {val_short}  Guard griff: {guard_hits}")
sys.exit(1 if fails else 0)
