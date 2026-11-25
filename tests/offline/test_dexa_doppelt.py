"""Gate kaiscribe-dexa-doppelt-rh60-n1 (Ursula Hofmeister 23.11.2026, RH 60): Im Kombi-Brief (Rö + DEXA) stand eine leere
KaiScribe-Vorlage „Knochendichtemessung (DEXA)“ mit „ODM – LWS: … [Wert_LWS] … [T_Wert_LWS]“ VOR dem echten DEXA-Teil.
Ursache (belegt, Nachbau unten): seit 3.19.20 (kaiscribe-georg-2011-n1, cas_vorlagen.nicht_diktiert_ergaenzen) bekommt
jede nicht diktierte CAS-Leistung mit Vorlage einen Normalbefund aus der Vorlage – die Brücke ordnet dexa/dexaneu/dxf/od/
odh der Vorlage knochendichtemessung_dexa zu → leere DEXA-Vorlage mit Platzhaltern. Zweiter Weg: detect wählte die DEXA-
Vorlage schon bei „Knochendichte“ irgendwo im Rö-Diktat (Regel 2 vor allen Regionen).
Soll (Lagebild): KaiScribe fügt NIE eine DEXA-Vorlage ein (reine DEXA → Roboter, Kombi → Office); nie ein unbefüllter
Platzhalter im Brief, sonst rote Prüfzeile. GWS a.p. + seitlich (kaiscribe-gws-seitlich-vorlage-n1) bleibt.
Synthetische Diktate, keine Patientendaten.  Aufruf: python3 tests/offline/test_dexa_doppelt.py"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import cas_vorlagen as cv  # noqa: E402
import detect  # noqa: E402
import pipeline as pl  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
DEXA = "knochendichtemessung_dexa"
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def L(kurz, text, vorlage, mod="Röntgen", seite=None):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": mod, "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True}


# wie die Praxis-Zuordnung (ris-mods katalog/kuerzel_vorlage.tsv: dexa, dexaneu, dxf, od, odh → knochendichtemessung_dexa)
OD = L("od", "Osteodensitometrie", DEXA)
DEXA_L = L("dexa", "Densitometrie", DEXA)
DXF = L("dxf", "Knochendichte inkl.Fettmessung", DEXA)
ODH = L("odh", "Knochendichte mit Hormonen", DEXA)
DEXA_UNBEKANNT = L("dexaneu", "Densitometrie", None)          # Zuordnung fehlt/unbekannt: Text genügt
LWS = L("lws2", "LWS 2 Ebenen", "lendenwirbelsäule_in_2_ebenen")
HUEFTE = L("hü", "Hüftgelenk li.", "hüftgelenk_in_2_ebenen", seite="links")
SONO_SCH = L("sosch", "Sonographie der Schulter re.", "sonografie_schultergelenk", mod="Sono", seite="rechts")
GWS = L("gws", "WS Ganzaufn. ap + stl. geteilt", "ganzaufnahme_der_wirbelsäule_a-p")


def ki_attrappe(prompts):
    def llm(p):
        prompts.append(p)
        titel = p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0]
        key = next(k for k, v in T.items() if v.get("display_name") == titel)
        body = T[key]["body"].split("\n", 1)[1] if "\n" in T[key]["body"] else ""
        return f"## {titel}\n\n## Befund\n{body}\n\n## Ergebnis\n" + (T[key].get("ergebnis") or "Unauffälliger Befund.")
    return llm


def lauf(diktat, leistungen=None):
    prompts, logs = [], []
    cas = None
    if leistungen is not None:
        h = cv.CasHinweis(leistungen, T)
        cas = h if (h or h.dexa) else None          # wie RaKScribe._cas_hinweis_fuer_lauf
    ctx = pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=ki_attrappe(prompts), log=logs.append,
                     cas=cas)
    return pl.befund_aus_diktat(diktat, ctx), prompts, logs, ctx


def ohne_dexa(erg, prompts):
    return ("Knochendichtemessung" not in erg.report and "ODM" not in erg.report and "[" not in erg.report
            and not any("<untersuchung>Knochendichtemessung" in p for p in prompts) and DEXA not in (erg.vorlagen or []))


# ───────────────────────────── 1. CAS: DEXA-Leistung ist keine Untersuchung der Vorlagenwahl ─────────────────────────────
for l in (OD, DEXA_L, DXF, ODH, DEXA_UNBEKANNT):
    c = cv.CasHinweis([LWS, l], T)
    check(f"CAS {l['kurz']} „{l['text']}“: nicht in der Vorlagenwahl, nur als DEXA-Auskunft",
          [x.kurz for x in c.alle] == ["lws2"] and c.dexa == [l["kurz"]] and DEXA not in c.vorlagen(),
          ([x.kurz for x in c.alle], c.dexa))
c = cv.CasHinweis([OD], T)
check("CAS nur DEXA: keine Vorlagenwahl nach CAS (bool False), DEXA bekannt", not c and c.dexa == ["od"])
check("Prompt-Block der Kombi nennt keine DEXA-Vorlage",
      "Knochendichte" not in cv.prompt_block(cv.CasHinweis([LWS, OD], T), T))

# ───────────────────────────── 2. Nachbau RH 60: Kombi Rö + DEXA (vorher: leere DEXA-Vorlage dazu) ─────────────────────────
erg, prompts, logs, ctx = lauf("LWS in 2 Ebenen: Osteochondrose L5/S1.", [LWS, OD])
check("Kombi LWS + DEXA (RH 60): nur der LWS-Befund, keine DEXA-Vorlage, kein Platzhalter",
      erg.vorlagen == ["lendenwirbelsäule_in_2_ebenen"] and erg.report.startswith("## Lendenwirbelsäule in 2 Ebenen")
      and erg.report.count("## Ergebnis") == 1 and ohne_dexa(erg, prompts), f"{erg.vorlagen}\n{erg.report}")
check("Kombi LWS + DEXA: kein Hinweis „Osteodensitometrie laut CAS, nicht diktiert“ (fügt das Office ein)",
      not any("Osteodensitometrie" in h or "nicht diktiert" in h for h in erg.cas_hinweise), erg.cas_hinweise)
check("Kombi LWS + DEXA: Protokoll ohne „Normalbefund der Vorlage knochendichtemessung_dexa“",
      not any(DEXA in z for z in logs), [z for z in logs if "[CAS]" in z])
check("Kombi LWS + DEXA: Rho-Regel kennt die DEXA weiter („gesperrt“)", pl._rho_dexa(ctx) == "gesperrt")

erg, prompts, _, _ = lauf("Hüftgelenk links: geringe Coxarthrose. Knochendichte vermindert.", [HUEFTE, DXF])
check("Kombi Hüfte + DEXA (dxf), Diktat mit „Knochendichte“: Hüft-Befund, keine DEXA-Vorlage",
      erg.vorlagen == ["hüftgelenk_in_2_ebenen"] and ohne_dexa(erg, prompts), f"{erg.vorlagen}\n{erg.report}")

erg, prompts, _, _ = lauf("Sonographie der rechten Schulter: Bursitis subacromialis.", [SONO_SCH, DEXA_L])
check("Kombi US Schulter + DEXA: nur der Sono-Befund, keine DEXA-Vorlage",
      erg.vorlagen == ["sonografie_schultergelenk"] and ohne_dexa(erg, prompts)
      and not any("nicht diktiert" in h for h in erg.cas_hinweise), f"{erg.vorlagen}\n{erg.report}\n{erg.cas_hinweise}")

# ───────────────────────────── 3. reine DEXA ─────────────────────────────
for diktat in ("Osteodensitometrie unauffällig.", "Knochendichtemessung (DEXA) unauffällig", "DEXA: T-Wert minus 2,6"):
    erg, prompts, _, ctx = lauf(diktat, [OD])
    check(f"reine DEXA „{diktat}“: nie die DEXA-Vorlage, kein Platzhalter", ohne_dexa(erg, prompts),
          f"{erg.vorlagen}\n{erg.report}")
check("reine DEXA: Rho-Regel „gesperrt“ (auch ohne Vorlagenwahl nach CAS)", pl._rho_dexa(ctx) == "gesperrt")
for d in ("Knochendichtemessung (DEXA) unauffällig", "Osteodensitometrie: T-Wert -2,6", "knochendichtemessung dexa o.B."):
    check(f"detect „{d}“ → nie DEXA (allgemein)", detect.detect_template(d, T) == "allgemein", detect.detect_template(d, T))

# ───────────────────────────── 4. detect: DEXA-Wörter im Rö-/US-Diktat ─────────────────────────────
for d, soll in (("LWS in 2 Ebenen: verminderte Knochendichte, Osteochondrose L5/S1.", "lendenwirbelsäule_in_2_ebenen"),
                ("Knochendichte vermindert. Osteochondrose L5/S1, Spondylose der LWS.", "lendenwirbelsäule_in_2_ebenen"),
                ("Hüftgelenk links: Coxarthrose. DEXA empfohlen.", "hüftgelenk_in_2_ebenen"),
                ("Sonographie der rechten Schulter: Bursitis subacromialis. Knochendichtemessung gesondert.",
                 "sonografie_schultergelenk")):
    check(f"detect „{d[:50]}…“ → {soll}", detect.detect_template(d, T) == soll, detect.detect_template(d, T))

# ───────────────────────────── 5. unverändert: GWS a.p. + seitlich, reiner Rö-Befund ─────────────────────────────
for name, leist in (("gws", [GWS]), ("gws + DEXA", [GWS, OD])):
    erg, prompts, _, _ = lauf("Ganzaufnahme der Wirbelsäule: Osteochondrose L5/S1.", leist)
    check(f"GWS a.p. + seitlich ({name}) → weiter „Gesamte Wirbelsäule“ mit HWS/BWS/LWS",
          erg.vorlagen == ["wirbelsäule_gesamt"] and erg.report.startswith("## Gesamte Wirbelsäule")
          and all(x in erg.report for x in ("HWS:", "BWS:", "LWS:")) and ohne_dexa(erg, prompts), erg.report)
erg, prompts, _, _ = lauf("LWS in 2 Ebenen: Osteochondrose L5/S1.")
erg2, _, _, _ = lauf("LWS in 2 Ebenen: Osteochondrose L5/S1.", [LWS])
check("reiner Rö-Befund ohne/mit CAS: LWS wie bisher, ohne Prüfzeile",
      erg.report.startswith("## Lendenwirbelsäule in 2 Ebenen") and erg.report == erg2.report
      and not erg2.cas_hinweise and "[" not in erg.report, f"{erg.report}\n{erg2.cas_hinweise}")
erg, _, _, _ = lauf("LWS in 2 Ebenen unauffällig.", [LWS])
check("Normalbefund-Bypass LWS mit CAS: Normaltext der Vorlage, ohne Prüfzeile",
      "Normale Lordose der Lendenwirbelsäule." in erg.report and not erg.cas_hinweise and "[" not in erg.report,
      f"{erg.report}\n{erg.cas_hinweise}")

# ───────────────────────────── 6. Platzhalter-Wächter ─────────────────────────────
R = ("## Knochendichtemessung (DEXA)\n\n## Befund\nODM - LWS:\nDie Knochendichtewerte gemittelt über L1 bis L4 betragen "
     "[Wert_LWS] g/cm² Calziumhydroxylapatit (entspricht einem T-Wert von [T_Wert_LWS]).\n\n## Ergebnis\nUnauffälliger Befund.")
r, z = br.platzhalter_entfernen(R)
check("Wächter: [Wert_LWS]/[T_Wert_LWS] → „…“, zwei rote Prüfzeilen",
      "[" not in r and "betragen … g/cm²" in r and len(z) == 2 and all("bitte prüfen" in x for x in z), (r, z))
S = "## Schulter\n\n## Befund\nNormale Stellung. Wert [X] beträgt. Glatte Kontur.\n\n## Ergebnis\nRegelrecht."
r, z = br.platzhalter_entfernen(S)
check("Wächter: Satz bleibt, nur der Platzhalter wird „…“",
      "Normale Stellung. Wert … beträgt. Glatte Kontur." in r and z ==
      [br.PLATZHALTER_ZEILE.format(name="Schulter", ph="[X]")], (r, z))
check("Wächter: ohne Platzhalter bit-gleich", br.platzhalter_entfernen(erg.report) == (erg.report, []))
erg, _, logs, _ = lauf("Ultraschallgezielte Blockade unauffällig.")
if "[X]" in T.get("ultraschall_gezielte_blockade", {}).get("body", ""):
    check("Kette: Vorlage mit [X] (Bypass) → „… ml“, Aufklärungssatz bleibt, rote Prüfzeile",
          "[X]" not in erg.report and "mit … ml Xylonest" in erg.report and any("Platzhalter [X]" in h for h in erg.cas_hinweise),
          f"{erg.report}\n{erg.cas_hinweise}")

# ───────────────────────────── 7. Web = EXE (Platzhalter-Wächter) ─────────────────────────────
faelle = [R, S, "## A\n\n## Befund\nx.\n\n## Ergebnis\ny.", "## B\n\n## Befund\n[Wert]\nRest.\n\n## Ergebnis\nz."]
js = ("import { platzhalterEntfernen } from './src/befundRegeln.ts';"
      "const f = JSON.parse(process.argv[1]); console.log(JSON.stringify(f.map(x => platzhalterEntfernen(x))));")
p = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", "--input-type=module", "-e", js,
                    json.dumps(faelle)], cwd=ROOT / "web_app", capture_output=True, text=True, timeout=60)
web = json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else None
exe = [list(br.platzhalter_entfernen(x)) for x in faelle]
check("Web platzhalterEntfernen = EXE platzhalter_entfernen", web == exe, f"{p.stderr[-400:]}\nweb={web}\nexe={exe}")

print(f"\n{'✅ alle grün' if not fails else f'❌ {fails} rot'}")
sys.exit(1 if fails else 0)
