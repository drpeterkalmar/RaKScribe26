#!/usr/bin/env python3
"""
Normalbefund-Treue-Test (v2.10.10) — der Deckel gegen das K&L/Normalbefund-Rezidiv.

Prüft:
1. TAUGHT-COVERAGE: Jeder der 44 beigebrachten Normalbefund-Blöcke (Skill
   radiology-shoulder-dictation) muss im zugeordneten App-Template nahezu
   vollständigt satzidentisch enthalten sein. Das war v2.10.9 der Kernfehler:
   App-Templates waren eine ältere, kürzere Generation.
2. DETECTOR-UNIT-TESTS: Der echte detect_template (source_code/detect.py, direkt
   importiert) muss die 16 neuen Keys erreichen.
3. BYPASS-SIMULATION: Der Normalbefund-Bypass (kein LLM) muss für neue Templates
   das v2.10.8-Headerformat produzieren: ## Titel vor ## Befund.
4. TITELZEILEN-GATE (v2.10.11): Zeile 1 JEDES Templates = display_name — sonst
   schreibt der Bypass den ersten Befund-Satz als Überschrift (Peter-Fall:
   „Sonomorphologisch unauffällige Verhältnisse…" als Titel der Unterschenkel-Sono).

Exit-Code 0 = alle Gates PASS. Läuft ohne Netz.
"""
import sys as _sys0, pathlib as _pl0
_sys0.path.insert(0, str(_pl0.Path(__file__).parent / "source_code"))
import detect as _detect  # Umbau Schritt 12: echte Erkennung direkt importiert (kein AST-Extrakt mehr)
import json
import os
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
print("TEIL 2: DETECTOR-TESTS (echter detect_template aus source_code/detect.py)")
print("=" * 70)


def detect(diktat):
    return _detect.detect_template(diktat, TPL)


DETECT_CASES = [
    # v3.2.2 Nerven (Georg 05.10.)
    ("N. medianus links unauffällig", "sonografie_nerv_medianus"),
    ("Nervus ulnaris rechts unauffällig", "sonografie_nerv_ulnaris"),
    ("Nervus radialis rechts unauffällig", "sonografie_nerv_radialis"),
    ("Plexus brachialis rechts unauffällig", "sonografie_plexus_brachialis"),
    ("Plexus cervicalis links unauffällig", "sonografie_plexus_cervicalis"),
    ("Nervus ischiadicus rechts unauffällig", "sonografie_nerv_ischiadicus"),
    ("Nervus fibularis links unauffällig", "sonografie_nerv_peroneus"),
    ("Nervus tibialis rechts unauffällig", "sonografie_nerv_tibialis"),
    ("Tarsaltunnel rechts unauffällig", "sonografie_nerv_tibialis"),
    ("Nervus femoralis rechts unauffällig", "sonografie_nerv_femoralis"),
    ("Nervus cutaneus femoris lateralis links unauffällig", "sonografie_nerv_femoralis_cutaneus_lateralis"),
    ("Nervus pudendus unauffällig", "sonografie_nervus_pudendus"),
    ("Nervus ilioinguinalis rechts unauffällig", "sonografie_nervus_iliohypogastricus_ilioinguinalis"),
    ("Ultraschallgezielte Blockade des Nervus medianus rechts", "ultraschall_gezielte_blockade"),
    ("Sono Schulter rechts unauffällig", "sonografie_schultergelenk"),
    ("Unterarm rechts unauffällig", "unterarm_in_2_ebenen"),
    ("Karpaltunnelaufnahme rechts unauffällig", "karpaltunnelaufnahme"),
    # (diktat, erwarteter key)
    ("HW ist unauffällig", "halswirbelsäule_in_2_ebenen"),
    ("Calcaneus rechts in 2 Ebenen unauffällig", "calcaneus_in_2_ebenen"),
    ("Calcaneus seitlich unauffällig", "calcaneus_seitlich"),
    ("Orbita p.a. beidseits unauffällig", "orbita_pa_aufnahme"),
    ("Skaphoidaufnahme beidseits", "skaphoidaufnahme"),  # v3.2.3: beigebrachter Block hat eigene Vorlage
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
    # v3.2 (Peter 05.10.: unauffälliges Lungenröntgen wurde als Skelett befundet)
    ("Lungenröntgen unauffällig", "thorax_in_2_ebenen"),
    ("Torax unauffällig", "thorax_in_2_ebenen"),
    ("Brustkorb Röntgen unauffällig", "thorax_in_2_ebenen"),
    ("Thorax p.a./seitlich unauffällig", "thorax_in_2_ebenen"),
    ("Thoraxaufnahme p.a. ohne Befund", "thorax_in_2_ebenen"),
    ("Röntgen der Lunge unauffällig", "thorax_in_2_ebenen"),
    ("Pulmo frei, Cor normal groß", "thorax_in_2_ebenen"),
    ("BWS thorakal unauffällig", "brustwirbelsäule_in_2_ebenen"),
    ("Knöcherner Hemithorax rechts unauffällig", "knöcherner_hemithorax"),
    # v3.2: Georgs Mehr-Regionen-Fall — nach dem Trenner je Segment die richtige Vorlage
    ("Schulter rechts Punkt neue Zeile mäßiggradige Omarthrose Punkt", "schultergelenk_in_2_ebenen"),
    ("Ellbogen rechts Punkt neue Zeile geringgradige Ellbogengelenksarthrose Punkt", "ellbogengelenk_in_2_ebenen"),
]
# v3.2: dieselben Fälle durch die Web-Erkennung (App.tsx detectTemplate) — EXE und Web müssen gleich entscheiden
import json as _json, subprocess as _sp, tempfile as _tf
with _tf.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as _f:
    _json.dump(DETECT_CASES, _f, ensure_ascii=False)
