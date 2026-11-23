"""Opus-Senf als schreibgeschützter Hinweis im KaiScribe-Fenster (kaiscribe-senf-anzeige-n1, Peter 20.11.2026) — ohne
Tk/Windows importierbar und testbar.

Peter (Kürzel kp) sieht beim Öffnen eines CAS-Diktats, was der Opus-Senf zur Untersuchung gefunden hat. Die Ablage
schreibt die VM (ris-mods opus_senf 1.7.0, Job opus-senf-n8-ablage): X:\\RaKScribe\\Daten\\senf\\<Diktatnummer>.json
{v, nr, status: laeuft|fertig|fehler|uebersprungen, zeit, befund: auffaellig|unauffaellig|nicht_beurteilbar,
 zeilen: ["RH xx · Untersuchung · Pathologie", …], weitere_laufen, eintraege: […]}.

Harte Regeln (Peter 19./20.11.):
- KaiScribe liest die Ablage NUR (kein Schreiben, kein Löschen).
- Der Senf landet NIE von selbst in Befund, Diktat, EOL-Datei oder Zwischenablage. Das Feld ist ein eigenes Widget;
  kopiert wird nur auf Peters Aktion (Markieren + Strg+C bzw. Knopf „Kopieren“).
- Nur Kürzel aus SENF_ANZEIGE (Standard kp). rg und andere sehen nichts.
- Lesen im Hintergrund-Thread, Frist ≤ 1 s; kein Netz/keine Ablage → Feld aus, Diktieren wird nie verzögert.
"""
import json
import os
import re
import threading

import umzug as _umzug

# Die VM schreibt in den alten Ordner auf X: (ris-mods opus_senf 1.7.0); Name aus umzug (ALT), damit es eine Quelle gibt
SENF_ORDNER_STANDARD = "X:\\" + _umzug.ALT + "\\Daten\\senf"
SENF_ANZEIGE_STANDARD = ("kp",)
LESE_FRIST_S = 1.0          # länger → wie „keine Ablage“ (Feld aus), der Thread darf im Hintergrund weiterhängen
NACHLADEN_S = 5             # solange „läuft“ bzw. noch keine Datei: alle 5 s (kaiscribe-sm-waechter-bleibt-n1, vorher
                            # 15 s: RH 20 am 23.11. kam der Senf 8 s vor EOL und wurde knapp verpasst)
NACHLADEN_MAX_S = 600       # … höchstens 10 min nach dem Öffnen
PRUEF_MS = 100              # wie oft der UI-Takt auf den Lese-Thread schaut (nur Abfrage, kein Warten)
MAX_ZEICHEN = 2000          # Schutz gegen eine kaputte/riesige Datei

LAEUFT = "laeuft"
FERTIG = "fertig"
KEIN = "kein"               # Fehler, übersprungen oder nach 10 min immer noch nichts

TEXT_LAEUFT = "Senf läuft…"
TEXT_UNAUFFAELLIG = "Senf: unauffällig"
TEXT_KEIN = "Senf: kein Ergebnis"
TEXT_NICHT_BEURTEILBAR = "Senf: nicht beurteilbar"
TEXT_WEITERE = "(weitere Serie läuft…)"

_AUS = ("", "aus", "0", "nein", "off", "-")
_NR = re.compile(r"^[0-9]{8,14}$")
_X = re.compile(r"^([A-Za-z]:\\)(" + "|".join((_umzug.ALT, _umzug.NAME)) + r")(\\.*)$", re.I)


def kuerzel_liste(roh, standard=SENF_ANZEIGE_STANDARD):
    """'kp' / 'kp, mh' / '[kp]' → ['kp', 'mh']; leer/aus → []. None → Standard."""
    if roh is None:
        return list(standard)
    t = str(roh).strip().strip("[]").strip()
    if t.lower() in _AUS:
        return []
    return [k for k in (s.strip().strip("'\"").lower() for s in re.split(r"[,;\s]+", t)) if k and k not in _AUS]


