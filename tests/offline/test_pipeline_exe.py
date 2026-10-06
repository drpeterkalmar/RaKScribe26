"""Gate (Umbau Schritt 15): Befund-Kette der EXE ohne Oberfläche (pipeline.befund_aus_diktat) — Bypass-Fälle
liefern denselben Report wie prod_pipeline.bypass_report, der Gen-Prompt ist zeichengleich zum bisherigen Aufbau
(v3.2.3), Fehlhör-Liste vor der Erkennung, Mehr-Regionen, leeres Diktat. LLM nachgebaut, kein Netz.
Aufruf: /usr/bin/python3 tests/offline/test_pipeline_exe.py"""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import pipeline as pl  # noqa: E402
import prod_pipeline as pp  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


def alter_gen_prompt(raw, t):
    """Referenz: Gen-Prompt-Aufbau wie in RaKScribe.py v3.2.3 (_befund_fuer_segment), wörtlich nachgebaut."""
    p_full = br.strip_prompt_marker(pp.GEN_PROMPT_RAW)
    p_full = p_full.replace('{roh_text}', raw).replace('{template_body}', t['body']).replace('{region_name}', t['display_name'])
    p_full = p_full + "\n<untersuchung>" + t['display_name'] + "</untersuchung>\n"
    p_full = p_full + "<normal_ergebnis>" + (t.get('ergebnis') or "Unauffälliger Befund.") + "</normal_ergebnis>\n"
    if pp.MISHEARD_HINTS:
        p_full = p_full + pp.MISHEARD_HINTS + "\n"
    return p_full.replace("{examples}", "") if "{examples}" in p_full else p_full + "\n\n" + ""


aufrufe = []
LLM_ANTWORT = "## Untersuchung\n\n## Befund\nBeschreibung der Veränderung mit ausreichend Text.\n\n## Ergebnis\nGonarthrose rechts."


def llm(prompt):
    aufrufe.append(prompt)
    return LLM_ANTWORT


def ctx(protokoll=None):
    return pp.exe_kontext(log=protokoll, llm=llm)


cases = json.loads((ROOT / "normal_bypass_tests.json").read_text(encoding="utf-8"))["cases"]
bypass_ok = llm_ok = 0
for c in cases:
    aufrufe.clear()
    erg = pl.befund_aus_diktat(c["in"], ctx())
    raw = pp.misheard.apply(c["in"].strip(), pp._MH_COMPILED)
    segs = br.split_regionen(raw)
    if len(segs) != 1 or not raw:
        continue
    key = pp.detect_template(raw)
    if c["bypass"] and key != "allgemein":
        soll = br.nachbearbeiten(pp.bypass_report(raw, key))
        ok = erg.report == soll and not aufrufe
        bypass_ok += ok
        check(f"Bypass = prod_pipeline.bypass_report: {c['in'][:50]!r}", ok, f"\n{erg.report[:200]}\n--- soll ---\n{soll[:200]}")
    else:
        ok = len(aufrufe) == 1 and aufrufe[0] == alter_gen_prompt(raw, pp.TEMPLATES.get(key) or pp.TEMPLATES["allgemein"]) \
            and erg.report == br.nachbearbeiten(LLM_ANTWORT)
        llm_ok += ok
        check(f"LLM-Pfad, Gen-Prompt zeichengleich: {c['in'][:50]!r}", ok)
check(f"Bypass-Fälle geprüft ({bypass_ok}) und LLM-Fälle geprüft ({llm_ok})", bypass_ok >= 10 and llm_ok >= 5)

erg = pl.befund_aus_diktat("   ", ctx())
check("leeres Diktat → leer, kein LLM", erg.leer and not erg.report)
aufrufe.clear()
prot = []
erg = pl.befund_aus_diktat("Schulter rechts Punkt Omarthrose Punkt Ellbogen rechts unauffällig", ctx(prot))
check("Mehr-Regionen: Schulter (LLM) + Ellbogen (Bypass), zusammengefügt",
      len(erg.segmente) == 2 and len(aufrufe) == 1 and erg.vollstaendig and erg.report.count("## Ergebnis") == 2
      and "Ellbogengelenk rechts in 2 Ebenen" in erg.report, erg.report[:300])
check("Protokoll je Segment (Mess-Harness)", [p["template"] for p in prot] == ["schultergelenk_in_2_ebenen", "ellbogengelenk_in_2_ebenen"],
      str([p["template"] for p in prot]))
gestartet = []
pl.befund_aus_diktat("Knie rechts unauffällig", ctx(), beim_start=lambda: gestartet.append(1))
check("beim_start wird vor der Erzeugung gerufen", gestartet == [1])


def llm_kaputt(p):
    raise RuntimeError("HTTP 401 Unauthorized")


k = pp.exe_kontext(llm=llm_kaputt)
try:
    pl.befund_aus_diktat("Knie rechts mäßiggradige Gonarthrose", k)
    check("Ein-Regionen-Diktat: LLM-Fehler wird geworfen (Dialog in der EXE)", False)
except RuntimeError as e:
    check("Ein-Regionen-Diktat: LLM-Fehler wird geworfen (Dialog in der EXE)", "401" in str(e))
erg = pl.befund_aus_diktat("Schulter rechts Punkt Omarthrose Punkt Ellbogen rechts unauffällig", k)
check("Mehr-Regionen: LLM-Fehler → Region benannt, Ellbogen-Bypass bleibt, nicht vollständig",
      erg.fehler == ["Schulter rechts"] and "## Ellbogengelenk" in erg.report and not erg.vollstaendig, str(erg.fehler))

print("\n" + ("✅ PIPELINE EXE PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