_web = _sp.run(["node", "detect_test.mjs", _f.name], cwd=REPO / "web_app", capture_output=True, text=True)
WEB_DETECT = _json.loads(_web.stdout) if _web.returncode == 0 and _web.stdout else {}
if not WEB_DETECT:
    failures.append("Web-detectTemplate nicht ausführbar: " + _web.stderr[-300:])
for diktat, expected in DETECT_CASES:
    if WEB_DETECT and WEB_DETECT.get(diktat) != expected:
        print(f"❌ FAIL  WEB detectTemplate({diktat!r}) = {WEB_DETECT.get(diktat)!r}  erwartet: {expected!r}")
        failures.append(f"Web detectTemplate({diktat!r}) → {WEB_DETECT.get(diktat)!r}")
for diktat, expected in DETECT_CASES:
    got = detect(diktat)
    ok = got == expected
    print(f"{'✅ PASS' if ok else '❌ FAIL'}  detect({diktat!r}) = {got!r}" + ("" if ok else f"  erwartet: {expected!r}"))
    if not ok:
        failures.append(f"detect_template({diktat!r}) → {got!r}, erwartet {expected!r}")

# ── 2c. PARITÄT (Umbau 06.10., Gutachten P1-3/P2-3): detect_fixtures.json durch EXE UND Web ──────────
print("\n" + "=" * 70)
print("TEIL 2c PARITÄT: detect_fixtures.json — EXE detect_template UND Web detectTemplate = Erwartungswert")
print("=" * 70)
DF = _json.loads((REPO / "detect_fixtures.json").read_text(encoding="utf-8"))
_namens = {}  # key → die drei Namens-Diktate (live aus templates.json, damit neue Vorlagen auffallen)
for _k, _v in TPL.items():
    _dn = _v["display_name"].strip()
    _namens[_k] = [f"{_dn} unauffällig", f"{_dn} rechts unauffällig", _k.replace("_", " ") + " o.B."]
_soll = {d: k for d, k in DF["faelle"]}
_fehlt = [d for ds in _namens.values() for d in ds if d not in _soll]
if _fehlt:
    print(f"❌ FAIL  {len(_fehlt)} Namens-Diktate fehlen in detect_fixtures.json (neue Vorlage?): {_fehlt[:3]}")
    failures.append(f"detect_fixtures.json unvollständig: {len(_fehlt)} Namens-Diktate fehlen")
