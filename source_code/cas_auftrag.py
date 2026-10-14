"""CAS-Auftrag von der RaKScribe-Brücke (ris-mods/bruecke, Protokoll 1) — Gegenstelle der EXE, ohne Windows testbar.

Peter 12.10.2026: RaKScribe soll im CAS ohne SpeechMagic laufen. CAS startet über das Dropdown („Digitales Diktat“)
die Brücke; sie legt %LOCALAPPDATA%\\RaKScribe\\cas_auftrag.json ab. RaKScribe holt ihn ab, zeigt oben ein Band
„CAS-Diktat <Nr> (<Benutzer>)“, und EOL schickt den sichtbaren Befund NICHT per Strg+V ins Vordergrundfenster, sondern
als Datei an die Brücke. Ohne Auftrag arbeitet RaKScribe exakt wie bisher.

Dateien (gleiche Namen/Felder wie ris-mods bruecke/auftrag.py — Änderungen immer in BEIDEN Repos):
  cas_auftrag.json            Brücke → RaKScribe {protokoll, auftrag_id, nr, benutzer, bruecke_pid, zeit, testbefund}
  cas_antwort_<id>.json       RaKScribe → Brücke {status: angenommen|fertig|abgebrochen|abgelehnt|ersetzt, …}
  cas_ergebnis_<nr>.txt/.wav  Befund-Markdown (UTF-8) und Aufnahme (PCM 16 bit mono), vor „fertig“ geschrieben
  cas_widerruf_<id>.json      Brücke → RaKScribe: Auftrag zurückgezogen (Zeitgrenze) → Band weg
  cas_leistungen_<id>.json    v3.12.0 (Brücke 1.1.0): CAS-Leistungen des Eintrags, Sekunden NACH dem Auftrag
                              {protokoll, auftrag_id, nr, roh, leistungen:[{kurz, text, appc, modalitaet, seite,
                              vorlage|null, ohne_vorlage, bekannt}], quelle, katalog, ms, zeit} — optional: ohne Datei
                              (ältere Brücke, Abfrage gescheitert) arbeitet RaKScribe wie bisher. Vorrang-Hinweis für die
                              Vorlagenwahl: cas_vorlagen.py.
  cas_ibl_<id>.json           v3.13.0 (Brücke 1.2.0): IB-Lab-Vorbefund-Bausteine des Eintrags, beim Start oder später,
                              bei jeder neuen/aktualisierten Fassung neu geschrieben {protokoll, auftrag_id, nr, quelle,
                              bausteine:[{accno, ziffer, modul, name, modul_name, version, aktualisiert, seiten,
                              befundteil, ergebnis, hinweise, nicht_zugeordnet}], zeit} — optional; Einsetzen nach der KI:
                              ibl_bausteine.py.
  cas_kontext_<id>.json       v3.14.0 (Brücke 2.0.0, RaK-Befund, aus der Datenbank des RIS): {protokoll, auftrag_id, nr,
                              quelle, zuweiser, info, befunder, vorbefund: {nr, datum, untersuchung, text, zeichen, gekuerzt}
                              | null, zeit} — optional. NUR Anzeige: Kopfzeile im Band (Zuweiser, Info) und Fenster
                              „Vorbefund“. Geht nie an die KI und nie ins Protokoll (dort nur Längen).
                              cas_leistungen kann dann je Leistung „ziffer“ (Accession = Diktatnummer + Ziffer) und
                              „accession“ tragen → exakte Zuordnung der IB-Lab-Bausteine.
Durch die Dateien wandern nur Diktatnummer und Benutzerkürzel, Leistungskürzel, KI-Messwerte der Untersuchung, ab v3.14.0
Zuweiser/Info/Vorbefund zur Anzeige (und am Ende der Befund selbst) — alles nur lokal.
"""
import io
import json
import os
import time
import wave

PROTOKOLL = 1
AUFTRAG = "cas_auftrag.json"
MAX_ALTER_S = 10 * 60   # älterer, nie abgeholter Auftrag (Brücke abgestürzt) wird ignoriert
# Gleicher Text wie ris-mods bruecke/bruecke.py TESTBEFUND — sichtbar als TEST markiert (Fern-Test ohne Mikrofon).
TESTBEFUND = ("## TEST RaKScribe-Brücke – bitte nicht vidieren\n\n"
              "## Befund\n"
              "TESTBEFUND ohne Diktat und ohne Patientenbezug. Dieser Text prüft nur die Übergabe von RaKScribe an CAS.\n\n"
              "## Ergebnis\n"
              "TEST – bitte nicht vidieren.")


def ordner_standard(umgebung=None):
    umgebung = os.environ if umgebung is None else umgebung
    basis = umgebung.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(basis, "RaKScribe")


def _json_schreiben(pfad, daten):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    tmp = f"{pfad}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False)
    for i in range(20):
        try:
            os.replace(tmp, pfad)
            return
        except PermissionError:   # Brücke/Virenschutz liest gerade
            if i == 19:
                raise
            time.sleep(0.05)


