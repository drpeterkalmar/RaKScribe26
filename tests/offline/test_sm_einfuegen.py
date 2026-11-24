"""Gate senf-ibl-speechmagic-paste-n1 (Peter 21.11.2026): Senf + pathologische IB-Lab-Sätze automatisch ins
SpeechMagic-Diktatfenster – nur kp, einmal je Diktatnummer, nie während der Aufnahme, Cursor und Zwischenablage zurück,
IB Lab nur auffällig und wörtlich wie im KaiScribe-Befund, Sicherheitsnetz bei stehen gebliebener [SENF]-Zeile.
Teil 1: reine Logik (Befehlszeile, Titel, Senf-Zeilen, IB-Lab-Ablage → Sätze). Teil 2: Wächter mit Attrappen-Fenster.
Teil 3: Win32-Einfügen (Markierung + Zwischenablage) mit Attrappen für SendMessage und win32clipboard.
Teil 4: KaiScribe-Fenster startet den Wächter nur unter Windows; Konfiguration SM_SENF/SM_IBL.
Synthetische Texte, keine Patientendaten.  Aufruf: python3 tests/offline/test_sm_einfuegen.py"""
import copy, json, os, pathlib, re, sys, tempfile, types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import ibl_bausteine as I  # noqa: E402
import sm_einfuegen as M  # noqa: E402
import config as C  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


NR = "20261121031"
CMD = rf'"C:\casmed\SpeechExec4\CASSpeechMagic.exe" -p 451898 -d 20261121 -n 31 -u kp -h wnd_cas1frmtWarteListe_port_9201 -nodevexpress -a i'
TITEL = "CASOnline Diktat - Testpatient *** User: kp"

# ───────────────────────────── Teil 1: Logik ─────────────────────────────
k = M.kommandozeile(CMD)
check("Befehlszeile → Nr = -d + -n dreistellig, Kürzel klein, PatId", k == {"nr": NR, "benutzer": "kp", "patid": "451898"}, k)
check("Befehlszeile ohne -n / mit Platzhalter / ohne -u → None",
      M.kommandozeile("CASSpeechMagic.exe -d 20261121 -u kp") is None
      and M.kommandozeile("x.exe -d 20261121 -n %numberinlist% -u kp") is None
      and M.kommandozeile("x.exe -d 20261121 -n 3") is None)
check("Fenstertitel: CASOnline Diktat … User: kp → kp; KP → kp; anderes Fenster → None",
      M.diktat_titel(TITEL) == "kp" and M.diktat_titel("CASOnline Diktat - x User: KP") == "kp"
      and M.diktat_titel("Dokument1 - Word") is None and M.diktat_titel("CASOnline Diktat") is None)

SENF = {"v": 1, "nr": NR, "status": "fertig", "zeit": "2026-11-21T20:00:00", "befund": "auffaellig",
        "zeilen": ["RH 31 · Knie re · Gelenkerguss", "RH 31 · Knie re · Fabella", "MESSUNG {\"a\": 1}"],
        "weitere_laufen": False}
z = M.senf_zeilen(SENF)
check("Nachtrag 21:13: Senf befundtauglich (ohne „RH xx · Untersuchung ·“), nur kurze Marke [SENF], ohne Messblock",
      z == ("fertig", ["[SENF] Gelenkerguss", "[SENF] Fabella"]), z)
check("senf_inhalt: RH-Zeile ohne Untersuchung, mehrteilige Pathologie bleibt, fremde Zeile unverändert",
      M.senf_inhalt("RH 31 · Knie re · Gelenkerguss") == "Gelenkerguss"
      and M.senf_inhalt("RH 7 · LWS · Spondylolisthese L5/S1 · Meyerding I") == "Spondylolisthese L5/S1 · Meyerding I"
      and M.senf_inhalt("RH 7 · Gelenkerguss") == "Gelenkerguss" and M.senf_inhalt("Kleiner Erguss.") == "Kleiner Erguss.")
check("ohne_marken: nur die Marken weg, Inhalt bleibt",
      M.ohne_marken("Diktat.\r\n[SENF] Gelenkerguss\r\n[SENF]Fabella") == "Diktat.\r\nGelenkerguss\r\nFabella")
check("Senf unauffällig → „[SENF] unauffällig“",
      M.senf_zeilen(dict(SENF, befund="unauffaellig", zeilen=["RH 31 · Knie · unauffällig (…)"]))
      == ("fertig", ["[SENF] unauffällig"]))
check("Senf läuft / weitere Serie läuft → warten; Fehler/übersprungen → nichts",
      M.senf_zeilen(dict(SENF, status="laeuft"))[0] == "warten" and M.senf_zeilen(dict(SENF, weitere_laufen=True))[0]
      == "warten" and M.senf_zeilen(dict(SENF, status="fehler"))[0] == "nichts"
      and M.senf_zeilen(dict(SENF, status="uebersprungen"))[0] == "nichts")
check("jede Senf-Zeile trägt die Marke [SENF (fürs Sicherheitsnetz)", all(M.hat_senf(x) for x in z[1]))

FAELLE = json.loads((ROOT / "tests/offline/snapshots/frog10_bausteine.json").read_text(encoding="utf-8"))["faelle"]
F = {f["nr"]: f["baustein"] for f in FAELLE}


def ablage_json(b, nr_neu=None):
    """Brücken-Baustein der Fixture → Ablage-Datei des Abholers (ibl-abholer/1), wie sie in X:\\IBL-Vorbefunde liegt."""
    acc = (nr_neu + b["accno"][-1]) if nr_neu else b["accno"]
    v = {"befundteil": b["befundteil"], "ergebnis_punkte": b["ergebnis"], "hinweise_fuer_befunder": b["hinweise"],
         "nicht_zugeordnet": b["nicht_zugeordnet"]}
    if b.get("befundtext"):
        v["befundtext"] = {b["modul"]: b["befundtext"]}
    return acc, {"format": "ibl-abholer/1", "accession_number": acc, "modul": b["modul"], "modul_name": b["modul_name"],
                 "version": b["version"], "aktualisiert": b["aktualisiert"], "vorbefund": v,
                 "quellen": [{"seiten": b["seiten"]}]}


tmp = tempfile.mkdtemp()
ABL = os.path.join(tmp, "IBL-Vorbefunde")
os.makedirs(ABL)


