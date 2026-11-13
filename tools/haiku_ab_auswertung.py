#!/usr/bin/env python3
"""tools/haiku_ab_auswertung.py — fasst die Messläufe von kaiscribe-haiku-ab-n1 zusammen (nur lesen, kein Netz).

Liest docs/benchmarks/modellvergleich_<cfg>-<kette>-r<N>.json (tools/modellvergleich.py je Runde) und
haiku_maske_*.json, rechnet je Konfiguration × Kette über alle Runden: Befunde, Fehler, Normalbefund-Treue, Seiten,
fehlende Pathologien (mit Fall), Latenz je Befund und je Aufrufart p50/p90, $ je Befund (gemessen, mit Cache).
Ausgabe: docs/benchmarks/haiku_ab_n1.json + Markdown-Tabelle auf stdout.
  python3 tools/haiku_ab_auswertung.py [quellordner]
"""
import collections
import glob
import json
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
QUELLE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "benchmarks"


def pz(werte, q):
    w = sorted(werte)
    if not w:
        return None
    return round(w[min(len(w) - 1, max(0, int(round(q * len(w))) - 1))], 2)


def main():
    gruppen = collections.defaultdict(list)
    for f in sorted(glob.glob(str(QUELLE / "modellvergleich_*-r*.json"))):
        m = re.search(r"modellvergleich_(\w+)-(web|exe)-r(\d+)_(?:web|exe)\.json$", f)
        if m:
            gruppen[(m.group(1), m.group(2))].append(json.load(open(f, encoding="utf-8")))
    aus = {}
    for (cfg, kette), laeufe in sorted(gruppen.items()):
        rows = [r for d in laeufe for r in d["rows"]]
        ok = [r for r in rows if not r["fehler"]]
        calls = collections.defaultdict(list)
        for r in ok:
            for c in r["calls"]:
                if c.get("s") is not None:
                    calls[(c["rolle"], c["modell"])].append(c["s"])
        fehlt = collections.Counter(f"{r['name']}: {p}" for r in ok for p in r["pathologie_fehlt"])
        kp = [r["treue"] for r in ok]
        sd = [r["seite_ok"] for r in ok if r["seite_ok"] is not None]
        seite_falsch = collections.Counter(r["name"] for r in ok if r["seite_ok"] is False)
        aus[f"{cfg}-{kette}"] = {
            "runden": len(laeufe), "befunde": len(rows), "fehler": len(rows) - len(ok),
            "treue": f"{sum(k for k, _ in kp)}/{sum(p for _, p in kp)}",
            "treue_pct": round(100 * sum(k for k, _ in kp) / max(1, sum(p for _, p in kp)), 1),
            "seiten": f"{sum(sd)}/{len(sd)}", "seite_falsch_faelle": dict(seite_falsch),
            "pathologie_fehlt": sum(fehlt.values()), "pathologie_fehlt_faelle": dict(fehlt),
            "befund_s_p50": pz([r["s"] for r in ok], 0.5), "befund_s_p90": pz([r["s"] for r in ok], 0.9),
            "befund_s_max": max((r["s"] for r in ok), default=None),
            "aufrufe_s": {f"{rolle}/{modell}": {"n": len(v), "p50": pz(v, 0.5), "p90": pz(v, 0.9)}
                          for (rolle, modell), v in sorted(calls.items())},
            "usd_je_befund": round(statistics.mean(r["usd"] for r in ok), 5) if ok else None,
            "usd_je_befund_ohne_cache": round(statistics.mean(r["usd_ohne_cache"] for r in ok), 5) if ok else None,
        }
    maske = {}
    for f in sorted(glob.glob(str(QUELLE / "haiku_maske_*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        je = collections.defaultdict(lambda: [0, 0, 0])
        for r in d["rows"]:
            x = je[r["satz"]]
            x[0] += 1
            x[1] += r["werte_da"]
            x[2] += any(a["rueckfall"] for a in r["aufrufe"])
        maske[pathlib.Path(f).stem] = dict(d["summary"], je_satz={k: {"n": v[0], "wert_im_befund": v[1], "rueckfall": v[2]}
                                                                  for k, v in je.items()})
    (ROOT / "docs" / "benchmarks" / "haiku_ab_n1.json").write_text(
        json.dumps({"ketten": aus, "maske": maske}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("| Konfig | Befunde | Treue | Seiten | Pathologie fehlt | Befund p50/p90 s | $/Befund (ohne Cache) |")
    print("|---|---|---|---|---|---|---|")
    for k, v in aus.items():
        print(f"| {k} | {v['befunde']} ({v['fehler']} Fehler) | {v['treue']} = {v['treue_pct']} % | {v['seiten']} | "
              f"{v['pathologie_fehlt']} | {v['befund_s_p50']} / {v['befund_s_p90']} (max {v['befund_s_max']}) | "
              f"{v['usd_je_befund']} ({v['usd_je_befund_ohne_cache']}) |")
    for k, v in aus.items():
        print(f"\n{k}: Aufrufe {json.dumps(v['aufrufe_s'], ensure_ascii=False)}\n  fehlt: {v['pathologie_fehlt_faelle']}"
              f"\n  Seite falsch: {v['seite_falsch_faelle']}")
    for k, v in maske.items():
        print(f"\n{k}: {json.dumps(v, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
