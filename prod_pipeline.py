"""prod_pipeline.py — baut die ECHTEN Produktionsketten von EXE und Web für Harness/verify_* nach (v3.2).

Keine Prompt-Kopien: Gen-Prompt = radiology_prompt.txt (eine Quelle für EXE + Web), systemInstruction =
SYS_MSG aus source_code/gemini.py, Validator (Web Call 2) und Call 0 aus App.tsx, Regionen-Trenner/Nummerierung/
Normalbefund-Bypass = source_code/befund_regeln.py, Template-Erkennung = source_code/detect.py (direkt importiert).

    import prod_pipeline as pp
    pp.exe_kette(diktat)          # EXE: misheard → split → je Region detect → Bypass | Gen (+SYS_MSG) → nummerieren
    pp.web_kette(diktat)          # Web: Call 0 → split → je Region detect → Bypass | Gen → Call 2 → nummerieren
    pp.gen_prompt(raw, key)       # Gen-Prompt wie EXE (für Harness-Einzelcalls)

Live-Calls laufen über test_all_regions.call_gemini (AQ-Key → SA-Bearer-Fallback + 429-Backoff).
"""
import json, os, pathlib, re, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "source_code"))
import misheard  # noqa: E402
import befund_regeln as br  # noqa: E402
import normalbypass as nb  # noqa: E402
import detect as _detect  # noqa: E402  (Umbau Schritt 12: kein AST-Extrakt mehr)
import gemini as _gemini  # noqa: E402  (Umbau Schritt 14)

TEMPLATES = json.loads((ROOT / "templates.json").read_text())
DISPLAY_NAMES = [v["display_name"] for v in TEMPLATES.values()]
_MH = misheard.load(str(ROOT))
_MH_COMPILED = misheard.compile_rules(_MH)
MISHEARD_HINTS = misheard.prompt_block(_MH)

_APP_SRC = (ROOT / "web_app" / "src" / "App.tsx").read_text()


def detect_template(raw):
    return _detect.detect_template(raw, TEMPLATES)


derive_untersuchungs_titel = _detect.derive_untersuchungs_titel

SYS_MSG = _gemini.SYS_MSG

GEN_PROMPT_RAW = (ROOT / "radiology_prompt.txt").read_text()
PROMPT_VERSION = br.prompt_version(GEN_PROMPT_RAW)
GEN_PROMPT = br.strip_prompt_marker(GEN_PROMPT_RAW)

_mv = re.search(r"const validationPrompt = `(.*?)`;", _APP_SRC, re.S)
VAL_TEMPLATE = _mv.group(1).replace("\\`", "`").replace('\\"', '"')


def gen_prompt(raw, template_key=None, examples="", prompt=None, hints=True, template=None):
    """Gen-Prompt exakt wie RaKScribe.py _befund_fuer_segment (Web identisch bis auf die llm-Hinweise)."""
    t = template or TEMPLATES.get(template_key or detect_template(raw), TEMPLATES.get("allgemein"))
    p = br.strip_prompt_marker(prompt if prompt is not None else GEN_PROMPT_RAW)
    p = (p.replace("{roh_text}", raw).replace("{template_body}", t["body"])
          .replace("{region_name}", t["display_name"]))
    p = p + "\n<untersuchung>" + t["display_name"] + "</untersuchung>\n"
    p = p + "<normal_ergebnis>" + (t.get("ergebnis") or "Unauffälliger Befund.") + "</normal_ergebnis>\n"
    if hints and MISHEARD_HINTS:
        p = p + MISHEARD_HINTS + "\n"
    return p.replace("{examples}", examples) if "{examples}" in p else p + "\n\n" + examples


def val_prompt(diktat, report):
    return VAL_TEMPLATE.replace("${rawDictation}", diktat).replace("${generatedReport}", report)


def bypass_report(raw, key):
    t = TEMPLATES[key]
    lines = t["body"].split("\n")
    titel = br.titel_mit_seite(derive_untersuchungs_titel(raw, lines[0].strip().rstrip(":")), raw)
    erg = br.ergebnis_mit_seite(t.get("ergebnis", ""), raw)
    return f"## {titel}\n\n## Befund\n" + "\n".join(lines[1:]) + f"\n\n## Ergebnis\n{erg}"


def _call(prompt, system=None):
    import test_all_regions as h
    return h.call_gemini(prompt, system=system)


def _clean(txt):
    txt = re.sub(r"^```[a-zA-Z]*\s*\n?", "", txt or "")
    return re.sub(r"\n?```\s*$", "", txt).strip()


def exe_segment(seg, examples="", prompt=None, log=None):
    key = detect_template(seg)
    if nb.is_pure_normal_finding(seg, DISPLAY_NAMES) and key != "allgemein":
        rep = bypass_report(seg, key)
    else:
        rep = _clean(_call(gen_prompt(seg, key, examples=examples, prompt=prompt), system=SYS_MSG))
    if log is not None:
        log.append({"segment": seg, "template": key, "roh": rep})
    return br.nachbearbeiten(rep)


def exe_kette(diktat, examples="", prompt=None, log=None):
    raw = misheard.apply(diktat.strip(), _MH_COMPILED)
    segs = br.split_regionen(raw)
    with ThreadPoolExecutor(max_workers=len(segs)) as ex:
        teile = list(ex.map(lambda s: exe_segment(s, examples, prompt, log), segs))
    return br.befunde_zusammenfuegen(teile)


def web_segment(seg, log=None):
    key = detect_template(seg)
    if nb.is_pure_normal_finding(seg, DISPLAY_NAMES) and key != "allgemein":
        rep = bypass_report(seg, key)
        c1 = rep
    else:
        # Web: Gen-Prompt ohne <stt_hinweise> (die stehen in Call 0), gleiches SYS_MSG
        c1 = _clean(_call(gen_prompt(seg, key, hints=False), system=SYS_MSG))
        c2 = _clean(_call(val_prompt(seg, c1)))
        bef_in = len(c1.split("## Ergebnis")[0])
        bef_out = len(c2.split("## Ergebnis")[0])
        ok = "## Ergebnis" in c2 and len(c2.split("## Ergebnis")[1].strip()) > 5
        rep = c2 if ok and not (bef_in > 0 and bef_out < bef_in * 0.7) else c1
    if log is not None:
        log.append({"segment": seg, "template": key, "call1": c1, "roh": rep})
    return br.nachbearbeiten(rep)


def web_kette(diktat, log=None):
    from call0_prompt import build_call0_prompt, apply_auto
    raw = apply_auto(diktat.strip())
    korr = _clean(_call(build_call0_prompt(diktat.strip())))
    if not korr or len(korr) < len(raw) * 0.6:
        korr = raw
    if log is not None:
        log.append({"call0": korr})
    segs = br.split_regionen(korr)
    with ThreadPoolExecutor(max_workers=len(segs)) as ex:
        teile = list(ex.map(lambda s: web_segment(s, log), segs))
    return br.befunde_zusammenfuegen(teile)