def ablegen(b, nr):
    acc, d = ablage_json(b, nr)
    with open(os.path.join(ABL, f"{acc}_{b['modul']}.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    return acc


acc11 = ablegen(F[11], NR)
gelesen = M.ibl_bausteine_lesen(ABL, NR)
zl = M.ibl_zeilen(gelesen)
soll = I.auffaellige_zeilen(I.aus_liste([dict(F[11], accno=acc11)]))
check("IB Lab aus der Ablage des Abholers: FROG pathologisch → dieselben Sätze wie die Markierung im KaiScribe-Befund",
      len(zl) == 1 and zl[0][0] == f"ibl:{acc11}_frog" and zl[0][1] == [x for x in soll if not I.ist_schluss(x)], (zl, soll))
check("… wörtlich: Stellungs-/Gewölbesatz und die lateinischen Begriffe (Hallux valgus, Pes cavus) mit Seite",
      F[11]["befundtext"]["stellung"][0] in zl[0][1] and F[11]["befundtext"]["gewoelbe"][0] in zl[0][1]
      and "Pes cavus links" in zl[0][1] and "Hochgradiger Hallux valgus links" in zl[0][1], zl)
check("… ohne Schlussanmerkung, ohne Messzeilen „(IB Lab FROG)“",
      not any(I.ist_schluss(x) or "(IB Lab" in x for x in zl[0][1]), zl)
# Normalbefund (Fixture 4 ohne befundtext) und Rho → kein Text
NR2 = "20261121032"
ablegen(F[4], NR2)
rho = {"accno": "x", "modul": "rho", "modul_name": "IB Lab Rho", "version": 1, "aktualisiert": "", "seiten": [],
       "befundteil": ["Rho-Score 8 von 10 (IB Lab Rho)."], "ergebnis": ["Erhöhte Wahrscheinlichkeit …"], "hinweise": [],
       "nicht_zugeordnet": []}
acc_r, d_r = ablage_json(dict(rho, accno="x2"), NR2)
with open(os.path.join(ABL, f"{acc_r}_rho.json"), "w", encoding="utf-8") as f:
    json.dump(d_r, f)
z4 = M.ibl_zeilen(M.ibl_bausteine_lesen(ABL, NR2))
soll4 = I.auffaellige_zeilen(I.aus_liste([F[4]]))
check("Normalbefund/„kein Text“ und Rho ergeben nichts bzw. nur, was KaiScribe auch markiert",
      all(not k.endswith("_rho") for k, _ in z4) and [z for _, zs in z4 for z in zs]
      == [x for x in soll4 if not I.ist_schluss(x)], (z4, soll4))
check("andere Diktatnummer / Ablage aus / fehlt → nichts",
      M.ibl_bausteine_lesen(ABL, "20261121099") == [] and M.ibl_bausteine_lesen("aus", NR) == []
      and M.ibl_bausteine_lesen(os.path.join(tmp, "fehlt"), NR) == [])
kaputt = os.path.join(ABL, f"{NR}9_lama.json")
open(kaputt, "w").write("{halb")
check("halb geschriebene Datei wird übergangen", len(M.ibl_bausteine_lesen(ABL, NR)) == 1)
os.remove(kaputt)

check("Block fürs Ende: eigene Zeilen, Umbruch davor nur, wenn schon Text ohne Zeilenende dasteht",
      M.block(["a", "b"], "") == "a\r\nb" and M.block(["a"], "Diktat.") == "\r\na"
      and M.block(["a"], "Diktat.\r\n") == "a")
check("neue_zeilen: schon im Fenster stehende Zeilen (Leerraum egal) fallen weg",
      M.neue_zeilen(["Pes cavus links", "x"], "Diktat.\r\nPes  cavus links\r\n") == ["x"])
check("Mikrofon: frei / aktiv (App) / unbekannt (Registry nicht lesbar → nie einfügen)",
      M.mikrofon_zustand(lambda: [("a.exe", 5, 9)]) == "frei"
      and M.mikrofon_zustand(lambda: [("a.exe", 5, 9), ("CASSpeechMagic.exe", 10, 0)]) == "aktiv (CASSpeechMagic.exe)"
      and M.mikrofon_zustand(lambda: [("b.exe", 12, 11)]) == "aktiv (b.exe)"
      and M.mikrofon_zustand(None) == "unbekannt" and M.mikrofon_zustand(lambda: 1 / 0) == "unbekannt")


# ───────────────────────────── Teil 2: Wächter ─────────────────────────────
class Uhr:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


class Api:
    """Attrappe: ein SpeechMagic-Fenster mit Textfeld; einfuegen hängt ans Ende und setzt den Cursor zurück."""

    def __init__(self, uhr):
        self.uhr = uhr
        self.procs, self.wins = [], []
        self.texte = {}
        self.cursor = {}
        self.mikro = "frei"
        self.einfuege_aufrufe = []
        self.clip = "Arzt-Zwischenablage"

    def sm_pids(self):
        return [p[0] for p in self.procs]

    def prozess_info(self, pid):
        return next(((p[1], p[2]) for p in self.procs if p[0] == pid), None)

    def fenster(self):
        return list(self.wins)

    def textfeld(self, hwnd):
        return f"E{hwnd}"

    def text(self, edit):
        return self.texte.get(edit)

    def mikrofon(self):
        return self.mikro

    def pegel(self):
        # kaiscribe-sm-senf-diktatpause-n1: Sprachpegel der CASSpeechMagic-Aufnahme (Peak, Sitzungen); Standard still
        self.pegel_aufrufe = getattr(self, "pegel_aufrufe", 0) + 1
        p = self.pegel_wert(self.uhr.t) if callable(getattr(self, "pegel_wert", None)) else getattr(self, "pegel_wert", 0.0)
        return (p, getattr(self, "sitzungen", 1)) if p is not None else (None, 0)

    def marken_entfernen(self, edit, marken):
        t = self.texte.get(edit, "")
        n = sum(t.count(m) for m in marken[:1])
        self.texte[edit] = M.ohne_marken(t)
        return True, n, ""

    def einfuegen(self, edit, text):
        self.einfuege_aufrufe.append((edit, text))
        vor = self.cursor.get(edit, 0)
        alt_clip = self.clip
        self.clip = text
        self.texte[edit] = self.texte.get(edit, "") + text.replace("\r\n", "\n")
        self.cursor[edit] = vor               # Cursor des Arztes zurück
        self.clip = alt_clip                  # Zwischenablage zurück
        return True, ""


def neu_waechter(cfg=None, senf=None, freigabe=True, aus=False, ordner=None):
    uhr = Uhr()
    api = Api(uhr)
    cfg = cfg or types.SimpleNamespace(sm_senf=["kp"], sm_ibl=["kp"], senf_ordner="S", ibl_ablage=ABL,
                                      sm_schalter_ordner=os.path.join(tmp, "Bruecke"))
    logs, warn = [], []
    senf_box = {"d": senf}
    lese = lambda o, nr: ("da", senf_box["d"]) if senf_box["d"] is not None else ("fehlt", None)  # noqa: E731
    ex = lambda p: (p.endswith(M.SM_FREIGABE_DATEI) and freigabe) or (p.endswith(M.SM_AUS_DATEI) and aus)  # noqa: E731
    merker = M.Merker(ordner or tempfile.mkdtemp(), None, jetzt=uhr)
    w = M.Waechter(api, cfg, merker, log=logs.append, warnen=lambda nr, t: warn.append((nr, t)), jetzt=uhr,
                   lese_senf=lese, existiert=ex)
    return w, api, uhr, logs, warn, senf_box


def oeffnen(api, uhr, hwnd=100, pid=7, cmd=CMD, titel=TITEL, text=""):
    api.procs.append((pid, uhr.t - 1, cmd))
    api.wins.append((hwnd, pid, titel))
    api.texte[f"E{hwnd}"] = text


def schliessen(api, hwnd=100):
    api.wins = [x for x in api.wins if x[0] != hwnd]


def takte(w, uhr, n=3, s=0.5):
    for _ in range(n):
        uhr.t += s
        w.takt()


w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
takte(w, uhr, 1)                                    # erster Takt: nichts offen
oeffnen(api, uhr)
takte(w, uhr, 6)
txt = api.texte["E100"]
check("kp öffnet SpeechMagic-Diktat → Senf + FROG-Sätze stehen am Ende des Diktats",
      "[SENF] Gelenkerguss" in txt and "RH 31" not in txt and "Pes cavus links" in txt, txt)
check("… IB-Lab-Sätze zuerst, Senf-Block zuletzt (klar abgesetzt)", txt.index("Pes cavus links") < txt.index("[SENF"), txt)
check("… in EINEM Einfügen, Cursor des Arztes und Zwischenablage danach wie vorher",
      len(api.einfuege_aufrufe) == 1 and api.cursor.get("E100", 0) == 0 and api.clip == "Arzt-Zwischenablage")
check("… Log ohne Text: Nummer, Zeilenzahl, Quelle", any(NR in l and "eingefügt" in l and "Senf" in l for l in logs), logs)
takte(w, uhr, 40, 1.0)
check("einmal je Diktatnummer: weitere Takte fügen nichts mehr ein", len(api.einfuege_aufrufe) == 1)
# Peter löscht den Senf und schließt → keine Warnung; Wiederöffnen → nichts doppelt
api.texte["E100"] = api.texte["E100"].split("[SENF")[0]
takte(w, uhr, 6)
schliessen(api)
takte(w, uhr, 2)
check("Senf gelöscht, Diktat zu → keine Warnung", warn == [], warn)
uhr.t += 120
oeffnen(api, uhr, hwnd=101, pid=8, text=api.texte["E100"])
takte(w, uhr, 50, 1.0)
check("Wiederöffnen derselben Nummer → nichts doppelt (Merker)", len(api.einfuege_aufrufe) == 1, api.einfuege_aufrufe)

# ── opus-senf-abgleich-ibl-vara-n1-einspielen: Abgleich IB Lab/Vara (a_…), später v 1 → 2 ──
A_E = {"id": "a_0123456789ab", "art": "Abgleich", "befund": "", "zeilen": ["Vara: neutral (Score 50/100)"],
       "abgleich": [{"art": "zusatz", "modul": "kl", "text": "IB Lab: KL 3 re."}]}
UN1 = {"v": 1, "nr": NR, "status": "fertig", "zeit": "2026-11-24T20:00:00", "befund": "unauffaellig", "zeilen": [],
       "weitere_laufen": False, "eintraege": []}
UN2 = dict(UN1, v=2, eintraege=[A_E])
check("senf_zeilen unauffällig + a_-Eintrag: Vara-Zeile nach „[SENF] unauffällig“, „IB Lab:“ nur ohne SM_IBL",
      M.senf_zeilen(UN2, False) == ("fertig", ["[SENF] unauffällig", "[SENF] Vara: neutral (Score 50/100)", "[SENF] IB Lab: KL 3 re."])
      and M.senf_zeilen(UN2, True) == ("fertig", ["[SENF] unauffällig", "[SENF] Vara: neutral (Score 50/100)"]), M.senf_zeilen(UN2, True))
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=UN1)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
check("v1 unauffällig → nur „[SENF] unauffällig“ im Diktat", api.texte["E100"].strip().endswith("[SENF] unauffällig") and "Vara" not in api.texte["E100"],
      api.texte["E100"])
senf_box["d"] = UN2
takte(w, uhr, 40, 1.0)
t = api.texte["E100"]
check("Abgleich kommt später (v 2): GENAU eine Zeile „Vara“ nachgefügt, kein „IB Lab:“ (SM_IBL aktiv), Status nicht doppelt",
      t.count("Vara: neutral (Score 50/100)") == 1 and "IB Lab" not in t and t.count("unauffällig") == 1
      and len(api.einfuege_aufrufe) == 2, (t, api.einfuege_aufrufe))
check("… Merker senf:v1 + senf:v2", {"senf:v1", "senf:v2"} <= set(w.merker.lesen(NR)["eingefuegt"]), w.merker.lesen(NR))
takte(w, uhr, 60, 1.0)
check("… weitere Takte fügen nichts mehr ein", len(api.einfuege_aufrufe) == 2)
# Übernehmen (Marken weg) + Wiederöffnen mit demselben Merker → v2 nicht noch einmal
api.texte["E100"] = M.ohne_marken(api.texte["E100"])
schliessen(api)
takte(w, uhr, 2)
uhr.t += 120
oeffnen(api, uhr, hwnd=101, pid=8, text=api.texte["E100"])
takte(w, uhr, 60, 1.0)
check("Wiederöffnen: Merker senf:v2 → nichts doppelt", len(api.einfuege_aufrufe) == 2, api.einfuege_aufrufe)
# Wiederöffnen, Text ohne die Zeile (Peter hat sie gelöscht), v 3 mit neuer Zeile → nur die neue
senf_box["d"] = dict(UN2, v=3, eintraege=[dict(A_E, zeilen=["Vara: neutral (Score 50/100)", "⚠ Prüfen: Seite re."])])
takte(w, uhr, 40, 1.0)
check("v 3: nur die neue ⚠-Zeile wird nachgefügt (Vara-Zeile steht schon als „Vara…“ ohne Marke)",
      api.texte["E101"].count("⚠ Prüfen: Seite re.") == 1 and len(api.einfuege_aufrufe) == 3, api.texte["E101"])
# kp ohne SM_IBL: „IB Lab:“-Zusatz wird mit eingefügt
cfg2 = types.SimpleNamespace(sm_senf=["kp"], sm_ibl=[], senf_ordner="S", ibl_ablage=ABL,
                             sm_schalter_ordner=os.path.join(tmp, "Bruecke"))
w, api, uhr, logs, warn, senf_box = neu_waechter(cfg=cfg2, senf=UN1)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
senf_box["d"] = UN2
takte(w, uhr, 40, 1.0)
check("SM_IBL aus: „IB Lab: KL 3 re.“ kommt über den Senf-Abgleich", "[SENF] IB Lab: KL 3 re." in api.texte["E100"], api.texte["E100"])
# Nachlese endet 15 min nach dem Öffnen
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=UN1)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
uhr.t += 901
senf_box["d"] = UN2
takte(w, uhr, 10, 1.0)
check("nach 15 min keine Nachlese mehr", len(api.einfuege_aufrufe) == 1, api.einfuege_aufrufe)

