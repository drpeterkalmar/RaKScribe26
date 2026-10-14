"""Gate v3.14.0 (RaK-Befund, Peter 14.10.2026): Kontext aus der Datenbank des RIS und IB-Lab-Gerüst vor dem Diktat.
Teil 1: cas_auftrag.kontext_lesen (eigener Auftrag, halb geschrieben, fremde Nummer), Kopfzeile (Zuweiser · Info, gekürzt),
        Vorbefund (nur mit Text).
Teil 2: ibl_bausteine — Ziffer exakt aus der Datenbank (statt Stelle in der Liste), auffällige Zeilen (nur wenn eine
        Regel daraus einen Ergebnispunkt machte), Gerüst (Titel der CAS-Vorlage mit Seite, sonst Region; nummeriertes
        Ergebnis; ohne Inhalt kein Gerüst).
Teil 3: EXE-Ablauf (exe_stubs): Kontext → Kopfzeile + Knopf „Vorbefund TT.MM.JJJJ“ im Band, Fenster nur lesen; IB-Lab-
        Bausteine vor dem Diktat → Gerüst im Befund-Feld, auffällige Werte markiert, Gerüst zählt nicht als Diktat (ein
        neuer Auftrag ersetzt statt abzulehnen), INS → Befund aus dem Diktat mit den Werten, F9 → Gerüst wieder.
Teil 4: Der Vorbefund (und Zuweiser/Info) gehen NIE an die KI: kein Prompt enthält sie; die Module, die Prompts bauen,
        kennen den Kontext nicht.
Synthetische Daten, keine Patientendaten.  Aufruf: /usr/bin/python3 tests/offline/test_cas_kontext.py"""
import json, os, pathlib, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exe_stubs as S  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import cas_auftrag as ca  # noqa: E402
import ibl_bausteine as I  # noqa: E402

T = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
fails = 0
VB_TEXT = "Lendenwirbelsäule\n\nZustand nach Kontrolle VORBEFUND-GEHEIMTEXT-7731.\n\nErgebnis:\nUnauffällig."


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# ───────────────────────────── Teil 1: Kontext lesen ─────────────────────────────
ORDNER = tempfile.mkdtemp(prefix="rks_kontext_")
k = ca.Kanal(ORDNER, pid=1, version="t")
a = ca.Auftrag({"auftrag_id": "k1", "nr": "20261014105", "benutzer": "kp"})


def kontext_ablegen(aid, nr, roh=None, **mehr):
    d = {"protokoll": 1, "auftrag_id": aid, "nr": nr, "quelle": "CAS-Datenbank", "zuweiser": "Dr. Max Zuweiser",
         "info": "Schmerzen seit drei Wochen, Zustand nach Sturz", "befunder": "kp",
         "vorbefund": {"nr": "20240312045", "datum": "2024-03-12", "untersuchung": "LWS", "text": VB_TEXT, "zeichen": 70,
                       "gekuerzt": False}, "zeit": time.time()}
    d.update(mehr)
    with open(os.path.join(ORDNER, f"cas_kontext_{aid}.json"), "w", encoding="utf-8") as f:
        f.write(roh if roh is not None else json.dumps(d, ensure_ascii=False))


check("kein Kontext → None", k.kontext_lesen(a) is None)
kontext_ablegen("k1", "20261014105", roh='{"auftrag_id": "k1", "nr"')
check("halb geschrieben → None (nächster Takt)", k.kontext_lesen(a) is None)
kontext_ablegen("k1", "20261099999")
check("fremde Nummer → leer (verworfen)", k.kontext_lesen(a) == {})
kontext_ablegen("k1", "20261014105")
a.kontext = k.kontext_lesen(a)
check("Kontext gelesen: Zuweiser, Info, Vorbefund", a.kontext["zuweiser"] == "Dr. Max Zuweiser"
      and a.vorbefund()["nr"] == "20240312045" and a.vorbefund()["text"] == VB_TEXT)
check("Kopfzeile „Zuweiser: … · Info: …“", a.kopfzeile() == "Zuweiser: Dr. Max Zuweiser  ·  Info: Schmerzen seit drei "
      "Wochen, Zustand nach Sturz", a.kopfzeile())
