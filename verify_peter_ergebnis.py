#!/usr/bin/env python3
"""verify_peter_ergebnis.py — v3.2-Regression für Peters Nachtrag (Telegram „RaKScribe26 dev“, 05.10.2026).

1. „Mein Diktat wird eins zu eins in das Ergebnis übernommen“ → Ergebnis = strukturierte Diagnosen bzw. das
   zur Untersuchung passende Normal-Ergebnis, NIE das Diktat.
2. „Ein unauffälliges Lungenröntgen wurde als unauffälliges Skelettröntgen beschrieben“ → Thorax-Vorlage,
   kein Skelett-Standardtext.
Kette A = EXE, Kette B = Web (prod_pipeline.py = echte Produktions-Prompts/-Funktionen), je 3 Läufe.

  /usr/bin/python3 verify_peter_ergebnis.py [runs]
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))
import prod_pipeline as pp  # noqa: E402

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def teile(rep):
    titel = rep.strip().split("\n", 1)[0]
    bef = rep.split("## Befund", 1)[1].split("## Ergebnis")[0] if "## Befund" in rep else "FEHLT: ## Befund Knochenstruktur"
    erg = rep.split("## Ergebnis", 1)[1].strip() if "## Ergebnis" in rep else ""
    return titel, bef, erg


def nicht_diktat(erg, diktat):
    n = lambda x: re.sub(r"[\s.:,]+", " ", x.lower()).strip()
    return n(erg) != n(diktat) and n(diktat) not in n(erg)


FAELLE = [
    ("Lungenröntgen unauffällig.", lambda t, b, e, d: [
        ("Titel Thorax", "thorax" in t.lower()),
        ("Thorax-Vorlage im Befund", "Lungenfelder" in b and "Mediastinum" in b),
        ("kein Skelett-Text (Mineralgehalt/Knochenstruktur)", "Knochenstruktur" not in b),
        ("Ergebnis 'Unauffälliger Befund.'", e == "Unauffälliger Befund."),
        ("Ergebnis ≠ Diktat", nicht_diktat(e, d))]),
    ("Torax p.a. und seitlich unauffällig.", lambda t, b, e, d: [
        ("Titel Thorax", "thorax" in t.lower()),
        ("kein Skelett-Text", "Knochenstruktur" not in b),
        ("Ergebnis ≠ Diktat", nicht_diktat(e, d))]),
    ("Thorax: Kardiomegalie, sonst unauffällig.", lambda t, b, e, d: [
        ("Titel Thorax", "thorax" in t.lower()),
        ("Ergebnis '1. Kardiomegalie'", e.startswith("1. Kardiomegalie")),
        ("Befund ohne 'Herz-Gefäßschatten normal konfiguriert'", "normal konfiguriert" not in b or "Herz-Gefäßschatten normal" not in b),
        ("Ergebnis ≠ Diktat", nicht_diktat(e, d))]),
    ("Knie rechts unauffällig", lambda t, b, e, d: [
        ("Titel 'Kniegelenk rechts in 2 Ebenen'", t == "## Kniegelenk rechts in 2 Ebenen"),
        ("Ergebnis 'Regelrechte Darstellung des Kniegelenkes rechts.'", e == "Regelrechte Darstellung des Kniegelenkes rechts."),
        ("Ergebnis ≠ Diktat", nicht_diktat(e, d))]),
]


def main():
    fails, out = 0, {}
    for diktat, checks in FAELLE:
        for kette, fn in (("A", pp.exe_kette), ("B", pp.web_kette)):
            for r in range(RUNS):
                try:
                    rep = fn(diktat)
                except Exception as ex:
                    rep = f"FEHLER {ex}"
                t, b, e = teile(rep)
                bad = [n for n, ok in checks(t, b, e, diktat) if not ok]
                fails += bool(bad)
                out.setdefault(diktat, {}).setdefault(kette, []).append(rep)
                print(f"{'✅' if not bad else '❌'} {kette}{r + 1} {diktat[:45]:45} → Ergebnis: {e.replace(chr(10), ' | ')[:80]}"
                      + (f"\n     FEHLT: {'; '.join(bad)}\n     TITEL: {t}" if bad else ""))
    (ROOT / "verify_peter_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n{'✅ GATE GRÜN' if not fails else f'❌ GATE ROT — {fails} Läufe'}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
