#!/usr/bin/env python3
"""tests/offline/misheard_test.py — prüft misheard_words.json gegen misheard_tests.json mit der EXE-Engine
(source_code/misheard.py). Das Web-Pendant ist web_app/misheard_test.mjs; beide müssen grün sein.

  /usr/bin/python3 tests/offline/misheard_test.py
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]  # Umbau Schritt 24: Gate liegt in tests/offline/
sys.path.insert(0, str(ROOT / "source_code"))
import misheard  # noqa: E402

data = misheard.load(str(ROOT))
assert data["_path"], "misheard_words.json nicht gefunden"
compiled = misheard.compile_rules(data)
cases = json.load(open(ROOT / "misheard_tests.json"))["cases"]
fail = 0
for c in cases:
    got = misheard.apply(c["in"], compiled)
    ok = got == c["out"]
    fail += not ok
    print(("PASS" if ok else "FAIL"), "|", c["in"][:60], "→", got[:70] if ok else f"{got!r}  (erwartet {c['out']!r})")
blk = misheard.prompt_block(data)
print(f"\n[PY] {len(cases) - fail}/{len(cases)} PASS · {len(compiled)} auto-Regexe · "
      f"{sum(1 for r in data['rules'] if r['mode'] == 'llm')} llm-Hinweise · Prompt-Block {len(blk)} Zeichen · {data['_path']}")

# Dieselben Fälle durch die TypeScript-Engine (Web-App) — beide müssen identisch ersetzen
import subprocess
ts = subprocess.run(["node", "--experimental-strip-types", "misheard_test.mjs"], cwd=ROOT / "web_app",
                    capture_output=True, text=True)
ts_fail = ts.returncode != 0
print("[TS]", (ts.stdout.strip().splitlines() or ["(keine Ausgabe)"])[-1], "" if not ts_fail else f"\n{ts.stdout}\n{ts.stderr}")
# Call-0-Prompt-Block: TypeScript und Python müssen denselben Text erzeugen (Harness = Web-App)
ts_blk = subprocess.run(["node", "--experimental-strip-types", "misheard_test.mjs", "--block"], cwd=ROOT / "web_app",
                        capture_output=True, text=True).stdout
py_blk = misheard.prompt_block_web(data)
print("[BLOCK] TS == PY:", ts_blk == py_blk, f"({len(py_blk)} Zeichen)")
sys.exit(1 if (fail or ts_fail or ts_blk != py_blk) else 0)
