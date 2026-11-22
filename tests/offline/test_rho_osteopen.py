"""Gate kaiscribe-rho-osteopen-n1 (Georg 22.11.2026): Rho-Score ≥ 7 → „Osteopenischer Knochenaspekt.“ statt des
Mineralisations-Normalsatzes – in ALLEN Untersuchungen des Auftrags („Überall ersetzen“), über die ganze EXE-Kette
(KI-Attrappe mit den echten Vorlagen aus templates.json, CAS-Leistungen, IB-Lab-Baustein). Die Textregel selbst
(EXE = Web) prüft befund_regeln_test.py (Fixtures „rho“ → „osteopen“).
  Score 6 → bleibt · 7 → ersetzt, kein Doppel · Mehrfach LWS + Becken Score 8 → beide · Diktat „Osteopenie“ → nichts ·
  Rho gesperrt (DEXA < 2 J: KaiScribe setzt keinen Rho-Text, IB-Lab-Rho ist nur Anzeige) → nichts · Ergebnis bleibt ·
  Vorlagen: jede Röntgen-Vorlage mit Mineralisations-Normalsatz wird erfasst.
Keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_rho_osteopen.py"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402,F401

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import cas_vorlagen as cv  # noqa: E402
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
O = br.OSTEOPEN_SATZ
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def L(kurz, text, vorlage, seite, ziffer=1):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": "Röntgen", "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True, "ziffer": ziffer}


def vorlage_report(key, titel):
    v = T[key]
    return f"## {titel}\n\n## Befund\n{v['body'].split(chr(10), 2)[2]}\n\n## Ergebnis\n{v['ergebnis']}"


def kontext(llm, leistungen=None, bausteine=None, log=None):
    cas = cv.CasHinweis(leistungen, T) if leistungen else None
    ibl = I.IblKontext(I.aus_liste(bausteine), cas_leistungen=leistungen) if bausteine else None
    return pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=llm, log=log or (lambda *a: None),
                      cas=cas, ibl=ibl)


def teil(report, titel):
    return report.split(f"## {titel}", 1)[1].split("\n\n\n## ", 1)[0]


def befund_teil(report, titel):
    return teil(report, titel).split("## Befund\n", 1)[1].split("## Ergebnis", 1)[0]


def mineral_normal(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if br._osteo_normal(s)]


LWS = L("lws", "LWS", "lendenwirbelsäule_in_2_ebenen", None, ziffer=1)
BUE = L("bü", "Beckenübersicht", "beckenübersicht_stehend", None, ziffer=2)
T_LWS, T_BUE = "Lendenwirbelsäule in 2 Ebenen", "Beckenübersicht stehend"


def ki_lws_bue(p):
    if "<untersuchung>Beckenübersicht" in p:
        return vorlage_report("beckenübersicht_stehend", T_BUE)
    return vorlage_report("lendenwirbelsäule_in_2_ebenen", T_LWS)


check("Vorlagen: LWS und Becken haben einen Mineralisations-Normalsatz (sonst prüft der Test nichts)",
      mineral_normal(vorlage_report("lendenwirbelsäule_in_2_ebenen", T_LWS))
      and mineral_normal(vorlage_report("beckenübersicht_stehend", T_BUE)))

# ── Score 6 / 7 (eine Untersuchung) ──
for score, ersetzt in (("6", False), ("7", True)):
    log = []
    erg = pl.befund_aus_diktat(f"LWS: Osteochondrose L5/S1. Rho {score}.", kontext(ki_lws_bue, log=log.append))
    b = befund_teil(erg.report, T_LWS)
    if ersetzt:
        check(f"Rho {score}: „{O}“ genau einmal, kein Mineralisations-Normalsatz mehr",
              erg.report.count(O) + erg.report.count(O.lower()) == 1 and not mineral_normal(b)
              and any("[RHO] Osteopenischer Knochenaspekt" in z for z in log), erg.report)
    else:
        check(f"Rho {score}: Normalsatz bleibt, kein „{O}“", mineral_normal(b) and "osteopenisch" not in erg.report.lower()
              and br.RHO_ERGEBNIS not in erg.report, erg.report)

# ── Mehrfach LWS + Becken, Score 8: beide ersetzt, Ergebnis unverändert ──
erg = pl.befund_aus_diktat("Lendenwirbelsäule: Osteochondrose L5/S1, Rho 8. Beckenübersicht: unauffällig.",
                           kontext(ki_lws_bue, [LWS, BUE]))
ok = True
for t in (T_LWS, T_BUE):
    b = befund_teil(erg.report, t)
    ok = ok and not mineral_normal(b) and (b.count(O) + b.count(O.lower())) == 1
check("Mehrfach LWS + Becken Rho 8: in BEIDEN Teilen genau einmal ersetzt", ok, erg.report)
check("Mehrfach: Ergebnisse unverändert, Rho-Befund bleibt am Schluss",
      teil(erg.report, T_BUE).split("## Ergebnis\n", 1)[1].strip().lstrip("1. ") == T["beckenübersicht_stehend"]["ergebnis"]
      and erg.report.rstrip().endswith(br.RHO_ERGEBNIS) and "osteopen" not in erg.report.split(br.RHO_TITEL)[1].lower(),
      erg.report)

# ── Diktat geht vor ──
for d in ("LWS: Osteopenie, Osteochondrose L5/S1. Rho 8.", "LWS: Mineralgehalt vermindert. Rho 8.",
          "LWS: Osteoporose. Rho 9."):
    erg = pl.befund_aus_diktat(d, kontext(lambda p: vorlage_report("lendenwirbelsäule_in_2_ebenen", T_LWS)))
    check(f"Diktat „{d[5:25]}…“: nichts ersetzt, kein „{O}“", "osteopenischer knochenaspekt" not in erg.report.lower(),
          erg.report)

# ── Rho gesperrt / nur IB-Lab-Rho (DEXA < 2 J entscheidet der Formatierer): KaiScribe ersetzt nichts ──
RHO_IBL = {"accno": "999001220011", "ziffer": 1, "modul": "rho", "name": "Rho", "modul_name": "16 Bit Rho", "version": 1,
           "befundteil": ["Rho-Score 8 von 10 (16 Bit Rho)."], "ergebnis": [], "hinweise": ["Rho analysierte: LWS"],
           "region": "lws"}
erg = pl.befund_aus_diktat("LWS: Osteochondrose L5/S1.", kontext(ki_lws_bue, [LWS], [RHO_IBL]))
check("IB-Lab-Rho 8 ohne Rho-Text (z. B. DEXA < 2 J): Normalsatz bleibt",
      mineral_normal(befund_teil(erg.report, T_LWS)) and "osteopenisch" not in erg.report.lower(), erg.report)

# ── Restructure: zweiter Umbau bleibt bei einem Ersatz ──
erg = pl.befund_aus_diktat("LWS: Osteochondrose L5/S1. Rho 8.", kontext(ki_lws_bue))
erg2, _ = br.osteopen_ersetzen(erg.report, "")
check("Zweiter Durchlauf ändert nichts (nie doppelt)", erg2 == erg.report, erg2)

# ── Alle Röntgen-Vorlagen: Normalsatz wird erkannt (sonst bliebe er bei Rho ≥ 7 stehen) ──
fehlt = []
for key, v in T.items():
    body = v.get("body") or ""
    if cv.modalitaet_key(key, T) != "Röntgen":
        continue
    for s in re.split(r"(?<=[.!?])\s+|\n", body):
        s = s.strip()
        if re.match(r"^(?:Knochenstruktur:\s*)?(?:Die\s+)?(?:Mineralgehalt|Knochenstruktur|Knochenmineralisation)\b", s) \
                and re.search(r"regelrecht|unauffällig|normal", s) and not br._osteo_normal(s):
            fehlt.append(f"{key}: {s}")
check("Vorlagen: jeder Mineralisations-Normalsatz einer Röntgen-Vorlage wird erkannt", not fehlt, "\n".join(fehlt))

print("ALLE GRÜN" if not fails else f"{fails} ROT")
sys.exit(1 if fails else 0)
