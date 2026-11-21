"""Senf + auffällige IB-Lab-Sätze automatisch ins SpeechMagic-Diktatfenster (senf-ibl-speechmagic-paste-n1, Peter
21.11.2026) — Logik ohne Tk/Windows importierbar und testbar; Win32 nur in der Klasse Win32 (ctypes + win32clipboard).

Peter 21.11.2026: „um unnötige klicks zu ersparen kopier gleich den senf ins speechmagic Fenster. Du kannst auch
pathologische ibl Befunde (zB pes planus usw) ins speechmagic pasten“. Das ändert bewusst seine Regel vom 19./20.11.
(„Senf nie automatisch in Diktat/Befund“) — aber NUR für das SpeechMagic-Fenster und nur für die Kürzel aus SM_SENF /
SM_IBL (Standard kp). Das Senf-Feld im KaiScribe-Fenster (senf_anzeige.py) bleibt, wie es ist; der KaiScribe-Diktatweg
(Brücke, EOL-Datei) bekommt den Senf weiterhin nie.

Ablauf (eigener Hintergrund-Thread, Takt 0,5 s, blockiert die Oberfläche nie):
  1. Erkennen: sichtbares Fenster „CASOnline Diktat … User: <kz>“ eines Prozesses CASSpeechMagic.exe (belegt in der
     Teststrecke hermi-n8b). Die Diktatnummer steht nur in der Befehlszeile, mit der CAS den Prozess startet:
     „CASSpeechMagic.exe -p <PatId> -d <JJJJMMTT> -n <nnn> -u <kz> -h … -a i“ → Nr = -d + -n dreistellig (wie die Brücke).
     Läuft schon ein CASSpeechMagic, übernimmt er das Diktat und der neue Prozess endet sofort — darum gilt eine
     Befehlszeile nur, wenn ihr Prozess höchstens START_FENSTER_S vor dem Fenster entstanden ist und das Kürzel zum
     Fenstertitel passt. Unklar → für dieses Fenster nichts (lieber nichts als ins falsche Diktat).
  2. Inhalt: Senf aus der Ablage der VM (senf_anzeige.lesen, Ordner + Zwilling, jüngstes Ergebnis gewinnt; nachladen
     alle 15 s, höchstens 10 min) — nur Status „fertig“, die Zeile(n) der Ablage ohne Mess-/JSON-Zeilen, jede mit „[SENF“
     davor (erste: SENF_KOPF). IB Lab aus der Ablage des Abholers (X:\\IBL-Vorbefunde\\<Nr><Ziffer>_<modul>.json, dieselbe
     Datei wie Brücke/Formatierer) → ibl_bausteine.auffaellige_zeilen: genau die pathologischen Sätze/Ergebnispunkte, die
     KaiScribe im eigenen Befund einsetzt und markiert — wörtlich, nie umformuliert; Normalbefunde/„kein Text“ ergeben nichts.
  3. Einfügen nur, wenn gerade NICHT aufgenommen wird (Windows-Mikrofonanzeige: keine App nutzt das Mikrofon; unbekannt
     → warten). Text ans ENDE des Diktats (WM_PASTE an das Textfeld, ohne Fokuswechsel), Cursor/Markierung des Arztes
     danach genau wie vorher, Zwischenablage danach zurück. Jeder Text höchstens EINMAL je Diktatnummer (Merker lokal +
     auf X:, vor dem Einfügen geschrieben; steht der Text schon im Fenster, wird nur gemerkt). Jeder Fehler → nichts.
  4. Sicherheitsnetz: Schließt das Diktatfenster, während noch eine „[SENF“-Zeile drinsteht → deutliche Warnung im
     KaiScribe-Fenster + Merker „senf_offen“ (für eine spätere Prüfung der Vidierliste). KaiScribe ändert den Brief nie.
Schalter: SM_SENF / SM_IBL in config.ini (Kürzel, Standard kp, „aus“ = niemand) und zentral die Freigabe
SM_FREIGABE_DATEI im Brücken-Ordner auf X: (fehlt = AUS, Release-Regel Georg: erst nach dem Lauf an 451898) sowie der
Notschalter SM_AUS_DATEI (liegt = AUS). Netz: alles bleibt in der Ordination, an keine KI geht etwas.
Tests: tests/offline/test_sm_einfuegen.py
"""
import json
import os
import re
import threading
import time

import ibl_bausteine as _ibl
import senf_anzeige as _senf
import umzug as _umzug

