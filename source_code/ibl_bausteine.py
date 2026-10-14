"""IB-Lab-Vorbefund-Bausteine im CAS-Diktat (v3.13.0) — reine Funktionen, ohne Tk/Windows testbar.

Peter 13.10.2026: „Ginge es, dass RaKScribe beim Öffnen gleich eventuell vorhandene Bausteine von IBL holt?“
Die RaKScribe-Brücke (ab 1.2.0) reicht zum offenen CAS-Auftrag die KI-Messwerte der Untersuchung nach (cas_auftrag.py:
cas_ibl_<id>.json; je Baustein Modul, Version, Seite(n), Ziffer der Leistung im CAS-Eintrag, Befundzeilen, Ergebnispunkte,
Hinweise). Sie kommen beim Start oder später (wenige Minuten nach der Aufnahme); eine neue Fassung ersetzt die alte.
Leitplanke: Messwerte 1:1, nie von der KI umformulieren. Darum:
  - Einsetzen NACH der KI, deterministisch: Befundzeilen ans Ende des Befundtexts der passenden Untersuchung,
    Ergebnispunkte an ihre Ergebnisliste (neu durchgezählt). Zuordnung: Ziffer der Leistung ↔ CAS-Leistung, sonst
    Modul ↔ Region (FROG → Fuß, LAMA → Ganzbein, HIPPO → Becken/Hüfte, KOALA → Knie, PANDA → Hand, SQUIRREL →
    Wirbelsäule), bei mehreren die Seite; mehrdeutig → eigener Absatz am Ende + Hinweis.
  - Doppelungen: nennt der Befund bzw. das Diktat dieselbe Messgröße mit demselben Wert oder dieselbe Diagnose
    („Pes planus“) → nicht doppelt, Hinweis. Im Zweifel (nur ein verwandtes Wort, Messgröße ohne Zahl) anhängen und
    im Hinweis markieren.
  - Widerspruch Diktat ↔ Messwert (andere Zahl; Ergebnis unauffällig, IB Lab auffällig; Befundsatz „Fußgewölbe
    regulär“ neben einer IB-Lab-Diagnose) → sichtbarer Hinweis, am diktierten Text wird nichts geändert.
  - Gate: jede eingesetzte Zeile steht danach wörtlich im Befund, jede Zahl daraus 1:1.
  - Gen-Prompt nur informiert (<ibl_messwerte>: welche Messgrößen ergänzt werden – nicht selbst nennen, keine Zahlen
    erfinden, nicht widersprechen; Diktiertes wie diktiert).
  - Hinweise des Bausteins (Bildqualität, Fraktur-Verdacht, Entwürfe) und nicht zugeordnete Messgrößen: NUR Anzeige.
Ohne Bausteine (keine Datei, ältere Brücke, Menü „IB-Lab-Bausteine übernehmen“ aus) wird nichts hiervon benutzt — Prompt
und Befund bleiben bit-gleich. Keine Praxisdaten hier (öffentliches Repo): nur Modulnamen und allgemeine Anatomie.
Tests: tests/offline/test_ibl_bausteine.py
"""
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

import befund_regeln as br
import cas_vorlagen as cv

# Modul → Regionen der passenden Untersuchung (None = jede). Modulnamen = öffentliche Produktnamen, Regionen wie
# cas_vorlagen.REGIONEN.
MODULE = {"frog": {"fuss"}, "lama": {"unterschenkel"}, "hippo": {"becken", "huefte"}, "koala": {"knie"},
          "squirrel": {"hws", "bws", "lws"}, "panda": {"hand"}, "rho": None, "rbfracture": None}
# Diagnose (Wörter im Ergebnispunkt) → Wörter, mit denen ein Befundsatz dieselbe Eigenschaft als normal beschreibt
# („Das Fußgewölbe ist regulär …“ neben „Pes planus“) — nur für den Hinweis, nie wird Text geändert.
BEZUG = [
    (("pes planus", "pes cavus", "längsgewölbe"), ("fußgewölbe", "längsgewölbe")),
    (("hallux valgus", "intermetatarsalwinkel", "metatarsus"), ("gelenkwinkel",)),
    (("genu varum", "genu valgum"), ("achse", "beinachse")),
    (("beinlängendifferenz",), ("beinlänge",)),
    (("überdachung", "hüftdysplasie", "pfannendach"), ("überdachung", "deckung", "pfannendach", "pfannendäch")),
    (("coxa vara", "coxa valga"), ("ccd winkel",)),
    (("gonarthrose",), ("gelenkspalt", "arthrose")),
    (("skolio", "krümmung"), ("skoliose", "krümmung")),
    (("knochenalter",), ("knochenalter", "skelettalter")),
]
# Themen der Vorlagen-Sätze, die die Messwerte eines Moduls ersetzen (nur für den Gen-Prompt)
THEMEN = {"frog": "Fußgewölbe und Gelenkwinkel des Fußes", "lama": "Beinachse (anatomische/mechanische Achse) und Beinlänge",
          "hippo": "Überdachung der Hüftköpfe, Pfannendach, CCD-Winkel und Beinlängendifferenz",
          "koala": "Gelenkspalt und Arthrosegrad des Kniegelenks", "squirrel": "Krümmung und Stellung der Wirbelsäule",
          "panda": "Knochenalter"}
