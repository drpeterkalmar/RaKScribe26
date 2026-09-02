#!/usr/bin/env python3
"""Quick Diff-Test: Call #1 vs Call #2 für 3 repräsentative Fälle."""
import json
import os
import urllib.request
import time
from pathlib import Path

API_KEY = os.environ.get("VERTEX_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
VERTEX_URL = "https://europe-west3-aiplatform.googleapis.com/v1/projects/895690562186/locations/europe-west3/publishers/google/models/gemini-2.5-flash:generateContent"

TEMPLATES_PATH = Path.home() / "RaKScribe26" / "web_app" / "src" / "templates.json"
with open(TEMPLATES_PATH) as f:
    TEMPLATES = json.load(f)

# Import CONFLICT_RULES + build_gen_prompt + build_val_prompt from test_all_regions
import sys
sys.path.insert(0, str(Path.home() / "RaKScribe26"))
from test_all_regions import CONFLICT_RULES, build_gen_prompt, build_val_prompt

def call_gemini(prompt, token=None, temperature=0.0, timeout=120):
    headers = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature}
    }).encode()
    req = urllib.request.Request(VERTEX_URL, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    if "error" in data:
        raise Exception(f"Gemini API error: {data['error'].get('message', data['error'])}")
    return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()

CASES = [
    # Die 4 WARN-Fälle aus test_results_v4.txt
    ("LWS Osteochondrose+Spondylose+Facettenarthrose", "lendenwirbelsäule_in_2_ebenen",
     "Lendenwirbelsäule, Röntgen, Skoliose, flachbogig linkskonvex, Osteochondrose L4/L5 sowie L5/S1, Spondylosis deformans L3 bis L5, Facettengelenksarthrosen L3 bis S1, Retrolisthese L4 gegenüber L5. Ansonsten unauffällig."),
    ("Ellbogen Fraktur", "ellbogengelenk_in_2_ebenen",
     "Ellbogen rechts, Röntgen, dislozierte Fraktur des Radiusköpfchens. Ansonsten unauffällig."),
    ("Hand Fraktur", "hand_in_2_ebenen",
     "Hand links, Röntgen, nicht dislozierte Fraktur der Kahnbeintaille links. Ansonsten unauffällig."),
    ("Sprunggelenk Arthrose", "sprunggelenk_in_2_ebenen",
     "Sprunggelenk links, Röntgen, Arthrose des oberen Sprunggelenkes, Gelenkspaltverschmälerung, subchondrale Sklerosierung, Osteophyten. Ansonsten unauffällig."),
]

for name, tkey, diktat in CASES:
    template_body = TEMPLATES.get(tkey, {}).get("body", "")
    print(f"\n{'='*70}")
    print(f"CASE: {name}")
    print(f"{'='*70}")

    gen_prompt = build_gen_prompt(diktat, template_body)
    t0 = time.time()
    call1 = call_gemini(gen_prompt, None, temperature=0.0)
    print(f"\n[Call #1] ({time.time()-t0:.1f}s):")
    print(call1)

    val_prompt = build_val_prompt(diktat, call1)
    t0 = time.time()
    call2 = call_gemini(val_prompt, None, temperature=0.0)
    print(f"\n[Call #2] ({time.time()-t0:.1f}s):")
    print(call2)

    if call1.strip() == call2.strip():
        print("\n✅ IDENTISCH — keine Korrektur nötig")
    else:
        print("\n⚠️ UNTERSCHIEDLICH — diff:")
        # Simple line diff
        lines1 = call1.split("\n")
        lines2 = call2.split("\n")
        for i, (l1, l2) in enumerate(zip(lines1, lines2)):
            if l1 != l2:
                print(f"  Line {i+1}:")
                print(f"    - {l1}")
                print(f"    + {l2}")
        if len(lines1) != len(lines2):
            print(f"  (Länge unterschiedlich: {len(lines1)} vs {len(lines2)})")

    time.sleep(1)

print("\nDone.")