SM_STANDARD = ("kp",)
EXE_NAME = "casspeechmagic.exe"
MARKE = "[SENF"
SENF_KOPF = "[SENF – Hinweis, vor Vidieren löschen] "
SENF_FOLGE = "[SENF] "
SENF_UNAUFFAELLIG = "[SENF] unauffällig"
SENF_NICHT_BEURTEILBAR = "[SENF] nicht beurteilbar"
TAKT_S = 0.5
START_FENSTER_S = 60        # Befehlszeile gilt nur, wenn ihr Prozess so kurz vor dem Fenster entstand
TEXT_LESEN_S = 1.0          # Fenstertext nachlesen (für „steht schon da“ und das Sicherheitsnetz)
IBL_NACHLADEN_S = 20
IBL_MAX_S = 30 * 60         # IB-Lab-Ergebnisse höchstens so lange nach dem Öffnen nachreichen
SCHALTER_S = 30             # Freigabe-/Notschalter-Datei so oft prüfen
MERKER_TAGE = 14
SM_FREIGABE_DATEI = "speechmagic_einfuegen_an.txt"
SM_AUS_DATEI = "speechmagic_einfuegen_aus.txt"
SCHALTER_ORDNER_STANDARD = "X:\\" + _umzug.NAME + "\\Bruecke"
MERKER_X_STANDARD = "X:\\" + _umzug.NAME + "\\Daten\\speechmagic"
WARNUNG = ("Im SpeechMagic-Diktat {nr} stand beim Schließen noch eine [SENF]-Zeile.\n"
           "Bitte vor dem Vidieren löschen (der Brief wird von KaiScribe nicht geändert).")

_NR = re.compile(r"^\d{11}$")
_MESS = re.compile(r"^\s*(?:MESSUNG|ZIEL|JSON)\b|^\s*[{\[]", re.I)
_TITEL = re.compile(r"^\s*casonline\s+diktat\b", re.I)
_TITEL_USER = re.compile(r"user:\s*([A-Za-z0-9_]{1,8})\s*$", re.I)


# ───────────────────────────── reine Logik ─────────────────────────────
def kommandozeile(cmd):
    """Befehlszeile von CASSpeechMagic → {"nr", "benutzer", "patid"} oder None (keine gültige Nummer/Kürzel)."""
    t = str(cmd or "")
    werte = {}
    for m in re.finditer(r"(?:^|\s)-([pdnu])\s+(\"?)([^\s\"]+)\2", t, re.I):
        werte.setdefault(m.group(1).lower(), m.group(3))
    d, n, u = werte.get("d", ""), werte.get("n", ""), werte.get("u", "")
    if not re.fullmatch(r"\d{8}", d) or not re.fullmatch(r"\d{1,4}", n) or not re.fullmatch(r"[A-Za-z0-9_]{1,8}", u):
        return None
    nr = f"{d}{int(n):03d}"
    if not _NR.match(nr):
        return None
    return {"nr": nr, "benutzer": u.lower(), "patid": werte.get("p", "")}


def diktat_titel(titel):
    """„CASOnline Diktat - … User: kp“ → "kp"; anderes Fenster → None."""
    t = str(titel or "").strip()
    if not _TITEL.match(t):
        return None
    m = _TITEL_USER.search(t)
    return m.group(1).lower() if m else None


def senf_zeilen(d):
    """Ablage-Inhalt (dict) → ("fertig", [Zeilen fürs Diktat]) | ("warten", []) | ("nichts", []).
    Nur „fertig“ ergibt Text; solange weitere Serien laufen, wird gewartet."""
    if not isinstance(d, dict):
        return "warten", []
    st = str(d.get("status") or "").strip().lower()
    if st == _senf.LAEUFT:
        return "warten", []
    if st != _senf.FERTIG:
        return "nichts", []
    if d.get("weitere_laufen"):
        return "warten", []
    bef = str(d.get("befund") or "").strip().lower()
    zeilen = [z for z in (" ".join(str(x).split()) for x in (d.get("zeilen") or [])) if z and not _MESS.match(z)]
    zeilen = [z[:300] for z in zeilen][:6]
    if bef == "unauffaellig":
        return "fertig", [SENF_UNAUFFAELLIG]
    if bef == "nicht_beurteilbar":
        return "fertig", [SENF_NICHT_BEURTEILBAR] + [SENF_FOLGE + z for z in zeilen]
    if not zeilen:
        return "nichts", []
    return "fertig", [SENF_KOPF + zeilen[0]] + [SENF_FOLGE + z for z in zeilen[1:]]


def _texte(x):
    return [s.strip() for s in x if isinstance(s, str) and s.strip()] if isinstance(x, list) else []


def _seiten(d, befundteil):
    """Seiten wie die Brücke (ris-mods bruecke/ibl_bausteine._seiten): Quellen des Abholers, sonst die Befundzeilen."""
    out = set()
    for q in d.get("quellen") or []:
        for s in (q.get("seiten") or []) if isinstance(q, dict) else []:
            s = str(s or "").strip().lower()
            if s in ("rechts", "re", "r", "right"):
                out.add("rechts")
            elif s in ("links", "li", "l", "left"):
                out.add("links")
            elif s in ("beidseits", "bds", "b", "bilateral", "both"):
                out |= {"rechts", "links"}
    for z in befundteil:
        out |= set(re.findall(r"(?<!\w)(rechts|links)(?!\w)", z))
    return [s for s in ("rechts", "links") if s in out]


