#!/usr/bin/env python3
"""befund_regeln_test.py — v3.2-Gate: deterministische Befund-Regeln, EXE- UND Web-Engine.

Prüft source_code/befund_regeln.py (EXE) und web_app/src/befundRegeln.ts (Web, per Node)
gegen dieselbe Tabelle befund_regeln_fixtures.json: Regionen-Trenner, Ergebnis-Nummerierung,
Normalbefund-Erkennung, Seite in der Bypass-Überschrift, Prompt-Versionsmarker. Dazu die
EXE-Prompt-Auswahl (alte radiology_prompt_v4.txt darf nicht mehr still gewinnen) und die
Sync-Checks Prompt-Datei ↔ App.tsx/RaKScribe.py.

  /usr/bin/python3 befund_regeln_test.py
"""
import json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402

F = json.loads((ROOT / "befund_regeln_fixtures.json").read_text())
fail = 0


def check(ok, label, detail=""):
    global fail
    fail += not ok
    print(("PASS" if ok else "FAIL"), "|", label, "" if ok else f"\n      {detail}")


print("── PY: Regionen-Trenner")
for c in F["split"]:
    got = br.split_regionen(c["in"])
    check(got == c["out"], c["name"], f"got {got!r}")
print("── PY: Ergebnis-Nummerierung")
for c in F["nummerieren"]:
    got = br.ergebnis_nummerieren(c["in"])
    check(got == c["out"], c["name"], f"got {got!r}")
print("── PY: CSA-Regel (Skill 3ac)")
for c in F["csa"]:
    got = br.csa_bereinigen(c["in"])
    check(got == c["out"], c["name"], f"got {got!r}")
print("── PY: '## Befund' sichern")
for c in F["befund_sichern"]:
    got = br.befund_ueberschrift_sichern(c["in"])
    check(got == c["out"], c["name"], f"got {got!r}")
print("── PY: Bypass-Ergebnis mit Seite")
for c in F["ergebnis_seite"]:
    got = br.ergebnis_mit_seite(c["ergebnis"], c["raw"])
    check(got == c["out"], f"{c['ergebnis'][:40]} + '{c['raw']}'", f"got {got!r}")
print("── PY: Seite in der Bypass-Überschrift")
for c in F["titel_seite"]:
    got = br.titel_mit_seite(c["titel"], c["raw"])
    check(got == c["out"], f"{c['titel']} + '{c['raw']}'", f"got {got!r}")
print("── PY: Prompt-Versionsmarker")
for c in F["prompt_version"]:
    check(br.prompt_version(c["in"]) == c["version"] and br.strip_prompt_marker(c["in"]) == c["stripped"], c["in"][:50])

print("── PY: EXE-Prompt-Auswahl (waehle_prompt)")
NEU = "<!-- RAKSCRIBE_PROMPT_VERSION: 2026-10-05-a -->\nNEU"
ALT_V4 = "<role>alter v4-Prompt ohne Nummerierung</role>"
ALT_MARK = "<!-- RAKSCRIBE_PROMPT_VERSION: 2026-09-01-x -->\nALT"
GLEICH_EDIT = "<!-- RAKSCRIBE_PROMPT_VERSION: 2026-10-05-a -->\nNEU + lokale Ergänzung"
t, q, h = br.waehle_prompt(NEU, [("radiology_prompt_v4.txt", ALT_V4), ("radiology_prompt.txt", "")])
check(t == NEU and q == "eingebaut" and "radiology_prompt_v4.txt" in h, "alte v4 ohne Marker → eingebauter Prompt + Hinweis", (q, h))
t, q, h = br.waehle_prompt(NEU, [("radiology_prompt_v4.txt", ""), ("radiology_prompt.txt", ALT_MARK)])
check(t == NEU and "2026-09-01-x" in h, "gespeicherter alter Prompt (älterer Marker) → eingebaut", (q, h))
t, q, h = br.waehle_prompt(NEU, [("radiology_prompt_v4.txt", ""), ("radiology_prompt.txt", GLEICH_EDIT)])
check(t == GLEICH_EDIT and q == "radiology_prompt.txt" and not h, "lokal gespeichert mit aktuellem Marker → lokal", (q, h))
t, q, h = br.waehle_prompt("", [("radiology_prompt_v4.txt", ""), ("radiology_prompt.txt", ALT_V4)])
check(t == ALT_V4, "ohne Bundle (Entwicklung) → lokale Datei", (q, h))

print("── SYNC: Prompt-Datei ↔ Apps")
prompt = (ROOT / "radiology_prompt.txt").read_text()
pv = br.prompt_version(prompt)
check(bool(pv), "radiology_prompt.txt hat Versionsmarker", pv)
app = (ROOT / "web_app/src/App.tsx").read_text()
check("radiology_prompt.txt?raw" in app, "Web importiert radiology_prompt.txt (eine Quelle)")
check("const newDefaultPrompt =" not in app, "kein zweiter Gen-Prompt mehr in App.tsx")
exe = (ROOT / "source_code/RaKScribe.py").read_text()
pl = (ROOT / "source_code/pipeline.py").read_text()  # Umbau Schritt 15: Befund-Kette der EXE in pipeline.py
check("befund_regeln" in exe and "waehle_prompt" in exe and "_pl.befund_aus_diktat(" in exe
      and "br.split_regionen(raw)" in pl and "br.nachbearbeiten(roh)" in pl,
      "EXE nutzt befund_regeln (Prompt-Wahl, Trenner, Nummerierung über pipeline.py)")
wf = (ROOT / ".github/workflows/build-exe.yml").read_text()
check("radiology_prompt.txt;." in wf and "befund_regeln" in wf, "EXE-Build bündelt Prompt + befund_regeln")
import gemini  # noqa: E402  (Umbau Schritt 14: SYS_MSG der EXE liegt in gemini.py)
gem_ts = (ROOT / "web_app/src/gemini.ts").read_text()  # Umbau Schritt 18: SYS_MSG der Web-App liegt in gemini.ts
m_web = re.search(r'export const SYS_MSG =\s*((?:"[^"]*"\s*\+?\s*)+);', gem_ts)
sys_exe = gemini.SYS_MSG
sys_web = "".join(re.findall(r'"([^"]*)"', m_web.group(1))) if m_web else None
check(sys_exe is not None and sys_exe == sys_web, "systemInstruction EXE == Web", f"EXE={sys_exe!r}\n      WEB={sys_web!r}")

print("── TS: dieselben Fixtures durch web_app/src/befundRegeln.ts")
ts = subprocess.run(["node", "--experimental-strip-types", "befund_regeln_test.mjs"], cwd=ROOT / "web_app",
                    capture_output=True, text=True)
for ln in ts.stdout.strip().splitlines():
    if not ln.startswith("PASS"):
        print("  [TS]", ln)
if ts.returncode != 0:
    fail += 1
    print(ts.stderr[-2000:])
print(f"\n{'✅ ALLE GRÜN' if not fail else f'❌ {fail} FAIL'} (PY + TS)")
sys.exit(1 if fail else 0)
