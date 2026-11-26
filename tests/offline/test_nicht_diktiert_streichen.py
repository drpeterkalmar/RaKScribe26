"""Gate kaiscribe-nicht-diktiert-streichen-n1 – Georg 26.11.2026 („1b“, Karte #542, ersetzt seine Regel vom 20.11.):
Bestellt das CAS mehrere Untersuchungen und wird nur ein Teil diktiert, bekommen die nicht diktierten Untersuchungen
KEINEN Titel, KEINEN Normaltext, KEINEN eigenen Befund – stattdessen GENAU EINE rote Prüfzeile im Befundfenster
„<Untersuchungen> bestellt, aber nicht diktiert – bitte prüfen“. Unverändert: reiner IB-Lab-Teil (Ganzbein mit LAMA),
Funktions-Kombi, GWS a.p. + seitlich, DEXA nie durch KaiScribe. EXE-Kette mit KI-Attrappe (das Web hat kein CAS).
Keine Patientendaten (nur RH-Nummern).  Aufruf: python3 tests/offline/test_nicht_diktiert_streichen.py"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402,F401

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import cas_vorlagen as cv  # noqa: E402
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def L(kurz, text, vorlage, seite=None, ziffer=1):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": "Röntgen", "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True, "ziffer": ziffer}


def ki(p):
    """KI-Attrappe: Titel der angefragten Untersuchung + Normalsätze ihrer Vorlage."""
    u = re.search(r"<untersuchung>(.*?)</untersuchung>", p).group(1)
    k = next((k for k, v in T.items() if v.get("display_name") == u), None)
    body = T[k]["body"].split("\n", 2)[2] if k else "Beschreibung laut Diktat."
    return f"## {u}\n\n## Befund\n{body}\n\n## Ergebnis\nBefund laut Diktat."


def lauf(diktat, leistungen, bausteine=None):
    cas = cv.CasHinweis(leistungen, T)
    ibl = I.IblKontext(I.aus_liste(bausteine), cas_leistungen=leistungen) if bausteine else None
    return pl.befund_aus_diktat(diktat, pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=ki,
                                                   log=lambda *a: None, cas=cas, ibl=ibl))


def titel(report):
    return [z[3:] for z in report.split("\n") if z.startswith("## ") and z[3:] not in ("Befund", "Ergebnis")]


def normal(key):
    return T[key]["body"].split("\n", 2)[2][:40]


def pruef(erg):
    return [h for h in erg.cas_hinweise if "bestellt, aber nicht diktiert" in h]


HWS = L("hws", "HWS", "halswirbelsäule_in_2_ebenen", ziffer=1)
BWS = L("bws", "BWS", "brustwirbelsäule_in_2_ebenen", ziffer=2)
LWS = L("lws", "LWS", "lendenwirbelsäule_in_2_ebenen", ziffer=3)
HUEFTE = L("hüfter", "Hüfte re.", "hüftgelenk_in_2_ebenen", "rechts", ziffer=4)
HWS_D = "Halswirbelsäule: Osteochondrose C5/6."

# ── 1: HWS diktiert, BWS + LWS nur bestellt ──
erg = lauf(HWS_D, [HWS, BWS, LWS])
check("1: HWS diktiert + BWS/LWS bestellt → nur der HWS-Befund", titel(erg.report) == ["Halswirbelsäule in 2 Ebenen"]
      and erg.vorlagen == ["halswirbelsäule_in_2_ebenen"], (titel(erg.report), erg.vorlagen))
check("1: kein Normaltext von BWS/LWS im Befund",
      normal("brustwirbelsäule_in_2_ebenen") not in erg.report and normal("lendenwirbelsäule_in_2_ebenen") not in erg.report,
      erg.report)
check("1: GENAU EINE Prüfzeile, Wortlaut fest „BWS, LWS bestellt, aber nicht diktiert – bitte prüfen“",
      pruef(erg) == ["BWS, LWS bestellt, aber nicht diktiert – bitte prüfen"]
      and not any("laut CAS, nicht diktiert" in h for h in erg.cas_hinweise), erg.cas_hinweise)
check("1: Prüfzeile ist rot (enthält „bitte prüfen“ wie die bestehenden Prüfzeilen, RaKScribe._cas_hinweise_zeigen)",
      "bitte prüfen" in pruef(erg)[0] if pruef(erg) else False, erg.cas_hinweise)
check("1: Prüfzeile steht nicht im Brief", "bestellt, aber nicht diktiert" not in erg.report, erg.report)

# ── 2: RH 68 (Ursulas Beispiel 20.11.): HWS diktiert, BWS/LWS/Hüfte nur im Auftrag → Überschriften fallen ganz weg ──
erg = lauf(HWS_D, [HWS, BWS, LWS, HUEFTE])
check("2 RH 68: keine Überschrift BWS/LWS/Hüfte, nur HWS", titel(erg.report) == ["Halswirbelsäule in 2 Ebenen"],
      titel(erg.report))
check("2 RH 68: eine Prüfzeile mit allen drei", pruef(erg) == ["BWS, LWS, Hüfte re. bestellt, aber nicht diktiert – bitte prüfen"],
      erg.cas_hinweise)
check("2 RH 68: keine Seiten-Prüfzeile für die nicht diktierte Hüfte", not any("Seite" in h for h in erg.cas_hinweise),
      erg.cas_hinweise)

# ── 3: alle diktiert → keine Prüfzeile ──
erg = lauf("Halswirbelsäule: Osteochondrose C5/6. Lendenwirbelsäule: Osteochondrose L4/5.", [HWS, LWS])
check("3: alle diktiert → zwei Befunde, keine Prüfzeile",
      titel(erg.report) == ["Halswirbelsäule in 2 Ebenen", "Lendenwirbelsäule in 2 Ebenen"] and not pruef(erg)
      and not any("nicht diktiert" in h for h in erg.cas_hinweise), (titel(erg.report), erg.cas_hinweise))

# ── 4: LAMA/Ganzbein (reiner IB-Lab-Teil) unverändert ──
LAMA = {"accno": "999001200542", "ziffer": 2, "modul": "lama", "name": "LAMA", "version": 1, "seiten": ["rechts", "links"],
        "befundteil": ["HKA-Winkel rechts 178,1° (IB Lab LAMA)."],
        "ergebnis": ["Regelrechte Beinachse beidseits (HKA rechts 1,9°, links 0,9°; MAD rechts 12,6 mm, links 11,7 mm)."],
        "hinweise": []}
GB = L("gb", "Ganzbein bds.", "ganzbeinaufnahme_im_stand", "beidseits", ziffer=2)
erg = lauf("Lendenwirbelsäule: Osteochondrose L5/S1.", [LWS, GB], [LAMA])
gb = next((t for t in titel(erg.report) if t.startswith("Ganzbein")), None)
check("4: Ganzbein mit LAMA, nicht diktiert → eigener Befund mit Titel + LAMA-Werten wie bisher",
      gb is not None and "Regelrechte Beinachse beidseits" in erg.report
      and any(cv.NICHT_DIKTIERT_NORMAL in h for h in erg.cas_hinweise) and not pruef(erg), (erg.report, erg.cas_hinweise))
erg = lauf("Lendenwirbelsäule: Osteochondrose L5/S1.", [LWS, GB, BWS], [LAMA])
check("4b: LAMA-Teil bleibt, nur die nicht diktierte BWS wird gestrichen (eine Prüfzeile „BWS …“)",
      any(t.startswith("Ganzbein") for t in titel(erg.report)) and not any(t.startswith("Brust") for t in titel(erg.report))
      and pruef(erg) == ["BWS bestellt, aber nicht diktiert – bitte prüfen"], (titel(erg.report), erg.cas_hinweise))
erg = lauf("Lendenwirbelsäule: Osteochondrose L5/S1.", [LWS, GB])
check("4c: Ganzbein OHNE IB-Lab-Baustein, nicht diktiert → gestrichen + Prüfzeile",
      not any(t.startswith("Ganzbein") for t in titel(erg.report))
      and pruef(erg) == ["Ganzbein bds. bestellt, aber nicht diktiert – bitte prüfen"], (titel(erg.report), erg.cas_hinweise))

# ── 5: Funktions-Kombi unverändert ──
FHWS = "funktionsaufnahmen_der_halswirbelsäule"
HWSMF = L("x-hws-funktion", "HWS ap u. seitl. incl.Funktion", FHWS)
SCHULTERR = L("x-schulter-re", "Schultergelenk rechts", "schultergelenk_in_2_ebenen", "rechts", ziffer=2)
erg = lauf("HWS unauffällig.", [HWSMF])
check("5: HWS incl. Funktion, HWS diktiert → HWS + Funktionsaufnahmen wie bisher, keine Prüfzeile",
      erg.vorlagen == ["halswirbelsäule_in_2_ebenen", FHWS] and not erg.cas_hinweise, (erg.vorlagen, erg.cas_hinweise))
erg = lauf("Schulter rechts: Omarthrose.", [HWSMF, SCHULTERR])
check("5b: Funktions-Kombi nicht diktiert → wie bisher nur der Hinweis „… laut CAS, nicht diktiert“, kein Abschnitt",
      erg.vorlagen == ["schultergelenk_in_2_ebenen"]
      and erg.cas_hinweise == ["HWS ap u. seitl. incl.Funktion laut CAS, nicht diktiert"], (erg.vorlagen, erg.cas_hinweise))

# ── 6: GWS a.p. + seitlich unverändert ──
GWS = L("gws", "WS Ganzaufn. ap + stl. geteilt", "ganzaufnahme_der_wirbelsäule_a-p")
erg = lauf("Ganzaufnahme der Wirbelsäule: flachbogige skoliotische Asymmetrie.", [GWS])
check("6: GWS a.p. + seitlich (ein CAS-Eintrag) → „Gesamte Wirbelsäule“, keine Prüfzeile",
      erg.vorlagen == ["wirbelsäule_gesamt"] and not pruef(erg), (erg.vorlagen, erg.cas_hinweise))

# ── 7: DEXA nie durch KaiScribe ──
DEXA_L = L("dexa", "Densitometrie", "knochendichtemessung_dexa", ziffer=2)
erg = lauf("Lendenwirbelsäule: Osteochondrose L4/5.", [LWS, DEXA_L])
check("7: LWS + DEXA → kein DEXA-Teil, DEXA nicht in der Prüfzeile",
      titel(erg.report) == ["Lendenwirbelsäule in 2 Ebenen"] and not pruef(erg)
      and not any("Densitometrie" in h for h in erg.cas_hinweise), (titel(erg.report), erg.cas_hinweise))

# ── 8: Regel-Register: neue Regel da, alte als ersetzt markiert (nicht still gelöscht) ──
R = {r["id"]: r for r in json.loads((ROOT / "tests" / "regel_register" / "regeln.json").read_text(encoding="utf-8"))["regeln"]}
check("8: Regel georg-nicht-diktiert-streichen (26.11.) eingetragen, georg-nicht-diktiert-normal „ersetzt“",
      R.get("georg-nicht-diktiert-streichen", {}).get("datum") == "2026-11-26"
      and R.get("georg-nicht-diktiert-normal", {}).get("status") == "ersetzt", "")

print("\n" + ("✅ alles grün" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