_IBL_NAME = re.compile(r"^(\d{12})_([a-z0-9]+)\.json$", re.I)


def ibl_bausteine_lesen(ablage, nr, listdir=os.listdir, oeffnen=open):
    """Bausteine des Abholers zur Diktatnummer, im Format der Brücke (cas_ibl, ris-mods bruecke/ibl_bausteine.
    baustein_lesen) → Liste von dicts. Ablage fehlt/aus → []. Wirft nie."""
    if not ablage or str(ablage).strip().lower() in ("aus", "-", "0", "nein") or not _NR.match(str(nr or "")):
        return []
    try:
        namen = sorted(listdir(ablage))
    except OSError:
        return []
    out = []
    for n in namen:
        m = _IBL_NAME.match(n)
        if not m or not m.group(1).startswith(nr):
            continue
        accno, modul = m.group(1), m.group(2).lower()
        try:
            with oeffnen(os.path.join(ablage, n), "r", encoding="utf-8-sig") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or d.get("format") != _ibl.ABLAGE_FORMAT or not isinstance(d.get("vorbefund"), dict):
            continue
        if str(d.get("accession_number") or accno).strip() != accno or str(d.get("modul") or modul).lower() != modul:
            continue
        v = d["vorbefund"]
        befundteil = _texte(v.get("befundteil"))
        b = {"accno": accno, "ziffer": int(accno[-1]), "modul": modul, "name": "", "modul_name":
             str(d.get("modul_name") or ""), "version": d.get("version") or 0, "aktualisiert": str(d.get("aktualisiert") or ""),
             "seiten": _seiten(d, befundteil), "befundteil": befundteil, "ergebnis": _texte(v.get("ergebnis_punkte")),
             "hinweise": _texte(v.get("hinweise_fuer_befunder")), "nicht_zugeordnet": _texte(v.get("nicht_zugeordnet"))}
        b["name"] = {"frog": "FROG", "squirrel": "SQUIRREL", "hippo": "HIPPO", "koala": "KOALA", "lama": "LAMA",
                     "panda": "PANDA", "rho": "Rho", "rbfracture": "RBfracture"}.get(modul, modul.upper())
        bt = v.get("befundtext")
        bt = bt.get(modul) if isinstance(bt, dict) else None
        if isinstance(bt, dict) and bt.get("format") == 1:
            b["befundtext"] = bt
        if modul == "rho":                       # wie Brücke 2.5.21 fuer_rakscribe: Rho nie als Text
            b["befundteil"], b["ergebnis"] = [], []
        out.append(b)
    return out


def ibl_zeilen(liste):
    """Bausteine (Brücken-Format) → [(schlüssel "ibl:<AccNo>_<modul>", [pathologische Zeilen wörtlich])], nur mit Text.
    Dieselbe Auswahl wie die Markierung „auffällig“ im KaiScribe-Befund (ibl_bausteine.auffaellige_zeilen)."""
    out = []
    try:
        bausteine = _ibl.aus_liste(liste)
    except Exception:
        return []
    for b in bausteine:
        try:
            zeilen = [" ".join(z.split()) for z in _ibl.auffaellige_zeilen([b])]
        except Exception:
            continue
        zeilen = [z for z in zeilen if z and not _ibl.ist_schluss(z)]
        if zeilen:
            out.append((f"ibl:{b.accno}_{b.modul}", zeilen))
    return out


def _zeilen_im_text(text):
    return {" ".join(z.split()) for z in str(text or "").replace("\r", "\n").split("\n") if z.strip()}


def neue_zeilen(zeilen, text):
    """Zeilen, die noch nicht (als ganze Zeile) im Fenstertext stehen."""
    da = _zeilen_im_text(text)
    return [z for z in zeilen if " ".join(z.split()) not in da]


def block(zeilen, text_vorher):
    """Einfüge-Text fürs Ende des Diktats: eigene Zeilen, mit Zeilenumbruch davor, wenn schon Text dasteht."""
    t = "\r\n".join(zeilen)
    vorher = str(text_vorher or "")
    if vorher.strip() and not vorher.endswith(("\r", "\n")):
        t = "\r\n" + t
    return t


def hat_senf(text):
    return MARKE in str(text or "")


def kuerzel_liste(roh, standard=SM_STANDARD):
    return _senf.kuerzel_liste(roh, standard)


