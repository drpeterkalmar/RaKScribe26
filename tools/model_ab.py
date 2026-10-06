#!/usr/bin/env python3
"""tools/model_ab.py — Befund-LLM A/B (26.09.2026): gleicher Harness (18 Fälle, Gen+Val,
Widerspruchs-/Vollständigkeits-Checks) + NORMALBEFUND-TREUE + Latenz pro Modell.

Normalbefund-Treue = Anteil der Template-Sätze (ohne Titelzeile), die WÖRTLICH im
finalen Befund stehen, gemessen NUR an Sätzen, die keinen Bezug zur diktierten
Pathologie haben (Satz enthält keines der Pathologie-Stichworte / Deskriptoren /
Region-Wörter des Konflikts). So misst die Zahl: 'bleiben unsere Normalbefunde
unangetastet, wo das Diktat nichts sagt?'

Aufruf: python3 tools/model_ab.py <model> <location> [runs]  → ab_<model>_<loc>.json
"""
import json, re, sys, time, os, urllib.request, urllib.error, pathlib, statistics
ROOT = pathlib.Path(__file__).resolve().parents[1]  # Repo-Root (Skript liegt in tools/)
sys.path.insert(0, str(ROOT / "tools"))
import test_all_regions as H  # noqa

MODEL, LOC = sys.argv[1], sys.argv[2]
RUNS = int(sys.argv[3]) if len(sys.argv) > 3 else 1
PROJECT = "rakscribe"
HOST = {"europe-west3": "https://europe-west3-aiplatform.googleapis.com",
        "eu": "https://aiplatform.eu.rep.googleapis.com",
        "global": "https://aiplatform.googleapis.com"}[LOC]
URL = f"{HOST}/v1/projects/{PROJECT}/locations/{LOC}/publishers/google/models/{MODEL}:generateContent"
TIMES = []
OUTS = []
# Bezug Diktat→Template-Satz: diese Satz-Stämme DÜRFEN bei der Pathologie angepasst werden
CONFLICT = {
 'arthrose': ['gelenkspalt', 'gelenkfläch', 'gelenkränd', 'konturiert', 'kongruent', 'artikulier', 'form'],
 'fraktur': ['form', 'kontur', 'kortikal', 'kompakta', 'knochenstruktur', 'stellung', 'artikulier', 'gelenkfläch'],
 'osteochondr': ['bandscheib', 'zwischenwirbel', 'grund- und deckplatt'],
 'diskopath': ['bandscheib', 'zwischenwirbel'], 'discopath': ['bandscheib', 'zwischenwirbel'],
 'spondyl': ['randkontur', 'kortikal'], 'facette': ['wirbelgelenk', 'gelenkfortsätz'],
 'skoliose': ['lordose', 'kyphose', 'achse', 'stellung'], 'kyphose': ['kyphose', 'stellung', 'form'],
 'fehlhaltung': ['lordose', 'achse', 'stellung'], 'streckhaltung': ['lordose', 'achse', 'stellung'],
 'listhese': ['stellung'], 'keilwirbel': ['form'], 'schmorl': ['grund- und deckplatt', 'randkontur'],
 'scheuermann': ['form', 'grund- und deckplatt'], 'hochstand': ['stellung'], 'kalzifik': ['weichteil'],
 'beckenschief': ['beckenkamm', 'symmetr'], 'coxarthrose': ['hüftk', 'gelenkspalt', 'gelenkfläch'],
 'dissoziation': ['stellung', 'gelenkspalt', 'artikulier'], 'sinus': ['nebenhöhl'], 'schleimhaut': ['nebenhöhl'],
 'unkovertebral': ['wirbelgelenk'], 'gelenksarthrose': ['wirbelgelenk'],
}


