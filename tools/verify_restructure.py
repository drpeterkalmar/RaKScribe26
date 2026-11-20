#!/usr/bin/env python3
"""tools/verify_restructure.py — Live-Check 3.19.16 Restructure (Peter 20.11.2026, kaiscribe-befundfeld-sicher-n1).

Je Fall: (1) Befund aus einem echten anonymisierten bzw. kurzen Diktat über die EXE-Kette (pipeline.befund_aus_diktat)
= KaiScribe-Stand, (2) Peters Ergänzung wie in der EXE eingebaut (befundfeld.ergaenzen, ohne Cursor), (3) Restructure
(pipeline.befund_umbauen, dieselbe Funktion wie der Knopf). Prüft: Titel bleibt, Peters Angabe im Befund und (als
Befund) im Ergebnis, kein widersprechender Normalsatz übrig (Katalog widersprueche, „Im Übrigen …“ zählt als
eingeschränkt), unveränderte Abschnitte Zeichen für Zeichen, keine Prüfzeilen.
Modell: wie die Produktion über KAISCRIBE_TEST_ROUTE (z. B. alle=claude-sonnet-5-5, maskiert), Kosten über testkosten.
  KAISCRIBE_TEST_ROUTE=alle=claude-sonnet-5-5 python3 tools/verify_restructure.py [läufe] [fall …]
Ergebnis: docs/benchmarks/restructure_live_<Datum>.json (+ .md mit Vorher/Nachher)
"""
import datetime
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "source_code")]
import prod_pipeline as pp  # noqa: E402
import befund_regeln as br  # noqa: E402
import befundfeld as bf  # noqa: E402
import pipeline as pl  # noqa: E402
import testkosten  # noqa: E402

# Diktate: RH 38 / RH 99 / Erhalt-Knie = echte anonymisierte Ordi-Diktate aus verify_konfabulation (12.–18.11.2026)
FAELLE = {
    "knie_enostose": ("Knie links unauffällig.", "Enostose im distalen Femur von 6 mm."),
    "rh38_erguss": ("Kniegelenk links. Mäßige Gelenkspaltverschmälerung des medialen Kniegelenkspaltes, im Übrigen "
                    "unauffällig.", "Kleiner Gelenkerguss im Recessus suprapatellaris."),
    "erhalt_knie_meniskus": ("Kniegelenk rechts: Mäßige Gonarthrose medial betont mit Osteophyten und subchondraler "
                             "Sklerosierung, kein Erguss.", "Zusätzlich Chondrokalzinose des Außenmeniskus."),
    "rh99_fraktur": ("Beckenübersicht stehend. Geringe Gelenkspaltverschmälerung beider Hüftgelenke kranial betont, kein "
                     "Hinweis auf eine Fraktur, im Übrigen unauffällig.",
                     "Alte, knöchern konsolidierte Fraktur des oberen Schambeinasts rechts."),
    "schulter_kalk": ("Schulter rechts unauffällig.", "Kalkdepot im Verlauf der Supraspinatussehne von 8 mm."),
    "mehrfach_hand": ("Knie rechts unauffällig. Hand links unauffällig.", "Hand links: Rhizarthrose."),
}


def titel(report):
    return [b["titel"] for b in bf.bloecke(report) if b["titel"]]