def aktiv(benutzer, liste):
    """Nur Kürzel aus der Liste (Groß/Klein egal). Leeres Kürzel → nie."""
    b = str(benutzer or "").strip().lower()
    return bool(b) and b in [str(k).strip().lower() for k in (liste or [])]


def ordner_kandidaten(ordner):
    """Konfigurierter Ordner + sein Zwilling (X:\\RaKScribe\\… ↔ X:\\KaiScribe\\…, Umzug 3.19.19). Die VM schreibt nach
    X:\\RaKScribe\\Daten\\senf; zieht die Ablage einmal um, findet KaiScribe sie ohne neue Version."""
    o = str(ordner or "").strip().strip('"')
    if o.lower() in _AUS:
        return []
    m = _X.match(o)
    if not m:
        return [o]
    lw, name, rest = m.groups()
    anders = _umzug.NAME if name.lower() == _umzug.ALT.lower() else _umzug.ALT
    return [o, lw + anders + rest]


def lesen(ordner, nr, ist_ordner=os.path.isdir, oeffnen=open):
    """Nur lesend. → ("aus", None) keine Ablage/kein Netz/keine Nummer | ("fehlt", None) Ablage da, Datei (noch) nicht
    | ("da", dict)."""
    nr = str(nr or "").strip()
    if not _NR.match(nr):
        return "aus", None
    gefunden = False
    treffer = []                          # alle lesbaren Dateien (Ordner + Zwilling), das jüngste Ergebnis gewinnt
    kaputt = False
    for o in ordner_kandidaten(ordner):
        try:
            if not ist_ordner(o):
                continue
        except OSError:
            continue
        gefunden = True
        p = os.path.join(o, nr + ".json")
        try:
            with oeffnen(p, "r", encoding="utf-8") as f:
                roh = f.read(64 * 1024)
        except FileNotFoundError:
            continue
        except OSError:
            continue
        try:
            d = json.loads(roh)
        except ValueError:
            kaputt = True                 # wird gerade geschrieben → beim nächsten Nachladen wieder
            continue
        if isinstance(d, dict) and str(d.get("nr") or nr) == nr:
            treffer.append(d)
    if treffer:
        # Die VM spiegelt in den Zwilling mit Verzögerung (kaiscribe-senf-anzeige-n1-einspielen, 21.11.: Zwilling stand
        # 1 min auf „laeuft“, der erste Ordner schon auf „fertig“) → nicht „erster Ordner gewinnt“, sondern jüngste
        # „zeit“ (ISO-Text, vergleichbar), bei Gleichstand „fertig“ vor „laeuft“.
        def rang(d):
            return (str(d.get("zeit") or ""), 1 if str(d.get("status") or "").strip().lower() == FERTIG else 0)
        return "da", max(treffer, key=rang)
    if kaputt:
        return "fehlt", None
    return ("fehlt" if gefunden else "aus"), None


def _zeilen(d):
    out = []
    for z in d.get("zeilen") or []:
        z = " ".join(str(z).split())
        if z:
            out.append(z)
    return out


def anzeige(d):
    """Ablage-Inhalt → (zustand, text). zustand: laeuft | fertig | kein."""
    if not isinstance(d, dict):
        return LAEUFT, TEXT_LAEUFT
    st = str(d.get("status") or "").strip().lower()
    if st == LAEUFT:
        return LAEUFT, TEXT_LAEUFT
    if st != FERTIG:
        return KEIN, TEXT_KEIN            # fehler, uebersprungen, unbekannt
    bef = str(d.get("befund") or "").strip().lower()
    zeilen = _zeilen(d)
    if bef == "unauffaellig":
        text = TEXT_UNAUFFAELLIG
    elif bef == "auffaellig":
        text = "\n".join(zeilen) if zeilen else "Senf: auffällig"
    elif bef == "nicht_beurteilbar":
        text = "\n".join([TEXT_NICHT_BEURTEILBAR] + zeilen)
    else:
        text = "\n".join(zeilen) if zeilen else TEXT_KEIN
    if d.get("weitere_laufen"):
        text += "\n" + TEXT_WEITERE
    return FERTIG, text[:MAX_ZEICHEN]


