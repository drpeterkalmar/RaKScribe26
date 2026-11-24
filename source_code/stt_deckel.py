"""Harter Tagesdeckel für die Google-Spracherkennung (kaiscribe-stt-tagesdeckel-n1, Peter 24.11.2026).

Warum: Für Speech/Chirp gibt es bei Google keine Euro-Ausgabenobergrenze. Seit 24.11. hat v1 (Live-Anzeige) eine harte
Tagesquota (240 min), chirp_3 (v2 Recognize) aber nur 56 Anfragen/min — in einer Fehlerschleife wären ~1.300 $/Tag
möglich. Der echte Tagesdeckel sitzt deshalb hier in KaiScribe. Reine Schutzgrenze: normal sind 15–30 min/Tag.

- Zähler je Installation: Datei <ordner>/stt_tagesdeckel_<PC>.json (Standard %APPDATA%\\KaiScribe, lokal – nicht X:,
  damit der Deckel auch ohne Netzlaufwerk zählt), atomar geschrieben (tmp + os.replace). Inhalt nur Zahlen:
  {"pc", "tag", "s" (alle Google-STT-Audiosekunden heute), "art": {"chirp", "streaming"}, "kuerzel": {"kp": s, …},
   "warn80", "grenze", "schleife"}. Zusätzlich im Speicher (Datei kaputt/gesperrt → der Speicherstand zählt weiter).
- Tageswechsel 00:00 Europe/Vienna (ohne tzdata auf Windows: Ortszeit des PCs – die steht in Wien).
- Grenze: config.ini STT_TAGESDECKEL_MIN (Standard 240 min Audio/Tag/PC). Erreicht → kein weiterer Google-Aufruf an
  diesem Tag (chirp_3 je 50-s-Stück vorher geprüft, Live-Anzeige je Sitzung/Paket). Die EXE behält das Audio als WAV
  und zeigt GRENZE_TEXT rot.
- Schleifenbremse: dieselbe Aufnahme (SHA-1 der Audio-Samples) höchstens SCHLEIFE_MAX× in SCHLEIFE_FENSTER_S an Google;
  danach für diese Aufnahme nie mehr (bis KaiScribe neu startet) → SCHLEIFE_TEXT rot.
- Ab 80 %: einmal je Tag eine Log-Zeile „[STT-DECKEL] WARNUNG …“ und melden("warn80", …) → die EXE schreibt das in den
  Nutzungszähler (X:\\KaiScribe\\Daten\\nutzung) → Tagesbericht-Zeile „STT-DECKEL …“ → tools/mac/kaiscribe_chirp_warnung.py
  legt eine Karte für Hermes an (nicht für Peter).
Ohne Tk/Windows/Google importierbar; Fehler beim Lesen/Schreiben sind nie fatal (Deckel zählt dann im Speicher).
"""
import datetime
import hashlib
import json
import os
import re
import threading
import time

DECKEL_STANDARD_MIN = 240
WARN_ANTEIL = 0.8
SCHLEIFE_MAX = 3
SCHLEIFE_FENSTER_S = 600
GRENZE_TEXT = "Tagesgrenze Spracherkennung erreicht – Aufnahme gesichert, bitte Hermes melden"
SCHLEIFE_TEXT = "Diese Aufnahme ging schon 3× an die Spracherkennung – gestoppt, Aufnahme gesichert, bitte Hermes melden"

try:
    from zoneinfo import ZoneInfo
    _WIEN = ZoneInfo("Europe/Vienna")
except Exception:          # Windows-EXE ohne tzdata → Ortszeit (Ordi-PCs stehen in Wien)
    _WIEN = None


def wien_jetzt():
    return datetime.datetime.now(_WIEN) if _WIEN is not None else datetime.datetime.now()


def _pc_name():
    roh = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "pc"
    return re.sub(r"[^A-Za-z0-9_-]", "_", roh)[:40] or "pc"


def aufnahme_hash(pcm):
    """SHA-1 der Samples (numpy-Array, bytes oder Liste) – nur zum Wiedererkennen, nie gespeichert."""
    try:
        roh = pcm.tobytes() if hasattr(pcm, "tobytes") else bytes(pcm)
    except Exception:
        roh = repr(pcm).encode()
    return hashlib.sha1(roh).hexdigest()