_SEITE_WORT = re.compile(r"(?<![a-zäöüß])(recht|link)(?:s|e|en|er|es)?(?![a-zäöüß])", re.I)
# Verwandte Wörter einer Diagnose (allgemeiner Sprachgebrauch): steht nur so ein Wort schon im Befund → anhängen + Hinweis
VERWANDT = [
    ("pes planus", "plattfuß", "plattfuss", "senkfuß", "senkfuss", "pes planovalgus", "längsgewölbe"),
    ("pes cavus", "hohlfuß", "hohlfuss"),
    ("hallux valgus", "ballenzeh"),
    ("metatarsus primus varus", "intermetatarsalwinkel", "spreizfuß", "spreizfuss"),
    ("hüftdysplasie", "dysplasie", "überdachung", "pfannendach"),
    ("coxa vara", "coxa valga", "ccd winkel"),
    ("gonarthrose", "arthrose", "kellgren"),
    ("genu varum", "varus", "varisch", "o bein"),
    ("genu valgum", "valgus", "valgisch", "x bein"),
    ("beinlängendifferenz", "beinlängenunterschied", "beinverkürzung"),
    ("knochenalter", "skelettalter"),
    ("skolio", "krümmung"),
    ("knochendichte", "osteopenie", "osteoporose", "knochendichtescreening"),
]
_GRAD = re.compile(r"\b(?:gering|leicht|mittel|mäßig|maessig|hoch|höchst|schwer|stark)(?:\s*bis\s*\w+)?"
                   r"(?:gradig|gradige|gradiger|gradiges|gradigen|e|er|es|en)?\b")
_SEITE = re.compile(r"(?<![a-zäöüß])(rechts|links|beidseits|beidseitig|bds)(?![a-zäöüß])", re.I)
_NORMAL = re.compile(r"regelrecht|regulär|\bnorm|ordnungsgemäß|unauffällig|\bkeine?\b|\bgut(?:e[rnms]?)?\b|kongruent|"
                     r"im normbereich", re.I)
_NEG_VOR = re.compile(r"\b(?:kein\w*|ohne|nicht|ausschluss|frei von)\b")
_NEG_NACH = re.compile(r"\b(?:nicht nachweisbar|nicht vorhanden|regelrecht\w*|regulär\w*|unauffällig\w*|normal\w*|"
                       r"ordnungsgemäß\w*|im normbereich)\b")
_NUM = re.compile(r"^\s*\d+\s*[.)]\s*")
_WERT = re.compile(r"(?P<zahl>[+\-−]?\d+(?:[.,]\d+)?)\s*(?P<einheit>°|mm|cm|m|%|Jahre|Monate|SD)?(?P<von>\s+von\s+\d+)?\s*$")
_ZAHL_TEXT = re.compile(r"([+\-−]?\d+(?:[.,]\d+)?)\s*(°|grad|mm|millimeter|cm|zentimeter|%|prozent)?", re.I)
_SATZENDE = re.compile(r"\.(?=\s|$)|[;!?\n]")
_MM = {"mm": Decimal(1), "millimeter": Decimal(1), "cm": Decimal(10), "zentimeter": Decimal(10), "m": Decimal(1000)}
ENDE = "Ende"


def _norm(t):
    """Vergleichsform: klein, Bindestriche = Leerzeichen, Leerraum zusammengefasst."""
    return re.sub(r"\s+", " ", (t or "").lower().replace("-", " ").replace("‐", " ")).strip()


