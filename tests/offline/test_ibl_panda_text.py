"""Gate IB Lab PANDA → Knochenalter als fertiger Ergebnisbefund (Georg Riegler 18.11.2026, Brief kaiscribe-panda-knochenalter-n1).
Bausteine aus tests/offline/snapshots/panda_bausteine.json (vom Abholer 1.3.10 ris-mods ibl/panda_ergebnis.py über die Brücke
erzeugt): 3 echte Fälle (anonym: 11.11., 16.11., 12.11.2026), retardiert, akzeleriert, NaN-%, hand2, Geburtsdatum fehlt,
Knochenalter NaN. Geprüft: Wortlaut 1:1, Gerüst = fertiger Befund ohne Befundteil, nach der KI (Vorlage „Knochenalter Junge“
mit Lücken, „Unauffälliger Befund.“) nur der Ergebnisbefund, Diktiertes danach nummeriert, Einzelpunkt ohne Nummer,
CAS-Leistung nicht Knochenalter (handgel, hand2) → kein Text + „PANDA außerhalb Auftrag/IFU“, Sonderfälle nur Anzeige,
zweimal einsetzen, Gen-Prompt, ganze EXE-Kette (KI-Attrappe, alle Wächter). Aufruf: python3 tests/offline/test_ibl_panda_text.py"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
SNAP = json.loads((ROOT / "tests/offline/snapshots/panda_bausteine.json").read_text(encoding="utf-8"))
FALL = {f["nr"]: I.aus_liste([f["baustein"]]) for f in SNAP["faelle"]}
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


SOLL = {
    1: "Zum Zeitpunkt der Untersuchung beträgt das Alter des Jungen 13 Jahre und 6 Monate. Das ermittelte Knochenalter nach "
       "Greulich und Pyle beträgt 13 Jahre und 3 Monate und ist damit altersentsprechend. Nach Bayley und Pinneau sind "
       "89,0 % des Wachstumspotenzials erreicht.",
    2: "Zum Zeitpunkt der Untersuchung beträgt das Alter des Jungen 9 Jahre und 10 Monate. Das ermittelte Knochenalter nach "
       "Greulich und Pyle beträgt 10 Jahre und 8 Monate und ist damit altersentsprechend. Nach Bayley und Pinneau sind "
       "80,0 % des Wachstumspotenzials erreicht.",
    3: "Zum Zeitpunkt der Untersuchung beträgt das Alter des Mädchens 11 Jahre und 10 Monate. Das ermittelte Knochenalter "
       "nach Greulich und Pyle beträgt 11 Jahre und 8 Monate und ist damit altersentsprechend. Nach Bayley und Pinneau "
       "sind 91,8 % des Wachstumspotenzials erreicht.",
    4: "Zum Zeitpunkt der Untersuchung beträgt das Alter des Jungen 11 Jahre und 6 Monate. Das ermittelte Knochenalter nach "
       "Greulich und Pyle beträgt 9 Jahre und 2 Monate und ist damit um 2 Jahre und 4 Monate retardiert. Nach Bayley und "
       "Pinneau sind 78,4 % des Wachstumspotenzials erreicht.",
    5: "Zum Zeitpunkt der Untersuchung beträgt das Alter des Mädchens 10 Jahre. Das ermittelte Knochenalter nach Greulich "
       "und Pyle beträgt 12 Jahre und 1 Monat und ist damit um 2 Jahre und 1 Monat akzeleriert. Nach Bayley und Pinneau "
       "sind 92,3 % des Wachstumspotenzials erreicht.",
    6: "Zum Zeitpunkt der Untersuchung beträgt das Alter des Jungen 6 Jahre und 8 Monate. Das ermittelte Knochenalter nach "
       "Greulich und Pyle beträgt 5 Jahre und 6 Monate und ist damit altersentsprechend.",
}
TITEL = "Hand links, Knochenalterbestimmung"
HANDL = [{"kurz": "handl", "text": "Hand li.", "vorlage": "hand_in_2_ebenen", "seite": "links", "ziffer": 1}]
VORLAGE_KI = ("Zum Zeitpunkt der Untersuchung beträgt das Alter des Jungen … Jahre und … Monate, die Körpergröße … cm. Das "
              "ermittelte Knochenalter nach Greulich und Pyle beträgt … Jahre.\nDie errechnete Endkörpergröße beträgt … cm.")


def befund(titel, ergebnis, befundteil=None):
    return f"## {titel}\n\n" + (f"## Befund\n{befundteil}\n\n" if befundteil else "") + f"## Ergebnis\n{ergebnis}"


for nr, soll in SOLL.items():
    b = FALL[nr]
    check(f"Fall {nr}: Text des Abholers = Georgs Wortlaut", I.panda_text(b[0]) == soll, I.panda_text(b[0]))
    g = I.geruest(b, HANDL, T)
    check(f"Fall {nr}: Gerüst (sofort EOL) = fertiger Ergebnisbefund ohne Befundteil, ohne Nummer",
          g is not None and g.report == befund(TITEL, soll), g.report if g else None)
    for z in ("Körpergröße", "Endgröße", " SD", "Norm", "…", "Unauffälliger Befund"):
        if z in (g.report if g else ""):
            check(f"Fall {nr}: kein „{z}“ im Befund", False, g.report)

# nach der KI: Vorlage „Knochenalter Junge“ (Lücken, Körpergröße, Endgröße) + „Unauffälliger Befund.“ → nur Ergebnisbefund
ki = befund(TITEL, "Unauffälliger Befund.", VORLAGE_KI)
e = I.einsetzen(ki, FALL[1], diktat="Knochenalter Junge.", cas_leistungen=HANDL, templates=T)
check("nach der KI: Befundteil mit Lücken/Körpergröße/Endgröße weg, „Unauffälliger Befund.“ ersetzt, Text ohne Nummer",
      e.report == befund(TITEL, SOLL[1]), e.report)
check("… eingesetzt = der Text, Gate ohne Abweichung",
      e.zeilen == [SOLL[1]] and not [h for h in e.hinweise if "nicht 1:1" in h], (e.zeilen, e.hinweise))
e2 = I.einsetzen(e.report, FALL[1], diktat="Knochenalter Junge.", cas_leistungen=HANDL, templates=T)
check("zweimal einsetzen: unverändert (nicht doppelt)", e2.report == e.report, e2.report)

# Diktiertes (Nebenbefund) folgt als nächster Punkt, dann nummeriert; KI-Satz zum Knochenalter entfällt
ki = befund("Hand links in 2 Ebenen", "1. Altersentsprechendes Knochenalter.\n2. Kleine Exostose am Os metacarpale II.",
            "Mineralgehalt und Knochenstruktur regelrecht. Gelenkspalten allseits normal weit.")
e = I.einsetzen(ki, FALL[4], diktat="Knochenalter. Nebenbefund kleine Exostose Os metacarpale II.",
                cas_leistungen=HANDL, templates=T)
check("Diktierter Nebenbefund nach dem Text (1./2.), Normalsätze der Hand-Vorlage und KI-Knochenaltersatz weg",
      e.report == befund("Hand links in 2 Ebenen", f"1. {SOLL[4]}\n2. Kleine Exostose am Os metacarpale II."), e.report)

# Diktierter pathologischer Befundsatz bleibt stehen (+ Hinweis), am Diktat wird nichts geändert
ki = befund(TITEL, "Unauffälliger Befund.", "Zystische Aufhellung im Os capitatum.")
e = I.einsetzen(ki, FALL[2], diktat="Zystische Aufhellung im Os capitatum.", cas_leistungen=HANDL, templates=T)
check("Diktierter Befundsatz bleibt, Hinweis „bitte prüfen“",
      "Zystische Aufhellung im Os capitatum." in e.report and SOLL[2] in e.report
      and any("Befundteil mit diktiertem Text" in h for h in e.hinweise), (e.report, e.hinweise))

# CAS-Leistung nicht Knochenalter → kein Text, Hinweis
for kurz in ("handgell", "hand2", "kahn"):
    leist = [{"kurz": kurz, "text": "Handgelenk li.", "vorlage": "handgelenk_in_2_ebenen", "seite": "links", "ziffer": 1}]
    ki = befund("Handgelenk links in 2 Ebenen", "Regelrechte Darstellung des Handgelenkes.", "Gelenkspalten normal weit.")
    e = I.einsetzen(ki, FALL[1], diktat="Handgelenk links.", cas_leistungen=leist, templates=T)
    check(f"CAS {kurz}: kein PANDA-Text, Hinweis „PANDA außerhalb Auftrag/IFU“",
          e.report == ki and any(I.PANDA_IFU in h for h in e.hinweise), (e.report, e.hinweise))
    check(f"CAS {kurz}: kein Gerüst", I.geruest(FALL[1], leist, T) is None)
check("CAS-Leistung „Knochenalter“ im Text (ohne Kürzel) passt",
      I.panda_auftrag_passt(FALL[1][0], [{"text": "Knochenalter", "ziffer": 1}]) is True)
check("ohne CAS-Leistungen: unbekannt → Text kommt (Weiche schickt PANDA nur bei handl)",
      I.panda_auftrag_passt(FALL[1][0], None) is None and I.panda_text(FALL[1][0]) == SOLL[1])

# Sonderfälle: kein Text, nur Anzeige
check("NaN-%: Hinweis „nicht tabelliert“ in der Anzeige",
      "IB Lab PANDA: Wachstumspotenzial bei diesem Knochenalter nicht tabelliert." in I.anzeige_hinweise(FALL[6]),
      I.anzeige_hinweise(FALL[6]))
for nr, wort in ((7, "2 Ergebnisse (Knochenalter 8 Jahre / 2 Jahre und 3 Monate)"), (8, "Geburtsdatum fehlt"),
                 (9, "Knochenalter nicht berechnet")):
    b = FALL[nr]
    ki = befund(TITEL, "Unauffälliger Befund.", VORLAGE_KI)
    e = I.einsetzen(ki, b, diktat="Knochenalter Junge.", cas_leistungen=HANDL, templates=T)
    check(f"Fall {nr}: kein Text, keine Messzeilen, Befund unverändert; Prüfzeile „{wort}“ in der Anzeige",
          e.report == ki and not e.zeilen and I.geruest(b, HANDL, T) is None
          and any(wort in h and "prüfen" in h for h in I.anzeige_hinweise(b)), (e.report, I.anzeige_hinweise(b)))
check("Herstellerstatus/Messzeilen kommen nie in den Befund", I.befund_zeilen(FALL[1][0]) == [])
check("auffällig markiert nur retardiert/akzeleriert",
      I.auffaellige_zeilen(FALL[1]) == [] and I.auffaellige_zeilen(FALL[4]) == [SOLL[4]])

# Gen-Prompt
blk = I.prompt_block(FALL[1], "Hand in 2 Ebenen\n\nMineralgehalt und Knochenstruktur regelrecht.", "Knochenalter Junge.")
check("Gen-Prompt: PANDA-Anweisung (kein Befundteil, keine Lücken), keine Zahlen",
      I.PANDA_PROMPT in blk and "13 Jahre" not in blk and "nicht übernehmen" not in blk, blk)
check("Gen-Prompt ohne Text (hand2): nichts", I.prompt_block(FALL[7], "", "") == "")


# ───────────────────────────── ganze EXE-Kette (KI-Attrappe, alle Wächter danach) ─────────────────────────────
def kette(diktat, bausteine, ki_befund, ki_ergebnis):
    prompts = []

    def llm(p):
        prompts.append(p)
        return befund(TITEL, ki_ergebnis, ki_befund)
    ctx = pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=llm, log=lambda *a: None,
                     ibl=I.IblKontext(bausteine, HANDL))
    return pl.befund_aus_diktat(diktat, ctx), prompts


for nr in (1, 3, 5, 6):
    erg, prompts = kette("Hand links Knochenalter.", FALL[nr], VORLAGE_KI.replace("des Jungen", "des Jungen/Mädchens"),
                         "Unauffälliger Befund.")
    check(f"EXE-Kette Fall {nr}: Ergebnisbefund 1:1 nach allen Wächtern",
          erg.report.strip() == befund(TITEL, SOLL[nr]), erg.report)
    check(f"EXE-Kette Fall {nr}: PANDA-Anweisung im Gen-Prompt", any(I.PANDA_PROMPT in p for p in prompts))

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
