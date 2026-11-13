"""KaiFormat-KI: Maskierer – Patientendaten verlassen die Ordi nie (Peter 03.11.2026, Bedingung für Anthropic direkt).

Vor JEDEM KI-Aufruf wird der Befundteil deterministisch maskiert, nach der Antwort lokal zurückgesetzt:
  ⟦P1⟧ Namen (Patient, Ärzte, Zuweiser – bekannte Namen aus der CAS-Auskunft + Muster „Dr./Prim./OA/Frau/Herrn …“)
  ⟦D1⟧ Datumsangaben (12.3.26, 12.03.2026, 12.3., März 2026, 03/2026, 2026-03-12, einzelne Jahreszahlen 1930–2049)
  ⟦N1⟧ Nummern (SVNR auch mit Leerzeichen, Diktat-/RH-/Patienten-/Accession-Nummern, Telefon, jede Ziffernfolge ≥ 5)
  ⟦A1⟧ Adressen (Straße + Hausnummer, PLZ + Ort)    ⟦E1⟧ E-Mail/Web-Adressen
Gleicher Wert → gleicher Platzhalter (innerhalb eines Aufrufs, nummeriert nach erstem Auftreten) – dadurch ist die
Maskierung desselben Texts immer gleich (Vorbereitung und Strg+Alt+B treffen dieselbe Kennung).

Im Zweifel maskieren. Danach prüft restpruefung() den maskierten Text noch einmal unabhängig: bekannte Namen/Geburtsdatum
in jeder Schreibweise, Ziffernfolgen ≥ 5, Datumsmuster, „@“. Bleibt etwas übrig → MaskeUnsicher → KEIN Aufruf, der
Formatierer nimmt den Regelweg wie bisher.

Nur Python-Stdlib (läuft in der Formatierer-EXE und am Büro-PC).
"""
from __future__ import annotations

import re
import unicodedata

VERSION = "1.0.0"

KLAMMER_AUF, KLAMMER_ZU = "⟦", "⟧"          # ⟦ ⟧ – kommen in Befundtexten nie vor
_PLATZHALTER = re.compile(KLAMMER_AUF + r"([PDNAE])(\d+)" + KLAMMER_ZU)


class MaskeUnsicher(Exception):
    """Der Maskierer kann nicht sicher arbeiten (Rest gefunden, Platzhalterzeichen schon im Text …) → kein KI-Aufruf."""


def _nfc(t):
    return unicodedata.normalize("NFC", t or "")


# ───────────────────────────── Muster ─────────────────────────────
_MONATE = (r"J(?:ä|ae)nner|Januar|Feber|Februar|M(?:ä|ae)rz|April|Mai|Juni|Juli|August|September|Oktober|November|"
           r"Dezember|J(?:ä|ae)n\.|Jan\.|Feb\.|M(?:ä|ae)r\.|Apr\.|Jun\.|Jul\.|Aug\.|Sept?\.|Okt\.|Nov\.|Dez\.")
_JAHR = r"(?:19|20)\d{2}"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\b(?:https?://|www\.)\S+", re.IGNORECASE)

_DATUM = [
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),                                          # 2026-03-12
    re.compile(r"(?<![\d,.])(?:0?[1-9]|[12]\d|3[01])\s?\.\s?(?:0?[1-9]|1[0-2])\s?\.\s?(?:" + _JAHR + r"|\d{2})(?!\d|,\d)"),
    re.compile(r"(?<![\d,.])(?:0?[1-9]|[12]\d|3[01])\.(?:0?[1-9]|1[0-2])\.(?!\d|,\d)"),  # 12.3. (ohne Jahr)
    re.compile(r"(?<![\d,./])(?:0?[1-9]|[12]\d|3[01])/(?:0?[1-9]|1[0-2])/(?:" + _JAHR + r"|\d{2})(?![\d/])"),  # 12/3/26
    re.compile(r"(?<![\d,./])(?:0?[1-9]|1[0-2])\s?/\s?" + _JAHR + r"(?!\d)"),         # 03/2026
    re.compile(r"(?:(?<![\d,.])(?:0?[1-9]|[12]\d|3[01])\.?\s*)?\b(?:" + _MONATE + r")(?:(?<=\.)|\b)(?:\s*(?:" + _JAHR
               + r"|\d{2})(?!\d))?", re.IGNORECASE),                                  # 12. März 2026, März 26, im Mai
    re.compile(r"(?<![\d,.])(?:19[3-9]\d|20[0-4]\d)(?!\d|,\d)"),                      # Jahreszahl allein
]