# sm-senf-laenge-n1 (Peter 23.11.2026, RH 146): bis 3.22.5 hart bei 300 Zeichen abgeschnitten („… stationär. (V“)
LANG = ("Gelenkerguss im oberen Rezessus mit synovialer Verdickung, Fabella ohne Reizzeichen, keine Fraktur. " * 4
        + "Vergleich zur Voruntersuchung stationär. (Verlauf empfohlen)")
assert 300 < len(LANG) < M.SENF_ZEILE_MAX
z = M.senf_zeilen(dict(SENF, zeilen=["RH 146 · Knie re · " + LANG]))
check("Senf über 300 Zeichen kommt vollständig an (kein „(V“-Abriss)", z == ("fertig", ["[SENF] " + LANG]), z)
check("genau 300 / 301 Zeichen bleiben ganz", M.senf_kuerzen("a" * 300) == "a" * 300 and M.senf_kuerzen("b" * 301) == "b" * 301)
RIESIG = ("Erster langer Satz mit Befund. " * 30) + "Zweiter Teil; " * 20 + "Schluss ohne Punkt " * 30
k = M.senf_kuerzen(RIESIG)
check("Zeile über 1200 Zeichen: am letzten Satzende vor der Grenze + „…“, nie mitten im Wort",
      len(RIESIG) > 1200 and len(k) <= M.SENF_ZEILE_MAX + 2 and k.endswith((". …", "; …"))
      and RIESIG.startswith(k[:-2]), (len(k), k[-40:]))
k2 = M.senf_kuerzen("Wort " * 400)
check("ohne Satzende: am letzten Leerzeichen + „…“", k2.endswith("Wort …") and len(k2) <= M.SENF_ZEILE_MAX + 2, k2[-20:])
check("Grenze im Code 1200, kein hartes [:300] mehr",
      M.SENF_ZEILE_MAX == 1200 and "[:300]" not in (ROOT / "source_code/sm_einfuegen.py").read_text(encoding="utf-8"))
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=dict(SENF, zeilen=["RH 146 · Knie re · " + LANG]))
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
takte(w, uhr, 40, 1.0)
check("langer Senf im Diktat: vollständig und genau einmal (kein doppeltes Einfügen)",
      len(api.einfuege_aufrufe) == 1 and api.texte["E100"].count(LANG) == 1, (api.einfuege_aufrufe, api.texte["E100"][-80:]))
schliessen(api)
uhr.t += 120
oeffnen(api, uhr, hwnd=101, pid=8, text=api.texte["E100"])
takte(w, uhr, 50, 1.0)
check("… Wiederöffnen → nichts doppelt", len(api.einfuege_aufrufe) == 1 and api.texte["E101"].count(LANG) == 1)

# kaiscribe-sm-waechter-bleibt-n1: zwei KaiScribe-Prozesse (z. B. stiller Wächter + neue Instanz/Gast) sehen dasselbe
# SpeechMagic-Fenster, gleicher Merker-Ordner (lokal je PC/Benutzer + X:) → genau EIN Einfügen
gemein = tempfile.mkdtemp()
w1, api, uhr, logs1, _, _ = neu_waechter(senf=SENF, ordner=gemein)
w2, _, _, logs2, _, _ = neu_waechter(senf=SENF, ordner=gemein)
w2.api, w2.jetzt, w2.merker = api, uhr, M.Merker(gemein, None, jetzt=uhr)
takte(w1, uhr, 1)
w2.takt()
oeffnen(api, uhr)
api.pegel_wert = 0.3                   # Peter diktiert: beide erkennen das Fenster, beide warten (Merker noch leer)
for _ in range(3):
    uhr.t += 0.5
    w1.takt()
    w2.takt()
api.pegel_wert = 0.0
for _ in range(14):
    uhr.t += 0.5
    w1.takt()
    w2.takt()
check("zwei Wächter, ein Diktat → genau ein Einfügen (Merker vor dem Einfügen neu gelesen)",
      len(api.einfuege_aufrufe) == 1 and api.texte["E100"].count("[SENF] Gelenkerguss") == 1,
      (len(api.einfuege_aufrufe), logs1, logs2))
check("… der zweite loggt „schon eingefügt (Merker)“ statt einzufügen",
      any("schon eingefügt (Merker)" in l for l in logs1 + logs2), logs1 + logs2)
check("Wächter-Sperre: außerhalb von Windows immer frei (Tests), Name je Sitzung (Local\\)",
      M.waechter_sperre() is True and M.WAECHTER_MUTEX.startswith("Local\\"))

# ── kaiscribe-sm-einfuegen-wiederholen-n1 (Peter 24.11.2026): SpeechMagic lädt das Diktat erst nach dem Fenster und
# überschreibt/speichert ein zu frühes Einfügen nicht → Ruhe-Prüfung, Nachkontrolle nach 3 s, bis zu 3 Versuche,
# Wiederöffnen nach Fehlschlag bzw. nach „Marke steht noch drin“ ──
SENF_Z = M.senf_zeilen(SENF)[1]
cfg_s = types.SimpleNamespace(sm_senf=["kp"], sm_ibl=[], senf_ordner="S", ibl_ablage=ABL,
                              sm_schalter_ordner=os.path.join(tmp, "Bruecke"))


