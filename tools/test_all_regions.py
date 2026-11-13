#!/usr/bin/env python3
"""
Vollständiger Widerspruchstest für alle Regionen/Modalitäten.
Testet Generierung + Validierung mit pathologischen Diktaten pro Region.
"""

import json
import os
import re
import urllib.request
import urllib.error
import time
import sys
from pathlib import Path

import testkosten  # noqa: E402  (kaiscribe-testkosten-n1: Testprojekt + Kostenzähler, nimmt --release aus argv)
API_KEY = ""  # Praxis-Schlüssel wird in Tests NICHT mehr benutzt
VERTEX_URL = "https://aiplatform.eu.rep.googleapis.com/v1/projects/<testprojekt>/locations/eu/publishers/google/models/gemini-3.5-flash:generateContent"  # nur Anzeige, Aufruf über testkosten

# Templates laden
TEMPLATES_PATH = Path(__file__).resolve().parents[1] / "templates.json"  # Repo-Root
with open(TEMPLATES_PATH) as f:
    TEMPLATES = json.load(f)

# v3.2: KEINE Prompt-Kopie mehr im Harness — Gen-Prompt = radiology_prompt.txt (eine Quelle für EXE + Web),
# Validator = App.tsx validationPrompt, systemInstruction = SYS_MSG aus RaKScribe.py (siehe tools/prod_pipeline.py).
import prod_pipeline as _pp  # noqa: E402
CONFLICT_RULES = _pp.GEN_PROMPT[_pp.GEN_PROMPT.index("## KONFLIKT-REGELN"):_pp.GEN_PROMPT.index("## STILBEISPIELE")]