# ───────────────────────────── Merker (einmal je Diktatnummer) ─────────────────────────────
class Merker:
    """Was je Diktatnummer schon eingefügt wurde: lokal (%LOCALAPPDATA%\\RaKScribe\\speechmagic) und auf X: (gilt auch
    nach Wiederöffnen an einem anderen PC). Gelesen wird aus beiden; ein Eintrag gilt, sobald EINE Stelle ihn hat."""

    def __init__(self, ordner_lokal, ordner_x=None, jetzt=time.time):
        self.lokal, self.x, self.jetzt = ordner_lokal, ordner_x, jetzt

    def _ordner(self):
        out = [self.lokal] if self.lokal else []
        if self.x and str(self.x).strip().lower() not in ("aus", "-", ""):
            out.append(_umzug.x_pfad(self.x))
        return out

    def lesen(self, nr):
        d = {"nr": nr, "eingefuegt": {}, "senf_offen": False}
        for o in self._ordner():
            try:
                with open(os.path.join(o, f"{nr}.json"), encoding="utf-8") as f:
                    x = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(x, dict):
                d["eingefuegt"].update(x.get("eingefuegt") or {})
                d["senf_offen"] = d["senf_offen"] or bool(x.get("senf_offen"))
        return d

    def schreiben(self, nr, schluessel=(), senf_offen=None):
        """Einträge ergänzen → True, wenn mindestens eine Stelle geschrieben wurde."""
        d = self.lesen(nr)
        z = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.jetzt()))
        for k in schluessel:
            d["eingefuegt"].setdefault(k, z)
        if senf_offen is not None:
            d["senf_offen"] = bool(senf_offen)
        d["zeit"] = z
        ok = False
        for o in self._ordner():
            try:
                os.makedirs(o, exist_ok=True)
                p = os.path.join(o, f"{nr}.json")
                tmp = f"{p}.{os.getpid()}.tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False)
                os.replace(tmp, p)
                ok = True
            except OSError:
                continue
        return ok

    def aufraeumen(self, tage=MERKER_TAGE):
        """Lokale Merker älter als tage löschen (nur <11 Ziffern>.json)."""
        n = 0
        try:
            for name in os.listdir(self.lokal):
                p = os.path.join(self.lokal, name)
                if re.fullmatch(r"\d{11}\.json", name) and self.jetzt() - os.path.getmtime(p) > tage * 86400:
                    os.remove(p)
                    n += 1
        except OSError:
            pass
        return n


# ───────────────────────────── Ablauf je Fenster ─────────────────────────────
class Sitzung:
    def __init__(self, hwnd, titel, benutzer, nr, t0, senf_an, ibl_an):
        self.hwnd, self.titel, self.benutzer, self.nr, self.t0 = hwnd, titel, benutzer, nr, t0
        self.senf_an, self.ibl_an = senf_an, ibl_an
        self.senf_fertig = not senf_an          # nichts mehr zu tun (eingefügt, gemerkt oder aufgegeben)
        self.senf_offen = []                    # fertige Senf-Zeilen, die noch eingefügt werden müssen
        self.senf_naechst = 0.0
        self.ibl_offen = {}                     # schlüssel → Zeilen
        self.ibl_erledigt = set()
        self.ibl_naechst = 0.0
        self.text = ""
        self.text_zeit = 0.0
        self.senf_eingefuegt = False
        self.mikro_gemeldet = None
        self.edit = None