_alle = list(DF["faelle"]) + [[d, None] for d in _fehlt]
with _tf.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as _f2:
    _json.dump(_alle, _f2, ensure_ascii=False)
_w2 = _sp.run(["node", "detect_test.mjs", _f2.name], cwd=REPO / "web_app", capture_output=True, text=True)
WEB2 = _json.loads(_w2.stdout) if _w2.returncode == 0 and _w2.stdout else {}
if not WEB2:
    failures.append("Parität: Web-detectTemplate nicht ausführbar: " + _w2.stderr[-300:])
_abw = 0
for d, soll in DF["faelle"]:
    e, w = detect(d), WEB2.get(d)
    if e != soll or w != soll:
        _abw += 1
        print(f"❌ FAIL  {d!r}: soll {soll} | EXE {e} | Web {w}")
        failures.append(f"Parität {d!r}: soll {soll}, EXE {e}, Web {w}")
print(f"{'✅ PASS' if not _abw else '❌ FAIL'}  {len(DF['faelle']) - _abw}/{len(DF['faelle'])} Diktate: EXE = Web = Erwartungswert")
_unerr = sorted(k for k, ds in _namens.items()
                if not any(detect(d) == k and WEB2.get(d) == k for d in ds))
_neu = sorted(set(_unerr) - set(DF["unerreichbar"]))
_wieder = sorted(set(DF["unerreichbar"]) - set(_unerr))
if _neu:
    print(f"❌ FAIL  neu unerreichbare Vorlagen (über keinen Namens-Diktat erreichbar): {_neu}")
    failures.append(f"Vorlagen neu unerreichbar: {_neu}")
if _wieder:
    print(f"ℹ️  HINWEIS  wieder erreichbar — bitte aus 'unerreichbar' in detect_fixtures.json streichen: {_wieder}")
print(f"{'✅ PASS' if not _neu else '❌ FAIL'}  Erreichbarkeit: {len(TPL) - len(_unerr)}/{len(TPL)} Vorlagen über ihren Namen erreichbar"
      f" (dokumentiert unerreichbar: {len(DF['unerreichbar'])})")

# ── 3. BYPASS-SIMULATION (Headerformat v2.10.8) ──────────────────────────
print("\n" + "=" * 70)
print("TEIL 3: BYPASS-SIMULATION (## Titel vor ## Befund, v3.2: Ergebnis = Normal-Ergebnis, NIE das Diktat)")
print("=" * 70)
import prod_pipeline as _pp  # echte Bypass-Bausteine (normalbypass + befund_regeln) statt eigenem Nachbau
def bypass_report(raw: str, key: str) -> str:
    return _pp.bypass_report(raw, key)

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
        _pp.nb.is_pure_normal_finding(raw, _pp.DISPLAY_NAMES),  # v3.2: strenger Bypass greift
        rep.split("## Ergebnis")[1].strip().rstrip(".") != raw.strip().rstrip("."),  # Diktat nie als Ergebnis
        rep.split("## Ergebnis")[1].strip() == _pp.br.ergebnis_mit_seite(TPL[key].get("ergebnis", ""), raw),
    ]
    ok = all(checks)
    print(f"{'✅ PASS' if ok else '❌ FAIL'}  Bypass {key} (Header vor Befund + taught-Satz drin)")
    if not ok:
        failures.append(f"Bypass-Simulation {key} fehlgeschlagen")

# ── 4. TITELZEILEN-GATE (v2.10.11) ────────────────────────────────────────
# Peters Unterschenkel-Fall (09.09.): Templates OHNE Titelzeile ließen den
# Bypass den ERSTEN BEFUND-SATZ als ##-Überschrift schreiben. Pflicht: Zeile 1
# = display_name (Bypass nimmt body.split('\n')[0] als Titel). Einzige
# tolerierte Abweichung: sonografie_halsgefaesse (wörtlich gemergter
# taught-Block mit Bindestrich „Duplex-Sonographie").
print("\n" + "=" * 70)
print("TEIL 4: TITELZEILEN-GATE (Zeile 1 = display_name, kein Satz als Titel)")
print("=" * 70)
def _clean_title(s: str) -> str:
    return re.sub(r"[\s\-\u2013\u2014:()\.,]+", "", s.lower())

