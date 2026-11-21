"""Gate kaiscribe-gws-ap-normaltext-n1 (Peter 20.11.2026, Kanban #459 „a“): Der Normaltext der Vorlage „Ganzaufnahme der
Wirbelsäule a.-p.“ lautet „Wirbelsäule: Normale Stellung. Alignementlinien regelrecht.“ – ohne die frühere
„flachbogige rechts-konvexe Skoliose“. Geprüft (EXE-Kette pipeline.befund_aus_diktat, KI-Attrappe, kein Netz):
  1. Vorlage selbst: kein „Skoliose“, Achsensatz wie gewünscht.
  2. GWS a.p. ohne SQUIRREL, ohne Stellungs-Diktat: Normalbefund (Bypass) und KI-Weg → kein „Skoliose“ im Befund,
     und die KI bekommt in der Vorlage keine Skoliose mehr vorgelegt.
  3. Mit diktierter Skoliose: geht an die KI (kein Bypass), das Diktat steht im Prompt, die Skoliose bleibt im Befund.
  4. Mit SQUIRREL (Cobb 44°): SQUIRREL-Text wie bisher an Stelle von „Normale Stellung.“, Ergebnis „Hochgradige …“.
Synthetische Diktate, keine Patientendaten.  Aufruf: python3 tests/offline/test_gws_ap_normaltext.py"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "source_code"))
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402
import prod_pipeline as pp  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
SQ = json.loads((ROOT / "tests" / "offline" / "squirrel_bausteine.json").read_text(encoding="utf-8"))
AP = "ganzaufnahme_der_wirbelsäule_a-p"
NEU = "Wirbelsäule: Normale Stellung. Alignementlinien regelrecht."
ALT = "flachbogige rechts-konvexe Skoliose"
S2 = "Rechtskonvexe skoliotische Krümmung der BWS (Th5–Th12) mit einem Cobb-Winkel von 44°."
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def befund(report):
    return report.split("## Befund\n")[1].split("\n\n## Ergebnis")[0]


aufrufe = []


def kette(diktat, antwort_befund):
    """EXE-Kette mit KI-Attrappe: die Attrappe antwortet mit der Vorlage, deren Achsensatz durch antwort_befund ersetzt."""
    body = T[AP]["body"].split("\n", 2)[2]
    antwort = (f"## {T[AP]['display_name']}\n\n## Befund\n{body.replace(NEU, antwort_befund)}\n\n## Ergebnis\n"
               f"{'Flachbogige linkskonvexe Skoliose.' if 'Skoliose' in antwort_befund else T[AP]['ergebnis']}")

    def llm(prompt):
        aufrufe.append(prompt)
        return antwort
    aufrufe.clear()
    return pl.befund_aus_diktat(diktat, pp.exe_kontext(llm=llm))


# ── 1. Vorlage ──
check("Vorlage GWS a.p.: „Wirbelsäule: Normale Stellung. Alignementlinien regelrecht.“",
      NEU in T[AP]["body"] and ALT not in T[AP]["body"], T[AP]["body"][:200])
check("Vorlage GWS a.p.: kein „Skoliose“ in Text und Normal-Ergebnis",
      "skolio" not in T[AP]["body"].lower() and "skolio" not in T[AP].get("ergebnis", "").lower(), T[AP])
check("kein anderer Vorlagentext enthält die alte Formulierung",
      not [k for k, v in T.items() if ALT in json.dumps(v, ensure_ascii=False)])

# ── 2. ohne SQUIRREL, ohne Stellungs-Diktat ──
e = kette("Ganzaufnahme der Wirbelsäule a.p. unauffällig.", NEU)
check("Normalbefund-Diktat: Bypass ohne KI", not aufrufe, len(aufrufe))
check("Normalbefund-Diktat: Achsensatz neu, kein „Skoliose“ im Befund",
      NEU in befund(e.report) and "skolio" not in e.report.lower(), e.report)

e = kette("Ganzaufnahme der Wirbelsäule a.p.: Leichte Osteochondrose L4/L5.", NEU)
check("Diktat ohne Stellung geht an die KI, Vorlage im Prompt ohne „Skoliose“",
      len(aufrufe) == 1 and NEU in aufrufe[0] and ALT not in aufrufe[0], aufrufe[:1])
check("Diktat ohne Stellung: kein „Skoliose“ im Befund", "skolio" not in befund(e.report).lower(), e.report)

# ── 3. mit diktierter Skoliose ──
D = "Wirbelsäule: Normale Stellung, flachbogige linkskonvexe Skoliose. Alignementlinien regelrecht."
e = kette("Ganzaufnahme der Wirbelsäule a.p.: flachbogige linkskonvexe Skoliose, sonst unauffällig.", D)
check("diktierte Skoliose: an die KI (kein Bypass), Diktat im Prompt",
      len(aufrufe) == 1 and "flachbogige linkskonvexe Skoliose" in aufrufe[0], len(aufrufe))
check("diktierte Skoliose steht im Befund und im Ergebnis",
      "flachbogige linkskonvexe Skoliose" in befund(e.report) and "Skoliose" in e.report.split("## Ergebnis\n")[1],
      e.report)

# ── 4. mit SQUIRREL: wie bisher ──
B = I.aus_liste([next(f["baustein"] for f in SQ if f["fall"] == "einzeln")])
v = T[AP]
rep = (f"## {v['display_name']}\n\n## Befund\n{v['body'].split(chr(10), 2)[2]}\n\n## Ergebnis\n{v['ergebnis']}")
e = I.einsetzen(rep, B, diktat="Wirbelsäule unauffällig.")
check("SQUIRREL: Sätze an Stelle von „Normale Stellung.“, Beschriftung und Alignement bleiben",
      f"Wirbelsäule: {S2} Alignementlinien regelrecht." in e.report and "Normale Stellung" not in e.report, e.report)
check("SQUIRREL: Ergebnis „Hochgradige rechtskonvexe Skoliose der BWS.“ wie bisher",
      e.report.split("## Ergebnis\n")[1].startswith("Hochgradige rechtskonvexe Skoliose der BWS."), e.report)

# ── 4b. Abnahme 21.11.2026 (C): KI ließ „Wirbelsäule:“ weg – SQUIRREL ersetzt „Normale Stellung.“ trotzdem ──
rep2 = ("## Ganzaufnahme der Wirbelsäule a.-p.\n\n## Befund\nNormale Stellung. Alignementlinien regelrecht. Anzahl, Form, Größe "
        "und Stellung der Wirbelkörper zueinander regelrecht.\n\n## Ergebnis\nRegelrechte Darstellung der Wirbelsäule.")
e2 = I.einsetzen(rep2, B, diktat="Wirbelsäule unauffällig.")
check("SQUIRREL ohne Beschriftung: Skoliose-Satz statt „Normale Stellung.“ (nie beides)",
      S2 in e2.report and "Normale Stellung" not in e2.report, e2.report)

# ── 5. Abnahme 21.11.2026: STT schreibt „ganz Aufnahme der Wirbelsäule AP“ → Fehlhör-Liste → a.p.-Vorlage ──
import detect as _det  # noqa: E402
import misheard as _mh  # noqa: E402
_roh = "ganz Aufnahme der Wirbelsäule AP. : unauffällig."
_korr = _mh.apply(_roh, _mh.compile_rules(json.loads((ROOT / "misheard_words.json").read_text(encoding="utf-8"))))
_korr = _korr[0] if isinstance(_korr, tuple) else _korr
check("„ganz Aufnahme der Wirbelsäule AP“ (STT) → „Ganzaufnahme …“ → Vorlage Ganzaufnahme der Wirbelsäule a.-p.",
      _det.detect_template(_korr, T) == AP, (_korr, _det.detect_template(_korr, T)))

print(f"\n{'GRÜN' if not fails else f'{fails} FEHLER'}")
sys.exit(1 if fails else 0)
