#!/usr/bin/env python3
"""test_parts_join.py — v2.11.1 Offline-Gate (deterministisch, ohne API):
Die ECHTEN Helper aus web_app/src/gemini.ts und source_code/gemini.py (beide direkt importiert)
gegen synthetische Gemini-Antworten: Split '## L' | 'endenwirbelsäule…' (mit thoughtSignature),
Thought-Part, abgeschnittene Antwort (MAX_TOKENS), fehlendes Ergebnis, Befund ohne '## Befund'-Zeile.
Plus Rohantworten aus parts_stress_raw.json, falls vorhanden. Exit 1 bei Abweichung."""
import json, pathlib, re, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "source_code"))
import gemini  # noqa: E402  (Umbau Schritt 14: kein AST-/Regex-Extrakt aus RaKScribe.py mehr)
FULL = ("## Lendenwirbelsäule in 2 Ebenen\n\n## Befund\nVerschmälerung des Intervertebralraums L4/L5 mit subchondraler Sklerosierung. "
        "Übrige Bandscheibenräume normal hoch.\n\n## Ergebnis\n1. Osteochondrose L4/L5.")
def resp(parts, fr="STOP"):
    return {"candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": fr}]}
CASES = [  # (name, response, erwarteter Text, vollständig?, finishOk?)
    ("single", resp([{"text": FULL}]), FULL, True, True),
    ("split ## L", resp([{"text": "## L"}, {"text": FULL[4:], "thoughtSignature": "abc"}]), FULL, True, True),
    ("split 3", resp([{"text": FULL[:30]}, {"text": FULL[30:90]}, {"text": FULL[90:]}]), FULL, True, True),
    ("thought-part", resp([{"text": "denke nach…", "thought": True}, {"text": FULL}]), FULL, True, True),
    ("max_tokens", resp([{"text": FULL[:80]}], "MAX_TOKENS"), FULL[:80], False, False),
    ("kein ergebnis", resp([{"text": FULL.split("## Ergebnis")[0]}]), FULL.split("## Ergebnis")[0], False, True),
    ("ohne ##Befund-Zeile", resp([{"text": FULL.replace("## Befund\n", "")}]), FULL.replace("## Befund\n", ""), True, True),
    ("leer", resp([]), "", False, True),
]
raw_file = ROOT / "parts_stress_raw.json"
if raw_file.exists():
    for i, d in enumerate(json.loads(raw_file.read_text())[:20]):
        t = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought"))
        CASES.append((f"echt#{i}", d, t, True, True))

# --- TS: echte Helper aus web_app/src/gemini.ts (Umbau Schritt 18: direkt importiert, kein esbuild-Extrakt mehr) ---
gem_url = (ROOT / "web_app" / "src" / "gemini.ts").as_uri()
js = (f"import {{ joinGeminiText, isCompleteReport, geminiFinishedOk }} from {json.dumps(gem_url)};\n"
      "const cases = " + json.dumps([[c[0], c[1]] for c in CASES], ensure_ascii=False) + ";\n"
      "console.log(JSON.stringify(cases.map(([n, d]) => { const t = joinGeminiText(d); return [n, t, isCompleteReport(t.trim()), geminiFinishedOk(d)]; })));\n")
with tempfile.TemporaryDirectory() as td:
    (pathlib.Path(td) / "t.mjs").write_text(js)
    ts_out = json.loads(subprocess.run(["node", "--experimental-strip-types", "--no-warnings", str(pathlib.Path(td) / "t.mjs")],
                                       capture_output=True, text=True, check=True).stdout)

# --- PY: echte EXE-Logik (source_code/gemini.py) ---
fails = 0
for (name, d, exp, comp, fin), (tn, tt, tcomp, tfin) in zip(CASES, ts_out):
    cand = d["candidates"][0]
    pt = gemini.join_text(cand)
    pcomp = gemini.report_complete(pt.strip())
    pfin = gemini.finish_ok(cand)
    ok = (tt == exp == pt) and (tcomp == comp == pcomp) and (tfin == fin == pfin)
    fails += not ok
    print(f"{'✅' if ok else '❌'} {name:22s} TS(voll={tcomp},stop={tfin}) PY(voll={pcomp},stop={pfin}) erwartet(voll={comp},stop={fin})")
print(f"\n{len(CASES) - fails}/{len(CASES)} PASS")
sys.exit(1 if fails else 0)
