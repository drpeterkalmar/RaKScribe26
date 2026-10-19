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

v3.15.4 (Peter 15.10.: „wenn ich den bestehenden text markiere wird er durch mein diktat überschrieben. oder ich lösche ihn
selbständig“): Markierung im Feld → das nächste Diktat ersetzt genau sie; Cursor im Feld mit heutigem Text → an der Stelle
einfügen; sonst wie bisher. Steht danach Vorbefund-/Normalbaustein-Text mit im Feld, gilt es als getippt (ohne KI — die
KI bekommt weiterhin nur Peters Diktat). Abschnitte eines Felds werden in ihrer Reihenfolge angewendet.
"""
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import einfuegen as _einf

LEER, VORBEFUND, VORLAGE, UEBERNOMMEN, DIKTAT, GETIPPT = "leer", "vorbefund", "vorlage", "uebernommen", "diktat", "getippt"
VORSCHLAG = (VORBEFUND, VORLAGE)
AKTIONEN = ("naechstes_feld", "voriges_feld", "uebernehmen", "maske_umschalten")
# eingeübte Tasten (SpeechMike-Bericht 3.8.0) — die Maske deutet sie nie um
FESTE_TASTEN = ("RECORD", "INS", "EOL", "F1", "F2", "STOP")
TASTATUR = "tastatur"   # v3.15.4: kein SpeechMike verbunden (Fern-Test) — Hilfezeile mit den Tastatur-Tasten


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
def tasten_belegung(definition, ueberschreiben=None, log=None, satz="tasten"):
    """{Taste: Aktion} aus masken.json „tasten“ ({Aktion: Taste}), optional überschrieben (config.ini [MASKE]).
    Eine eingeübte Taste (Record, INS, EOL, F1, F2, Stop) oder eine unbekannte Aktion wird nie übernommen.
    v3.15.4: satz = „tasten_ambient“ für das SpeechMike Ambient (ohne F1–F4; config.ini [MASKE] AMBIENT_…)."""
    log = log or (lambda *a: None)
    soll = dict((definition or {}).get(satz) or {})
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


# Anzeige-Reihenfolge je Aktion: F-Tasten (Premium) vor Play/Command (Ambient ohne F1–F4)
_TASTEN_REIHE = ("FF", "REW", "F3", "F4", "PLAY", "COMMAND", "INSTR")


def tasten_fuer(belegung, aktion, verfuegbar=None):
    """Tasten einer Aktion in Anzeige-Reihenfolge; verfuegbar = Tasten des erkannten Geräts (None = alle)."""
    t = [k for k, a in belegung.items() if a == aktion and (verfuegbar in (None, TASTATUR) or k in verfuegbar)]
    return sorted(t, key=lambda k: (_TASTEN_REIHE.index(k) if k in _TASTEN_REIHE else len(_TASTEN_REIHE), k))


def taste_name(belegung, aktion, verfuegbar=None):
    """Name der Taste für Hinweise („Play noch einmal = verwerfen“): ohne SpeechMike die Tastatur (F3/F4), sonst die
    erste Taste des Geräts für diese Aktion."""
    if verfuegbar == TASTATUR:
        return {"uebernehmen": "F3", "maske_umschalten": "F4"}.get(aktion, "")
    t = tasten_fuer(belegung, aktion, verfuegbar)
    return TASTEN_NAME.get(t[0], t[0]) if t else {"uebernehmen": "F3", "maske_umschalten": "F4"}.get(aktion, "")


def tasten_text(belegung):
    """Kurztext für Protokoll und Menü, mehrere Tasten einer Aktion mit „/“, z. B. „Vorspulen = nächstes Feld ·
    Rückspulen = voriges Feld · F3/Play = Vorbefund übernehmen · F4/Command = Maske aus/an“."""
    namen = {"naechstes_feld": "nächstes Feld", "voriges_feld": "voriges Feld", "uebernehmen": "Vorbefund übernehmen",
             "maske_umschalten": "Maske aus/an"}
    out = []
    for aktion in AKTIONEN:
        t = tasten_fuer(belegung, aktion)
        if t:
            out.append(f"{'/'.join(TASTEN_NAME.get(k, k) for k in t)} = {namen[aktion]}")
    return " · ".join(out)


def tasten_kurz(belegung, verfuegbar=None):
    """Kurzfassung für die Hilfezeile der Maske — nur Tasten, die das erkannte Gerät hat (v3.15.4: SpeechMike Ambient
    ohne F1–F4 → „Vorspulen/Rückspulen = Feld · Play = übernehmen · Command = Maske aus“), je Aktion die erste Taste.
    verfuegbar: None = alle (Premium bzw. unbekannt), Menge = Tasten des Geräts, TASTATUR = kein SpeechMike."""
    if verfuegbar == TASTATUR:
        return "Bild↓/Bild↑ = Feld · F3 = übernehmen · F4 = Maske aus"

    def namen(aktion):
        return [TASTEN_NAME.get(t, t) for t in tasten_fuer(belegung, aktion, verfuegbar)]
    vor, zur = namen("naechstes_feld"), namen("voriges_feld")
    teile = []
    if vor and zur:
        teile.append(f"{vor[0]}/{zur[0]} = Feld")
    else:
        teile += [f"{vor[0]} = nächstes Feld"] if vor else []
        teile += [f"{zur[0]} = voriges Feld"] if zur else []
    teile += [f"{namen('uebernehmen')[0]} = übernehmen"] if namen("uebernehmen") else []
    teile += [f"{namen('maske_umschalten')[0]} = Maske aus"] if namen("maske_umschalten") else []
    return " · ".join(teile)


TASTEN_NAME = {"FF": "Vorspulen", "REW": "Rückspulen", "F3": "F3", "F4": "F4", "INSTR": "INSTR", "COMMAND": "Command",
               "PLAY": "Play"}


# ───────────────────────────── Text-Hilfen ─────────────────────────────
def datum_kurz(iso):
    """„2024-06-05“ → „05.06.2024“ (sonst unverändert)."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(iso or "").strip())
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else str(iso or "").strip()


