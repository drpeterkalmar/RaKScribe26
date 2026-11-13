#!/usr/bin/env python3
"""tools/modellvergleich.py — Befund-LLM-Vergleich je Kette (kaiscribe-modellvergleich-n1, 13.11.2026). NUR MESSUNG.

Schickt die 18 synthetischen Harness-Diktate (test_all_regions.TEST_CASES) durch die echte Web-Kette
(Call 0 Korrektur → Gen → Validator, pp.web_kette) bzw. EXE-Kette (nur Gen, pp.exe_kette) und misst je Befund:
Wandzeit (Latenz, Regionen parallel wie in der App), Kosten aus usage (mit und ohne Cache gerechnet), Token je Rolle.
Welches Modell welche Rolle bekommt, steuert KAISCRIBE_TEST_ROUTE (siehe tools/testkosten.py), z. B.

  KAISCRIBE_TEST_ROUTE="alle=gemini-4-hydrogen@eu~LOW" python tools/modellvergleich.py hydrogen web 2
  KAISCRIBE_TEST_ROUTE="gen=claude-sonnet-5-5,korr=gemini-3.5-flash@eu,val=gemini-3.5-flash@eu" … mix web 1

Ausgabe: docs/benchmarks/modellvergleich_<name>_<kette>.json (+ SUMMARY-Zeile).
"""
import json
import pathlib
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import testkosten as tk  # noqa: E402
import test_all_regions as H  # noqa: E402
import prod_pipeline as pp  # noqa: E402

_call_vorher, _argv = H.call_gemini, sys.argv
sys.argv = ["model_ab", "gemini-3.5-flash", "eu"]
import model_ab  # noqa: E402  (nur treue(): Normalbefund-Treue wie im A/B vom 26.09.)
sys.argv, H.call_gemini = _argv, _call_vorher

NAME, KETTE = sys.argv[1], sys.argv[2]
RUNS = tk.argv_laeufe(3, 1)
NUR = sys.argv[4].split(",") if len(sys.argv) > 4 else None


def buch_ab(n0):
    try:
        with open(tk.BUCH.pfad, encoding="utf-8") as f:
            zeilen = [json.loads(z) for z in f if z.strip()]
    except FileNotFoundError:
        return []
    return [z for z in zeilen[n0:] if z.get("pid") == __import__("os").getpid()]


def ohne_cache_usd(z):
    """Kosten desselben Aufrufs, wenn der Cache-Anteil voll bezahlt würde (Produktion heute: kein expliziter Cache)."""
    ort = "anthropic" if z["art"] == "anthropic" else "eu"
    p_in, _pc, p_out, _ = tk.preis(z["modell"], ort)
    return (z["in"] * p_in + z["out"] * p_out) / 1e6


def zeilen_zahl():
    try:
        with open(tk.BUCH.pfad, encoding="utf-8") as f:
            return sum(1 for z in f if z.strip())
    except FileNotFoundError:
        return 0


SEITEN = {"links": "rechts", "rechts": "links"}


def seiten_treue(diktat, rep):
    """Diktierte Seite steht im Titel, die Gegenseite nirgends im Befund (außer das Diktat nennt beide/beidseits)."""
    d, r = diktat.lower(), (rep or "").lower()
    titel = r.split("\n", 1)[0]
    genannt = [s for s in SEITEN if re.search(rf"\b{s}", d)]
    if len(genannt) != 1 or "beidseit" in d:
        return None
    s = genannt[0]
    return bool(re.search(rf"\b{s}", titel)) and not re.search(rf"\b{SEITEN[s]}", r)


def ein_befund(fall):
    name, _key, diktat, _exp = fall
    t0 = time.time()
    try:
        rep = (pp.web_kette if KETTE == "web" else pp.exe_kette)(diktat)
        fehler = ""
    except Exception as e:  # noqa: BLE001
        rep, fehler = "", str(e)[:200]
    bef = rep.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in rep else ""
    kept, pool = model_ab.treue(H.TEMPLATES[_key]["body"], diktat, _exp, bef)
    fehlt = [e for e in _exp if e.lower()[:6] not in rep.lower()]
    return {"name": name, "s": round(time.time() - t0, 2), "report": rep, "fehler": fehler, "treue": [kept, pool],
            "seite_ok": seiten_treue(diktat, rep), "pathologie_fehlt": fehlt}


def main():
    faelle = [f for f in H.TEST_CASES if not NUR or f[0] in NUR]
    tk.projekt()                                   # Token vorab holen (sonst landet das in der Latenz des 1. Befunds)
    if any(m.startswith("claude") for m, _o, _d in tk.route().values()):
        tk._anthropic_key()                        # Vaultwarden-Abruf ≈ 20 s, nicht mitmessen
    rows = []
    for run in range(RUNS):
        for fall in faelle:          # nacheinander, damit die Wandzeit je Befund nicht durch Nachbarn verfälscht wird
            n0 = zeilen_zahl()
            r = ein_befund(fall)
            calls = buch_ab(n0)
            r.update(run=run, usd=round(sum(z["usd"] for z in calls if z["art"] != "cache-anlegen"), 5),
                     usd_ohne_cache=round(sum(ohne_cache_usd(z) for z in calls if z["art"] != "cache-anlegen"), 5),
                     calls=[{k: z.get(k) for k in ("rolle", "modell", "s", "in", "cache", "out", "denk", "usd")}
                            for z in calls if z["art"] != "cache-anlegen"])
            rows.append(r)
            print(f"{run} {r['name'][:40]:40s} {r['s']:6.1f} s {r['usd']:.4f} $ {r['fehler'][:80]}", flush=True)
    ok = [r for r in rows if not r["fehler"]]
    lat = sorted(r["s"] for r in ok)
    summ = {"name": NAME, "kette": KETTE, "route": tk.route(), "n": len(rows), "fehler": len(rows) - len(ok),
            "latenz_median_s": round(statistics.median(lat), 2) if lat else None,
            "latenz_p95_s": round(lat[max(0, int(round(0.95 * len(lat))) - 1)], 2) if lat else None,
            "usd_je_befund": round(statistics.mean(r["usd"] for r in ok), 5) if ok else None,
            "usd_je_befund_ohne_cache": round(statistics.mean(r["usd_ohne_cache"] for r in ok), 5) if ok else None}
    kp = [r["treue"] for r in ok]
    summ["normalbefund_treue"] = f"{sum(k for k, _ in kp)}/{sum(p for _, p in kp)}"
    sd = [r["seite_ok"] for r in ok if r["seite_ok"] is not None]
    summ["seiten_treue"] = f"{sum(sd)}/{len(sd)}"
    summ["pathologie_fehlt"] = sum(len(r["pathologie_fehlt"]) for r in ok)
    for rolle in ("korr", "gen", "val"):
        c = [c for r in ok for c in r["calls"] if c["rolle"] == rolle]
        if c:
            summ[f"{rolle}_s_median"] = round(statistics.median(x["s"] for x in c), 2)
            summ[f"{rolle}_out_mittel"] = round(statistics.mean(x["out"] for x in c))
            summ[f"{rolle}_denk_mittel"] = round(statistics.mean(x.get("denk") or 0 for x in c))
    if summ["usd_je_befund"] is not None:
        summ["usd_monat_3000"] = round(summ["usd_je_befund"] * 3000, 2)
        summ["usd_monat_3000_ohne_cache"] = round(summ["usd_je_befund_ohne_cache"] * 3000, 2)
    out = ROOT / "docs" / "benchmarks" / f"modellvergleich_{NAME}_{KETTE}.json"
    out.write_text(json.dumps({"summary": summ, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SUMMARY", json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