class Laedt(Api):
    """SpeechMagic-Attrappe: lädt den gespeicherten Text erst `lade_s` nach dem Öffnen und überschreibt dabei das Feld;
    `schlucken` = so viele Einfügungen gehen verloren (sofort: `sofort`, sonst 1 s später überschrieben)."""

    def __init__(self, uhr, lade_s=None, gespeichert="Diktat vom Arzt.\r\n", schlucken=0, sofort=True):
        super().__init__(uhr)
        self.lade_s, self.gespeichert, self.schlucken, self.sofort = lade_s, gespeichert, schlucken, sofort
        self.offen_seit, self.geladen, self.ueberschreib = {}, set(), {}

    def text(self, edit):
        t0 = self.offen_seit.get(edit)
        if self.lade_s is not None and t0 is not None and edit not in self.geladen and self.uhr.t - t0 >= self.lade_s:
            self.texte[edit] = self.gespeichert           # Laden überschreibt alles, was bis dahin im Feld stand
            self.geladen.add(edit)
        u = self.ueberschreib.get(edit)
        if u and self.uhr.t >= u[0]:
            self.texte[edit] = u[1]
            del self.ueberschreib[edit]
        return self.texte.get(edit)

    def einfuegen(self, edit, text):
        vorher = self.texte.get(edit, "")
        ok, g = super().einfuegen(edit, text)
        if self.schlucken > 0:
            self.schlucken -= 1
            if self.sofort:
                self.texte[edit] = vorher                 # Paste verpufft
            else:
                self.ueberschreib[edit] = (self.uhr.t + 1.0, vorher)   # erst da, 1 s später überschrieben
        return ok, g


def neu_laedt(**kw):
    w, _, uhr, logs, warn, box = neu_waechter(cfg=cfg_s, senf=SENF, ordner=kw.pop("ordner", None))
    api = Laedt(uhr, **kw)
    w.api = api
    return w, api, uhr, logs, warn, box


def oeffnen_l(api, uhr, hwnd=100, pid=7, text=""):
    oeffnen(api, uhr, hwnd=hwnd, pid=pid, text=text)
    api.offen_seit[f"E{hwnd}"] = uhr.t


# 1. Feld lädt nach dem Öffnen nach (überschreibt) → erst einfügen, wenn ruhig
w, api, uhr, logs, warn, box = neu_laedt(lade_s=1.5)
takte(w, uhr, 1)
oeffnen_l(api, uhr)
t_auf = uhr.t
zeiten = []
for _ in range(20):
    uhr.t += 0.5
    n = len(api.einfuege_aufrufe)
    w.takt()
    if len(api.einfuege_aufrufe) > n:
        zeiten.append(uhr.t - t_auf)
t = api.texte["E100"]
check("Ruhe: Feld lädt 1,5 s nach dem Öffnen nach → genau EIN Einfügen, erst danach (Diktat + Senf beide da)",
      len(api.einfuege_aufrufe) == 1 and t.startswith("Diktat vom Arzt.") and all(z in t for z in SENF_Z), (zeiten, t, logs))
check("… frühestens 2 s nach dem Öffnen und ≥ 1 s nach dem Laden (zwei gleiche Lesungen)",
      zeiten and zeiten[0] >= max(M.RUHE_ALTER_S, 1.5 + M.RUHE_GLEICH_S), zeiten)
check("… Log „Versuch 1/3 … eingefügt“ und „Kontrolle nach 3 s – steht drin“",
      any("Versuch 1/3" in l and "eingefügt" in l for l in logs) and any("Kontrolle nach 3 s – steht drin" in l for l in logs),
      logs)
# Ruhe gilt für jedes Einfügen: solange sich der Text ändert (Arzt tippt), wird nicht eingefügt
w, api, uhr, logs, warn, box = neu_laedt()
takte(w, uhr, 1)
oeffnen_l(api, uhr, text="a")
for i in range(12):
    api.texte["E100"] += "x"                              # jede Lesung anders
    uhr.t += 0.5
    w.takt()
n_tippen = len(api.einfuege_aufrufe)
takte(w, uhr, 6)
check("Ruhe: Text ändert sich laufend → nichts; steht er still → eingefügt (Log „Feld nicht ruhig“ einmal)",
      n_tippen == 0 and len(api.einfuege_aufrufe) == 1 and sum("Feld nicht ruhig" in l for l in logs) == 1, logs)

# 2. Fehlschlag „nicht im Text“ → Merker zurück, Versuch 2/3 nach 2 s, dann eingefügt
w, api, uhr, logs, warn, box = neu_laedt(schlucken=1)
takte(w, uhr, 1)
oeffnen_l(api, uhr)
takte(w, uhr, 6)
check("Fehlschlag sofort: Merker zurückgenommen (kein „senf“ gemerkt)", "senf" not in w.merker.lesen(NR)["eingefuegt"]
      and any("Versuch 1/3" in l and "NICHT eingefügt (nicht im Text)" in l and "nächster in 2 s" in l for l in logs), logs)
takte(w, uhr, 12)
t = api.texte["E100"]
check("… Versuch 2/3 eingefügt, Senf genau einmal, Merker „senf“ wieder gesetzt",
      len(api.einfuege_aufrufe) == 2 and t.count(SENF_Z[0]) == 1 and "senf" in w.merker.lesen(NR)["eingefuegt"]
      and any("Versuch 2/3" in l and "eingefügt" in l and "NICHT" not in l for l in logs), (t, logs))
# Nachtrag 10:49 (a): eingefügt, Prüfung bestanden, 1 s später von SpeechMagic überschrieben → Kontrolle nach 3 s
w, api, uhr, logs, warn, box = neu_laedt(schlucken=1, sofort=False)
takte(w, uhr, 1)
oeffnen_l(api, uhr)
takte(w, uhr, 6)
n1 = len(api.einfuege_aufrufe)
takte(w, uhr, 20)
t = api.texte["E100"]
check("Nachkontrolle: sofort drin, 1 s später überschrieben → nach 3 s erkannt, wiederholt, am Ende genau einmal drin",
      n1 == 1 and len(api.einfuege_aufrufe) == 2 and t.count(SENF_Z[0]) == 1
      and any("Kontrolle nach 3 s – 2 Zeile(n) nicht mehr im Text – Versuch 1/3" in l for l in logs), (t, logs))
# Arzt bearbeitet in den 3 s (übernimmt = Marken weg) → zählt als da, kein zweites Einfügen
w, api, uhr, logs, warn, box = neu_laedt()
takte(w, uhr, 1)
oeffnen_l(api, uhr)
takte(w, uhr, 5)
api.texte["E100"] = M.ohne_marken(api.texte["E100"])
takte(w, uhr, 20)
check("Nachkontrolle: Marken in den 3 s übernommen → steht drin, nichts doppelt",
      len(api.einfuege_aufrufe) == 1 and any("steht drin" in l for l in logs), logs)

# 3. alle 3 Versuche scheitern → aufgegeben; nächstes Öffnen desselben Diktats → erneut, einmal
gem = tempfile.mkdtemp()
w, api, uhr, logs, warn, box = neu_laedt(schlucken=5, ordner=gem)
takte(w, uhr, 1)
oeffnen_l(api, uhr)
takte(w, uhr, 40)
check("3 Fehlschläge → genau 3 Versuche, „Versuch 3/3, aufgegeben; beim nächsten Öffnen erneut“, Merker ohne senf",
      len(api.einfuege_aufrufe) == 3 and any("Versuch 3/3, aufgegeben" in l for l in logs)
      and "senf" not in w.merker.lesen(NR)["eingefuegt"], (len(api.einfuege_aufrufe), logs))
schliessen(api)
takte(w, uhr, 2)
check("… Diktat zu: keine Warnung (keine Marke im Text)", warn == [], warn)
api.schlucken = 0
uhr.t += 120
oeffnen_l(api, uhr, hwnd=101, pid=8, text=api.texte["E100"])
takte(w, uhr, 20)
check("Wiederöffnen nach Fehlschlag → Senf jetzt eingefügt, genau einmal",
      len(api.einfuege_aufrufe) == 4 and api.texte["E101"].count(SENF_Z[0]) == 1, (api.einfuege_aufrufe[-1:], logs[-4:]))
api.texte["E101"] = M.ohne_marken(api.texte["E101"]).split("Gelenkerguss")[0]     # Arzt löscht den Senf
takte(w, uhr, 3)
schliessen(api, 101)
takte(w, uhr, 2)
uhr.t += 120
oeffnen_l(api, uhr, hwnd=102, pid=9, text=api.texte["E101"])
takte(w, uhr, 20)
check("… danach übernommen/gelöscht und wieder geöffnet → nichts doppelt", len(api.einfuege_aufrufe) == 4, logs[-3:])

