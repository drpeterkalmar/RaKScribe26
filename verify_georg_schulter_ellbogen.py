#!/usr/bin/env python3
"""verify_georg_schulter_ellbogen.py — v3.2-Regression: Georgs Referenzfall (Telegram-Gruppe 05.10.2026).

Diktat (chirp_3 roh): Schulter rechts (mäßiggradige Omarthrose, mäßiggradige Tendinosis calcarea mit 17 mm
Kalkdepot) + Ellbogen rechts (geringgradige Arthrose, kortikale Unregelmäßigkeiten Extensorensehnenplatte
als Hinweis für Tendinose). Soll = Hermes-Telegram-Befund ("korrekt und sehr gut").

Kette A = EXE (misheard → Regionen-Trenner → je Region detect_template → radiology_prompt.txt + SYS_MSG →
          Ergebnis-Nummerierung), Kette B = Web (Call 0 → Trenner → Gen → Call 2 Validator → Nummerierung).
Beide über prod_pipeline.py = echte Produktions-Prompts/-Funktionen. Je Kette 3 Läufe (Nichtdeterminismus).
Zusatzfälle (Kette A): alte radiology_prompt_v4.txt neben der EXE (versionierte Prompt-Wahl muss sie
ignorieren) und alte unnummerierte Praxisbefunde als Few-Shot-Beispiele (dürfen das Format nicht kippen).

  /usr/bin/python3 verify_georg_schulter_ellbogen.py          # Gate (3× A, 3× B, 2 Zusatzfälle)
  /usr/bin/python3 verify_georg_schulter_ellbogen.py --ab     # zusätzlich A/B Few-Shots an/aus (je 3×)
"""
import json, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))
import prod_pipeline as pp  # noqa: E402

RUNS = 3
DIKTAT = ("Schulter rechts Punkt neue Zeile mäßig gradige Ommatrose Punkt mäßig gradige Tenenosis kakaria mit 17 mm "
          "Messing am Kack Depot Punkt neue Zeile Ellbogen rechts Punkt neue Zeile geringgradige "
          "Ellbogengelenksarthrose Punkt neue Zeile kortikale Unregelmäßigkeiten im Bereich der "
          "Extensorensehnenplatte rechts das ist indirekter Hinweis für Tendenose der Extensorensehnen Punkt")

# Alte Praxisbefunde im Stil der practice_reports.db (unnummeriert, "Beurteilung", anderer Standardtext)
ALTE_BEISPIELE = """
### BEISPIELE FÜR TYPISCHE BERICHTE DIESER PRAXIS:

Beispiel 1:
Schulter rechts: Gelenkkörper normal geformt. Omarthrose. Kalkdepot in der Supraspinatussehne. Weichteile frei.
Beurteilung: Omarthrose rechts. Tendinosis calcarea rechts.
---

Beispiel 2:
Ellbogen rechts. Knochenstruktur: unauffällig. Gelenkflächen: arthrotisch. Weichteile: frei.
Beurteilung: Ellbogenarthrose rechts. Epicondylitis.
---
"""


def abschnitte(report):
    """[(titel, befund, ergebnis)] je Block."""
    out = []
    for blk in re.split(r"\n(?=## (?!Befund|Ergebnis))", "\n" + report.strip()):
        blk = blk.strip()
        if not blk.startswith("## "):
            continue
        titel = blk.split("\n", 1)[0][3:].strip()
        bef = blk.split("## Befund", 1)[1].split("## Ergebnis")[0].strip() if "## Befund" in blk else ""
        erg = blk.split("## Ergebnis", 1)[1].strip() if "## Ergebnis" in blk else ""
        out.append((titel, bef, erg))
    return out


def checks(report):
    bl = abschnitte(report)
    sch = next((b for b in bl if b[0].lower().startswith("schulter")), None)
    ell = next((b for b in bl if b[0].lower().startswith("ellbogen")), None)
    c = []
    c.append(("2 Regionen-Blöcke", len(bl) == 2, [b[0] for b in bl]))
    c.append(("Überschrift 'Schultergelenk rechts in 2 Ebenen'", bool(sch) and sch[0] == "Schultergelenk rechts in 2 Ebenen", sch and sch[0]))
    c.append(("Überschrift 'Ellbogengelenk rechts in 2 Ebenen'", bool(ell) and ell[0] == "Ellbogengelenk rechts in 2 Ebenen", ell and ell[0]))
    for name, b in (("Schulter", sch), ("Ellbogen", ell)):
        erg_lines = [l for l in (b[2] if b else "").split("\n") if l.strip()]
        c.append((f"{name}: Ergebnis nummeriert (1. 2.)", len(erg_lines) >= 2 and all(l.startswith(f"{i+1}. ") for i, l in enumerate(erg_lines)), erg_lines))
        c.append((f"{name}: keine 'Label:'-Präfixe/Fettschrift im Befund",
                  bool(b) and not re.search(r"^\s*(\*\*)?(Skelett|Knochenstruktur|Gelenkflächen|Weichteile)(\*\*)?:", b[1], re.M | re.I) and "**" not in b[1],
                  b and b[1][:120]))
    se = sch[2].lower() if sch else ""
    ee = ell[2].lower() if ell else ""
    sb = sch[1] if sch else ""
    eb = ell[1] if ell else ""
    c.append(("Schulter-Ergebnis: 'Mäßiggradige Tendinosis calcarea' + '17 mm'", "mäßiggradige tendinosis calcarea" in se and "17 mm" in se, se))
    c.append(("Schulter-Ergebnis: Omarthrose K&L Grad 3", "omarthrose" in se and re.search(r"grad 3 nach kellgren", se) is not None, se))
    c.append(("Ellbogen-Ergebnis: Arthrose K&L Grad 2", "arthrose" in ee and re.search(r"grad 2 nach kellgren", ee) is not None, ee))
    c.append(("Ellbogen-Ergebnis: 'Extensorensehnen'", "extensorensehnen" in ee, ee))
    # Standardtext = Template (Georg: "nimmt einen anderen Standardtext")
    c.append(("Schulter-Befund: Template-Sätze erhalten", all(x in sb for x in (
        "Humeruskopf in regelrechter Artikulation", "AC-Gelenk altersentsprechend, keine Luxation",
        "Unauffällige Darstellung der übrigen angrenzenden Skelettanteile")), sb[:200]))
    c.append(("Schulter-Befund: 'Keine Kalzifikationen' ersetzt", "Keine Kalzifikationen" not in sb and "17 mm" in sb, sb[-200:]))
    c.append(("Ellbogen-Befund: Template-Sätze erhalten", "Mineralgehalt und Knochenstruktur regelrecht" in eb and "Weichteilmantel" in eb, eb[:200]))
    return c


