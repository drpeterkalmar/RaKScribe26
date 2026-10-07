"""Gate (v3.3.0, Peter 06.10.2026): Ordi-Textbausteine — EXE (source_code/bausteine.py) = Web (web_app/src/bausteine.ts)
auf allen Fällen aus ordi_bausteine_tests.json; jeder Baustein über sein Kürzel erreichbar; Pipeline: Nur-Baustein
ohne KI wörtlich, Baustein mit Zusatz → KI mit Baustein als Vorlage; Satz-Bausteine eingesetzt; Daten gebündelt.
Aufruf: /usr/bin/python3 tests/offline/test_ordi_bausteine.py"""
import json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import bausteine as bs  # noqa: E402
import pipeline as pl  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


B = bs.laden(str(ROOT / "ordi_bausteine.json"))
F = json.loads((ROOT / "ordi_bausteine_tests.json").read_text(encoding="utf-8"))["faelle"]
check(f"{len(B)} Bausteine geladen", len(B) >= 100, len(B))

# 1. Python gegen die von Hand geprüften Erwartungen
for f in F:
    k, r = bs.befund_baustein(f["diktat"], B)
    ist = {"baustein": k, "rest": r if k else None, "nur": bs.nur_baustein(r) if k else None,
           "satz": bs.saetze_einsetzen(f["diktat"], B), "bericht": bs.bericht(k, B, f["diktat"]) if k else None}
    soll = {x: f[x] for x in ist}
    check(f"EXE: {f['diktat'][:50]}", ist == soll, f"{ist} != {soll}")

# 2. Jeder Baustein über jedes seiner Kürzel erreichbar (Befund-Bausteine als Befund, Sätze als Satz)
for key, b in B.items():
    for a in b["sprich"]:
        d = "Baustein " + a
        if b["art"] == "satz":
            ok = bs.saetze_einsetzen(d, B) == b["text"]
        else:
            ok = bs.befund_baustein(d, B)[0] == key
        if not ok:
            check(f"erreichbar: {d} → {key}", False)
check("alle Kürzel erreichbar", True)

# 3. Web = EXE (Node, Type-Stripping)
js = r"""
import { readFileSync } from 'node:fs';
import { ORDI_BAUSTEINE as B, befundBaustein, nurBaustein, saetzeEinsetzen, bericht } from './src/bausteine.ts';
const F = JSON.parse(readFileSync('../ordi_bausteine_tests.json', 'utf8')).faelle;
const out = F.map(f => { const [k, r] = befundBaustein(f.diktat, B);
  return { baustein: k, rest: k ? r : null, nur: k ? nurBaustein(r) : null, satz: saetzeEinsetzen(f.diktat, B), bericht: k ? bericht(k, B, f.diktat) : null }; });
const alle = [];
for (const [key, b] of Object.entries(B)) for (const a of b.sprich) { const d = 'Baustein ' + a;
  alle.push(b.art === 'satz' ? saetzeEinsetzen(d, B) === b.text : befundBaustein(d, B)[0] === key); }
console.log(JSON.stringify({ out, alle: alle.every(Boolean) }));
"""
p = subprocess.run(["node", "--experimental-strip-types", "--input-type=module", "-e", js], cwd=ROOT / "web_app",
                   capture_output=True, text=True)
try:
    web = json.loads(p.stdout.strip().splitlines()[-1])
    for f, w in zip(F, web["out"]):
        soll = {x: f[x] for x in ("baustein", "rest", "nur", "satz", "bericht")}
        check(f"Web = EXE: {f['diktat'][:44]}", w == soll, f"{w} != {soll}")
    check("Web: alle Kürzel erreichbar", web["alle"])
except Exception as e:
    check("Web-Lauf", False, f"{e}: {p.stderr[-800:]}")

# 4. Pipeline (EXE): Nur-Baustein ohne KI, Zusatz mit KI + Baustein-Vorlage, Satz eingesetzt
aufrufe = []
ANTWORT = "## Oesophagus in Doppelkontrast\n\n## Befund\nText mit ausreichend Inhalt für den Test.\n\n## Ergebnis\nHiatushernie."


def llm(prompt):
    aufrufe.append(prompt)
    return ANTWORT


T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
ctx = pl.Kontext(templates=T, display_names=[v["display_name"] for v in T.values()], prompt="{roh_text}\n{template_body}", llm=llm,
                 log=lambda *a, **k: None)
e = pl.befund_aus_diktat("Baustein Mammo 1", ctx)
check("Mammo 1: ohne KI", not aufrufe, aufrufe[:1])
check("Mammo 1: Wortlaut (Peter 07.10., Foto Praxis-PC)", "## Mammographie beidseits" in e.report
      and "Verglichen mit .......... unverändert kleinfleckig strukturierter Drüsenkörper. Keine suspekten Verkalkungen." in e.report
      and "\n\nSonographie:" in e.report, e.report)
check("Mammo 1: Ergebnis unnummeriert wie in der Ordi (ACR / BIRADS)", e.report.rstrip().endswith("## Ergebnis\nACR\nBIRADS"), e.report[-60:])
e2 = pl.befund_aus_diktat("Baustein Mammo 2", ctx)
check("wörtliche Bausteine generell unnummeriert", "## Ergebnis\nInvolutionsmamma beidseits.\nKontrolle" in e2.report, e2.report[-120:])
e = pl.befund_aus_diktat("Baustein Ösophagus 2, zusätzlich kleine Hiatushernie", ctx)
check("Ösophagus 2 + Zusatz: KI mit Baustein", len(aufrufe) == 1 and "Wasser-Siphon-Tests" in aufrufe[0]
      and "<ordi_baustein>" in aufrufe[0], aufrufe[-1:] and aufrufe[-1][:300])
aufrufe.clear()
e = pl.befund_aus_diktat("Baustein veneu links", ctx)
check("veneu links: Seite getauscht", "Beinvenen links" in e.report and "rechts" not in e.report and not aufrufe, e.report)
e = pl.befund_aus_diktat("Knochendichte LWS und Hüfte, Baustein A1", ctx)
check("Satz-Baustein A1 im Diktat", "Manitoba" in (aufrufe[-1] if aufrufe else ""), aufrufe[-1:] and aufrufe[-1][:200])

# 5. Gebündelt (keine Extradatei)
y = (ROOT / ".github/workflows/build-exe.yml").read_text(encoding="utf-8")
check("EXE-Build bündelt ordi_bausteine.json", '--add-data "../ordi_bausteine.json;."' in y and "--hidden-import=bausteine" in y)

print("FAILS:", fails)
sys.exit(1 if fails else 0)