# 4. Nachtrag 10:49 (b), RH 58: eingefügt + Kontrolle bestanden, geschlossen mit Marke, SpeechMagic hat es nicht gespeichert
w, api, uhr, logs, warn, box = neu_laedt(lade_s=0.2)
takte(w, uhr, 1)
oeffnen_l(api, uhr)
takte(w, uhr, 16)
schliessen(api)
takte(w, uhr, 2)
check("RH 58: eingefügt, Kontrolle bestanden, zu mit Marke → Warnung, senf_offen", len(api.einfuege_aufrufe) == 1
      and len(warn) == 1 and w.merker.lesen(NR)["senf_offen"] is True, (warn, logs))
uhr.t += 1000
oeffnen_l(api, uhr, hwnd=101, pid=8)                     # lädt den gespeicherten Stand – ohne Senf
takte(w, uhr, 20)
t = api.texte["E101"]
check("… Wiederöffnen, Senf fehlt im Text (Arzt hat ihn nicht gelöscht) → erneut eingefügt, genau einmal",
      len(api.einfuege_aufrufe) == 2 and t.startswith("Diktat vom Arzt.") and t.count(SENF_Z[0]) == 1
      and any("zuletzt mit [SENF]-Marke geschlossen" in l for l in logs), (t, logs))
# … Senf (mit Marke, vom Arzt ergänzt) steht beim Wiederöffnen da → nur gemerkt
schliessen(api, 101)
takte(w, uhr, 2)
api.gespeichert = "Diktat vom Arzt.\r\n[SENF] Gelenkerguss, klein\r\n"
uhr.t += 100
oeffnen_l(api, uhr, hwnd=102, pid=9)
takte(w, uhr, 20)
check("… Marke steht beim Wiederöffnen (bearbeitet) → nicht neu eingefügt", len(api.einfuege_aufrufe) == 2,
      (api.texte["E102"], logs[-3:]))
# … zuletzt „übernommen bzw. gelöscht“ geschlossen → nie neu, auch wenn der Senf fehlt
w, api, uhr, logs, warn, box = neu_laedt(lade_s=0.2)
takte(w, uhr, 1)
oeffnen_l(api, uhr)
takte(w, uhr, 16)
api.texte["E100"] = "Diktat vom Arzt.\r\n"                # Arzt löscht den Senf
takte(w, uhr, 3)
schliessen(api)
takte(w, uhr, 2)
uhr.t += 100
oeffnen_l(api, uhr, hwnd=101, pid=8)
takte(w, uhr, 20)
check("… zuletzt „Senf übernommen bzw. gelöscht“ → beim Wiederöffnen nicht neu eingefügt",
      len(api.einfuege_aufrufe) == 1 and "[SENF" not in api.texte["E101"] and w.merker.lesen(NR)["senf_offen"] is False,
      logs[-4:])
# … zu vor der Kontrolle, Zeilen schon wieder weg → nicht als eingefügt gemerkt, nächstes Öffnen erneut
w, api, uhr, logs, warn, box = neu_laedt(schlucken=1, sofort=False)
takte(w, uhr, 1)
oeffnen_l(api, uhr)
takte(w, uhr, 5)
uhr.t += 1.0
w.takt()                                                 # Lesung: überschrieben
schliessen(api)
takte(w, uhr, 2)
check("zu vor der Kontrolle, Zeilen fehlten → Merker zurück („beim nächsten Öffnen erneut“)",
      "senf" not in w.merker.lesen(NR)["eingefuegt"] and any("vor der Kontrolle" in l for l in logs), logs[-3:])

# Übernehmen (Taste): nur die Marken weg, danach keine Warnung beim Schließen
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
api.texte["E100"] = "Kniegelenk rechts: kein Erguss.\n" + api.texte["E100"]
w.uebernehmen_anfordern()
takte(w, uhr, 1)
t = api.texte["E100"]
check("Übernehmen: Marken entfernt, Senf-Inhalt + Diktat + IB-Lab-Sätze bleiben wörtlich",
      "[SENF" not in t and "Gelenkerguss" in t and "Fabella" in t and t.startswith("Kniegelenk rechts: kein Erguss.")
      and "Pes cavus links" in t, t)
check("… Log nennt die Zahl der Marken (ohne Text)", any("Übernehmen – 2 Marke(n) entfernt" in l for l in logs), logs)
api.texte["E100"] += "\nGelenkerguss mit Begleitsynovitis."      # Peter ergänzt frei
takte(w, uhr, 6)
schliessen(api)
takte(w, uhr, 2)
check("… übernommen und frei ergänzt → beim Schließen KEINE Warnung (nur die Marke zählt, nie der Inhalt)", warn == [], warn)
w.uebernehmen_anfordern()
takte(w, uhr, 1)
check("Übernehmen ohne offenes Diktat → nur Log, nichts geändert", any("kein offenes SpeechMagic-Diktat" in l for l in logs))

# Auslöser-Datei (live L2: injizierte Tasten erreichen den keyboard-Hook nicht) → derselbe Weg wie die Taste
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
aus_datei = os.path.join(tmp, "sm_uebernehmen.txt")
w.ausloeser = aus_datei
w.existiert = lambda p, alt=w.existiert: os.path.exists(p) if p == aus_datei else alt(p)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
open(aus_datei, "w").write("x")
takte(w, uhr, 1)
check("Auslöser-Datei: Marken weg wie mit der Taste, Datei sofort gelöscht",
      "[SENF" not in api.texte["E100"] and "Gelenkerguss" in api.texte["E100"] and not os.path.exists(aus_datei)
      and any("Auslöser-Datei" in l for l in logs), logs)

# Sicherheitsnetz: Senf bleibt stehen, Fenster zu → Warnung + Merker senf_offen
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
schliessen(api)
takte(w, uhr, 2)
check("Sicherheitsnetz: [SENF]-Marke beim Schließen noch drin → Warnung mit Diktatnummer",
      len(warn) == 1 and warn[0][0] == NR and "[SENF]" in warn[0][1] and "Vidieren" in warn[0][1], warn)
check("… Merker senf_offen = true (für die spätere Vidierlisten-Prüfung)", w.merker.lesen(NR)["senf_offen"] is True)

# nur kp: rg-Fenster → nichts
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
takte(w, uhr, 1)
oeffnen(api, uhr, cmd=CMD.replace("-u kp", "-u rg"), titel=TITEL.replace("User: kp", "User: rg"))
takte(w, uhr, 30, 1.0)
check("nur kp: rg öffnet SpeechMagic → nichts eingefügt, nichts gelesen", api.einfuege_aufrufe == [] and
      not any("erkannt" in l for l in logs), logs)

# getrennt schaltbar: Senf aus, IB Lab an
cfg = types.SimpleNamespace(sm_senf=[], sm_ibl=["kp"], senf_ordner="S", ibl_ablage=ABL,
                            sm_schalter_ordner=os.path.join(tmp, "Bruecke"))
w, api, uhr, logs, warn, senf_box = neu_waechter(cfg=cfg, senf=SENF)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
check("SM_SENF = aus, SM_IBL = kp → nur die IB-Lab-Sätze", "Pes cavus links" in api.texte["E100"]
      and "[SENF" not in api.texte["E100"], api.texte["E100"])
cfg2 = types.SimpleNamespace(sm_senf=["kp"], sm_ibl=[], senf_ordner="S", ibl_ablage=ABL,
                             sm_schalter_ordner=os.path.join(tmp, "Bruecke"))
w, api, uhr, logs, warn, senf_box = neu_waechter(cfg=cfg2, senf=SENF)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
check("SM_SENF = kp, SM_IBL = aus → nur der Senf", "[SENF" in api.texte["E100"] and "Pes cavus" not in api.texte["E100"])

# Freigabe-Datei fehlt / Notschalter liegt → nichts
for frei, aus, name in ((False, False, "Freigabe-Datei fehlt"), (True, True, "Notschalter liegt")):
    w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF, freigabe=frei, aus=aus)
    takte(w, uhr, 1)
    oeffnen(api, uhr)
    takte(w, uhr, 10, 1.0)
    check(f"{name} → nichts eingefügt", api.einfuege_aufrufe == [])

# nicht während der Aufnahme (kaiscribe-sm-senf-diktatpause-n1: Sprachpegel statt Mikrofonanzeige)
SM_MIK = "aktiv (CASSpeechMagic.exe)"
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
api.mikro, api.pegel_wert = SM_MIK, 0.4
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 40, 0.5)
check("es wird gesprochen (Pegel 0,4) → wartet, fügt nichts ein (Log „es wird gesprochen“ einmal)",
      api.einfuege_aufrufe == [] and sum("es wird gesprochen" in l for l in logs) == 1, logs)