_NUMMER = [
    # Schlüsselwort + Nummer (auch kurz: „RH 89“, „Pat.-Nr. 4711“, „Zl. 12/3“)
    re.compile(r"\b(?:SV-?Nr|SVNR|VSNR|SV-Nummer|Sozialversicherungs(?:nummer|nr)|Versicherungs(?:nummer|nr)|Vers\.-?Nr|"
               r"Pat(?:ienten)?\.?-?(?:Nr|Nummer|ID)|PID|Diktat(?:nummer|-?Nr)?|Untersuchungs(?:nummer|-?Nr)|RH|"
               r"Acc(?:ession)?(?:-?(?:Nr|No|Nummer))?|AccNo|Auftrags(?:nummer|-?Nr)|Befund(?:nummer|-?Nr)|Zl|Akt(?:enzahl)?|"
               r"Fall(?:nummer|-?Nr)|Aufnahmezahl|Nr|No)\.?\s*[:.#]?\s*(\d[\d\s/.-]{0,24}\d|\d)", re.IGNORECASE),
    # Telefon/Fax mit Schlüsselwort
    re.compile(r"\b(?:Tel(?:efon)?|Fax|Handy|Mobil|Mob|Ruf(?:nummer)?)\.?\s*[:.]?\s*(\+?[\d(][\d\s()/-]{4,}\d)",
               re.IGNORECASE),
    # SVNR 4+6 Ziffern, auch „1234 120380“ oder „1234 12 03 80“
    re.compile(r"(?<![\d,.])(\d{4}\s?\d{2}\s?\d{2}\s?\d{2})(?!\d|,\d)"),
    # Telefon ohne Schlüsselwort: +43 …, 0664 …
    re.compile(r"(\+\d{1,3}[\s/-]?(?:\(0\))?[\d\s/-]{5,}\d|\b0\d{2,4}[\s/-]\d{2,}(?:[\s/-]\d{2,})*)"),
    # jede Ziffernfolge ab 5 Ziffern (Diktat-/Patienten-/Accession-Nummern)
    re.compile(r"(?<![\d,])(\d{5,})(?!\d|,\d)"),
]

_STRASSE = (r"(?i:stra(?:ß|ss)e|str\.|gasse|g\.|weg|platz|pl\.|allee|ring|zeile|kai|l(?:ä|ae)nde|promenade|gürtel|"
            r"guertel|steig|hof|siedlung|markt|berg|feld|au)")
_ADRESSE = [
    re.compile(r"\b(?:[A-ZÄÖÜ][\w\-äöüß.]*?" + _STRASSE + r"|Gürtel|Guertel|Ring|Weg|Platz|Kai|Lände|Allee|Gasse|"
               r"Stra(?:ß|ss)e|Zeile|Promenade|Markt)\s+\d+[a-zA-Z]?(?:\s?[/-]\s?\d+[a-zA-Z]?)*"),
    re.compile(r"\b(?:A-)?[1-9]\d{3}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+(?:an|am|im|bei|ob)\s+der\s+[A-ZÄÖÜ][a-zäöüß]+)?\b"),
]

# Name nach Anrede/Titel: Titelwörter bleiben, nur der Name wird ⟦P⟧
_TITEL_WORT = (r"(?:Dr|Prim|Primar(?:ius|ia)?|OA|OÄ|OAe|Oberarzt|Oberärztin|Prof|Univ\.?-?Prof|Doz|Priv\.?-?Doz|Mag|DDr|"
               r"Dipl\.?-?Ing|FA|FÄ|Fachärztin|Facharzt|Frau|Fr|Herrn?|Hr|Kolleg(?:e|en|in)|Zuweiser(?:in)?|Hausarzt|"
               r"Hausärztin|fecit|i\.\s?V|med|univ|MSc|PhD|MBA|MAS|Med\.?-?Rat|OMR|Familie)")