class Waechter:
    """Takt-Logik (ohne Windows): api liefert Fenster/Prozesse/Text/Mikrofon und fügt ein (Win32 bzw. Attrappe).
    warnen(nr, text) zeigt die Sicherheitsnetz-Warnung (im KaiScribe-Hauptthread)."""

    def __init__(self, api, cfg, merker, log=print, warnen=None, jetzt=time.time, lese_senf=_senf.lesen,
                 lese_ibl=ibl_bausteine_lesen, existiert=os.path.exists):
        self.api, self.cfg, self.merker, self.log = api, cfg, merker, log
        self.warnen = warnen or (lambda nr, text: None)
        self.jetzt, self.lese_senf, self.lese_ibl, self.existiert = jetzt, lese_senf, lese_ibl, existiert
        self.sitzungen = {}            # hwnd → Sitzung | None (ignoriert)
        self.starts = {}               # pid → (erstellt, {nr, benutzer} | None)
        self.vergeben = set()          # pids, deren Befehlszeile schon einem Fenster gehört
        self.erster = True
        self._schalter = (None, -1e9)
        self.eingefuegt_n = 0

    # Schalter
    def frei(self):
        """Freigabe-Datei da und Notschalter nicht da (alle SCHALTER_S geprüft; X: fehlt → AUS)."""
        wert, zeit = self._schalter
        jetzt = self.jetzt()
        if wert is None or jetzt - zeit >= SCHALTER_S:
            o = getattr(self.cfg, "sm_schalter_ordner", SCHALTER_ORDNER_STANDARD)
            try:
                o = _umzug.x_pfad(o)
                neu = bool(self.existiert(os.path.join(o, SM_FREIGABE_DATEI))) and not self.existiert(
                    os.path.join(o, SM_AUS_DATEI))
            except Exception:
                neu = False
            if neu != wert:
                self.log(f"[SM] Einfügen ins SpeechMagic-Fenster {'FREIGEGEBEN' if neu else 'aus'} "
                         f"({SM_FREIGABE_DATEI}{'' if neu else ' fehlt oder ' + SM_AUS_DATEI + ' liegt'})")
            self._schalter = (neu, jetzt)
            wert = neu
        return wert

    def _listen(self):
        return (list(getattr(self.cfg, "sm_senf", SM_STANDARD) or []), list(getattr(self.cfg, "sm_ibl", SM_STANDARD) or []))

    def takt(self):
        senf_l, ibl_l = self._listen()
        if not senf_l and not ibl_l:
            return
        if not self.frei():
            self.sitzungen.clear()
            self.erster = True
            return
        jetzt = self.jetzt()
        # 1. Prozesse: Befehlszeilen neuer CASSpeechMagic-Prozesse merken (der Startprozess lebt oft nur kurz)
        lebend = set()
        for pid, erstellt, cmd in self.api.prozesse():
            lebend.add(pid)
            if pid not in self.starts:
                self.starts[pid] = (erstellt, kommandozeile(cmd))
        for pid in list(self.starts):
            if pid not in lebend and jetzt - self.starts[pid][0] > 2 * START_FENSTER_S:
                del self.starts[pid]
                self.vergeben.discard(pid)
        # 2. Fenster
        offen = {}
        for hwnd, pid, titel in self.api.fenster():
            if diktat_titel(titel):
                offen[hwnd] = (pid, titel)
        for hwnd in list(self.sitzungen):
            s = self.sitzungen[hwnd]
            if hwnd not in offen or (s is not None and offen[hwnd][1] != s.titel):
                self._ende(hwnd)
        for hwnd, (pid, titel) in offen.items():
            if hwnd not in self.sitzungen:
                self.sitzungen[hwnd] = None if self.erster else self._neu(hwnd, titel, senf_l, ibl_l, jetzt)
        self.erster = False
        # 3. je Diktat
        for s in [s for s in self.sitzungen.values() if s is not None]:
            try:
                self._sitzung(s, jetzt)
            except Exception as e:      # nie weiterwerfen – Diktat geht vor
                self.log(f"[SM] {s.nr}: Fehler {type(e).__name__} – nichts eingefügt")
                s.senf_fertig, s.ibl_an = True, False

    def _neu(self, hwnd, titel, senf_l, ibl_l, jetzt):
        benutzer = diktat_titel(titel)
        senf_an = _senf.aktiv(benutzer, senf_l)
        ibl_an = _senf.aktiv(benutzer, ibl_l)
        if not senf_an and not ibl_an:
            return None
        kand = [(erst, pid, p) for pid, (erst, p) in self.starts.items()
                if p and p["benutzer"] == benutzer and pid not in self.vergeben and -5 <= jetzt - erst <= START_FENSTER_S]
        if not kand:
            self.log(f"[SM] SpeechMagic-Diktat ({benutzer}) erkannt, Diktatnummer unklar – nichts eingefügt")
            return None
        erst, pid, p = max(kand)
        self.vergeben.add(pid)
        d = self.merker.lesen(p["nr"])
        s = Sitzung(hwnd, titel, benutzer, p["nr"], jetzt, senf_an, ibl_an)
        if "senf" in d["eingefuegt"]:
            s.senf_fertig = True
            s.senf_eingefuegt = True
        s.ibl_erledigt = {k for k in d["eingefuegt"] if k.startswith("ibl:")}
        self.log(f"[SM] {p['nr']}: SpeechMagic-Diktat ({benutzer}) erkannt – Senf {'an' if senf_an else 'aus'}, "
                 f"IB Lab {'an' if ibl_an else 'aus'}" + (", schon einmal eingefügt" if d["eingefuegt"] else ""))
        return s

    def _ende(self, hwnd):
        s = self.sitzungen.pop(hwnd, None)
        if s is None:
            return
        if hat_senf(s.text):
            self.log(f"[SM] {s.nr}: Diktat geschlossen, [SENF]-Zeile steht noch drin – Warnung")
            try:
                self.merker.schreiben(s.nr, senf_offen=True)
            except Exception:
                pass
            try:
                self.warnen(s.nr, WARNUNG.format(nr=s.nr))
            except Exception:
                pass
        else:
            self.log(f"[SM] {s.nr}: Diktat geschlossen" + (" (Senf-Zeile gelöscht)" if s.senf_eingefuegt else ""))
            if s.senf_eingefuegt:
                try:
                    self.merker.schreiben(s.nr, senf_offen=False)
                except Exception:
                    pass

    def _sitzung(self, s, jetzt):
        if s.edit is None:
            s.edit = self.api.textfeld(s.hwnd)
            if s.edit is None:
                return
        if jetzt - s.text_zeit >= TEXT_LESEN_S:
            t = self.api.text(s.edit)
            if t is not None:
                s.text, s.text_zeit = t, jetzt
        # Senf
        if not s.senf_fertig and not s.senf_offen and jetzt >= s.senf_naechst:
            s.senf_naechst = jetzt + _senf.NACHLADEN_S
            art, d = self.lese_senf(getattr(self.cfg, "senf_ordner", _senf.SENF_ORDNER_STANDARD), s.nr)
            zust, zeilen = senf_zeilen(d) if art == "da" else (("nichts", []) if art == "aus" else ("warten", []))
            if zust == "fertig":
                s.senf_offen = zeilen
            elif zust == "nichts" or jetzt - s.t0 > _senf.NACHLADEN_MAX_S:
                s.senf_fertig = True
                self.log(f"[SM] {s.nr}: kein Senf zum Einfügen ({art if zust != 'nichts' else 'kein Ergebnis'})")
        # IB Lab
        if s.ibl_an and jetzt >= s.ibl_naechst and jetzt - s.t0 <= IBL_MAX_S:
            s.ibl_naechst = jetzt + IBL_NACHLADEN_S
            for k, zeilen in ibl_zeilen(self.lese_ibl(getattr(self.cfg, "ibl_ablage", "X:\\IBL-Vorbefunde"), s.nr)):
                if k not in s.ibl_erledigt and k not in s.ibl_offen:
                    s.ibl_offen[k] = zeilen
        if not s.senf_offen and not s.ibl_offen:
            return
        m = self.api.mikrofon()
        if m != "frei":
            if s.mikro_gemeldet != m:
                self.log(f"[SM] {s.nr}: Mikrofon {m} – warte mit dem Einfügen")
                s.mikro_gemeldet = m
            return
        self._einfuegen(s)

    def _einfuegen(self, s):
        schluessel = list(s.ibl_offen) + (["senf"] if s.senf_offen else [])
        zeilen = [z for k in s.ibl_offen for z in s.ibl_offen[k]] + list(s.senf_offen)
        text = self.api.text(s.edit)
        if text is None:
            return                                  # Fenster antwortet gerade nicht → nächster Takt
        s.text = text
        neu = neue_zeilen(zeilen, text)
        if not self.merker.schreiben(s.nr, schluessel):
            self.log(f"[SM] {s.nr}: Merker nicht schreibbar – nichts eingefügt (nie doppelt)")
            s.senf_offen, s.ibl_offen, s.senf_fertig, s.ibl_an = [], {}, True, False
            return
        s.ibl_erledigt |= set(s.ibl_offen)
        hatte_senf = bool(s.senf_offen)
        s.ibl_offen, s.senf_offen = {}, []
        if hatte_senf:
            s.senf_fertig = True
        if not neu:
            self.log(f"[SM] {s.nr}: {', '.join(schluessel)} steht schon im Diktat – nur gemerkt")
            s.senf_eingefuegt = s.senf_eingefuegt or hatte_senf
            return
        ok, grund = self.api.einfuegen(s.edit, block(neu, text))
        nach = self.api.text(s.edit)
        if nach is not None:
            s.text = nach
        drin = ok and nach is not None and not neue_zeilen(neu, nach)
        if drin:
            self.eingefuegt_n += 1
            s.senf_eingefuegt = s.senf_eingefuegt or hatte_senf
        self.log(f"[SM] {s.nr}: {len(neu)} Zeile(n) ({', '.join(k.split('_')[-1] if k != 'senf' else 'Senf' for k in schluessel)}) "
                 + ("eingefügt, Cursor zurück, Zwischenablage zurück" if drin else f"NICHT eingefügt ({grund or 'nicht im Text'})"))