def _thread_starten(ziel):
    t = threading.Thread(target=ziel, name="senf-lesen", daemon=True)
    t.start()
    return t


class Verfolgung:
    """Ein CAS-Auftrag: liest die Ablage im Hintergrund, nie blockierend. takt(jetzt) gibt zurück
    (anzeige, weiter_ms): anzeige = None (unverändert) | ("aus", "") Feld ausblenden | (zustand, text);
    weiter_ms = None → fertig, sonst nächster Takt in ms."""

    def __init__(self, auftrag_id, nr, ordner, jetzt, lese=lesen, starte=_thread_starten,
                 frist=LESE_FRIST_S, nachladen=NACHLADEN_S, max_s=NACHLADEN_MAX_S):
        self.auftrag_id, self.nr, self.ordner = auftrag_id, str(nr or ""), ordner
        self.t0, self.lese, self.starte = jetzt, lese, starte
        self.frist, self.nachladen, self.max_s = frist, nachladen, max_s
        self._lauf = None          # [start, ergebnis|None, fertig?]
        self._haengt = None        # verworfener Lese-Thread, der noch nicht zurück ist
        self.zustand = None
        self.text = ""
        self.lesungen = 0
        self.zeitueberschreitungen = 0

    def _lesen_starten(self, jetzt):
        lauf = {"start": jetzt, "ergebnis": None, "fertig": False}

        def arbeit():
            try:
                lauf["ergebnis"] = self.lese(self.ordner, self.nr)
            except Exception:
                lauf["ergebnis"] = ("aus", None)
            lauf["fertig"] = True
        self._lauf = lauf
        self.lesungen += 1
        self.starte(arbeit)

    def takt(self, jetzt):
        lauf = self._lauf
        if lauf is None:
            if self._haengt is not None and not self._haengt["fertig"]:
                return self._weiter(jetzt, ("aus", ""))     # voriger Versuch hängt noch → keinen zweiten starten
            self._haengt = None
            self._lesen_starten(jetzt)
            lauf = self._lauf
        if not lauf["fertig"]:
            if jetzt - lauf["start"] <= self.frist:
                return None, PRUEF_MS
            self.zeitueberschreitungen += 1          # Netz zäh → Feld aus, in NACHLADEN_S noch einmal (max. 10 min)
            self._haengt, self._lauf = lauf, None
            return self._weiter(jetzt, ("aus", ""))
        self._lauf = None
        art, d = lauf["ergebnis"] or ("aus", None)
        if art == "aus":
            return self._setzen(("aus", "")), None     # keine Ablage/kein Laufwerk → Feld aus, nicht weiter nachfragen
        if art == "fehlt":
            return self._weiter(jetzt, (LAEUFT, TEXT_LAEUFT))
        zustand, text = anzeige(d)
        if zustand == FERTIG and isinstance(d, dict) and d.get("weitere_laufen"):
            return self._weiter(jetzt, (zustand, text))
        if zustand == LAEUFT:
            return self._weiter(jetzt, (zustand, text))
        return self._setzen((zustand, text)), None

    def _weiter(self, jetzt, a):
        """Noch nicht endgültig: in NACHLADEN_S wieder — außer die 10 min sind um."""
        if jetzt - self.t0 + self.nachladen > self.max_s:
            if a[0] == LAEUFT:
                a = (KEIN, TEXT_KEIN)       # nach 10 min immer noch nichts → klar sagen statt ewig „läuft“
            return self._setzen(a), None
        return self._setzen(a), int(self.nachladen * 1000)

    def _setzen(self, a):
        if a == (self.zustand, self.text):
            return None
        self.zustand, self.text = a
        return a
