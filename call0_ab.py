#!/usr/bin/env python3
"""call0_ab.py — STT-Korrektur-Call (App.tsx correctionPrompt, echt extrahiert) auf den
chirp_3-Rohtranskripten der echten Diktate: 2.5-flash (IST) vs 3.5-flash eu."""
import json, re, sys, time, statistics, pathlib
sys.argv = [sys.argv[0], "gemini-2.5-flash", "europe-west3", "1"]
import model_ab as M
ROOT = pathlib.Path(__file__).parent
app = (ROOT / "web_app/src/App.tsx").read_text()
from call0_prompt import build_call0_prompt  # v3.1: Prompt exakt wie Web-App (Fehlhör-Block + auto-Regeln)
res = json.load(open(ROOT / "stt_ab_results.json"))
raws = [r for r in res["chirp_3 (IST)"] if not r["txt"].startswith("ERR")]
import stt_ab as S  # TERMS
HOST = {"europe-west3": "https://europe-west3-aiplatform.googleapis.com", "eu": "https://aiplatform.eu.rep.googleapis.com"}
for model, loc in (("gemini-2.5-flash", "europe-west3"), ("gemini-3.5-flash", "eu")):
    M.URL = f"{HOST[loc]}/v1/projects/rakscribe/locations/{loc}/publishers/google/models/{model}:generateContent"
    M.TIMES.clear(); hits = n = 0
    for r in raws:
        prompt = build_call0_prompt(r["txt"])
        out = M.call(prompt)
        terms = S.TERMS.get(r["file"])
        if terms:
            h = sum(1 for t in terms if re.search(t, out, re.I)); hits += h; n += len(terms)
        print(f"[{model}] {r['file']}: {out[:220]}")
    print(f"== {model}: Termini {hits}/{n}, median {statistics.median(M.TIMES):.2f}s\n")
