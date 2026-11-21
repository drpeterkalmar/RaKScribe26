"""Gate senf-ibl-speechmagic-paste-n1 (Peter 21.11.2026): Senf + pathologische IB-Lab-Sätze automatisch ins
SpeechMagic-Diktatfenster – nur kp, einmal je Diktatnummer, nie während der Aufnahme, Cursor und Zwischenablage zurück,
IB Lab nur auffällig und wörtlich wie im KaiScribe-Befund, Sicherheitsnetz bei stehen gebliebener [SENF]-Zeile.
Teil 1: reine Logik (Befehlszeile, Titel, Senf-Zeilen, IB-Lab-Ablage → Sätze). Teil 2: Wächter mit Attrappen-Fenster.
Teil 3: Win32-Einfügen (Markierung + Zwischenablage) mit Attrappen für SendMessage und win32clipboard.
Teil 4: KaiScribe-Fenster startet den Wächter nur unter Windows; Konfiguration SM_SENF/SM_IBL.
Synthetische Texte, keine Patientendaten.  Aufruf: python3 tests/offline/test_sm_einfuegen.py"""
import copy, json, os, pathlib, sys, tempfile, types

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
takte(w, uhr, 3)
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
takte(w, uhr, 3)
schliessen(api)
takte(w, uhr, 2)
check("Senf gelöscht, Diktat zu → keine Warnung", warn == [], warn)
uhr.t += 120
oeffnen(api, uhr, hwnd=101, pid=8, text=api.texte["E100"])
takte(w, uhr, 50, 1.0)
check("Wiederöffnen derselben Nummer → nichts doppelt (Merker)", len(api.einfuege_aufrufe) == 1, api.einfuege_aufrufe)

# Übernehmen (Taste): nur die Marken weg, danach keine Warnung beim Schließen
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 3)
api.texte["E100"] = "Kniegelenk rechts: kein Erguss.\n" + api.texte["E100"]
w.uebernehmen_anfordern()
takte(w, uhr, 1)
t = api.texte["E100"]
check("Übernehmen: Marken entfernt, Senf-Inhalt + Diktat + IB-Lab-Sätze bleiben wörtlich",
      "[SENF" not in t and "Gelenkerguss" in t and "Fabella" in t and t.startswith("Kniegelenk rechts: kein Erguss.")
      and "Pes cavus links" in t, t)
check("… Log nennt die Zahl der Marken (ohne Text)", any("Übernehmen – 2 Marke(n) entfernt" in l for l in logs), logs)
api.texte["E100"] += "\nGelenkerguss mit Begleitsynovitis."      # Peter ergänzt frei
takte(w, uhr, 3)
schliessen(api)
takte(w, uhr, 2)
check("… übernommen und frei ergänzt → beim Schließen KEINE Warnung (nur die Marke zählt, nie der Inhalt)", warn == [], warn)
w.uebernehmen_anfordern()
takte(w, uhr, 1)
check("Übernehmen ohne offenes Diktat → nur Log, nichts geändert", any("kein offenes SpeechMagic-Diktat" in l for l in logs))

# Sicherheitsnetz: Senf bleibt stehen, Fenster zu → Warnung + Merker senf_offen
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 3)
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
takte(w, uhr, 5)
check("SM_SENF = aus, SM_IBL = kp → nur die IB-Lab-Sätze", "Pes cavus links" in api.texte["E100"]
      and "[SENF" not in api.texte["E100"], api.texte["E100"])
cfg2 = types.SimpleNamespace(sm_senf=["kp"], sm_ibl=[], senf_ordner="S", ibl_ablage=ABL,
                             sm_schalter_ordner=os.path.join(tmp, "Bruecke"))
w, api, uhr, logs, warn, senf_box = neu_waechter(cfg=cfg2, senf=SENF)
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 5)
check("SM_SENF = kp, SM_IBL = aus → nur der Senf", "[SENF" in api.texte["E100"] and "Pes cavus" not in api.texte["E100"])

# Freigabe-Datei fehlt / Notschalter liegt → nichts
for frei, aus, name in ((False, False, "Freigabe-Datei fehlt"), (True, True, "Notschalter liegt")):
    w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF, freigabe=frei, aus=aus)
    takte(w, uhr, 1)
    oeffnen(api, uhr)
    takte(w, uhr, 10, 1.0)
    check(f"{name} → nichts eingefügt", api.einfuege_aufrufe == [])

# nicht während der Aufnahme
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF)
api.mikro = "aktiv (CASSpeechMagic.exe)"
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 20, 1.0)
check("Aufnahme läuft → wartet, fügt nichts ein (Log einmal)", api.einfuege_aufrufe == []
      and sum("Mikrofon aktiv" in l for l in logs) == 1, logs)
api.mikro = "unbekannt"
takte(w, uhr, 5, 1.0)
check("Mikrofon-Zustand unbekannt → ebenfalls nichts", api.einfuege_aufrufe == [])
api.mikro = "frei"
takte(w, uhr, 2, 1.0)
check("Pause/Stopp → jetzt eingefügt", len(api.einfuege_aufrufe) == 1 and "[SENF" in api.texte["E100"])

# Senf kommt später: läuft → fertig (nachladen alle 15 s)
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=dict(SENF, status="laeuft"))
takte(w, uhr, 1)
oeffnen(api, uhr, text="Diktat begonnen.")
takte(w, uhr, 3)
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
takte(w, uhr, 3)
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
takte(w, uhr, 3)
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
takte(w, uhr, 4)
check("Senf steht schon im Diktat → nicht doppelt, nur gemerkt", api.einfuege_aufrufe == []
      and "senf" in w.merker.lesen(NR)["eingefuegt"], logs)
# Merker nicht schreibbar → nie einfügen
w, api, uhr, logs, warn, senf_box = neu_waechter(senf=SENF, ordner=os.path.join(tmp, "datei_statt_ordner"))
open(os.path.join(tmp, "datei_statt_ordner"), "w").write("x")
takte(w, uhr, 1)
oeffnen(api, uhr)
takte(w, uhr, 5)
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
takte(w, uhr, 5)
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
z = Zaehler()
th = M.Thread(z, log=lambda *a: None).start()
_t.sleep(1.2)
th.stop()
check("Thread: ~2 Takte in 1,2 s, dazwischen ≥ 10× Startwache", 2 <= z.takte <= 4 and z.erfasst >= 10, (z.takte, z.erfasst))

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
