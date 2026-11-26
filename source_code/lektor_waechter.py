"""Deterministischer Diff-Wächter für Lektor-Korrekturen (kaiscribe-lektor-messlauf-n1, 24.11.2026). NUR MESSUNG.

Der Lektor liefert Korrekturen als [{"alt": exakter Ausschnitt, "neu": Ersatz}]. Jede Korrektur wird einzeln geprüft und
nur übernommen, wenn sich NICHTS davon ändert: Seiten/Lage, Zahlen/Maße/Einheiten, Verneinungen, Normal-Aussagen,
Graduierungen/Unsicherheit, Platzhalter, Überschriften, Regel-Register-Wortlaute. Zusätzlich darf eine Korrektur nur
Schreibweise/Grammatik sein: jedes Inhaltswort im Ersatz braucht ein ähnliches Wort im Original (und umgekehrt), neu
dürfen nur Funktionswörter (Artikel, ist/sind, Präpositionen) hinzukommen. Nur Standardbibliothek.
"""
from __future__ import annotations

import collections
import difflib
import json
import re
import unicodedata

WORT = re.compile(r"[\wÄÖÜäöüß]+(?:[-'’&/][\wÄÖÜäöüß]+)*|[^\s\w]")
ROEMISCH = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12}
SEITE = (("links", ("link", "li")), ("rechts", ("recht", "re")), ("beidseits", ("beid", "bds", "bilateral")),
         ("medial", ("medial",)), ("lateral", ("lateral",)), ("ventral", ("ventral",)), ("dorsal", ("dorsal",)),
         ("proximal", ("proximal",)), ("distal", ("distal",)), ("kranial", ("kranial", "cranial")),
         ("kaudal", ("kaudal", "caudal")), ("ulnar", ("ulnar",)), ("radial", ("radial",)),
         ("oben", ("ober", "oben")), ("unten", ("unter", "unten")), ("innen", ("innen",)), ("aussen", ("außen", "aussen")))
NEGATION = (("kein", ("kein",)), ("nicht", ("nicht",)), ("ohne", ("ohne",)), ("weder", ("weder",)), ("nie", ("nie",)),
            ("frei", ("frei",)))
NORMAL = (("unauffällig", ("unauffällig", "unauffaellig")), ("regelrecht", ("regelrecht",)), ("normal", ("normal",)),
          ("altersentsprechend", ("altersentsprech", "altersgemäß")), ("intakt", ("intakt",)),
          ("physiologisch", ("physiologisch",)), ("regulär", ("regulär",)), ("unverändert", ("unveränder",)),
          ("stationär", ("stationär",)))
GRAD = (("gering", ("gering",)), ("leicht", ("leicht",)), ("mäßig", ("mäßig", "massig", "mässig")),
        ("mittel", ("mittel",)), ("hochgradig", ("hochgrad",)), ("ausgeprägt", ("ausgeprägt", "ausgepraegt")),
        ("deutlich", ("deutlich",)), ("diskret", ("diskret",)), ("beginnend", ("beginn",)),
        ("fortgeschritten", ("fortgeschritt",)), ("minimal", ("minimal",)), ("massiv", ("massiv",)),
        ("schwer", ("schwer",)), ("grad", ("grad",)), ("fraglich", ("fraglich",)), ("verdacht", ("verdacht", "v.a")),
        ("dd", ("dd",)), ("wahrscheinlich", ("wahrscheinlich",)), ("möglich", ("möglich",)),
        ("vereinbar", ("vereinbar",)), ("kompatibel", ("kompatib",)), ("klein", ("klein",)), ("groß", ("groß", "gross")),
        ("stark", ("stark",)), ("angedeutet", ("angedeut",)), ("dezent", ("dezent",)), ("birads", ("bi-rads", "birads")),
        ("kellgren", ("kellgren", "k&l")), ("tossy", ("tossy",)), ("acr", ("acr",)), ("stadium", ("stadi",)),
        ("typ", ("typ",)), ("akut", ("akut",)), ("frisch", ("frisch",)), ("alt", ("alte", "älter", "veraltet")))
EINHEIT = {"mm", "cm", "m", "ml", "°", "%", "kg", "g", "kv", "mgy", "msv", "hu"}
# Dürfen als Grammatik-Korrektur neu hinzukommen oder wegfallen (Artikel, Hilfsverb, Präposition, Bindewort)
FUNKTION = set("""der die das den dem des ein eine einer eines einem einen ist sind wird werden war waren zeigt zeigen
zeigt sich es sich und sowie mit im in am an zur zum von vom bei auf aus als zu um""".split())
TITEL = re.compile(r"^\s*#{1,6}\s")


def _nfc(t):
    return unicodedata.normalize("NFC", t or "").replace(" ", " ")


def woerter(t):
    return [w for w in WORT.findall(_nfc(t)) if re.search(r"\w", w)]


