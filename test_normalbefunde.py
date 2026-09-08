#!/usr/bin/env python3
"""
Normalbefund-Treue-Test (v2.10.10) — der Deckel gegen das K&L/Normalbefund-Rezidiv.

Prüft:
1. TAUGHT-COVERAGE: Jeder der 44 beigebrachten Normalbefund-Blöcke (Skill
   radiology-shoulder-dictation) muss im zugeordneten App-Template nahezu
   vollständigt satzidentisch enthalten sein. Das war v2.10.9 der Kernfehler:
   App-Templates waren eine ältere, kürzere Generation.
2. DETECTOR-UNIT-TESTS: Der echte detect_template aus source_code/RaKScribe.py
   (per AST extrahiert, nicht nachgebaut) muss die 16 neuen Keys erreichen.
3. BYPASS-SIMULATION: Der Normalbefund-Bypass (kein LLM) muss für neue Templates
   das v2.10.8-Headerformat produzieren: ## Titel vor ## Befund.

Exit-Code 0 = alle Gates PASS. Läuft ohne Netz.
"""
import ast
import json
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).parent
TAUGHT = json.loads((REPO / "taught_blocks.json").read_text())
TPL = json.loads((REPO / "templates.json").read_text())

# taught-Blockname → Template-Key (MIRROR aus migrate_normalbefunde.py — synchron halten!)
MAPPING = {
    "Schädel in 2 Ebenen": "schädel_in_2_ebenen",
    "Orbita p.-a.-Aufnahme": "orbita_pa_aufnahme",
    "Halswirbelsäule in 2 Ebenen mit Dens-Zielaufnahme": "halswirbelsäule_in_2_ebenen",
    "Brustwirbelsäule in 2 Ebenen": "brustwirbelsäule_in_2_ebenen",
    "Lendenwirbelsäule in 2 Ebenen": "lendenwirbelsäule_in_2_ebenen",
    "Steißbein in 2 Ebenen": "steißbein_in_2_ebenen",
    "Kreuzbein in 2 Ebenen": "kreuzbein_und_steißbein_in_2_ebenen",
    "Beckenübersicht a.-p. stehend": "beckenübersicht_stehend",
    "Hüftgelenk in 2 Ebenen": "hüftgelenk_in_2_ebenen",
    "Kniegelenk in 2 Ebenen": "kniegelenk_in_2_ebenen",
    "Unterschenkel in 2 Ebenen": "unterschenkel_in_2_ebenen",
    "Sprunggelenk in 2 Ebenen": "sprunggelenk_in_2_ebenen",
    "Sprunggelenk mit Mortise View in 2 Ebenen": "sprunggelenk_mortise_view",
    "Sprunggelenk in 2 Ebenen mit gehaltenen Aufnahmen": "sprunggelenk_gehaltene_aufnahmen",
    "Sprunggelenk in 2 Ebenen mit Fuß": "sprunggelenk_mit_fuss",
    "Calcaneus in 2 Ebenen": "calcaneus_in_2_ebenen",
    "Calcaneus seitlich": "calcaneus_seitlich",
    "Zehe in 2 Ebenen": "zehe_in_2_ebenen",
    "Fuß in 2 Ebenen": "fuß_in_2_ebenen",
    "Vorfuß in 2 Ebenen": "vorfuß_in_2_ebenen",
    "Thorax p.a. und seitlich": "thorax_in_2_ebenen",
    "Knöcherner Hemithorax": "knöcherner_hemithorax",
    "Abdomen im Stand": "abdomen_im_stand",
    "Abdomen im Liegen": "abdomen_im_liegen",
    "Nasennebenhöhlen in 2 Ebenen": "nasennebenhöhlen",
    "Schädelfernröntgen": "schädelfernröntgen",
    "Magen-Duodenum in Doppelkontrast": "durchleuchtung:_magen-darm-passage_mdp",
    "Oesophagus in Doppelkontrast": "durchleuchtung:_ösophagus-breischluck",
    "Oesophagus-Magenduodenum in Doppelkontrast": "oesophagus_magenduodenum_doppelkontrast",
    "Videokinematographie des Schluckaktes": "videokinematographie_schluckakt",
    "Hysterosalpingographie": "hysterosalpingographie",
    "Aszendierende Pressphlebographie des rechten Beins": "aszendierende_pressphlebographie",
    "Intravenöse Urographie (IVP)": "intravenöses_urogramm",
    "Schultergelenk in 2 Ebenen": "schultergelenk_in_2_ebenen",
    "Finger in 2 Ebenen": "finger_in_2_ebenen",
    "Skaphoidaufnahme": "skaphoidaufnahme",
    "Sonographie der Schulter": "sonografie_schultergelenk",
    # 'Sonographie Hals' → gemerged in sonografie_halsweichteile (Teilmengen-Check unten)
    "Sonographie der Bauchdecke": "sonografie_bauchdecke",
    "Sonographie der dorsalen Oberschenkelmuskulatur": "sonografie_dorsaler_oberschenkel",
    "Sonographie des M. gastrocnemius medialis": "sonografie_gastrocnemius_medialis",
    "Sonographie der dorsalen Unterschenkelmuskulatur": "sonografie_dorsaler_unterschenkel",
    "Sonographie der anterioren Oberschenkelmuskulatur": "sonografie_anteriorer_oberschenkel",
    "Farbcodierte Duplex-Sonographie der Halsgefäße": "sonografie_halsgefaesse",
}