# ───────────────────────────── Windows ─────────────────────────────
class Win32:
    """Fenster/Prozesse über user32/kernel32/ntdll (ctypes), Zwischenablage über win32clipboard, Mikrofon über die
    Windows-Datenschutzanzeige (Registry CapabilityAccessManager, nur lesen)."""

    def __init__(self, eigene_pid=None):
        import ctypes
        from ctypes import wintypes
        self.c, self.w = ctypes, wintypes
        self.u = ctypes.WinDLL("user32", use_last_error=True)
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.nt = ctypes.WinDLL("ntdll")
        u, k = self.u, self.k
        self._enum_t = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        u.EnumWindows.argtypes = [self._enum_t, wintypes.LPARAM]
        u.EnumChildWindows.argtypes = [wintypes.HWND, self._enum_t, wintypes.LPARAM]
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.IsWindow.argtypes = [wintypes.HWND]
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                          wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
        u.SendMessageTimeoutW.restype = ctypes.c_size_t
        k.OpenProcess.restype = wintypes.HANDLE
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                 ctypes.POINTER(wintypes.DWORD)]
        k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        k.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        self.nt.NtQueryInformationProcess.argtypes = [wintypes.HANDLE, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong,
                                                      ctypes.POINTER(ctypes.c_ulong)]
        self.nt.NtQueryInformationProcess.restype = ctypes.c_long

        class PE32(ctypes.Structure):
            _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                        ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                        ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                        ("szExeFile", ctypes.c_wchar * 260)]
        self.PE32 = PE32
        k.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PE32)]
        k.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PE32)]
        self.eigene_pid = os.getpid() if eigene_pid is None else eigene_pid
        self._sm_pids = set()

    # Prozesse
    def _pids(self):
        """PIDs aller CASSpeechMagic.exe (Toolhelp-Schnappschuss)."""
        c, k = self.c, self.k
        h = k.CreateToolhelp32Snapshot(0x2, 0)
        out = []
        if not h or h == self.w.HANDLE(-1).value:
            return out
        try:
            e = self.PE32()
            e.dwSize = c.sizeof(self.PE32)
            ok = k.Process32FirstW(h, c.byref(e))
            while ok:
                if e.szExeFile.lower() == EXE_NAME:
                    out.append(int(e.th32ProcessID))
                ok = k.Process32NextW(h, c.byref(e))
        finally:
            k.CloseHandle(h)
        return out

    def _cmd_und_zeit(self, pid):
        c, w, k = self.c, self.w, self.k
        h = k.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return None, ""
        try:
            ft = [w.FILETIME() for _ in range(4)]
            erstellt = None
            if k.GetProcessTimes(h, *[c.byref(f) for f in ft]):
                t = (ft[0].dwHighDateTime << 32) | ft[0].dwLowDateTime
                erstellt = t / 1e7 - 11644473600.0
            n = c.c_ulong(0)
            self.nt.NtQueryInformationProcess(h, 60, None, 0, c.byref(n))   # ProcessCommandLineInformation
            cmd = ""
            if 0 < n.value < 65536:
                buf = c.create_string_buffer(n.value)
                if self.nt.NtQueryInformationProcess(h, 60, buf, n.value, c.byref(n)) == 0:
                    laenge = c.c_ushort.from_buffer(buf, 0).value
                    zeiger = c.c_void_p.from_buffer(buf, 8 if c.sizeof(c.c_void_p) == 8 else 4).value
                    if zeiger and laenge:
                        cmd = c.wstring_at(zeiger, laenge // 2)
            return erstellt, cmd
        finally:
            k.CloseHandle(h)

    def prozesse(self):
        out = []
        pids = self._pids()
        self._sm_pids = set(pids)
        for pid in pids:
            try:
                erstellt, cmd = self._cmd_und_zeit(pid)
            except Exception:
                continue
            if erstellt is not None:
                out.append((pid, erstellt, cmd))
        return out

    # Fenster
    def _titel(self, hwnd):
        r = self.c.c_size_t(0)
        if not self.u.SendMessageTimeoutW(hwnd, 0x000E, 0, 0, 2, 500, self.c.byref(r)):   # WM_GETTEXTLENGTH
            return None
        n = min(int(r.value), 200000)
        buf = self.c.create_unicode_buffer(n + 2)
        if not self.u.SendMessageTimeoutW(hwnd, 0x000D, n + 1, self.c.cast(buf, self.c.c_void_p).value, 2, 1000,
                                          self.c.byref(r)):                                  # WM_GETTEXT
            return None
        return buf.value

    def fenster(self):
        pids = self._sm_pids
        out = []
        if not pids:
            return out
        u = self.u

        def cb(h, _l):
            p = self.w.DWORD(0)
            u.GetWindowThreadProcessId(h, self.c.byref(p))
            if p.value in pids and u.IsWindowVisible(h):
                t = self._titel(h)
                if t:
                    out.append((int(h), int(p.value), t))
            return True
        u.EnumWindows(self._enum_t(cb), 0)
        return out

    def textfeld(self, hwnd):
        """Größtes sichtbares RichEdit-Kind (> 100 px hoch), wie die Teststrecke (diktieren.ps1) → hwnd oder None."""
        u, c = self.u, self.c
        kand = []

        def cb(h, _l):
            if u.IsWindowVisible(h):
                buf = c.create_unicode_buffer(256)
                u.GetClassNameW(h, buf, 256)
                if "richedit" in buf.value.lower():
                    r = self.w.RECT()
                    u.GetWindowRect(h, c.byref(r))
                    if r.bottom - r.top > 100:
                        kand.append(((r.bottom - r.top) * (r.right - r.left), int(h)))
            return True
        u.EnumChildWindows(hwnd, self._enum_t(cb), 0)
        return max(kand)[1] if kand else None

    def text(self, edit):
        try:
            if not self.u.IsWindow(edit):
                return None
            return self._titel(edit)
        except Exception:
            return None

    def _sende(self, h, msg, wp=0, lp=0, frist=2000):
        r = self.c.c_size_t(0)
        ok = self.u.SendMessageTimeoutW(h, msg, wp, lp, 2, frist, self.c.byref(r))
        return (int(r.value) if ok else None)

    def einfuegen(self, edit, text):
        """Text ans Ende des Textfelds (WM_PASTE, kein Fokuswechsel); Markierung und Zwischenablage danach wie vorher.
        → (ok, grund)."""
        import win32clipboard as cb
        EM_GETSEL, EM_SETSEL, WM_PASTE = 0x00B0, 0x00B1, 0x0302
        sel = self._sende(edit, EM_GETSEL)
        if sel is None or sel >= 0xFFFFFFFF or sel < 0:
            return False, "Markierung nicht lesbar"
        a, e = sel & 0xFFFF, (sel >> 16) & 0xFFFF
        alt = self._clip_sichern(cb)
        if alt is None:
            return False, "Zwischenablage belegt"
        try:
            if not self._clip_text(cb, text):
                return False, "Zwischenablage belegt"
            if self._sende(edit, EM_SETSEL, 0x7FFFFFFF, 0x7FFFFFFF) is None:
                return False, "Ende nicht setzbar"
            if self._sende(edit, WM_PASTE, 0, 0, frist=5000) is None:
                return False, "Fenster antwortet nicht"
            return True, ""
        finally:
            try:
                self._sende(edit, EM_SETSEL, a, e)         # Cursor/Markierung des Arztes (vor dem eingefügten Ende)
            except Exception:
                pass
            self._clip_zurueck(cb, alt)

    def _clip_offen(self, cb, versuche=10):
        for _ in range(versuche):
            try:
                cb.OpenClipboard()
                return True
            except Exception:
                time.sleep(0.05)
        return False

    def _clip_sichern(self, cb):
        """Alle lesbaren Formate der Zwischenablage → [(format, daten)] bzw. None (belegt)."""
        if not self._clip_offen(cb):
            return None
        out = []
        try:
            f = cb.EnumClipboardFormats(0)
            while f:
                if f not in (2, 3, 9, 14, 0x0080, 0x0081, 0x0082, 0x0083, 0x008E):   # GDI-/Owner-Formate auslassen
                    try:
                        out.append((f, cb.GetClipboardData(f)))
                    except Exception:
                        pass
                f = cb.EnumClipboardFormats(f)
        except Exception:
            pass
        finally:
            try:
                cb.CloseClipboard()
            except Exception:
                pass
        return out

    def _clip_text(self, cb, text):
        if not self._clip_offen(cb):
            return False
        try:
            cb.EmptyClipboard()
            cb.SetClipboardData(cb.CF_UNICODETEXT, text)
            return True
        except Exception:
            return False
        finally:
            try:
                cb.CloseClipboard()
            except Exception:
                pass

    def _clip_zurueck(self, cb, alt):
        if not self._clip_offen(cb, versuche=20):
            return
        try:
            cb.EmptyClipboard()
            for f, d in alt or []:
                try:
                    cb.SetClipboardData(f, d)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            try:
                cb.CloseClipboard()
            except Exception:
                pass

    def mikrofon(self):
        """„aktiv“, wenn irgendeine App gerade das Mikrofon nutzt (Windows-Datenschutzanzeige), „frei“, sonst „unbekannt“."""
        return mikrofon_zustand(_winreg_leser())


def _winreg_leser():
    """→ Funktion, die [(App, LastUsedTimeStart, LastUsedTimeStop)] aller Apps liefert, oder None (Registry nicht lesbar)."""
    try:
        import winreg
    except ImportError:
        return None
    basis = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"

    def werte():
        out = []

        def lese(schluessel, tiefe):
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(schluessel, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(schluessel, name) as s:
                        try:
                            a = winreg.QueryValueEx(s, "LastUsedTimeStart")[0]
                            b = winreg.QueryValueEx(s, "LastUsedTimeStop")[0]
                            out.append((name.split("#")[-1][:60], int(a), int(b)))
                        except OSError:
                            pass
                        if tiefe < 1:
                            lese(s, tiefe + 1)
                except OSError:
                    continue
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, basis) as k:
            lese(k, 0)
        return out
    return werte


def mikrofon_zustand(leser):
    """leser() → [(App, start, stop)] (FILETIME-Zahlen). In Benutzung = start > 0 und stop == 0 oder stop < start.
    → "frei" | "aktiv (<App>)" | "unbekannt" (Registry nicht lesbar → nie einfügen)."""
    if leser is None:
        return "unbekannt"
    try:
        werte = leser()
    except Exception:
        return "unbekannt"
    for app, a, b in werte:
        if a > 0 and (b == 0 or b < a):
            return f"aktiv ({app})"
    return "frei"


def win32_oder_none():
    try:
        return Win32()
    except Exception:
        return None


class Thread:
    """Hintergrund-Thread mit Waechter.takt alle TAKT_S; jeder Fehler wird geloggt und der Takt läuft weiter."""

    def __init__(self, waechter, log=print, takt_s=TAKT_S):
        self.w, self.log, self.takt_s = waechter, log, takt_s
        self._stop = threading.Event()
        self.t = None

    def start(self):
        self.t = threading.Thread(target=self._lauf, name="sm-einfuegen", daemon=True)
        self.t.start()
        return self

    def stop(self):
        self._stop.set()

    def _lauf(self):
        try:
            self.w.merker.aufraeumen()
        except Exception:
            pass
        fehler = 0
        while not self._stop.wait(self.takt_s):
            try:
                self.w.takt()
                fehler = 0
            except Exception as e:
                fehler += 1
                if fehler in (1, 10, 100):
                    self.log(f"[SM] Takt-Fehler {type(e).__name__}: {e}")