_NAME_TOKEN = r"[A-ZÄÖÜ][a-zäöüßéèáàç'’]+(?:-[A-ZÄÖÜ][a-zäöüßéèáàç'’]+)?"
_NACH_TITEL = re.compile(r"\b" + _TITEL_WORT + r"\.?(?:\s+" + _TITEL_WORT + r"\.?)*\s+((?:von\s+|van\s+|de\s+)?"
                         + _NAME_TOKEN + r"(?:\s+" + _NAME_TOKEN + r"){0,2})")
# Wörter, die nach einer Anrede vorkommen, aber kein Name sind („Frau Doktor“, „Kollegen Bescheid“ …)
_KEIN_NAME = {"doktor", "kollegin", "kollege", "kollegen", "patientin", "patient", "befund", "bitte", "danke", "dank",
              "med", "univ", "prof", "dr", "zuweisung", "zuweiser", "der", "die", "das", "und", "mit", "zur", "zum",
              "im", "am", "vom", "von", "nach", "laut", "lt", "befunde", "befunder", "befunderin", "rücksprache",
              "ruecksprache", "kontrolle", "verlauf", "vorbefund", "vorbefunde", "untersuchung", "ordination", "praxis",
              "spital", "klinik", "abteilung", "station", "ambulanz", "röntgen", "roentgen", "sonographie", "mammographie"}