a.kontext["info"] = "x " * 80
check("lange Info gekürzt (…)", a.kopfzeile().endswith("…") and len(a.kopfzeile()) < 140, a.kopfzeile())
a.kontext = {"zuweiser": "", "info": "", "vorbefund": {"nr": "1", "text": "  "}}
check("ohne Zuweiser/Info: leere Kopfzeile; Vorbefund ohne Text → None", a.kopfzeile() == "" and a.vorbefund() is None)

# ───────────────────────────── Teil 2: Ziffer, auffällig, Gerüst ─────────────────────────────
FROG = {"accno": "T-0023", "ziffer": 3, "modul": "frog", "name": "FROG", "version": 1, "seiten": ["links"],
        "befundteil": ["Calcaneusneigungswinkel 10° (IB Lab FROG).", "Hallux-valgus-Winkel 12° (IB Lab FROG)."],
        "ergebnis": ["Pes planus links (Calcaneusneigungswinkel 10°)."]}
CAS_POS = [{"kurz": "a", "text": "LWS", "vorlage": "lendenwirbelsäule_in_2_ebenen", "seite": ""},
           {"kurz": "b", "text": "HWS", "vorlage": "halswirbelsäule_in_2_ebenen"},
           {"kurz": "c", "text": "Fuß li.", "vorlage": "fuß_in_2_ebenen", "seite": "links"}]
CAS_DB = [{"kurz": "c", "text": "Fuß li.", "vorlage": "fuß_in_2_ebenen", "seite": "links", "ziffer": 3},
          {"kurz": "a", "text": "LWS", "vorlage": "lendenwirbelsäule_in_2_ebenen", "seite": "", "ziffer": 1}]
check("Ziffer ohne Datenbank: Stelle in der Liste (wie 3.13)", I._leistung_zur_ziffer(3, CAS_POS)["kurz"] == "c")
check("Ziffer aus der Datenbank: exakt die Leistung mit dieser Ziffer (Reihenfolge egal)",
      I._leistung_zur_ziffer(3, CAS_DB)["kurz"] == "c" and I._leistung_zur_ziffer(1, CAS_DB)["kurz"] == "a"
      and I._leistung_zur_ziffer(2, CAS_DB) is None)
b = I.aus_liste([FROG])
check("auffällig: Messwert, aus dem ein Ergebnispunkt wurde, + der Punkt; ohne Regel nichts",
      I.auffaellige_zeilen(b) == ["Calcaneusneigungswinkel 10° (IB Lab FROG).",
                                  "Pes planus links (Calcaneusneigungswinkel 10°)."], I.auffaellige_zeilen(b))
e = I.geruest(b, CAS_DB, T)
check("Gerüst mit CAS-Vorlage: Titel mit Seite, Befundzeilen wörtlich, Ergebnis nummeriert",
      e.report == "## Fuß links in 2 Ebenen\n\n## Befund\nCalcaneusneigungswinkel 10° (IB Lab FROG).\n"
                  "Hallux-valgus-Winkel 12° (IB Lab FROG).\n\n## Ergebnis\n1. Pes planus links (Calcaneusneigungswinkel 10°).",
      e.report)
check("… Zeilen fürs Messwert-Gate, Stand je Baustein", I.gate(e.report, e.zeilen) == []
      and e.behandelt == {("T-0023", "frog"): 1})
e2 = I.geruest(b, None, T)
check("Gerüst ohne CAS-Leistungen: Region des Moduls mit Seite", e2.report.startswith("## Fuß links\n\n## Befund\n"),
      e2.report)
ohne = I.aus_liste([dict(FROG, ergebnis=[], befundteil=["Calcaneusneigungswinkel 24° (IB Lab FROG)."])])
e3 = I.geruest(ohne, CAS_DB, T)
check("unauffällig: Gerüst ohne „## Ergebnis“, nichts markiert", "## Ergebnis" not in e3.report
      and I.auffaellige_zeilen(ohne) == [], e3.report)