def _json_lesen(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def wav_aus_pcm(pcm_bytes, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm_bytes)
    return buf.getvalue()


def prozess_lebt(pid):
    """Windows: läuft die Brücke noch? Außerhalb von Windows (Mac-Tests) nicht prüfbar → True."""
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except (ImportError, AttributeError, OSError):
        return True
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k32.OpenProcess(0x1000, False, int(pid))   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        code = wintypes.DWORD(0)
        return bool(k32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


class Auftrag:
    def __init__(self, d):
        self.auftrag_id = str(d.get("auftrag_id") or "")
        self.nr = str(d.get("nr") or "")
        self.benutzer = str(d.get("benutzer") or "")
        self.bruecke_pid = d.get("bruecke_pid")
        self.zeit = d.get("zeit") or 0
        self.testbefund = bool(d.get("testbefund"))
        self.leistungen = None   # v3.12.0: Liste aus cas_leistungen_<id>.json; None = (noch) keine Datei
        self.ibl = None          # v3.13.0: Bausteine aus cas_ibl_<id>.json (Liste von dicts); None = (noch) keine Datei
        self.ibl_signatur = None  # Größe + Änderungszeit der zuletzt gelesenen Datei (nur bei Änderung neu lesen)
        self.kontext = None      # v3.14.0: dict aus cas_kontext_<id>.json; None = (noch) keine Datei

    def labels(self):
        """Kurznamen der Leistungen fürs Band (ohne Abrechnungsposten), z. B. ['HWS', 'Schulter re. (Sono)']."""
        import cas_vorlagen as cv
        return [cv.label(l.get("text"), l.get("kurz"), l.get("modalitaet")) for l in (self.leistungen or [])
                if not l.get("ohne_vorlage")]

    def kopfzeile(self, max_info=90):
        """v3.14.0: „Zuweiser: Dr. X · Info: …“ für das Band (nur Anzeige) — leer ohne Kontext."""
        k = self.kontext or {}
        teile = []
        if str(k.get("zuweiser") or "").strip():
            teile.append("Zuweiser: " + " ".join(str(k["zuweiser"]).split()))
        info = " ".join(str(k.get("info") or "").split())
        if info:
            teile.append("Info: " + (info if len(info) <= max_info else info[:max_info - 1].rstrip() + "…"))
        return "  ·  ".join(teile)

    def vorbefund(self):
        """v3.14.0: {nr, datum, untersuchung, text, …} oder None."""
        vb = (self.kontext or {}).get("vorbefund")
        return vb if isinstance(vb, dict) and str(vb.get("text") or "").strip() else None

    def band_text(self):
        t = f"CAS-Diktat {self.nr}" + (f" ({self.benutzer})" if self.benutzer else "")
        labels = self.labels()
        if labels:   # v3.12.0: „CAS-Diktat <Nr> (<Benutzer>) · HWS · Schulter re. (Sono)“
            t += " · " + " · ".join(labels[:4]) + (" · …" if len(labels) > 4 else "")
        return t


def entscheidung(aktiv, hat_inhalt):
    """Was mit einem neuen Auftrag passiert, wenn schon einer offen ist (Patientensicherheit: ein Diktat für Patient A
    darf nie still bei Patient B landen). annehmen | ersetzen (alter Auftrag ohne Inhalt) | ablehnen."""
    if aktiv is None:
        return "annehmen"
    return "ablehnen" if hat_inhalt else "ersetzen"


class Kanal:
    def __init__(self, ordner=None, pid=None, version="?", log=None, prozess_lebt=None, jetzt=time.time):
        self.ordner = ordner or ordner_standard()
        self.pid = os.getpid() if pid is None else pid
        self.version = version
        self.log = log or (lambda *a: None)
        self.prozess_lebt = prozess_lebt
        self.jetzt = jetzt

    def abholen(self):
        """Neuen Auftrag aus dem Eingang holen (Datei wird gelöscht). None, wenn keiner da/ungültig/veraltet."""
        pfad = os.path.join(self.ordner, AUFTRAG)
        if not os.path.exists(pfad):
            return None
        d = _json_lesen(pfad)
        if d is None:
            return None                       # halb geschrieben → nächster Takt
        try:
            os.remove(pfad)
        except OSError:
            return None
        a = Auftrag(d)
        if d.get("protokoll") != PROTOKOLL or not a.auftrag_id or not a.nr:
            self.log(f"[CAS] Auftrag verworfen (Protokoll {d.get('protokoll')}, unvollständig)")
            return None
        if self.jetzt() - float(a.zeit or 0) > MAX_ALTER_S:
            self.log(f"[CAS] Auftrag {a.nr} verworfen (älter als {MAX_ALTER_S // 60} min)")
            return None
        if self.prozess_lebt is not None and a.bruecke_pid and not self.prozess_lebt(a.bruecke_pid):
            self.log(f"[CAS] Auftrag {a.nr} verworfen (Brücke läuft nicht mehr)")
            return None
        return a

    def antworten(self, a, status, **mehr):
        d = {"protokoll": PROTOKOLL, "auftrag_id": a.auftrag_id, "nr": a.nr, "status": status,
             "rakscribe_pid": self.pid, "version": self.version, "zeit": self.jetzt()}
        d.update({k: v for k, v in mehr.items() if v is not None})
        _json_schreiben(os.path.join(self.ordner, f"cas_antwort_{a.auftrag_id}.json"), d)
        self.log(f"[CAS] {a.nr}: {status}" + (f" ({mehr.get('grund')})" if mehr.get("grund") else ""))

    def zurueckgezogen(self, a):
        """Grund, wenn die Brücke den Auftrag aufgegeben hat (Widerruf-Datei oder Brücke beendet), sonst None."""
        w = _json_lesen(os.path.join(self.ordner, f"cas_widerruf_{a.auftrag_id}.json"))
        if w is not None:
            return w.get("grund") or "widerrufen"
        if self.prozess_lebt is not None and a.bruecke_pid and not self.prozess_lebt(a.bruecke_pid):
            return "bruecke_beendet"
        return None

    def leistungen_lesen(self, a):
        """v3.12.0: CAS-Leistungen zum Auftrag a (Datei der Brücke). None = (noch) nicht da, halb geschrieben oder
        nicht zu diesem Auftrag; sonst die Liste (darf leer sein). Die Brücke räumt die Datei selbst auf."""
        d = _json_lesen(os.path.join(self.ordner, f"cas_leistungen_{a.auftrag_id}.json"))
        if d is None:
            return None
        if str(d.get("auftrag_id") or "") != a.auftrag_id or str(d.get("nr") or "") != a.nr:
            self.log(f"[CAS] Leistungen verworfen (gehören nicht zu Auftrag {a.nr})")
            return []
        liste = d.get("leistungen")
        if not isinstance(liste, list):
            return []
        return [l for l in liste if isinstance(l, dict) and (l.get("kurz") or l.get("text"))]

    def kontext_lesen(self, a):
        """v3.14.0: Kontext (Zuweiser, Info, Vorbefund) zum Auftrag a. None = (noch) nicht da, halb geschrieben oder nicht
        zu diesem Auftrag; sonst dict mit den bekannten Feldern. Die Brücke räumt die Datei selbst auf."""
        d = _json_lesen(os.path.join(self.ordner, f"cas_kontext_{a.auftrag_id}.json"))
        if d is None:
            return None
        if str(d.get("auftrag_id") or "") != a.auftrag_id or str(d.get("nr") or "") != a.nr:
            self.log(f"[CAS] Kontext verworfen (gehört nicht zu Auftrag {a.nr})")
            return {}
        vb = d.get("vorbefund")
        if isinstance(vb, dict):
            vb = {k: vb.get(k) for k in ("nr", "datum", "untersuchung", "text", "zeichen", "gekuerzt")}
            vb["text"] = str(vb.get("text") or "")
        else:
            vb = None
        return {"zuweiser": str(d.get("zuweiser") or ""), "info": str(d.get("info") or ""),
                "befunder": str(d.get("befunder") or ""), "vorbefund": vb, "quelle": str(d.get("quelle") or "")}

    def ibl_lesen(self, a):
        """v3.13.0: IB-Lab-Bausteine zum Auftrag a, nur wenn sich die Datei der Brücke seit dem letzten Lesen geändert hat.
        → Liste (darf leer sein) oder None (keine Datei, unverändert, halb geschrieben, gehört nicht zu diesem Auftrag).
        Die Brücke schreibt die Datei bei jeder neuen Fassung neu und räumt sie selbst auf."""
        pfad = os.path.join(self.ordner, f"cas_ibl_{a.auftrag_id}.json")
        try:
            st = os.stat(pfad)
        except OSError:
            return None
        signatur = (st.st_size, st.st_mtime_ns)
        if signatur == a.ibl_signatur:
            return None
        d = _json_lesen(pfad)
        if d is None:
            return None                       # halb geschrieben → nächster Takt (Signatur bleibt alt)
        a.ibl_signatur = signatur
        if str(d.get("auftrag_id") or "") != a.auftrag_id or str(d.get("nr") or "") != a.nr:
            self.log(f"[CAS] IB-Lab-Bausteine verworfen (gehören nicht zu Auftrag {a.nr})")
            return None
        liste = d.get("bausteine")
        return [b for b in liste if isinstance(b, dict)] if isinstance(liste, list) else []

    def ergebnis_schreiben(self, a, text, pcm_bytes=None, rate=16000, test=False):
        """EOL: Befund (+ Aufnahme) ablegen, DANACH „fertig“ melden — die Brücke liest nie eine halbe Datei."""
        os.makedirs(self.ordner, exist_ok=True)
        txt = os.path.join(self.ordner, f"cas_ergebnis_{a.nr}.txt")
        with open(txt, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        wav = None
        if pcm_bytes:
            wav = os.path.join(self.ordner, f"cas_ergebnis_{a.nr}.wav")
            with open(wav, "wb") as f:
                f.write(wav_aus_pcm(pcm_bytes, rate))
        self.antworten(a, "fertig", text_datei=txt, wav_datei=wav, zeichen=len(text), test=bool(test))
        return txt, wav