# ───────────────────────────── Maske ─────────────────────────────
class Maske:
    """Ein Maskier-Durchgang. maskieren() für jede Zeile, danach restpruefung(); zuruecksetzen() für Antwort-Texte."""

    def __init__(self, namen=(), geburtsdatum=None):
        self.namen = _namen_varianten(namen)
        self.geburtsdatum = geburtsdatum
        self.wert_zu = {}            # (Art, normierter Wert) → Platzhalter
        self.zu_wert = {}            # Platzhalter → Originalwert (erstes Vorkommen)
        self.zaehler = {k: 0 for k in "PDNAE"}

    # Platzhalter für einen Wert (gleicher Wert → gleicher Platzhalter)
    def _ph(self, art, wert):
        schluessel = (art, re.sub(r"\s+", " ", wert.strip()).lower())
        ph = self.wert_zu.get(schluessel)
        if ph is None:
            self.zaehler[art] += 1
            ph = f"{KLAMMER_AUF}{art}{self.zaehler[art]}{KLAMMER_ZU}"
            self.wert_zu[schluessel] = ph
            self.zu_wert[ph] = wert
        return ph

    def _ersetze(self, text, muster, art, gruppe=0):
        def f(m):
            if gruppe == 0:
                return self._ph(art, m.group(0))
            s, e = m.span(gruppe)
            if s < 0:
                return m.group(0)
            return m.group(0)[:s - m.start()] + self._ph(art, m.group(gruppe)) + m.group(0)[e - m.start():]
        return muster.sub(f, text)

    def maskieren(self, text):
        t = _nfc(text)
        if KLAMMER_AUF in t or KLAMMER_ZU in t:
            raise MaskeUnsicher("Platzhalterzeichen schon im Text")
        # 1. bekannte Namen (aus der CAS-Auskunft) – zuerst, damit Doppelnamen ganz ersetzt werden
        for v in self.namen:
            t = re.sub(r"(?<![\w" + KLAMMER_AUF + r"])" + re.escape(v) + r"(?!\w)", lambda m: self._ph("P", m.group(0)),
                       t, flags=re.IGNORECASE)
        # 2. E-Mail/Web
        t = self._ersetze(t, _EMAIL, "E")
        # 3. Nummern mit Schlüsselwort, Telefon, SVNR (vor den Datumsmustern: „1234 120380“ ist kein Datum)
        for m in _NUMMER[:4]:
            t = self._ersetze(t, m, "N", 1)
        # 4. Datumsangaben
        for m in _DATUM:
            t = self._ersetze(t, m, "D")
        # 5. Adressen
        for m in _ADRESSE:
            t = self._ersetze(t, m, "A")
        # 6. übrige lange Ziffernfolgen
        t = self._ersetze(t, _NUMMER[4], "N", 1)
        # 7. Namen nach Anrede/Titel
        t = _NACH_TITEL.sub(self._name_nach_titel, t)
        return t

    def _name_nach_titel(self, m):
        name = m.group(1)
        woerter = name.split()
        # Name endet vor dem ersten Wort, das sicher kein Name ist
        keep = []
        for w in woerter:
            if w in ("von", "van", "de", "zu"):          # Namenszusatz gehört zum Namen
                keep.append(w)
                continue
            if w.lower().strip(".") in _KEIN_NAME:
                break
            keep.append(w)
        while keep and keep[-1] in ("von", "van", "de", "zu"):
            keep.pop()
        if not keep:
            return m.group(0)
        n = " ".join(keep)
        s = m.start(1) - m.start()
        return m.group(0)[:s] + self._ph("P", n) + m.group(0)[s + len(n):]

    def restpruefung(self, texte):
        """Unabhängige Nachprüfung des maskierten Texts. Wirft MaskeUnsicher mit einer Grund-Kategorie (ohne Wert)."""
        alles = "\n".join(_PLATZHALTER.sub(" ", _nfc(t)) for t in texte)
        for v in self.namen:
            if re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", alles, flags=re.IGNORECASE):
                raise MaskeUnsicher("bekannter Name im Text")
        for v in _datum_varianten(self.geburtsdatum):
            if v in alles:
                raise MaskeUnsicher("Geburtsdatum im Text")
        if re.search(r"\d{5,}", alles):
            raise MaskeUnsicher("lange Ziffernfolge")
        if re.search(r"(?<![\d,])\d{1,2}\.\d{1,2}\.(?:\d{2,4})?(?!\d|,\d)", alles):
            raise MaskeUnsicher("Datumsmuster")
        if re.search(r"(?<![\d,])(?:19[3-9]\d|20[0-4]\d)(?!\d|,\d)", alles):
            raise MaskeUnsicher("Jahreszahl")
        if "@" in alles:
            raise MaskeUnsicher("E-Mail")
        if re.search(r"\d{3,}\s\d{3,}", alles):
            raise MaskeUnsicher("Ziffernblock")
        return True

    def zuruecksetzen(self, text):
        """Platzhalter in einem Antwort-Text (Hinweis) wieder durch die Originalwerte ersetzen – nur lokal."""
        return _PLATZHALTER.sub(lambda m: self.zu_wert.get(m.group(0), m.group(0)), text or "")

    def zaehlung(self):
        """Nur Zahlen (für format.log/Bericht): wie viele Platzhalter je Art."""
        return dict(self.zaehler)


def _namen_varianten(namen):
    """Bekannte Namen → Suchwörter: ganzer Name, Teile (ab 3 Buchstaben), Doppelnamen ganz und einzeln, ä/ae-Formen.
    Längste zuerst (Doppelname vor Teil)."""
    out = set()
    for n in namen or ():
        n = _nfc(str(n or "")).strip()
        if not n:
            continue
        teile = [n] + re.split(r"[\s,;/]+", n)
        for t in list(teile):
            if "-" in t:
                teile += t.split("-")
        for t in teile:
            t = t.strip(" .,'\"")
            if len(t) < 3 or t.lower() in _KEIN_NAME or t.lower() in ("dr", "med", "univ", "prof", "mag", "frau", "herr"):
                continue
            out.add(t)
            out.add(t.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
                     .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue"))
    return sorted(out, key=len, reverse=True)


def _datum_varianten(gd):
    """Geburtsdatum (TT.MM.JJJJ, JJJJ-MM-TT, JJJJMMTT) → alle üblichen Schreibweisen."""
    if not gd:
        return []
    s = str(gd).strip()
    m = (re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s) or None)
    if m:
        t, mo, j = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.fullmatch(r"(\d{4})-?(\d{2})-?(\d{2})", s)
        if not m:
            return []
        j, mo, t = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return sorted({f"{t}.{mo}.{j}", f"{t:02d}.{mo:02d}.{j}", f"{t}.{mo}.{j % 100:02d}", f"{t:02d}.{mo:02d}.{j % 100:02d}",
                   f"{j}-{mo:02d}-{t:02d}", f"{j}{mo:02d}{t:02d}", f"{t:02d}{mo:02d}{j % 100:02d}"})