def alter_jahre(iso, heute=None):
    """Volle Jahre seit dem Vorbefund (ISO-Datum) — für den Hinweis „vor N Jahren“ (Probelauf M2: ein Vorbefund war
    8 Jahre alt). None, wenn kein Datum."""
    import datetime
    try:
        d = datetime.date.fromisoformat(str(iso or "")[:10])
    except ValueError:
        return None
    heute = heute or datetime.date.today()
    return int((heute - d).days // 365.25)


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
# v3.16.3 (Ordi-E2E 15.10.: chirp_3 schrieb „… beidseits ACRA 2. BI-RADS 1“ → bisher ACR A und „… beidseits 2.“):
# Buchstabe direkt am bzw. nach „ACR“ und danach eine Zahl im selben Satz → die Zahl ist der Wert, der Buchstabe
# ein Hörfehler. Nur mit Leerzeichen dazwischen und Satzende/BI-RADS danach („ACR A. 2 Herde“ bleibt A).
_ACR_ZAHL = re.compile(r"\bACR[\s:=-]*[A-Da-d]\s+(?P<v>[1-4]|eins|zwei|zwo|drei|vier)(?=\s*(?:[.,;]|$|BI[\s-]?RADS))",
                       re.I)
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
        m = (_ACR_ZAHL.search(rest) if art == "acr" else None) or muster.search(rest)
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
    # 3.15.3 (Ordi-Probelauf M3: „Inspektion u. Palpation:“): „und“ zwischen zwei Wörtern auch als „u.“, „&“, „+“
    return "".join(out).replace(r"\s+und\s+", r"(?:\s+und\s+|\s*(?:u\.|&|\+)\s*)")


def _label_muster(maske_def):
    labels = _labels(maske_def)
    alt = "|".join(f"(?P<g{i}>{_syn_muster(s)})" for i, (s, _, _) in enumerate(labels))
    return re.compile(r"(?:" + alt + r")(?![\wäöüÄÖÜß])[ \t]*(?P<doppelpunkt>:)?", re.I), labels


def _ergebnis_ids(maske_def):
    return {f["id"] for f in maske_def.get("felder") or [] if f.get("typ") == "ergebnis"}


def zerlegen(text, maske_def):
    """Vorbefund-Text (Befundteil, Klartext) → Felder nach Labels. Ein Label zählt am Zeilenanfang oder nach einem
    Satzende und braucht den Doppelpunkt (das Ergebnis-Label auch allein in seiner Zeile). Text vor dem ersten Label =
    Titel. ACR/BI-RADS: aus dem Ergebnis; eigene Wert-Zeilen („ACR: B“) in anderen Abschnitten gehören auch zu den Werten
    (nicht in deren Text). Was nach dem Ergebnis kommt (Screening-Text, Befunder, Gruß), gehört zu keinem Feld."""
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
    werte_aussen = {}
    for k, (a, e, fid, anh, label) in enumerate(treffer):
        ende = treffer[k + 1][0] if k + 1 < len(treffer) else len(text)
        stueck = text[e:ende]
        if fid in erg_ids:
            stueck, rest = _ergebnis_schneiden(stueck, maske_def)
            if rest:
                z.rest = (z.rest + "\n\n" + rest).strip()
        zeilen = [l.strip() for l in stueck.split("\n") if l.strip()]
        if fid not in erg_ids:
            for l in [l for l in zeilen if _ist_wertzeile(l)]:
                for w, v in werte_aus_text(l)[1].items():
                    werte_aussen.setdefault(w, v)
            zeilen = [l for l in zeilen if not _ist_wertzeile(l)]
        inhalt = " ".join(zeilen)
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
            if not rest:
                z.felder.pop(fid)
    for w, v in werte_aussen.items():
        z.werte.setdefault(w, v)
    return z


_WERT_ZEILE = re.compile(r"\s*(?:ACR|BI[\s-]?RADS|(?:Brust|Drüsen)?[Dd]ichte)\b", re.I)


def _ist_wertzeile(z):
    """Eine reine Wert-Zeile („ACR: 2“, „BI-RADS 2 beidseits“, „ACR B, BIRADS 1“) — beginnt mit dem Wert-Label, liefert
    einen Wert, und es bleibt kaum Text übrig. Ein Satz („Dichte des Drüsenkörpers erhöht“) ist keine."""
    if not _WERT_ZEILE.match(z or ""):
        return False
    rest, werte = werte_aus_text(z)
    rest = re.sub(r"(?i)\b(?:beidseits|bds|rechts|links|re|li|und|kategorie|typ)\b", "", rest)
    return bool(werte) and len(re.sub(r"[\W_]+", "", rest)) <= 3


def _ergebnis_schneiden(stueck, maske_def):
    """Ergebnis-Abschnitt bis zu einem Schluss-Merkmal (masken.json „ergebnis_ende“: Screening-Text, Befunder, Gruß).
    Wert-Zeilen (ACR/BI-RADS) darin sind die Werte; Text = alle Absätze VOR der ersten Wert-Zeile (ohne Werte: nur der
    erste Absatz). Nach den Werten Folgendes gehört zu keinem Feld. Stehen die Werte erst nach einem Schluss-Merkmal (alte
    Briefe), zählen eigene Wert-Zeilen dort trotzdem. → (ergebnis, rest)."""
    ende_worte = [w.lower() for w in maske_def.get("ergebnis_ende") or []]
    zeilen = stueck.split("\n")
    n = next((i for i, z in enumerate(zeilen) if z.strip() and any(z.strip().lower().startswith(w) for w in ende_worte)),
             len(zeilen))
    abschnitt, danach = zeilen[:n], zeilen[n:]
    while abschnitt and not abschnitt[0].strip():
        abschnitt = abschnitt[1:]
    wert_idx = [i for i, z in enumerate(abschnitt) if _ist_wertzeile(z)]
    if wert_idx:
        text = [z for z in abschnitt[:wert_idx[0]] if z.strip()]
        werte = [abschnitt[i] for i in wert_idx]
        rest = [z for i, z in enumerate(abschnitt[wert_idx[0]:], wert_idx[0]) if i not in wert_idx] + danach
        return "\n".join(text + werte), "\n".join(rest).strip()
    erster = []
    for i, z in enumerate(abschnitt):
        if not z.strip() and erster:
            danach = abschnitt[i:] + danach
            break
        if z.strip():
            erster.append(z)
    spaete = [z for z in danach if _ist_wertzeile(z)]             # Werte nach dem Screening-Text (alte Briefe)
    rest = [z for z in danach if not _ist_wertzeile(z)]
    return "\n".join(erster + spaete), "\n".join(rest).strip()


# ───────────────────────────── „unverändert“ + Vergleichsdatum ─────────────────────────────
_DATUM = r"(?:\d{1,2}\.\s?\d{1,2}\.\s?\d{2,4}|\d{1,2}/\d{2,4}|\d{4}|\.{3,}|…+)"
_VERGLEICH_DATUM = re.compile(r"^(?P<praefix>(?:Verglichen|Im\s+Vergleich)\s+(?:mit|zu|zur)\s+(?:(?:der|den|dem)\s+)?"
                              r"(?:Vor\w*\s+)?(?:vom\s+)?)(?P<datum>" + _DATUM + r")", re.I)
_VERGLEICH_OHNE = re.compile(r"^(?:Verglichen|Im\s+Vergleich)\s+(?:mit|zu|zur)\s+(?:(?:der|den|dem)\s+)?Vor\w+\b", re.I)
_PLATZHALTER = re.compile(r"^(?:Verglichen|Im\s+Vergleich)\s+(?:mit|zu|zur)\s+(?:\.{3,}|…+)\s*(?:unverändert\s+)?", re.I)
# 3.15.3 (Ordi-Probelauf M3): alte Datumsangaben, die nicht direkt hinter „vom“ stehen — „(12.03.2022)“, „von 2022“,
# „vom März 2022“, „aus dem Jahr 2021“, „12.03.2022 und 01.02.2020“. Sonst bliebe das alte Datum neben dem neuen stehen.
_MONAT = (r"(?:Jänner|Januar|Feber|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember|"
          r"(?:Jan|Feb|Mär|Apr|Jun|Jul|Aug|Sept?|Okt|Nov|Dez)\.)")
_DATUM_ALT = (r"(?:\d{1,2}\.\s?\d{1,2}\.\s?\d{2,4}|\d{1,2}/\d{2,4}|(?:\d{1,2}\.\s?)?" + _MONAT + r"\s+\d{4}|"
              r"(?:19|20)\d{2})(?!\d)")
_VERGLEICH_KOPF = re.compile(
    r"^(?:Verglichen|Im\s+Vergleich)\s+(?:mit|zu|zur)\s+"
    r"(?:(?:der|den|dem|des|die|letzten|letzte|vorangegangenen|vorhergehenden|vorigen|auswärtigen|externen|alten|"
    r"früheren)\s+)*(?:(?:Vor\w*|Mammo[gG]ra(?:ph|f)ie\w*|Untersuchung\w*|Aufnahme\w*|Befund\w*)\s*)?"
    r"(?:(?:vom|von|aus(?:\s+dem\s+Jahre?)?|im(?:\s+Jahre?)?|am)\s+)?"
    r"\(?\s*" + _DATUM_ALT + r"(?:\s*(?:und|,|bzw\.?|sowie)\s*" + _DATUM_ALT + r")*(?:\s*\))?", re.I)


def ist_unveraendert(text, maske_def):
    """Ist das Diktat eines Felds nur „unverändert“ (oder eine Variante aus masken.json)?"""
    n = _norm(text)
    return bool(n) and n in {_norm(p) for p in maske_def.get("unveraendert") or []}


def vergleich(text, datum, maske_def):
    """Vorbefund-Text eines Felds als heutiger Befund „unverändert verglichen mit <Datum>“ (deterministisch, ohne KI).
    1. beginnt mit „Verglichen mit <Datum> …“ → nur das Datum ersetzt; 2. „Verglichen mit der Voruntersuchung …“ (ohne
    Datum) → „Verglichen mit <Datum> …“; 3. „Kein/Keine …“ → „Verglichen mit <Datum> weiterhin keine …“; 4. beginnt mit
    einem Eigenschaftswort aus masken.json → „Verglichen mit <Datum> unverändert <klein> …“; 5. sonst
    „Verglichen mit <Datum> unverändert. <Text>“. 3.15.3: Steht die alte Angabe anders im Kopf („Voruntersuchung
    (12.03.2022)“, „von 2022“, „vom März 2022“, zwei Daten), wird der ganze Kopf „Verglichen mit <Datum>“ — nie zwei Daten."""
    t = " ".join(str(text or "").split())
    d = datum_kurz(datum)
    if not t:
        return ""
    if not d:
        return satz(t)
    m = _VERGLEICH_DATUM.match(t)
    k = _VERGLEICH_KOPF.match(t)
    if k and (not m or k.end() > m.end()):           # 3.15.3: alte Angabe weiter hinten → der ganze Kopf wird neu
        rest = t[k.end():].lstrip()
        return satz(f"Verglichen mit {d}" + ("" if not rest or rest[0] in ".,;:" else " ") + rest)
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


_VORUNT_IM_TEXT = re.compile(r"\b(?:zur|zum|zu\s+der|mit\s+der|mit\s+dem|der|dem)\s+(?:letzten\s+|vorigen\s+)?"
                             r"(?:Vor(?:untersuchung|befund|mammo[gG]ra(?:ph|f)ie|aufnahme)\w*)\b(?!\s*(?:vom|von|\(|\d))", re.I)
_DATUM_IM_TEXT = re.compile(_DATUM_ALT)


def vergleich_diktat(text, datum, maske_def):
    """v3.16.7 (Peter 19.10.): heute NEU diktierter Text eines Vergleichs-Felds (Mammographie/Sonographie) bekommt das
    Datum der Voruntersuchung — sonst stand es nur bei „unverändert“/Übernehmen im Befund. Nie „unverändert“ dazu (das
    sagt nur Peters Diktat). 1. kein Datum bekannt / schon ein Datum im Diktat → wie diktiert; 2. „Verglichen mit der
    Voruntersuchung …“ (ohne Datum) → „Verglichen mit <Datum> …“; 3. „… zur Voruntersuchung …“ im Satz → „… zur
    Voruntersuchung vom <Datum> …“; 4. sonst vorn „Verglichen mit <Datum>“ (Eigenschaftswort/kein/unverändert klein
    weiter, sonst mit Doppelpunkt)."""
    t = " ".join(str(text or "").split())
    d = datum_kurz(datum)
    if not t or not d:
        return satz(t) if t else ""
    if _DATUM_IM_TEXT.search(t) and not _PLATZHALTER.match(t):
        return satz(t)                      # Peter hat ein Datum diktiert → seines gilt
    m = _PLATZHALTER.match(t)
    if m:
        return satz(f"Verglichen mit {d} " + t[m.end():].lstrip()) if t[m.end():].strip() else satz(f"Verglichen mit {d}")
    m = _VERGLEICH_OHNE.match(t)
    if m:
        return satz(f"Verglichen mit {d}" + t[m.end():])
    m = _VORUNT_IM_TEXT.search(t)
    if m:
        return satz(t[:m.end()] + f" vom {d}" + t[m.end():])
    erstes = _norm(t.split(" ", 1)[0])
    klein = {_norm(w) for w in ((maske_def.get("vergleich") or {}).get("klein_anfang") or [])
             + ((maske_def.get("vergleich") or {}).get("diktat_klein_anfang") or [])}
    if any(erstes == w or (erstes.startswith(w) and len(erstes) - len(w) <= 3) for w in klein):
        return satz(f"Verglichen mit {d} {_klein_anfang(t)}")
    return satz(f"Verglichen mit {d}: {t}")


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
class Abschnitt:
    """v3.15.4: Diktat-Abschnitt eines Felds, solange die Spracherkennung läuft. art: „ersetzen“ (erstes Diktat ersetzt
    Vorschlag/Übernommenes/Getipptes), „anhaengen“ (Nachdiktat), „ziel“ (markierter Text bzw. Cursor-Stelle: von/bis im
    beim Abschnittsbeginn angezeigten Text basis)."""
    nr: int
    art: str
    von: int = 0
    bis: int = 0
    basis: str = ""
    text: Optional[str] = None               # None = Spracherkennung läuft


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
    teile: List[Optional[str]] = field(default_factory=list)   # erkannte Diktat-Abschnitte (Peters Wörter)
    sitzung: int = 0                        # steigt, wenn das Feld geleert wird (späte Erkennung alter Abschnitte verfällt)
    text: str = ""                          # übernommener / getippter Text (bei DIKTAT: Ergebnis der Verarbeitung)
    werte: Dict[str, str] = field(default_factory=dict)        # heutige Werte (übernommen/getippt/diktiert)
    verarbeitet: Dict[str, tuple] = field(default_factory=dict)  # Rohtext → (Text, Werte, Hinweis): je Diktat nur einmal KI
    laufend: List[Abschnitt] = field(default_factory=list)     # v3.15.4: Abschnitte, deren Erkennung noch läuft
    cursor: Optional[int] = None            # v3.15.4: Cursor-Stelle nach dem Einfügen (für die Anzeige, einmalig)

    @property
    def roh(self):
        return " ".join(t.strip() for t in self.teile if t and t.strip())

    @property
    def wartet(self):
        return bool(self.laufend)

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
        self.gross_satzanfang = True            # v3.15.4: Einfügen an der Cursor-Stelle (Menü „Satzanfang groß“)
        self._abschnitt_nr = 0
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
        f.teile, f.text, f.werte, f.verarbeitet, f.laufend, f.cursor = [], "", {}, {}, [], None
        f.sitzung += 1

    # Übernehmen / Diktat / Tippen ─────────────────────────────────────────────
    def uebernehmen(self, i=None, taste="F3"):
        """Vorschlag des Felds bewusst übernehmen (Vorbefund: mit Vergleichsdatum, wie „unverändert“). Noch einmal = wieder
        Vorschlag. → Meldung für die Hilfezeile (taste = Name der Taste des Geräts, z. B. „Play“ am Ambient)."""
        f = self.felder[self.aktiv if i is None else i]
        if f.quelle == UEBERNOMMEN:
            self._leeren(f)
            f.quelle = f.vorschlag_art or LEER
            self._geaendert()
            return f"{f.label}: wieder Vorschlag (nicht übernommen)"
        if f.quelle not in VORSCHLAG:
            if f.quelle in (DIKTAT, GETIPPT):
                return f"{f.label}: heute {'diktiert' if f.quelle == DIKTAT else 'getippt'} – {taste} noch einmal = verwerfen"
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

    def reservieren(self, i=None, ziel=None):
        """Diktat-Abschnitt für das Feld anmelden (Spracherkennung läuft). Der Stand des Felds ändert sich erst, wenn
        Text erkannt ist — Stille beim Durchspringen ändert nichts. v3.15.4: ziel = (von, bis) im angezeigten Feldtext
        (Markierung bzw. Cursor-Stelle) → das Diktat ersetzt genau diese Stelle; nur, solange im Feld nichts mehr
        erkannt wird (sonst Nachdiktat wie bisher). → (Feld-Index, Sitzung, Abschnitt-Nr.)."""
        k = self.aktiv if i is None else i
        f = self.felder[k]
        self._abschnitt_nr += 1
        if ziel is not None and not f.laufend:
            basis = vorschau(f, self)
            von, bis = sorted(max(0, min(int(x), len(basis))) for x in ziel)
            a = Abschnitt(self._abschnitt_nr, "ziel", von, bis, basis)
        else:
            a = Abschnitt(self._abschnitt_nr, "anhaengen" if (f.laufend or f.quelle == DIKTAT) else "ersetzen")
        f.laufend.append(a)
        return k, f.sitzung, a.nr

    def diktat_fertig(self, k, sitzung, nr, text):
        """Erkannter Text eines Abschnitts. Die Abschnitte eines Felds wirken in ihrer Reihenfolge (ein später erkannter
        früherer Abschnitt wartet nicht hinten an). Das erste Wort ersetzt Vorschlag/Übernommenes/Getipptes (Diktat
        gewinnt); weitere Abschnitte im selben Feld hängen an (Nachdiktat); ein Abschnitt mit Ziel ersetzt die Markierung
        bzw. fügt an der Cursor-Stelle ein. Leer (Stille) → nichts ändert sich. → False, wenn der Abschnitt verfallen
        ist (Feld inzwischen geleert, übernommen oder getippt)."""
        f = self.felder[k]
        a = next((x for x in f.laufend if x.nr == nr), None) if sitzung == f.sitzung else None
        if a is None:
            return False
        a.text = (text or "").strip()
        while f.laufend and f.laufend[0].text is not None:
            self._anwenden(f, f.laufend.pop(0))
        self._geaendert()
        return True

    def _anwenden(self, f, a):
        t = a.text
        if not t:
            return
        f.sichtbar = True                           # diktiert = gewollt (auch ein eingeklapptes Sono-Feld)
        art = a.art
        if art == "ziel":
            if vorschau(f, self) != a.basis:       # Feld inzwischen anders (z. B. Vorbefund nachgekommen) → anhängen
                art = "anhaengen"
            elif not a.basis.strip():
                art = "ersetzen"
            elif a.von <= 0 and a.bis >= len(a.basis.rstrip()):
                art = "alles"                       # ganzer Text markiert = neues Diktat (heutige Werte bleiben)
        heutige = self._heutige_werte(f, a.basis if a.art == "ziel" else None)
        if art == "ziel":
            if a.basis[a.von:a.bis].rstrip().endswith((".", "!", "?")) and not t.rstrip().endswith((".", "!", "?", ":")):
                t = t.rstrip() + "."                # markierter Satz samt Punkt ersetzt → der Punkt bleibt
            neu, cursor = _einf.einfuegen(a.basis, a.von, a.bis, t, gross=self.gross_satzanfang)
            if f.quelle == DIKTAT and not _zeigt_vorbefund(f, self):
                f.teile, f.verarbeitet = [_mit_werten(neu, heutige, f)], {}    # nur Peters Wörter → bleibt Diktat (KI)
            else:                                   # Vorbefund/Normalbaustein/Getipptes steht mit drin → getippt, ohne KI
                f.text, f.werte, f.quelle, f.teile, f.verarbeitet = neu, heutige, GETIPPT, [], {}
            f.cursor = cursor
            return
        if art == "anhaengen" and f.quelle == DIKTAT:
            f.teile.append(t)
            f.verarbeitet = {}
            return
        if art == "anhaengen" and f.quelle == GETIPPT and f.text.strip():
            f.text = f.text.rstrip() + " " + t      # nach dem Einfügen weiterdiktiert
            return
        f.text, f.werte, f.verarbeitet = "", {}, {}
        f.teile = [_mit_werten(t, heutige, f) if art == "alles" else t]
        f.quelle = DIKTAT

    def _heutige_werte(self, f, angezeigt=None):
        """ACR/BI-RADS, die das Feld heute schon trägt (diktiert, getippt, übernommen) und die NICHT im Textfeld stehen
        (nur unter dem Feld) — die bleiben beim Ändern des Texts. Was im Text steht, ändert der Text selbst (markiert und
        ersetzt bzw. gelöscht = weg). Vorschlag-Werte zählen nie (nichts still übernehmen)."""
        if f.quelle in VORSCHLAG + (LEER,):
            return {}
        sichtbar = werte_aus_text(vorschau(f, self) if angezeigt is None else angezeigt)[1]
        return {k: v for k, v in werte_vorschau(f, self).items() if k not in sichtbar}

    def tippen(self, i, text):
        """Von Hand im Feld geändert → getippt (wie geschrieben, ohne KI). Unverändert gegenüber der Anzeige → nichts.
        v3.15.4: heute diktierte/übernommene ACR/BI-RADS bleiben (sie stehen nicht im Textfeld); ganz gelöscht → leer
        (stand ein Vorschlag da: „gelöscht“, kommt nicht in den Befund; ✕ verwerfen holt ihn zurück)."""
        f = self.felder[i]
        t = (text or "").strip()
        if t == vorschau(f, self).strip():
            return False
        heutige = self._heutige_werte(f)
        self._leeren(f)
        # wie getippt stehen lassen (auch „ACR: 1“-Zeilen im Ergebnis — die Werte liest erst der Befund heraus)
        f.text, f.quelle, f.sichtbar = t, (GETIPPT if (t or f.vorschlag_art) else LEER), True
        f.werte = heutige if f.quelle == GETIPPT else {}
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
        return any(f.quelle in (DIKTAT, UEBERNOMMEN) or (f.quelle == GETIPPT and f.text.strip()) for f in self.felder)

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


def _zeigt_vorbefund(f, maske):
    """Zeigt ein diktiertes Feld den Vorbefund („unverändert“ → Vergleichssatz)? Dann ist ein Einfügen darin kein reines
    Diktat mehr (der Vorbefund ginge sonst an die KI)."""
    t = werte_aus_text(f.roh)[0] if f.typ == "ergebnis" else f.roh
    return ist_unveraendert(t, maske.definition) and f.vorschlag_art == VORBEFUND and bool(f.vorschlag.strip())


def _mit_werten(text, werte, f):
    """Ergebnis-Feld: heutige ACR/BI-RADS, die nicht im Text stehen (sie stehen unter dem Feld), als Diktat-Wörter
    anhängen — sonst gingen sie beim Ersetzen des Texts verloren. Neu diktierte Werte gehen vor."""
    if f.typ != "ergebnis" or not werte:
        return text
    da = werte_aus_text(text)[1]
    fehlt = [f"{_WERT_KURZ[k]} {v}" for k, v in werte.items() if k in _WERT_KURZ and v and k not in da]
    return (text.rstrip() + " " + " ".join(fehlt)).strip() if fehlt else text


_WERT_KURZ = {"acr": "ACR", "birads": "BIRADS"}


def laufend_ziel(f):
    """Der Abschnitt mit Ziel (Markierung/Cursor), dessen Erkennung noch läuft — für die Live-Anzeige an der Stelle."""
    return f.laufend[0] if f.laufend and f.laufend[0].art == "ziel" else None


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
        w = dict(f.werte)                       # v3.15.4: heutige Werte bleiben, getippte gehen vor
        w.update(werte_aus_text(f.text)[1])
        return w
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
        if f.vergleich and maske.vorbefund and maske.datum:     # v3.16.7: Voruntersuchungs-Datum auch bei neuem Diktat
            text = vergleich_diktat(text, maske.datum, maske.definition)
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
            if f.typ == "ergebnis":
                w = {**f.werte, **w}            # v3.15.4: heutige Werte bleiben, getippte gehen vor
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
    # v3.16.7 (Peter 19.10.): heute nicht genannte ACR/BI-RADS kommen aus dem Vorbefund (Doppelbefundung final vor dem
    # Brieftext) — sichtbar als Hinweis. Nicht, wenn das Ergebnis-Feld bewusst geleert wurde.
    erg_f = next((f for f in maske.felder if f.typ == "ergebnis"), None)
    if erg_f is not None and maske.vorbefund and not (erg_f.quelle == GETIPPT and not erg_f.text.strip()):
        aus_vb = [a for a in ("acr", "birads") if not werte.get(a) and erg_f.vorschlag_werte.get(a)]
        for a in aus_vb:
            werte[a] = erg_f.vorschlag_werte[a]
        if aus_vb:
            labs = [(d.get("werte") or {}).get(a, {}).get("label") or _WERT_LABEL[a] for a in aus_vb]
            b.hinweise.append(" und ".join(labs) + f" aus dem Vorbefund{(' vom ' + maske.datum) if maske.datum else ''}"
                              " übernommen – bitte prüfen")
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


def offene_meldung(maske, taste="F3"):
    """Warnung vor INS: welche Felder noch Vorbefund-/Vorschlag-Stand haben (nichts wird still übernommen). taste = Name
    der Übernehmen-Taste des Geräts (Ambient: „Play“)."""
    offen = maske.offene()
    if not offen:
        return ""
    namen = ", ".join(f.label + (" (Vorbefund)" if f.vorschlag_art == VORBEFUND else " (Normalbaustein)") for f in offen)
    return (f"Noch nicht übernommen: {namen} – {taste} übernimmt · Record diktiert neu · INS noch einmal = ohne diese "
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
        return "optional (keine Sono-Leistung in CAS)" if f.nur_mit_sono else "eingeklappt"
    if f.quelle == GETIPPT and not f.text.strip():
        return "gelöscht – kommt nicht in den Befund"
    return {VORBEFUND: f"Vorbefund {datum}".strip(), VORLAGE: "Normalbaustein (Vorschlag)", UEBERNOMMEN: "✓ übernommen",
            DIKTAT: "… erkennt" if f.wartet else "diktiert", GETIPPT: "getippt", LEER: "leer"}.get(f.quelle, f.quelle)
