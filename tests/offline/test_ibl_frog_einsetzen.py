"""Gate kaiscribe-frog-einsetzen-n1 – IB Lab FROG kommt in den Befund, auch mit einer alten Brücke (Georg Riegler 19.11.2026,
RH 127 „keine Werte“; „Teste das immer ob es funktioniert“).
Befund: KaiScribe 3.19.13 fand den FROG-Baustein (Fuß beidseits), setzte aber 0 Zeilen ein, nur Hinweise. Ursache: am
Befund-PC lief noch die Brücke 2.5.15 – sie reicht das Feld „befundtext“ (FROG ab Brücke 2.5.20, HIPPO ab 2.5.22) nicht
durch; ohne die Sätze fiel KaiScribe in den alten Weg und verwarf die Begriffe („Ergebnis unauffällig“). Dazu hatte die KI
bei beidseitiger CAS-Leistung „Das Fußskelett ist beidseits nach Form …“ geschrieben – dieser Satz wurde nicht erkannt.
Fix: ibl_bausteine.text_nachladen holt den Text aus der Abholer-Ablage (gleiche AccNo + Fassung) + sichtbarer Hinweis;
die Vorlagensätze werden auch mit „beidseits“ erkannt.
Teil 1: der Fall vom 19.11. (snapshots/frog_1911_beidseits.json, mit ris-mods aus den echten Winkeln erzeugt, Nummer
        erfunden) – alte Brücke, alte Brücke + Ablage, neue Brücke, KI-Text mit „beidseits“, Normalbefund ohne KI.
Teil 2: echte anonyme Fälle (snapshots/frog10_bausteine.json): einseitig, beidseits, Vorfuß – Text steht im Befund,
        über die alte Brücke + Ablage Wort für Wort wie über die neue.
Teil 3: Nachladen nur, wenn es passt (Fassung, Datei, „aus“, AccNo, schon Text, FROG ohne Pathologie) + HIPPO.
Keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_ibl_frog_einsetzen.py"""
import copy, json, os, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402,F401

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import cas_vorlagen as cv  # noqa: E402
import ibl_bausteine as I  # noqa: E402
import pipeline as pl  # noqa: E402

HIER = pathlib.Path(__file__).resolve().parent
T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DISPLAY = [v.get("display_name", "") for v in T.values()]
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
F19 = json.loads((HIER / "snapshots" / "frog_1911_beidseits.json").read_text(encoding="utf-8"))
F10 = {f["nr"]: f for f in json.loads((HIER / "snapshots" / "frog10_bausteine.json").read_text(encoding="utf-8"))["faelle"]}
HIPPO = json.loads((HIER / "hippo_bausteine.json").read_text(encoding="utf-8"))
SCHLUSS = "Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen."
KLEINZEHE = "Varusstellung der Kleinzehe beidseits mit einem Metatarsophalangealwinkel V von rechts 17° und links 13°."
fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else f"\n{detail}\n")
    fails += 0 if ok else 1


def L(kurz, text, vorlage, seite):
    return {"kurz": kurz, "text": text, "appc": "", "modalitaet": "Röntgen", "seite": seite, "vorlage": vorlage,
            "ohne_vorlage": False, "bekannt": True, "ziffer": 1}


CAS = {"fussl": L("fussl", "Fuß li.", "fuß_in_2_ebenen", "links"),
       "fuss2": L("fuss2", "Fuß bds.", "fuß_in_2_ebenen", "beidseits"),
       "vofu2": L("vofu2", "Vorfuß bds.", "vorfuß_in_2_ebenen", "beidseits")}
TITEL = {"fussl": "Fuß links in 2 Ebenen", "fuss2": "Fuß beidseits in 2 Ebenen", "vofu2": "Vorfuß beidseits in 2 Ebenen"}


def ki_text(code):
    """KI-Attrappe: Vorlage mit Überschrift; bei beidseits wie die KI am 19.11. „… ist beidseits nach Form …“."""
    v = T[CAS[code]["vorlage"]]
    body = v["body"].split("\n", 2)[2]
    erg = v["ergebnis"].rstrip(".")
    if CAS[code]["seite"] == "beidseits":
        body = (body.replace("Das Fußskelett ist nach", "Das Fußskelett ist beidseits nach")
                .replace("ist ordnungsgemäß.", "ist beidseits ordnungsgemäß."))
        erg += " beidseits"
    else:
        erg += " " + CAS[code]["seite"]
    return f"## {TITEL[code]}\n\n## Befund\n{body}\n\n## Ergebnis\n{erg}."