_KOPF_NAME = re.compile(r"^\s*(?:Name|Patient(?:in)?|Pat\.)\s*:\s*(.*?)(?:,?\s*geb(?:oren|\.)?\s*(?:am)?\s*:?\s*"
                        r"(\d{1,2}\.\d{1,2}\.\d{4}))?(?:\t|\s{2,}|$)", re.IGNORECASE)
_KOPF_GEB = re.compile(r"geb(?:oren|\.)?\s*(?:am)?\s*:?\s*(\d{1,2}\.\d{1,2}\.\d{4})", re.IGNORECASE)
_KOPF_ZW = re.compile(r"^\s*(?:ZW|Zuweiser(?:in)?|Zuweisung|An|Kopie an|cc)\s*:\s*(.*)$", re.IGNORECASE)
_NAMENSWORT = re.compile(r"[A-ZÄÖÜ][a-zäöüßéèáàç'\u2019]+(?:-[A-ZÄÖÜ][a-zäöüßéèáàç'\u2019]+)*")


def kontext_aus_kopf(zeilen, zuweiser=None):
    """CAS-Briefkopf (Absätze VOR dem Befundteil – sie selbst gehen nie hinaus) → bekannte Namen + Geburtsdatum für die
    Maske. „Name: Nachname Vorname geb.: TT.MM.JJJJ“, „ZW: Dr. …“ und der Zuweiser aus der CAS-Auskunft.
    → {"namen": [...], "geburtsdatum": "TT.MM.JJJJ"|None} (bleibt lokal)."""
    namen, gd = [], None
    for z in zeilen or ():
        z = _nfc(z).replace("\x0b", "\n")
        for teil in z.split("\n"):
            m = _KOPF_NAME.match(teil)
            if m:
                namen += _NAMENSWORT.findall(m.group(1) or "")
                gd = gd or m.group(2)
            g = _KOPF_GEB.search(teil)
            if g:
                gd = gd or g.group(1)
                if not m:
                    namen += _NAMENSWORT.findall(teil[:g.start()])
            w = _KOPF_ZW.match(teil)
            if w:
                namen += _NAMENSWORT.findall(w.group(1))
    if zuweiser:
        namen += _NAMENSWORT.findall(_nfc(str(zuweiser)))
    namen = [n for n in namen if n.lower() not in _KEIN_NAME and n.lower() not in _KOPF_WORT]
    return {"namen": sorted(set(namen)), "geburtsdatum": gd}


_KOPF_WORT = {"name", "geb", "befund", "graz", "wien", "am", "dr", "med", "univ", "prof", "mag", "prim", "frau", "herr",
              "herrn", "zw", "dres", "ordination", "praxis", "gemeinschaftspraxis", "facharzt", "fachärztin", "fachaerztin",
              "allgemeinmedizin", "innere", "medizin", "orthopädie", "orthopaedie", "chirurgie", "unfallchirurgie",
              "gynäkologie", "gynaekologie", "urologie", "neurologie", "kinderheilkunde", "radiologie", "dermatologie",
              "lkh", "ukh", "spital", "klinikum", "krankenhaus", "ambulanz", "abteilung", "station", "ambulatorium",
              "gruppenpraxis", "primärversorgung", "primaerversorgung", "zentrum", "institut", "kopie", "an", "cc",
              "zuweiser", "zuweiserin", "zuweisung", "patient", "patientin", "info"}


def platzhalter_in(text):
    return _PLATZHALTER.findall(text or "")


def maskiere_zeilen(zeilen, namen=(), geburtsdatum=None):
    """Bequem: Zeilen maskieren + Restprüfung. → (maskierte Zeilen, Maske). Wirft MaskeUnsicher."""
    m = Maske(namen, geburtsdatum)
    aus = [m.maskieren(z) for z in zeilen]
    m.restpruefung(aus)
    return aus, m
