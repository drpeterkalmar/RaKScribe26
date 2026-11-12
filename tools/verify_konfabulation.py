#!/usr/bin/env python3
"""Live-Regression „KaiScribe erfindet Befundinhalte“ (Peter 12.11.2026, RH 38) — echte EXE-/Web-Kette mit Gemini.

Anlass: Diktat Knie links nur „Mäßige Gelenkspaltverschmälerung des medialen Kniegelenkspaltes, im Übrigen
unauffällig“ → KaiScribe 3.18.0 schrieb Osteophyten, subchondrale Sklerose und „Mäßiggradige Gonarthrose … (Arthrose
Grad 3 nach Kellgren & Lawrence)“. Richtig: nur das Diktierte + Normalsätze der Vorlage; ein K&L-Grad nur, wenn diktiert
oder aus einem IB-Lab-Baustein (KOALA), ein diktierter Grad geht vor.

Fälle (synthetisch, keine Patientendaten — nur der Diktat-Wortlaut):
  rh38_cas      EXE mit CAS-Leistung Knie links (so lief der echte Fall), ohne IB Lab → 0 erfundene Pathologie/K&L
  rh38_exe      EXE ohne CAS („Kniegelenk links. …“)
  rh38_web      Web-Kette (Call 0 → Gen → Validator)
  ibl_kl1       wie rh38_cas + IB-Lab-KOALA-Baustein KL 1 links → „Grad … 1“, kein anderer Grad
  diktat_kl     Diktat nennt selbst K&L 2, IB Lab sagt 1 → Grad 2, IB-Lab-Grad nicht zusätzlich
  diktat_kl_ohne  Diktat nennt K&L 3, ohne IB Lab → Grad 3
  erhalt_knie   Diktat mit Gonarthrose, Osteophyten, Sklerose, „kein Erguss“ → alles bleibt in Befund/Ergebnis, kein Grad
  erhalt_web    derselbe Fall in der Web-Kette
  erhalt_schulter  „mäßiggradige Omarthrose“ ohne Grad → Omarthrose im Ergebnis mit Grad-Adjektiv, kein K&L-Grad

Aufruf: tools/verify_konfabulation.py [Läufe je Fall, Standard 1] [Fall …]   (z. B. „20 rh38_cas rh38_web“)
Ergebnis: docs/benchmarks/konfabulation_<datum>.json (Berichte + Befunde je Lauf).
"""
import datetime
import json
import pathlib
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "source_code"))
import prod_pipeline as pp  # noqa: E402
import cas_vorlagen as cv  # noqa: E402
import ibl_bausteine as ib  # noqa: E402
import befund_regeln as br  # noqa: E402

RH38 = "Mäßige Gelenkspaltverschmälerung des medialen Kniegelenkspaltes, im Übrigen unauffällig."
KNIE_LI = {"kurz": "x-knie-li", "text": "Kniegelenk links", "appc": "", "modalitaet": "Röntgen", "seite": "links",
           "vorlage": "kniegelenk_in_2_ebenen", "ohne_vorlage": False, "bekannt": True}
KNIE_RE = dict(KNIE_LI, kurz="x-knie-re", text="Kniegelenk rechts", seite="rechts")
KOALA_KL1 = {"accno": "T-0201", "ziffer": 1, "modul": "koala", "name": "KOALA", "modul_name": "IB Lab KOALA",
             "version": 1, "seiten": ["links"], "befundteil": ["Kellgren-Lawrence-Grad links 1 (IB Lab KOALA)."],
             "ergebnis": [], "hinweise": [], "nicht_zugeordnet": []}

# Nicht diktierte Pathologie (positiv genannt) = erfunden. Verneinte Nennung („kein Erguss“) = Warnung.
PATHO = [("Osteophyt", r"osteophyt|randzack|randwulst|randzuschärf|randausziehung"),
         ("Sklerose", r"skleros|sklerot"), ("Zyste", r"zyst"), ("Erguss", r"erguss|ergüss"),
         ("Arthrose", r"arthros|arthrot"), ("Chondrokalzinose", r"chondrokalz"), ("Geröll", r"geröll"),
         ("Fraktur", r"fraktur"), ("Subluxation", r"luxation")]
KL = re.compile(r"kellgren|\bk\s*&\s*l\b|\bkl[- ]grad", re.I)
GRAD = re.compile(r"(?:grad|grade)\s*(?:links|rechts|beidseits)?\s*:?\s*([0-4]|i{1,3}v?|iv)\b(?=[^.\n]{0,40}kellgren)"
                  r"|kellgren[^.\n]{0,30}?(?:grad|grade)?\s*(?:links|rechts|beidseits)?\s*:?\s*([0-4]|iv|i{1,3})\b", re.I)
_ROEM = {"i": "1", "ii": "2", "iii": "3", "iv": "4"}
NEG = re.compile(r"(?:kein\w*|ohne|nicht|frei von)\b[^.;\n]{0,30}$", re.I)