def pruefen(stand, aktuell, nachher, vor, hinweise):
    p = []
    if titel(nachher) != titel(aktuell):
        p.append(f"❌ Titel geändert: {titel(aktuell)} → {titel(nachher)}")
    befundteil = "\n".join(z for z in nachher.split("\n") if z.strip() not in ("## Befund", "## Ergebnis")
                           and z not in bf.ergebnis_text(nachher).split("\n"))
    erg = bf.ergebnis_text(nachher)
    for s in vor:
        if not bf.inhalt_da(s, befundteil):
            p.append(f"❌ Vorrang fehlt im Befund: {s}")
        if br.has_pathology(s) and not bf.inhalt_da(s, erg, 0.5):
            p.append(f"❌ Vorrang fehlt im Ergebnis: {s}")
    befunde = br.widerspruch_befunde(" . ".join(vor))
    for b in bf.bloecke(nachher):
        if not b["befund"]:
            continue
        z = nachher.split("\n")
        text = "\n".join(z[b["befund"][0]:b["befund"][1]])
        if not any(bf.inhalt_da(s, bf.block_text(nachher, b)) for s in vor):
            continue                                   # Abschnitt ohne Peters Änderung (z. B. das Knie daneben)
        for a, e, ids in br.widerspruch_saetze(text, befunde):
            p.append(f"❌ widersprechender Normalsatz übrig: {text[a:e][:80]}")
    alt = {bf.block_text(aktuell, b) for b in bf.bloecke(aktuell)}
    neu = {bf.block_text(nachher, b) for b in bf.bloecke(nachher)}
    if len(bf.bloecke(aktuell)) > 1 and not (alt & neu):
        p.append("❌ unveränderter Abschnitt nicht Zeichen für Zeichen erhalten")
    p += [f"⚠ Prüfzeile: {h}" for h in hinweise]
    return p


def ein_lauf(name, i):
    diktat, zusatz = FAELLE[name]
    t0 = time.time()
    try:
        ctx = pp.exe_kontext()
        stand = pl.befund_aus_diktat(diktat, ctx).report
        aktuell = bf.ergaenzen(stand, zusatz)[0]
        vor = bf.vorrang(stand, aktuell)
        e = pl.befund_umbauen(aktuell, stand, pp.exe_kontext())
    except Exception as ex:  # noqa: BLE001
        return {"fall": name, "lauf": i, "status": "ERROR", "probleme": [f"💥 {ex}"]}
    probleme = pruefen(stand, aktuell, e.report, vor, e.cas_hinweise)
    status = "FAIL" if any(x.startswith("❌") for x in probleme) else ("WARN" if probleme else "PASS")
    return {"fall": name, "lauf": i, "status": status, "probleme": probleme, "diktat": diktat, "zusatz": zusatz,
            "stand": stand, "vorher": aktuell, "nachher": e.report, "vorrang": vor, "hinweise": e.cas_hinweise,
            "s": round(time.time() - t0, 1)}


def main():
    args = sys.argv[1:]
    n = testkosten.laeufe(int(args.pop(0)) if args and args[0].isdigit() else None, 1)
    namen = args or list(FAELLE)
    jobs = [(f, i) for f in namen for i in range(1, n + 1)]
    with ThreadPoolExecutor(max_workers=3) as ex:
        res = list(ex.map(lambda j: ein_lauf(*j), jobs))
    tag = f"{datetime.date.today():%Y%m%d}"
    out = ROOT / "docs" / "benchmarks" / f"restructure_live_{tag}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"prompt": pp.PROMPT_VERSION, "route": testkosten.os.environ.get("KAISCRIBE_TEST_ROUTE", ""),
                               "laeufe": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# Restructure live {tag} (Prompt {pp.PROMPT_VERSION}, Route {testkosten.os.environ.get('KAISCRIBE_TEST_ROUTE', '')})", ""]
    for r in res:
        md += [f"## {r['fall']} #{r['lauf']}: {r['status']}", ""]
        if r.get("diktat"):
            md += [f"Diktat: „{r['diktat']}“ · Ergänzung von Peter: „{r['zusatz']}“", "",
                   "**Vorher (KaiScribe-Befund + Ergänzung):**", "```", r["vorher"], "```",
                   "**Nachher (Restructure):**", "```", r["nachher"], "```"]
        md += [f"- {x}" for x in r["probleme"]] + [""]
    out.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    zus = {}
    for r in res:
        z = zus.setdefault(r["fall"], {"PASS": 0, "WARN": 0, "FAIL": 0, "ERROR": 0})
        z[r["status"]] += 1
        if r["status"] != "PASS":
            print(f"[{r['status']}] {r['fall']} #{r['lauf']}: " + " | ".join(r["probleme"]))
    for f, z in zus.items():
        print(f"{f:22s} PASS {z['PASS']} | WARN {z['WARN']} | FAIL {z['FAIL']} | ERROR {z['ERROR']}")
    print(f"→ {out}  · Kosten Job bisher {testkosten.job_summe():.3f} $")


if __name__ == "__main__":
    main()
