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
  erhalt_schulter  „mäßiggradige Omarthrose“ → Omarthrose mit Grad-Adjektiv, K&L 3 (v3.18.5: Grad zum Adjektiv einer
                   DIKTIERTEN Arthrose, Nachtrag RH 99); erhalt_knie/erhalt_web ebenso K&L 3
  erhalt_ohne_adj  „Coxarthrose“ ohne Adjektiv → kein Grad
  rh99_*           Nachtrag RH 99 (Becken stehend + HIPPO, 27 Messwerte): Diktat ohne Arthrose-Wort (normal, „Gelenkspalt-
                   verschmälerung“, „degenerative Veränderungen“, Web) → 0× Arthrose/Kellgren; rh99_koxa(_web) „mäßige
                   Coxarthrose beidseits“ → K&L 3

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
import testkosten  # noqa: E402
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


def pruef_erhalt(muss_befund, muss_ergebnis, kl=None):
    """kl = erwarteter K&L-Grad (v3.18.5: Grad zum Adjektiv einer diktierten Arthrose), None = kein Grad."""
    def f(rep, diktat, zeilen, hinweise):
        befund, ergebnis = teile(rep)
        p = []
        for w in muss_befund:
            if not re.search(w, befund, re.I):
                p.append(f"❌ verschluckt im Befund: {w}")
        for w in muss_ergebnis:
            if not re.search(w, ergebnis, re.I):
                p.append(f"❌ verschluckt im Ergebnis: {w}")
        if kl is None and (grade(rep) or (KL.search(rep) and not KL.search(diktat))):
            p.append(f"❌ K&L-Grad ohne Diktat/IB Lab: {sorted(grade(rep))}")
        if kl is not None and grade(rep) != {kl}:
            p.append(f"❌ K&L {kl} erwartet, gefunden {sorted(grade(rep)) or '–'}")
        pos, _neg, _kl = erfunden(rep, diktat, zeilen)
        if pos:
            p.append("❌ erfunden: " + ", ".join(pos))
        return p
    return f


# Nachtrag RH 99 (Peter 12.11.2026, 20261112099): Beckenübersicht stehend + HIPPO-Baustein mit 27 Messwerten (LCE, Tönnis,
# Sharp, Offsets, Kopfdurchmesser, CCD, Beckenschiefstand, Beinlängendifferenz — KEIN K&L, kein „Arthrose“). KaiScribe 3.18.0
# schlug „Coxarthrose (Kellgren & Lawrence Grad 3) beidseits“ vor. Werte synthetisch (ris-mods ibl Fixture HIPPO_SR).
BECKEN = {"kurz": "x-becken", "text": "Becken stehend", "appc": "", "modalitaet": "Röntgen", "seite": "",
          "vorlage": "beckenübersicht_stehend", "ohne_vorlage": False, "bekannt": True}
HIPPO_26 = {"accno": "T-0299", "ziffer": 1, "modul": "hippo", "name": "HIPPO", "modul_name": "IB Lab HIPPO",
            "version": 1, "seiten": ["rechts", "links"], "befundteil": ['LCE-Winkel nach Wiberg rechts 32,3° (IB Lab HIPPO).', 'CCD-Winkel rechts 132,6° (IB Lab HIPPO).', 'Pfannendachwinkel nach Tönnis (Acetabulumindex) rechts 10,1° (IB Lab HIPPO).', 'Sharp-Winkel rechts 34,7° (IB Lab HIPPO).', 'Extrusionsindex des Femurkopfes rechts 13,0 % (IB Lab HIPPO).', 'Femurkopfüberdachung rechts 87,0 % (IB Lab HIPPO).', 'Femorales Offset rechts 46,9 mm (IB Lab HIPPO).', 'Acetabuläres Offset rechts 38,6 mm (IB Lab HIPPO).', 'Globales Offset rechts 85,5 mm (IB Lab HIPPO).', 'Femurkopfdurchmesser rechts 56,0 mm (IB Lab HIPPO).', 'Länge der Schenkelhalsachse rechts 43,7 mm (IB Lab HIPPO).', 'Höhe des Trochanter minor rechts 72,0 mm (IB Lab HIPPO).', 'LCE-Winkel nach Wiberg links 38,3° (IB Lab HIPPO).', 'CCD-Winkel links 132,1° (IB Lab HIPPO).', 'Pfannendachwinkel nach Tönnis (Acetabulumindex) links 5,9° (IB Lab HIPPO).', 'Sharp-Winkel links 30,7° (IB Lab HIPPO).', 'Extrusionsindex des Femurkopfes links 6,0 % (IB Lab HIPPO).', 'Femurkopfüberdachung links 94,0 % (IB Lab HIPPO).', 'Femorales Offset links 47,4 mm (IB Lab HIPPO).', 'Acetabuläres Offset links 39,1 mm (IB Lab HIPPO).', 'Globales Offset links 86,5 mm (IB Lab HIPPO).', 'Femurkopfdurchmesser links 55,0 mm (IB Lab HIPPO).', 'Länge der Schenkelhalsachse links 37,8 mm (IB Lab HIPPO).', 'Höhe des Trochanter minor links 65,0 mm (IB Lab HIPPO).', 'Beckenschiefstand 0,0° (IB Lab HIPPO).', 'Beckenhöhendifferenz 0,0 mm (IB Lab HIPPO).', 'Beinlängendifferenz 7,0 mm (IB Lab HIPPO).'],
            "ergebnis": [], "hinweise": [], "nicht_zugeordnet": []}