def lauf(liste, code, diktat=None, ki=True):
    leistung = CAS[code]
    ctx = pl.Kontext(templates=T, display_names=DISPLAY, prompt=PROMPT, llm=lambda p: ki_text(code), log=lambda *a: None,
                     cas=cv.CasHinweis([leistung], T), ibl=I.IblKontext(I.aus_liste(liste), cas_leistungen=[leistung]))
    nennung = TITEL[code].replace(" in 2 Ebenen", "")
    return pl.befund_aus_diktat(diktat or (f"{nennung}." if ki else f"{nennung} unauffällig."), ctx)


def ablage(*dateien):
    t = tempfile.mkdtemp(prefix="ibl_ablage_")
    for d in dateien:
        pathlib.Path(t, f"{d['accession_number']}_{d['modul']}.json").write_text(json.dumps(d, ensure_ascii=False),
                                                                                encoding="utf-8")
    return t


def abholer_datei(b):
    """Abholer-Datei (Format der Ablage) zu einem Baustein der neuen Brücke – das Feld „befundtext“ steht dort unter
    vorbefund.befundtext.<modul> (ris-mods ibl/vorbefund.py)."""
    return {"format": I.ABLAGE_FORMAT, "accession_number": b["accno"], "modul": b["modul"], "version": b["version"],
            "vorbefund": {"befundteil": b["befundteil"], "ergebnis_punkte": b["ergebnis"],
                          "befundtext": {b["modul"]: dict(b["befundtext"], format=1)}}}


def ohne_text(b):
    return {k: v for k, v in copy.deepcopy(b).items() if k != "befundtext"}


def befund_teil(report):
    return report.split("## Befund\n", 1)[1].split("\n## Ergebnis", 1)[0].strip()


def ergebnis_teil(report):
    return report.split("## Ergebnis\n", 1)[1].strip()


# ───────────────────────────── Teil 1: der Fall vom 19.11.2026 ─────────────────────────────
ALT, NEU, DATEI = F19["bruecke_alt"], F19["bruecke_neu"], F19["abholer_datei"]
check("Fixture: alte Brücke ohne „befundtext“, neue mit; Abholer-Datei mit dem Text (anonym, Nummer erfunden)",
      "befundtext" not in ALT and NEU["befundtext"]["stellung"] == [KLEINZEHE] and DATEI["accession_number"].startswith("999")
      and DATEI["vorbefund"]["befundtext"]["frog"]["stellung"] == [KLEINZEHE], json.dumps(NEU, ensure_ascii=False)[:300])

e = lauf([ALT], "fuss2")
check("so war es am 19.11.: alte Brücke → 0 Zeilen, nur Hinweise (Fehler nachgestellt)",
      len(e.ibl.zeilen) == 0 and KLEINZEHE not in e.report and "Digitus" not in e.report, e.report)
check("… dazu jetzt ein klarer Hinweis auf die veraltete Brücke", any("Brücke an diesem PC veraltet" in h and "nicht eingesetzt" in h
      for h in I.anzeige_hinweise(I.aus_liste([ALT]))), I.anzeige_hinweise(I.aus_liste([ALT])))

SOLL_BEFUND = (KLEINZEHE + " Das Fußgewölbe ist regulär ausgebildet. Mineralgehalt und Knochenstruktur sind regelrecht.")
SOLL_ERG = f"Digitus quintus varus beidseits.\n\n{I.ANMERKUNG}{SCHLUSS}"   # Punkt 9 (Georg 20.11.2026): „Anmerkung: …“-Block
neu = lauf([NEU], "fuss2")
check("neue Brücke, KI schreibt „Das Fußskelett ist beidseits nach Form …“: Satz ersetzt (nicht am Ende angehängt)",
      befund_teil(neu.report).startswith(SOLL_BEFUND) and "ist beidseits nach Form" not in neu.report
      and not any("nicht gefunden" in h for h in neu.ibl.hinweise), neu.report + "\n" + str(neu.ibl.hinweise))