def lauf(label, fn):
    t0 = time.time()
    log = []
    try:
        rep = fn(log)
    except Exception as e:  # Netzfehler = roter Lauf, nicht Abbruch der Suite
        rep = f"FEHLER: {e}"
    cs = checks(rep)
    ok = all(x[1] for x in cs)
    print(f"\n{'✅' if ok else '❌'} {label} ({time.time() - t0:.1f} s)")
    for name, good, det in cs:
        if not good:
            print(f"   ❌ {name}: {str(det)[:300]}")
    return ok, rep, log


def main():
    ab = "--ab" in sys.argv
    print(f"Prompt {pp.PROMPT_VERSION} · Referenzfall Georg 05.10.2026")
    results, reports = {}, {}
    for i in range(RUNS):
        results[f"A{i+1}"], reports[f"A{i+1}"], _ = lauf(f"Kette A (EXE) Lauf {i+1}", lambda log: pp.exe_kette(DIKTAT, log=log))
    for i in range(RUNS):
        results[f"B{i+1}"], reports[f"B{i+1}"], _ = lauf(f"Kette B (Web) Lauf {i+1}", lambda log: pp.web_kette(DIKTAT, log=log))

    # Zusatz 1: alte radiology_prompt_v4.txt (Stand vor v3.2, ohne Marker) neben der EXE
    alt = subprocess.run(["git", "show", "04bb66f:radiology_prompt.txt"], cwd=ROOT, capture_output=True, text=True).stdout
    text, quelle, hinweis = pp.br.waehle_prompt(pp.GEN_PROMPT_RAW, [("radiology_prompt_v4.txt", alt), ("radiology_prompt.txt", "")])
    print(f"\nPrompt-Wahl mit alter v4-Datei: Quelle={quelle} · Hinweis: {hinweis}")
    results["V4"], reports["V4"], _ = lauf("Kette A mit alter radiology_prompt_v4.txt",
                                           lambda log: pp.exe_kette(DIKTAT, prompt=text, log=log))
    results["V4"] = results["V4"] and quelle == "eingebaut"
    # Zusatz 2: alte unnummerierte Praxisbefunde als Few-Shots
    results["FS"], reports["FS"], _ = lauf("Kette A mit alten unnummerierten Few-Shot-Beispielen",
                                           lambda log: pp.exe_kette(DIKTAT, examples=ALTE_BEISPIELE, log=log))

    ab_out = {}
    if ab:
        # A/B Few-Shots: Was macht das LLM SELBST (vor der deterministischen Nummerierung)?
        for arm, ex in (("ohne", ""), ("mit", ALTE_BEISPIELE)):
            rows = []
            for i in range(RUNS):
                log = []
                rep = pp.exe_kette(DIKTAT, examples=ex, log=log)
                roh = "\n\n".join(x["roh"] for x in log)
                roh_num = all(re.search(r"## Ergebnis\s*\n\s*1\. ", x["roh"]) for x in log)
                beurteilung = "beurteilung" in roh.lower()
                label = bool(re.search(r"^\s*(\*\*)?(Knochenstruktur|Gelenkflächen|Weichteile)(\*\*)?:", roh, re.M))
                cs = checks(rep)
                rows.append({"llm_nummeriert": roh_num, "beurteilung": beurteilung, "labels": label,
                             "checks_ok": sum(1 for x in cs if x[1]), "checks": len(cs)})
            ab_out[arm] = rows
            print(f"\nA/B Few-Shots {arm}: " + " | ".join(
                f"LLM-nummeriert={r['llm_nummeriert']} Beurteilung={r['beurteilung']} Labels={r['labels']} Checks {r['checks_ok']}/{r['checks']}"
                for r in rows))

    (ROOT / "verify_georg_results.json").write_text(json.dumps(
        {"prompt_version": pp.PROMPT_VERSION, "results": results, "reports": reports, "ab_fewshots": ab_out},
        ensure_ascii=False, indent=1))
    print("\n" + "=" * 60)
    for k, v in results.items():
        print(f"{'✅' if v else '❌'} {k}")
    print(f"\nBeispiel-Ausgabe Kette A Lauf 1:\n{reports['A1']}")
    gate = all(results.values())
    print(f"\n{'✅ GATE GRÜN' if gate else '❌ GATE ROT'} — {sum(results.values())}/{len(results)}")
    sys.exit(0 if gate else 1)


if __name__ == "__main__":
    main()