# ─── Testfälle ───
TEST_CASES = [
    # (name, template_key, diktat, erwartete_pathologien)
    ("HWS Streckhaltung+Skoliose+Osteochondrose", "halswirbelsäule_in_2_ebenen",
     "HWS, Röntgen, Streckhaltung, flachbogige Konvexität, Skoliose, degenerative Antelisthese C5 gegenüber C6, bei Osteochondrose, bei Unkovertebralgelenksarthrosen und Spondylosis deformans in diesen Segmenten. Ansonsten unauffällig.",
     ["Streckhaltung", "Skoliose", "Antelisthese", "Osteochondrose", "Unkovertebralgelenksarthrose", "Spondylosis deformans"]),

    ("LWS Osteochondrose+Spondylose+Facettenarthrose", "lendenwirbelsäule_in_2_ebenen",
     "Lendenwirbelsäule, Röntgen, Skoliose, flachbogig linkskonvex, Osteochondrose L4/L5 sowie L5/S1, Spondylosis deformans L3 bis L5, Facettengelenksarthrosen L3 bis S1, Retrolisthese L4 gegenüber L5. Ansonsten unauffällig.",
     ["Skoliose", "Osteochondrose", "Spondylosis deformans", "Facettengelenksarthrose", "Retrolisthese"]),

    ("BWS Morbus Scheuermann", "brustwirbelsäule_in_2_ebenen",
     "Brustwirbelsäule, Röntgen, vermehrte Kyphose, Morbus Scheuermann, Keilwirbel Th7 bis Th9, Schmorl-Knoten Th6 bis Th10. Ansonsten unauffällig.",
     ["Kyphose", "Morbus Scheuermann", "Keilwirbel", "Schmorl"]),

    ("Schulter Omarthrose+Tendinosis calcarea", "schultergelenk_in_2_ebenen",
     "Schulter rechts, Röntgen, Omarthrose, Kalzifikation Supraspinatussehne, Humeruskopfhochstand. Ansonsten unauffällig.",
     ["Omarthrose", "Kalzifikation", "Humeruskopfhochstand"]),

    ("Schulter Fraktur", "schultergelenk_in_2_ebenen",
     "Schulter links, Röntgen, dislozierte Fraktur des Collum chirurgicum humeri. Ansonsten unauffällig.",
     ["Fraktur", "Collum chirurgicum"]),

    ("Hüfte Coxarthrose", "hüftgelenk_in_2_ebenen",
     "Hüfte links, Röntgen, Coxarthrose links, Gelenkspaltverschmälerung, subchondrale Sklerosierung, osteophytäre Randwülste. Ansonsten unauffällig.",
     ["Coxarthrose"]),

    ("Hüfte Schenkelhalsfraktur", "hüftgelenk_in_2_ebenen",
     "Hüfte rechts, Röntgen, nicht dislozierte Schenkelhalsfraktur rechts, Garden I. Ansonsten unauffällig.",
     ["Schenkelhalsfraktur", "Garden"]),

    ("Knie Gonarthrose", "kniegelenk_in_2_ebenen",
     "Knie rechts, Röntgen, Gonarthrose rechts, medialbetonte Gelenkspaltverschmälerung, subchondrale Sklerosierung, Osteophyten. Ansonsten unauffällig.",
     ["Gonarthrose"]),   # v3.18.4 (RH 38): kein K&L-Grad ohne Diktat/IB Lab — „Kellgren“ wäre jetzt erfunden

    ("Knie Gonarthrose K&L (Peter 08.09., Screenshot-Case)", "kniegelenk_in_2_ebenen",
     "Kniegelenk links, Röntgen, maßgradige Gonarthrose des medialen Femorotibialkompartiments, geringgradige Retropatellararthrose. Ansonsten unauffällig.",
     ["Gonarthrose", "Retropatellararthrose", "Kellgren"]),   # v3.18.5: diktierte Arthrose + Adjektiv → K&L zum Adjektiv

    # v3.18.4 (Peter 12.11.2026, RH 38): nur Deskriptor diktiert → keine Gonarthrose, keine Osteophyten/Sklerose, kein Grad
    ("Knie Gelenkspaltverschmälerung ohne Diagnose (RH 38, Konfabulation)", "kniegelenk_in_2_ebenen",
     "Kniegelenk links. Mäßige Gelenkspaltverschmälerung des medialen Kniegelenkspaltes, im Übrigen unauffällig.",
     ["Gelenkspaltverschmälerung", "medial"]),
    ("Knie Gonarthrose mit diktiertem K&L-Grad", "kniegelenk_in_2_ebenen",
     "Kniegelenk rechts, Röntgen, Gonarthrose medial betont, Grad 3 nach Kellgren und Lawrence. Ansonsten unauffällig.",
     ["Gonarthrose", "Grad 3 nach Kellgren"]),

    ("Ellbogen Fraktur", "ellbogengelenk_in_2_ebenen",
     "Ellbogen rechts, Röntgen, dislozierte Fraktur des Radiusköpfchens. Ansonsten unauffällig.",
     ["Fraktur", "Radiusköpfchen"]),

    ("Hand Fraktur", "hand_in_2_ebenen",
     "Hand links, Röntgen, nicht dislozierte Fraktur der Kahnbeintaille links. Ansonsten unauffällig.",
     ["Fraktur", "Kahnbein"]),

    ("Handgelenk SLAC", "handgelenk_in_2_ebenen",
     "Handgelenk rechts, Röntgen, SLAC wrist, Scapholunäre Dissoziation, Arthrose radioscaphoid. Ansonsten unauffällig.",
     ["SLAC", "Dissoziation", "Arthrose"]),

    ("Beckenübersicht Coxarthrose+Beckenschiefstand", "beckenübersicht_stehend",
     "Beckenübersicht stehend, Röntgen, Beckenschiefstand nach links um 4 mm, Beinlängendifferenz links -4 mm, Coxarthrose links. Ansonsten unauffällig.",
     ["Beckenschiefstand", "Beinlängendifferenz", "Coxarthrose"]),

    ("Sprunggelenk Arthrose", "sprunggelenk_in_2_ebenen",
     "Sprunggelenk links, Röntgen, Arthrose des oberen Sprunggelenkes, Gelenkspaltverschmälerung, subchondrale Sklerosierung, Osteophyten. Ansonsten unauffällig.",
     ["Arthrose"]),

    ("HWS Discopathiezeichen (Peter 07.09., Regression)", "halswirbelsäule_in_2_ebenen",
     "HWS: Osteochondrose C3/C4, deformierende Spondylose C2–C7, Discopathiezeichen C4–C7.",
     ["Osteochondrose", "Spondylose", "Discopathiezeichen"]),

    ("HWS Flachprofil-STT + kyphotische Fehlhaltung (Peter 07.09., Screenshot-Case)", "halswirbelsäule_in_2_ebenen",
     "HWS: flachprofile nach links, komplexe kyphotische Fehlhaltung. Osteochondrose C2 bis C4. Gelenksarthrose C3 bis C5. Hochgradige Diskopathie C4 bis C7.",
     ["flachbogig", "Fehlhaltung", "Osteochondrose", "Gelenksarthrose", "Diskopathie"]),

    ("Schädel Fraktur", "schädel_in_2_ebenen",
     "Schädel, Röntgen, undislozierte Fraktur des Os parietale links. Ansonsten unauffällig.",
     ["Fraktur", "Os parietale"]),

    ("Nasennebenhöhlen Sinusitis", "nasennebenhöhlen",
     "Nasennebenhöhlen, Röntgen, Schleimhautschwellung und Verlegung des Sinus maxillaris bds., Spiegelbildung links. Ansonsten unauffällig.",
     ["Schleimhautschwellung", "Spiegelbildung"]),
]


def _get_sa_token():
    """Bearer des TESTPROJEKTS (tools/testkosten.py) — Name bleibt für ältere Skripte."""
    return testkosten.bearer()


def call_gemini(prompt, token=None, temperature=0.0, timeout=120, system=None):
    """Seit kaiscribe-testkosten-n1 (13.11.2026): Live-Aufruf nur über tools/testkosten.py — Testprojekt
    rakscribe-test, Kostenbuch + Obergrenze je Job, Kontext-Cache für den festen Gen-Prompt. Weder Praxis-Schlüssel
    noch das alte Hermes-Dienstkonto."""
    return testkosten.gemini(prompt, system=system, temperature=temperature, timeout=timeout)