check("… Ergebnis: Begriff zuerst, Standardsatz weg, Schlussanmerkung unten ohne Nummer",
      ergebnis_teil(neu.report) == SOLL_ERG and "Regelrechte Darstellung" not in neu.report, neu.report)

liste, geholt = I.text_nachladen([copy.deepcopy(ALT)], ablage(DATEI))
check("alte Brücke + Ablage: Text nachgeladen", geholt == ["FROG v3"] and liste[0].get("befundtext_quelle") == "ablage", geholt)
mit = lauf(liste, "fuss2")
check("… derselbe Befund Wort für Wort wie mit der neuen Brücke", mit.report == neu.report and len(mit.ibl.zeilen) == 4,
      mit.report)
check("… sichtbarer Hinweis „Text aus der IB-Lab-Ablage geholt – Brücke veraltet“",
      any("aus der IB-Lab-Ablage geholt" in h for h in I.anzeige_hinweise(I.aus_liste(liste))))
check("… Gate: jede eingesetzte Zeile wörtlich im Befund", not I.gate(mit.report, mit.ibl.zeilen), I.gate(mit.report, mit.ibl.zeilen))
nb = lauf(liste, "fuss2", ki=False)
check("Normalbefund ohne KI (Diktat „Fuß beidseits unauffällig.“): FROG-Satz + Begriff im Befund",
      KLEINZEHE in befund_teil(nb.report) and ergebnis_teil(nb.report) == SOLL_ERG
      and "Das Fußskelett ist" not in nb.report, nb.report)
for t in (neu.report, mit.report, nb.report):
    if "Norm " in t or "(Norm" in t or "[" in t or "(IB Lab FROG)" in t:
        check("FROG-Wortlaut: keine Normbereiche, keine Messzeilen", False, t)
        break
else:
    check("FROG-Wortlaut: keine Normbereiche, keine Messzeilen „… (IB Lab FROG).“", True)

# ───────────────────────────── Teil 2: einseitig, beidseits, Vorfuß ─────────────────────────────
FAELLE = [(10, "fussl", "einseitig (Fuß links, Hallux valgus)"), (7, "fuss2", "beidseits (Hallux valgus + Pes cavus)"),
          (1, "vofu2", "Vorfuß beidseits (nur d.p.)")]
for nr, code, name in FAELLE:
    b = copy.deepcopy(F10[nr]["baustein"])
    bt = I.aus_liste([b])[0].befundtext
    neu = lauf([b], code)
    liste, geholt = I.text_nachladen([ohne_text(b)], ablage(abholer_datei(b)))
    alt = lauf(liste, code)
    begriffe = [f"{x['text']} {x['seite']}".strip() for x in bt["begriffe"] if code != "vofu2" or x["art"] == "dp"]
    erg = ergebnis_teil(neu.report)
    check(f"Fall {nr} {name}: Stellungs-Sätze im Befund", all(s in befund_teil(neu.report) for s in bt["stellung"]),
          neu.report)
    check(f"Fall {nr} {name}: Begriffe als erster Ergebnispunkt, Schlussanmerkung zuletzt",
          all(t in erg.split("\n")[0] for t in begriffe) and erg.endswith(SCHLUSS)
          and "Regelrechte Darstellung" not in erg, erg)
    check(f"Fall {nr} {name}: Vorlagen-Stellungssatz ersetzt (kein Widerspruch „… Stellung … normal“)",
          "Stellung der Phalangen, Ossa metatarsalia und der Fußwurzelknochen normal" not in neu.report
          and not (bt["phalangen"] and "ist beidseits ordnungsgemäß" in neu.report), neu.report)
    check(f"Fall {nr} {name}: alte Brücke + Ablage = neue Brücke (Wort für Wort)", geholt and alt.report == neu.report,
          alt.report)
    if code == "vofu2":
        check(f"Fall {nr}: Vorfuß ohne Gewölbe-Text/-Begriffe", "Längsgewölbe" not in neu.report
              and "Pes " not in neu.report and "Fußgewölbe" not in neu.report, neu.report)
    if nr == 7:
        check("Fall 7: Gewölbe-Satz ersetzt den Vorlagen-Gewölbesatz", bt["gewoelbe"][0] in befund_teil(neu.report)
              and "bei ordnungsgemäßen Gelenkwinkeln" not in neu.report, neu.report)

