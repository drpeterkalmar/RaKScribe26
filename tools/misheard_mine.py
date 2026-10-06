#!/usr/bin/env python3
"""tools/misheard_mine.py — Fehlhör-Kandidaten aus Benchmark-Läufen schürfen.

Vergleicht chirp_3-Hypothesen (meddictate_bench_results.json, stt_ab_g35t_results.json)
wortweise mit den Referenzen (MedDictate-Parquet bzw. den Referenztexten in
~/.hermes/skills/productivity/fast-stt/references/stt-benchmarks-and-misrecognitions.md)
und listet Substitutionen "gehört → gemeint" samt Häufigkeit. Dient als Vorschlagsliste
für misheard_words.json — NICHT blind übernehmen (Kasus-/Kompositum-Noise filtern).

  /usr/bin/python3 tools/misheard_mine.py [--all]
"""
import collections, difflib, json, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]  # Repo-Root (Skript liegt in tools/)
PARQ = pathlib.Path(os.path.expanduser("~/.hermes/cache/scratch/meddictate/de.parquet"))
SHOW_ALL = "--all" in sys.argv


def norm(t: str):
    t = re.sub(r"\{(Punkt|Komma|Doppelpunkt|Semikolon|Fragezeichen|Ausrufezeichen)\}", " ", t)
    t = re.sub(r"\b(neue Zeile|neuer Absatz|neue Absatz|Absatz|Zeilenumbruch)\b", " ", t, flags=re.I)
    t = t.lower().replace("ß", "ss")
    t = re.sub(r"[^\wäöü/²-]+", " ", t)
    return t.split()


def pairs(ref: str, hyp: str):
    R, H = norm(ref), norm(hyp)
    sm = difflib.SequenceMatcher(a=R, b=H, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace" and (i2 - i1) <= 3 and (j2 - j1) <= 3:
            a, b = " ".join(R[i1:i2]), " ".join(H[j1:j2])
            if a != b and not (a.isdigit() or b.isdigit()):
                yield b, a


def interesting(h: str, w: str) -> bool:
    if SHOW_ALL:
        return True
    # Fachwort-Länge, lautliche Nähe (echte Verhörer), aber keine reinen Flexionsendungen
    if len(w) < 6:
        return False
    r = difflib.SequenceMatcher(None, h, w).ratio()
    if r < 0.4:
        return False
    if h[:-2] == w[:-2] and abs(len(h) - len(w)) <= 2:  # Kasus-/Plural-Noise
        return False
    return True


subs = collections.Counter()

# 1) MedDictate (de): Referenz aus Parquet
res_p = ROOT / "docs" / "benchmarks" / "meddictate_bench_results.json"
if res_p.exists() and PARQ.exists():
    import pyarrow.parquet as pq
    rows = pq.read_table(PARQ).to_pylist()
    d = json.load(open(res_p))
    for name, runs in d.items():
        if not name.startswith("chirp_3"):
            continue
        for r in runs:
            if "err" in r:
                continue
            idx = int(r["id"].split("_")[1]) - 1
            for h, w in pairs(rows[idx]["transcription_formatted"], r["txt"]):
                subs[(h, w)] += 1

# 2) Eigene Diktate: Referenztexte aus dem fast-stt-Skill
md = pathlib.Path(os.path.expanduser("~/.hermes/skills/productivity/fast-stt/references/stt-benchmarks-and-misrecognitions.md"))
res_g = ROOT / "docs" / "benchmarks" / "stt_ab_g35t_results.json"
if md.exists() and res_g.exists():
    txt = md.read_text()
    refs = {}
    for m in re.finditer(r"`?([\w\-]+\.ogg)`?[^\n]*\n+(?:\*\*)?(?:Referenz|Soll)[^\n]*?[:：]\s*(?:\*\*)?\s*\n?[>\"„]?\s*([^\n]{40,})", txt):
        refs.setdefault(m.group(1), m.group(2).strip().strip('"“”'))
    d = json.load(open(res_g))
    for name, runs in d.items():
        if not name.startswith("chirp_3"):
            continue
        for r in runs:
            ref = refs.get(r["file"])
            if ref and not r["txt"].startswith("ERR"):
                for h, w in pairs(ref, r["txt"]):
                    subs[(h, w)] += 1
    print(f"[eigene Diktate] Referenzen gefunden für: {sorted(refs)}")

rows = sorted(((h, w, c) for (h, w), c in subs.items() if interesting(h, w)), key=lambda x: (-x[2], x[1]))
print(f"{len(subs)} Substitutionen gesamt, {len(rows)} Kandidaten\n")
for h, w, c in rows:
    print(f"{c}×  gehört: {h!r:44s} gemeint: {w!r}")