api.pegel_wert = None
takte(w, uhr, 20, 0.5)
check("Pegel nicht messbar → ebenfalls nichts (Log „nicht messbar“)", api.einfuege_aufrufe == []
      and any("Sprachpegel nicht messbar" in l for l in logs), logs)
api.pegel_wert, api.sitzungen = 0.0, 0
takte(w, uhr, 20, 0.5)
check("keine CASSpeechMagic-Aufnahmesitzung gefunden, Anzeige sagt SpeechMagic aktiv → unbekannt, nichts",
      api.einfuege_aufrufe == [])
api.sitzungen = 1
api.mikro = "aktiv (Teams.exe)"
takte(w, uhr, 20, 0.5)
check("fremde App nimmt auf (Anzeige) → nichts, auch bei stillem SpeechMagic", api.einfuege_aufrufe == []
      and any("andere App nimmt auf" in l for l in logs), logs)
api.mikro = SM_MIK
takte(w, uhr, 6, 0.5)
check("Pause (Pegel still) → jetzt eingefügt, Log „Pause erkannt“", len(api.einfuege_aufrufe) == 1
      and "[SENF" in api.texte["E100"] and any("Pause erkannt" in l for l in logs), logs)


# ── kaiscribe-sm-senf-diktatpause-n1 (Georg 24.11.2026, RH 105–126): CASSpeechMagic belegt das Mikrofon vom Öffnen bis
# zum Schließen → die Mikrofonanzeige meldet immer „aktiv“; Pause = Sprachpegel ≥ 2 s still UND Feld ≥ 2 s unverändert ──
def lauf(w, api, uhr, sek, schritt=0.5, sprache=None, erkennung=None):
    """sek Sekunden takten; sprache(t_rel) → Pegel; erkennung(t_rel) → True = SM schreibt gerade erkannten Text.
    → Zeitpunkte (relativ zum Öffnen) der Einfügungen."""
    zeiten = []
    for _ in range(int(sek / schritt)):
        uhr.t += schritt
        rel = uhr.t - api.t_auf
        if sprache:
            api.pegel_wert = sprache(rel)
        if erkennung and erkennung(rel):
            api.texte["E100"] = api.texte.get("E100", "") + "wort "
        n = len(api.einfuege_aufrufe)
        w.takt()
        if len(api.einfuege_aufrufe) > n:
            zeiten.append(rel)
    return zeiten


def neu_pause(text="", mik=SM_MIK):
    w, api, uhr, logs, warn, box = neu_waechter(cfg=cfg_s, senf=SENF)
    api.mikro = mik
    takte(w, uhr, 1)
    oeffnen(api, uhr, text=text)
    api.t_auf = uhr.t
    return w, api, uhr, logs


# RH 126: Georg wartet bewusst, Mikrofon „aktiv (CASSpeechMagic)“ ab dem Öffnen, kein Pegel → eingefügt
w, api, uhr, logs = neu_pause(text="Diktat vom Arzt.\r\n")
z = lauf(w, api, uhr, 10, sprache=lambda t: 0.003)
check("RH 126: Mikrofon ab dem Öffnen „aktiv (CASSpeechMagic)“, niemand spricht → eingefügt, genau einmal, ≥ 2 s nach dem Öffnen",
      len(z) == 1 and z[0] >= M.PAUSE_S and all(x in api.texte["E100"] for x in SENF_Z), (z, logs))
check("… Log „Pause erkannt (x s still …)“", any(re.search(r"Pause erkannt \(\d+\.\d s still", l) for l in logs), logs)

# Aufnahme startet 1 s nach dem Öffnen (Georg), Dauersprechen 60 s → nie
w, api, uhr, logs = neu_pause()
z = lauf(w, api, uhr, 60, sprache=lambda t: 0.0 if t < 1.0 else 0.35, erkennung=lambda t: t > 1.5)
check("Aufnahme 1 s nach dem Öffnen, 60 s Dauersprechen → nie eingefügt", z == [] and api.einfuege_aufrufe == [], (z, logs))
check("… Log „es wird gesprochen“", any("es wird gesprochen" in l for l in logs), logs)
# Sprechen mit kurzen Atempausen (≤ 1 s still) → nie
w, api, uhr, logs = neu_pause()
z = lauf(w, api, uhr, 40, sprache=lambda t: 0.0 if t < 1.0 or (t % 3.0) < 1.0 else 0.3, erkennung=lambda t: t > 1.5)
check("Sprechen mit Atempausen ≤ 1 s → nie eingefügt", z == [], (z, logs))

# Pause 3 s mitten im Diktat → eingefügt (erst wenn Pegel ≥ 2 s still UND Feld ≥ 2 s unverändert)
w, api, uhr, logs = neu_pause()
spricht = lambda t: 0.3 if 1.0 <= t < 10.0 or 13.0 <= t < 30.0 else 0.0   # noqa: E731
erk = lambda t: 1.5 <= t < 10.5 or 13.5 <= t < 30.5                          # noqa: E731  Erkennung hinkt 0,5 s nach
z = lauf(w, api, uhr, 40, sprache=spricht, erkennung=erk)
check("Pause 3 s mitten im Diktat (10–13 s) → genau einmal eingefügt, in der Pause",
      len(z) == 1 and 12.0 <= z[0] < 13.0 and len(api.einfuege_aufrufe) == 1, (z, logs))
check("… frühestens 2 s nach dem letzten Pegel und 2 s nach der letzten Textänderung",
      z and z[0] - 10.0 >= M.PAUSE_S and z[0] - 10.5 >= M.RUHE_GLEICH_S - 0.5, z)
check("… nach der Pause kein zweites Einfügen, Senf genau einmal im Text",
      api.texte["E100"].count(SENF_Z[0]) == 1, api.texte["E100"][-120:])

# Pegel still, aber die Erkennung schreibt noch (Text ändert sich) → warten, Log „Feld nicht ruhig“
w, api, uhr, logs = neu_pause()
z = lauf(w, api, uhr, 20, sprache=lambda t: 0.3 if 1.0 <= t < 3.0 else 0.0, erkennung=lambda t: 1.5 <= t < 8.0)
check("Pegel still, Erkennung schreibt noch bis 8 s → erst danach eingefügt (Feld ≥ 2 s unverändert)",
      len(z) == 1 and z[0] >= 8.0 + M.RUHE_GLEICH_S - 0.5 and any("Feld nicht ruhig" in l for l in logs), (z, logs))

# Pegel unbekannt (Core Audio nicht lesbar) → nie
w, api, uhr, logs = neu_pause()
z = lauf(w, api, uhr, 30, sprache=lambda t: None)
check("Pegel unbekannt → nie eingefügt", z == [], (z, logs))
# ein einzelner stiller Wert nach „unbekannt“ reicht nicht: Pause beginnt erst mit der ersten gültigen Messung
w, api, uhr, logs = neu_pause()
z = lauf(w, api, uhr, 10, sprache=lambda t: None if t < 5.0 else 0.0)
check("nach „unbekannt“ zählt die Pause erst ab der ersten stillen Messung (≥ 2 s danach)",
      len(z) == 1 and z[0] >= 5.0 + M.PAUSE_S - 0.5, (z, logs))

# RH 58 (SpeechMagic überschreibt das Einfügen 1 s später) mit Mikrofon „aktiv (CASSpeechMagic)“ → Kontrolle fängt es ab
w, _, uhr, logs, warn, box = neu_waechter(cfg=cfg_s, senf=SENF)
api = Laedt(uhr, schlucken=1, sofort=False)
api.mikro = SM_MIK
w.api = api
takte(w, uhr, 1)
oeffnen_l(api, uhr)
api.t_auf = uhr.t
lauf(w, api, uhr, 30, sprache=lambda t: 0.0)
t = api.texte["E100"]
check("RH 58 bei SpeechMagic-Mikrofon „aktiv“: überschrieben → Kontrolle, erneut in der Pause, am Ende genau einmal",
      len(api.einfuege_aufrufe) == 2 and t.count(SENF_Z[0]) == 1
      and any("nicht mehr im Text – Versuch 1/3" in l for l in logs), (t, logs))
# … während des Wiederholungs-Abstands wird gesprochen → zweiter Versuch erst in der nächsten Pause
w, _, uhr, logs, warn, box = neu_waechter(cfg=cfg_s, senf=SENF)
api = Laedt(uhr, schlucken=1, sofort=False)
api.mikro = SM_MIK
w.api = api
takte(w, uhr, 1)
oeffnen_l(api, uhr)
api.t_auf = uhr.t
z = lauf(w, api, uhr, 40, sprache=lambda t: 0.3 if 4.0 <= t < 20.0 else 0.0)
check("RH 58 + Sprechen ab 4 s: Wiederholung nie während gesprochen wird, erst in der Pause danach",
      len(z) == 2 and z[1] >= 20.0 + M.PAUSE_S - 0.5 and api.texte["E100"].count(SENF_Z[0]) == 1, (z, logs))