def teile(rep):
    befund = rep.split("## Befund", 1)[1].split("## Ergebnis", 1)[0] if "## Befund" in rep else ""
    ergebnis = rep.split("## Ergebnis", 1)[1] if "## Ergebnis" in rep else ""
    return befund, ergebnis


def grade(text):
    out = set()
    for m in GRAD.finditer(text or ""):
        g = (m.group(1) or m.group(2) or "").lower()
        out.add(_ROEM.get(g, g))
    return out


def erfunden(rep, diktat, ibl_zeilen=()):
    """→ (erfundene Pathologie positiv, nur verneint genannt, K&L ja/nein) ohne IB-Lab-Zeilen und Vorlagensätze."""
    t = rep
    for z in ibl_zeilen:
        t = t.replace(z, "")
    t = t.lower()
    d = (diktat or "").lower()
    pos, neg = [], []
    for name, rx in PATHO:
        if re.search(rx, d):
            continue
        for m in re.finditer(rx, t):
            (neg if NEG.search(t[max(0, m.start() - 40):m.start()]) else pos).append(name)
    return sorted(set(pos)), sorted(set(neg) - set(pos)), bool(KL.search(t)) and not KL.search(d)


def lauf_exe(diktat, cas=None, ibl=None):
    ctx = pp.exe_kontext()
    if cas:
        ctx.cas = cv.CasHinweis(cas, pp.TEMPLATES)
    if ibl:
        ctx.ibl = ib.IblKontext(ib.aus_liste(ibl), cas_leistungen=cas)
    erg = pp._pipeline.befund_aus_diktat(diktat, ctx)
    if erg.ausnahmen:
        raise erg.ausnahmen[0]
    return erg.report, (erg.ibl.zeilen if erg.ibl else []), (erg.ibl.hinweise if erg.ibl else [])


def lauf_web(diktat, cas=None, ibl=None):
    return pp.web_kette(diktat), [], []


def pruef_rh38(rep, diktat, zeilen, hinweise):
    befund, ergebnis = teile(rep)
    p = []
    pos, neg, kl = erfunden(rep, diktat, zeilen)
    if pos:
        p.append("❌ erfunden: " + ", ".join(pos))
    if kl:
        p.append("❌ K&L-Grad erfunden")
    if neg:
        p.append("⚠️ nicht diktiert, verneint: " + ", ".join(neg))
    for teil, name in ((befund, "Befund"), (ergebnis, "Ergebnis")):
        tl = teil.lower()
        if not (re.search(r"gelenk(?:s)?spalt", tl) and "verschmäler" in tl):
            p.append(f"❌ Gelenkspaltverschmälerung fehlt im {name}")
        if "medial" not in tl:
            p.append(f"❌ „medial“ fehlt im {name}")
    if "mäßig" not in ergebnis.lower():
        p.append("❌ Grad-Adjektiv „mäßig“ fehlt im Ergebnis")
    if re.search(r"regelrechte darstellung", ergebnis, re.I):
        p.append("❌ Ergebnis „Regelrechte Darstellung …“ trotz Befund")
    if "Patella in regelrechter Position" not in befund:
        p.append("⚠️ Vorlagensatz „Patella in regelrechter Position“ fehlt")
    return p


def pruef_kl(soll, verboten=()):
    def f(rep, diktat, zeilen, hinweise):
        p = []
        g = grade(rep)
        if soll not in g:
            p.append(f"❌ K&L-Grad {soll} fehlt (gefunden {sorted(g) or '–'})")
        if g - {soll}:
            p.append(f"❌ anderer K&L-Grad im Befund: {sorted(g - {soll})}")
        for z in verboten:
            if z in rep:
                p.append(f"❌ IB-Lab-Zeile trotz diktiertem Grad: {z}")
        pos, _neg, _kl = erfunden(rep, diktat, zeilen)
        if pos:
            p.append("❌ erfunden: " + ", ".join(pos))
        return p
    return f


def pruef_ibl_kl1(rep, diktat, zeilen, hinweise):
    """IB-Lab-Grad darf (als K&L-Klammer am diktierten Befund) im Ergebnis stehen — eine neue Diagnose nicht."""
    if re.search(r"gonarthrose", rep, re.I):
        return ["❌ Diagnose „Gonarthrose“ aus dem IB-Lab-Grad abgeleitet"] + pruef_rh38(rep, diktat, zeilen, hinweise)
    rep = re.sub(r"\s*\(Arthrose Grad 1 nach Kellgren & Lawrence\)", "", rep)
    p = pruef_rh38(rep, diktat, zeilen, hinweise)
    p = [x for x in p if "K&L-Grad erfunden" not in x]
    g = grade(rep) | grade("\n".join(zeilen))
    if g != {"1"}:
        p.append(f"❌ K&L-Grad laut IB Lab 1 erwartet, gefunden {sorted(g) or '–'}")
    return p