def derive_titel_harness(raw, display_name):
    """Wie derive_untersuchungs_titel in RaKScribe.py (sync!) — generische
    '(Allgemein)'-Templates bekommen den Titel aus dem Diktat."""
    if not re.search(r"\(allgemein\)", display_name or "", re.I):
        return display_name
    # v2.10.13-Sync: Negations-Guard, Loop statt break, ':'-Strip, Leak, Cap.
    t = re.sub(r"\bHW\b", "HWS", (raw or "").strip())
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[.?!]\s*$", "", t).strip()
    for _ in range(3):
        stripped = False
        for f in (r"unauff(?:ae|ä)?llig", r"o\.?\s?B\.?", r"ohne pathologischen Befund",
                  r"ohne pathologischem Befund", r"kein pathologischer Befund",
                  r"regelrecht", r"normal"):
            m = re.search(r"(?:^|[\s,])" + f + r"\s*$", t, re.I)
            if m:
                pre = t[:m.start()].strip()
                if re.search(r"\bnicht\s*$", pre, re.I):
                    continue
                t = pre.strip()
                stripped = True
        if not stripped:
            break
    t = re.sub(r"[.,?!:]+$", "", t).strip()
    t = re.sub(r"\(\s*allgemein\s*\)", "", t, flags=re.I).strip()
    if len(t) > 80:
        t = t[:80].strip()
    return t or re.sub(r"\s*\(Allgemein\)", "", display_name, flags=re.I).strip()


def build_gen_prompt(raw_text, template_body, region_name=None):
    """Gen-Prompt wie die EXE (radiology_prompt.txt + <untersuchung>) — Web nutzt dieselbe Datei."""
    p = (_pp.GEN_PROMPT.replace("{roh_text}", raw_text).replace("{template_body}", template_body)
         .replace("{region_name}", region_name or "").replace("{examples}", ""))
    return p + (f"\n<untersuchung>{region_name}</untersuchung>\n" if region_name else "")


def build_val_prompt(raw_dictation, generated_report):
    """Validator (Web Call 2) exakt aus App.tsx."""
    return _pp.val_prompt(raw_dictation, generated_report)


def check_contradictions(report, template_body):
    """Checkt ob Normalbefund-Sätze trotz Pathologie im Befund stehen geblieben sind.

    Kontextbewusst: Wörter wie "übrigen", "ansonsten", "übrige" qualifizieren
    eine Phrase als bewusste Einschränkung auf nicht-pathologische Bereiche.
    Solche qualifizierten Phrasen sind KEINE Widersprüche.
    """
    contradictions = []
    befund = report.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in report else ""
    befund_lower = befund.lower()

    # Liste von Normalbefund-Phrasen, die bei Pathologie nicht bleiben dürfen
    contradiction_checks = [
        ("Bandscheibenräume normal hoch", "Osteochondrose", ["Verschmälerung", "Intervertebralraums"]),
        ("Kein Nachweis von Discopathien", "Osteochondrose", ["Verschmälerung", "Intervertebralraums"]),
        ("Kein Nachweis von Facettengelenksarthrosen", "Facettengelenksarthrose", ["Degenerative Veränderungen", "Facetten"]),
        ("Gelenkflächen glatt und kongruent", "Arthrose", ["Gelenkspaltverschmälerung", "Sklerosierung", "Osteophyt"]),
        ("Gelenkränder unauffällig", "Arthrose", ["Osteophyt", "Sklerosierung", "Randwulst"]),
        ("Gelenksspalten normal weit", "Arthrose", ["Gelenkspaltverschmälerung", "Gelenksspaltenverschmälerung"]),
        ("Normale Form und Struktur der Gelenkkörper", "Fraktur", ["Fraktur", "Frakturlinie", "Dislokation"]),
        ("Normaler Achsenverlauf", "Skoliose", ["Skoliose", "skoliotisch"]),
        ("Normaler Achsenverlauf", "Streckhaltung", ["Streckhaltung"]),
        ("achsengerechte Stellung", "Skoliose", ["Skoliose", "skoliotisch"]),
        ("achsengerechte Stellung", "Streckhaltung", ["Streckhaltung"]),
        ("Knochenstruktur unauffällig", "Fraktur", ["Fraktur"]),
        ("Alle Wirbelkörper von normaler Form", "Fraktur", ["Fraktur"]),
    ]

    # Qualifikatoren, die eine Phrase als bewusste Einschränkung markieren
    qualifiers = ["übrigen", "übrige", "ansonsten", "anderen", "restlichen"]

    def is_qualified(phrase, text_lower):
        """Prüft ob die Phrase durch einen Qualifikator eingeschränkt ist."""
        idx = text_lower.find(phrase.lower())
        if idx == -1:
            return False
        # Schaue 60 Zeichen vor der Phrase nach Qualifikatoren
        window_before = text_lower[max(0, idx - 60):idx]
        # Und 60 Zeichen nach der Phrase (falls der Qualifikator danach kommt)
        window_after = text_lower[idx:idx + len(phrase) + 60]
        combined = window_before + " " + window_after
        return any(q in combined for q in qualifiers)

    for normal_phrase, pathology, expected_descriptors in contradiction_checks:
        if normal_phrase.lower() in befund_lower:
            # Skip wenn qualifiziert (z.B. "die übrigen Bandscheibenräume normal hoch")
            if is_qualified(normal_phrase, befund_lower):
                continue
            # Check if the pathology or its descriptors are also in the befund
            has_pathology = pathology.lower() in befund_lower or \
                           any(d.lower() in befund_lower for d in expected_descriptors)
            if has_pathology:
                contradictions.append(f"❌ '{normal_phrase}' noch im Befund trotz {pathology}")

    return contradictions


