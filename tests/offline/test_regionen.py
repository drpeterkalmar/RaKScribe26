"""Gate (Umbau Schritt 5, Gutachten P2-6): Mehr-Regionen-Befund — scheitert eine Region, bleiben die fertigen
sichtbar und die fehlende ist benannt. Aufruf: /usr/bin/python3 tests/offline/test_regionen.py"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import pipeline as pl  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


def voll(t):  # Vollständigkeit wie _report_complete (vereinfacht für den Test)
    return "## Ergebnis" in t and len(t.split("## Ergebnis")[1].strip()) > 5


SCHULTER = "## Schultergelenk rechts in 2 Ebenen\n\n## Befund\nText.\n\n## Ergebnis\n1. Omarthrose rechts."
ELLBOGEN = "## Ellbogengelenk rechts in 2 Ebenen\n\n## Befund\nText.\n\n## Ergebnis\n1. Arthrose rechts."
seg = br.split_regionen("Schulter rechts Punkt Omarthrose Punkt Ellbogen rechts Punkt Ellbogengelenksarthrose")
check("Trenner liefert 2 Segmente (Fixture-Annahme)", len(seg) == 2, str(seg))

rep, fehler = pl.assemble_regions(seg, [SCHULTER, ELLBOGEN], voll)
check("alle Regionen fertig → zusammengefügt, keine Fehler", fehler == [] and rep == br.befunde_zusammenfuegen([SCHULTER, ELLBOGEN]))
rep, fehler = pl.assemble_regions(seg, [SCHULTER, RuntimeError("HTTP 503")], voll)
check("Region 2 wirft → Schulter-Befund bleibt sichtbar", rep.startswith(SCHULTER), rep[:80])
check("… fehlende Region benannt", fehler == ["Ellbogen rechts"] and
      "Befund für Region Ellbogen rechts konnte nicht erstellt werden — bitte erneut diktieren." in rep, str(fehler))
rep, fehler = pl.assemble_regions(seg, ["## Schultergelenk rechts\n\n## Befund\nText.", ELLBOGEN], voll)
check("unvollständiger Teil (kein Ergebnis) zählt als gescheitert", fehler == ["Schulter rechts"] and ELLBOGEN in rep, str(fehler))
rep, fehler = pl.assemble_regions(seg, [None, None], voll)
check("beide gescheitert → zwei Hinweise, kein Befund", len(fehler) == 2 and "## Ergebnis" not in rep)
check("Regionsname aus erstem Satz, gekürzt", pl.region_name("Sprunggelenk links: Distorsion") == "Sprunggelenk links"
      and len(pl.region_name("x" * 90)) == 40 and pl.region_name("") == "?")

src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE nutzt assemble_regions + Fehlerdialog statt stummem Abbruch",
      "_pl.assemble_regions(segmente, teile, _report_complete)" in src and "if fehler:" in src
      and 'report = br.befunde_zusammenfuegen(teile) if all(' not in src)

print("\n" + ("✅ MEHR-REGIONEN PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