VAL_MODEL = os.environ.get("VAL_MODEL")  # "model@loc" für Hybrid
VAL_MARK = "Du bist ein radiologischer Qualitätskontrolleur"
def call(prompt, token=None, temperature=0.0, timeout=120):
    url = URL
    if VAL_MODEL and prompt.lstrip().startswith(VAL_MARK):
        vm, vl = VAL_MODEL.split("@")
        vh = {"europe-west3": "https://europe-west3-aiplatform.googleapis.com", "eu": "https://aiplatform.eu.rep.googleapis.com", "global": "https://aiplatform.googleapis.com"}[vl]
        url = f"{vh}/v1/projects/{PROJECT}/locations/{vl}/publishers/google/models/{vm}:generateContent"
    gc = {"temperature": temperature, "thinkingConfig": {"thinkingBudget": 0}}
    body = json.dumps({"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                       "generationConfig": gc}).encode()
    for attempt in range(5):
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json", "Authorization": "Bearer " + H._get_sa_token()})
        t = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            TIMES.append(time.time() - t)
            parts = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            o = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            OUTS.append(o)
            return o
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 4:
                time.sleep(15 * (attempt + 1)); continue
            raise Exception(f"HTTP {e.code} {e.read()[:200]}")
        except Exception:
            if attempt < 4:
                time.sleep(5); continue
            raise


H.call_gemini = call  # run_test_case nutzt den Modul-Namen


def strip_fences(t):
    return re.sub(r"^```[a-z]*\s*|\s*```$", "", t.strip())


def sentences(body):
    lines = body.split("\n")[1:]  # Titelzeile raus
    txt = " ".join(l.strip() for l in lines if l.strip() and not l.strip().endswith(":"))
    # Abkürzungen schützen
    prot = re.sub(r"\b(N|M|Lig|Proc|Os|Mm|Nn|z|B|o|ca|bzw|u|a|p|re|li|bds)\.", lambda m: m.group(1) + "§", txt)
    out = [s.replace("§", ".").strip() for s in re.split(r"(?<=[.!?])\s+", prot)]
    return [s for s in out if len(s) > 15]


def norm(s):
    return re.sub(r"\s+", " ", s.lower().replace("ß", "ss")).strip(" .")


def treue(template_body, diktat, expected, befund):
    dl = diktat.lower()
    keys = [e.lower()[:6] for e in expected]
    for p, stems in CONFLICT.items():
        if p in dl:
            keys += stems
    pool, kept = [], 0
    for s in sentences(template_body):
        sl = s.lower()
        if any(k in sl for k in keys):
            continue  # Satz betrifft Diktat-Inhalt → darf angepasst werden
        pool.append(s)
        if norm(s) in norm(befund):
            kept += 1
    return kept, len(pool)


def main():
    rows = []
    for run in range(RUNS):
        for name, tkey, diktat, expected in H.TEST_CASES:
            body = H.TEMPLATES[tkey]["body"]
            t0 = time.time(); n0 = len(TIMES); o0 = len(OUTS)
            try:
                r = H.run_test_case(name, tkey, diktat, expected, None)
            except Exception as e:
                r = {"name": name, "status": "ERROR", "issues": [str(e)[:200]]}
            wall = time.time() - t0
            fin = strip_fences(r.get("report", ""))
            bef = fin.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in fin else ""
            k, n = treue(body, diktat, expected, bef)
            g = strip_fences(OUTS[o0]) if len(OUTS) > o0 else ""
            gb = g.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in g else ""
            k1, _ = treue(body, diktat, expected, gb)
            rows.append({"run": run, "name": name, "status": r["status"], "issues": r.get("issues", []),
                         "wall": round(wall, 2), "calls": [round(x, 2) for x in TIMES[n0:]],
                         "treue_kept": k, "treue_pool": n, "treue_call1": k1, "gen": g, "report": fin})
    st = [r["status"] for r in rows]
    kept = sum(r["treue_kept"] for r in rows); pool = sum(r["treue_pool"] for r in rows)
    summ = {"val": VAL_MODEL, "model": MODEL, "loc": LOC, "runs": RUNS, "n": len(rows),
            "PASS": st.count("✅ PASS"), "WARN": st.count("⚠️ WARN"), "FAIL": st.count("❌ FAIL"),
            "ERROR": st.count("ERROR"),
            "missing_in_ergebnis": sum(1 for r in rows for i in r["issues"] if "fehlt im Ergebnis" in i),
            "treue": f"{kept}/{pool} = {100*kept/max(pool,1):.1f}%",
            "treue_call1": f"{sum(r['treue_call1'] for r in rows)}/{pool}",
            "call_median_s": round(statistics.median(TIMES), 2) if TIMES else None,
            "call_p90_s": round(sorted(TIMES)[int(0.9 * len(TIMES)) - 1], 2) if TIMES else None,
            "case_median_s": round(statistics.median(r["wall"] for r in rows), 2)}
    out = ROOT / "docs" / "benchmarks" / (f"ab_{MODEL}_{LOC}" + (f"__val_{VAL_MODEL}" if VAL_MODEL else "") + ".json")
    out.write_text(json.dumps({"summary": summ, "rows": rows}, ensure_ascii=False, indent=1))
    print("SUMMARY", json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