def run_test_case(name, template_key, diktat, expected_pathologies, token):
    template_body = TEMPLATES.get(template_key, {}).get("body", "")
    if not template_body:
        return {"name": name, "status": "ERROR", "issues": [f"Template '{template_key}' nicht gefunden"]}

    print(f"\n{'─'*60}")
    print(f"TEST: {name}")
    print(f"{'─'*60}")

    # Call #1: Generation
    try:
        gen_prompt = build_gen_prompt(diktat, template_body, region_name=derive_titel_harness(diktat, TEMPLATES[template_key].get("display_name", "")))
        t0 = time.time()
        report = call_gemini(gen_prompt, token, temperature=0.0, system=_pp.SYS_MSG)
        gen_time = time.time() - t0
    except Exception as e:
        return {"name": name, "status": "ERROR", "issues": [f"Gen call failed: {e}"]}

    # Call #2: Validation
    try:
        val_prompt = build_val_prompt(diktat, report)
        t0 = time.time()
        validated = call_gemini(val_prompt, token, temperature=0.0)
        val_time = time.time() - t0
    except Exception as e:
        return {"name": name, "status": "ERROR", "issues": [f"Val call failed: {e}"]}

    final = validated if validated and "## Befund" in validated else report
    final = _pp.br.nachbearbeiten(final)  # v3.2: wie Produktion (EXE + Web)
    was_corrected = validated.strip() != report.strip()

    # Checks
    issues = []
    befund = final.split("## Befund")[1].split("## Ergebnis")[0] if "## Befund" in final else ""
    ergebnis = final.split("## Ergebnis")[1] if "## Ergebnis" in final else ""

    # 1. Widerspruchs-Check
    contradictions = check_contradictions(final, template_body)
    issues.extend(contradictions)

    # 2. Vollständigkeit: jede erwartete Pathologie im Ergebnis?
    for exp in expected_pathologies:
        if exp.lower() not in ergebnis.lower():
            issues.append(f"⚠️ '{exp}' fehlt im Ergebnis")

    # 3. Diagnosen im Befundtext?
    diagnosis_words = ["Osteochondrose", "Omarthrose", "Coxarthrose", "Gonarthrose",
                       "Spondylosis deformans", "Facettengelenksarthrose", "Morbus Scheuermann"]
    for dw in diagnosis_words:
        if dw.lower() in befund.lower() and dw.lower() not in template_body.lower():
            issues.append(f"⚠️ Diagnose '{dw}' im Befundtext statt Deskriptor")

    # 4. Erfundene Begriffe? (nur wenn NICHT im Diktat genannt — "Fehlhaltung" kann diktiert sein)
    invented = [inv for inv in ["Fehlhaltung"] if inv.lower() not in diktat.lower()]
    for inv in invented:
        if inv.lower() in ergebnis.lower():
            issues.append(f"⚠️ Erfundener Begriff '{inv}' im Ergebnis")
    # 4a. v3.18.4 (RH 38): K&L-Grad bzw. Osteophyten/Sklerose/Diagnose, die nicht diktiert sind = erfunden
    if "kellgren" in final.lower() and "kellgren" not in diktat.lower() and not _pp.br.kl_adjektiv_grade(diktat):
        issues.append("❌ K&L-Grad ohne Diktat erfunden")
    for wort, muster in (("Osteophyten", r"osteophyt"), ("Sklerose", r"skleros"), ("Gonarthrose", r"gonarthros")):
        if not re.search(muster, diktat, re.I) and re.search(muster, final, re.I) \
                and not re.search(muster, template_body, re.I) and "gelenkspaltverschmälerung" in diktat.lower():
            issues.append(f"❌ {wort} nicht diktiert (erfunden)")
    # 4b. "Flachprofil" darf NIE im Report stehen (existiert radiologisch nicht)
    if "flachprofil" in final.lower():
        issues.append(f"❌ 'Flachprofil' im Befund — existiert radiologisch nicht (korrekt: flachbogige Skoliose)")

    # 5. Wurde korrigiert?
    if was_corrected:
        issues.append("📝 Call #2 hat korrigiert")

    status = "✅ PASS" if not contradictions and not any("❌" in i for i in issues) else "❌ FAIL"
    if issues and "❌" not in " ".join(issues):
        status = "⚠️ WARN"

    print(f"  Gen: {gen_time:.1f}s | Val: {val_time:.1f}s | Status: {status}")
    if issues:
        for i in issues:
            print(f"  {i}")
    else:
        print("  Keine Widersprüche gefunden ✅")

    # Print final result
    print(f"\n--- {name} FINALES ERGEBNIS ---")
    print(final[:600])

    return {"name": name, "status": status, "issues": issues, "report": final}