# ───────────────────────────── Teil 3: Nachladen nur, wenn es passt ─────────────────────────────
pfad = ablage(DATEI)
for name, liste_, ab in (("andere Fassung in der Ablage", [dict(ohne_text(ALT), version=2)], pfad),
                         ("Datei fehlt", [dict(ohne_text(ALT), accno="999001190021")], pfad),
                         ("IBL_ABLAGE = aus", [ohne_text(ALT)], "aus"), ("keine Ablage", [ohne_text(ALT)], ""),
                         ("AccNo mit Pfadzeichen", [dict(ohne_text(ALT), accno="../999001190011")], pfad),
                         ("Ablage fehlt ganz", [ohne_text(ALT)], os.path.join(pfad, "weg"))):
    out, geholt = I.text_nachladen(copy.deepcopy(liste_), ab)
    check(f"kein Nachladen: {name}", geholt == [] and out == liste_, geholt)
out, geholt = I.text_nachladen([copy.deepcopy(NEU)], os.path.join(pfad, "weg"))
check("Brücke liefert den Text schon: nichts gelesen, unverändert", geholt == [] and out == [NEU])
ohne_path = dict(ohne_text(ALT), ergebnis=[])
out, geholt = I.text_nachladen([ohne_path], pfad)
check("FROG ohne Ergebnispunkte (nichts pathologisch): kein Lesen", geholt == [] and out == [ohne_path])
kaputt = tempfile.mkdtemp(prefix="ibl_kaputt_")
pathlib.Path(kaputt, f"{DATEI['accession_number']}_frog.json").write_text("{halb", encoding="utf-8")
check("halb geschriebene Datei: nichts, kein Fehler", I.text_nachladen([ohne_text(ALT)], kaputt)[1] == [])
fremd = tempfile.mkdtemp(prefix="ibl_fremd_")     # Dateiname passt, Inhalt gehört zu einer anderen AccNo
pathlib.Path(fremd, f"{DATEI['accession_number']}_frog.json").write_text(
    json.dumps(dict(DATEI, accession_number="999009999991"), ensure_ascii=False), encoding="utf-8")
check("Datei gehört zu anderer AccNo: nichts", I.text_nachladen([ohne_text(ALT)], fremd)[1] == [])
check("Rho/andere Module: nie nachgeladen", I.text_nachladen([{"accno": "999001190011", "modul": "rho", "version": 3,
                                                               "ergebnis": ["x"]}], pfad)[1] == [])

hb = copy.deepcopy(next(f["baustein"] for f in HIPPO if f["baustein"].get("befundtext")))
liste, geholt = I.text_nachladen([ohne_text(hb)], ablage(abholer_datei(hb)))
check("HIPPO (Brücke < 2.5.22): Text ebenso aus der Ablage", geholt and I.aus_liste(liste)[0].befundtext
      == I.aus_liste([hb])[0].befundtext, geholt)

# Vorlagensätze mit eingeschobener Seite (cas_beidseits: „wo nötig beidseits“)
for satz, rx in (("Das Fußskelett ist beidseits nach Form, Größe, Anzahl und Stellung der Phalangen normal.", I._FROG_STELLUNG),
                 ("Die Fußskelette sind beidseits nach Form, Größe, Anzahl und Stellung normal.", I._FROG_STELLUNG),
                 ("Das Fußgewölbe ist beidseits regulär ausgebildet bei ordnungsgemäßen Gelenkwinkeln.", I._FROG_GEWOELBE),
                 ("Die Fußgewölbe sind beidseits regulär ausgebildet.", I._FROG_GEWOELBE),
                 ("Die Stellung der Phalangen im Vergleich zu den Ossa metatarsalia ist beidseits ordnungsgemäß.",
                  I._FROG_PHALANGEN)):
    check(f"Vorlagensatz erkannt: „{satz[:60]}…“", bool(rx.fullmatch(satz)))
