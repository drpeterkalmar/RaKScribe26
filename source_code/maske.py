"""Masken (v3.15.0, Peter 14.10.2026): „… eine Mammographie diktiere und gleich eine Maske aufgeht, wo ich mit einem Knopf
am SpeechMike durchspringen kann von Punkt zu Punkt, und die Voruntersuchungsergebnisse … schon drinnen stehen!“

Reine Logik ohne Tk/Windows (tests/offline/test_maske.py); die Oberfläche steht in RaKScribe.py (Abschnitt „v3.15.0
Mammo-Maske“). Die Definition (Felder, Labels, Vorbefund-Zerlegung, „unverändert“, Werte, Ausgabe, Tasten) steht in
masken.json (gebündelt). Generisch: keine RIS-Tabellen, keine Patientendaten. Den Vorbefund (Text, Datum, ACR/BI-RADS)
liefert die Brücke im Kontext — er wird nur angezeigt und deterministisch eingesetzt, geht NIE an die KI (die Korrektur
bekommt nur Peters Diktat eines Felds) und nie ins Protokoll (dort nur Zustände/Zählungen).

Feld-Zustände (quelle): leer · vorbefund (Vorschlag aus dem Vorbefund, grau) · vorlage (Vorschlag Normalbaustein, grau) ·
uebernommen (Vorschlag bewusst übernommen: Taste/Klick) · diktat (heute diktiert: ersetzt den Vorschlag) · getippt.
Ein Vorschlag wird nie still zum heutigen Befund: INS warnt bei offenen Vorschlägen (zweites INS = ohne diese Felder).
"""
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

LEER, VORBEFUND, VORLAGE, UEBERNOMMEN, DIKTAT, GETIPPT = "leer", "vorbefund", "vorlage", "uebernommen", "diktat", "getippt"
VORSCHLAG = (VORBEFUND, VORLAGE)
AKTIONEN = ("naechstes_feld", "voriges_feld", "uebernehmen", "maske_umschalten")
# eingeübte Tasten (SpeechMike-Bericht 3.8.0) — die Maske deutet sie nie um
FESTE_TASTEN = ("RECORD", "INS", "EOL", "F1", "F2", "STOP")