# ─── v3.12.0: Fälle mit CAS-Hinweis (RaKScribe-Brücke 1.1.0 reicht die CAS-Leistungen nach) ───
# Echte EXE-Kette (pipeline.befund_aus_diktat) mit ctx.cas — je Fall: erwartete Abschnitte (Titel-Wörter in Diktat-
# Reihenfolge), je Abschnitt erwartete Pathologien im Ergebnis, erwartete Hinweise. Aufruf: tools/test_all_regions.py --cas
def _cas_l(kurz, text, mod, vorlage, seite=None):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": mod, "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True}


_CAS_HWS = _cas_l("x-hws", "HWS", "Röntgen", "halswirbelsäule_in_2_ebenen")
_CAS_LWS = _cas_l("x-lws", "LWS", "Röntgen", "lendenwirbelsäule_in_2_ebenen")
_CAS_FUSSL = _cas_l("x-fuss-li", "Fuß links", "Röntgen", "fuß_in_2_ebenen", "links")
_CAS_SOSUR = _cas_l("x-sono-schulter-re", "Sonographie der Schulter re.", "Sono", "sonografie_schultergelenk", "rechts")
_CAS_USKNIE = _cas_l("x-sono-knie", "Sono Knie", "Sono", "sonografie_allgemein")
CAS_FAELLE = [
    # (name, CAS-Leistungen, Diktat, [(Titel-Wort, [Pathologien im Ergebnis])], erwartete Hinweise)
    ("gemischt: HWS Röntgen + Schulter Sono", [_CAS_HWS, _CAS_SOSUR],
     "HWS: Steilstellung, Osteochondrose C5/6 mit Unkovertebralarthrose. Schulter rechts: Bursitis subacromialis, "
     "Tendinosis calcarea der Supraspinatussehne.",
     [("Halswirbelsäule", ["Osteochondrose", "Unkovertebral"]), ("Sonographie", ["Bursitis", "Tendinosis calcarea"])], []),
    ("gemischt: Fuß links + LWS", [_CAS_FUSSL, _CAS_LWS],
     "Fuß links: Hallux valgus, Arthrose im Großzehengrundgelenk. LWS: Osteochondrose L4/5, Spondylarthrose L5/S1.",
     [("Fuß", ["Hallux valgus", "Arthrose"]), ("Lendenwirbelsäule", ["Osteochondrose", "Spondylarthrose"])], []),
    ("CAS Fuß + LWS, nur LWS diktiert (kein erfundener Fuß-Befund)", [_CAS_FUSSL, _CAS_LWS],
     "LWS: Osteochondrose L4/5, sonst unauffällig.",
     [("Lendenwirbelsäule", ["Osteochondrose"])], ["Fuß links laut CAS, nicht diktiert"]),
    ("CAS Sono Knie, Diktat nennt nur Knie (Sono statt Röntgen-Vorlage)", [_CAS_USKNIE],
     "Knie rechts: Baker-Zyste von 3 cm, kein Gelenkerguss.",
     [("Sono", ["Baker"])], []),
]


def _abschnitte(report):
    """[(Titel, Ergebnistext)] je ## Untersuchung."""
    out, titel, erg, im_erg = [], None, [], False
    for z in (report or "").splitlines():
        if z.startswith("## "):
            kopf = z[3:].strip().rstrip(":")
            if kopf.lower() == "befund":
                continue
            if kopf.lower() == "ergebnis":
                im_erg = True
                continue
            if titel is not None:
                out.append((titel, "\n".join(erg)))
            titel, erg, im_erg = kopf, [], False
        elif im_erg:
            erg.append(z)
    if titel is not None:
        out.append((titel, "\n".join(erg)))
    return out


def run_cas_fall(name, leistungen, diktat, erwartet, hinweise_soll):
    import cas_vorlagen as cv
    print(f"\n{'─'*60}\nCAS-FALL: {name}\n{'─'*60}")
    ctx = _pp.exe_kontext()
    ctx.cas = cv.CasHinweis(leistungen, TEMPLATES)
    t0 = time.time()
    erg = _pp._pipeline.befund_aus_diktat(diktat, ctx)
    issues = []
    if erg.ausnahmen:
        return {"name": name, "status": "ERROR", "issues": [f"Gemini: {erg.ausnahmen[0]}"]}
    abschnitte = _abschnitte(erg.report)
    if len(abschnitte) != len(erwartet):
        issues.append(f"❌ {len(abschnitte)} Abschnitte statt {len(erwartet)}: {[t for t, _ in abschnitte]}")
    for (titel, ergebnis), (wort, patho) in zip(abschnitte, erwartet):
        if wort.lower() not in titel.lower():
            issues.append(f"❌ Titel „{titel}“ ohne „{wort}“")
        for p in patho:
            if p.lower() not in ergebnis.lower():
                issues.append(f"⚠️ '{p}' fehlt im Ergebnis von „{titel}“")
    if erg.cas_hinweise != hinweise_soll:
        issues.append(f"❌ Hinweise {erg.cas_hinweise} statt {hinweise_soll}")
    if "cas_untersuchungen" in erg.report or "CAS" in erg.report:
        issues.append("❌ CAS-Liste ist in den Befundtext geraten")
    status = "❌ FAIL" if any("❌" in i for i in issues) else ("⚠️ WARN" if issues else "✅ PASS")
    print(f"  {time.time() - t0:.1f}s | Vorlagen {erg.vorlagen} | Hinweise {erg.cas_hinweise} | {status}")
    for i in issues:
        print(f"  {i}")
    print(erg.report[:900])
    return {"name": "CAS: " + name, "status": status, "issues": issues, "report": erg.report}