def norm(s: str) -> str:
    s = s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"[^a-z0-9<>=.,]+", " ", s).strip()
    return re.sub(r"\s+", " ", s)

# taught-Blockname ↔ Template-Key in beide Richtungen
KEY_TO_TAUGHT = {v: k for k, v in MAPPING.items()}

def taught_sentences(block: str):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", block) if len(s.strip()) > 30]

failures = []

# ── 1. TAUGHT-COVERAGE ────────────────────────────────────────────────────
print("=" * 70)
print("TEIL 1: TAUGHT-COVERAGE (44 Blöcke)")
print("=" * 70)
for name, key in MAPPING.items():
    body = TPL[key]["body"]
    body_after_title = "\n".join(body.split("\n")[1:])  # Zeile 1 = display_name
    sents = taught_sentences(TAUGHT[name])
    misses = [s for s in sents if norm(s)[:70] not in norm(body_after_title)]
    status = "✅ PASS" if not misses else "❌ FAIL"
    if misses:
        failures.append(f"Coverage {name} → {key}: {len(misses)}/{len(sents)} Sätze fehlen: {misses[0][:80]}")
    print(f"{status}  {name} → {key} ({len(sents)-len(misses)}/{len(sents)} Sätze)")
    for s in misses:
        print(f"      fehlt: {s[:100]}")

# Teilmenge 'Sonographie Hals' ⊂ sonografie_halsweichteile
hw = norm(TPL["sonografie_halsweichteile"]["body"])
sub_ok = all(norm(s)[:70] in hw for s in taught_sentences(TAUGHT["Sonographie Hals"]))
print(f"{'✅ PASS' if sub_ok else '❌ FAIL'}  Sonographie Hals ⊂ sonografie_halsweichteile")
if not sub_ok:
    failures.append("Sonographie Hals nicht in sonografie_halsweichteile enthalten")

# ── 2. DETECTOR-UNIT-TESTS (echter Code, per AST extrahiert) ─────────────
print("\n" + "=" * 70)
print("TEIL 2: DETECTOR-TESTS (echter detect_template aus RaKScribe.py)")
print("=" * 70)
tree = ast.parse((REPO / "source_code" / "RaKScribe.py").read_text())
fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "detect_template")
ns = {"re": re, "RADIOLOGY_TEMPLATES": TPL}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<detect_template>", "exec"), ns)
detect = ns["detect_template"]

