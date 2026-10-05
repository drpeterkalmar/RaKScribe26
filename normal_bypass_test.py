#!/usr/bin/env python3
"""normal_bypass_test.py — v3.2-Gate: Normalbefund-Bypass (Python- UND TS-Engine gegen dieselben Fixtures)
+ jedes Template hat ein Normal-Ergebnis + Bypass-Report enthält NIE das rohe Diktat im Ergebnis.

    /usr/bin/python3 normal_bypass_test.py
"""
import json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "source_code"))
from normalbypass import is_pure_normal_finding  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text())
assert T == json.loads((ROOT / "web_app/src/templates.json").read_text()), "EXE/Web templates divergiert"
DN = [v["display_name"] for v in T.values()]
cases = json.loads((ROOT / "normal_bypass_tests.json").read_text())["cases"]
fail = 0
print("── Python-Engine ──")
for c in cases:
    got = is_pure_normal_finding(c["in"], DN)
    ok = got == c["bypass"]
    fail += not ok
    print("PASS" if ok else "FAIL", "|", repr(c["in"])[:70], "→", got)

print("\n── TS-Engine (web_app/src/normalbypass.ts) ──")
r = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", str(ROOT / "web_app/normalbypass_test.mjs")],
                   capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())
fail += r.returncode != 0

print("\n── Normal-Ergebnis je Template ──")
ohne = [k for k, v in T.items() if not v.get("ergebnis")]
ok = set(ohne) == {"knochendichtemessung_dexa", "ultraschall_gezielte_blockade"}
fail += not ok
print("PASS" if ok else "FAIL", f"| {len(T) - len(ohne)}/{len(T)} mit 'ergebnis', ohne: {ohne}")
for k, want in [("thorax_in_2_ebenen", "Unauffälliger Befund."), ("kniegelenk_in_2_ebenen", "Regelrechte Darstellung des Kniegelenkes."),
                ("halswirbelsäule_in_2_ebenen", "Regelrechte Darstellung der HWS.")]:
    ok = T[k].get("ergebnis") == want
    fail += not ok
    print("PASS" if ok else "FAIL", f"| {k}: {T[k].get('ergebnis')!r}")

print(f"\n{'GRÜN' if not fail else f'{fail} FEHLER'}")
sys.exit(1 if fail else 0)