def main_cas():
    results = [run_cas_fall(*f) for f in CAS_FAELLE]
    print(f"\n{'='*70}\nCAS-FÄLLE: " + " | ".join(f"{r['status']} {r['name']}" for r in results))
    return 0 if all(r["status"] != "❌ FAIL" and r["status"] != "ERROR" for r in results) else 1


# ─── v3.13.0: Fälle mit IB-Lab-Bausteinen (Brücke 1.2.0 reicht cas_ibl_<id>.json nach) ───
# Echte EXE-Kette mit ctx.cas + ctx.ibl, live mit Gemini: die KI bekommt nur <ibl_messwerte> (Namen, keine Zahlen),
# die Werte setzt ibl_bausteine.py danach wörtlich ein. Geprüft: Abschnitte, IB-Lab-Zeilen im richtigen Abschnitt und
# 1:1 (Gate), keine eigenen Zahlen der KI zu IB-Lab-Messgrößen, keine Hinweise im Befundtext; Vorlagensätze wie
# „Fußgewölbe regulär“ (Prompt: weglassen) nur als Warnung. Texte wie ris-mods/ibl/vorbefund.py sie bildet (synthetisch).
# Aufruf: tools/test_all_regions.py --ibl
_IBL_FROG_LI = {"accno": "T-0101", "ziffer": 1, "modul": "frog", "name": "FROG", "modul_name": "IB Lab FROG",
                "version": 1, "seiten": ["links"],
                "befundteil": ["Hallux-valgus-Winkel links 18,2° (IB Lab FROG).",
                               "Calcaneusneigungswinkel links 12,4° (IB Lab FROG)."],
                "ergebnis": ["Pes planus links (Calcaneusneigungswinkel 12,4°).",
                             "Geringgradiger Hallux valgus links (Hallux-valgus-Winkel 18,2°)."],
                "hinweise": [], "nicht_zugeordnet": []}
_IBL_LAMA = {"accno": "T-0111", "ziffer": 1, "modul": "lama", "name": "LAMA", "modul_name": "IB Lab LAMA",
             "version": 1, "seiten": ["rechts", "links"],
             "befundteil": ["HKA-Winkel rechts 174,2° (IB Lab LAMA).", "HKA-Winkel links 179,1° (IB Lab LAMA).",
                            "Beinlängendifferenz 15 mm (IB Lab LAMA)."],
             "ergebnis": ["Genu varum rechts (HKA-Winkel 174,2°).", "Beinlängendifferenz von 15 mm."],
             "hinweise": ["LAMA: HKA-Konvention (< 180° = Varus) noch nicht an echtem SR bestätigt – Varus/Valgus bitte "
                          "am Bild prüfen."], "nicht_zugeordnet": []}
_IBL_HIPPO = {"accno": "T-0112", "ziffer": 2, "modul": "hippo", "name": "HIPPO", "modul_name": "IB Lab HIPPO",
              "version": 1, "seiten": ["rechts", "links"],
              "befundteil": ["LCE-Winkel nach Wiberg rechts 18° (IB Lab HIPPO).", "CCD-Winkel rechts 128° (IB Lab HIPPO).",
                             "LCE-Winkel nach Wiberg links 31° (IB Lab HIPPO).", "CCD-Winkel links 131° (IB Lab HIPPO)."],
              "ergebnis": ["Verminderte laterale Überdachung des Hüftkopfes im Sinne einer Hüftdysplasie rechts "
                           "(LCE-Winkel nach Wiberg 18°)."], "hinweise": [], "nicht_zugeordnet": []}
_IBL_KOALA_LI = {"accno": "T-0201", "ziffer": 1, "modul": "koala", "name": "KOALA", "modul_name": "IB Lab KOALA",
                 "version": 1, "seiten": ["links"], "befundteil": ["Kellgren-Lawrence-Grad links 1 (IB Lab KOALA)."],
                 "ergebnis": [], "hinweise": [], "nicht_zugeordnet": []}