DETECT_CASES = [
    # (diktat, erwarteter key)
    ("HW ist unauffällig", "halswirbelsäule_in_2_ebenen"),
    ("Calcaneus rechts in 2 Ebenen unauffällig", "calcaneus_in_2_ebenen"),
    ("Calcaneus seitlich unauffällig", "calcaneus_seitlich"),
    ("Orbita p.a. beidseits unauffällig", "orbita_pa_aufnahme"),
    ("Skaphoidaufnahme beidseits", "naviculareserie"),
    ("Naviculareserie unauffällig", "naviculareserie"),
    ("Sprunggelenk mit Mortise View unauffällig", "sprunggelenk_mortise_view"),
    ("Sprunggelenk in 2 Ebenen mit gehaltenen Aufnahmen unauffällig", "sprunggelenk_gehaltene_aufnahmen"),
    ("Sprunggelenk in 2 Ebenen mit Fuß unauffällig", "sprunggelenk_mit_fuss"),
    ("Sprunggelenk in 2 Ebenen unauffällig", "sprunggelenk_in_2_ebenen"),
    ("Sonographie der Bauchdecke, keine Hernie", "sonografie_bauchdecke"),
    ("Sonographie Muskulatur Oberschenkel dorsal unauffällig", "sonografie_dorsaler_oberschenkel"),  # 'Muskulatur' ohne 'muskel'
    ("Sonographie M. gastrocnemius medialis unauffällig", "sonografie_gastrocnemius_medialis"),
    ("Sonographie dorsale Unterschenkelmuskulatur unauffällig", "sonografie_dorsaler_unterschenkel"),
    ("Sonographie anteriorer Oberschenkelmuskulatur unauffällig", "sonografie_anteriorer_oberschenkel"),
    ("Visa beidseits unauffällig", "videokinematographie_schluckakt"),
    ("Videokinematographie des Schluckaktes unauffällig", "videokinematographie_schluckakt"),
    ("Ösophagus-Magenduodenum in Doppelkontrast unauffällig", "oesophagus_magenduodenum_doppelkontrast"),
    ("Ösophagus-Breischluck unauffällig", "durchleuchtung:_ösophagus-breischluck"),
    ("Aszendierende Pressphlebographie unauffällig", "aszendierende_pressphlebographie"),
    ("Beinphlebographie unauffällig", "beinphlebographie"),
    ("HWS unauffällig", "halswirbelsäule_in_2_ebenen"),          # Regression: nicht calcaneus etc.
    ("Thorax p.a. und seitlich unauffällig", "thorax_in_2_ebenen"),
    ("Schädelfernröntgen unauffällig", "schädelfernröntgen"),
    ("Mammographie beidseits unauffällig", "mammographie_beidseits"),
]
for diktat, expected in DETECT_CASES:
    got = detect(diktat)
    ok = got == expected
    print(f"{'✅ PASS' if ok else '❌ FAIL'}  detect({diktat!r}) = {got!r}" + ("" if ok else f"  erwartet: {expected!r}"))
    if not ok:
        failures.append(f"detect_template({diktat!r}) → {got!r}, erwartet {expected!r}")

# ── 3. BYPASS-SIMULATION (Headerformat v2.10.8) ──────────────────────────
print("\n" + "=" * 70)
print("TEIL 3: BYPASS-SIMULATION (## Titel vor ## Befund, Ergebnis = Rohtext)")
print("=" * 70)
def bypass_report(raw: str, key: str) -> str:
    body = TPL[key]["body"].split("\n")
    tpl_title = body[0].strip().rstrip(":")
    tpl_rest = "\n".join(body[1:])
    formatted = raw.strip()
    formatted = re.sub(r"\bHW\b", "HWS", formatted)
    formatted = formatted[0].upper() + formatted[1:]
    if not formatted.endswith("."):
        formatted += "."
    return f"## {tpl_title}\n\n## Befund\n{tpl_rest}\n\n## Ergebnis\n{formatted}"

BYPASS_CASES = [
    ("HW ist unauffällig", "halswirbelsäule_in_2_ebenen"),
    ("Calcaneus in 2 Ebenen unauffällig", "calcaneus_in_2_ebenen"),
    ("Orbita p.a. unauffällig", "orbita_pa_aufnahme"),
    ("Sonographie der Schulter beidseits unauffällig", "sonografie_schultergelenk"),
]
for raw, key in BYPASS_CASES:
    rep = bypass_report(raw, key)
    taught_key = KEY_TO_TAUGHT[key]
    kern = taught_sentences(TAUGHT[taught_key])[0]
    checks = [
        rep.startswith("## "),
        "## Befund" in rep,
        "## Ergebnis" in rep,
        rep.index("## Befund") < rep.index("## Ergebnis"),
        norm(kern)[:70] in norm(rep),
    ]
    ok = all(checks)
    print(f"{'✅ PASS' if ok else '❌ FAIL'}  Bypass {key} (Header vor Befund + taught-Satz drin)")
    if not ok:
        failures.append(f"Bypass-Simulation {key} fehlgeschlagen")

print("\n" + "=" * 70)
if failures:
    print(f"❌ {len(failures)} FAILS:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("✅ ALLE NORMALBEFUNDE-GATES PASS")
print("=" * 70)