"""Gate v3.15.5 (Peter 15.10.2026: „Fibroostosen, Exostosen, Spondylosen usw. können in praktisch jeder Knochenregion
auftreten.“): systematische Widerspruchs-Prüfung Pathologie ↔ Normalsatz über ALLE Skelett-Vorlagen (templates.json,
inkl. CT/MR-Skelett und Prothesen) und die Ordi-Bausteine mit Skelett-Normaltext.

Automatische Matrix Vorlage × passender Befund aus dem Katalog (vorlagen_vorrang.json „widersprueche“):
  1. Diktat „<Vorlage>: <Befund an einer Stelle dieser Region>, ansonsten unauffällig“ → der Befund wird erkannt.
  2. Ungünstigster Fall der KI: Vorlage WÖRTLICH übernommen + Befundsatz angehängt + Normal-Ergebnis der Vorlage.
  3. widersprueche_bereinigen → kein widersprechender Normalsatz bleibt uneingeschränkt stehen, der Befund steht im
     Befundtext, der übrige Normaltext bleibt Zeichen für Zeichen, das Ergebnis nennt den Befund und behauptet keine
     „Regelrechte Darstellung“.
  4. Gegenprobe je Vorlage ohne Befund (bzw. mit verneintem Befund): Normaltext Zeichen für Zeichen unverändert.
  5. Dieselben Fälle durch die Web-Engine (befundRegeln.ts, Node): gleiche Ausgabe (EXE = Web).
Ergebnis-Tabelle (Vorlagen × Kategorien: ✓ Widerspruch erkannt + bereinigt, – kein widersprechender Normalsatz in der
Vorlage (Ergebnis trotzdem geprüft), ✗ Fehler) → docs/widerspruch_matrix.md.
Aufruf: /usr/bin/python3 tests/offline/widerspruch_matrix_test.py [--ohne-web]"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import cas_vorlagen as cv  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
B = json.loads((ROOT / "ordi_bausteine.json").read_text(encoding="utf-8")).get("bausteine") or {}
D = br._vorrang_laden()
KAT = {k["id"]: k for k in D["widersprueche"]["kategorien"]}

# Befund an einer Stelle der Region (synthetisch). Schlüssel = Region aus cas_vorlagen.regionen() bzw. eigene
ORTE = {
    "huefte": {"am": "am Trochanter major", "im": "im Schenkelhals", "des": "des Schenkelhalses",
               "arthrose": "geringgradige Coxarthrose", "osteophyt": "Osteophyt am Pfannenerker",
               "chondro": "Chondrokalzinose des Hüftgelenkes"},
    "becken": {"am": "am Tuber ischiadicum", "im": "im Os ilium", "des": "des oberen Schambeinastes",
               "arthrose": "geringgradige ISG-Arthrose", "osteophyt": "Osteophyt am Iliosakralgelenk"},
    "oberschenkel": {"am": "am Trochanter major", "im": "im Femurschaft", "des": "des Femurschaftes",
                     "arthrose": "geringgradige Coxarthrose"},
    "knie": {"am": "am Patellaoberpol", "im": "im Tibiakopf", "des": "des Tibiakopfes",
             "arthrose": "geringgradige Gonarthrose", "osteophyt": "Osteophyt am Patellaoberpol",
             "chondro": "Chondrokalzinose der Menisken"},
    "unterschenkel": {"am": "an der Tuberositas tibiae", "im": "im Tibiaschaft", "des": "des Tibiaschaftes",
                      "arthrose": "geringgradige Arthrose des oberen Sprunggelenkes"},
    "sprunggelenk": {"fibro": "dorsaler Fersensporn", "am": "am Malleolus medialis", "im": "im Talus",
                     "des": "des Malleolus lateralis", "arthrose": "geringgradige Arthrose des oberen Sprunggelenkes",
                     "osteophyt": "Osteophyt an der ventralen Tibiakante", "akz": "Os trigonum"},
    "fuss": {"fibro": "plantarer Fersensporn", "am": "am Calcaneus", "im": "im Calcaneus", "des": "des Os metatarsale V",
             "arthrose": "Arthrose des Großzehengrundgelenkes", "osteophyt": "Osteophyt am Großzehengrundgelenk",
             "akz": "Os tibiale externum"},
    "schulter": {"am": "am Tuberculum majus", "im": "im Humeruskopf", "des": "der Clavicula",
                 "arthrose": "geringgradige Omarthrose", "osteophyt": "Osteophyt am unteren Glenoidrand",
                 "verkalkung": "Tendinosis calcarea der Supraspinatussehne", "chondro": "Chondrokalzinose des Schultergelenkes"},
    "oberarm": {"am": "am Epicondylus lateralis", "im": "im Humerusschaft", "des": "des Humerusschaftes",
                "arthrose": "geringgradige Omarthrose"},
    "ellbogen": {"am": "am Olecranon", "im": "im Radiusköpfchen", "des": "des Radiusköpfchens",
                 "arthrose": "geringgradige Ellbogengelenksarthrose", "osteophyt": "Osteophyt am Processus coronoideus"},
    "unterarm": {"am": "am Processus styloideus ulnae", "im": "im distalen Radius", "des": "des distalen Radius",
                 "arthrose": "geringgradige Radiokarpalarthrose"},
    "hand": {"am": "am Processus styloideus ulnae", "im": "im Os scaphoideum", "des": "des Os metacarpale V",
             "arthrose": "geringgradige Rhizarthrose", "osteophyt": "Osteophyt am Daumensattelgelenk",
             "akz": "Sesambein am Daumengrundgelenk", "chondro": "Chondrokalzinose des Discus triangularis"},
    "hws": {"fibro": "Fibroostose an den Dornfortsätzen", "im": "im Wirbelkörper C4", "des": "des Wirbelkörpers C6",
            "spondylose": "Spondylose C4 bis C6", "osteochondrose": "Osteochondrose C5/6",
            "spondylarthrose": "Spondylarthrose C3/4", "unkovertebralarthrose": "Unkovertebralarthrose C5/6",
            "skoliose": "Streckhaltung der HWS"},
    "bws": {"fibro": "Fibroostose an den Dornfortsätzen", "im": "im Wirbelkörper Th8", "des": "des Wirbelkörpers Th12",
            "spondylose": "Spondylose Th6 bis Th9", "osteochondrose": "Osteochondrose Th7/8",
            "spondylarthrose": "Spondylarthrose Th10/11", "dish": "DISH der BWS",
            "skoliose": "flachbogige rechtskonvexe Skoliose"},
    "lws": {"fibro": "Fibroostose an den Dornfortsätzen", "im": "im Wirbelkörper L3", "des": "des Wirbelkörpers L1",
            "spondylose": "Spondylose L3 bis L5", "osteochondrose": "Osteochondrose L4/5",
            "spondylarthrose": "Spondylarthrose L5/S1", "baastrup": "Baastrup L4/5", "dish": "DISH der LWS",
            "skoliose": "flachbogige linkskonvexe Skoliose"},
    "schaedel": {"exostose": "Exostose an der Protuberantia occipitalis externa", "im": "in der Schädelkalotte",
                 "des": "des Nasenbeins", "sklerose": "Hyperostosis frontalis interna"},
    "kiefer": {"arthrose": "Kiefergelenksarthrose", "im": "im Unterkiefer", "des": "des Unterkiefers"},
    "thorax": {"am": "an der 5. Rippe", "im": "in der 5. Rippe", "des": "der 6. Rippe rechts"},
}
# Reihenfolge, falls eine Vorlage mehrere Regionen nennt (die genaueste zuerst)
REGION_REIHE = ["hws", "bws", "lws", "huefte", "knie", "sprunggelenk", "fuss", "ellbogen", "hand", "schulter",
                "oberschenkel", "unterschenkel", "oberarm", "unterarm", "becken", "kiefer", "schaedel", "thorax"]
GELENK = {"huefte", "becken", "knie", "sprunggelenk", "fuss", "schulter", "ellbogen", "hand", "kiefer"}
WIRBEL = {"hws", "bws", "lws"}


def region(key, name):
    r = cv.regionen(f"{key} {name}")
    if "ws" in r or {"hws", "bws", "lws"} <= r:
        r |= {"hws", "bws", "lws"}
    for x in REGION_REIHE:
        if x in r:
            return x
    if "abdomen" in r:
        return "lws"                     # Abdomen/Urogramm: mitabgebildete LWS
    return None


def befunde_fuer(reg):
    o = ORTE[reg]
    out = []
    if reg in WIRBEL:
        out += [("fibroostose", o["fibro"])]
        for k in ("spondylose", "osteochondrose", "spondylarthrose", "unkovertebralarthrose", "baastrup", "dish", "skoliose"):
            if k in o:
                out.append((k, o[k]))
    elif reg == "schaedel":
        out += [("exostose", o["exostose"]), ("sklerose", o["sklerose"])]
    elif reg != "kiefer":
        out.append(("fibroostose", o.get("fibro") or f"Fibroostose {o['am']}"))
        out.append(("exostose", f"kartilaginäre Exostose {o.get('am', o['im'])}"))
    out += [("enostose", f"Enostose {o['im']}"), ("zyste", f"kleine Knochenzyste {o['im']}"),
            ("fraktur", f"alte konsolidierte Fraktur {o['des']}"), ("osteopenie", "Osteopenie")]
    if reg not in WIRBEL and reg not in ("schaedel", "kiefer"):
        out.append(("fehlstellung", f"alte Fraktur {o['des']} in leichter Fehlstellung verheilt"))
        out.append(("verkalkung", o.get("verkalkung") or f"periartikuläre Verkalkung {o.get('am', o['im'])}"))
    if reg in GELENK:
        out.append(("arthrose", o["arthrose"]))
        if "osteophyt" in o:
            out.append(("osteophyt", o["osteophyt"]))
        if "chondro" in o:
            out.append(("chondrokalzinose", o["chondro"]))
    if "akz" in o:
        out.append(("accessorium", o["akz"]))
    if reg not in ("schaedel",):
        out.append(("sklerose", f"umschriebene Sklerose {o['im']}"))
    return out


def vorlagen():
    out = []
    for key, v in T.items():
        body = "\n".join((v.get("body") or "").split("\n")[1:]).strip()
        if br.ist_skelett_text(body):
            out.append((key, v.get("display_name") or key, body, v.get("ergebnis") or "Unauffälliger Befund."))
    for key, v in B.items():
        if isinstance(v, dict) and br.ist_skelett_text(v.get("befund") or ""):
            name = (v.get("titel") or v.get("name") or key).strip() or key
            out.append(("baustein:" + key, name, (v.get("befund") or "").strip(),
                        (v.get("ergebnis") or "Unauffälliger Befund.").strip()))
    return out


def befund_teil(report):
    z = report.split("\n")
    for a, e in br._abschnitt(z, "befund"):
        return "\n".join(z[a:e])
    return ""


def ergebnis_teil(report):
    return report.split("## Ergebnis", 1)[1] if "## Ergebnis" in report else ""


def fall(key, name, body, ergebnis, kid, phrase):
    diktat = f"{name}: {phrase}, ansonsten unauffällig"
    befunde = br.widerspruch_befunde(diktat)
    probleme = []
    if kid not in [b["id"] for b in befunde]:
        probleme.append(f"Befund nicht erkannt ({[b['id'] for b in befunde]})")
    vorher = br.widerspruch_saetze(body, befunde)
    satz = br._satz_aus_phrase(phrase)
    absatz = body.find("\n\n")
    roh_body = (body[:absatz] + " " + satz + body[absatz:]) if absatz > 0 else (body + " " + satz)
    report = f"## {name}\n\n## Befund\n{roh_body}\n\n## Ergebnis\n{ergebnis}"
    neu, _aend = br.widersprueche_bereinigen(report, diktat)
    bt = befund_teil(neu)
    rest = br.widerspruch_saetze(bt, befunde)
    if rest:
        probleme.append("Widerspruch übrig: " + " | ".join(bt[a:e][:60] for a, e, _ in rest))
    c = br._wid()
    k = next(x for x in c["kat"] if x["id"] == kid)
    if not br._nennt(bt.lower(), k, c):
        probleme.append("Befund fehlt im Befundtext")
    geaendert = {(a, e) for a, e, _ in vorher}
    for a, e in br.saetze_mit_lage(body):
        if (a, e) not in geaendert and body[a:e] not in bt:
            probleme.append("Normaltext verändert: " + body[a:e][:60])
    et = ergebnis_teil(neu)
    if not (br._nennt(et.lower(), k, c) or re.search(KAT[kid].get("ergebnis") or "$^", et.lower())):
        probleme.append("Ergebnis nennt den Befund nicht")
    if br._WID_NORMAL_ERG.search(et):
        probleme.append("Ergebnis behauptet Normalbefund")
    return {"key": key, "kategorie": kid, "diktat": diktat, "report": report, "neu": neu,
            "status": "✗" if probleme else ("✓" if vorher else "–"), "probleme": probleme,
            "widersprueche": [body[a:e] for a, e, _ in vorher]}


def gegenprobe(key, name, body, ergebnis):
    report = f"## {name}\n\n## Befund\n{body}\n\n## Ergebnis\n{ergebnis}"
    out = []
    for diktat in (f"{name} unauffällig", f"{name}: kein Fersensporn, keine Arthrose, keine Fraktur, ohne Osteophyten"):
        neu, aend = br.widersprueche_bereinigen(report, diktat)
        out.append({"key": key, "diktat": diktat, "report": report, "neu": neu, "ok": neu == report and not aend})
    return out


def main():
    web = "--ohne-web" not in sys.argv
    faelle, gegen, ohne_region = [], [], []
    for key, name, body, ergebnis in vorlagen():
        reg = region(key, name)
        gegen += gegenprobe(key, name, body, ergebnis)
        if reg is None:
            ohne_region.append(key)
            continue
        for kid, phrase in befunde_fuer(reg):
            faelle.append(fall(key, name, body, ergebnis, kid, phrase))
    fails = [f for f in faelle if f["status"] == "✗"] + [g for g in gegen if not g["ok"]]
    # EXE = Web: dieselben Diktate/Rohbefunde durch befundRegeln.ts
    web_fehler = []
    if web:
        eingabe = [{"report": f["report"], "diktat": f["diktat"]} for f in faelle] + \
                  [{"report": g["report"], "diktat": g["diktat"]} for g in gegen]
        p = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", "widerspruch_matrix.mjs"],
                           input=json.dumps(eingabe, ensure_ascii=False), capture_output=True, text=True,
                           cwd=ROOT / "web_app", timeout=180)
        if p.returncode != 0:
            web_fehler.append(f"Node-Fehler: {p.stderr[-800:]}")
        else:
            aus = json.loads(p.stdout)
            soll = [f["neu"] for f in faelle] + [g["neu"] for g in gegen]
            for i, (a, s) in enumerate(zip(aus, soll)):
                if a != s:
                    web_fehler.append(f"Fall {i}: Web ≠ EXE\n--- EXE\n{s}\n--- Web\n{a}")
            if len(aus) != len(soll):
                web_fehler.append(f"Anzahl Web {len(aus)} ≠ EXE {len(soll)}")
    # Tabelle Vorlagen × Kategorien
    kats = [k for k in KAT if any(f["kategorie"] == k for f in faelle)]
    keys = list(dict.fromkeys(f["key"] for f in faelle))
    zelle = {(f["key"], f["kategorie"]): f["status"] for f in faelle}
    kopf = "| Vorlage | " + " | ".join(kats) + " |"
    zeilen = ["# Widerspruchs-Matrix (v3.15.5) — Vorlagen × Befund-Kategorien", "",
              "Automatisch erzeugt von `tests/offline/widerspruch_matrix_test.py`. ✓ = widersprechender Normalsatz der "
              "Vorlage erkannt und nach der KI eingeschränkt (Befund im Befundtext, Ergebnis nennt ihn), – = die Vorlage "
              "hat für diesen Befund keinen widersprechenden Normalsatz (Ergebnis trotzdem geprüft), ✗ = Fehler, leer = "
              "Kategorie passt nicht zur Region. Gegenprobe je Vorlage (ohne bzw. mit verneintem Befund): Text Zeichen für "
              "Zeichen unverändert.", "",
              f"**{len(keys)} Vorlagen/Bausteine · {len(faelle)} Kombinationen · ✓ {sum(f['status'] == '✓' for f in faelle)} "
              f"· – {sum(f['status'] == '–' for f in faelle)} · ✗ {sum(f['status'] == '✗' for f in faelle)} · Gegenproben "
              f"{sum(g['ok'] for g in gegen)}/{len(gegen)} unverändert · Web = EXE: "
              f"{'ja' if web and not web_fehler else ('nicht geprüft' if not web else 'NEIN')}**", "",
              kopf, "|---|" + "---|" * len(kats)]
    for k in keys:
        zeilen.append(f"| {k} | " + " | ".join(zelle.get((k, c), "") for c in kats) + " |")
    if ohne_region:
        zeilen += ["", "Ohne Region (nur Gegenprobe): " + ", ".join(ohne_region)]
    zeilen += ["", "## Beispiele (Diktat → Normalsätze, die eingeschränkt werden)", ""]
    for f in faelle:
        if f["key"] in ("calcaneus_in_2_ebenen", "hüftgelenk_in_2_ebenen", "beckenübersicht_stehend",
                        "ellbogengelenk_in_2_ebenen", "kniegelenk_in_2_ebenen") and f["kategorie"] in ("fibroostose", "osteophyt"):
            zeilen.append(f"- `{f['key']}` · {f['diktat']}: " + (" / ".join(f"„{s.strip()}“" for s in f["widersprueche"])
                                                                   or "–"))
    (ROOT / "docs" / "widerspruch_matrix.md").write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    for f in fails[:40]:
        print("❌", f.get("key"), f.get("kategorie", "Gegenprobe"), f.get("probleme") or f.get("diktat"))
    for w in web_fehler[:5]:
        print("❌", w[:1500])
    print(f"Matrix: {len(keys)} Vorlagen, {len(faelle)} Fälle, ✓ {sum(f['status'] == '✓' for f in faelle)}, "
          f"– {sum(f['status'] == '–' for f in faelle)}, ✗ {sum(f['status'] == '✗' for f in faelle)}; "
          f"Gegenproben {sum(g['ok'] for g in gegen)}/{len(gegen)}; Web {'=' if web and not web_fehler else '≠/–'} EXE")
    ok = not fails and not web_fehler
    print("✅ WIDERSPRUCH-MATRIX PASS" if ok else "❌ WIDERSPRUCH-MATRIX FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
