"""Gate (kaiscribe-haiku-ab-n1): Web-Maske web_app/src/kiMaske.ts = source_code/ki_maske.py (KaiFormat-Maske).
Gleiche Platzhalter, gleiche Originalwerte, gleiches Ergebnis der Restprüfung — für Musterfälle, alle Vorlagen und die
Harness-Diktate. Aufruf: python3 tests/offline/test_ki_maske_web.py (braucht node ≥ 22)"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import ki_maske  # noqa: E402

FAELLE = [
    ("Vergleich mit der Voruntersuchung vom 12.03.2025, 12.3.25, 12.3., 2026-03-12, 03/2026, März 2026, im Mai.", []),
    ("Zuweisung Dr. med. Huber, Kopie an OA Dr. Müller-Lüdenscheidt und Frau Mag. Anna Gruber.", []),
    ("SVNR 1234 120380, Pat.-Nr. 4711, RH 89, Tel. 0316 / 385-12058, +43 664 1234567, Zl. 12/3.", []),
    ("Ordination Hauptstraße 12/3, 8010 Graz, Mail praxis@kai.at, www.kai.at.", []),
    ("Kniegelenk rechts, Patient Gruber Anna, geb. 03.04.1961, mäßiggradige Gonarthrose.", ["Gruber Anna"]),
    ("Herr Fischer-Öztürk kommt zur Kontrolle 2027, Diskopathie L4/5, 18 mm, Cobb 12,5°, Grad 2.", ["Fischer-Öztürk"]),
    ("Kein Datum: C5/C6, Th7 bis Th9, 1,8 cm, BI-RADS 2, Kellgren & Lawrence 3, 15 mm².", []),
    ("Leitlinie 2018 und Studie 1957, Nummer 12345678 und 0664 12 34 56.", []),
    ("Prim. Univ.-Prof. Dr. von Weber und Frau Doktor bitte Rücksprache.", []),
]


def main():
    node = shutil.which("node")
    if not node:
        print("ℹ️  node fehlt — Web-Maske nicht geprüft")
        return 0
    tpl = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
    faelle = FAELLE + [(v.get("body") or "", []) for v in tpl.values()]
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import importlib
        src = (ROOT / "tools" / "test_all_regions.py").read_text(encoding="utf-8")
        start = src.index("TEST_CASES = [")
        ende = src.index("\n]\n", start) + 3
        ns = {}
        exec(src[start:ende], ns)   # nur die Fallliste, ohne testkosten/Netz
        faelle += [(c[2], []) for c in ns["TEST_CASES"]]
        del importlib
    except Exception as e:  # noqa: BLE001
        print("ℹ️  Harness-Diktate nicht lesbar:", e)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(faelle, f, ensure_ascii=False)
    r = subprocess.run([node, "--experimental-strip-types", "--no-warnings", "ki_maske_test.mjs", f.name],
                       cwd=ROOT / "web_app", capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print("❌ node:", r.stderr[-800:])
        return 1
    web = json.loads(r.stdout)
    fails = 0
    for (text, namen), w in zip(faelle, web):
        m = ki_maske.Maske(namen)
        try:
            mask = m.maskieren(text)
            rest = ""
            try:
                m.restpruefung([mask])
            except ki_maske.MaskeUnsicher as e:
                rest = str(e)
            py = {"maskiert": mask, "zuwert": m.zu_wert, "rest": rest, "zurueck": m.zuruecksetzen(mask)}
        except ki_maske.MaskeUnsicher as e:
            py = {"fehler": str(e)}
        ok = py == w
        fails += not ok
        if not ok or text in dict(FAELLE):
            print(("✅" if ok else "❌"), text[:70].replace("\n", " "), "" if ok else f"\n   py:  {py}\n   web: {w}")
    print(f"{len(faelle) - fails}/{len(faelle)} gleich (Python-Maske = Web-Maske)")
    return (1 if fails else 0) + anbieter(node)


def anbieter(node):
    """llmAnbieter.ts maskieren()/korrekturPlausibel() = llm_anbieter.py für echte Gen-/Call-0-/Validator-Prompts."""
    import re
    import korrektur
    import llm_anbieter as la
    import pipeline
    tpl = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
    prompt = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
    val = re.search(r"export const validationPrompt = \(rawDictation: string, generatedReport: string\): string => `(.*?)`;",
                    (ROOT / "web_app" / "src" / "gemini.ts").read_text(encoding="utf-8"), re.S).group(1)
    diktate = ["Kniegelenk rechts, Zuweisung Dr. Huber, Vergleich mit 12.03.2025, RH 4711, Gonarthrose.",
               "HWS: Osteochondrose C5/C6, Kontrolle im März 2027.", "Thorax unauffällig."]
    faelle = []
    for d in diktate:
        faelle.append((pipeline.gen_prompt(d, next(iter(tpl.values())), prompt), d, d.upper()))
        faelle.append((korrektur.prompt("<x>Liste</x>", d), d, "Bitte gib mir den Text, den du korrigieren möchtest."))
        faelle.append((val.replace("${rawDictation}", d).replace("${generatedReport}", "## X\n## Befund\nT.\n## Ergebnis\n1. Y"), d, d))
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(faelle, f, ensure_ascii=False)
    r = subprocess.run([node, "--experimental-strip-types", "--no-warnings", "ki_maske_test.mjs", "--anbieter", f.name],
                       cwd=ROOT / "web_app", capture_output=True, text=True, timeout=120)
    web = json.loads(r.stdout) if r.returncode == 0 else []
    fails = 0 if web else 1
    for (p, roh, antwort), w in zip(faelle, web):
        fest, rest, _m, pflicht = la.maskieren(p)
        py = {"fest": fest, "rest": rest, "pflicht": pflicht, "plausibel": la.korrektur_plausibel(roh, antwort)}
        ok = py == w
        fails += not ok
        if not ok:
            print("❌ Prompt-Aufteilung", p[:40], f"\n   py:  {str(py)[-300:]}\n   web: {str(w)[-300:]}")
    print(f"{'✅' if not fails else '❌'} Prompt-Aufteilung/Pflicht/Plausibilität Python = Web ({len(web)} Prompts)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
