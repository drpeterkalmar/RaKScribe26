"""Gate v3.2.3 (Peter 06.10.): Jede Vorlage ist erreichbar und wird korrekt priorisiert — EXE = Web.
1. Erreichbarkeit: "<Vorlagenname> unauffällig" und "<Vorlagenname> rechts unauffällig" treffen für ALLE Vorlagen ihren Key.
2. Vorrang: vorlagen_vorrang_tests.json (Kollisionsfälle: Vorfuß/Fuß, Funktion/HWS, MRT/Röntgen, Blockade/Sono …).
3. Parität: echte EXE-detect_template (source_code/detect.py) und Web-detectTemplate liefern dasselbe.
Aufruf: /usr/bin/python3 tests/offline/vorlagen_erreichbar_test.py"""
import json, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]  # Umbau Schritt 24: Gate liegt in tests/offline/
sys.path.insert(0, str(ROOT / "source_code"))
import detect

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
def det(d):
    return detect.detect_template(d, T)

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