check("Pegel-Messung nur, solange etwas einzufügen ist (nicht dauernd)",
      api.pegel_aufrufe < 40 / 0.5, api.pegel_aufrufe)
check("Win32.pegel: Core Audio nicht lesbar (hier: kein Windows) → (None, 0) = unbekannt, nie Ausnahme",
      M.Win32.pegel(types.SimpleNamespace(_sm_pids={7}, _pids=lambda: [7])) == (None, 0))
check("Selbsttest zeigt den Sprachpegel (für die Abnahme am PC)",
      "pegel={api.pegel()}" in (ROOT / "source_code/RaKScribe.py").read_text(encoding="utf-8"))
check("Konstanten: Pause 2 s, Feld 2 s, Schwelle < 0,05", M.PAUSE_S == 2.0 and M.RUHE_GLEICH_S == 2.0
      and 0 < M.PEGEL_STILL < 0.05)

# Senf kommt später: läuft → fertig (nachladen alle 15 s)
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=dict(SENF, status="laeuft"))
takte(w, uhr, 1)
oeffnen(api, uhr, text="Diktat begonnen.")
takte(w, uhr, 6)
n_ibl = len(api.einfuege_aufrufe)
senf_box["d"] = SENF
takte(w, uhr, 20, 1.0)
check("Senf läuft beim Öffnen → IB Lab sofort, Senf nach dem Nachladen (eigenes Einfügen)",
      n_ibl == 1 and len(api.einfuege_aufrufe) == 2 and "[SENF" in api.einfuege_aufrufe[1][1]
      and "Pes cavus" not in api.einfuege_aufrufe[1][1], api.einfuege_aufrufe)
check("… Umbruch vor dem Block, wenn schon Diktat dasteht", api.einfuege_aufrufe[0][1].startswith("\r\n"))
# kein Senf nach 10 min → aufgeben
w, api, uhr, logs, warn, senf_box = neu_waechter(cfg=cfg2, senf=None)
takte(w, uhr, 1)
oeffnen(api, uhr)
for _ in range(45):
    uhr.t += 15
    w.takt()
check("kein Senf nach 10 min → aufgegeben, nichts eingefügt, kein Dauer-Nachladen",
      api.einfuege_aufrufe == [] and any("kein Senf" in l for l in logs), logs[-3:])

# Diktatnummer unklar: Fenster ohne passenden frischen Start (residenter Prozess von früher, Startprozess verpasst)
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
api.procs.append((7, uhr.t - 3600, CMD))           # residenter Prozess, Befehlszeile einer alten Nummer
takte(w, uhr, 1)
api.wins.append((100, 7, TITEL))
api.texte["E100"] = ""
takte(w, uhr, 10, 1.0)
check("Fenster eines alten (residenten) Prozesses → Nummer unklar, nichts eingefügt",
      api.einfuege_aufrufe == [] and any("unklar" in l for l in logs), logs)
# residenter Prozess + frischer Startprozess mit neuer Nummer → die neue gilt
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
api.procs.append((7, uhr.t - 3600, CMD.replace("-n 31", "-n 5")))
takte(w, uhr, 1)
api.procs.append((9, uhr.t - 0.3, CMD))            # Startprozess (endet gleich wieder)
takte(w, uhr, 1)
api.procs = [p for p in api.procs if p[0] != 9]
api.wins.append((100, 7, TITEL))
api.texte["E100"] = ""
takte(w, uhr, 6)
check("residenter Prozess übernimmt: Befehlszeile des kurzen Startprozesses zählt (Nr 031, nicht 005)",
      len(api.einfuege_aufrufe) == 1 and any(NR in l and "erkannt" in l for l in logs), logs)
# Live 21.11. (L1, Diktat 036): Startprozess lebt kürzer als ein Takt – nur die Startwache (50 ms) sieht ihn
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
api.procs.append((7, uhr.t - 3600, CMD.replace("-n 31", "-n 5")))
takte(w, uhr, 1)
check("Startwache nur bei Freigabe aktiv", w.schnell() is True)
uhr.t += 0.05
api.procs.append((9, uhr.t - 0.02, CMD))
w.starts_erfassen()                                # zwischen zwei Takten
api.procs = [p for p in api.procs if p[0] != 9]    # nach 0,2 s wieder weg
uhr.t += 0.2
api.wins.append((100, 7, TITEL))
api.texte["E100"] = ""
takte(w, uhr, 6)
check("… Startprozess nur zwischen zwei Takten sichtbar → Nummer trotzdem richtig, eingefügt",
      len(api.einfuege_aufrufe) == 1 and any(NR in l and "erkannt" in l for l in logs), logs)
w2, *_ = neu_waechter(senf=SENF, freigabe=False)
w2.takt()
check("Startwache ohne Freigabe aus (keine Prozessliste alle 50 ms)", w2.schnell() is False)

# KaiScribe startet, während schon ein Diktat offen ist → dieses Fenster nie
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
oeffnen(api, uhr)
takte(w, uhr, 10, 1.0)
check("Diktat war schon vor KaiScribe offen → nicht angefasst", api.einfuege_aufrufe == [])
# steht schon da (z. B. von Hand kopiert) → nur merken
w, api, uhr, logs, warn, senf_box = neu_waechter(cfg=cfg2, senf=SENF)
takte(w, uhr, 1)
oeffnen(api, uhr, text="Diktat.\n" + "\n".join(M.senf_zeilen(SENF)[1]) + "\n")
takte(w, uhr, 6)
check("Senf steht schon im Diktat → nicht doppelt, nur gemerkt", api.einfuege_aufrufe == []
      and "senf" in w.merker.lesen(NR)["eingefuegt"], logs)
# Merker nicht schreibbar → nie einfügen
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF, ordner=os.path.join(tmp, "datei_statt_ordner"))
open(os.path.join(tmp, "datei_statt_ordner"), "w").write("x")
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
check("Merker nicht schreibbar → nichts eingefügt (lieber nichts als doppelt)", api.einfuege_aufrufe == []
      and any("Merker nicht schreibbar" in l for l in logs), logs)


# Fehler im Fenster → still nichts, Takt läuft weiter
class Kaputt(Api):
    def einfuegen(self, edit, text):
        raise RuntimeError("weg")


w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
w.api = api = Kaputt(uhr)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 6)
check("Fehler beim Einfügen → nichts, Log, kein Absturz", any("Fehler RuntimeError" in l for l in logs), logs)

# Thread: Takt alle 0,5 s, dazwischen Startwache alle 50 ms (nur wenn schnell())
class Zaehler:
    def __init__(self):
        self.takte, self.erfasst = 0, 0
        self.merker = types.SimpleNamespace(aufraeumen=lambda: 0)

    def takt(self):
        self.takte += 1

    def schnell(self):
        return True

    def starts_erfassen(self):
        self.erfasst += 1


import time as _t  # noqa: E402
# sm-senf-laenge-n1: macOS bündelt Timer unter Last (Event.wait(0.05) dauerte 0,23 s) → Erwartung an die gemessene
# Wartegenauigkeit dieses Rechners anpassen (Windows/CI: ~0,05 s → wie bisher ≥ 10)
_e, _t0 = __import__("threading").Event(), _t.monotonic()
for _ in range(5):
    _e.wait(M.STARTWACHE_S)
_g = max(M.STARTWACHE_S, (_t.monotonic() - _t0) / 5)
z = Zaehler()
th = M.Thread(z, log=lambda *a: None).start()
_t.sleep(1.2)
th.stop()
_soll = max(1, min(10, int(0.6 / _g)))
check(f"Thread: ~2 Takte in 1,2 s, dazwischen ≥ {_soll}× Startwache", 2 <= z.takte <= 4 and z.erfasst >= _soll,
      (z.takte, z.erfasst, round(_g, 3)))

# Merker lokal + X: (Wiederöffnen an einem anderen PC)
lok1, lok2, xo = tempfile.mkdtemp(), tempfile.mkdtemp(), tempfile.mkdtemp()
m1, m2 = M.Merker(lok1, xo), M.Merker(lok2, xo)
m1.schreiben(NR, ["senf"])
check("Merker: zweiter PC (anderer lokaler Ordner) sieht den Eintrag über X:", "senf" in m2.lesen(NR)["eingefuegt"])
alt = os.path.join(lok1, "20261101001.json")
open(alt, "w").write("{}")
os.utime(alt, (0, 0))
check("Merker: lokale Einträge älter als 14 Tage werden aufgeräumt", m1.aufraeumen() == 1 and not os.path.exists(alt))


