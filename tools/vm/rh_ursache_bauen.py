#!/usr/bin/env python3
"""rh_ursache_bauen.py (kaiscribe-schulter-ergebnis-n1, 23.11.2026) – baut das VM-Lese-Skript rh_ursache_vm.py mit den
Vorlagensätzen aus templates.json (eingebettet) und startet es über x_lauf_mac.py. NUR LESEN (Lauf-Dateien auf X:).
Ausgabe je Lauf-Datei: Zeit, Version, Vorlagen, IB-Lab-Module, je Teil Titel + Satz-Kürzel:
  V:<Vorlagensatz-Anfang>  Satz wörtlich aus einer Vorlage (keine Patientendaten)
  D<n>[flags]              anderer Satz (n Wörter; Flags = medizinische Stichwörter aus fester Liste, keine Freitexte)
Diktat nur als Stichwort-Liste. Kein Name, keine Nr außer der Kurz-ID.

  python3 tools/vm/rh_ursache_bauen.py 20261123 030 059 088 ...
"""
import json, os, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
t = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
saetze = set()
for v in t.values():
    for teil in (v.get("body", ""), v.get("ergebnis", "")):
        for s in re.split(r"(?<=[.!?:])\s+|\n", teil):
            s = s.strip()
            if len(s) > 12:
                saetze.add(re.sub(r"\s+", " ", s.lower())[:70])
VM = r'''
import glob, json, os, re, sys
VORLAGE = set(json.loads(VORLAGE_JSON))
STICH = ["fraktur","tep","prothes","lockerung","periprothet","coxarthros","gonarthros","omarthros","arthros","kellgren","grad",
 "enthesi","bursa","bursitis","step","impingement","beckenschief","beinlängen","hippo","koala","lama","squirrel","lce","ai-","ccd",
 "regelrecht","unauffällig","normal","unverändert","voruntersuchung","vergleich","unterarm","handgelenk","radius","ulna","ganzbein",
 "traglinie","hka","mikulicz","funktion","skolio","cobb","flexion","inklination","reklination","hüft","becken","knie","schulter",
 "lws","bws","hws","gering","mäßig","hochgradig","beginnend","mittelgradig","fibroostos","gluteal","sehne","ac-gelenk","verkalk",
 "gelenkspalt","hüftkopf","stellung","im übrigen","ansonsten","rho","osteopen","dunn","nerv","peroneus","enkapsul","einkapsel",
 "malleol","ausriss","fragment","kortikalis","weichteil","links","rechts","beidseits","mtp","zehe","großzeh","kommt","dazu","ergebnis"]
def kurz(s):
    n = re.sub(r"\s+", " ", s.strip().lower())
    for k in (n[:70],):
        if k in VORLAGE: return "V:" + s.strip()[:48]
    if re.sub(r"^(im übrigen|ansonsten),?\s+", "", n)[:70] in VORLAGE: return "VU:" + s.strip()[:48]
    if re.match(r"^\d+\.\s", n):
        r = re.sub(r"^\d+\.\s*", "", n)
        if r[:70] in VORLAGE: return n[:3] + "V:" + s.strip()[3:40]
    fl = [k for k in STICH if k in n]
    return "D%d[%s]" % (len(n.split()), ",".join(fl))
def teile(rep):
    out, tit, cur = [], "", None
    for z in rep.splitlines():
        s = z.strip()
        if not s: continue
        m = re.match(r"^#+\s*(.*)$", s)
        if m:
            h = m.group(1).strip().rstrip(":")
            if h.lower() in ("befund", "ergebnis", "anmerkung"):
                cur = h[0].upper(); out.append([tit, cur, []])
            else:
                tit = h[:70]
            continue
        if cur is None: out.append([tit, "?", []]); cur = "?"
        for x in re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9])", s):
            out[-1][2].append(kurz(x))
    return out
tag = sys.argv[1]
for nnn in sys.argv[2:]:
    nr = tag + nnn
    fs = []
    for w in (r"X:\KaiScribe\Daten\laeufe", r"X:\RaKScribe\Daten\laeufe"):
        fs += glob.glob(os.path.join(w, nr + "_*.json"))
    print("=" * 20, "RH", nnn, "dateien=%d" % len(fs))
    for p in sorted(set(fs), key=os.path.basename):
        d = json.load(open(p, encoding="utf-8-sig"))
        dk = str(d.get("diktat") or d.get("stt_roh") or "").lower()
        print("-- LAUF", os.path.basename(p)[12:27], "ks=%s" % d.get("kaiscribe"), "modell=%s" % str(d.get("modell"))[:30],
              "vorlagen=%s" % ",".join(d.get("vorlagen") or []), "ibl=%s" % ",".join(d.get("ibl_module") or []),
              "ibl_zeilen=%s" % d.get("ibl_zeilen"), "maske=%s" % d.get("maske", "-"), "diktat_worte=%d" % len(dk.split()))
        print("   DIKTAT_STICH", ",".join(k for k in STICH if k in dk))
        for tit, art, ss in teile(str(d.get("ergebnis_vorschlag") or "")):
            print("   [%s] %s: %s" % (art, tit, " | ".join(ss)))
'''
tag, nrs = sys.argv[1], sys.argv[2:]
ziel = pathlib.Path(os.path.expanduser("~/cj/work/kaiscribe-schulter-ergebnis-n1"))
ziel.mkdir(parents=True, exist_ok=True)
skript = ziel / "rh_ursache_vm.py"
skript.write_text("VORLAGE_JSON = %r\n" % json.dumps(sorted(saetze), ensure_ascii=False) + VM, encoding="utf-8")
env = dict(os.environ, VM_FRIST=os.environ.get("VM_FRIST", "600"))
sys.exit(subprocess.call([sys.executable, str(ROOT / "tools/vm/x_lauf_mac.py"), str(skript), tag] + nrs, env=env))
