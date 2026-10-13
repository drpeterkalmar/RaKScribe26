#!/usr/bin/env python3
"""tools/cas_bitgleich.py — v3.12.0: Einzelbefunde OHNE CAS-Hinweis sind bit-gleich mit einem früheren Stand.

Lädt source_code/pipeline.py aus einer Git-Revision (Standard: ae97251 = letzter Stand vor v3.12.0, sonst --rev) als
eigenes Modul und vergleicht für alle Diktate aus detect_fixtures.json, normal_bypass_tests.json, befund_regeln_fixtures.json
(split) und tools/test_all_regions.py: Segmente, Gen-Prompts (Attrappe statt Gemini, die jeden Prompt mitschreibt) und
Normalbefund-Berichte. Ohne Netz, ohne Gemini.   Aufruf: /usr/bin/python3 tools/cas_bitgleich.py [--rev <git-rev>]
"""
import importlib.util, json, pathlib, subprocess, sys, tempfile, types

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source_code"))
sys.path.insert(0, str(ROOT / "tools"))
import pipeline as neu  # noqa: E402


def alte_pipeline(rev):
    code = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:source_code/pipeline.py"], capture_output=True,
                          text=True, check=True).stdout
    pfad = pathlib.Path(tempfile.mkdtemp()) / "pipeline_alt.py"
    pfad.write_text(code, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("pipeline_alt", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def diktate():
    out = [f[0] for f in json.loads((ROOT / "detect_fixtures.json").read_text(encoding="utf-8"))["faelle"]]
    out += [c["in"] for c in json.loads((ROOT / "normal_bypass_tests.json").read_text(encoding="utf-8"))["cases"]]
    out += [c["in"] for c in json.loads((ROOT / "befund_regeln_fixtures.json").read_text(encoding="utf-8"))["split"]]
    out += [c["in"] for c in json.loads((ROOT / "misheard_tests.json").read_text(encoding="utf-8"))["cases"]]
    try:
        import test_all_regions as h
        out += [c[2] for c in h.TEST_CASES] + [c[2] for c in h.CAS_FAELLE]
    except Exception:
        pass
    return list(dict.fromkeys(out))


def lauf(modul, diktat, templates, display, prompt):
    prompts = []

    def llm(p):
        prompts.append(p)
        t = p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0]
        return f"## {t}\n\n## Befund\nBeschreibung laut Diktat, ausreichend lang für den Vergleich.\n\n## Ergebnis\nBefund."
    ctx = modul.Kontext(templates=templates, display_names=display, prompt=prompt, llm=llm, log=lambda *a: None)
    erg = modul.befund_aus_diktat(diktat, ctx)
    return erg.segmente, prompts, erg.report


def main():
    rev = sys.argv[sys.argv.index("--rev") + 1] if "--rev" in sys.argv else "ae97251"  # letzter Stand vor v3.12.0
    alt = alte_pipeline(rev)
    templates = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
    display = [v.get("display_name", "") for v in templates.values()]
    prompt = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
    alle = diktate()
    abweichend = []
    for d in alle:
        if lauf(alt, d, templates, display, prompt) != lauf(neu, d, templates, display, prompt):
            abweichend.append(d)
    print(f"Vergleich mit {rev}: {len(alle)} Diktate, {len(alle) - len(abweichend)} bit-gleich "
          f"(Segmente, Gen-Prompts, Berichte), {len(abweichend)} abweichend")
    for d in abweichend[:10]:
        print("  ABWEICHEND:", d[:100])
    return 1 if abweichend else 0


if __name__ == "__main__":
    sys.exit(main())