check("keine Bausteine mit Inhalt → kein Gerüst (kein Platzhalter)",
      I.geruest(I.aus_liste([dict(FROG, befundteil=[], ergebnis=[])]), CAS_DB, T) is None and I.geruest([], CAS_DB, T) is None)

# ───────────────────────────── Teil 3: EXE-Ablauf ─────────────────────────────
mod = S.lade_rakscribe()
mod.keys_ready = lambda: True
mod._get_stt_access_token = lambda: "token"
mod._fokus_ist_eigenes_fenster = lambda: False
cas_mod = mod._cas
LLM_PROMPTS = []


def ki(p):
    LLM_PROMPTS.append(p)
    titel = p.rsplit("<untersuchung>", 1)[1].split("</untersuchung>")[0]
    diktat = p.split("<diktat>\n", 1)[1].split("\n</diktat>")[0]
    return f"## {titel}\n\n## Befund\nBeschreibung laut Diktat: {diktat}\n\n## Ergebnis\nUnauffällig."


mod._llm_aufruf = ki
EXE_ORDNER = tempfile.mkdtemp(prefix="rks_kontext_exe_")


class FakeBand:
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


def ablegen(nr, aid):
    with open(os.path.join(EXE_ORDNER, cas_mod.AUFTRAG), "w", encoding="utf-8") as f:
        json.dump({"protokoll": 1, "auftrag_id": aid, "nr": nr, "benutzer": "kp", "bruecke_pid": 4242,
                   "zeit": time.time(), "zeit_text": "", "testbefund": False}, f)


ZEIT = [time.time()]


def datei(name, d):
    p = os.path.join(EXE_ORDNER, name)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    ZEIT[0] += 1
    os.utime(p, (ZEIT[0], ZEIT[0]))


S.AUFZ.tasten.clear(); S.AUFZ.dialoge.clear()
app = S.baue_app(mod)
app._cas, app._cas_aufnahmen, app._cas_test = None, [], False
app._cas_kanal = cas_mod.Kanal(EXE_ORDNER, pid=777, version="3.14.0", prozess_lebt=lambda pid: True)
app._fensterziel = mod._fz.Fensterziel(None)
app.cas_label, app.cas_hinweis_label, app.bestaetigung_label = S.FakeWidget(), S.FakeWidget(), S.FakeWidget()
app.cas_band, app.bestaetigung_band, app.main_container = FakeBand(), FakeBand(), None
app.cas_kopf_label, app.vorbefund_knopf = FakeBand(), FakeBand()
app.ibl_label, app.ibl_hinweis_label, app.ibl_zeile, app.ibl_knopf = FakeBand(), FakeBand(), FakeBand(), FakeBand()
app.ibl_var = Var(True)
app.destroy = lambda: None


def bis_ruhe(timeout=8):
    S.pump(app, lambda: app._job.zustand in ("READY", "ERROR") and app._status_raw != "PROCESSING", timeout)
    S.pump(app, lambda: False, 0.2)


ablegen("20261014105", "x1")
app._cas_einmal()
check("Auftrag ohne Kontext: keine Kopfzeile, kein Vorbefund-Knopf", app._cas is not None
      and not app.cas_kopf_label.sichtbar and not app.vorbefund_knopf.sichtbar)
datei("cas_kontext_x1.json", {"protokoll": 1, "auftrag_id": "x1", "nr": "20261014105", "zuweiser": "Dr. Max Zuweiser",
                              "info": "Sturz", "vorbefund": {"nr": "20240312045", "datum": "2024-03-12",
                                                             "untersuchung": "LWS", "text": VB_TEXT}})
app._cas_einmal()
check("Kontext kommt: Kopfzeile + Knopf „Vorbefund 12.03.2024“, Band höher",
      app.cas_kopf_label.sichtbar and app.cas_kopf_label.cget("text") == "Zuweiser: Dr. Max Zuweiser  ·  Info: Sturz"
      and app.vorbefund_knopf.sichtbar and app.vorbefund_knopf.cget("text") == "Vorbefund 12.03.2024"
      and app.cas_band.cfg.get("height") == 74, (app.cas_kopf_label.cfg, app.vorbefund_knopf.cfg, app.cas_band.cfg))