def _zahl(text):
    try:
        return Decimal(str(text).replace("−", "-").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


# ───────────────────────────── Bausteine aus der Datei der Brücke ─────────────────────────────
@dataclass
class Baustein:
    accno: str
    modul: str                     # frog | lama | … (Schlüssel des Abholers)
    name: str                      # FROG | Rho | …
    version: int
    ziffer: int = 0                # Reihenfolge der Leistung im CAS-Eintrag (0 = unbekannt)
    seiten: List[str] = field(default_factory=list)
    befundteil: List[str] = field(default_factory=list)
    ergebnis: List[str] = field(default_factory=list)
    hinweise: List[str] = field(default_factory=list)
    nicht_zugeordnet: List[str] = field(default_factory=list)
    modul_name: str = ""
    aktualisiert: str = ""

    @property
    def schluessel(self):
        return (self.accno, self.modul)

    @property
    def stand(self):
        return (self.accno, self.modul, self.version, self.aktualisiert)

    @property
    def label(self):
        """„FROG rechts“, „FROG beidseits“, „LAMA“ — für Band und Hinweise."""
        s = set(self.seiten)
        seite = "beidseits" if {"rechts", "links"} <= s else (self.seiten[0] if len(self.seiten) == 1 else "")
        return f"{self.name} {seite}".strip()

    @property
    def regionen(self):
        return MODULE.get(self.modul)


def _texte(x):
    return [s.strip() for s in x if isinstance(s, str) and s.strip()] if isinstance(x, list) else []


def aus_liste(liste):
    """Bausteine aus cas_ibl_<id>.json (Liste von dicts) → [Baustein] — Ungültiges wird still übergangen."""
    out = []
    for d in liste or []:
        if not isinstance(d, dict):
            continue
        modul = str(d.get("modul") or "").strip().lower()
        accno = str(d.get("accno") or "").strip()
        if not re.fullmatch(r"[a-z0-9]+", modul) or not accno:
            continue
        try:
            version = int(d.get("version") or 0)
        except (TypeError, ValueError):
            version = 0
        try:
            ziffer = int(d.get("ziffer"))
        except (TypeError, ValueError):
            ziffer = int(accno[-1]) if accno[-1:].isdigit() else 0
        seiten = [s for s in ("rechts", "links") if s in (d.get("seiten") or [])]
        out.append(Baustein(accno=accno, modul=modul, name=str(d.get("name") or modul.upper()), version=version,
                            ziffer=ziffer, seiten=seiten, befundteil=_texte(d.get("befundteil")),
                            ergebnis=_texte(d.get("ergebnis")), hinweise=_texte(d.get("hinweise")),
                            nicht_zugeordnet=_texte(d.get("nicht_zugeordnet")),
                            modul_name=str(d.get("modul_name") or ""), aktualisiert=str(d.get("aktualisiert") or "")))
    out.sort(key=lambda b: (b.ziffer, b.modul))
    return out


def band_text(bausteine, an=True):
    """„IB Lab: FROG rechts ✓ · LAMA ✓“ (Übernahme aus: ohne Haken, mit Hinweis aufs Menü)."""
    if not bausteine:
        return ""
    if not an:
        return "IB Lab: " + " · ".join(b.label for b in bausteine) + "  (Übernahme aus – Menü)"
    return "IB Lab: " + " · ".join(f"{b.label} ✓" for b in bausteine)


def anzeige_hinweise(bausteine):
    """Hinweise des Abholers (nur Anzeige, nie in den Befund) + Zahl nicht zugeordneter Messgrößen."""
    out = []
    for b in bausteine:
        out += [h if h.lower().startswith((b.name.lower(), (b.modul_name or "-").lower())) else f"{b.name}: {h}"
                for h in b.hinweise]
        if b.nicht_zugeordnet:
            out.append(f"{b.name}: {len(b.nicht_zugeordnet)} Messgröße(n) nicht zugeordnet (Katalog ergänzen)")
    return list(dict.fromkeys(out))


# ───────────────────────────── Messwerte lesen und vergleichen ─────────────────────────────
@dataclass
class Messwert:
    zeile: str
    name: str                      # „Calcaneusneigungswinkel“
    wert: str                      # „10,0°“ (wie im Baustein)
    zahl: Optional[Decimal]
    einheit: str = ""


def messwert(zeile):
    """Befundzeile des Bausteins „<Name>[ Seite] <Wert> (<Quelle>).“ → Messwert; Werte ohne Zahl (Codes) → zahl None."""
    rumpf = re.sub(r"\s*\([^()]*\)\.?\s*$", "", zeile or "").rstrip(" .")
    m = _WERT.search(rumpf)
    if m:
        name, wert = rumpf[:m.start()], rumpf[m.start():].strip()
        zahl, einheit = _zahl(m.group("zahl")), (m.group("einheit") or "")
    else:
        name, _, wert = rumpf.partition(":")
        zahl, einheit = None, ""
    name = _SEITE.sub("", name).strip(" :")
    if not name:
        return None
    return Messwert(zeile, name, wert.strip(), zahl, einheit)


def _gleich(zahl_a, einheit_a, zahl_b, einheit_b):
    a, b = _MM.get((einheit_a or "").lower()), _MM.get((einheit_b or "").lower())
    if a is not None and b is not None:
        return zahl_a * a == zahl_b * b
    return zahl_a == zahl_b


def im_text(mw, text):
    """Kommt die Messgröße im Text vor? → („fehlt“ | „gleich“ | „anders“ | „ohne_zahl“, gefundener Wert)."""
    t, n = _norm(text), _norm(mw.name)
    if len(n) < 3:
        return "fehlt", ""
    funde = []
    for m in re.finditer(r"(?<![a-zäöüß0-9])" + re.escape(n) + r"(?![a-zäöüß])", t):
        rest = _SATZENDE.split(t[m.end():m.end() + 80], 1)[0]
        z = _ZAHL_TEXT.search(rest)
        funde.append((_zahl(z.group(1)), (z.group(2) or "").lower(), z.group(0).strip()) if z else None)
    if not funde:
        return "fehlt", ""
    if mw.zahl is None or all(f is None for f in funde):
        return "ohne_zahl", ""
    for f in funde:
        if f is not None and f[0] is not None and _gleich(f[0], f[1], mw.zahl, mw.einheit):
            return "gleich", f[2]
    return "anders", next(f[2] for f in funde if f is not None)


def diagnose_kern(punkt):
    """„Mittelgradiger Hallux valgus rechts (Hallux-valgus-Winkel 24,3°).“ → „hallux valgus“."""
    t = _norm((punkt or "").split("(")[0])
    t = _SEITE.sub(" ", t)
    t = re.sub(r"\bvon\s+[\d.,]+\s*\S*", " ", t)
    t = _GRAD.sub(" ", t)
    t = re.sub(r"[^a-zäöüß ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _vorkommen(wort, text):
    """Je Vorkommen von wort im Text: „positiv“ oder „verneint“ (kein/ohne/nicht davor, regelrecht/unauffällig danach)."""
    t = _norm(text)
    out = []
    for m in re.finditer(r"(?<![a-zäöüß])" + re.escape(wort), t):
        vor = re.split(r"[.;:\n]", t[max(0, m.start() - 30):m.start()])[-1]
        nach = re.split(r"[,.;:\n]", t[m.end():m.end() + 40], 1)[0]
        neg = _NEG_VOR.search(vor) or _NEG_NACH.search(nach)
        out.append("verneint" if neg else "positiv")
    return out


def _diagnose_im_text(punkt, bericht, diktat):
    """Steht die Diagnose eines Ergebnispunkts schon da? → (Art, Wort):
    doppelt (Kern im Diktat bzw. im KI-Text, nicht verneint) | widerspruch (das Diktat verneint sie, z. B. „kein
    Plattfuß“) | verwandt (nur ein verwandtes Wort, z. B. „Senkfuß“ zu „Pes planus“) | neu."""
    kern = diagnose_kern(punkt)
    if len(kern) >= 4:
        d = _vorkommen(kern, diktat)
        if "positiv" in d:
            return "doppelt", kern
        if d:
            return "widerspruch", kern
        if "positiv" in _vorkommen(kern, bericht):
            return "doppelt", kern
    p = _norm(punkt)
    for gruppe in VERWANDT:
        if not any(w in p for w in gruppe):
            continue
        for w in gruppe:
            d = _vorkommen(w, diktat)
            if "positiv" in d or "positiv" in _vorkommen(w, bericht):
                return "verwandt", w
            if d:
                return "widerspruch", w
    return "neu", ""


def _rho_im_text(text):
    """RaKScribes eigener Rho-Baustein bzw. ein diktierter Rho-Score im Text? → (ja, Score|None)."""
    t = _norm(text)
    if not re.search(r"knochendichtescreening|\(rho\)|\brho\b", t):
        return False, None
    m = re.search(r"score\s+(?:von\s+)?(\d{1,2})\b", t)
    return True, (_zahl(m.group(1)) if m else None)


# ───────────────────────────── Befund in Abschnitte zerlegen ─────────────────────────────
@dataclass
class Abschnitt:
    titel: str
    start: int                     # Zeilenindex der Titelzeile (bzw. erste Zeile)
    ende: int                      # exklusiv
    befund: int = -1               # Zeilenindex „## Befund“
    ergebnis: int = -1             # Zeilenindex „## Ergebnis“
    segment: str = ""              # Diktat-Abschnitt (falls bekannt)

    @property
    def regionen(self):
        return cv.regionen(self.titel)

    @property
    def seite(self):
        s = {x.lower() for x in _SEITE.findall(self.titel)} or {x.lower() for x in _SEITE.findall(self.segment[:60])}
        if s & {"beidseits", "beidseitig", "bds"} or {"rechts", "links"} <= s:
            return "beidseits"
        return next(iter(s), "")


def abschnitte(zeilen):
    """Zeilen eines Befunds → [Abschnitt] je „## Titel“ (mit „## Befund“/„## Ergebnis“ darin)."""
    out = []
    for i, z in enumerate(zeilen):
        st = z.strip()
        if not st.startswith("## "):
            continue
        kopf = st[3:].strip().rstrip(":").lower()
        if kopf in ("befund", "ergebnis"):
            if not out:
                out.append(Abschnitt("", 0, len(zeilen)))
            if kopf == "befund" and out[-1].befund < 0:
                out[-1].befund = i
            elif kopf == "ergebnis" and out[-1].ergebnis < 0:
                out[-1].ergebnis = i
            continue
        if out:
            out[-1].ende = i
        out.append(Abschnitt(st[3:].strip(), i, len(zeilen)))
    return out


def ergebnis_normal(zeilen):
    """Nur Normalaussagen im Ergebnis (z. B. „Regelrechte Darstellung des Fußskeletts.“)?"""
    punkte = [_NUM.sub("", z).strip() for z in zeilen if z.strip()]
    return bool(punkte) and all(_NORMAL.search(p) and not br.has_pathology(p) for p in punkte)


# ───────────────────────────── Zuordnung Baustein → Abschnitt ─────────────────────────────
def _leistung_info(l, templates):
    text = f"{l.get('text') or ''} {cv.vorlagen_text(l.get('vorlage'), templates or {}) if l.get('vorlage') else ''}"
    return cv.regionen(text), (l.get("seite") or "")


def _seite_passt(a, b):
    return not a or not b or a == b or "beidseits" in (a, b)


def _leistung_zur_ziffer(ziffer, liste):
    """v3.14.0: Tragen die CAS-Leistungen ihre Ziffer selbst (Brücke 2.0.0, aus der Datenbank: Accession = Diktatnummer +
    Ziffer), gilt genau diese Leistung; sonst wie bisher die Stelle in der Liste (Kürzelzeile, unbestätigt)."""
    dicts = [x for x in liste or [] if isinstance(x, dict)]
    if any(isinstance(x.get("ziffer"), int) and x.get("ziffer") for x in dicts):
        return next((x for x in dicts if x.get("ziffer") == ziffer), None)
    if 1 <= ziffer <= len(liste or []) and isinstance(liste[ziffer - 1], dict):
        return liste[ziffer - 1]
    return None


def zuordnen(b, teile, cas_leistungen=None, templates=None):
    """Abschnitt-Index für Baustein b oder None (mehrdeutig/keiner) + Art (ziffer | region | seite)."""
    reg = b.regionen
    kand = [i for i, a in enumerate(teile) if reg is None or (a.regionen & reg)]
    if reg is None and len(teile) > 1:
        kand = []                          # Rho & Co.: ohne Ziffer nur bei genau einer Untersuchung
    b_seite = b.seiten[0] if len(b.seiten) == 1 else ("beidseits" if b.seiten else "")
    liste = cas_leistungen or []
    leistung = _leistung_zur_ziffer(b.ziffer, liste)
    if leistung is not None:
        l_reg, l_seite = _leistung_info(leistung, templates)
        if (reg is None or (l_reg & reg)) and _seite_passt(b_seite, l_seite):
            treffer = [i for i, a in enumerate(teile)
                       if (a.regionen & l_reg) and _seite_passt(a.seite, l_seite) and (reg is None or a.regionen & reg)]
            if len(treffer) == 1:
                return treffer[0], "ziffer"
    if len(kand) == 1:
        return kand[0], "region"
    if len(kand) > 1 and b_seite in ("rechts", "links"):
        s = [i for i in kand if teile[i].seite in (b_seite, "beidseits")]
        if len(s) == 1:
            return s[0], "seite"
    return None, ""


# ───────────────────────────── Einsetzen ─────────────────────────────
@dataclass
class Einsatz:
    report: str
    hinweise: List[str] = field(default_factory=list)
    zeilen: List[str] = field(default_factory=list)          # wörtlich eingesetzte Zeilen (Gate)
    behandelt: Dict[Tuple[str, str], int] = field(default_factory=dict)   # (AccNo, Modul) → Version
    eingesetzt: Dict[Tuple[str, str], List[str]] = field(default_factory=dict)   # je Baustein die Zeilen
    zuordnung: Dict[str, str] = field(default_factory=dict)  # Modul → Abschnitt-Titel | „Ende“
    nicht_entfernt: List[str] = field(default_factory=list)  # Zeilen einer älteren Fassung, die nicht mehr wörtlich da waren


def _kurz(t, n=60):
    t = (t or "").strip()
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def _befund_pruefen(b, bericht, diktat, hinweise):
    """Befundzeilen gegen Befund (KI-Text) und Diktat prüfen → Zeilen, die eingesetzt werden; Hinweise ergänzt."""
    gesamt = f"{bericht}\n{diktat}"
    if b.modul == "rho":
        rho_da, score = _rho_im_text(gesamt)
        if rho_da:
            mw = next((m for m in map(messwert, b.befundteil) if m and m.zahl is not None), None)
            if mw is not None and score is not None and score != mw.zahl:
                hinweise.append(f"{b.name}: Score im Befund {score}, laut {b.modul_name or b.name} {mw.wert} – bitte "
                                "prüfen (nichts angefügt)")
            else:
                hinweise.append(f"{b.name}: Rho-Text schon im Befund – nicht doppelt angefügt")
            return None
    out = []
    for z in b.befundteil:
        mw = messwert(z)
        art, gefunden = im_text(mw, gesamt) if mw else ("fehlt", "")
        if art == "gleich":
            hinweise.append(f"{b.name}: {mw.name} schon im Befund ({gefunden}) – nicht doppelt angefügt")
        elif art == "anders":
            hinweise.append(f"{b.name}: {mw.name} im Befund {gefunden}, laut IB Lab {mw.wert} – bitte prüfen "
                            "(IB-Lab-Wert nicht angefügt)")
        else:
            out.append(z)
            if mw and im_text(mw, diktat)[0] == "ohne_zahl":    # der Arzt hat die Messgröße ohne Zahl diktiert
                hinweise.append(f"{b.name}: {mw.name} schon diktiert – IB-Lab-Wert angefügt, bitte prüfen")
    return out


def _ergebnis_pruefen(b, bericht, diktat, erg_zeilen, hinweise):
    """Ergebnispunkte prüfen: Ergebnis unauffällig (außer Rho) → nichts, Hinweis; Diagnose schon da → nicht doppelt;
    vom Diktat verneint → nicht, Hinweis; nur verwandtes Wort → anhängen + Hinweis."""
    if not b.ergebnis:
        return []
    if b.modul != "rho" and ergebnis_normal(erg_zeilen):
        for p in b.ergebnis:
            hinweise.append(f"{b.name}: „{_kurz(p)}“ nicht ins Ergebnis übernommen – Ergebnis unauffällig, bitte prüfen")
        return []
    out = []
    for p in b.ergebnis:
        art, wort = _diagnose_im_text(p, bericht, diktat)
        if art == "doppelt":
            hinweise.append(f"{b.name}: „{_kurz(p)}“ – Diagnose schon im Befund, nicht doppelt angefügt")
        elif art == "widerspruch":
            hinweise.append(f"{b.name}: „{_kurz(p)}“ – Diktat verneint „{wort}“, bitte prüfen (nicht angefügt)")
        else:
            if art == "verwandt":
                hinweise.append(f"{b.name}: „{_kurz(p)}“ angefügt – Befund nennt schon „{wort}“, bitte prüfen")
            out.append(p)
    return out


def _normalsaetze(b, zeilen, punkte):
    """Befundsätze, die eine Eigenschaft der IB-Lab-Diagnosen (BEZUG, Kern der Diagnose) als normal beschreiben bzw.
    verneinen, z. B. „Das Fußgewölbe ist regulär ausgebildet …“ neben „Pes planus“ — nur für den Hinweis."""
    woerter = [k for k in map(diagnose_kern, punkte) if len(k) >= 4]
    for p in map(_norm, punkte):
        for diagnosen, worte in BEZUG:
            if any(d in p for d in diagnosen):
                woerter += list(worte)
    woerter = list(dict.fromkeys(woerter))
    if not woerter:
        return []
    seiten_ib = {s.lower()[:5] for p in punkte for s in _SEITE_WORT.findall(p)}
    if any(re.search(r"beidseit|bds", p, re.I) for p in punkte):
        seiten_ib |= {"recht", "link"}
    out = []
    for z in zeilen:
        if z.strip().startswith("#"):
            continue
        for satz in re.split(r"(?<=[.!?])\s+", z.strip()):
            seiten = {s.lower()[:5] for s in _SEITE_WORT.findall(satz)}
            if seiten and seiten_ib and not (seiten & seiten_ib):
                continue                   # Satz über die andere Seite („linkes Bein normal“ bei Varus rechts)
            for w in woerter:
                v = _vorkommen(w, satz)
                if v and ("verneint" in v or (_NORMAL.search(satz) and not br.has_pathology(satz))):
                    out.append(satz.strip())
                    break
    return list(dict.fromkeys(out))


def _befund_anfuegen(zeilen, a, neu):
    """Befundzeilen als eigener Absatz ans Ende des Befundtexts von a (vor „## Ergebnis“) → Zahl eingefügter Zeilen."""
    e = a.ergebnis if a.ergebnis >= 0 else a.ende
    j = e
    while j > a.start + 1 and not zeilen[j - 1].strip():
        j -= 1
    block = ([] if zeilen[j - 1].strip().startswith("## ") else [""]) + list(neu)
    if a.ergebnis >= 0:
        block.append("")                     # genau eine Leerzeile vor „## Ergebnis“
        alt, zeilen[j:e] = e - j, block
        return len(block) - alt
    zeilen[j:j] = block                      # ohne „## Ergebnis“: Leerzeilen vor dem nächsten Abschnitt bleiben
    return len(block)


def _ergebnis_anfuegen(zeilen, a, punkte):
    """Ergebnispunkte ans Ende der Ergebnisliste von a; nummerierte Listen (oder ein einzelner Punkt) neu durchzählen,
    mehrere unnummerierte (wörtlicher Ordi-Baustein) bleiben unnummeriert — wie br.rho_einfuegen. → Zeilen mehr."""
    if a.ergebnis < 0:
        k = a.ende
        while k > a.start + 1 and not zeilen[k - 1].strip():
            k -= 1
        block = ["", "## Ergebnis"] + list(punkte)
        zeilen[k:k] = block
        return len(block)
    s, k = a.ergebnis + 1, a.ende
    while k > s and not zeilen[k - 1].strip():
        k -= 1
    inhalt = zeilen[s:k]
    da = [z for z in inhalt if z.strip()]
    neu = inhalt + list(punkte)
    if any(_NUM.match(z) for z in da) or len(da) <= 1:
        neu = br.ergebnis_nummerieren("## Ergebnis\n" + "\n".join(neu)).split("\n")[1:]
    zeilen[s:k] = neu
    return len(neu) - len(inhalt)


def _verschieben(teile, i, n, nur_ende=False):
    """Nach n eingefügten Zeilen in Abschnitt i die Zeilenindizes anpassen (Befund: ab „## Ergebnis“, Ergebnis: Ende)."""
    a = teile[i]
    if not nur_ende and a.ergebnis >= 0:
        a.ergebnis += n
    a.ende += n
    for t in teile[i + 1:]:
        t.start, t.ende = t.start + n, t.ende + n
        t.befund += n if t.befund >= 0 else 0
        t.ergebnis += n if t.ergebnis >= 0 else 0


def _zeilen_entfernen(text, alte):
    """Zeilen einer älteren Fassung wörtlich herausnehmen (Ergebnispunkte samt Nummer) → (Text, nicht gefunden)."""
    fehlt = []
    for z in alte or []:
        neu = re.sub(r"(?m)^[ \t]*(?:\d+\.\s*)?" + re.escape(z) + r"[ \t]*(?:\n|$)", "", text, count=1)
        if neu == text:
            fehlt.append(z)
        text = neu
    return text, fehlt


def einsetzen(report, bausteine, segmente=None, diktat="", cas_leistungen=None, templates=None, entfernen=None):
    """Bausteine deterministisch in den fertigen Befund (Markdown ## Titel / ## Befund / ## Ergebnis) einsetzen.
    segmente: Diktat-Abschnitte in Befund-Reihenfolge (Pipeline) · diktat: ganzes Diktat (sonst) · cas_leistungen:
    Liste der Brücke in CAS-Reihenfolge (Ziffer → Leistung) · entfernen: Zeilen einer älteren Fassung, die vorher
    wörtlich herausgenommen werden (Knopf „IB Lab einfügen“ nach einer neuen Fassung)."""
    e = Einsatz(report=report or "")
    if not bausteine or not (report or "").strip():
        return e
    text, e.nicht_entfernt = _zeilen_entfernen(report, entfernen)
    zeilen = text.split("\n")
    teile = abschnitte(zeilen)
    if segmente and len(segmente) == len(teile):
        for a, s in zip(teile, segmente):
            a.segment = s
    elif len(teile) == 1:
        teile[0].segment = diktat or "\n".join(segmente or [])
    ganz = diktat or "\n".join(segmente or [])
    ende_zeilen = []
    for b in bausteine:
        e.behandelt[b.schluessel] = b.version
        if not b.befundteil and not b.ergebnis:
            continue
        i, _art = zuordnen(b, teile, cas_leistungen, templates)
        if i is None:
            bericht = "\n".join(zeilen + ende_zeilen)
            befund = _befund_pruefen(b, bericht, ganz, e.hinweise)
            if befund is None:
                continue
            neu = befund + _ergebnis_pruefen(b, bericht, ganz, [], e.hinweise)
            if neu:
                ende_zeilen += neu
                e.eingesetzt[b.schluessel] = neu
                e.zuordnung[b.modul] = ENDE
                e.hinweise.append(f"{b.label}: keiner Untersuchung eindeutig zuzuordnen – Werte als eigener Absatz am "
                                  "Ende, bitte prüfen")
            continue
        a = teile[i]
        bericht = "\n".join(zeilen[a.start:a.ende])
        befund = _befund_pruefen(b, bericht, a.segment, e.hinweise)
        if befund is None:
            continue
        ergebnis = _ergebnis_pruefen(b, bericht, a.segment, zeilen[a.ergebnis + 1:a.ende] if a.ergebnis >= 0 else [],
                                     e.hinweise)
        if ergebnis:
            for satz in _normalsaetze(b, zeilen[a.start:a.ergebnis if a.ergebnis >= 0 else a.ende], ergebnis):
                e.hinweise.append(f"{b.name}: Befundtext „{_kurz(satz, 50)}“ widerspricht IB Lab – bitte prüfen")
        if befund:
            _verschieben(teile, i, _befund_anfuegen(zeilen, a, befund))
        if ergebnis:
            _verschieben(teile, i, _ergebnis_anfuegen(zeilen, a, ergebnis), nur_ende=True)
        if befund or ergebnis:
            e.eingesetzt[b.schluessel] = befund + ergebnis
            e.zuordnung[b.modul] = a.titel or "Befund"
    text = "\n".join(zeilen).rstrip()
    if ende_zeilen:
        text += "\n\n" + "\n".join(ende_zeilen)
    e.report = text
    e.zeilen = [z for zs in e.eingesetzt.values() for z in zs]
    e.hinweise += [f"IB-Lab-Wert nicht 1:1 im Befund: {_kurz(z)} – bitte prüfen" for z in gate(e.report, e.zeilen)]
    e.hinweise = list(dict.fromkeys(e.hinweise))
    return e


def gate(report, zeilen):
    """Messwert-Gate: jede eingesetzte Zeile wörtlich im Befund und jede Zahl daraus 1:1 → Liste der Abweichungen."""
    fehlt = []
    for z in zeilen:
        if z not in (report or ""):
            fehlt.append(z)
            continue
        for zahl in re.findall(r"\d+(?:,\d+)?", z):
            if zahl not in report:
                fehlt.append(z)
                break
    return fehlt


# ───────────────────────────── Gen-Prompt ─────────────────────────────
def prompt_block(bausteine, vorlage=None):
    """<ibl_messwerte> für den Gen-Prompt — nur mit Bausteinen (sonst bleibt der Prompt bit-gleich). Ohne Zahlen und
    ohne Diagnosen: die KI soll nichts davon selbst schreiben, nur wissen, dass es ergänzt wird. vorlage = Text der
    Vorlage dieses Abschnitts: Sätze daraus, die einer IB-Lab-Diagnose widersprechen („Regelrechte Abbildung beider
    Pfannendächer.“ neben einer Hüftdysplasie), werden wörtlich als „weglassen“ genannt (live 13.10.: nur die Themen zu
    nennen reichte der KI beim Becken nicht)."""
    zeilen = []
    for b in bausteine or []:
        namen = list(dict.fromkeys(m.name for m in map(messwert, b.befundteil) if m))
        if namen:
            thema = THEMEN.get(b.modul)
            zeilen.append(f"- {b.name}: " + ", ".join(namen) + (f" (ersetzt Vorlagen-Sätze zu: {thema})" if thema else ""))
    if not zeilen:
        return ""
    weg = []
    for b in bausteine:
        if b.ergebnis and vorlage:
            weg += [s for s in _normalsaetze(b, vorlage.split("\n"), b.ergebnis) if s not in weg]
    if weg:
        zeilen.append("Diese Sätze der Vorlage widersprechen den IB-Lab-Werten – nicht übernehmen (bzw. nur ohne die "
                      "widersprechende Aussage): " + " ".join(f"„{s}“" for s in weg))
    return ("<ibl_messwerte>\n"
            "Zu dieser Untersuchung liegen KI-Messwerte von IB Lab vor. RaKScribe fügt sie nach dem Befund automatisch "
            "und wörtlich ein:\n" + "\n".join(zeilen) + "\n"
            "Regeln: Nenne diese Messwerte nicht selbst und erfinde keine Zahlen. Widersprich ihnen nicht: Sätze der "
            "Vorlage zu den in Klammern genannten Themen lässt du weg (die Messwerte ersetzen sie), außer der Arzt hat "
            "dazu etwas diktiert. Was der Arzt selbst an Messwerten oder Diagnosen diktiert hat, übernimmst du genau wie "
            "diktiert.\n"
            "</ibl_messwerte>")


def fuer_abschnitt(bausteine, regionen, einziger=False):
    """Bausteine, deren Modul zur Region eines Diktat-Abschnitts passt (Module ohne Region nur bei einem Abschnitt)."""
    return [b for b in bausteine or [] if (b.regionen is None and einziger) or (b.regionen and b.regionen & regionen)]


@dataclass
class IblKontext:
    """Für pipeline.Kontext.ibl: Bausteine des offenen Auftrags + CAS-Leistungen (Ziffer → Leistung)."""
    bausteine: List[Baustein]
    cas_leistungen: Optional[list] = None

    def __bool__(self):
        return any(b.befundteil or b.ergebnis for b in self.bausteine)


# ───────────────────────────── v3.14.0: Gerüst vor dem Diktat, auffällige Werte ─────────────────────────────
# Peter 14.10.2026: „RaKScribe soll bereits a priori relevante IBL-Zusatzinfos (pathologische Messwerte usw.) in den
# structured report einbauen, wenn ich auf Diktieren klicke.“ Öffnet die Brücke RaKScribe mit IB-Lab-Bausteinen, steht
# im Befund-Feld schon vor dem ersten Wort das Gerüst: je Untersuchung Titel, die Befundzeilen von IB Lab wörtlich und
# die Ergebnispunkte — gebaut mit derselben Funktion wie nach der KI (einsetzen), also deterministisch und 1:1.
# Auffällig (in der Anzeige hervorgehoben) ist eine Zeile nur, wenn eine Regel des Abholers aus dem Messwert einen
# Ergebnispunkt gemacht hat (die Schwellen stehen mit Quelle in den Regeln des Abholers): der Messwert („Calcaneus-
# neigungswinkel 10°“) steht dann wörtlich im Ergebnispunkt („Pes planus (Calcaneusneigungswinkel 10°).“). Ohne
# Ergebnispunkt wird nichts gewertet, nur angezeigt. Keine Bausteine mit Inhalt → kein Gerüst (kein Platzhalter).
_QUELLE_ZEILE = re.compile(r"\s*\((?:IB Lab|16 Bit|Radiobotics)[^)]*\)\s*\.?\s*$")


def messung_text(zeile):
    """„Calcaneusneigungswinkel 10° (IB Lab FROG).“ → „Calcaneusneigungswinkel 10°“."""
    return _QUELLE_ZEILE.sub("", (zeile or "").strip()).rstrip(" .")


def auffaellige_zeilen(bausteine):
    """Befundzeilen, aus deren Messwert ein Ergebnispunkt wurde, und die Ergebnispunkte selbst (in Baustein-Reihenfolge)."""
    out = []
    for b in bausteine or []:
        for z in b.befundteil:
            m = messung_text(z)
            if m and any(m in p for p in b.ergebnis):
                out.append(z)
        out += [p for p in b.ergebnis if p not in out]
    return out


def _titel_mit_seite(name, seite):
    if not seite or seite in name.lower():
        return name
    return name.replace(" in ", f" {seite} in ", 1) if " in " in name else f"{name} {seite}"


REGION_TITEL = {"frog": "Fuß", "lama": "Ganzbeinaufnahme", "hippo": "Becken und Hüften", "koala": "Knie",
                "squirrel": "Wirbelsäule", "panda": "Hand", "rho": "Knochendichte (opportunistisch)"}


def _leistung_fuer(b, liste, templates):
    """CAS-Leistung (dict) zum Baustein: Ziffer (exakt bzw. Stelle), sonst eindeutig über Region und Seite; sonst None."""
    reg = b.regionen
    b_seite = b.seiten[0] if len(b.seiten) == 1 else ("beidseits" if b.seiten else "")
    l = _leistung_zur_ziffer(b.ziffer, liste)
    if l is not None:
        l_reg, l_seite = _leistung_info(l, templates)
        if (reg is None or (l_reg & reg)) and _seite_passt(b_seite, l_seite):
            return l
    if reg is None:
        return None
    kand = [x for x in liste or [] if isinstance(x, dict) and not x.get("ohne_vorlage")
            and (_leistung_info(x, templates)[0] & reg) and _seite_passt(b_seite, _leistung_info(x, templates)[1])]
    return kand[0] if len(kand) == 1 else None


def geruest(bausteine, cas_leistungen=None, templates=None):
    """Gerüst des strukturierten Befunds aus den IB-Lab-Bausteinen (vor dem Diktat) → Einsatz (report, zeilen,
    eingesetzt, behandelt, zuordnung) oder None, wenn kein Baustein Befundzeilen oder Ergebnispunkte hat.
    Je Untersuchung ein Abschnitt „## <Titel>“ / „## Befund“ / „## Ergebnis“ (nummeriert wie nach der KI); Titel = Vorlage
    der zugeordneten CAS-Leistung (mit Seite), sonst Region des Moduls (mit Seite), sonst „IB Lab <Modul>“. Messwerte und
    Ergebnispunkte wörtlich; leere Überschriften gibt es nicht."""
    mit_inhalt = [b for b in bausteine or [] if b.befundteil or b.ergebnis]
    if not mit_inhalt:
        return None
    templates = templates or {}
    gruppen = []                                 # [(titel, [Bausteine])] in Reihenfolge
    for b in mit_inhalt:
        l = _leistung_fuer(b, cas_leistungen, templates)
        name = (templates.get(l.get("vorlage")) or {}).get("display_name") if l and l.get("vorlage") else None
        if name:
            titel = _titel_mit_seite(name, l.get("seite") or "")
        else:
            seite = "beidseits" if {"rechts", "links"} <= set(b.seiten) else (b.seiten[0] if len(b.seiten) == 1 else "")
            titel = (REGION_TITEL.get(b.modul, "") + (f" {seite}" if seite else "")).strip() or f"IB Lab {b.name}"
        g = next((g for g in gruppen if g[0] == titel), None)
        if g is None:
            gruppen.append((titel, [b]))
        else:
            g[1].append(b)
    e = Einsatz(report="")
    teile = []
    for titel, bs in gruppen:
        befund = [z for b in bs for z in b.befundteil]
        punkte = [p for b in bs for p in b.ergebnis]
        block = [f"## {titel}"]
        if befund:
            block += ["", "## Befund"] + befund
        if punkte:
            block += ["", br.ergebnis_nummerieren("## Ergebnis\n" + "\n".join(punkte))]
        teile.append("\n".join(block))
        for b in bs:
            e.behandelt[b.schluessel] = b.version
            e.eingesetzt[b.schluessel] = list(b.befundteil) + list(b.ergebnis)
            e.zuordnung[b.modul] = titel
    e.report = "\n\n".join(teile).strip()
    e.zeilen = [z for zs in e.eingesetzt.values() for z in zs]
    return e