check("… ein diktierter Seitenbefund bleibt unberührt („Das Fußgewölbe ist rechts abgeflacht.“)",
      not I._FROG_GEWOELBE.search("Das Fußgewölbe ist rechts abgeflacht."))

# ───────────────────────────── Teil 4: EXE-Ablauf (CAS-Takt → INS) ─────────────────────────────
import time  # noqa: E402
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: False
PROMPTS = []
mod._llm_aufruf = lambda p: (PROMPTS.append(p), ki_text("fuss2"))[1]
ORDNER = tempfile.mkdtemp(prefix="rks_frog_")
NR, AID = DATEI["accession_number"][:11], "f1"
mod.CFG.ibl_ablage = ablage(DATEI)


class Band:
    def __init__(self):
        self.sichtbar, self.cfg = False, {}

    def pack(self, **k):
        self.sichtbar = True

    def pack_forget(self):
        self.sichtbar = False

    def winfo_ismapped(self):
        return self.sichtbar

    def configure(self, **k):
        self.cfg.update(k)

    def cget(self, k):
        return self.cfg.get(k, "")


class Var:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v


def schreiben(name, d):
    p = os.path.join(ORDNER, name)
    pathlib.Path(p + ".tmp").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    os.replace(p + ".tmp", p)


schreiben(mod._cas.AUFTRAG, {"protokoll": 1, "auftrag_id": AID, "nr": NR, "benutzer": "rg", "bruecke_pid": 4242,
                             "zeit": time.time(), "zeit_text": "", "testbefund": False})
schreiben(f"cas_leistungen_{AID}.json", {"protokoll": 1, "auftrag_id": AID, "nr": NR, "roh": "Datenbank: fuss2",
                                        "leistungen": [CAS["fuss2"]]})
schreiben(f"cas_ibl_{AID}.json", {"protokoll": 1, "auftrag_id": AID, "nr": NR, "quelle": "ibl-abholer/1",
                                 "bausteine": [ALT], "zeit": time.time()})
S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
app = S.baue_app(mod)
app._cas, app._cas_aufnahmen, app._cas_test = None, [], False
app._cas_kanal = mod._cas.Kanal(ORDNER, pid=777, version="3.19.14", prozess_lebt=lambda pid: True)
app._fensterziel = mod._fz.Fensterziel(None)
app.cas_label, app.cas_hinweis_label, app.bestaetigung_label = S.FakeWidget(), S.FakeWidget(), S.FakeWidget()
app.cas_band, app.bestaetigung_band, app.main_container = Band(), Band(), None
app.ibl_label, app.ibl_hinweis_label, app.ibl_zeile, app.ibl_knopf = Band(), Band(), Band(), Band()
app.ibl_var = Var(True)
app.destroy = lambda: None
app._lauf_protokollieren = lambda *a, **k: None       # kein X: im Test
app._cas_einmal()
app._cas_einmal()                                     # 1. Takt: Auftrag, 2. Takt: IB-Lab-Datei
bs = app._ibl_bausteine()
check("EXE: Brücken-Datei ohne Text → KaiScribe holt ihn beim CAS-Takt aus der Ablage",
      len(bs) == 1 and bs[0].befundtext is not None and bs[0].text_aus_ablage, [vars(b) for b in bs])
app.transcript_text.text = "Fuß beidseits."
app.befund_aus_text(kontrolle=True)
S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", 8)
S.pump(app, lambda: False, 0.2)
r = app.result_text.text
check("EXE: INS → Kleinzehen-Satz im Befund, „Digitus quintus varus beidseits.“ als Ergebnis, Schlussanmerkung",
      KLEINZEHE in r and "Digitus quintus varus beidseits." in r and r.rstrip().endswith(SCHLUSS)
      and "Regelrechte Darstellung" not in r, r)
check("EXE: Hinweis „Brücke an diesem PC veraltet“ sichtbar", "Brücke an diesem PC veraltet"
      in " ".join(getattr(app, "_ibl_hinweise", [])), getattr(app, "_ibl_hinweise", []))

print(f"\nFEHLER: {fails}")
sys.exit(1 if fails else 0)