def _datei(name):
    for d in (getattr(sys, "_MEIPASS", None), os.path.dirname(os.path.abspath(__file__)),
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")):
        if d and os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    return None


def laden(pfad=None):
    """masken.json → dict (leer, wenn die Datei fehlt — dann gibt es keine Maske, RaKScribe arbeitet wie bisher)."""
    pfad = pfad or _datei("masken.json")
    if not pfad:
        return {}
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


# ───────────────────────────── Tasten ─────────────────────────────
def tasten_belegung(definition, ueberschreiben=None, log=None):
    """{Taste: Aktion} aus masken.json „tasten“ ({Aktion: Taste}), optional überschrieben (config.ini [MASKE]).
    Eine eingeübte Taste (Record, INS, EOL, F1, F2, Stop) oder eine unbekannte Aktion wird nie übernommen."""
    log = log or (lambda *a: None)
    soll = dict((definition or {}).get("tasten") or {})
    for aktion, taste in (ueberschreiben or {}).items():
        aktion = str(aktion).strip().lower()
        if aktion not in AKTIONEN:
            log(f"[MASKE] Tastenbelegung: unbekannte Aktion {aktion!r} ignoriert")
            continue
        soll[aktion] = str(taste or "").strip().upper()
    out = {}
    for aktion, taste in soll.items():
        if aktion not in AKTIONEN or not taste:
            continue
        for t in str(taste).replace(",", " ").split():
            t = t.strip().upper()
            if t in FESTE_TASTEN:
                log(f"[MASKE] Tastenbelegung: {t} ist eingeübt (bleibt wie sie ist) — nicht für {aktion}")
                continue
            out[t] = aktion
    return out


def tasten_text(belegung):
    """Kurztext für Protokoll und Hilfezeile, z. B. „FF = nächstes Feld · REW = voriges Feld · …“."""
    namen = {"naechstes_feld": "nächstes Feld", "voriges_feld": "voriges Feld", "uebernehmen": "Vorbefund übernehmen",
             "maske_umschalten": "Maske aus/an"}
    reihe = sorted(belegung.items(), key=lambda kv: (AKTIONEN.index(kv[1]), kv[0]))
    return " · ".join(f"{TASTEN_NAME.get(t, t)} = {namen[a]}" for t, a in reihe)


def tasten_kurz(belegung):
    """Kurzfassung für die Hilfezeile der Maske, z. B. „Vorspulen/Rückspulen = Feld · F3 = übernehmen · F4 = Maske aus“."""
    def namen(aktion):
        return [TASTEN_NAME.get(t, t) for t, a in sorted(belegung.items()) if a == aktion]
    vor, zur = namen("naechstes_feld"), namen("voriges_feld")
    teile = []
    if len(vor) == 1 and len(zur) == 1:
        teile.append(f"{vor[0]}/{zur[0]} = Feld")
    else:
        teile += [f"{'/'.join(vor)} = nächstes Feld"] if vor else []
        teile += [f"{'/'.join(zur)} = voriges Feld"] if zur else []
    teile += [f"{'/'.join(namen('uebernehmen'))} = übernehmen"] if namen("uebernehmen") else []
    teile += [f"{'/'.join(namen('maske_umschalten'))} = Maske aus"] if namen("maske_umschalten") else []
    return " · ".join(teile)


TASTEN_NAME = {"FF": "Vorspulen", "REW": "Rückspulen", "F3": "F3", "F4": "F4", "INSTR": "INSTR", "COMMAND": "Command",
               "PLAY": "Play"}


# ───────────────────────────── Text-Hilfen ─────────────────────────────
def datum_kurz(iso):
    """„2024-06-05“ → „05.06.2024“ (sonst unverändert)."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(iso or "").strip())
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else str(iso or "").strip()


def _norm(text):
    t = (text or "").lower().replace("ß", "ss")
    t = re.sub(r"[^\wäöü]+", " ", t)
    return " ".join(t.split())


def satz(text):
    """Feldtext sauber: Leerraum zusammengezogen, groß am Anfang, Punkt am Ende (außer nach : ! ? )."""
    t = " ".join(str(text or "").replace("\r", "\n").split(" "))
    zeilen = [" ".join(z.split()) for z in t.split("\n")]
    t = "\n".join(z for z in zeilen if z).strip()
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    if t[-1] not in ".:!?)":
        t += "."
    return t


def _klein_anfang(text):
    return text[:1].lower() + text[1:] if text else text


# ───────────────────────────── Werte (ACR / BI-RADS) ─────────────────────────────
_ZAHLWORT = {"null": "0", "eins": "1", "ein": "1", "zwei": "2", "zwo": "2", "drei": "3", "vier": "4", "fünf": "5",
             "fuenf": "5", "sechs": "6", "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6"}
_ACR = re.compile(r"\b(?:ACR|(?:Brust|Drüsen)?[Dd]ichte(?:typ)?)(?:[\s-]*(?:Typ|Kategorie|Dichte))?[\s:.,=-]*"
                  r"(?P<v>[1-4]|[A-Da-d]|IV|I{1,3}|eins|zwei|zwo|drei|vier)(?![\wäöü])", re.I)
_BIRADS = re.compile(r"\bBI[\s-]?RADS(?:[\s-]*Kategorie)?[\s:.,=-]*"
                     r"(?P<v>[0-6](?:\s?[a-c](?![\wäöü]))?|VI|IV|V|I{1,3}|null|eins|zwei|drei|vier|fünf|fuenf|sechs)"
                     r"(?![\wäöü])", re.I)


def _wert(v, art):
    v = str(v or "").strip()
    w = _ZAHLWORT.get(v.lower())
    if w is not None and not (art == "acr" and v.lower() in ("v", "vi")):
        return w
    if art == "acr" and len(v) == 1 and v.isalpha():
        return v.upper()
    return v.replace(" ", "").lower() if art == "birads" else v


def werte_aus_text(text):
    """→ (Text ohne die Wert-Angaben, {"acr": …, "birads": …}) — nur gefundene Werte. Groß/klein, „BI-RADS“/„Birads“,
    „Dichte B“, Zahlwörter und römische Ziffern; die Werte bleiben in der diktierten Schreibweise (ACR B bleibt B)."""
    werte, rest = {}, str(text or "")
    for art, muster in (("birads", _BIRADS), ("acr", _ACR)):
        m = muster.search(rest)
        if not m:
            continue
        werte[art] = _wert(m.group("v"), art)
        rest = rest[:m.start()] + " " + rest[m.end():]
    rest = re.sub(r"[ \t]+", " ", rest)
    rest = re.sub(r"\s+([.,;:])", r"\1", rest)
    rest = re.sub(r"([.,;:])(?:\s*[.,;:])+", r"\1", rest)
    rest = re.sub(r"(?m)^[\s.,;:]+|[\s,;:]+$", "", rest).strip()
    return rest, werte


def werte_in_text(text):
    """Nur lesen (ohne Entfernen): Werte, die in einem anderen Feld mitdiktiert wurden („Drüsendichte ACR B“)."""
    return werte_aus_text(text)[1]


# ───────────────────────────── Vorbefund zerlegen ─────────────────────────────
@dataclass
class Zerlegung:
    felder: Dict[str, str] = field(default_factory=dict)
    werte: Dict[str, str] = field(default_factory=dict)
    titel: str = ""
    rest: str = ""                      # nach dem Ergebnis (Screening-Text, Befunder) — nur im Vorbefund-Fenster

    @property
    def anzahl(self):
        return sum(1 for v in self.felder.values() if v.strip())


def _labels(maske_def):
    """[(Synonym, feld_id, anhaengen)] — längste zuerst (die Alternative probiert links nach rechts)."""
    out = []
    for f in maske_def.get("felder") or []:
        for s in [f.get("label", "")] + list(f.get("synonyme") or []):
            if s:
                out.append((s, f["id"], False))
        for s in f.get("anhaengen") or []:
            out.append((s, f["id"], True))
    return sorted(set(out), key=lambda x: (-len(x[0]), x[0]))


def _syn_muster(s):
    out = []
    for t in re.split(r"(\s*/\s*|\s+)", s.strip()):
        if not t:
            continue
        out.append(r"\s*/\s*" if "/" in t else (r"\s+" if t.isspace() else re.escape(t)))
    return "".join(out)


def _label_muster(maske_def):
    labels = _labels(maske_def)
    alt = "|".join(f"(?P<g{i}>{_syn_muster(s)})" for i, (s, _, _) in enumerate(labels))
    return re.compile(r"(?:" + alt + r")(?![\wäöüÄÖÜß])[ \t]*(?P<doppelpunkt>:)?", re.I), labels


def _ergebnis_ids(maske_def):
    return {f["id"] for f in maske_def.get("felder") or [] if f.get("typ") == "ergebnis"}


def zerlegen(text, maske_def):
    """Vorbefund-Text (Befundteil, Klartext) → Felder nach Labels. Ein Label zählt am Zeilenanfang oder nach einem
    Satzende und braucht den Doppelpunkt (das Ergebnis-Label auch allein in seiner Zeile). Text vor dem ersten Label =
    Titel. Das Ergebnis endet an der ersten Leerzeile bzw. nach den ACR/BI-RADS-Zeilen; was danach kommt (Screening-Text,
    Befunder, Gruß), gehört zu keinem Feld."""
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    z = Zerlegung()
    if not text.strip():
        return z
    muster, labels = _label_muster(maske_def)
    erg_ids = _ergebnis_ids(maske_def)
    treffer = []
    for m in muster.finditer(text):
        davor = text[:m.start()]
        am_zeilenanfang = not davor.rsplit("\n", 1)[-1].strip()
        nach_satz = not am_zeilenanfang and bool(re.search(r"[.!?]\s+$", davor))
        if not (am_zeilenanfang or nach_satz):
            continue
        i = next(k for k in range(len(labels)) if m.group(f"g{k}") is not None)
        _syn, fid, anh = labels[i]
        if not m.group("doppelpunkt"):
            # ohne Doppelpunkt nur das Ergebnis-Label allein in seiner Zeile („Mammographie beidseits – …“ ist ein Titel)
            if not (fid in erg_ids and am_zeilenanfang and not text[m.end():].split("\n", 1)[0].strip()):
                continue
        treffer.append((m.start(), m.end(), fid, anh, m.group(f"g{i}")))
    if not treffer:
        z.titel = text.strip()
        return z
    z.titel = text[:treffer[0][0]].strip()
    for k, (a, e, fid, anh, label) in enumerate(treffer):
        ende = treffer[k + 1][0] if k + 1 < len(treffer) else len(text)
        stueck = text[e:ende]
        if fid in erg_ids:
            stueck, rest = _ergebnis_schneiden(stueck, maske_def)
            if rest:
                z.rest = (z.rest + "\n\n" + rest).strip()
        inhalt = " ".join(l.strip() for l in stueck.split("\n") if l.strip())
        if anh and inhalt:
            inhalt = " ".join(label.split()) + ": " + inhalt
        if not inhalt:
            continue
        z.felder[fid] = (z.felder.get(fid, "") + " " + inhalt).strip()
    for fid in list(z.felder):
        if fid in erg_ids:
            rest, w = werte_aus_text(z.felder[fid])
            z.werte.update(w)
            z.felder[fid] = rest
    return z


_WERT_ZEILE = re.compile(r"\s*(?:ACR|BI[\s-]?RADS)\b", re.I)


def _ergebnis_schneiden(stueck, maske_def):
    """Ergebnis bis zur ersten Leerzeile; ACR/BI-RADS-Zeilen gleich danach gehören dazu, nach ihnen endet es; ebenso an
    einer Zeile, die mit einem Schluss-Merkmal aus masken.json beginnt („Verlaufskontrolle …“, „Erstbefunder …“).
    → (ergebnis, rest)."""
    ende_worte = [w.lower() for w in maske_def.get("ergebnis_ende") or []]
    zeilen = stueck.split("\n")
    ergebnis, i, inhalt, wert_gesehen = [], 0, False, False
    while i < len(zeilen):
        z = zeilen[i]
        if not z.strip():
            if inhalt:
                j = i
                while j < len(zeilen) and not zeilen[j].strip():
                    j += 1
                if j < len(zeilen) and _WERT_ZEILE.match(zeilen[j]) and not wert_gesehen:
                    i = j
                    continue
                break
            i += 1
            continue
        ist_wert = bool(_WERT_ZEILE.match(z))
        if (wert_gesehen and not ist_wert) or any(z.strip().lower().startswith(w) for w in ende_worte):
            break
        wert_gesehen = wert_gesehen or ist_wert
        inhalt = True
        ergebnis.append(z)
        i += 1
    return "\n".join(ergebnis), "\n".join(zeilen[i:]).strip()


# ───────────────────────────── „unverändert“ + Vergleichsdatum ─────────────────────────────
_DATUM = r"(?:\d{1,2}\.\s?\d{1,2}\.\s?\d{2,4}|\d{1,2}/\d{2,4}|\d{4}|\.{3,}|…+)"
_VERGLEICH_DATUM = re.compile(r"^(?P<praefix>(?:Verglichen|Im\s+Vergleich)\s+(?:mit|zu|zur)\s+(?:(?:der|den|dem)\s+)?"
                              r"(?:Vor\w*\s+)?(?:vom\s+)?)(?P<datum>" + _DATUM + r")", re.I)
_VERGLEICH_OHNE = re.compile(r"^(?:Verglichen|Im\s+Vergleich)\s+(?:mit|zu|zur)\s+(?:(?:der|den|dem)\s+)?Vor\w+\b", re.I)
_PLATZHALTER = re.compile(r"^(?:Verglichen|Im\s+Vergleich)\s+(?:mit|zu|zur)\s+(?:\.{3,}|…+)\s*(?:unverändert\s+)?", re.I)


def ist_unveraendert(text, maske_def):
    """Ist das Diktat eines Felds nur „unverändert“ (oder eine Variante aus masken.json)?"""
    n = _norm(text)
    return bool(n) and n in {_norm(p) for p in maske_def.get("unveraendert") or []}


def vergleich(text, datum, maske_def):
    """Vorbefund-Text eines Felds als heutiger Befund „unverändert verglichen mit <Datum>“ (deterministisch, ohne KI).
    1. beginnt mit „Verglichen mit <Datum> …“ → nur das Datum ersetzt; 2. „Verglichen mit der Voruntersuchung …“ (ohne
    Datum) → „Verglichen mit <Datum> …“; 3. „Kein/Keine …“ → „Verglichen mit <Datum> weiterhin keine …“; 4. beginnt mit
    einem Eigenschaftswort aus masken.json → „Verglichen mit <Datum> unverändert <klein> …“; 5. sonst
    „Verglichen mit <Datum> unverändert. <Text>“."""
    t = " ".join(str(text or "").split())
    d = datum_kurz(datum)
    if not t:
        return ""
    if not d:
        return satz(t)
    m = _VERGLEICH_DATUM.match(t)
    if m:
        praefix = m.group("praefix")
        if re.search(r"\bvom\s+$", praefix, re.I) is None and re.search(r"\bVor\w+\s+$", praefix, re.I):
            praefix += "vom "
        return satz(praefix + d + t[m.end():])
    m = _VERGLEICH_OHNE.match(t)
    if m:
        return satz(f"Verglichen mit {d}" + t[m.end():])
    if re.match(r"keine?\b", t, re.I):
        return satz(f"Verglichen mit {d} weiterhin {_klein_anfang(t)}")
    erstes = _norm(t.split(" ", 1)[0])
    klein = {_norm(w) for w in (maske_def.get("vergleich") or {}).get("klein_anfang") or []}
    if any(erstes == w or (erstes.startswith(w) and len(erstes) - len(w) <= 3) for w in klein):
        return satz(f"Verglichen mit {d} unverändert {_klein_anfang(t)}")
    return satz(f"Verglichen mit {d} unverändert. {t}")


def ohne_platzhalter(text, datum=""):
    """Normalbaustein („Verglichen mit .......... unverändert …“): mit Vorbefund-Datum eingesetzt, ohne Vorbefund der
    Vergleich weg („Kleinfleckig strukturierter …“)."""
    t = " ".join(str(text or "").split())
    m = _PLATZHALTER.match(t)
    if not m:
        return satz(t)
    if datum:
        return satz(f"Verglichen mit {datum_kurz(datum)} unverändert " + t[m.end():])
    return satz(t[m.end():])


# ───────────────────────────── Auslöser ─────────────────────────────
def erkennen(leistungen, maske_def):
    """CAS-Leistungen → {"art": "screening"|"kurativ", "seite": …, "sono": bool} oder None (keine Mammographie).
    Mammo: Leistung mit „mammo“ (aus der Datenbank: Tarif-Kennzeichen) oder Vorlage aus masken.json (Rückfall: Kürzel/Text
    über die Zuordnung). Screening: „mammo“ = screening oder Leistungstext mit „Screening“/„Rescreen“. Sono: eigene
    Mamma-Sono-Leistung (Vorlage aus masken.json) oder Mammo-Leistung „… und Sonographie“ (Kombi-Leistung)."""
    a = maske_def.get("ausloeser") or {}
    vorlagen = set(a.get("vorlagen") or [])
    sono_vorlagen = set(a.get("sono_vorlagen") or [])
    worte_screening = [w.lower() for w in a.get("screening_worte") or []]
    worte_sono = [w.lower() for w in a.get("sono_worte") or []]
    mammo, sono = [], False
    for l in leistungen or []:
        if not isinstance(l, dict) or l.get("ohne_vorlage"):
            continue
        text = str(l.get("text") or "").lower()
        if l.get("mammo") in ("screening", "kurativ") or l.get("vorlage") in vorlagen:
            mammo.append(l)
            if any(w in text for w in worte_sono):
                sono = True
        elif l.get("vorlage") in sono_vorlagen:
            sono = True
        elif (l.get("modalitaet") == "Sono" or any(w in text for w in worte_sono)) and ("mamm" in text or "brust" in text):
            sono = True                          # Mamma-Sono mit (noch) unbekanntem Kürzel: Modalität + Text
    if not mammo:
        return None
    screening = any(l.get("mammo") == "screening" or any(w in str(l.get("text") or "").lower() for w in worte_screening)
                    for l in mammo)
    seiten = {str(l.get("seite") or "").strip().lower() for l in mammo} - {""}
    seite = seiten.pop() if len(seiten) == 1 and seiten <= {"rechts", "links"} else None
    return {"art": "screening" if screening else "kurativ", "seite": seite, "sono": sono}


# ───────────────────────────── Maske (Zustand) ─────────────────────────────
@dataclass
class Feld:
    id: str
    label: str
    typ: str = "text"                       # "text" | "ergebnis" (mit ACR/BI-RADS)
    vergleich: bool = False                 # „unverändert“/Übernehmen → Satz mit Vergleichsdatum
    nur_mit_sono: bool = False
    sichtbar: bool = True                   # False: nicht in den Leistungen — eingeklappt, kommt nur mit Diktat/Klick dazu
    vorschlag: str = ""                     # Text aus dem Vorbefund bzw. dem Normalbaustein
    vorschlag_art: str = ""                 # VORBEFUND | VORLAGE | ""
    vorschlag_werte: Dict[str, str] = field(default_factory=dict)
    quelle: str = LEER
    teile: List[Optional[str]] = field(default_factory=list)   # Diktat-Abschnitte (None = Spracherkennung läuft)
    sitzung: int = 0                        # steigt, wenn das Feld geleert wird (späte Erkennung alter Abschnitte verfällt)
    text: str = ""                          # übernommener / getippter Text (bei DIKTAT: Ergebnis der Verarbeitung)
    werte: Dict[str, str] = field(default_factory=dict)        # heutige Werte (übernommen/getippt/diktiert)
    verarbeitet: Dict[str, tuple] = field(default_factory=dict)  # Rohtext → (Text, Werte, Hinweis): je Diktat nur einmal KI

    @property
    def roh(self):
        return " ".join(t.strip() for t in self.teile if t and t.strip())

    @property
    def wartet(self):
        return any(t is None for t in self.teile)

    @property
    def offen(self):
        """Vorschlag da, aber weder übernommen noch diktiert/getippt (nur sichtbare Felder)."""
        return self.sichtbar and self.quelle in VORSCHLAG and bool(self.vorschlag.strip() or self.vorschlag_werte)


def _acr_gleich(a, b):
    m = {"a": "1", "b": "2", "c": "3", "d": "4"}
    a, b = str(a or "").strip().lower(), str(b or "").strip().lower()
    return m.get(a, a) == m.get(b, b)


class Maske:
    """Zustand einer offenen Maske: Felder, aktives Feld, Version (jede Änderung zählt hoch — EOL schickt nur einen
    Befund, der aus dem aktuellen Stand gebaut wurde)."""

    def __init__(self, maske_def, art="kurativ", seite=None, sono=False, vorbefund=None, normal=None, schluss_an=True):
        self.definition = maske_def
        self.art, self.seite, self.sono = art, seite, bool(sono)
        self.vorbefund = vorbefund if isinstance(vorbefund, dict) and str(vorbefund.get("text") or "").strip() else None
        self.datum = datum_kurz((self.vorbefund or {}).get("datum"))
        self.schluss_an = schluss_an
        self.version = 0
        self.felder = []
        for f in maske_def.get("felder") or []:
            nur_sono = bool(f.get("nur_mit_sono"))
            self.felder.append(Feld(id=f["id"], label=f.get("label") or f["id"], typ=f.get("typ") or "text",
                                    vergleich=bool(f.get("vergleich")), nur_mit_sono=nur_sono,
                                    sichtbar=not nur_sono or self.sono))
        self.aktiv = 0
        self.zerlegung = Zerlegung()
        self._normal = normal or Zerlegung()
        self._vorschlaege_setzen()

    # Vorschläge ───────────────────────────────────────────────────────────────
    def _vorschlaege_setzen(self):
        if self.vorbefund:
            self.zerlegung = zerlegen(self.vorbefund.get("text"), self.definition)
        werte_db = {k: str(v).strip() for k, v in ((self.vorbefund or {}).get("werte") or {}).items()
                    if k in ("acr", "birads") and str(v or "").strip() not in ("", "-1", "None", "null")}
        for f in self.felder:
            f.vorschlag, f.vorschlag_art, f.vorschlag_werte = "", "", {}
            t = self.zerlegung.felder.get(f.id, "").strip()
            if t:
                f.vorschlag, f.vorschlag_art = t, VORBEFUND
            elif self._normal.felder.get(f.id, "").strip():
                f.vorschlag, f.vorschlag_art = ohne_platzhalter(self._normal.felder[f.id], self.datum), VORLAGE
            if f.typ == "ergebnis" and self.vorbefund:
                w = dict(self.zerlegung.werte)
                w.update(werte_db)          # Doppelbefundung (final) geht vor dem Text des Briefs
                f.vorschlag_werte = w
                if w and f.vorschlag_art != VORBEFUND:   # nur Werte im Vorbefund: Vorschlag = diese Werte
                    f.vorschlag_art, f.vorschlag = VORBEFUND, ""
            if f.quelle in VORSCHLAG + (LEER,):
                f.quelle = f.vorschlag_art or LEER

    def vorbefund_setzen(self, vorbefund):
        """Kontext kam nach dem Öffnen (Datenbank langsamer als die Leistungen): Vorschläge ergänzen — nur Felder, die noch
        Vorschlag/leer sind, ändern sich."""
        if not (isinstance(vorbefund, dict) and str(vorbefund.get("text") or "").strip()):
            return False
        self.vorbefund = vorbefund
        self.datum = datum_kurz(vorbefund.get("datum"))
        self._vorschlaege_setzen()
        self._geaendert()
        return True

    def werte_abweichung(self):
        """Hinweis, wenn ACR/BI-RADS im Text des Vorbefunds anders stehen als in der Doppelbefundung (final)."""
        db = {k: str(v).strip() for k, v in ((self.vorbefund or {}).get("werte") or {}).items()
              if k in ("acr", "birads") and str(v or "").strip() not in ("", "-1", "None", "null")}
        text = self.zerlegung.werte
        diff = [k for k in ("acr", "birads") if k in db and k in text
                and not (_acr_gleich(db[k], text[k]) if k == "acr" else db[k].lower() == text[k].lower())]
        if not diff:
            return ""
        return "Vorbefund: " + ", ".join(f"{_WERT_LABEL[k]} im Brief {text[k]}, Doppelbefundung {db[k]}" for k in diff)

    # Navigation ───────────────────────────────────────────────────────────────
    @property
    def feld(self):
        return self.felder[self.aktiv]

    def index(self, fid):
        return next((i for i, f in enumerate(self.felder) if f.id == fid), None)

    def naechstes(self):
        """Feste Reihenfolge, auch über ein eingeklapptes Feld (blind: „3× Vorspulen = Ergebnis“). Am Ende bleibt es."""
        if self.aktiv + 1 < len(self.felder):
            self.aktiv += 1
            return True
        return False

    def voriges(self):
        if self.aktiv > 0:
            self.aktiv -= 1
            return True
        return False

    def gehe_zu(self, i):
        if 0 <= i < len(self.felder):
            self.aktiv = i
            return True
        return False

    def _geaendert(self):
        self.version += 1

    def _leeren(self, f):
        f.teile, f.text, f.werte, f.verarbeitet = [], "", {}, {}
        f.sitzung += 1

    # Übernehmen / Diktat / Tippen ─────────────────────────────────────────────
    def uebernehmen(self, i=None):
        """Vorschlag des Felds bewusst übernehmen (Vorbefund: mit Vergleichsdatum, wie „unverändert“). Noch einmal = wieder
        Vorschlag. → Meldung für die Hilfezeile."""
        f = self.felder[self.aktiv if i is None else i]
        if f.quelle == UEBERNOMMEN:
            self._leeren(f)
            f.quelle = f.vorschlag_art or LEER
            self._geaendert()
            return f"{f.label}: wieder Vorschlag (nicht übernommen)"
        if f.quelle not in VORSCHLAG:
            if f.quelle in (DIKTAT, GETIPPT):
                return f"{f.label}: heute {'diktiert' if f.quelle == DIKTAT else 'getippt'} – F3 noch einmal = verwerfen"
            return f"{f.label}: kein Vorbefund – Record diktiert"
        self._leeren(f)
        f.text = self._vorschlag_heute(f)
        f.werte = dict(f.vorschlag_werte) if f.typ == "ergebnis" else {}
        f.quelle, f.sichtbar = UEBERNOMMEN, True
        self._geaendert()
        return f"{f.label}: übernommen" + (f" (verglichen mit {self.datum})" if f.vergleich and f.vorschlag_art == VORBEFUND
                                            and self.datum else "")

    def _vorschlag_heute(self, f):
        if not f.vorschlag.strip():
            return ""
        if f.vorschlag_art == VORBEFUND and f.vergleich:
            return vergleich(f.vorschlag, self.datum, self.definition)
        return satz(f.vorschlag)

    def verwerfen(self, i=None):
        """Heutiges Diktat bzw. getippten Text des Felds verwerfen → wieder der Vorschlag (bzw. leer)."""
        f = self.felder[self.aktiv if i is None else i]
        self._leeren(f)
        f.quelle = f.vorschlag_art or LEER
        if f.nur_mit_sono and not self.sono:
            f.sichtbar = False
        self._geaendert()
        return f"{f.label}: Diktat verworfen" + (" – wieder Vorbefund" if f.vorschlag_art == VORBEFUND else "")

    def reservieren(self, i=None):
        """Diktat-Abschnitt für das Feld anmelden (Spracherkennung läuft). Der Stand des Felds ändert sich erst, wenn
        Text erkannt ist — Stille beim Durchspringen ändert nichts. → (Feld-Index, Sitzung, Teil-Index)."""
        k = self.aktiv if i is None else i
        f = self.felder[k]
        f.teile.append(None)
        return k, f.sitzung, len(f.teile) - 1

    def diktat_fertig(self, k, sitzung, teil, text):
        """Erkannter Text eines Abschnitts. Das erste Wort ersetzt Vorschlag/Übernommenes/Getipptes (Diktat gewinnt);
        weitere Abschnitte im selben Feld hängen an (Nachdiktat). Leer (Stille) → nichts ändert sich."""
        f = self.felder[k]
        if sitzung != f.sitzung or teil >= len(f.teile):
            return False
        t = (text or "").strip()
        f.teile[teil] = t
        if t and f.quelle != DIKTAT:
            f.text, f.werte, f.verarbeitet = "", {}, {}
            f.quelle, f.sichtbar = DIKTAT, True     # diktiert = gewollt (auch ein eingeklapptes Sono-Feld)
        if t:
            f.verarbeitet = {}
        self._geaendert()
        return True

    def tippen(self, i, text):
        """Von Hand im Feld geändert → getippt (wie geschrieben, ohne KI). Unverändert gegenüber der Anzeige → nichts."""
        f = self.felder[i]
        t = (text or "").strip()
        if t == vorschau(f, self).strip():
            return False
        self._leeren(f)
        # wie getippt stehen lassen (auch „ACR: 1“-Zeilen im Ergebnis — die Werte liest erst der Befund heraus)
        f.text, f.quelle, f.sichtbar = t, (GETIPPT if t else (f.vorschlag_art or LEER)), True
        self._geaendert()
        return True

    def sichtbar_schalten(self, i):
        """Eingeklapptes Feld (z. B. Sonographie ohne Sono-Leistung) per Klick zuschalten / wieder einklappen."""
        f = self.felder[i]
        if not f.nur_mit_sono:
            return False
        f.sichtbar = not f.sichtbar
        self._geaendert()
        return True

    def neu(self):
        """F1/F9 „Neu“: alles Heutige weg, wieder die Vorschläge."""
        for f in self.felder:
            self._leeren(f)
            f.quelle = f.vorschlag_art or LEER
            f.sichtbar = not f.nur_mit_sono or self.sono
        self.aktiv = 0
        self._geaendert()

    # Prüfen vor INS ───────────────────────────────────────────────────────────
    def offene(self):
        return [f for f in self.felder if f.offen]

    def wartende(self):
        return [f for f in self.felder if f.wartet]

    def heutiges(self):
        return any(f.quelle in (DIKTAT, GETIPPT, UEBERNOMMEN) for f in self.felder)

    def zustand(self):
        """Für Selbsttest/Protokoll: je Feld id:quelle (ohne Text)."""
        return " ".join(f"{f.id}:{f.quelle}{'' if f.sichtbar else '(aus)'}{'…' if f.wartet else ''}" for f in self.felder)


def vorschau(f, maske):
    """Was das Feld JETZT zeigt (Vorschlag, Übernommenes, Getipptes, Diktat — „unverändert“ gleich mit Vergleichssatz,
    sonst das Erkannte, nach INS der korrigierte Text)."""
    if f.quelle in VORSCHLAG:
        return f.vorschlag
    if f.quelle in (UEBERNOMMEN, GETIPPT):
        return f.text
    if f.quelle == DIKTAT:
        roh = f.roh
        if roh in f.verarbeitet:
            return f.verarbeitet[roh][0]
        t = roh
        if f.typ == "ergebnis":
            t = werte_aus_text(t)[0]
        if ist_unveraendert(t, maske.definition) and f.vorschlag_art == VORBEFUND and f.vorschlag.strip():
            return vergleich(f.vorschlag, maske.datum, maske.definition) if f.vergleich else satz(f.vorschlag)
        return roh
    return ""


def werte_vorschau(f, maske):
    """ACR/BI-RADS, die das Feld gerade trägt (Vorschlag, übernommen/getippt, diktiert — „unverändert“ mit den Werten des
    Vorbefunds, diktierte Werte gehen vor)."""
    if f.typ != "ergebnis":
        return {}
    if f.quelle in VORSCHLAG:
        return dict(f.vorschlag_werte)
    if f.quelle == DIKTAT:
        roh = f.roh
        if roh in f.verarbeitet:
            return dict(f.verarbeitet[roh][1])
        t, w = werte_aus_text(roh)
        if ist_unveraendert(t, maske.definition) and f.vorschlag_art == VORBEFUND:
            v = dict(f.vorschlag_werte)
            v.update(w)
            return v
        return w
    if f.quelle == GETIPPT:
        return werte_aus_text(f.text)[1]
    return dict(f.werte)


_WERT_LABEL = {"acr": "ACR", "birads": "BI-RADS"}


# ───────────────────────────── Befund bauen (INS) ─────────────────────────────
@dataclass
class Befund:
    report: str = ""
    hinweise: List[str] = field(default_factory=list)    # nur Anzeige (Band/Hilfezeile)
    ohne: List[str] = field(default_factory=list)          # Felder mit offenem Vorschlag, die NICHT im Befund stehen
    werte: Dict[str, str] = field(default_factory=dict)
    ki_aufrufe: int = 0


def feld_verarbeiten(f, maske, korrektur=None, misheard=None):
    """Diktat eines Felds → (Text, Werte, Hinweis). „unverändert“ mit Vorbefund → Vorbefund mit Vergleichsdatum (ohne KI);
    sonst Fehlhör-Liste → Korrektur (KI bekommt NUR dieses Diktat) → sauberer Satz. Ergebnis: ACR/BI-RADS heraus."""
    roh = f.roh
    if roh in f.verarbeitet:
        return f.verarbeitet[roh] + (False,)
    t = misheard(roh) if misheard else roh
    werte = {}
    if f.typ == "ergebnis":
        t, werte = werte_aus_text(t)
    hinweis, ki = "", False
    if ist_unveraendert(t, maske.definition):
        if f.vorschlag_art == VORBEFUND and f.vorschlag.strip():
            text = vergleich(f.vorschlag, maske.datum, maske.definition) if f.vergleich else satz(f.vorschlag)
            if f.typ == "ergebnis":
                w = dict(f.vorschlag_werte)
                w.update(werte)
                werte = w
        else:
            text = satz(t)
            hinweis = f"{f.label}: „unverändert“ ohne Vorbefund – so übernommen"
    elif t:
        if korrektur:
            k = (korrektur(t) or t).strip()
            ki = True
        else:
            k = t
        if f.typ == "ergebnis":
            k, w2 = werte_aus_text(k)
            for a, v in w2.items():
                werte.setdefault(a, v)
        text = satz(k)
    else:
        text = ""
    erg = (text, werte, hinweis)
    f.verarbeitet = {roh: erg}
    return erg + (ki,)


def vorverarbeiten(maske, korrektur=None, misheard=None, parallel=True):
    """Alle diktierten Felder verarbeiten (KI je Feld parallel, nur Peters Diktat dieses Felds). → Zahl der KI-Aufrufe."""
    felder = [f for f in maske.felder if f.quelle == DIKTAT and f.roh and f.roh not in f.verarbeitet]
    if not felder:
        return 0
    if not parallel or len(felder) == 1:
        return sum(int(bool(feld_verarbeiten(f, maske, korrektur, misheard)[3])) for f in felder)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=len(felder)) as ex:
        erg = list(ex.map(lambda f: feld_verarbeiten(f, maske, korrektur, misheard), felder))
    return sum(int(bool(e[3])) for e in erg)


def befund_bauen(maske, korrektur=None, misheard=None, ohne_offene=False):
    """INS: Befund (Markdown wie RaKScribe: ## Titel / ## Befund / ## Ergebnis) aus den Feldern. Offene Vorschläge
    (weder übernommen noch diktiert) kommen NIE hinein — ohne_offene=False → None + Liste (die Oberfläche warnt zuerst)."""
    d = maske.definition
    offen = maske.offene()
    if offen and not ohne_offene:
        return None
    b = Befund(ohne=[f.label for f in offen])
    texte, werte = {}, {}
    for f in maske.felder:
        if not f.sichtbar and f.quelle not in (DIKTAT, GETIPPT, UEBERNOMMEN):
            continue
        if f.quelle == DIKTAT:
            text, w, hinweis, ki = feld_verarbeiten(f, maske, korrektur, misheard)
            b.ki_aufrufe += int(bool(ki))
            if hinweis:
                b.hinweise.append(hinweis)
            f.text = text
        elif f.quelle == UEBERNOMMEN:
            text, w = f.text, dict(f.werte)
        elif f.quelle == GETIPPT:
            text, w = (werte_aus_text(f.text) if f.typ == "ergebnis" else (f.text, {}))
            text = satz(text)
        else:
            continue
        texte[f.id] = text
        if f.typ == "ergebnis":
            werte.update(w)
    # Werte, die in einem anderen Feld mitdiktiert wurden (z. B. „Drüsendichte ACR B“ im Mammographie-Teil)
    for f in maske.felder:
        if f.typ != "ergebnis" and f.id in texte and f.quelle == DIKTAT:
            for a, v in werte_in_text(texte[f.id]).items():
                werte.setdefault(a, v)
    b.werte = werte
    titel = titel_text(maske)
    zeilen = [f"## {titel}", "", "## Befund"]
    teile = []
    erg = None
    for f in maske.felder:
        if f.id not in texte:
            continue
        if f.typ == "ergebnis":
            erg = texte[f.id]
            continue
        if texte[f.id]:
            teile.append(f"{f.label}: {texte[f.id]}")
    zeilen.append("\n\n".join(teile))
    erg_zeilen = [erg] if erg else []
    for a in ("acr", "birads"):
        lab = (d.get("werte") or {}).get(a, {}).get("label") or _WERT_LABEL[a]
        if werte.get(a):
            erg_zeilen.append(f"{lab}: {werte[a]}")
    if erg_zeilen:
        zeilen += ["", "## Ergebnis", "\n".join(erg_zeilen)]
    fehlend = [(d.get("werte") or {}).get(a, {}).get("label") or _WERT_LABEL[a] for a in ("acr", "birads")
               if not werte.get(a)]
    if fehlend:
        b.hinweise.append(" und ".join(fehlend) + (" fehlen" if len(fehlend) > 1 else " fehlt") + " im Ergebnis")
    erg_feld = next((f for f in maske.felder if f.typ == "ergebnis"), None)
    if erg_feld is not None and erg_feld.quelle == DIKTAT and not erg and werte:
        b.hinweise.append(f"{erg_feld.label}: nur ACR/BI-RADS diktiert, kein Ergebnissatz")
    schluss, hinweis = schluss_text(maske, werte.get("birads"))
    if schluss:
        zeilen += ["", schluss]
    if hinweis:
        b.hinweise.append(hinweis)
    if b.ohne:
        b.hinweise.insert(0, "Nicht im Befund (Vorschlag nicht übernommen): " + ", ".join(b.ohne))
    b.report = "\n".join(zeilen).strip()
    return b


def titel_text(maske):
    t = (maske.definition.get("titel") or {})
    muster = t.get(maske.art) or t.get("kurativ") or "{seite}"
    return muster.format(seite=maske.seite or t.get("seite_standard") or "beidseits").strip()


def schluss_text(maske, birads):
    """Screening-Baustein je BI-RADS (masken.json „schluss“). → (Text oder "", Hinweis oder "")."""
    if not maske.schluss_an or maske.art != "screening":
        return "", ""
    s = (maske.definition.get("schluss") or {}).get("screening") or {}
    b = str(birads or "").strip().lower()
    if not b:
        return "", ""
    text = (s.get("texte") or {}).get(b)
    if text:
        return text, ""
    return "", (s.get("hinweis_sonst") or "").format(birads=b.upper())


def offene_meldung(maske):
    """Warnung vor INS: welche Felder noch Vorbefund-/Vorschlag-Stand haben (nichts wird still übernommen)."""
    offen = maske.offene()
    if not offen:
        return ""
    namen = ", ".join(f.label + (" (Vorbefund)" if f.vorschlag_art == VORBEFUND else " (Normalbaustein)") for f in offen)
    return (f"Noch nicht übernommen: {namen} – F3 übernimmt · Record diktiert neu · INS noch einmal = ohne diese "
            f"{'Felder' if len(offen) > 1 else 'Feld'}")


def normal_zerlegung(bausteine, maske_def):
    """Normalbaustein aus den Ordi-Bausteinen (masken.json „normalbaustein“, z. B. mam1 = „Baustein Mammo 1“) → Felder."""
    key = maske_def.get("normalbaustein")
    b = (bausteine or {}).get(key) if key else None
    if not isinstance(b, dict):
        return Zerlegung()
    text = (b.get("befund") or "") + "\n\nErgebnis:\n" + (b.get("ergebnis") or "")
    z = zerlegen(text, maske_def)
    z.werte = {}
    for fid in list(z.felder):     # „ACR / BIRADS“ ohne Wert (Platzhalter) ist kein Vorschlag
        if not re.sub(r"(?i)\b(?:ACR|BI-?RADS)\b", "", z.felder[fid]).strip(" .\n"):
            z.felder.pop(fid)
    return z


def anzeige_zustand(f, datum=""):
    """Kurztext rechts am Feld (Chip)."""
    if not f.sichtbar:
        return "eingeklappt – keine Sono-Leistung" if f.nur_mit_sono else "eingeklappt"
    return {VORBEFUND: f"Vorbefund {datum}".strip(), VORLAGE: "Normalbaustein (Vorschlag)", UEBERNOMMEN: "✓ übernommen",
            DIKTAT: "… erkennt" if f.wartet else "diktiert", GETIPPT: "getippt", LEER: "leer"}.get(f.quelle, f.quelle)