class Deckel:
    def __init__(self, ordner, pc=None, limit_min=DECKEL_STANDARD_MIN, jetzt=None, uhr=None, log=None, melden=None):
        """ordner: Pfad oder Funktion; jetzt: () → datetime (Wien), uhr: () → Sekunden (Schleifenbremse);
        melden(art, info): art = warn80 | grenze | schleife (EXE → Nutzungszähler, ohne Patientendaten)."""
        self._ordner, self.pc = ordner, pc or _pc_name()
        self.limit_min = limit_min if (isinstance(limit_min, (int, float)) and limit_min > 0) else DECKEL_STANDARD_MIN
        self.jetzt = jetzt or wien_jetzt
        self.uhr = uhr or time.time
        self.log = log or (lambda *a: None)
        self.melden = melden
        self.kuerzel = ""            # Befunder des laufenden Diktats (EXE setzt es aus dem CAS-Auftrag)
        self._sperre = threading.RLock()
        self._mem = None             # letzter Stand (auch wenn die Datei nicht geht)
        self._aufrufe = {}           # hash → [Zeitpunkte]
        self._gesperrt = set()       # hashes der Schleifenbremse

    # ── Datei ──────────────────────────────────────────────────────────────────────────────────────────────
    @property
    def ordner(self):
        try:
            return self._ordner() if callable(self._ordner) else self._ordner
        except Exception:
            return None

    def pfad(self):
        o = self.ordner
        return os.path.join(o, f"stt_tagesdeckel_{self.pc}.json") if o else None

    def _tag(self):
        return self.jetzt().strftime("%Y-%m-%d")

    def _leer(self, tag):
        return {"pc": self.pc, "tag": tag, "s": 0.0, "art": {}, "kuerzel": {}}

    def _stand(self):
        """Stand von heute: Speicher; beim Start bzw. Tageswechsel aus der Datei (KaiScribe läuft je PC einmal –
        Einzelinstanz). Datei weg/kaputt → Speicher bzw. 0."""
        tag = self._tag()
        if self._mem and self._mem.get("tag") == tag:
            return json.loads(json.dumps(self._mem))
        d = None
        p = self.pfad()
        if p:
            try:
                with open(p, encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                d = None
        if not isinstance(d, dict) or d.get("tag") != tag:
            d = self._leer(tag)
        try:
            d["s"] = float(d.get("s", 0) or 0)
        except (TypeError, ValueError):
            d["s"] = 0.0
        for k in ("art", "kuerzel"):
            if not isinstance(d.get(k), dict):
                d[k] = {}
        self._mem = json.loads(json.dumps(d))
        return d

    def _schreiben(self, d):
        self._mem = json.loads(json.dumps(d))
        p = self.pfad()
        if not p:
            return
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
            os.replace(tmp, p)
        except Exception:
            pass

    # ── Abfragen ───────────────────────────────────────────────────────────────────────────────────────────
    def limit_s(self):
        return float(self.limit_min) * 60.0

    def verbraucht_s(self):
        with self._sperre:
            return float(self._stand().get("s", 0) or 0)

    def erreicht(self):
        return self.verbraucht_s() >= self.limit_s()

    def _melden(self, art, info):
        if self.melden is not None:
            try:
                self.melden(art, info)
            except Exception:
                pass

    def vorher(self, pcm=None):
        """Vor einem Google-Aufruf: None = erlaubt, sonst „grenze“ | „schleife“. Mit pcm zählt der Aufruf für die
        Schleifenbremse (je Aufnahme EINMAL pro chirp3_worker-Aufruf, Wiederholungen eingeschlossen)."""
        with self._sperre:
            if self.erreicht():
                d = self._stand()
                if not d.get("grenze"):
                    d["grenze"] = 1
                    self._schreiben(d)
                    self.log(f"[STT-DECKEL] Tagesgrenze erreicht: {d.get('s', 0) / 60:.1f} von {self.limit_min:g} min "
                             f"Audio heute ({self.pc}) – keine Google-Spracherkennung mehr bis Mitternacht")
                    self._melden("grenze", {"min": round(d.get("s", 0) / 60, 1), "limit_min": self.limit_min})
                return "grenze"
            if pcm is None:
                return None
            h = aufnahme_hash(pcm)
            if h in self._gesperrt:
                return "schleife"
            t = self.uhr()
            liste = [x for x in self._aufrufe.get(h, []) if t - x < SCHLEIFE_FENSTER_S]
            if len(liste) >= SCHLEIFE_MAX:
                self._gesperrt.add(h)
                self._aufrufe[h] = liste
                d = self._stand()
                d["schleife"] = int(d.get("schleife", 0) or 0) + 1
                self._schreiben(d)
                self.log(f"[STT-DECKEL] Schleifenbremse: dieselbe Aufnahme schon {len(liste)}× in "
                         f"{SCHLEIFE_FENSTER_S // 60} min an Google – keine weiteren Aufrufe dafür")
                self._melden("schleife", {"n": len(liste)})
                return "schleife"
            liste.append(t)
            self._aufrufe[h] = liste
            if len(self._aufrufe) > 200:      # nur die jüngsten Aufnahmen merken
                for k in sorted(self._aufrufe, key=lambda k: max(self._aufrufe[k]))[:100]:
                    self._aufrufe.pop(k, None)
            return None

    def gesperrt_aufnahme(self, pcm):
        return aufnahme_hash(pcm) in self._gesperrt

    # ── Buchen ─────────────────────────────────────────────────────────────────────────────────────────────
    def buchen(self, sekunden, art="chirp"):
        """An Google geschickte Audiosekunden (auch leere/fehlgeschlagene Antworten)."""
        try:
            sekunden = float(sekunden or 0)
        except (TypeError, ValueError):
            return
        if sekunden <= 0:
            return
        with self._sperre:
            d = self._stand()
            vorher = float(d.get("s", 0) or 0)
            d["s"] = round(vorher + sekunden, 1)
            a = d.setdefault("art", {})
            a[art] = round(float(a.get(art, 0) or 0) + sekunden, 1)
            k = re.sub(r"[^a-z0-9]", "", str(self.kuerzel or "").lower())[:8] or "?"
            ku = d.setdefault("kuerzel", {})
            ku[k] = round(float(ku.get(k, 0) or 0) + sekunden, 1)
            warn = not d.get("warn80") and d["s"] >= WARN_ANTEIL * self.limit_s()
            if warn:
                d["warn80"] = 1
            self._schreiben(d)
        if warn:
            self.log(f"[STT-DECKEL] WARNUNG: {d['s'] / 60:.1f} von {self.limit_min:g} min Google-Spracherkennung heute "
                     f"({int(WARN_ANTEIL * 100)} %, {self.pc}) – bitte Hermes prüfen")
            self._melden("warn80", {"min": round(d["s"] / 60, 1), "limit_min": self.limit_min})