RH99_NORMAL = ("Beckenübersicht stehend. Die Hüftgelenke beidseits altersentsprechend dargestellt, kein Beckenschiefstand. "
               "Die Messwerte von IB Lab wurden übernommen, im Übrigen unauffällig.")
RH99_SPALT = ("Beckenübersicht stehend. Geringe Gelenkspaltverschmälerung beider Hüftgelenke kranial betont, "
              "kein Hinweis auf eine Fraktur, im Übrigen unauffällig.")
RH99_SPALT2 = ("Becken im Stehen. Hüftgelenke beidseits mit mäßiger Verschmälerung des Gelenkspaltes, rechts mehr als links, "
               "kein Beckenschiefstand, Iliosakralgelenke unauffällig.")   # nicht im Prompt-Beispiel (gegen Überanpassung)
RH99_DEGEN = ("Beckenübersicht stehend. Geringe degenerative Veränderungen beider Hüftgelenke, kein Beckenschiefstand, "
              "im Übrigen unauffällig.")
RH99_DEGEN2 = ("Becken im Stehen. Beginnende degenerative Veränderungen am rechten Hüftgelenk mit kleinen Randanbauten, "
               "links unauffällig.")   # nicht im Prompt-Beispiel
RH99_KOXA = "Beckenübersicht stehend. Mäßige Coxarthrose beidseits, im Übrigen unauffällig."


def pruef_rh99(rep, diktat, zeilen, hinweise):
    """Diktat ohne Arthrose-Wort + HIPPO: 0× „Coxarthrose“/„Arthrose“, 0× „Kellgren“, kein Grad."""
    t = rep
    for z in zeilen:
        t = t.replace(z, "")
    p = []
    if re.search(r"arthros", t, re.I):
        p.append("❌ Arthrose/Coxarthrose erfunden")
    if re.search(r"kellgren|\bk\s*&\s*l\b", t, re.I):
        p.append("❌ K&L erfunden")
    pos, neg, _kl = erfunden(rep, diktat, zeilen)
    if pos:
        p.append("❌ erfunden: " + ", ".join(pos))
    if neg:
        p.append("⚠️ nicht diktiert, verneint: " + ", ".join(neg))
    _b0, erg0 = teile(rep)
    if not re.sub(r"[\s.]", "", erg0):
        p.append("❌ Ergebnis leer")
    if "verschmäler" in diktat.lower():
        _b, erg = teile(rep)
        if "verschmäler" not in erg.lower():
            p.append("❌ diktierte Gelenkspaltverschmälerung fehlt im Ergebnis")
    return p


def pruef_rh99_koxa(rep, diktat, zeilen, hinweise):
    """Diktierte „mäßige Coxarthrose beidseits“ → Coxarthrose beidseits mit K&L 3 bleibt (Nachtrag b)."""
    _b, erg = teile(rep)
    p = []
    if not re.search(r"coxarthrose", erg, re.I):
        p.append("❌ Coxarthrose fehlt im Ergebnis")
    if not re.search(r"beidseits|beider", erg, re.I):
        p.append("❌ „beidseits“ fehlt im Ergebnis")
    if not re.search(r"mäßig", erg, re.I):
        p.append("❌ Grad-Adjektiv fehlt im Ergebnis")
    g = grade(rep)
    if g != {"3"}:
        p.append(f"❌ K&L 3 erwartet, gefunden {sorted(g) or '–'}")
    pos, _neg, _kl = erfunden(rep, diktat, zeilen)
    if pos:
        p.append("❌ erfunden: " + ", ".join(pos))
    return p


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
                                 [r"gonarthrose", r"mäßig", r"medial", r"rechts"], kl="3")),
    "erhalt_web": (lauf_web, ERHALT_KNIE, None, None,
                   pruef_erhalt([r"osteophyt", r"skleros", r"medial"], [r"gonarthrose", r"mäßig", r"medial"], kl="3")),
    "erhalt_schulter": (lauf_exe, "Schulter rechts, Röntgen, mäßiggradige Omarthrose, ansonsten unauffällig.", None,
                        None, pruef_erhalt([r"gelenk(?:s)?spalt|degenerativ|arthrot"],
                                           [r"mäßiggradige omarthrose", r"rechts"], kl="3")),
    "erhalt_ohne_adj": (lauf_exe, "Hüftgelenk rechts, Röntgen, Coxarthrose, ansonsten unauffällig.", None, None,
                        pruef_erhalt([r"degenerativ|arthrot|gelenk(?:s)?spalt"], [r"coxarthrose", r"rechts"])),
    "rh99_normal": (lauf_exe, RH99_NORMAL, [BECKEN], [HIPPO_26], pruef_rh99),
    "rh99_spalt": (lauf_exe, RH99_SPALT, [BECKEN], [HIPPO_26], pruef_rh99),
    "rh99_web": (lauf_web, RH99_SPALT, None, None, pruef_rh99),
    "rh99_spalt2": (lauf_exe, RH99_SPALT2, [BECKEN], [HIPPO_26], pruef_rh99),
    "rh99_degen2": (lauf_exe, RH99_DEGEN2, [BECKEN], [HIPPO_26], pruef_rh99),
    "rh99_degen": (lauf_exe, RH99_DEGEN, [BECKEN], [HIPPO_26], pruef_rh99),
    "rh99_koxa": (lauf_exe, RH99_KOXA, [BECKEN], [HIPPO_26], pruef_rh99_koxa),
    "rh99_koxa_web": (lauf_web, RH99_KOXA, None, None, pruef_rh99_koxa),
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
    n = testkosten.laeufe(int(args.pop(0)) if args and args[0].isdigit() else None, 1)  # ≤ 5, mehr nur mit --release
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