def _klasse(tok):
    """Schutz-Schlüssel eines Wortes oder None."""
    if tok in ROEMISCH and len(tok) > 1 or tok in ("III", "IV", "VI", "II"):
        return ("zahl", str(ROEMISCH[tok]))
    if re.search(r"\d", tok):
        return ("zahl", re.sub(r"[^\d,.]", "", tok).replace(",", ".").strip("."))
    w = tok.lower()
    if w in EINHEIT:
        return ("einheit", w)
    for art, liste in (("seite", SEITE), ("neg", NEGATION), ("norm", NORMAL), ("grad", GRAD)):
        for name, staemme in liste:
            for s in staemme:
                kurz = len(s) <= 3
                if (w == s) if kurz else (w.startswith(s) or (art == "norm" and s in w) or (art == "grad" and s in w
                                                                                              and len(s) >= 6)):
                    return (art, name)
    return None


def schutz(t):
    return collections.Counter(k for k in (_klasse(w) for w in woerter(t)) if k)


def _norm_wort(w):
    w = w.lower().replace("c", "k").replace("z", "k").replace("ph", "f").replace("ae", "ä").replace("-", "")
    return w


def _aehnlich(a, b):
    a, b = _norm_wort(a), _norm_wort(b)
    if a == b or a.startswith(b) or b.startswith(a):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.6


def _inhalt(ws):
    return [w for w in ws if w.lower() not in FUNKTION and _klasse(w) is None]


def register_saetze(pfad):
    """Prüfwortlaute aus tests/regel_register/regeln.json: zitierte Sätze (≥ 15 Zeichen) → Liste."""
    with open(pfad, encoding="utf-8") as f:
        d = json.load(f)
    out = set()
    for r in d.get("regeln", []):
        for liste in (r.get("pruefwort") or {}).values():
            for s in liste:
                for m in re.finditer(r"[\"“„']([^\"“”„']{15,})[\"”']", s):
                    w = _nfc(m.group(1)).strip()
                    # nur Wortlaute (≥ 15 Zeichen, ≥ 3 Wörter), keine Code-Schnipsel aus .py/.ts-Prüfwörtern
                    if len(w) >= 15 and len(w.split()) >= 3 and not re.search(r"[\[\]=(){};]|\\", w):
                        out.add(w)
    return sorted(out)


def _muster(alt):
    return re.compile(r"(?<![\wÄÖÜäöüß])" + re.escape(alt) + r"(?![\wÄÖÜäöüß])")


def _fundstellen(text, alt):
    return [m.start() for m in _muster(alt).finditer(text)]


def satz_um(text, pos, laenge):
    """Satz (bis . ! ? oder Zeilenende) rund um text[pos:pos+laenge]."""
    a = pos
    while a > 0 and text[a - 1] not in "\n" and not (text[a - 1] == " " and a >= 2 and text[a - 2] in ".!?"):
        a -= 1
    b = pos + laenge
    while b < len(text) and text[b] != "\n" and not (text[b] in ".!?" and (b + 1 >= len(text) or text[b + 1] in " \n")):
        b += 1
    return text[a:b + 1].strip()


def pruefen_eine(text, alt, neu, register=(), vorlagen=None):
    """→ (ok, grund). text = aktueller Befund (Markdown)."""
    alt, neu = _nfc(alt), _nfc(neu)
    if not alt or alt == neu:
        return False, "leer/gleich"
    n = len(_fundstellen(text, alt))
    if n == 0:
        return False, "nicht gefunden"
    if n > 1 and len(woerter(alt)) < 2 and len(alt) < 6:
        return False, "mehrdeutig"
    if "⟦" in alt + neu or "⟧" in alt + neu:
        return False, "Platzhalter"
    if len(alt) > 120 or len(woerter(alt)) > 12:
        return False, "zu lang"
    for zeile in text.splitlines():
        if alt in zeile and TITEL.match(zeile):
            return False, "Überschrift"
    if "\n" in alt or "\n" in neu:
        return False, "Absatz"
    if schutz(alt) != schutz(neu):
        return False, "Schutzwort (Seite/Zahl/Negation/Normal/Grad)"
    wa, wn = _inhalt(woerter(alt)), _inhalt(woerter(neu))
    for w in wn:
        if not any(_aehnlich(w, x) for x in wa):
            return False, "neues Inhaltswort"
    for w in wa:
        if not any(_aehnlich(w, x) for x in wn):
            return False, "Inhaltswort entfernt"
    if abs(len(wa) - len(wn)) > 1:
        return False, "Wortzahl"
    pos = _fundstellen(text, alt)
    for s in register:
        for m in re.finditer(re.escape(s), text):
            if any(p < m.end() and p + len(alt) > m.start() for p in pos):
                return False, "Regel-Register-Wortlaut"
    if vorlagen:
        for p in pos:
            if " ".join(satz_um(text, p, len(alt)).lower().split()) in vorlagen:
                return False, "Vorlagensatz"
    return True, "ok"


def anwenden(text, korrekturen, register=(), vorlagen=None):
    """→ (neuer_text, [(korrektur, ok, grund)]). Jede Korrektur einzeln; außerhalb von Überschriften überall ersetzt."""
    text = _nfc(text)
    protokoll = []
    for k in korrekturen or []:
        alt, neu = str(k.get("alt") or ""), str(k.get("neu") or "")
        ok, grund = pruefen_eine(text, alt, neu, register, vorlagen)
        if ok:
            alt, neu = _nfc(alt), _nfc(neu)
            m = _muster(alt)
            text = "\n".join(z if TITEL.match(z) else m.sub(lambda _x: neu, z) for z in text.split("\n"))
        protokoll.append((k, ok, grund))
    return text, protokoll