# v3.18.8 (Peter 12.11.2026, Foto „Fuß beidseits in 2 Ebenen“): nur HVA + IMA I/II je Seite in den Befund
_IBL_FROG_FOTO = {"accno": "T-0121", "ziffer": 1, "modul": "frog", "name": "FROG", "modul_name": "IB Lab FROG",
                  "version": 1, "seiten": ["rechts", "links"],
                  "befundteil": ["Fuß d.p.:", "Hallux-valgus-Winkel rechts 19° (IB Lab FROG).",
                                 "Intermetatarsalwinkel I/II rechts 10° (IB Lab FROG).",
                                 "Distaler metatarsaler Gelenkflächenwinkel rechts 6° (IB Lab FROG).",
                                 "Knöcherne Fußbreite rechts 100,4 mm (IB Lab FROG).",
                                 "Hallux-valgus-Winkel links 24° (IB Lab FROG).",
                                 "Intermetatarsalwinkel I/II links 10° (IB Lab FROG).",
                                 "Knöcherne Fußbreite links 98,2 mm (IB Lab FROG).", "Fuß seitlich rechts:",
                                 "Calcaneusneigungswinkel rechts 27° (IB Lab FROG).", "Meary-Winkel rechts 12° (IB Lab FROG).",
                                 "Cuboidhöhe rechts 17,6 mm (IB Lab FROG)."],
                  "ergebnis": ["Fuß d.p.: Geringgradiger Hallux valgus rechts (Hallux-valgus-Winkel 19°).",
                               "Fuß d.p.: Mittelgradiger Hallux valgus links (Hallux-valgus-Winkel 24°).",
                               "Fuß d.p.: Vergrößerter Intermetatarsalwinkel I/II (Metatarsus primus varus) beidseits "
                               "(Intermetatarsalwinkel I/II rechts 10°, links 10°)."], "hinweise": [], "nicht_zugeordnet": []}
IBL_FAELLE = [
    ("FROG Fuß beidseits (Peters Foto 12.11.: nur pathologische Maße)",
     [_cas_l("x-fuss-bds", "Fuß beidseits", "Röntgen", "fuß_in_2_ebenen", "beidseits")], [_IBL_FROG_FOTO],
     "Fuß beidseits in 2 Ebenen: keine Fraktur, sonst unauffällig.", [("Fuß", "FROG")]),
    # (name, CAS-Leistungen, Bausteine, Diktat, [(Titel-Wort, Modul oder None)])
    # v3.18.4 (Peter 12.11.2026, RH 38): KL 1 laut IB Lab, Diktat nur Gelenkspaltverschmälerung → kein Grad 3, keine Gonarthrose
    ("KOALA Knie links KL 1 (RH 38, nur Deskriptor diktiert)",
     [_cas_l("x-knie-li", "Kniegelenk links", "Röntgen", "kniegelenk_in_2_ebenen", "links")], [_IBL_KOALA_LI],
     "Mäßige Gelenkspaltverschmälerung des medialen Kniegelenkspaltes, im Übrigen unauffällig.", [("Kniegelenk", "KOALA")]),
    # v3.18.5 (Peter 12.11.2026, Nachtrag RH 99): Becken stehend + HIPPO-Messwerte, keine Arthrose diktiert → keine Coxarthrose
    ("HIPPO Becken stehend (RH 99, Gelenkspaltverschmälerung ohne Arthrose)",
     [_cas_l("x-becken", "Becken stehend", "Röntgen", "beckenübersicht_stehend")], [_IBL_HIPPO],
     "Beckenübersicht stehend. Geringe Gelenkspaltverschmälerung beider Hüftgelenke, kein Beckenschiefstand, im Übrigen unauffällig.",
     [("Becken", "HIPPO")]),
    ("FROG Fuß links (Hallux valgus diktiert, Pes planus von IB Lab)",
     [_cas_l("x-fuss-li", "Fuß links", "Röntgen", "fuß_in_2_ebenen", "links")], [_IBL_FROG_LI],
     "Fuß links: Hallux valgus mit Arthrose im Großzehengrundgelenk, sonst unauffällig.", [("Fuß", "FROG")]),
    ("LAMA Ganzbein + HIPPO Becken (zwei Leistungen, zwei Module)",
     [_cas_l("x-ganzbein", "Ganzbeinaufnahme", "Röntgen", "ganzbeinaufnahme_im_stand"),
      _cas_l("x-becken", "Becken", "Röntgen", "beckenübersicht_stehend")], [_IBL_LAMA, _IBL_HIPPO],
     "Ganzbeinaufnahme im Stand: varische Beinachse rechts, sonst unauffällig. Becken: beginnende Coxarthrose rechts.",
     [("Ganzbein", "LAMA"), ("Becken", "HIPPO")]),
]