FENSTER = []


class FakeFenster:
    def __init__(self, *a, **k):
        self.titel, FENSTER[:] = "", [self]

    def title(self, t):
        self.titel = t

    def geometry(self, *a):
        pass

    def attributes(self, *a):
        pass

    def after(self, ms, fn):
        pass

    def winfo_exists(self):
        return True

    def destroy(self):
        pass


class FakeBox:
    def __init__(self, *a, **k):
        self.text, self.zustand = "", "normal"
        FENSTER.append(self)

    def pack(self, **k):
        pass

    def insert(self, idx, t):
        self.text += t

    def configure(self, **k):
        self.zustand = k.get("state", self.zustand)


mod.ctk.CTkToplevel, alt_box = FakeFenster, mod.ctk.CTkTextbox
mod.ctk.CTkTextbox = FakeBox
app._vorbefund_zeigen()
mod.ctk.CTkTextbox = alt_box
check("Vorbefund-Fenster: Titel mit Datum/Untersuchung, Text = Vorbefund, nur lesen",
      getattr(app, "_vorbefund_gezeigt", 0) == 1 and len(FENSTER) == 2 and "12.03.2024" in FENSTER[0].titel
      and "nur Anzeige" in FENSTER[0].titel and FENSTER[1].text == VB_TEXT and FENSTER[1].zustand == "disabled",
      [getattr(f, "titel", getattr(f, "text", "")) for f in FENSTER])
datei("cas_leistungen_x1.json", {"protokoll": 1, "auftrag_id": "x1", "nr": "20261014105", "roh": "Datenbank: c",
                                 "leistungen": CAS_DB[:1], "quelle": "CAS-Datenbank"})
app._cas_einmal()
datei("cas_ibl_x1.json", {"protokoll": 1, "auftrag_id": "x1", "nr": "20261014105", "bausteine": [FROG]})
app._cas_einmal()
check("IB-Lab vor dem Diktat → Gerüst im Befund-Feld, auffällige Werte markiert",
      app.result_text.text.startswith("## Fuß links in 2 Ebenen") and app._nur_geruest()
      and getattr(app, "_ibl_geruest_n", 0) == 1, app.result_text.text[:200])
check("… Gerüst zählt nicht als Diktat (ein neuer Auftrag würde ersetzen, nicht abgelehnt)", not app._cas_hat_inhalt())
app.transcript_text.text = "Fuß links: Hallux valgus angedeutet."
app.befund_aus_text(kontrolle=True)
bis_ruhe()
check("INS: Befund aus dem Diktat, IB-Lab-Werte wörtlich darin, Gerüst ersetzt",
      "Beschreibung laut Diktat" in app.result_text.text
      and "Calcaneusneigungswinkel 10° (IB Lab FROG)." in app.result_text.text and not app._nur_geruest(),
      app.result_text.text[:400])
app.reset_dictation()
S.pump(app, lambda: False, 0.3)
check("F9 → Gerüst wieder vorab", app._nur_geruest() and app.result_text.text.startswith("## Fuß links"),
      app.result_text.text[:120])

# ───────────────────────────── Teil 4: nie an die KI ─────────────────────────────
alle = "\n".join(LLM_PROMPTS)
check("kein Prompt enthält Vorbefund, Zuweiser oder Info", LLM_PROMPTS and "VORBEFUND-GEHEIMTEXT" not in alle
      and "Max Zuweiser" not in alle and "Sturz" not in alle, len(LLM_PROMPTS))
for name in ("pipeline.py", "gemini.py", "cas_vorlagen.py", "korrektur.py"):
    text = (ROOT / "source_code" / name).read_text(encoding="utf-8").lower()
    check(f"{name} kennt den Kontext nicht (kein „vorbefund“/„kontext_lesen“/„zuweiser“)",
          "vorbefund" not in text and "kontext_lesen" not in text and "zuweiser" not in text)

print("FEHLER:", fails)
sys.exit(1 if fails else 0)