# ───────────────────────────── Teil 3: Win32-Einfügen (Attrappen) ─────────────────────────────
class Clip:
    CF_UNICODETEXT = 13

    def __init__(self):
        self.daten = {13: "Arzt-Text", 49999: b"Format des Arztes"}
        self.offen = False
        self.log = []

    def OpenClipboard(self):
        assert not self.offen
        self.offen = True

    def CloseClipboard(self):
        self.offen = False

    def EnumClipboardFormats(self, f):
        ks = sorted(self.daten)
        if f == 0:
            return ks[0] if ks else 0
        i = ks.index(f) + 1
        return ks[i] if i < len(ks) else 0

    def GetClipboardData(self, f):
        return self.daten[f]

    def EmptyClipboard(self):
        self.daten = {}

    def SetClipboardData(self, f, d):
        self.daten[f] = d


clip = Clip()
sys.modules["win32clipboard"] = clip
wi = object.__new__(M.Win32)
gesendet = []
feld = {"text": "Diktat.", "sel": (3, 5)}


def sende(h, msg, wp=0, lp=0, frist=2000):
    gesendet.append((msg, wp, lp))
    if msg == 0x00B0:
        a, e = feld["sel"]
        return a | (e << 16)
    if msg == 0x00B1:
        feld["sel"] = (min(wp, len(feld["text"])), min(lp, len(feld["text"])))
        return 0
    if msg == 0x0302:
        a, e = feld["sel"]
        feld["text"] = feld["text"][:a] + clip.daten[13] + feld["text"][e:]
        feld["sel"] = (a + len(clip.daten[13]),) * 2
        return 0
    return 0


wi._sende = sende
ok, grund = wi.einfuegen(42, "\r\n[SENF] unauffällig")
check("Win32: Text landet am ENDE (nicht an der Cursorstelle des Arztes)", ok and feld["text"] == "Diktat.\r\n[SENF] unauffällig",
      (ok, grund, feld))
check("Win32: Markierung des Arztes danach exakt wie vorher (3–5)", feld["sel"] == (3, 5), feld)
check("Win32: Zwischenablage danach wie vorher (Text + eigenes Format), Zwischenablage geschlossen",
      clip.daten == {13: "Arzt-Text", 49999: b"Format des Arztes"} and not clip.offen, clip.daten)
check("Win32: Reihenfolge Markierung lesen → ans Ende → WM_PASTE → Markierung zurück",
      [g[0] for g in gesendet] == [0x00B0, 0x00B1, 0x0302, 0x00B1], gesendet)


def sende_haengt(h, msg, wp=0, lp=0, frist=2000):
    return None if msg == 0x0302 else sende(h, msg, wp, lp, frist)


wi._sende = sende_haengt
feld.update(text="Diktat.", sel=(7, 7))
ok, grund = wi.einfuegen(42, "x")
check("Win32: Fenster antwortet nicht → (False, Grund), Zwischenablage trotzdem zurück",
      not ok and "antwortet" in grund and clip.daten[13] == "Arzt-Text", (ok, grund))
wi._sende = lambda *a, **k: 0xFFFFFFFF
check("Win32: Markierung nicht lesbar (Text > 64k) → nichts", wi.einfuegen(42, "x") == (False, "Markierung nicht lesbar"))

# Übernehmen in Win32: RichEdit zählt Absätze als ein Zeichen (\r), WM_GETTEXT liefert \r\n
class Feld:
    def __init__(self, text, sel, crlf_intern=False):
        self.t = text.replace("\r\n", "\n").replace("\n", "\r\n" if crlf_intern else "\r")
        self.sel, self.crlf, self.undo = sel, crlf_intern, []

    def gettext(self):
        return self.t if self.crlf else self.t.replace("\r", "\r\n")

    def sende(self, h, msg, wp=0, lp=0, frist=2000):
        if msg == 0x00B0:
            return self.sel[0] | (self.sel[1] << 16)
        if msg == 0x00B1:
            self.sel = (wp, lp)
        if msg == 0x0303:
            a, e = self.sel
            self.undo.append(self.t)
            self.t = self.t[:a] + self.t[e:]
            self.sel = (a, a)
        if msg == 0x00C7 and self.undo:
            self.t = self.undo.pop()
        return 0


for crlf in (False, True):
    f = Feld("Diktat.\r\n[SENF] Gelenkerguss\r\n[SENF] Fabella", (3, 3), crlf_intern=crlf)
    wi2 = object.__new__(M.Win32)
    wi2._sende = f.sende
    wi2.text = lambda edit, f=f: f.gettext()
    ok, n, grund = wi2.marken_entfernen(1, (M.SENF_FOLGE, M.MARKE_KURZ))
    check(f"Win32 Übernehmen ({'CRLF' if crlf else 'CR'} intern): 2 Marken weg, Text sonst gleich, Cursor (3) unverändert",
          ok and n == 2 and f.gettext().replace("\r\n", "\n").replace("\r", "\n") == "Diktat.\nGelenkerguss\nFabella"
          and f.sel == (3, 3), (ok, n, grund, repr(f.gettext()), f.sel))
f = Feld("[SENF] Erguss\r\nDiktat", (20, 20))
wi2._sende, wi2.text = f.sende, (lambda edit, f=f: f.gettext())
ok, n, grund = wi2.marken_entfernen(1, (M.SENF_FOLGE, M.MARKE_KURZ))
check("Win32 Übernehmen: Cursor hinter der Marke rückt um die gelöschten Zeichen nach vorn",
      ok and f.sel == (20 - len(M.SENF_FOLGE),) * 2, (ok, f.sel))


class Stur(Feld):
    def sende(self, h, msg, wp=0, lp=0, frist=2000):
        if msg == 0x0303:              # löscht das Falsche
            self.undo.append(self.t)
            self.t = self.t[1:]
            return 0
        return Feld.sende(self, h, msg, wp, lp, frist)


f = Stur("Diktat.\r\n[SENF] Erguss", (0, 0))
wi2._sende, wi2.text = f.sende, (lambda edit, f=f: f.gettext())
vorher = f.gettext()
ok, n, grund = wi2.marken_entfernen(1, (M.SENF_FOLGE, M.MARKE_KURZ))
check("Win32 Übernehmen: Text weicht nach dem Löschen ab → Rückgängig, Text unverändert, ok=False",
      not ok and n == 0 and f.gettext() == vorher, (ok, n, grund, f.gettext()))
del sys.modules["win32clipboard"]

# ───────────────────────────── Teil 4: Konfiguration + Fenster ─────────────────────────────
d = tempfile.mkdtemp()
p = os.path.join(d, "config.ini")
open(p, "w", encoding="utf-8").write("[SETTINGS]\nLLM_PROVIDER = gemini\n")
c = C.load_config(p)
check("config: Standard SM_SENF = SM_IBL = kp, Taste Übernehmen Strg+Alt+S",
      c.sm_senf == ["kp"] and c.sm_ibl == ["kp"] and c.sm_uebernehmen_taste == "ctrl+alt+s")
open(p, "w", encoding="utf-8").write("[SETTINGS]\nSM_SENF = aus\nSM_IBL = kp, MH\n")
c = C.load_config(p)
check("config: SM_SENF = aus → niemand, SM_IBL = kp, MH → [kp, mh]", c.sm_senf == [] and c.sm_ibl == ["kp", "mh"])
check("config.ini im Repo dokumentiert SM_SENF/SM_IBL",
      "SM_SENF" in (ROOT / "config.ini").read_text(encoding="utf-8")
      and "SM_IBL" in (ROOT / "config.ini").read_text(encoding="utf-8"))
check("ohne Windows kein Win32 (Wächter bleibt aus)", M.win32_oder_none() is None)
src = (ROOT / "source_code/RaKScribe.py").read_text(encoding="utf-8")
check("KaiScribe-Fenster startet den Wächter, Warnung über Warteschlange (nie aus dem Thread in Tk)",
      "self._sm_start()" in src and "w.uebernehmen_anfordern" in src and "_sm_warnungen.append" in src and "popleft" in src)
check("EXE-Bau nimmt das Modul mit", "--hidden-import=sm_einfuegen" in (ROOT / ".github/workflows/build-exe.yml").read_text())
check("Senf im KaiScribe-Diktatweg bleibt unberührt: senf_anzeige wird hier nur gelesen, nicht geändert",
      "Der Senf landet NIE von selbst in Befund" in (ROOT / "source_code/senf_anzeige.py").read_text(encoding="utf-8"))

print(f"\n{'ALLE GRÜN' if not fails else f'{fails} FEHLER'}")
sys.exit(1 if fails else 0)
