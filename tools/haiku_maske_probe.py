#!/usr/bin/env python3
"""tools/haiku_maske_probe.py — Maskierung im echten Ablauf messen (kaiscribe-haiku-ab-n1, 13.11.2026). NUR MESSUNG.

Die 20 Harness-Diktate bekommen je EINEN synthetischen Personendaten-Satz (Vergleichsdatum, Zuweiser, Kontrolltermin,
Befundnummer — erfunden, keine Patientendaten) und laufen durch die echte Kette (web: Call 0 → Gen → Validator,
exe: Gen). Mit KAISCRIBE_TEST_ROUTE="alle=claude-haiku-5-5" geht jeder Aufruf durch source_code/llm_anbieter (maskiert,
Rückfall Gemini). Gemessen je Befund: steht der Originalwert wieder im Befund? Platzhalter-Rest „⟦“? Rückfälle je Grund
(aus dem Weichen-Protokoll <job>.weiche.jsonl).

  KAISCRIBE_TEST_ROUTE="alle=claude-haiku-5-5" python tools/haiku_maske_probe.py haiku web 1
Ausgabe: docs/benchmarks/haiku_maske_<name>_<kette>.json (+ SUMMARY-Zeile).
"""
import collections
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import testkosten as tk  # noqa: E402
import test_all_regions as H  # noqa: E402
import prod_pipeline as pp  # noqa: E402

NAME, KETTE = sys.argv[1], sys.argv[2]
RUNS = tk.argv_laeufe(3, 1)

# (Satz, Werte, die danach wieder im Befund stehen sollen, Stelle)
ZUSAETZE = [
    ("Im Vergleich zur Voruntersuchung vom 12.03.2025 unverändert.", ["12.03.2025"], "hinten"),
    ("Zuweisung durch Dr. Huber.", ["Huber"], "vorne"),
    ("Kontrolle im März 2027 empfohlen.", ["März 2027"], "hinten"),
    ("Befundnummer RH 4711.", ["4711"], "hinten"),
]


def diktat_mit(diktat, i):
    satz, werte, stelle = ZUSAETZE[i % len(ZUSAETZE)]
    d = diktat.strip()
    return (satz + " " + d if stelle == "vorne" else d.rstrip(".") + ". " + satz), satz, werte


def weiche_zeilen(pid):
    pfad = tk._logdir() / f"{tk.job_name()}.weiche.jsonl"
    try:
        return [z for z in map(json.loads, filter(str.strip, open(pfad, encoding="utf-8"))) if z.get("pid") == pid]
    except FileNotFoundError:
        return []


def main():
    tk.projekt()
    if any(m.startswith("claude") for m, _o, _d in tk.route().values()):
        tk._anthropic_key()
    rows = []
    for run in range(RUNS):
        for i, (name, _key, diktat, _exp) in enumerate(H.TEST_CASES):
            d, satz, werte = diktat_mit(diktat, i + run)
            n0 = len(weiche_zeilen(os.getpid()))
            try:
                rep = (pp.web_kette if KETTE == "web" else pp.exe_kette)(d)
                fehler = ""
            except Exception as e:  # noqa: BLE001
                rep, fehler = "", str(e)[:200]
            w = weiche_zeilen(os.getpid())[n0:]
            rows.append({"run": run, "name": name, "satz": satz, "werte_da": all(v in rep for v in werte),
                         "rest_platzhalter": "⟦" in rep or "⟧" in rep, "fehler": fehler,
                         "aufrufe": [{k: z.get(k) for k in ("rolle", "anbieter", "rueckfall", "platzhalter", "pflicht")}
                                     for z in w], "report": rep})
            print(f"{run} {name[:38]:38s} werte={'ja' if rows[-1]['werte_da'] else 'NEIN'} "
                  f"rückfall={[z['rueckfall'] for z in w if z.get('rueckfall')]}", flush=True)
    gruende = collections.Counter(a["rueckfall"] for r in rows for a in r["aufrufe"] if a["rueckfall"])
    alle = [a for r in rows for a in r["aufrufe"]]
    summ = {"name": NAME, "kette": KETTE, "route": tk.route(), "n": len(rows),
            "werte_im_befund": f"{sum(r['werte_da'] for r in rows)}/{len(rows)}",
            "platzhalter_rest": sum(r["rest_platzhalter"] for r in rows),
            "aufrufe": len(alle), "anthropic_ok": sum(1 for a in alle if a["anbieter"] == "anthropic"),
            "rueckfaelle": sum(gruende.values()), "rueckfall_gruende": dict(gruende),
            "mit_pflicht_platzhalter": sum(1 for a in alle if (a.get("pflicht") or 0) > 0),
            "fehler": sum(1 for r in rows if r["fehler"])}
    out = ROOT / "docs" / "benchmarks" / f"haiku_maske_{NAME}_{KETTE}.json"
    out.write_text(json.dumps({"summary": summ, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SUMMARY", json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