bad_titles = []
for key, t in TPL.items():
    dn = t["display_name"].strip().rstrip(":").strip()
    l1 = t["body"].split("\n")[0].strip().rstrip(":").strip()
    if _clean_title(l1) != _clean_title(dn):
        bad_titles.append(key)
if bad_titles:
    print(f"❌ FAIL  {len(bad_titles)} Templates ohne korrekte Titelzeile: {bad_titles[:10]}")
    failures.append(f"Titelzeilen-Gate: {len(bad_titles)} Templates ohne Zeile 1 = display_name")
else:
    print(f"✅ PASS  Alle {len(TPL)} Templates: Zeile 1 = display_name (Titelzeile)")

# Peters Fall als Regression: 'Unterschenkel-Sonographie rechts unauffällig'
# läuft über sonografie_allgemein. Titel kommt (generisches '(Allgemein)'-Template,
# v2.10.12) aus dem DIKTAT — NIEMALS '(Allgemein)' im Report; Satz 1 bleibt im Befund.
_peters_raw = "Unterschenkel-Sonographie rechts unauffällig."
_derive_titel = _detect.derive_untersuchungs_titel  # echte Funktion (Umbau Schritt 12, vorher Klon)
# v2.10.13-fix2: Peters Unterschenkel-Diktat detectet jetzt das EIGENE Template
# (sonografie_unterschenkel statt allgemein-Fallback) — Fall umgezogen.
_t = TPL["sonografie_unterschenkel"]["body"].split("\n")
_p_title = _derive_titel(_peters_raw, _t[0].strip().rstrip(":"))
_p_rest = "\n".join(_t[1:])
_p_report = _pp.bypass_report(_peters_raw, "sonografie_unterschenkel")  # v3.2: echte Bypass-Logik
_p_befund = _p_report.split("## Befund")[1].split("## Ergebnis")[0]
_p_ok = (
    _p_report.startswith("## Sonographie des Unterschenkels")  # eigenes Template = kanonischer Titel
    and "(Allgemein)" not in _p_report
    and "homogenem, echonormalem Parenchym" in _p_befund  # Unterschenkel-Template-Kernsatz
    and _p_report.strip().endswith("## Ergebnis\n" + _pp.br.ergebnis_mit_seite(TPL["sonografie_unterschenkel"]["ergebnis"], _peters_raw))
    and not _p_report.strip().endswith(_peters_raw)  # v3.2 (Peter 05.10.): Diktat nie 1:1 als Ergebnis
)
print(f"{'✅ PASS' if _p_ok else '❌ FAIL'}  Peters Fall: Titel aus Diktat 'Unterschenkel-Sonographie rechts', kein '(Allgemein)' im Report, Satz 1 im Befund")
if not _p_ok:
    failures.append("Peters Unterschenkel-Fall: Bypass-Report falsch formatiert")

# ── 4b. TITEL-FIXTURES (v2.10.13, K3-Befund 7/8): tabellengetriebene Regression ──
# Eine Quelle der Wahrheit (titel_fixtures.py); geprüft wird die ECHTE Funktion aus source_code/detect.py.
try:
    import titel_fixtures
    _ok, _fails = titel_fixtures.run_fixtures(_detect.derive_untersuchungs_titel)
    if _ok:
        print(f"✅ PASS  Titel-Fixtures: alle {len(titel_fixtures.TITEL_FIXTURES)} Cases gegen echte detect.py-Funktion")
    else:
        for _f in _fails:
            print(f"❌ FAIL  Titel-Fixture: {_f}")
        failures.append(f"Titel-Fixtures: {len(_fails)} Fälle falsch")
except Exception as _e:
    print(f"❌ FAIL  Titel-Fixtures-Modul: {_e}")
    failures.append(f"Titel-Fixtures: {_e}")

print("\n" + "=" * 70)
if failures:
    print(f"❌ {len(failures)} FAILS:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("✅ ALLE NORMALBEFUNDE-GATES PASS")
print("=" * 70)