#!/usr/bin/env python3
"""tools/verify_widerspruch.py — Live-Check v3.15.5 (Peter 15.10.): umschriebene Skelettbefunde vs. Normalsätze der Vorlage.
EXE-Kette (pipeline.befund_aus_diktat, dieselbe Funktion wie RaKScribe.py) + Web-Kette (Call 0/1/2 wie pipeline.ts) mit
echtem Gemini (Hermes-SA-Bearer wie test_all_regions), synthetische Diktate. Prüft je Befund: kein widersprechender
Normalsatz übrig, Befund im Befundtext (Name oder Deskriptoren), Ergebnis nennt ihn, kein Normal-Ergebnis; zählt, wie oft
die deterministische Nachprüfung (widersprueche_bereinigen) eingreifen musste.
Ergebnis: docs/benchmarks/widerspruch_live_3.15.5.json
  python3 tools/verify_widerspruch.py
"""
import sys, json, pathlib, re, time
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "source_code")]
import prod_pipeline as pp
import befund_regeln as br
from concurrent.futures import ThreadPoolExecutor
FAELLE = [
    ("Calcaneus rechts: Fersensporn plantar, ansonsten unauffällig", True),
    ("Hüfte links: Fibroostose am Trochanter major, sonst unauffällig", True),
    ("Beckenübersicht: Fibroostose am Trochanter major rechts, sonst unauffällig", True),
    ("Ellbogen rechts: Enthesiopathie am Olecranon, ansonsten unauffällig", True),
    ("Knie links: kleiner Osteophyt am Patellaoberpol, sonst unauffällig", True),
    ("Knie rechts unauffällig", False),
    ("Calcaneus links: kein Fersensporn, keine Fraktur, unauffällig", False),
    ("Knie rechts: mäßiggradige Gonarthrose", True),
]
def pruefe(diktat, report):
    befunde = br.widerspruch_befunde(diktat)
    z = report.split("\n")
    bt = ""
    for a, e in br._abschnitt(z, "befund"):
        bt = "\n".join(z[a:e]); break
    et = report.split("## Ergebnis", 1)[1] if "## Ergebnis" in report else ""
    c = br._wid(); kat = {k["id"]: k for k in c["kat"]}
    probleme = []
    rest = br.widerspruch_saetze(bt, befunde)
    if rest: probleme.append("Widerspruch übrig: " + " | ".join(bt[a:b][:70] for a, b, _ in rest))
    for b in befunde:
        k = kat[b["id"]]
        if not br._beschreibt(bt.lower(), k, c): probleme.append(f"Befund fehlt im Befundtext ({b['id']})")
        if not (br._nennt(et.lower(), k, c) or re.search(k.get("ergebnis") or "$^", et.lower())):
            probleme.append(f"Ergebnis nennt {b['id']} nicht")
    if befunde and br._WID_NORMAL_ERG.search(et): probleme.append("Ergebnis behauptet Normalbefund")
    return probleme
def exe(d):
    log = []
    rep = pp.exe_kette(d, log=log)
    roh = log[0]["roh"] if log else ""
    _, aend = br.widersprueche_bereinigen(br.nachbearbeiten(roh), d) if roh else (None, [])
    return rep, aend
def web(d):
    return pp.web_kette(d)
t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    e_res = list(ex.map(lambda f: exe(f[0]), FAELLE))
    w_res = list(ex.map(lambda f: web(f[0]), FAELLE))
out = []
for (d, pat), (rep, aend), wrep in zip(FAELLE, e_res, w_res):
    pe, pw = pruefe(d, rep), pruefe(d, wrep)
    out.append({"diktat": d, "exe": rep, "exe_nachkorrektur": aend, "exe_probleme": pe, "web": wrep, "web_probleme": pw})
    print("=" * 100); print("DIKTAT:", d)
    print("--- EXE", "OK" if not pe else pe, "| Nachkorrektur nötig:" , aend or "nein"); print(rep)
    print("--- WEB", "OK" if not pw else pw); print(wrep)
print(f"\nDauer {time.time()-t0:.0f}s; EXE ok {sum(not o['exe_probleme'] for o in out)}/{len(out)}, Web ok {sum(not o['web_probleme'] for o in out)}/{len(out)}; KI allein (ohne Nachkorrektur) {sum(not o['exe_nachkorrektur'] for o in out)}/{len(out)}")
(ROOT / "docs" / "benchmarks" / "widerspruch_live_3.15.5.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
