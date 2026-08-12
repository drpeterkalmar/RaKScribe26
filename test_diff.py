#!/usr/bin/env python3
"""Quick Diff-Test: Call #1 vs Call #2 für 3 repräsentative Fälle."""
import json
import urllib.request
import time
from pathlib import Path
import google.auth.transport.requests as grequests
from google.oauth2.service_account import Credentials

KEY_PATH = Path.home() / ".hermes" / "rakscribe-google-key.json"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

TEMPLATES_PATH = Path.home() / "RaKScribe26" / "web_app" / "src" / "templates.json"
with open(TEMPLATES_PATH) as f:
    TEMPLATES = json.load(f)

# Import CONFLICT_RULES + build_gen_prompt + build_val_prompt from test_all_regions
import sys
sys.path.insert(0, str(Path.home() / "RaKScribe26"))
from test_all_regions import CONFLICT_RULES, build_gen_prompt, build_val_prompt

def get_token():
    creds = Credentials.from_service_account_file(
        str(KEY_PATH),
        scopes=["https://www.googleapis.com/auth/generative-language"]
    )
    creds.refresh(grequests.Request())
    return creds.token

def call_gemini(prompt, token, temperature=0.0, timeout=120):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature}
    }).encode()
    req = urllib.request.Request(GEMINI_URL, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
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

token = get_token()

for name, tkey, diktat in CASES:
    template_body = TEMPLATES.get(tkey, {}).get("body", "")
    print(f"\n{'='*70}")
    print(f"CASE: {name}")
    print(f"{'='*70}")

    gen_prompt = build_gen_prompt(diktat, template_body)
    t0 = time.time()
    call1 = call_gemini(gen_prompt, token, temperature=0.0)
    print(f"\n[Call #1] ({time.time()-t0:.1f}s):")
    print(call1)

    val_prompt = build_val_prompt(diktat, call1)
    t0 = time.time()
    call2 = call_gemini(val_prompt, token, temperature=0.0)
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