def run_ibl_fall(name, leistungen, bausteine, diktat, erwartet):
    import cas_vorlagen as cv
    import ibl_bausteine as ib
    print(f"\n{'─'*60}\nIB-LAB-FALL: {name}\n{'─'*60}")
    ctx = _pp.exe_kontext()
    ctx.cas = cv.CasHinweis(leistungen, TEMPLATES)
    bs = ib.aus_liste(bausteine)
    ctx.ibl = ib.IblKontext(bs, cas_leistungen=leistungen)
    t0 = time.time()
    erg = _pp._pipeline.befund_aus_diktat(diktat, ctx)
    if erg.ausnahmen:
        return {"name": "IB Lab: " + name, "status": "ERROR", "issues": [f"Gemini: {erg.ausnahmen[0]}"]}
    issues, e = [], erg.ibl
    teile = [t for t in erg.report.split("\n\n\n") if t.strip()]
    if len(teile) != len(erwartet):
        issues.append(f"❌ {len(teile)} Abschnitte statt {len(erwartet)}")
    for teil, (wort, modul) in zip(teile, erwartet):
        titel = teil.split("\n", 1)[0]
        if wort.lower() not in titel.lower():
            issues.append(f"❌ Titel „{titel}“ ohne „{wort}“")
        for b in bs:
            drin = f"(IB Lab {b.name})" in teil
            soll = b.name == modul and bool(ib.befund_zeilen(b))   # v3.18.8: FROG/HIPPO/KOALA nur Zeilen mit Treffer
            for z in (b.befundteil if b.name == modul else []):
                if z not in ib.befund_zeilen(b) and z in teil:
                    issues.append(f"❌ unauffälliger Wert im Befund: {z}")
            if soll != drin:
                issues.append(f"❌ {b.name}-Zeilen {'fehlen in' if soll else 'stehen in'} „{titel}“")
    if e is None or ib.gate(erg.report, e.zeilen):
        issues.append(f"❌ Gate: {ib.gate(erg.report, e.zeilen) if e else 'nichts eingesetzt'}")
    ohne = erg.report
    for z in (e.zeilen if e else []):
        ohne = ohne.replace(z, "")
    for b in bs:                                  # eigene Zahlen der KI zu IB-Lab-Messgrößen?
        for m in filter(None, map(ib.messwert, b.befundteil)):
            art, gef = ib.im_text(m, ohne)
            if art in ("gleich", "anders"):
                issues.append(f"❌ KI nennt selbst {m.name} ({gef})")
    erlaubt = (set(_pp.br.kl_grade(diktat)) or {g for b in bs for z in b.befundteil for g in _pp.br.kl_grade(z)}
               or set(_pp.br.kl_adjektiv_grade(diktat)))   # v3.18.5: Grad zum Adjektiv einer diktierten Arthrose
    if set(_pp.br.kl_grade(ohne)) - erlaubt or ("gonarthrose" in erg.report.lower() and "arthrose" not in diktat.lower()
                                                and any(b.modul == "koala" and not b.ergebnis for b in bs)) \
            or _pp.br.arthrose_bereinigen(erg.report, diktat)[1]:   # v3.18.5 RH 99: Arthrose ohne Diktat
        issues.append(f"❌ K&L-Grad/Diagnose ohne Diktat oder IB Lab: {_pp.br.kl_grade(ohne)}")
    if any(w in erg.report for w in ("bitte prüfen", "ibl_messwerte", "HKA-Konvention", "nicht doppelt", "IB-Lab-Wert")):
        issues.append("❌ Hinweise/Prompt-Text sind in den Befund geraten")
    for h in (e.hinweise if e else []):
        if "widerspricht IB Lab" in h:
            issues.append(f"⚠️ {h}")
    status = "❌ FAIL" if any("❌" in i for i in issues) else ("⚠️ WARN" if issues else "✅ PASS")
    print(f"  {time.time() - t0:.1f}s | Zuordnung {e.zuordnung if e else {}} | Hinweise {e.hinweise if e else []} | {status}")
    for i in issues:
        print(f"  {i}")
    print(erg.report)
    return {"name": "IB Lab: " + name, "status": status, "issues": issues, "report": erg.report,
            "hinweise": e.hinweise if e else []}


def main_ibl():
    results = [run_ibl_fall(*f) for f in IBL_FAELLE]
    print(f"\n{'='*70}\nIB-LAB-FÄLLE: " + " | ".join(f"{r['status']} {r['name']}" for r in results))
    return 0 if all(r["status"] not in ("❌ FAIL", "ERROR") for r in results) else 1


def main():
    if "--cas" in sys.argv:
        sys.exit(main_cas())
    if "--ibl" in sys.argv:
        sys.exit(main_ibl())
    print("=" * 70)
    print("VOLLSTÄNDIGER WIDERSPRUCHSTEST — Alle Regionen")
    print("=" * 70)

    results = []

    for name, tkey, diktat, expected in TEST_CASES:
        r = run_test_case(name, tkey, diktat, expected, None)
        results.append(r)
        time.sleep(1)  # Rate limit

    # Summary
    print(f"\n{'='*70}")
    print("ZUSAMMENFASSUNG")
    print(f"{'='*70}")
    passes = sum(1 for r in results if r["status"] == "✅ PASS")
    warns = sum(1 for r in results if r["status"] == "⚠️ WARN")
    fails = sum(1 for r in results if r["status"] == "❌ FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print(f"\n✅ PASS: {passes} | ⚠️ WARN: {warns} | ❌ FAIL: {fails} | ERROR: {errors}")
    print(f"Total: {len(results)}")

    print(f"\n{'─'*70}")
    for r in results:
        icon = {"✅ PASS": "✅", "⚠️ WARN": "⚠️", "❌ FAIL": "❌", "ERROR": "💥"}.get(r["status"], "?")
        print(f"{icon} {r['name']}")
        for issue in r.get("issues", []):
            print(f"    {issue}")


if __name__ == "__main__":
    main()