#!/usr/bin/env python3
"""tools/parts_stress.py — v2.11.1-Gate: N echte Gemini-3.5-Gen-Aufrufe (Standard 20, höchstens 100) (EXE-Prompt radiology_prompt.txt,
Harness-Fälle rotierend). Pro Antwort: Anzahl parts, alte Lesart (parts[0]) vs. neue (join).
Rohantworten → parts_stress_raw.json (für den TS-Paritätstest). Exit 1 wenn neue Lesart je leer/unvollständig."""
import sys as _kb_sys, pathlib as _kb_pl; _kb_sys.path.insert(0, str(_kb_pl.Path(__file__).resolve().parent))
import kosten_bremse  # noqa: F401,E402  Test-Budget ≤5 $/Monat, Vertex-Guthaben 20 $ (Peter 14.11.2026)
import json, sys, time, re, pathlib, urllib.request, urllib.error
ROOT = pathlib.Path(__file__).resolve().parents[1]  # Repo-Root (Skript liegt in tools/)
sys.path.insert(0, str(ROOT / "tools"))
import testkosten  # noqa: E402
sys.argv = [sys.argv[0]] + (sys.argv[1:] or ["20"])
N = min(int(sys.argv[1]), 100)
import test_all_regions as H
TPL = (ROOT / "radiology_prompt.txt").read_text()
SYS = "Du bist ein präziser Radiologie-Assistent der Praxis 'Röntgen am Kai'. Nutze ## Befund und ## Ergebnis als einzige Haupttitel."


def complete(t):
    return "## Befund" in t and "## Ergebnis" in t and len(t.split("## Ergebnis")[1].strip()) > 5


raw, stats = [], {"multi": 0, "old_bad": 0, "new_bad": 0, "err": 0}
for i in range(N):
    name, tk, dk, exp = H.TEST_CASES[i % len(H.TEST_CASES)]
    t = H.TEMPLATES[tk]
    p = TPL.replace("{roh_text}", dk).replace("{template_body}", t["body"]).replace("{region_name}", t["display_name"])
    p = p.replace("{examples}", "") + "\n<untersuchung>" + t["display_name"] + "</untersuchung>\n"
    try:  # kaiscribe-testkosten-n1: über testkosten (Testprojekt, Kostenbuch, Obergrenze), kein Praxis-Schlüssel mehr
        d = testkosten.gemini_roh(p, system=SYS)[1]
    except Exception as e:
        print(i, "ERR", str(e)[:120]); d = None
    if d is None:
        stats["err"] += 1; print(i, "ERR"); continue
    parts = d["candidates"][0]["content"].get("parts", [])
    old = (parts[0].get("text", "") if parts else "").strip()
    new = "".join(x.get("text", "") for x in parts if isinstance(x.get("text"), str) and not x.get("thought")).strip()
    if len(parts) > 1: stats["multi"] += 1
    if not complete(old): stats["old_bad"] += 1
    if not complete(new): stats["new_bad"] += 1
    raw.append(d)
    print(f"{i:2d} parts={len(parts)} alt={'OK ' if complete(old) else 'KAPUTT'} neu={'OK' if complete(new) else 'KAPUTT'}  {name[:40]}"
          + (f"  | Split: …{parts[0].get('text','')[-25:]!r} ‖ {parts[1].get('text','')[:25]!r}…" if len(parts) > 1 else ""))
(ROOT / "docs" / "benchmarks" / "parts_stress_raw.json").write_text(json.dumps(raw, ensure_ascii=False))
print("\nSUMME", json.dumps(stats), f"n={len(raw)}")
sys.exit(1 if stats["new_bad"] or stats["err"] else 0)
