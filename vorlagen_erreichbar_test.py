"""Gate v3.2.3 (Peter 06.10.): Jede Vorlage ist erreichbar und wird korrekt priorisiert — EXE = Web.
1. Erreichbarkeit: "<Vorlagenname> unauffällig" und "<Vorlagenname> rechts unauffällig" treffen für ALLE Vorlagen ihren Key.
2. Vorrang: vorlagen_vorrang_tests.json (Kollisionsfälle: Vorfuß/Fuß, Funktion/HWS, MRT/Röntgen, Blockade/Sono …).
3. Parität: echte EXE-detect_template (AST-Extract) und Web-detectTemplate (Function-Extract) liefern dasselbe.
Aufruf: /usr/bin/python3 vorlagen_erreichbar_test.py"""
import ast, json, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
ns = {"re": re, "RADIOLOGY_TEMPLATES": T, "br": br}
for n in ast.parse((ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")).body:
    if isinstance(n, ast.FunctionDef) and n.name == "detect_template":
        exec(compile(ast.Module([n], []), n.name, "exec"), ns)
det = ns["detect_template"]

faelle = []
for k, v in T.items():
    dn = v["display_name"].strip()
    if "(allgemein)" in dn.lower():  # interne Sammel-Vorlage: erreichbar über den Fallback ihrer Gruppe (Vorrang-Fälle)
        continue
    faelle += [[f"{dn} unauffällig", k], [f"{dn} rechts unauffällig", k]]
n_reach = len(faelle)
faelle += json.loads((ROOT / "vorlagen_vorrang_tests.json").read_text(encoding="utf-8"))

with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
    json.dump(faelle, f, ensure_ascii=False)
r = subprocess.run(["node", "detect_test.mjs", f.name], cwd=ROOT / "web_app", capture_output=True, text=True)
if r.returncode:
    print(r.stderr); sys.exit(1)
web = json.loads(r.stdout)

fails = 0
for i, (d, soll) in enumerate(faelle):
    e, w = det(d), web[d]
    teil = "Erreichbar" if i < n_reach else "Vorrang"
    if e != soll or w != soll:
        fails += 1
        print(f"❌ {teil}: {d!r}\n     soll {soll} | EXE {e} | Web {w}")
print(f"\n{len(T)} Vorlagen, {n_reach} Erreichbarkeits- + {len(faelle) - n_reach} Vorrang-Fälle, je EXE + Web")
print("✅ ALLE VORLAGEN ERREICHBAR, VORRANG + PARITÄT PASS" if not fails else f"❌ {fails} FAIL")
sys.exit(1 if fails else 0)
