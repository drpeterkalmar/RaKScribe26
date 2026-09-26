#!/usr/bin/env python3
"""test_parts_join.py — v2.11.1 Offline-Gate (deterministisch, ohne API):
Die ECHTEN Helper aus App.tsx (per esbuild transpiliert) und RaKScribe.py (AST-extract)
gegen synthetische Gemini-Antworten: Split '## L' | 'endenwirbelsäule…' (mit thoughtSignature),
Thought-Part, abgeschnittene Antwort (MAX_TOKENS), fehlendes Ergebnis, Befund ohne '## Befund'-Zeile.
Plus Rohantworten aus parts_stress_raw.json, falls vorhanden. Exit 1 bei Abweichung."""
import ast, json, pathlib, re, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).parent
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

# --- TS: echte Helper extrahieren + mit esbuild transpilieren ---
app = (ROOT / "web_app/src/App.tsx").read_text()
names = ["joinGeminiText", "geminiFinishedOk", "befundSection", "isCompleteReport"]
src = []
for n in names:
    m = re.search(rf"^const {n} = .*?;\n(?=\n|const |//)", app, re.S | re.M)
    assert m, n
    src.append(m.group(0))
ts = "\n".join(src) + "\nconst cases = " + json.dumps([[c[0], c[1]] for c in CASES], ensure_ascii=False) + ";\n" \
     "console.log(JSON.stringify(cases.map(([n, d]) => { const t = joinGeminiText(d); return [n, t, isCompleteReport(t.trim()), geminiFinishedOk(d)]; })));\n"
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / "t.ts"; p.write_text(ts)
    js = subprocess.run(["npx", "esbuild", str(p), "--format=cjs", "--log-level=error"], cwd=ROOT / "web_app",
                        capture_output=True, text=True, check=True).stdout
    (pathlib.Path(td) / "t.js").write_text(js)
    ts_out = json.loads(subprocess.run(["node", str(pathlib.Path(td) / "t.js")], capture_output=True, text=True, check=True).stdout)

# --- PY: echte EXE-Logik (AST) ---
rak = (ROOT / "source_code/RaKScribe.py").read_text()
ns = {}
for node in ast.walk(ast.parse(rak)):
    if isinstance(node, ast.FunctionDef) and node.name == "_report_complete":
        exec(ast.get_source_segment(rak, node), ns)
m = re.search(r'txt = ("".join\(p\.get\("text", ""\) for p in cand\.get\("content", \{\}\)\.get\("parts", \[\]\)\s*\n\s*if isinstance\(p\.get\("text"\), str\) and not p\.get\("thought"\)\))', rak)
assert m, "EXE-Join-Ausdruck nicht gefunden"
join_expr = re.sub(r"\s*\n\s*", " ", m.group(1))

fails = 0
for (name, d, exp, comp, fin), (tn, tt, tcomp, tfin) in zip(CASES, ts_out):
    cand = d["candidates"][0]
    pt = eval(join_expr, {"cand": cand})
    pcomp = ns["_report_complete"](pt.strip())
    pfin = cand.get("finishReason", "STOP") == "STOP"
    ok = (tt == exp == pt) and (tcomp == comp == pcomp) and (tfin == fin == pfin)
    fails += not ok
    print(f"{'✅' if ok else '❌'} {name:22s} TS(voll={tcomp},stop={tfin}) PY(voll={pcomp},stop={pfin}) erwartet(voll={comp},stop={fin})")
print(f"\n{len(CASES) - fails}/{len(CASES)} PASS")
sys.exit(1 if fails else 0)