def pruef_erhalt(muss_befund, muss_ergebnis):
    def f(rep, diktat, zeilen, hinweise):
        befund, ergebnis = teile(rep)
        p = []
        for w in muss_befund:
            if not re.search(w, befund, re.I):
                p.append(f"❌ verschluckt im Befund: {w}")
        for w in muss_ergebnis:
            if not re.search(w, ergebnis, re.I):
                p.append(f"❌ verschluckt im Ergebnis: {w}")
        if grade(rep) or (KL.search(rep) and not KL.search(diktat)):
            p.append(f"❌ K&L-Grad ohne Diktat/IB Lab: {sorted(grade(rep))}")
        pos, _neg, _kl = erfunden(rep, diktat, zeilen)
        if pos:
            p.append("❌ erfunden: " + ", ".join(pos))
        return p
    return f


ERHALT_KNIE = ("Kniegelenk rechts: Mäßige Gonarthrose medial betont mit Osteophyten und subchondraler Sklerosierung, "
               "kein Erguss.")
FAELLE = {
    "rh38_cas": (lauf_exe, RH38, [KNIE_LI], None, pruef_rh38),
    "rh38_exe": (lauf_exe, "Kniegelenk links. " + RH38, None, None, pruef_rh38),
    "rh38_web": (lauf_web, "Kniegelenk links. " + RH38, None, None, pruef_rh38),
    "ibl_kl1": (lauf_exe, RH38, [KNIE_LI], [KOALA_KL1], pruef_ibl_kl1),
    "diktat_kl": (lauf_exe, "Mäßige Gonarthrose medial betont, Kellgren-Lawrence Grad 2, im Übrigen unauffällig.",
                  [KNIE_LI], [KOALA_KL1], pruef_kl("2", ["Kellgren-Lawrence-Grad links 1 (IB Lab KOALA)."])),
    "diktat_kl_ohne": (lauf_exe, "Kniegelenk rechts: Gonarthrose medial betont, Grad 3 nach Kellgren und Lawrence.",
                       None, None, pruef_kl("3")),
    "erhalt_knie": (lauf_exe, ERHALT_KNIE, [KNIE_RE], None,
                    pruef_erhalt([r"osteophyt", r"skleros", r"medial", r"gelenk(?:s)?spalt|degenerativ|arthrot"],
                                 [r"gonarthrose", r"mäßig", r"medial", r"rechts"])),
    "erhalt_web": (lauf_web, ERHALT_KNIE, None, None,
                   pruef_erhalt([r"osteophyt", r"skleros", r"medial"], [r"gonarthrose", r"mäßig", r"medial"])),
    "erhalt_schulter": (lauf_exe, "Schulter rechts, Röntgen, mäßiggradige Omarthrose, ansonsten unauffällig.", None,
                        None, pruef_erhalt([r"gelenk(?:s)?spalt|degenerativ|arthrot"],
                                           [r"mäßiggradige omarthrose", r"rechts"])),
}


def ein_lauf(name, i):
    fn, diktat, cas, ibl, pruef = FAELLE[name]
    t0 = time.time()
    try:
        rep, zeilen, hinweise = fn(diktat, cas, ibl)
    except Exception as e:  # noqa: BLE001
        return {"fall": name, "lauf": i, "status": "ERROR", "probleme": [f"💥 {e}"], "befund": ""}
    probleme = pruef(rep, diktat, zeilen, hinweise)
    status = "FAIL" if any(x.startswith("❌") for x in probleme) else ("WARN" if probleme else "PASS")
    return {"fall": name, "lauf": i, "status": status, "probleme": probleme, "befund": rep,
            "ibl_hinweise": hinweise, "s": round(time.time() - t0, 1)}


def main():
    args = sys.argv[1:]
    n = int(args.pop(0)) if args and args[0].isdigit() else 1
    namen = args or list(FAELLE)
    jobs = [(f, i) for f in namen for i in range(1, n + 1)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(lambda j: ein_lauf(*j), jobs))
    print(f"Prompt-Stand {pp.PROMPT_VERSION} · {n} Lauf/Läufe je Fall")
    zus = {}
    for r in res:
        z = zus.setdefault(r["fall"], {"PASS": 0, "WARN": 0, "FAIL": 0, "ERROR": 0})
        z[r["status"]] += 1
        if r["status"] != "PASS":
            print(f"\n[{r['status']}] {r['fall']} #{r['lauf']}: " + " | ".join(r["probleme"]))
            print("  " + (r["befund"] or "").replace("\n", "\n  ")[:1500])
    print("\n" + "=" * 70)
    for f, z in zus.items():
        print(f"{f:16s} PASS {z['PASS']:2d} | WARN {z['WARN']:2d} | FAIL {z['FAIL']:2d} | ERROR {z['ERROR']:2d}")
    out = ROOT / "docs" / "benchmarks" / f"konfabulation_{datetime.date.today():%Y%m%d}_{pp.PROMPT_VERSION}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    alt = json.loads(out.read_text()) if out.exists() else []
    out.write_text(json.dumps(alt + res, ensure_ascii=False, indent=1))
    print(f"→ {out.relative_to(ROOT)}")
    return 0 if all(z["FAIL"] == 0 and z["ERROR"] == 0 for z in zus.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
