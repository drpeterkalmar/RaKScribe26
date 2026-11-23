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
import json
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

import befund_regeln as br
import cas_vorlagen as cv

# Modul → Regionen der passenden Untersuchung (None = jede). Modulnamen = öffentliche Produktnamen, Regionen wie
# cas_vorlagen.REGIONEN.
# kaiscribe-schulter-ergebnis-n1 (Punkt 61, Georg RH 120 23.11.2026: „Du übernimmst offensichtlich noch die
# KOALA-Knieauswertung. Die muss raus“; Peter RH 65 20.11.; Freigabe Kanban #514 am 23.11. 20:19): KOALA (Knie) setzt
# KaiScribe NICHT mehr automatisch ein – kein K&L-Grad, kein K&L-Satz, keine Spaltweiten, kein Ergebnispunkt, keine
# KOALA-Hinweiszeile, kein Prompt-Block. Knie = nur Diktiertes (diktierter Grad/Adjektiv → K&L-Satz wie Register).
# aus_liste() lässt KOALA-Bausteine weg; der alte Weg (18.11.2026, kl-koala) bleibt hinter dem Schalter erhalten.
# #420 (KOALA nach K&L-Tabelle) entfällt damit. Andere Gelenke (K&L peripher, Rhizarthrose) unverändert.
KOALA_KNIE_AUTOMATIK = False
MODULE = {"frog": {"fuss"}, "lama": {"unterschenkel"}, "hippo": {"becken", "huefte"}, "koala": {"knie"},
          "squirrel": {"hws", "bws", "lws"}, "panda": {"hand"}, "rho": None, "rbfracture": None}
# Diagnose (Wörter im Ergebnispunkt) → Wörter, mit denen ein Befundsatz dieselbe Eigenschaft als normal beschreibt
# („Das Fußgewölbe ist regulär …“ neben „Pes planus“) — nur für den Hinweis, nie wird Text geändert.
BEZUG = [
    (("pes planus", "pes cavus", "längsgewölbe"), ("fußgewölbe", "längsgewölbe")),
    (("hallux valgus", "intermetatarsalwinkel", "metatarsus"), ("gelenkwinkel",)),
    (("genu varum", "genu valgum", "varusfehlstellung", "valgusfehlstellung"), ("achse", "beinachse")),
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
    vorwerte: List[dict] = field(default_factory=list)   # v3.18.0: frühere Werte derselben Messgröße (nur Anzeige)
    befundtext: Optional[dict] = None   # v3.19.8: FROG – fertige Sätze + Begriffe des Abholers ≥ 1.3.7 (Georg 17.11.2026)
    text_aus_ablage: bool = False       # kaiscribe-frog-einsetzen-n1: befundtext von KaiScribe aus der Ablage (Brücke zu alt)
    alter: Optional[int] = None         # 18.11.2026: Alter des Patienten in Jahren, wenn die Brücke es liefert (KOALA < 18)

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


# v3.19.9 (Georg Riegler 18.11.2026, Brief kaiscribe-ibl-ohne-norm-n1): „Die Normalwerte kommen nicht in den Befund und das
# Ergebnis.“ Der Abholer (ris-mods ibl/lama_ergebnis.py, ibl/frog_ergebnis.py) schreibt seit 18.11. keine Normbereiche mehr;
# Bausteine eines älteren Abholers („(Norm 0–15°)“, „[−2 bis 4°]“, „[3 bis 17 mm]“) werden hier beim Lesen bereinigt –
# Messwerte bleiben. Gleiche Regel: ris-mods bruecke/ibl_einfuegen.ohne_norm.
_ZAHL = r"[−-]?\d+(?:[.,]\d+)?"
_NORM_KLAMMER = re.compile(rf"\s*(?:\(Norm\s+{_ZAHL}\s*(?:–|-|bis)\s*{_ZAHL}\s*°\)|"
                           rf"\[{_ZAHL}\s*(?:bis|–)\s*{_ZAHL}\s*(?:°|mm)\])")
OHNE_NORM = ("lama", "frog")


def ohne_norm(t):
    """„HKA 5,0° [−2 bis 4°]“ → „HKA 5,0°“, „von 42° (Norm 0–15°)“ → „von 42°“; sonst unverändert."""
    return _NORM_KLAMMER.sub("", t) if isinstance(t, str) else t


def _vorwerte(x):
    """v3.18.0: Vorwerte der Brücke (je Wert u. a. „text“ = „Vorwert 03/2024: 12°, IB Lab“) – nur Einträge mit Text."""
    return [dict(v) for v in x if isinstance(v, dict) and isinstance(v.get("text"), str) and v["text"].strip()] \
        if isinstance(x, list) else []


def _befundtext(modul, x):
    """v3.19.8 (FROG, Georg Riegler 17.11.2026): Feld „befundtext“ der Brücke (Abholer ≥ 1.3.7, ris-mods
    ibl/frog_ergebnis.py) – nur Fassung 1 mit Inhalt; sonst None (dann gilt das Verhalten bis 3.19.7).
    v3.19.13 (HIPPO, Georg 18.11.2026, Abholer ≥ 1.3.11, ris-mods ibl/hippo_ergebnis.py): {"saetze", "ergebnis",
    "schluss", "kind", "becken"}. SQUIRREL (Georg 20.11.2026, Abholer ≥ 1.3.14): {"saetze", "cobb_satz", "ergebnis",
    "schluss", "coronal", "anatomisch", "kind", "achse_normal_weg", "kruemmungen"}."""
    if modul == "hippo" and isinstance(x, dict) and x.get("format") == 1:
        bt = {"saetze": _texte(x.get("saetze")), "ergebnis": str(x.get("ergebnis") or "").strip(),
              "schluss": str(x.get("schluss") or "").strip(), "kind": bool(x.get("kind")),
              "becken": bool(x.get("becken"))}
        return bt if bt["saetze"] else None
    if modul == "squirrel" and isinstance(x, dict) and x.get("format") == 1:
        # Georg 20.11.2026 „1a 2a 3a 4a 5ja“ (Abholer ≥ 1.3.14, ris-mods ibl/squirrel_ergebnis.py): Skoliose-Sätze, Cobb-Satz
        # für den Diktat-Fall (Peter 20.11.2026 Punkt 20), ein Ergebnispunkt, Schluss
        bt = {"saetze": _texte(x.get("saetze")), "cobb_satz": str(x.get("cobb_satz") or "").strip(),
              "ergebnis": str(x.get("ergebnis") or "").strip(), "schluss": str(x.get("schluss") or "").strip(),
              "coronal": str(x.get("coronal") or "").strip(), "anatomisch": bool(x.get("anatomisch")),
              "kind": bool(x.get("kind")), "achse_normal_weg": bool(x.get("achse_normal_weg", True)),
              "kruemmungen": [dict(k) for k in (x.get("kruemmungen") if isinstance(x.get("kruemmungen"), list) else [])
                              if isinstance(k, dict)]}
        return bt if bt["saetze"] and bt["cobb_satz"] else None
    if modul != "frog" or not isinstance(x, dict) or x.get("format") != 1:
        return None
    begriffe = [{"art": str(g.get("art") or ""), "text": str(g.get("text") or "").strip(),
                 "seite": str(g.get("seite") or "").strip()}
                for g in (x.get("begriffe") if isinstance(x.get("begriffe"), list) else [])
                if isinstance(g, dict) and str(g.get("text") or "").strip()]
    bt = {"stellung": [ohne_norm(t) for t in _texte(x.get("stellung"))],
          "gewoelbe": [ohne_norm(t) for t in _texte(x.get("gewoelbe"))],
          "gewoelbe_weg": bool(x.get("gewoelbe_weg")), "gewoelbe_pathologisch": bool(x.get("gewoelbe_pathologisch")),
          "phalangen": bool(x.get("phalangen")), "ein_fuss": bool(x.get("ein_fuss")), "begriffe": begriffe,
          "schluss": str(x.get("schluss") or "").strip()}
    # NACHTRAG ibl-georg-2011-n1 (ris-mods, Abholer 1.3.14, RH 30): alle Winkel in Norm + Toleranz bzw. widersprüchlich →
    # keine Diagnose, aber „messwerte“-Sätze (d.p. / seitlich) ans Ende der Fuß-Beschreibung, kein Ergebnispunkt
    bt["messwerte"] = [ohne_norm(t) for t in _texte(x.get("messwerte"))]
    bt["ohne_diagnose"] = bool(x.get("ohne_diagnose")) and bool(bt["messwerte"])
    return bt if (begriffe and (bt["stellung"] or bt["gewoelbe"])) or bt["ohne_diagnose"] else None


def _alter(d):
    """Alter in Jahren aus dem Baustein („alter“ bzw. „patient_alter“) – sonst None (unbekannt)."""
    for k in ("alter", "patient_alter"):
        try:
            if d.get(k) is not None and str(d.get(k)).strip() != "":
                return int(float(str(d.get(k)).replace(",", ".")))
        except (TypeError, ValueError):
            pass
    return None


NUR_ANZEIGE = {"rho"}               # v3.19.10: Module, von denen KaiScribe nie Text einsetzt (nur Hinweise in der Anzeige)
# kaiscribe-georg-2011-n1 (Georg 20.11.2026, Punkt 21b, RH 69/92): KI-Hinweise (RBfracture „KI: Verdacht auf …“) sind nie ein
# Ergebnispunkt und stehen nicht im Befund – sie bleiben nur als Hinweis für den Arzt (Anzeige).
NUR_HINWEIS = {"rbfracture"}


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
        if modul == "koala" and not KOALA_KNIE_AUTOMATIK:     # Punkt 61: KOALA-Knie-Automatik ganz raus
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
        ergebnis, hinweise = _texte(d.get("ergebnis")), _texte(d.get("hinweise"))
        if modul in OHNE_NORM:                                   # v3.19.9: nie ein Normbereich (Georg 18.11.2026)
            ergebnis, hinweise = [ohne_norm(t) for t in ergebnis], [ohne_norm(t) for t in hinweise]
        befundteil = _texte(d.get("befundteil"))
        if modul in NUR_HINWEIS:
            name = str(d.get("name") or modul.upper())
            hinweise = hinweise + [f"{name}: {t} (nur Hinweis, nicht im Befund)" for t in befundteil + ergebnis
                                   if t not in hinweise]
            befundteil, ergebnis = [], []
        if modul in NUR_ANZEIGE:
            # v3.19.10 (Georg 18.11.2026, RH 57): KaiScribe setzt von Rho nichts ein – weder „Rho-Score N von 10“ noch den
            # Entwurf des Abholers. Ein Rho-Text kommt nur bei Score ≥ 7, ohne DEXA in den letzten 2 Jahren und nur für
            # die LWS; das prüft allein der Formatierer (ris-mods ibl_einfuegen, Screening-Baustein mit Georgs Wortlaut),
            # KaiScribe kennt die DEXA-Vorgeschichte nicht. Die Hinweise bleiben (nur Anzeige). Ab Brücke 2.5.21 kommt Rho
            # schon ohne Text an; das hier deckt ältere Brücken ab.
            befundteil, ergebnis = [], []
        out.append(Baustein(accno=accno, modul=modul, name=str(d.get("name") or modul.upper()), version=version,
                            ziffer=ziffer, seiten=seiten, befundteil=befundteil,
                            ergebnis=ergebnis, hinweise=hinweise,
                            nicht_zugeordnet=_texte(d.get("nicht_zugeordnet")),
                            modul_name=str(d.get("modul_name") or ""), aktualisiert=str(d.get("aktualisiert") or ""),
                            vorwerte=_vorwerte(d.get("vorwerte")), befundtext=_befundtext(modul, d.get("befundtext")),
                            text_aus_ablage=d.get("befundtext_quelle") == "ablage", alter=_alter(d)))
    out.sort(key=lambda b: (b.ziffer, b.modul))
    return out


# kaiscribe-frog-einsetzen-n1 (Georg 19.11.2026, RH 127 „keine Werte“): an einem Befund-PC lief noch die Brücke 2.5.15 – sie
# reicht das Feld „befundtext“ nicht durch (FROG erst ab Brücke 2.5.20, HIPPO ab 2.5.22). KaiScribe bekam FROG mit
# Messzeilen und Begriffen, aber ohne die Sätze, fiel in den alten Weg und setzte 0 Zeilen ein (Ergebnis der Vorlage
# „unauffällig“ → Begriffe verworfen). Darum holt KaiScribe den Text dann selbst aus der Ablage des Abholers
# (X:\IBL-Vorbefunde\<AccNo>_<modul>.json, dieselbe Datei, aus der die Brücke liest) – nur bei derselben Fassung, sonst
# bleibt alles wie geliefert. Sichtbarer Hinweis, damit die veraltete Brücke auffällt (KaiScribe-einrichten.cmd).
# SQUIRREL (20.11.2026) ebenso – die Brücke reicht den Skoliose-Text erst ab 1.8.0/Abholer 1.3.14 durch.
TEXT_MODULE = ("frog", "hippo", "squirrel")
ABLAGE_FORMAT = "ibl-abholer/1"     # = ris-mods ibl/abholer.py ABLAGE_FORMAT
_ACCNO = re.compile(r"[0-9A-Za-z-]+")


def _ablage_befundtext(ablage, accno, modul, version):
    """Roh-Feld befundtext[modul] aus der Abholer-Datei derselben Fassung, sonst None (fehlt, andere Fassung, kaputt)."""
    try:
        with open(os.path.join(ablage, f"{accno}_{modul}.json"), encoding="utf-8-sig") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or d.get("format") != ABLAGE_FORMAT or not isinstance(d.get("vorbefund"), dict):
        return None
    if str(d.get("accession_number") or "").strip() != accno:
        return None
    try:
        if int(d.get("version") or 0) != version:
            return None
    except (TypeError, ValueError):
        return None
    bt = d["vorbefund"].get("befundtext")
    bt = bt.get(modul) if isinstance(bt, dict) else None
    return bt if _befundtext(modul, bt) is not None else None


def text_nachladen(liste, ablage):
    """Bausteine der Brücke (Liste von dicts) → (Liste, [„FROG v3“ …]): FROG/HIPPO ohne „befundtext“ bekommen ihn aus der
    Ablage des Abholers (gleiche AccNo und Fassung). FROG nur mit Ergebnispunkten (ohne Pathologie gibt es keinen Text).
    ablage leer/„aus“ → unverändert. Wirft nie."""
    if not liste or not ablage or str(ablage).strip().lower() == "aus":
        return liste, []
    out, geholt = [], []
    for d in liste:
        modul = str(d.get("modul") or "").strip().lower() if isinstance(d, dict) else ""
        accno = str(d.get("accno") or "").strip() if modul else ""
        if (modul in TEXT_MODULE and not d.get("befundtext") and _ACCNO.fullmatch(accno)
                and (modul != "frog" or _texte(d.get("ergebnis")))):
            try:
                version = int(d.get("version") or 0)
            except (TypeError, ValueError):
                version = 0
            bt = _ablage_befundtext(ablage, accno, modul, version)
            if bt is not None:
                d = dict(d, befundtext=bt, befundtext_quelle="ablage")
                geholt.append(f"{str(d.get('name') or modul.upper())} v{version}")
        out.append(d)
    return out, geholt


def band_text(bausteine, an=True):
    """„IB Lab: FROG rechts ✓ · LAMA ✓“ (Übernahme aus: ohne Haken, mit Hinweis aufs Menü)."""
    if not bausteine:
        return ""
    if not an:
        return "IB Lab: " + " · ".join(b.label for b in bausteine) + "  (Übernahme aus – Menü)"
    return "IB Lab: " + " · ".join(f"{b.label} ✓" for b in bausteine)


FROG_KI_BILD = "am KI-Bild prüfen"   # ris-mods ibl/frog_ergebnis (1.3.15): Widerspruch / „keine Diagnose …“ → rote Prüfzeile


def anzeige_hinweise(bausteine):
    """Hinweise des Abholers (nur Anzeige, nie in den Befund) + Zahl nicht zugeordneter Messgrößen."""
    out = []
    for b in bausteine:
        hs = [h if h.lower().startswith((b.name.lower(), (b.modul_name or "-").lower())) else f"{b.name}: {h}"
              for h in b.hinweise]
        if b.modul == "squirrel":          # 20.11.2026: Metall, Verlauf nicht zuordenbar, Konvexität fehlt = rote Prüfzeile
            hs = [f"⚠ {h}" if "prüfen" in h and not h.startswith("⚠") else h for h in hs]
        elif b.modul == "frog":            # 3.20.1 (Georg 20.11., RH 30; Abholer 1.3.15): Widerspruch der Winkel bzw. Messwerte
            hs = [f"⚠ {h}" if FROG_KI_BILD in h and not h.startswith("⚠") else h for h in hs]   # ohne Diagnose = rot
        out += hs
        if b.nicht_zugeordnet:
            out.append(f"{b.name}: {len(b.nicht_zugeordnet)} Messgröße(n) nicht zugeordnet (Katalog ergänzen)")
        if b.text_aus_ablage:
            out.append(f"{b.name}: Text aus der IB-Lab-Ablage geholt – Brücke an diesem PC veraltet "
                       "(KaiScribe-einrichten.cmd)")
        elif b.modul == "frog" and b.befundtext is None and any(ist_schluss(p) for p in b.ergebnis):
            out.append(f"{b.name}: Fuß-Text fehlt – Brücke an diesem PC veraltet (KaiScribe-einrichten.cmd), "
                       "IB-Lab-Werte nicht eingesetzt")
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


def kl_grade(bausteine, seite=""):
    """v3.18.4 (Peter 12.11.2026, RH 38): Kellgren-&-Lawrence-Grade aus den Befundzeilen der Bausteine (KOALA) → Liste.
    seite „links“/„rechts“: nur Zeilen dieser Seite bzw. ohne Seitenangabe (KL links 1, rechts 3 → links nur „1“)."""
    out = set()
    for b in bausteine or []:
        for z in b.befundteil:
            if "kellgren" not in z.lower():
                continue
            s = {x.lower() for x in _SEITE.findall(z)}
            if seite in ("links", "rechts") and s and seite not in s and not s & {"beidseits", "beidseitig", "bds"}:
                continue
            out.update(br.kl_grade(z))
    return sorted(out)


def _kl_pruefen(b, mw, z, diktat, hinweise):
    """v3.18.4: K&L-Grad des Bausteins gegen einen DIKTIERTEN Grad (jede Schreibweise, br.kl_grade) → True = nicht
    anfügen (diktiert gleich: nicht doppelt; diktiert anders: der diktierte Grad gilt, IB-Lab-Wert nicht zusätzlich)."""
    if "kellgren" not in (mw.name or "").lower():
        return False
    diktiert, eigen = br.kl_grade(diktat), br.kl_grade(z)
    if not diktiert or not eigen:
        return False
    if set(eigen) <= set(diktiert):
        hinweise.append(f"{b.name}: {mw.name} schon diktiert ({', '.join(diktiert)}) – nicht doppelt angefügt")
    else:
        hinweise.append(f"{b.name}: {mw.name} diktiert {', '.join(diktiert)}, laut IB Lab {', '.join(eigen)} – der "
                        "diktierte Grad gilt (IB-Lab-Wert nicht angefügt), bitte prüfen")
    return True


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
    nur = b.modul in BEFUND_NUR_AUFFAELLIG | BEFUND_OHNE_ZEILEN   # v3.18.8: nur Zeilen mit Ergebnispunkt (befund_zeilen)
    bleibt = befund_zeilen(b)
    for z in b.befundteil:
        mw = messwert(z)
        if z not in bleibt:
            _weggefiltert_pruefen(b, mw, z, gesamt, diktat, hinweise)
            continue
        if nur and _abschnitt_zeile(z):
            out.append(z)
            continue
        if mw and _kl_pruefen(b, mw, z, diktat, hinweise):
            continue
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
    return _ohne_leere_beschriftung(out) if nur else out


def _weggefiltert_pruefen(b, mw, z, gesamt, diktat, hinweise):
    """v3.18.8: Messzeile ohne Ergebnispunkt (kommt nicht in den Befund): kein „schon im Befund“-Hinweis, aber ein
    diktierter/geschriebener ABWEICHENDER Wert derselben Messgröße bleibt ein Prüf-Hinweis."""
    if mw is None or _abschnitt_zeile(z):
        return
    if "kellgren" in (mw.name or "").lower():
        diktiert, eigen = br.kl_grade(diktat), br.kl_grade(z)
        if diktiert and eigen and not set(eigen) <= set(diktiert):
            hinweise.append(f"{b.name}: {mw.name} diktiert {', '.join(diktiert)}, laut IB Lab {', '.join(eigen)} – "
                            "der diktierte Grad gilt, bitte prüfen")
        return
    art, gefunden = im_text(mw, gesamt)
    if art == "anders":
        hinweise.append(f"{b.name}: {mw.name} im Befund {gefunden}, laut IB Lab {mw.wert} – bitte prüfen "
                        "(unauffälliger IB-Lab-Wert, nicht im Befund)")


def _ergebnis_pruefen(b, bericht, diktat, erg_zeilen, hinweise):
    """Ergebnispunkte prüfen: Ergebnis unauffällig (außer Rho) → nichts, Hinweis; Diagnose schon da → nicht doppelt;
    vom Diktat verneint → nicht, Hinweis; nur verwandtes Wort → anhängen + Hinweis."""
    if not b.ergebnis:
        return []
    if b.modul in ERGEBNIS_ZUERST:
        return _lama_ergebnis_pruefen(b, bericht, diktat, hinweise)
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
        neu = re.sub(r"(?m)^[ \t]*(?:\d+\.\s*)?(?:Anmerkung:\s*)?" + re.escape(z) + r"[ \t]*(?:\n|$)", "", text, count=1)
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
        if not b.befundteil and not b.ergebnis and not frog_ohne_diagnose(b):
            continue
        i, _art = zuordnen(b, teile, cas_leistungen, templates)
        if b.modul == "panda":             # 19.11.2026: Knochenalter als fertiger Ergebnisbefund (Georg 18.11.2026)
            t = panda_text(b, cas_leistungen, e.hinweise)
            if t and i is not None:
                _panda_einsetzen(zeilen, teile, i, b, t, e)
            elif t:
                e.hinweise.append(f"{b.label}: keiner Hand-Untersuchung eindeutig zuzuordnen – Knochenalter-Text nicht "
                                  "eingesetzt, bitte prüfen")
            continue
        if b.modul == "koala":             # 18.11.2026: fester Kniebefund nach K&L-Tabelle statt Messzeilen (Georg)
            if i is not None:
                _koala_einsetzen(zeilen, teile, i, b, e)
            elif koala_hat_text(b):
                e.hinweise.append(f"{b.label}: keiner Knie-Untersuchung eindeutig zuzuordnen – KOALA-Text nicht "
                                  "eingesetzt, bitte prüfen")
            continue
        if _squirrel_text(b):              # 20.11.2026: Skoliose-Text (Georg „1a 2a 3a 4a 5ja“, Peter Punkt 20/40b)
            if i is not None:
                _squirrel_einsetzen(zeilen, teile, i, b, e, ganz)
                continue
            bericht = "\n".join(zeilen + ende_zeilen)
            neu = [z for z in _squirrel_ende(b, ganz) if z not in bericht]
            if neu:
                ende_zeilen += neu
                e.eingesetzt[b.schluessel] = neu
                e.zuordnung[b.modul] = ENDE
                e.hinweise.append(f"{b.label}: keiner Wirbelsäulen-Untersuchung eindeutig zuzuordnen – Text als eigener "
                                  "Absatz am Ende, bitte prüfen")
            continue
        if _hippo_text(b):                 # v3.19.13: Becken-/Hüft-Text (Georg 18.11.2026)
            if i is not None:
                _hippo_einsetzen(zeilen, teile, i, b, e)
                continue
            bericht = "\n".join(zeilen + ende_zeilen)
            neu = [z for z in _hippo_geruest(b, "")[0] + _hippo_geruest(b, "")[1] if z not in bericht]
            if neu:
                ende_zeilen += neu
                e.eingesetzt[b.schluessel] = neu
                e.zuordnung[b.modul] = ENDE
                e.hinweise.append(f"{b.label}: keiner Becken-/Hüft-Untersuchung eindeutig zuzuordnen – Text als eigener "
                                  "Absatz am Ende, bitte prüfen")
            continue
        if _frog_text(b):                  # v3.19.8: fertige Sätze statt Messzeilen (Georg 17.11.2026)
            if i is not None:
                _frog_einsetzen(zeilen, teile, i, b, e)
                continue
            bericht = "\n".join(zeilen + ende_zeilen)
            plan = _frog_plan(b, "", "", ganz, e.hinweise)
            neu = [z for z in (_frog_zeilen(plan) if plan else []) if z not in bericht]
            if neu:
                ende_zeilen += neu
                e.eingesetzt[b.schluessel] = neu
                e.zuordnung[b.modul] = ENDE
                e.hinweise.append(f"{b.label}: keiner Untersuchung eindeutig zuzuordnen – Text als eigener Absatz am "
                                  "Ende, bitte prüfen")
            continue
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
            for satz in _normalsaetze(b, zeilen[a.start:a.ergebnis if a.ergebnis >= 0 else a.ende],
                                      _pathologische_punkte(b, ergebnis)):
                e.hinweise.append(f"{b.name}: Befundtext „{_kurz(satz, 50)}“ widerspricht IB Lab – bitte prüfen")
        if befund:
            _verschieben(teile, i, _befund_anfuegen(zeilen, a, befund))
        if ergebnis and b.modul in ERGEBNIS_ZUERST:
            _verschieben(teile, i, _ergebnis_vorne(zeilen, a, ergebnis, a.segment, b, e.hinweise), nur_ende=True)
        elif ergebnis:
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
def _kl_satz(kl):
    """K&L-Satz des Gen-Prompts (v3.18.4, RH 38) aus den K&L-Befundzeilen der Bausteine."""
    return ("Kellgren-&-Lawrence-Grad laut IB Lab: " + "; ".join(messung_text(z) for z in kl) + ". Gehört ein "
            "diktierter Befund im Ergebnis zu diesem Gelenk (gleiche Seite, z. B. Arthrose oder "
            "Gelenkspaltverschmälerung) und ist kein eigener Grad diktiert, steht dahinter genau dieser Grad "
            "im Format „(Arthrose Grad X nach Kellgren & Lawrence)“ – keinen anderen. Diktiert der Arzt einen "
            "anderen Grad, gilt der diktierte Grad und der IB-Lab-Grad wird nicht genannt. Mache aus dem "
            "IB-Lab-Grad keine neue Diagnose (kein „Gonarthrose“, wenn sie nicht diktiert ist).")


def prompt_block(bausteine, vorlage=None, diktat=""):
    """<ibl_messwerte> für den Gen-Prompt — nur mit Bausteinen (sonst bleibt der Prompt bit-gleich). Ohne Zahlen und
    ohne Diagnosen: die KI soll nichts davon selbst schreiben, nur wissen, dass es ergänzt wird. vorlage = Text der
    Vorlage dieses Abschnitts: Sätze daraus, die einer IB-Lab-Diagnose widersprechen („Regelrechte Abbildung beider
    Pfannendächer.“ neben einer Hüftdysplasie), werden wörtlich als „weglassen“ genannt (live 13.10.: nur die Themen zu
    nennen reichte der KI beim Becken nicht)."""
    zeilen, koala = [], []
    for b in bausteine or []:
        if b.modul == "panda":             # 19.11.2026: KaiScribe setzt den Knochenalter-Ergebnisbefund selbst ein
            if panda_text(b):
                zeilen += [f"- {b.name}: Knochenalter-Ergebnisbefund (ersetzt Vorlagen-Sätze zu: {THEMEN['panda']}, Alter, "
                           "Körpergröße, Endgröße, Wachstumspotenzial)", PANDA_PROMPT]
            continue
        if b.modul == "koala":             # 18.11.2026: KaiScribe schreibt den femorotibialen Satz + Gonarthrose-Punkt selbst
            titel = (vorlage or "").split("\n")[0]
            if _koala_plan(b, titel, br.diktierte_seite(diktat), diktat, [], vorlage or "") is not None:
                koala.append(b)
                zeilen.append(f"- {b.name}: Satz zum femorotibialen Gelenkspalt (Kellgren & Lawrence, Kompartiment) und "
                              "Ergebnispunkt zur Gonarthrose")
            continue
        if _frog_text(b):                  # v3.19.8: KaiScribe ersetzt Stellungs- und Gewölbesatz der Vorlage selbst
            zeilen.append(f"- {b.name}: Sätze zu Zehenstellung und Fußgewölbe und die zugehörigen Diagnosen im Ergebnis")
            continue
        if _hippo_text(b):                 # v3.19.13: KaiScribe setzt die HIPPO-Sätze oben ein und gleicht die Vorlage an
            zeilen.append(f"- {b.name}: Sätze zu Beckenschiefstand, Beinlängendifferenz und auffälligen Hüftwinkeln (oben "
                          "in der Beschreibung) und die zugehörigen Diagnosen als erster Ergebnispunkt")
            continue
        if _squirrel_text(b):              # 20.11.2026: KaiScribe setzt Skoliose-Sätze bzw. Cobb-Winkel selbst ein
            zeilen.append(f"- {b.name}: " + ("Cobb-Winkel (die Krümmung hat der Arzt selbst diktiert)"
                                             if squirrel_diktiert(diktat) else
                                             "Sätze zur seitlichen Krümmung (Skoliose) mit Cobb-Winkel an der Stelle des "
                                             "Vorlagensatzes zur Achse und die Diagnose als erster Ergebnispunkt"))
            continue
        nur = b.modul in BEFUND_NUR_AUFFAELLIG | BEFUND_OHNE_ZEILEN
        namen = list(dict.fromkeys(m.name for m in map(messwert, befund_zeilen(b))
                                   if m and not (nur and _abschnitt_zeile(m.zeile))))
        if b.modul in ERGEBNIS_ZUERST and b.ergebnis:
            zeilen.append(f"- {b.name}: Ergebnispunkte zu Beinlängendifferenz und Beinachse (ersetzt Vorlagen-Sätze zu: "
                          f"{THEMEN.get(b.modul)})")
            continue
        if namen:
            # v3.18.8: bei „nur auffällige Werte“ ersetzen die Zeilen keine Vorlagen-Sätze zum ganzen Thema (die übrigen
            # Werte sind unauffällig und kommen nicht in den Befund); widersprechende Sätze nennt „weg“ unten wörtlich
            thema = None if nur else THEMEN.get(b.modul)
            zeilen.append(f"- {b.name}: " + ", ".join(namen) + (f" (ersetzt Vorlagen-Sätze zu: {thema})" if thema else ""))
    kl = [z for b in bausteine or [] if b not in koala for z in b.befundteil
          if "kellgren" in z.lower() and br.kl_grade(z)]
    if not zeilen and kl:
        # v3.18.8: KOALA ohne Regeltreffer – kein Messwert kommt in den Befund, den K&L-Grad muss die KI trotzdem kennen
        # (Grad zu einer DIKTIERTEN Arthrose, Regel ab 3.18.5)
        return ("<ibl_messwerte>\n"
                "Zu dieser Untersuchung liegen KI-Messwerte von IB Lab vor; sie sind unauffällig und kommen nicht in den "
                "Befund.\n" + _kl_satz(kl) + "\n"
                "Regeln: Nenne diese Messwerte nicht selbst und erfinde keine Zahlen. Leite aus ihnen KEINE Diagnose ab: "
                "ohne diktierte Arthrose kein „Arthrose“/„Gonarthrose“ und kein K&L-Grad.\n"
                "</ibl_messwerte>")
    if not zeilen:
        return ""
    weg = []
    for b in bausteine:
        if b.ergebnis and vorlage and not _frog_text(b) and not _hippo_text(b) and not _squirrel_text(b) \
                and b.modul not in ("koala", "panda"):
            weg += [s for s in _normalsaetze(b, vorlage.split("\n"), _pathologische_punkte(b, b.ergebnis)) if s not in weg]
    if kl:   # v3.18.4 (RH 38): den IB-Lab-Grad muss die KI kennen, um ihn statt eines eigenen zu übernehmen
        zeilen.append(_kl_satz(kl))
    if any(b.modul in ERGEBNIS_ZUERST and b.ergebnis for b in bausteine):
        zeilen.append(LAMA_PROMPT)
    if any(_frog_text(b) for b in bausteine):
        zeilen.append(FROG_PROMPT)
    if any(_hippo_text(b) for b in bausteine):
        zeilen.append(HIPPO_PROMPT)
    if any(_squirrel_text(b) for b in bausteine):
        zeilen.append(SQUIRREL_PROMPT)
    if koala:
        zeilen.append(KOALA_PROMPT)
    if weg:
        zeilen.append("Diese Sätze der Vorlage widersprechen den IB-Lab-Werten – nicht übernehmen (bzw. nur ohne die "
                      "widersprechende Aussage): " + " ".join(f"„{s}“" for s in weg))
    return ("<ibl_messwerte>\n"
            "Zu dieser Untersuchung liegen KI-Messwerte von IB Lab vor. KaiScribe fügt sie nach dem Befund automatisch "
            "und wörtlich ein:\n" + "\n".join(zeilen) + "\n"
            "Regeln: Nenne diese Messwerte nicht selbst und erfinde keine Zahlen. Widersprich ihnen nicht: Sätze der "
            "Vorlage zu den in Klammern genannten Themen lässt du weg (die Messwerte ersetzen sie), außer der Arzt hat "
            "dazu etwas diktiert. Was der Arzt selbst an Messwerten oder Diagnosen diktiert hat, übernimmst du genau wie "
            "diktiert. Leite aus diesen Messwerten KEINE Diagnose ab: Winkel, Offsets, Überdachung, Beckenschiefstand oder "
            "Beinlängendifferenz sind kein Hinweis auf eine Arthrose — ohne diktierte Arthrose kein „Arthrose“/„Coxarthrose“ "
            "und kein K&L-Grad.\n"
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
        return any(b.befundteil or b.ergebnis or frog_ohne_diagnose(b) for b in self.bausteine)


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


def _abschnitt_zeile(z):
    """„Fuß d.p.:“ / „Fuß seitlich rechts:“ — Abschnitts-Beschriftung des Abholers bei mehreren Aufnahmen eines Moduls."""
    z = (z or "").strip()
    return z.endswith(":") and "(" not in z and not re.search(r"\d", z)


def _punkt_traf(z, abschnitt, punkte, beschriftungen=()):
    """v3.18.8: Ist aus der Befundzeile z (unter der Beschriftung abschnitt) ein Ergebnispunkt geworden? Erst wörtlich
    (wie bis 3.18.7: „Calcaneusneigungswinkel 10°“ steht im Punkt), sonst Messgröße + Wert mit passender Seite – der
    Abholer schreibt im Punkt die Seite nicht in die Klammer („Mittelgradiger Hallux valgus rechts (Hallux-valgus-Winkel
    24,3°).“) bzw. fasst beide Seiten zusammen („… beidseits (Intermetatarsalwinkel I/II rechts 10°, links 10°).“).
    Bei mehreren Aufnahmen trägt der Punkt die Beschriftung („Fuß d.p.: …“) – dann nur Zeilen dieser Aufnahme."""
    m = messung_text(z)
    if not m or _abschnitt_zeile(z):
        return False
    mw = messwert(z)
    seiten = {s.lower() for s in _SEITE.findall(re.sub(r"\([^()]*\)\.?\s*$", "", z))}
    for p in punkte or []:
        titel, sep, rest = p.partition(": ")
        if sep and titel.strip() in beschriftungen:
            if titel.strip() != abschnitt:
                continue
            p = rest
        if m in p:
            return True
        if mw is None or not mw.wert or len(mw.name) < 3:
            continue
        i = p.find(mw.name)
        while i >= 0:
            nach = p[i + len(mw.name):]
            if nach[:1].isspace():
                teil = re.split(r"[;)]", nach, 1)[0]
                for f in _PUNKT_WERT.finditer(teil):
                    if not _wert_gleich(mw, f.group(2), f.group(3)):
                        continue
                    s = (f.group(1) or "").lower()
                    if s:
                        ok = not seiten or s in seiten or s == "beidseits"
                    else:                      # Seite steht vor der Klammer („… links (Hallux-valgus-Winkel 24°)“)
                        ps = {x.lower() for x in _SEITE.findall(p.split("(", 1)[0])}
                        ok = not seiten or not ps or bool(ps & (seiten | {"beidseits", "beidseitig", "bds"}))
                    if ok:
                        return True
            i = p.find(mw.name, i + 1)
    return False


_PUNKT_WERT = re.compile(r"(?:(rechts|links|beidseits)\s+)?(?<![\d,.])([+\-−]?\d+(?:[.,]\d+)?)(?![\d])\s*(°|mm|cm|%)?")


def _wert_gleich(mw, zahl, einheit):
    """Wert im Ergebnispunkt = Wert der Befundzeile? Zahlen numerisch (10° = 10,0°), Einheiten nur, wenn beide eine haben."""
    if mw.zahl is None:
        return mw.wert.strip() == f"{zahl}{einheit or ''}".strip()
    z = _zahl(zahl)
    if z is None:
        return False
    if mw.einheit and einheit and mw.einheit != einheit:
        return mw.einheit in _MM and einheit in _MM and _gleich(z, einheit, mw.zahl, mw.einheit)
    return z == mw.zahl


def _treffer(b):
    """Je Befundzeile des Bausteins: hat eine Regel daraus einen Ergebnispunkt gemacht? (Beschriftungen: False)"""
    out, abschnitt = [], None
    titel = {z.strip()[:-1].strip() for z in b.befundteil if _abschnitt_zeile(z)}
    for z in b.befundteil:
        if _abschnitt_zeile(z):
            abschnitt = z.strip()[:-1].strip()
            out.append(False)
        else:
            out.append(_punkt_traf(z, abschnitt, b.ergebnis, titel))
    return out


# v3.18.8 (Peter 12.11.2026, Foto „Fuß beidseits in 2 Ebenen“: „Das ist viel zu viel für den Befund. Bitte nur die
# pathologischen Maße in den Befund eintragen.“ – Nachtrag: HIPPO und KOALA ebenso): Für diese Module kommen nur die
# Messzeilen in den Befund (Gerüst und Einsetzen nach der KI), aus denen eine aktive Regel des Abholers (ris-mods
# ibl/regeln/<modul>.toml) einen Ergebnispunkt gemacht hat. Ergebnispunkte unverändert und vollständig; alle Werte
# bleiben in den IB-Lab-Details sichtbar. Kein Treffer → keine Befundzeile und kein erfundener Normalsatz (die Regeln
# decken nicht alle Messgrößen ab). IB Labs eigene „Abnormally High/Low“-Flags zählen hier NICHT. Weitere Module: hier
# eintragen.
BEFUND_NUR_AUFFAELLIG = {"frog", "hippo", "koala"}

# IB Lab LAMA (Georg Riegler 17.11.2026, Brief kaiscribe-lama-ergebnistext-n1): der Abholer (ris-mods ibl/lama_ergebnis.py)
# liefert einen FERTIGEN Ergebnistext – nur Ergebnis, keine Beschreibung. Darum: keine LAMA-Befundzeilen in den Befund
# (alle Werte bleiben in den IB-Lab-Details), die LAMA-Punkte stehen als ERSTE Punkte im Ergebnis, diktierte Befunde
# folgen als nächste Punkte, die Schlussanmerkung („HKA = Hüft-Knie-Sprunggelenk-Winkel, …“) steht ohne Nummer ganz
# unten (befund_regeln._UNNUM_RE). Ein Normalsatz der KI/Vorlage zur Beinachse („Regelrechte Darstellung der
# Beinachsen.“) wird durch das LAMA-Ergebnis ersetzt, außer der Arzt hat zur Achse/Beinlänge etwas diktiert. Ohne Diktat
# (sofort EOL) ist das Gerüst damit der fertige Befund.
BEFUND_OHNE_ZEILEN = {"lama"}
ERGEBNIS_ZUERST = {"lama"}
LAMA_SCHLUSS = "HKA = Hüft-Knie-Sprunggelenk-Winkel"
LAMA_PROMPT = ("LAMA: Schreibe zu Beinachse und Beinlänge weder im Befund noch im Ergebnis etwas – auch keinen Normalsatz "
               "wie „Regelrechte Darstellung der Beinachsen.“ –, außer der Arzt hat dazu etwas diktiert. KaiScribe setzt "
               "das IB-Lab-Ergebnis als erste Ergebnispunkte ein; diktierte Befunde folgen danach.")
_LAMA_THEMA = re.compile(r"achse|beinläng|beinlaeng|darstellung", re.I)
_LAMA_DIKTAT = re.compile(r"achse|beinläng|beinlaeng|varus|valgus|varisch|valgisch|x-bein|o-bein|genu", re.I)
_LAMA_NORMAL = re.compile(r"^(?:Keine Beinlängendifferenz|Regelrechte Beinachse|Beidseits regelrechte Beinachse)")


# kaiscribe-georg-2011-n1 (Georg 20.11.2026, Punkt 9/25/26d): Winkel-Erläuterungen (LAMA/FROG/HIPPO-Schlussanmerkung, „Weitere
# Winkelmessungen …“) stehen als eigener Block „Anmerkung: …“ mit einer Leerzeile davor am Ende des Ergebnisses.
ANMERKUNG = "Anmerkung: "
_ANMERKUNG = re.compile(r"^\s*Anmerkung:\s*")


def _ohne_anmerkung(punkt):
    return _ANMERKUNG.sub("", _NUM.sub("", (punkt or "").strip()))


def ist_lama_schluss(punkt):
    return _ohne_anmerkung(punkt).startswith(LAMA_SCHLUSS)


def ist_schluss(punkt):
    """Schlussanmerkung von LAMA, FROG oder HIPPO – steht ohne Nummer ganz unten im Ergebnis (befund_regeln._UNNUM_RE)."""
    t = _ohne_anmerkung(punkt)
    return ist_lama_schluss(punkt) or t.startswith(FROG_SCHLUSS) or t.startswith(HIPPO_SCHLUSS)


def _pathologische_punkte(b, punkte):
    """Ergebnispunkte, gegen die Normalsätze im Befund als Widerspruch gelten (LAMA: ohne Normal-Punkte und
    Schlussanmerkung – „Regelrechte Beinachse rechts …“ widerspricht keinem Normalsatz)."""
    if b.modul not in ERGEBNIS_ZUERST:
        return punkte
    out = []
    for p in punkte:
        if ist_lama_schluss(p):
            continue
        saetze = [s for s in re.split(r"(?<=\))\.\s+", p) if s.strip()]
        if not all(_LAMA_NORMAL.match(s.strip()) for s in saetze):
            out.append(p)
    return out


def _lama_ergebnis_pruefen(b, bericht, diktat, hinweise):
    """LAMA: alle Punkte kommen (auch wenn das KI-Ergebnis unauffällig ist); Doppelung/Widerspruch nur gegen das Diktat
    (der KI-Text zur Achse wird ersetzt); ein Punkt, der wörtlich schon dasteht (dieselbe Fassung noch einmal), kommt nicht
    doppelt. Die Schlussanmerkung kommt immer mit, wenn ein Punkt kommt."""
    out = []
    for p in b.ergebnis:
        if ist_lama_schluss(p) or p in (bericht or ""):
            continue
        art, wort = _diagnose_im_text(p, "", diktat)
        if art == "doppelt":
            hinweise.append(f"{b.name}: „{_kurz(p)}“ – schon diktiert, nicht doppelt angefügt")
        elif art == "widerspruch":
            hinweise.append(f"{b.name}: „{_kurz(p)}“ – Diktat verneint „{wort}“, bitte prüfen (nicht angefügt)")
        else:
            if art == "verwandt":
                hinweise.append(f"{b.name}: „{_kurz(p)}“ angefügt – Diktat nennt schon „{wort}“, bitte prüfen")
            out.append(p)
    if out:
        out += [p for p in b.ergebnis if ist_lama_schluss(p)]
    return out


def _ergebnis_vorne(zeilen, a, punkte, diktat, b, hinweise):
    """LAMA: IB-Lab-Punkte als ERSTE Punkte des Ergebnisses von a, die übrigen (diktierten) danach, Schlussanmerkung
    ganz unten ohne Nummer; neu durchgezählt (ein Punkt: ohne Nummer). Ein KI-Normalsatz zu Beinachse/Beinlänge
    („Regelrechte Darstellung der Beinachsen.“) entfällt, wenn das Diktat nichts dazu sagt. → Zeilen mehr."""
    schluss = [p for p in punkte if ist_schluss(p)]
    vorne = [p for p in punkte if not ist_schluss(p)]
    frog = _frog_text(b)
    if a.ergebnis < 0:
        return _ergebnis_anfuegen(zeilen, a, vorne + schluss)
    s, k = a.ergebnis + 1, a.ende
    while k > s and not zeilen[k - 1].strip():
        k -= 1
    inhalt = zeilen[s:k]
    rest = []
    for z in inhalt:
        if not z.strip():
            continue
        t = _NUM.sub("", z).strip()
        if ist_schluss(t):
            continue
        if frog:
            # FROG (Georg 17.11.2026): derselbe Punkt nie doppelt; der Standard-Ergebnissatz zum Fuß entfällt, sobald ein
            # Begriff eingesetzt wird („… des oberen Sprunggelenkes und des Fußskeletts.“ behält das Sprunggelenk)
            if t in vorne:
                continue
            if vorne and z[:1] not in (" ", "\t"):
                m = _FROG_ERG_UND.match(t)
                if m:
                    hinweise.append(f"{b.name}: „{_kurz(t)}“ gekürzt – Fuß laut IB Lab auffällig")
                    rest.append(m.group(1) + m.group(2) + ".")
                    continue
                if ergebnis_normal([t]) and _FROG_ERG_NORMAL.search(t):
                    hinweise.append(f"{b.name}: „{_kurz(t)}“ durch das IB-Lab-Ergebnis ersetzt")
                    continue
            rest.append(z)
            continue
        if z[:1] not in (" ", "\t") and ergebnis_normal([t]) and _LAMA_THEMA.search(t) \
                and not _LAMA_DIKTAT.search(diktat or ""):
            hinweise.append(f"{b.name}: „{_kurz(t)}“ durch das IB-Lab-Ergebnis ersetzt")
            continue
        rest.append(z)
    neu = br.ergebnis_nummerieren("## Ergebnis\n" + "\n".join(vorne + rest + schluss)).split("\n")[1:]
    zeilen[s:k] = neu
    return len(neu) - len(inhalt)


# IB Lab FROG (Georg Riegler 17.11.2026, Brief kaiscribe-frog-fusstext-n1): der Abholer ≥ 1.3.7 (ris-mods
# ibl/frog_ergebnis.py) liefert im Feld „befundtext“ fertige Sätze für die Beschreibung und die lateinischen Begriffe fürs
# Ergebnis – nur wenn mindestens eine Größe pathologisch ist. KaiScribe setzt sie in den Standardbefund ein:
#   Fuß / Sprunggelenk mit Fuß: der Stellungssatz („Das Fußskelett ist nach Form, Größe, Anzahl und Stellung … normal.“)
#     entfällt, an seiner Stelle stehen die Stellungs-Sätze; der Gewölbesatz („Das Fußgewölbe ist regulär ausgebildet bei
#     ordnungsgemäßen Gelenkwinkeln.“) wird durch die Gewölbe-Sätze ersetzt (Gewölbe normal: „Das Fußgewölbe ist regulär
#     ausgebildet.“, widersprüchliche Winkel: ersatzlos gestrichen).
#   Vorfuß: nur d.p. – der Phalangen-Satz („Die Stellung der Phalangen … ist ordnungsgemäß.“) entfällt bei Hallux valgus
#     oder Digitus quintus varus; sonst stehen die Sätze dahinter. Kein Gewölbe-Text, keine Gewölbe-Begriffe.
#   Ergebnis: die Begriffe als ERSTER Punkt („Hochgradiger Hallux valgus links. Pes cavus links.“), der Standardsatz
#     („Regelrechte Darstellung des Fußskeletts.“) entfällt, Diktiertes folgt als nächster Punkt, die Schlussanmerkung
#     („Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.“) steht ohne Nummer ganz unten.
#   Keine Messzeilen mehr („… (IB Lab FROG).“) – alle Werte bleiben in den IB-Lab-Details und KI-Bildern.
# Am Diktat wird nichts geändert: ein schon diktierter Begriff kommt nicht doppelt, verneint das Diktat einen Begriff,
# kommt aus dieser Projektion nichts (Hinweis nur in der Anzeige). Findet sich der Satz der Vorlage nicht mehr (der Arzt
# hat dazu diktiert), stehen die FROG-Sätze als eigener Absatz am Ende der Beschreibung + Hinweis. Ohne „befundtext“
# (Abholer < 1.3.7, nichts pathologisch) bleibt alles wie bis 3.19.7.
FROG_SCHLUSS = "Weitere Winkelmessungen sind den KI-Auswertungsbildern"
FROG_PROMPT = ("FROG: Übernimm die Vorlagen-Sätze „Das Fußskelett ist nach Form, Größe, Anzahl und Stellung … normal.“, „Die "
               "Stellung der Phalangen … ist ordnungsgemäß.“ und „Das Fußgewölbe ist regulär ausgebildet bei "
               "ordnungsgemäßen Gelenkwinkeln.“ wörtlich und unverändert, außer der Arzt hat dazu etwas diktiert – "
               "KaiScribe ersetzt sie nach dem Befund durch die IB-Lab-Sätze. Schreibe selbst keinen Satz und keine "
               "Diagnose zur Stellung der Groß- und Kleinzehe oder zum Längsgewölbe, außer der Arzt hat es diktiert.")
# kaiscribe-frog-einsetzen-n1 (RH 127, Fuß beidseits): bei beidseitiger CAS-Leistung schreibt die KI „wo nötig beidseits“
# in die Normalsätze (cas_vorlagen.beidseits_block) – „Das Fußskelett ist beidseits nach Form …“ muss ebenso ersetzt werden.
_BDS = r"(?: (?:beidseits|beidseitig|jeweils))?"
_FROG_STELLUNG = re.compile(r"(?:Das Fu(?:ß|ss)skelett|Die Fu(?:ß|ss)skelette)" + _BDS + r" (?:ist|sind)" + _BDS
                            + r" nach Form[^.\n]*?Stellung[^.\n]*\.")
_FROG_PHALANGEN = re.compile(r"Die Stellung der Phalangen[^.\n]*?ist" + _BDS + r" ordnungsgemäß\.")
_FROG_GEWOELBE = re.compile(r"(?:Das Fu(?:ß|ss)gewölbe|Die Fu(?:ß|ss)gewölbe)" + _BDS + r" (?:ist|sind)" + _BDS
                            + r" regulär ausgebildet(?: bei ordnungsgemäßen Gelenkwinkeln)?\.")
_FROG_GEW_NORMAL = re.compile(r"^Das Fu(?:ß|ss)gewölbe (?:(?:rechts|links) )?ist regulär ausgebildet\.$")
_FROG_GEW_SATZ = re.compile(r"(?:Erhöhtes|Abgeflachtes) Längsgewölbe|Das Fu(?:ß|ss)gewölbe")
_FROG_ERG_UND = re.compile(r"^(Regelrechte Darstellung\b.*?) und des Fu(?:ß|ss)skeletts"
                           r"((?:\s+(?:rechts|links|beidseits))?)\.?$")
_FROG_ERG_NORMAL = re.compile(r"darstellung\b.*fu(?:ß|ss)|^(?:(?:unauffälliger|regelrechter|altersentsprechender)\s+)?"
                              r"(?:normalbefund|befund)\.?$", re.I)
_VORFUSS = re.compile(r"vorfu(?:ß|ss)", re.I)
_FROG_MARKE = {"s": "\x01FROG-S\x01", "g": "\x01FROG-G\x01"}


def _frog_text(b):
    """FROG-Baustein mit fertigem Text des Abholers (≥ 1.3.7)?"""
    return b.modul == "frog" and b.befundtext is not None


def frog_ohne_diagnose(b):
    """NACHTRAG ibl-georg-2011-n1 (Abholer 1.3.14, RH 30): FROG ohne Diagnose, nur Messwert-Sätze?"""
    return _frog_text(b) and bool(b.befundtext.get("ohne_diagnose"))


def _frog_plan(b, titel, seite, diktat, hinweise):
    """FROG-Text für EINE Untersuchung → (Stellungs-Sätze, Gewölbe-Sätze, Gewölbesatz streichen, Ergebnispunkt,
    Schlussanmerkung) oder None (nichts einsetzen). Vorfuß: nur d.p. Ein Fuß ohne Seite im Begriff: Seite aus dem Titel
    der Untersuchung. Diktat: ein schon diktierter Begriff kommt nicht doppelt ins Ergebnis (die Sätze mit den Winkeln
    kommen trotzdem); verneint das Diktat einen Begriff, kommt aus dieser Projektion nichts (Hinweis)."""
    bt = b.befundtext
    vorfuss = bool(_VORFUSS.search(titel or ""))
    if bt.get("ohne_diagnose"):              # RH 30: nur die Messwerte (Vorfuß: nur d.p.), Vorlagensätze bleiben
        mw = [m for m in bt["messwerte"] if not vorfuss or not re.search(r"seitlich", m, re.I)]
        return (mw, [], False, "", bt["schluss"]) if mw else None
    if seite not in ("rechts", "links"):     # Titel ohne Seite: die Seite des Bausteins (genau ein Fuß)
        seite = b.seiten[0] if len(b.seiten) == 1 else ""
    texte, aktiv, verneint = [], set(), set()
    for x in bt["begriffe"]:
        if vorfuss and x["art"] != "dp":
            continue
        s = x["seite"] or (seite if bt["ein_fuss"] and seite in ("rechts", "links") else "")
        t = f"{x['text']} {s}".strip()
        art, wort = _diagnose_im_text(x["text"], "", diktat or "")
        if art == "widerspruch":
            hinweise.append(f"{b.name}: „{_kurz(t)}“ – Diktat verneint „{wort}“, bitte prüfen (nicht eingesetzt)")
            verneint.add(x["art"])
            continue
        aktiv.add(x["art"])
        if art == "doppelt":
            hinweise.append(f"{b.name}: „{_kurz(t)}“ – schon diktiert, nicht doppelt angefügt")
            continue
        if art == "verwandt":
            hinweise.append(f"{b.name}: „{_kurz(t)}“ angefügt – Diktat nennt schon „{wort}“, bitte prüfen")
        texte.append((x["art"], t))
    aktiv -= verneint
    if not aktiv:
        return None
    stellung = list(bt["stellung"]) if "dp" in aktiv else []
    if vorfuss or "gewoelbe" in verneint:
        gewoelbe, weg = [], False
    elif "gewoelbe" in aktiv or not bt["gewoelbe_weg"]:
        gewoelbe, weg = list(bt["gewoelbe"]), False
    else:
        gewoelbe, weg = [], True
    return stellung, gewoelbe, weg, " ".join(t + "." for art, t in texte if art in aktiv), bt["schluss"]


def _frog_punkte(plan):
    return ([plan[3]] if plan[3] else []) + ([plan[4]] if plan[4] else [])


def _frog_zeilen(plan, punkte=True):
    """Sätze je Zeile (Gerüst, Absatz am Ende): die Stellungs-Sätze und – nur wenn das Gewölbe pathologisch ist – die
    Gewölbe-Sätze; mit punkte=True dazu Ergebnispunkt und Schlussanmerkung."""
    gw = plan[1] if any(not _FROG_GEW_NORMAL.match(s) for s in plan[1]) else []
    return plan[0] + gw + (_frog_punkte(plan) if punkte else [])


def _satz_raus(text, start, ende, neu=""):
    """text[start:ende] durch neu ersetzen bzw. samt einem Leerzeichen (und einer dadurch leeren Zeile) herausnehmen."""
    if neu:
        return text[:start] + neu + text[ende:]
    vor, nach = text[:start], text[ende:]
    if nach[:1] == " ":
        nach = nach[1:]
    elif vor[-1:] == " ":
        vor = vor[:-1]
    if (not vor or vor.endswith("\n")) and nach[:1] == "\n":
        nach = nach[1:]
    elif not nach and vor.endswith("\n"):
        vor = vor[:-1]
    return vor + nach


def _frog_befund(block, st, gw, weg, phalangen, alte):
    """Beschreibung einer Untersuchung (Text ohne Überschriften) → (neuer Text, Sätze ohne Platz in der Vorlage).
    alte: Sätze einer früheren Fassung bzw. derselben (noch einmal eingesetzt) – ihre Stelle gilt wie der Vorlagensatz."""
    for satz in dict.fromkeys(alte):
        art = "g" if _FROG_GEW_SATZ.match(satz) else "s"
        while satz and satz in block:
            i = block.index(satz)
            block = _satz_raus(block, i, i + len(satz), "" if _FROG_MARKE[art] in block else _FROG_MARKE[art])
    rest, neu_st, neu_gw = [], " ".join(st), " ".join(gw)
    m = _FROG_STELLUNG.search(block)
    p = _FROG_PHALANGEN.search(block) if m is None else None
    if m:
        block = _satz_raus(block, m.start(), m.end(), neu_st)
    elif p and phalangen:
        block = _satz_raus(block, p.start(), p.end(), neu_st)
    elif p and neu_st:
        block = block[:p.end()] + " " + neu_st + block[p.end():]
    elif _FROG_MARKE["s"] in block:
        i = block.index(_FROG_MARKE["s"])
        block = _satz_raus(block, i, i + len(_FROG_MARKE["s"]), neu_st)
    else:
        rest += st
    m = _FROG_GEWOELBE.search(block)
    if m:
        if weg or neu_gw:
            block = _satz_raus(block, m.start(), m.end(), "" if weg else neu_gw)
    elif _FROG_MARKE["g"] in block:
        i = block.index(_FROG_MARKE["g"])
        block = _satz_raus(block, i, i + len(_FROG_MARKE["g"]), "" if weg else neu_gw)
    elif any(not _FROG_GEW_NORMAL.match(s) for s in gw):
        rest += gw
    for marke in _FROG_MARKE.values():
        while marke in block:
            i = block.index(marke)
            block = _satz_raus(block, i, i + len(marke))
    return block, rest


def _frog_einsetzen(zeilen, teile, i, b, e):
    """FROG-Text in die Untersuchung teile[i] einsetzen (Beschreibung: Sätze an die Stelle der Vorlagensätze, Ergebnis:
    Begriffe zuerst, Schlussanmerkung unten). Hinweise, eingesetzte Zeilen und Zuordnung nach e."""
    a = teile[i]
    plan = _frog_plan(b, a.titel, a.seite, a.segment, e.hinweise)
    for mw in map(messwert, b.befundteil):   # ein abweichend DIKTIERTER Winkel bleibt ein Hinweis (nichts wird geändert)
        if mw is not None and not _abschnitt_zeile(mw.zeile):
            art, gefunden = im_text(mw, a.segment or "")
            if art == "anders":
                e.hinweise.append(f"{b.name}: {mw.name} diktiert {gefunden}, laut IB Lab {mw.wert} – bitte prüfen")
    if plan is None:
        return
    st, gw, weg, _punkt, _schluss = plan
    punkte = _frog_punkte(plan)
    if b.befundtext.get("ohne_diagnose"):    # RH 30: Messwerte als Absatz ans Ende der Beschreibung, nur die Anmerkung
        da = "\n".join(zeilen[a.start:a.ende])
        neu = [m for m in st if m not in da]
        if neu:
            _verschieben(teile, i, _befund_anfuegen(zeilen, a, neu))
        if punkte:
            _verschieben(teile, i, _ergebnis_vorne(zeilen, a, punkte, a.segment, b, e.hinweise), nur_ende=True)
        da = "\n".join(zeilen[a.start:a.ende])
        e.eingesetzt[b.schluessel] = [m for m in st if m in da] + punkte
        e.zuordnung[b.modul] = a.titel or "Befund"
        return
    bs = (a.befund if a.befund >= 0 else a.start) + 1
    be = a.ergebnis if a.ergebnis >= 0 else a.ende
    alt = "\n".join(zeilen[bs:be])
    ersetzt = [z for z in e.nicht_entfernt if z and z in alt]        # Sätze einer älteren Fassung (mitten im Absatz)
    block, rest = _frog_befund(alt, st, gw, weg, b.befundtext["phalangen"], ersetzt + st + gw)
    e.nicht_entfernt = [z for z in e.nicht_entfernt if z not in ersetzt]
    if block != alt:
        neu = block.split("\n")
        zeilen[bs:be] = neu
        _verschieben(teile, i, len(neu) - (be - bs))
    if rest:
        if block.strip():
            e.hinweise.append(f"{b.name}: Satz der Vorlage zu Zehenstellung/Fußgewölbe nicht gefunden – IB-Lab-Sätze "
                              "am Ende der Beschreibung, bitte prüfen")
        _verschieben(teile, i, _befund_anfuegen(zeilen, a, rest))
    if punkte:
        _verschieben(teile, i, _ergebnis_vorne(zeilen, a, punkte, a.segment, b, e.hinweise), nur_ende=True)
    da = "\n".join(zeilen[a.start:a.ende])
    e.eingesetzt[b.schluessel] = [s for s in dict.fromkeys(st + gw) if s in da] + punkte
    e.zuordnung[b.modul] = a.titel or "Befund"


# ───────────────────────────── IB Lab KOALA: Kniebefund nach der K&L-Tabelle ─────────────────────────────
# Georg Riegler 18.11.2026 (GO, Brief kaiscribe-kl-tabelle-zurueck-n1): KOALA → Knie-Vorlage (kniegelenk_in_2_ebenen /
# _mit_patella_axial), nur das a.p.-Ergebnis (der Abholer liefert nur a.p./p.a.-Werte, je Seite aus einer Aufnahme),
# Seite aus Bild/Messlage. Keine Messzeilen und keine mm-Werte im Text.
#   - Kein KOALA-Text: Alter < 18, Prothese (Vorlage/Überschrift/Diktat), seitliche/axiale Bilder, KL 0/1 (Vorlage bleibt),
#     Diktat nennt selbst eine Gonarthrose bzw. einen K&L-Grad (Diktat geht immer vor – Hinweis bei anderem Grad).
#   - KL 2–4: Kompartiment = das mit dem engeren Gelenkspalt (minimale Gelenkspaltweite medial vs. lateral); es bekommt den
#     Satz der K&L-Tabelle (befund_regeln.KL_TABELLE) mit vorangestelltem „Medial“/„Lateral“, das andere „Lateral normal
#     weiter Gelenkspalt.“ bzw. „Medial …“ – an der Stelle von „Der Gelenkspalt ist allseits normal weit.“. Nie „betont“.
#     „Die Gelenkflächen sind normal geformt und kongruent.“ entfällt, „Normale Form und Stellung der dargestellten
#     Skelettabschnitte.“ → „Normale Stellung der dargestellten Skelettabschnitte.“ (Regel 2).
#   - Ergebnis: ERSTER Punkt „Mäßiggradige Gonarthrose links medial (Arthrose Grad 3 nach Kellgren & Lawrence).“; beide
#     Seiten gleich → „… beidseits medial …“; das Normal-Ergebnis des Knies entfällt. Diktiertes (Femoropatellararthrose,
#     Erguss) schreibt die KI nach den Prompt-Regeln.
#   - Mehrere a.p.-Bilder einer Seite mit verschiedenen Graden → kein Text, Prüf-Hinweis.
KOALA_STELLUNG = "Normale Stellung der dargestellten Skelettabschnitte."
KOALA_PROMPT = ("KOALA: KaiScribe setzt nach dem Befund selbst den Satz zum femorotibialen Gelenkspalt (Grad und Kompartiment "
                "laut IB Lab, Wortlaut der K&L-Tabelle) und den Ergebnispunkt zur Gonarthrose ein und gleicht „Normale Form "
                "und Stellung der dargestellten Skelettabschnitte.“ und „Die Gelenkflächen sind normal geformt und "
                "kongruent.“ an. Übernimm „Der Gelenkspalt ist allseits normal weit.“ wörtlich und schreibe selbst KEINEN "
                "Satz, KEINE Diagnose und KEINEN Kellgren-&-Lawrence-Grad zur Gonarthrose bzw. zum femorotibialen "
                "Gelenkspalt. Der IB-Lab-Grad gilt nur femorotibial: eine diktierte Femoropatellararthrose bekommt den Grad "
                "zu ihrem diktierten Grad-Adjektiv. Andere diktierte Befunde (z.B. Femoropatellararthrose, Gelenkerguss) "
                "schreibst du wie gewohnt; ohne weitere diktierte Pathologie steht im Ergebnis das Normal-Ergebnis "
                "(KaiScribe ersetzt es).")
_KOALA_KL = re.compile(r"kellgren", re.I)
_KOALA_JSW = re.compile(r"gelenkspaltweite\s+(medial|lateral)", re.I)
_KOALA_NICHT_AP = re.compile(r"seitl|axial", re.I)
_PROTHESE = re.compile(r"prothes|\btep\b|endoprothes|schlittenprothes", re.I)
_KNIE_TITEL = re.compile(r"\bknie", re.I)
_DEFILEE = re.compile(r"defilee|patella\s+in\s+\d", re.I)
_KOALA_DIKTAT_ARTHROSE = re.compile(r"[\wäöüß-]*(?:th?ros|rthrot|rtrot)[\wäöüß]*", re.I)
_KNIE_SPALT = re.compile(r"(?:Der Gelenkspalt ist |(?:Im Übrigen|Ansonsten),? ist der Gelenkspalt )"
                         r"(?:(?:im Übrigen|ansonsten|sonst|femorotibial|beidseits|allseits)\s+){0,3}normal weit\.")
# Femoropatellar-Satz der KI (Tabellensatz): steht in Georgs Wortlaut HINTER dem femorotibialen Satz
_FP_SATZ = re.compile(r"(?:Femoropatellar (?:(beidseits|rechts|links) )?|(Beidseits|Rechts|Links) femoropatellar )"
                      r"((?:geringe|mäßiggradige|aufgehobener)[^.]*\.)\s?")


def _fp_form(m):
    """„Beidseits femoropatellar …“ → Georgs Form „Femoropatellar beidseits …“."""
    s = (m.group(1) or m.group(2) or "").lower()
    return f"Femoropatellar {s + ' ' if s else ''}{m.group(3)}"
_KNIE_FLAECHEN = re.compile(r"(?:Die Gelenkflächen sind (?:im Übrigen |ansonsten )?|(?:Im Übrigen|Ansonsten) sind die "
                            r"Gelenkflächen )normal geformt und kongruent\.")
# Weichteil-/Erguss-Satz, den die KI als eigenen Absatz setzt – die Knie-Vorlage ist EIN Absatz (Georg Nr. 34)
_KNIE_WT_ABSATZ = re.compile(r"\n\s*\n((?:[^.\n]*Gelenkergu(?:ss|ß)[^.\n]*\.\s*)?(?:Ansonsten u|U)nauffällige Weichteile\.)\s*$")
_KNIE_FORM = re.compile(r"(?:Im Übrigen n|Ansonsten n|N)ormale (?:Form und )?Stellung der dargestellten "
                        r"Skelettabschnitte(?: (?:beidseits|rechts|links))?\.")
# Femoropatellar-Punkt der KI („Mäßige patellofemorale Arthrose beidseits (Arthrose Grad 3 …)“) → Georgs Form
# „Mäßiggradige Femoropatellararthrose beidseits (Arthrose Grad 3 nach Kellgren & Lawrence).“ (Fixture Nr. 34/50)
_FP_PUNKT = re.compile(r"^(?:[A-Za-zÄÖÜäöüß-]+\s+)?(?:(?:patellofemoral|femoropatellar)(?:e|er|en)?\s+arthrose|"
                       r"femoropatellararthrose|patellofemoralarthrose)(?=\s)", re.I)
_KNIE_ANKER = [re.compile(r"Femoropatellar(?:er)?\s"), re.compile(r"Kein Hinweis auf freie Gelenkkörper\."),
               re.compile(r"Keine intra- oder periartikulären Verkalkungen\.")]
_ANDERES = {"medial": "Lateral", "lateral": "Medial"}


def _koala_werte(b):
    """KOALA-Befundzeilen → {Seite: {"kl": {Grad, …}, "medial": mm, "lateral": mm}} („“ = ohne Seite). Zeilen unter einer
    Beschriftung „… seitlich:“/„… axial:“ zählen nie (nur a.p.)."""
    out, abschnitt = {}, ""
    for z in b.befundteil:
        if _abschnitt_zeile(z):
            abschnitt = z
            continue
        if _KOALA_NICHT_AP.search(abschnitt):
            continue
        rumpf = re.sub(r"\s*\([^()]*\)\.?\s*$", "", z)
        s = {x.lower() for x in _SEITE.findall(rumpf)}
        seite = "rechts" if s == {"rechts"} else "links" if s == {"links"} else ""
        w = out.setdefault(seite, {"kl": set(), "medial": None, "lateral": None})
        if _KOALA_KL.search(rumpf):
            w["kl"].update(int(g) for g in br.kl_grade(rumpf))
            continue
        m = _KOALA_JSW.search(rumpf)
        mw = messwert(z)
        if m and mw is not None and mw.zahl is not None:
            k = m.group(1).lower()
            w[k] = mw.zahl if w[k] is None else min(w[k], mw.zahl)
    return out


def _koala_gonarthrose_diktiert(diktat):
    """Nennt das Diktat selbst eine femorotibiale Gonarthrose/Kniearthrose oder einen K&L-Grad? (Femoropatellar-,
    Retropatellar- und patellofemorale Arthrose zählen nicht – die schreibt die KI daneben.)"""
    if br.kl_grade(diktat):
        return True
    for m in _KOALA_DIKTAT_ARTHROSE.finditer(diktat or ""):
        davor = (diktat or "")[max(0, m.start() - 25):m.start()]
        if br._FEMOROPATELLAR.search(m.group(0)) or re.search(r"(?:patell|femoropat)\w*\s*$", davor, re.I):
            continue
        return True
    return False


def _koala_sperre(b, titel, diktat, vorlage=""):
    """Grund, warum kein KOALA-Text kommt (Alter, Prothese, keine Knie-Untersuchung) – sonst ""."""
    if b.alter is not None and b.alter < 18:
        return f"Patient {b.alter} Jahre (unter 18)"
    if _PROTHESE.search(f"{titel or ''}\n{vorlage or ''}\n{diktat or ''}"):
        return "Knieprothese"
    if titel and (not _KNIE_TITEL.search(titel) or _DEFILEE.search(titel)):
        return f"Untersuchung „{_kurz(titel, 40)}“ ist kein Kniegelenk a.p."
    return ""


def _koala_plan(b, titel, seite, diktat, hinweise, vorlage=""):
    """KOALA-Text für EINE Knie-Untersuchung → (Befundsätze, Ergebnispunkte) oder None (nichts einsetzen, ggf. Hinweis)."""
    if b.modul != "koala":
        return None
    werte = _koala_werte(b)
    if not any(w["kl"] for w in werte.values()):
        return None
    sperre = _koala_sperre(b, titel, diktat, vorlage)
    if sperre:
        if any(g >= 2 for w in werte.values() for g in w["kl"]):
            hinweise.append(f"{b.label}: kein KOALA-Text ({sperre})")
        return None
    if seite == "beidseits" or (seite not in ("rechts", "links") and set(b.seiten) == {"rechts", "links"}):
        seiten = ["rechts", "links"]
    elif seite in ("rechts", "links"):
        seiten = [seite]
    else:
        seiten = list(b.seiten) or [""]
    je = []
    for s in seiten:
        w = werte.get(s) or (werte.get("") if len(seiten) == 1 else None)
        if w is None and s == "" and len(werte) == 1:
            w = next(iter(werte.values()))
        if not w or not w["kl"]:
            je.append((s, None, None))
            continue
        if len(w["kl"]) > 1:
            hinweise.append(f"⚠ {b.name} {s}: verschiedene Kellgren-Lawrence-Grade ({', '.join(map(str, sorted(w['kl'])))}) "
                            "aus mehreren a.p.-Aufnahmen – kein KOALA-Text, bitte am Bild prüfen".replace("  ", " "))
            return None
        g = next(iter(w["kl"]))
        k = None
        if g >= 2:
            med, lat = w["medial"], w["lateral"]
            if med is not None and lat is not None and med != lat:
                k = "medial" if med < lat else "lateral"
            else:
                hinweise.append(f"{b.name} {s}: Kompartiment aus dem Gelenkspalt nicht bestimmbar – KOALA-Text ohne "
                                "medial/lateral, bitte prüfen".replace("  ", " "))
        je.append((s, g, k))
    if _koala_gonarthrose_diktiert(diktat):     # Diktat geht immer vor
        kl = sorted({str(g) for _s, g, _k in je if g is not None})
        diktiert = br.kl_grade(diktat) or br.kl_adjektiv_grade(diktat)
        if diktiert and kl and set(diktiert) != set(kl):
            hinweise.append(f"{b.name}: Kellgren-Lawrence-Grad diktiert {', '.join(diktiert)}, laut IB Lab "
                            f"{', '.join(kl)} – der diktierte Grad gilt (kein KOALA-Text), bitte prüfen")
        elif any(g is not None and g >= 2 for _s, g, _k in je):
            hinweise.append(f"{b.name}: Gonarthrose schon diktiert – KOALA-Text nicht eingesetzt (Diktat geht vor)")
        return None
    if not any(g is not None and g >= 2 for _s, g, _k in je):
        return None                             # KL 0/1: Vorlage unverändert
    return _koala_saetze(je)


def _klein(satz):
    return satz[:1].lower() + satz[1:]


def _koala_saetze(je):
    """[(Seite, Grad|None, Kompartiment|None)] → (Befundsätze, Ergebnispunkte)."""
    tab, adj = br.KL_TABELLE, br.KL_ADJEKTIV
    aktiv = [x for x in je if x[1] is not None and x[1] >= 2]
    if len(je) == 2 and len(aktiv) == 2 and aktiv[0][1:] == aktiv[1][1:]:
        g, k = aktiv[0][1], aktiv[0][2]
        befund = [f"Beidseits {k} {_klein(tab[g])}" if k else f"Beidseits {_klein(tab[g])}"]
        if k:
            befund.append(f"{_ANDERES[k]} beidseits normal weiter Gelenkspalt.")
        return befund, [f"{adj[g]} Gonarthrose beidseits{' ' + k if k else ''} {br.kl_klammer(g)}."]
    befund, punkte, mehrere = [], [], len(je) > 1
    for s, g, k in je:
        if g is None or g < 2:
            if mehrere and s:
                befund.append(f"{s.capitalize()} normal weiter Gelenkspalt.")
            continue
        if mehrere and s:
            befund.append(f"{s.capitalize()} {k + ' ' if k else ''}{_klein(tab[g])}")
            if k:
                befund.append(f"{_ANDERES[k]} {s} normal weiter Gelenkspalt.")
        else:
            befund.append(f"{k.capitalize()} {_klein(tab[g])}" if k else tab[g])
            if k:
                befund.append(f"{_ANDERES[k]} normal weiter Gelenkspalt.")
        punkte.append(f"{adj[g]} Gonarthrose{' ' + s if s else ''}{' ' + k if k else ''} {br.kl_klammer(g)}.")
    return befund, punkte


def koala_hat_text(b):
    """Bringt Baustein b (ohne Diktat, ohne bekannte Untersuchung) einen KOALA-Text? (Gerüst, Band)"""
    return b.modul == "koala" and _koala_plan(b, "", "", "", []) is not None


def _koala_befund(block, saetze, alte=()):
    """Beschreibung einer Knie-Untersuchung (Text ohne Überschriften) → (neuer Text, ohne Platz eingesetzt?)."""
    ende = len(block) - len(block.rstrip())
    m = _KNIE_WT_ABSATZ.search(block.rstrip())
    if m:
        block = block.rstrip()[:m.start()].rstrip() + " " + m.group(1) + block[len(block) - ende:]
    for satz in dict.fromkeys(alte):              # eine frühere Fassung (bzw. dieselbe) zuerst herausnehmen
        while satz and satz in block and satz not in saetze:
            i = block.index(satz)
            block = _satz_raus(block, i, i + len(satz))
    m = _KNIE_FORM.search(block)
    if m and m.group(0) != KOALA_STELLUNG:
        block = _satz_raus(block, m.start(), m.end(), KOALA_STELLUNG)
    if all(s in block for s in saetze):
        return block, False
    neu = " ".join(saetze)
    m = _KNIE_FORM.search(block)
    if m and m.group(0) == KOALA_STELLUNG:
        pass
    elif m:
        block = _satz_raus(block, m.start(), m.end(), KOALA_STELLUNG)
    elif "Stellung" not in block and block.strip():
        i = len(block) - len(block.lstrip())
        block = block[:i] + KOALA_STELLUNG + " " + block[i:]
    m = _KNIE_FLAECHEN.search(block)
    if m:
        block = _satz_raus(block, m.start(), m.end())
    m = _KNIE_SPALT.search(block)
    if m:
        return _fp_nach(_satz_raus(block, m.start(), m.end(), neu), neu), False
    for anker in _KNIE_ANKER:
        m = anker.search(block)
        if m:
            return _fp_nach(block[:m.start()] + neu + " " + block[m.start():], neu), False
    return block, True


def _fp_nach(block, neu):
    """Femoropatellar-Satz, der VOR dem femorotibialen KOALA-Text steht, direkt dahinter (Georg: Medial – Lateral –
    Femoropatellar)."""
    i = block.find(neu)
    if i < 0:
        return block
    vor = [m for m in _FP_SATZ.finditer(block[:i])]
    saetze = [_fp_form(m) for m in vor]
    for m in reversed(vor):
        block = block[:m.start()] + block[m.end():]
    if saetze:
        i = block.find(neu) + len(neu)
        block = block[:i] + " " + " ".join(saetze) + block[i:]
    i = block.find(neu) + len(neu)
    return block[:i] + _FP_SATZ.sub(lambda m: _fp_form(m) + (" " if m.group(0).endswith(" ") else ""), block[i:])


def _koala_ergebnis(zeilen, a, punkte, b, hinweise):
    """KOALA-Punkte als ERSTE Punkte des Ergebnisses von a; das Normal-Ergebnis des Knies entfällt, derselbe Punkt nie
    doppelt; neu durchgezählt. → Zeilen mehr."""
    if a.ergebnis < 0:
        return _ergebnis_anfuegen(zeilen, a, punkte)
    s, k = a.ergebnis + 1, a.ende
    while k > s and not zeilen[k - 1].strip():
        k -= 1
    inhalt = zeilen[s:k]
    rest = []
    for z in inhalt:
        t = _NUM.sub("", z).strip()
        if not t or t in punkte:
            continue
        g = br.kl_grade(t)
        m = _FP_PUNKT.match(t)
        if m and len(g) == 1 and int(g[0]) in br.KL_ADJEKTIV:
            neu_t = f"{br.KL_ADJEKTIV[int(g[0])]} Femoropatellararthrose" + t[m.end():]
            if neu_t != t:
                hinweise.append(f"{b.name}: „{_kurz(t, 40)}“ → „{_kurz(neu_t, 40)}“ (Form der K&L-Tabelle)")
                z = z.replace(t, neu_t)
        if z[:1] not in (" ", "\t") and ergebnis_normal([t]) and re.search(r"knie", t, re.I):
            hinweise.append(f"{b.name}: „{_kurz(t)}“ durch das IB-Lab-Ergebnis ersetzt")
            continue
        rest.append(z)
    neu = br.ergebnis_nummerieren("## Ergebnis\n" + "\n".join(list(punkte) + rest)).split("\n")[1:]
    zeilen[s:k] = neu
    return len(neu) - len(inhalt)


def _koala_einsetzen(zeilen, teile, i, b, e):
    """KOALA-Text in die Knie-Untersuchung teile[i] einsetzen (Beschreibung + erster Ergebnispunkt)."""
    a = teile[i]
    plan = _koala_plan(b, a.titel, a.seite, a.segment or "", e.hinweise)
    if plan is None:
        return
    saetze, punkte = plan
    bs = (a.befund if a.befund >= 0 else a.start) + 1
    be = a.ergebnis if a.ergebnis >= 0 else a.ende
    alt = "\n".join(zeilen[bs:be])
    ersetzt = [z for z in e.nicht_entfernt if z and z in alt]
    block, ohne_platz = _koala_befund(alt, saetze, ersetzt)
    e.nicht_entfernt = [z for z in e.nicht_entfernt if z not in ersetzt]
    if block != alt:
        neu = block.split("\n")
        zeilen[bs:be] = neu
        _verschieben(teile, i, len(neu) - (be - bs))
    if ohne_platz:
        e.hinweise.append(f"{b.name}: Satz der Vorlage zum Gelenkspalt nicht gefunden – KOALA-Text am Ende der "
                          "Beschreibung, bitte prüfen")
        _verschieben(teile, i, _befund_anfuegen(zeilen, a, [" ".join(saetze)]))
    _verschieben(teile, i, _koala_ergebnis(zeilen, a, punkte, b, e.hinweise), nur_ende=True)
    e.eingesetzt[b.schluessel] = list(saetze) + list(punkte)
    e.zuordnung[b.modul] = a.titel or "Befund"


def _koala_geruest(b, titel, vorlage=None):
    """Gerüst vor dem Diktat: Vorlage der Knie-Leistung mit KOALA-Text (bzw. ohne bekannte Vorlage nur die Sätze) →
    (Befundzeilen, Ergebnispunkte)."""
    plan = _koala_plan(b, titel, Abschnitt(titel, 0, 0).seite, "", [], vorlage or "")
    if plan is None:
        return [], []
    saetze, punkte = plan
    if vorlage and _KNIE_SPALT.search(vorlage):
        rumpf = "\n".join(vorlage.split("\n")[1:]).strip("\n")
        block, ohne_platz = _koala_befund(rumpf, saetze)
        if not ohne_platz:
            return block.split("\n"), punkte
    return [" ".join(saetze)], punkte


# ───────────────────────────── IB Lab HIPPO: Becken-/Hüft-Text ─────────────────────────────
# Georg Riegler 18.11.2026 (GO 19:58, Brief kaiscribe-hippo-ergebnistext-n1 + Nachträge 18:30–18:54): der Abholer ≥ 1.3.11
# (ris-mods ibl/hippo_ergebnis.py) liefert im Feld „befundtext“ fertige Sätze für die Beschreibung (Beckenschiefstand,
# Beinlängendifferenz, auffällige Winkel mit Wert), den Ergebnispunkt mit den Begriffen ohne Werte und die Schlussanmerkung.
# Maßgeblich sind die CAS-Vorlagen (templates.json):
#   - „Beckenübersicht stehend“ (und Hüfte analog): bei HIPPO-Ergebnis entfallen IMMER „Anatomisch normale und symmetrische
#     Form des Beckenskeletts.“, „Beide Beckenschaufeln stehen gleichhoch.“, „Der CCD-Winkel ist im Normbereich.“ und „Die
#     artikulierenden Flächen sind kongruent bei guter Deckung der Hüftköpfe durch die Pfannen.“ (Hüfte: „Anatomisch normale
#     Form des Hüftgelenkes …“, „… guter Deckung des Hüftkopfes durch die Pfanne.“); die HIPPO-Sätze stehen am Anfang, danach
#     „Mineralgehalt und Knochenstruktur sind regelrecht. …“.
#   - „Beckenübersicht und Hüfte“ und die Prothesen-Vorlagen: nur die Zeile „Beckenschiefstand: Keiner. Keine signifikante
#     Beinlängendifferenz.“ wird durch die HIPPO-Sätze ersetzt.
#   - Ein verbleibender Vorlagensatz, der einer HIPPO-Diagnose widerspricht („Regelrechte Abbildung beider Pfannendächer.“
#     neben einer Hüftdysplasie) → rote Prüfzeile, am Text wird nichts geändert.
#   - Ergebnis: der HIPPO-Punkt als ERSTER Punkt, das Normal-Ergebnis („Regelrechte Darstellung des Beckens.“) entfällt dann,
#     Diktiertes folgt, die Schlussanmerkung („LCE = … Weitere Winkelmessungen …“) ohne Nummer ganz unten – auch ohne Punkt
#     (Kinder unter 16: nur beschreibend, kein Punkt; Georg: der Schlusssatz bleibt).
#   - Schon diktierter Begriff → nicht doppelt; vom Diktat verneint → nicht eingesetzt (Hinweis).
HIPPO_SCHLUSS = ("LCE = ", "AI = ", "CCD = ")                    # = ris-mods ibl/hippo_ergebnis.ist_schlussanmerkung
HIPPO_PROMPT = ("HIPPO: Übernimm die Sätze der Becken-/Hüft-Vorlage wörtlich und unverändert (auch „Beckenschiefstand: …“), "
                "außer der Arzt hat dazu etwas diktiert – KaiScribe setzt nach dem Befund die IB-Lab-Sätze zu "
                "Beckenschiefstand, Beinlängendifferenz und auffälligen Hüftwinkeln oben in die Beschreibung, nimmt die "
                "Vorlagen-Sätze zu Beckenform, Beckenschaufeln, CCD-Winkel und Deckung der Hüftköpfe heraus und setzt die "
                "Diagnosen als ersten Ergebnispunkt. Schreibe selbst keinen Satz und keine Diagnose zu Beckenschiefstand, "
                "Beinlänge, Überdachung, Pfannendach, Hüftdysplasie oder CCD-Winkel, außer der Arzt hat es diktiert.")
_HIPPO_WEG = [re.compile(x) for x in (
    r"Anatomisch normale und symmetrische Form des Beckenskeletts\.",
    r"Beide Beckenschaufeln stehen gleich ?hoch\.",
    r"Der CCD-Winkel ist (?:beidseits )?im Normbereich\.",
    r"Die artikulierenden Flächen sind kongruent bei guter Deckung der Hüftköpfe durch die Pfannen\.",
    r"Anatomisch normale Form des Hüftgelenkes mit regelrechter Stellung des Hüftkopfes in der Pfanne\.",
    r"Die artikulierenden Flächen sind kongruent bei guter Deckung des Hüftkopfes durch die Pfanne\.",
    r"Das Beckenskelett (?:ist )?horizontal, regelrecht konfiguriert und unauffällig strukturiert\.")]
_HIPPO_ZEILE = re.compile(r"Beckenschiefstand:\s*Keiner\.(?:[ \t]*Keine (?:signifikante )?Beinlängendifferenz\.)?")
_HIPPO_ERG_NORMAL = re.compile(r"darstellung\b.*(?:becken|hüft)", re.I)
_HIPPO_MARKE = "\x01HIPPO\x01"


def _hippo_text(b):
    """HIPPO-Baustein mit fertigem Text des Abholers (≥ 1.3.11)?"""
    return b.modul == "hippo" and b.befundtext is not None


def _hippo_punkt(b, diktat, hinweise):
    """Ergebnispunkt (Begriffe) nach dem Diktat: schon diktierter bzw. verneinter Begriff fällt heraus (Hinweis)."""
    out = []
    for satz in [s.strip() for s in re.split(r"(?<=\.)\s+", b.befundtext["ergebnis"]) if s.strip()]:
        art, wort = _diagnose_im_text(satz.rstrip("."), "", diktat or "")
        if art == "doppelt":
            hinweise.append(f"{b.name}: „{_kurz(satz)}“ – schon diktiert, nicht doppelt angefügt")
            continue
        if art == "widerspruch":
            hinweise.append(f"{b.name}: „{_kurz(satz)}“ – Diktat verneint „{wort}“, bitte prüfen (nicht eingesetzt)")
            continue
        if art == "verwandt":
            hinweise.append(f"{b.name}: „{_kurz(satz)}“ angefügt – Diktat nennt schon „{wort}“, bitte prüfen")
        out.append(satz)
    return " ".join(out)


def _hippo_befund(block, saetze, alte=()):
    """Beschreibung einer Becken-/Hüft-Untersuchung (Text ohne Überschriften) → neuer Text: HIPPO-Sätze an die Stelle der
    Zeile „Beckenschiefstand: …“ bzw. an den Anfang, die vier Vorlagen-Sätze heraus. alte: Sätze einer früheren Fassung."""
    neu = " ".join(saetze)
    for satz in dict.fromkeys(alte):                  # frühere Fassung (bzw. dieselbe) zuerst herausnehmen, Stelle merken
        while satz and satz in block:
            i = block.index(satz)
            block = _satz_raus(block, i, i + len(satz), "" if _HIPPO_MARKE in block else _HIPPO_MARKE)
    for rx in _HIPPO_WEG:
        m = rx.search(block)
        while m:
            block = _satz_raus(block, m.start(), m.end())
            m = rx.search(block)
    m = _HIPPO_ZEILE.search(block)
    if _HIPPO_MARKE in block:
        i = block.index(_HIPPO_MARKE)
        block = _satz_raus(block, i, i + len(_HIPPO_MARKE), neu)
        if m:
            m = _HIPPO_ZEILE.search(block)
            block = _satz_raus(block, m.start(), m.end())
    elif m:
        block = _satz_raus(block, m.start(), m.end(), neu)
    else:
        i = len(block) - len(block.lstrip())
        rest = block[i:]
        block = block[:i] + neu + ((" " + rest) if rest and not rest.startswith("\n") else rest)
    return block


def _hippo_ergebnis(zeilen, a, punkte, schluss, b, hinweise, normal=_HIPPO_ERG_NORMAL, weg=()):
    """HIPPO-Punkt als ERSTER Punkt, Normal-Ergebnis des Beckens/der Hüfte entfällt (nur mit Punkt), derselbe Punkt nie
    doppelt, Schlussanmerkung ohne Nummer ganz unten. → Zeilen mehr. normal: Normal-Ergebnis der Region, weg: eigene Punkte
    einer früheren Fassung, die nicht mehr gelten (SQUIRREL)."""
    if a.ergebnis < 0:
        return _ergebnis_anfuegen(zeilen, a, list(punkte) + ([schluss] if schluss else []))
    s, k = a.ergebnis + 1, a.ende
    while k > s and not zeilen[k - 1].strip():
        k -= 1
    inhalt = zeilen[s:k]
    rest = []
    for z in inhalt:
        t = _NUM.sub("", z).strip()
        if not t or t in punkte or t in weg or ist_schluss(t):
            continue
        if punkte and z[:1] not in (" ", "\t") and ergebnis_normal([t]) and normal.search(t):
            hinweise.append(f"{b.name}: „{_kurz(t)}“ durch das IB-Lab-Ergebnis ersetzt")
            continue
        rest.append(z)
    neu = br.ergebnis_nummerieren("## Ergebnis\n" + "\n".join(list(punkte) + rest + ([schluss] if schluss else []))
                                  ).split("\n")[1:]
    zeilen[s:k] = neu
    return len(neu) - len(inhalt)


def _hippo_einsetzen(zeilen, teile, i, b, e):
    """HIPPO-Text in die Becken-/Hüft-Untersuchung teile[i] einsetzen (Beschreibung oben, erster Ergebnispunkt, Schluss)."""
    a = teile[i]
    bt = b.befundtext
    punkt = _hippo_punkt(b, a.segment or "", e.hinweise)
    bs = (a.befund if a.befund >= 0 else a.start) + 1
    be = a.ergebnis if a.ergebnis >= 0 else a.ende
    alt = "\n".join(zeilen[bs:be])
    ersetzt = [z for z in e.nicht_entfernt if z and z in alt]
    block = _hippo_befund(alt, bt["saetze"], ersetzt + bt["saetze"])
    e.nicht_entfernt = [z for z in e.nicht_entfernt if z not in ersetzt]
    if punkt:                                         # verbleibende Vorlagensätze gegen die HIPPO-Diagnosen
        ohne = block
        for s in bt["saetze"]:
            ohne = ohne.replace(s, "")
        for satz in _normalsaetze(b, ohne.split("\n"), [punkt]):
            e.hinweise.append(f"⚠ {b.name}: Befundtext „{_kurz(satz, 50)}“ widerspricht IB Lab – bitte prüfen")
    if block != alt:
        neu = block.split("\n")
        zeilen[bs:be] = neu
        _verschieben(teile, i, len(neu) - (be - bs))
    punkte = [punkt] if punkt else []
    _verschieben(teile, i, _hippo_ergebnis(zeilen, a, punkte, bt["schluss"], b, e.hinweise), nur_ende=True)
    da = "\n".join(zeilen[a.start:a.ende])
    e.eingesetzt[b.schluessel] = [s for s in bt["saetze"] if s in da] + punkte + ([bt["schluss"]] if bt["schluss"] else [])
    e.zuordnung[b.modul] = a.titel or "Befund"


def _vorlage_ergebnis(l, templates):
    """Ergebnis-Satz der Vorlage einer CAS-Leistung (Gerüst) – sonst ""."""
    v = cv.leistung_vorlage(l, templates or {}) if l else None
    if not v:
        return ""
    return str(((templates or {}).get(v) or {}).get("ergebnis") or "").strip()


def _hippo_geruest(b, titel, vorlage=None, vorlage_ergebnis=""):
    """Gerüst vor dem Diktat: Vorlage der Becken-/Hüft-Leistung mit den HIPPO-Sätzen (bzw. ohne bekannte Vorlage nur die
    Sätze) → (Befundzeilen, Ergebnispunkte: HIPPO-Punkt bzw. Normal-Ergebnis der Vorlage, Schlussanmerkung)."""
    bt = b.befundtext
    punkte = [bt["ergebnis"]] if bt["ergebnis"] else ([vorlage_ergebnis] if vorlage_ergebnis else [])
    punkte += [bt["schluss"]] if bt["schluss"] else []
    if vorlage:
        rumpf = "\n".join(vorlage.split("\n")[1:]).strip("\n")
        if rumpf.strip():
            return _hippo_befund(rumpf, bt["saetze"]).split("\n"), punkte
    return [" ".join(bt["saetze"])], punkte


# ───────────────────────────── IB Lab SQUIRREL: Skoliose-Text der Ganzwirbelsäule ─────────────────────────────
# Georg Riegler 20.11.2026 („1a 2a 3a 4a 5ja“, Brief kaiscribe-squirrel-ergebnistext-n1): der Abholer ≥ 1.3.14 (ris-mods
# ibl/squirrel_ergebnis.py, Regeln ibl/regeln/squirrel.toml [ergebnistext]) liefert im Feld „befundtext“ je Krümmung ≥ 10°
# (kranial → kaudal) einen Satz („Rechtskonvexe skoliotische Krümmung der BWS (Th5–Th12) mit einem Cobb-Winkel von 44°.“),
# ggf. die seitliche Rumpfabweichung, EINEN Ergebnispunkt (Hauptkrümmung zuerst, ggf. „Zunahme von 32° (03/2025) auf 44° im
# Sinne einer Progredienz.“), den Cobb-Satz für den Diktat-Fall und die Schlussanmerkung. Unter 10°, Metall, andere Region/
# Projektion, unter 10 J.: kein Feld. „ergebnis_punkte“ bleibt für SQUIRREL leer – den Skoliose-Satz setzt nur, wer das
# Diktat kennt (KaiScribe hier, sonst der Formatierer ris-mods bruecke/ibl_einfuegen.squirrel_text_planen).
#   - Vorrang Diktat (Peter 20.11.2026, Punkt 20): nennt das DIKTAT (nicht die Vorlage, nicht die eigenen Sätze) eine
#     seitliche Krümmung/Skoliose/Asymmetrie – auch verneint –, bleibt die Wortwahl des Arztes; dann nur der Cobb-Satz
#     (+ Rumpfabweichung) hinter seinen Satz, KEIN Ergebnissatz, nie zusätzlich „Skoliose“ (DIKTAT_KRUEMMUNG).
#   - Sonst: die Sätze an die Stelle des Vorlagensatzes zur Achse („Wirbelsäule: Normale Stellung, …“ der GWS a.p.,
#     „Normaler Achsenverlauf.“/„Annähernd achsengerechte Stellung.“; Gesamte Wirbelsäule mit HWS/BWS/LWS-Abschnitten bzw.
#     ohne Achsensatz: als erster Absatz), der Punkt als ERSTER Ergebnispunkt (Normal-Ergebnis der Wirbelsäule entfällt),
#     Schlussanmerkung ohne Nummer ganz unten.
#   - Peter 20.11.2026, Punkt 40b: Kyphose-/Lordose-Sätze der Vorlage bleiben; „achsengerechte Stellung“/„Normaler
#     Achsenverlauf“ (VORLAGE_ACHSE_NORMAL) entfällt bei Skoliose-Text ODER diktierter Krümmung (außer der Arzt hat selbst so
#     diktiert).
#   - Keine Messzeilen „Cobb-Winkel … (IB Lab SQUIRREL).“, wenn der Text da ist; Hinweise mit „prüfen“ = rote Prüfzeile.
SQUIRREL_PROMPT = ("SQUIRREL: Übernimm die Sätze der Wirbelsäulen-Vorlage wörtlich und unverändert (auch „Normale Stellung …“, "
                   "„Normaler Achsenverlauf.“, „achsengerechte Stellung“ und die Kyphose-/Lordose-Sätze), außer der Arzt hat "
                   "dazu etwas diktiert – KaiScribe setzt nach dem Befund die IB-Lab-Sätze zur seitlichen Krümmung mit den "
                   "Cobb-Winkeln an die Stelle des Achsensatzes und die Skoliose als ersten Ergebnispunkt. Schreibe selbst "
                   "keinen Satz, keinen Cobb-Winkel und keine Diagnose zu Skoliose oder seitlicher Krümmung, außer der Arzt "
                   "hat es diktiert. Hat der Arzt eine seitliche Krümmung, Skoliose oder Asymmetrie diktiert (auch verneint), "
                   "übernimm seine Wortwahl wörtlich in Befund und Ergebnis – mache daraus keine „Skoliose“, wenn er sie nicht "
                   "so genannt hat, und verschärfe nie; KaiScribe ergänzt dann nur die Cobb-Winkel.")
# = ris-mods ibl/squirrel_ergebnis.DIKTAT_KRUEMMUNG / VORLAGE_ACHSE_NORMAL (wörtlich; Test prüft die Gleichheit)
DIKTAT_KRUEMMUNG = re.compile(
    r"(?i)skolio\w*|asymmetri\w*|rechtskonvex\w*|linkskonvex\w*|konvex\w*\s+(?:nach\s+)?(?:rechts|links)|"
    r"(?:seitliche|seitwärts|lateral\w*)\s+(?:\w+\s+)?(?:krümmung|ausbiegung|verkrümmung|abweichung)|"
    r"seitausbiegung|s-förmig\w*|c-förmig\w*|fehlhaltung\s+nach\s+(?:rechts|links)|"
    r"krümmung\w*\s+nach\s+(?:rechts|links)")
VORLAGE_ACHSE_NORMAL = re.compile(
    r"(?i)[^.\n]*(?:achsengerechte[nr]?\s+Stellung|normaler\s+Achsenverlauf|regelrechter\s+Achsenverlauf|"
    r"achsengerechte[rn]?\s+Achsenverlauf)[^.\n]*\.?")
# GWS a.p. (templates.json ganzaufnahme_der_wirbelsäule_a-p): „Wirbelsäule: Normale Stellung, flachbogige rechts-konvexe
# Skoliose. Alignementlinien regelrecht.“ – der Achsensatz hinter „Wirbelsäule: “ (die Beschriftung bleibt)
# 3.20.5 (Abnahme 21.11.2026, GWS a.p. C): die KI ließ die Beschriftung „Wirbelsäule:“ weg – „Normale Stellung.“ am Zeilen-/
# Befundanfang zählt genauso (sonst stand der Skoliose-Satz NEBEN „Normale Stellung.“)
_SQ_GWS = re.compile(r"(?m)(?:(?<=Wirbelsäule: )|^)Normale Stellung(?:, flachbogige (?:rechts|links)-?konvexe Skoliose)?\.")
_SQ_ABSCHNITT = re.compile(r"(?m)^(?:HWS|BWS|LWS):[ \t]*$")          # Gesamte Wirbelsäule / HWS und LWS
_SQ_BESCHRIFTUNG = re.compile(r"[A-Za-zÄÖÜäöüß]{2,15}:[ \t]*")
_SQ_ERG_NORMAL = re.compile(r"darstellung\b.*(?:wirbelsäule|hws|bws|lws)", re.I)
_SQ_METALL = re.compile(r"metall|implantat", re.I)
_SQ_SATZENDE = re.compile(r"\.(?=\s|$)")
_SQ_MARKE, _SQ_ACHSE = "\x01SQ\x01", "\x01SQ-X\x01"


def _squirrel_text(b):
    """SQUIRREL-Baustein mit fertigem Text des Abholers (≥ 1.3.14)?"""
    return b.modul == "squirrel" and b.befundtext is not None


def _squirrel_metall(b):
    """SQUIRREL ohne Text wegen Metall/Implantat (Hinweis des Abholers) – dann nur die Prüfzeile, keine Messzeilen."""
    return b.modul == "squirrel" and b.befundtext is None and any(_SQ_METALL.search(h) for h in b.hinweise)


def squirrel_diktiert(diktat):
    """Nennt das Diktat eine seitliche Krümmung/Skoliose/Asymmetrie (auch verneint)? (Peter 20.11.2026, Punkt 20)"""
    return bool(DIKTAT_KRUEMMUNG.search(diktat or ""))


def _squirrel_neu(b, diktiert):
    """Sätze für die Beschreibung: Skoliose-Sätze bzw. (Diktat-Fall) nur Cobb-Satz + Rumpfabweichung."""
    bt = b.befundtext
    return [x for x in (bt["cobb_satz"], bt["coronal"]) if x] if diktiert else list(bt["saetze"])


def _squirrel_befund(block, neu, diktiert, diktat="", alte=()):
    """Beschreibung einer Wirbelsäulen-Untersuchung (Text ohne Überschriften) → (neuer Text, Sätze, die ohne diktierte
    Krümmung schon eine Krümmung nennen – Prüfzeile). alte: eigene Sätze einer früheren Fassung (ihre Stelle gilt)."""
    txt = " ".join(neu)
    for satz in dict.fromkeys(alte):
        while satz and satz in block:
            i = block.index(satz)
            block = _satz_raus(block, i, i + len(satz), "" if _SQ_MARKE in block else _SQ_MARKE)
    gesamt = bool(_SQ_ABSCHNITT.search(block))
    if not diktiert:
        m = _SQ_GWS.search(block)
        if m:
            block = _satz_raus(block, m.start(), m.end(), _SQ_ACHSE)
    if not VORLAGE_ACHSE_NORMAL.search(diktat or ""):    # 40b – außer der Arzt hat selbst so diktiert
        pos = 0
        while True:
            m = VORLAGE_ACHSE_NORMAL.search(block, pos)
            if not m:
                break
            a, z = m.start(), m.end()
            a += len(block[a:z]) - len(block[a:z].lstrip())
            lab = _SQ_BESCHRIFTUNG.match(block, a)
            a = lab.end() if lab and lab.end() < z else a
            if DIKTAT_KRUEMMUNG.search(block[a:z]):          # der Satz nennt selbst eine Krümmung (Diktat) – bleibt
                pos = z
                continue
            setzen = _SQ_ACHSE not in block and not gesamt
            block = _satz_raus(block, a, z, _SQ_ACHSE if setzen else "")
            pos = a + (len(_SQ_ACHSE) if setzen else 0)
    m = DIKTAT_KRUEMMUNG.search(block) if diktiert else None
    if m:                                                # hinter den Satz des Arztes
        e = _SQ_SATZENDE.search(block, m.end())
        j = e.end() if e else (block.find("\n", m.end()) if "\n" in block[m.end():] else len(block))
        block = block[:j] + " " + txt + block[j:]
    elif _SQ_MARKE in block:                             # Stelle einer früheren Fassung
        i = block.index(_SQ_MARKE)
        block = _satz_raus(block, i, i + len(_SQ_MARKE), txt)
    elif _SQ_ACHSE in block:
        i = block.index(_SQ_ACHSE)
        block = _satz_raus(block, i, i + len(_SQ_ACHSE), txt)
    else:
        i = len(block) - len(block.lstrip())
        rest = block[i:]
        if gesamt:
            block = block[:i] + txt + ("\n\n" + rest if rest else "")
        else:
            block = block[:i] + txt + ((" " + rest) if rest and not rest.startswith("\n") else rest)
    for marke in (_SQ_MARKE, _SQ_ACHSE):
        while marke in block:
            i = block.index(marke)
            block = _satz_raus(block, i, i + len(marke))
    konflikt = []
    if not diktiert:
        ohne = block.replace(txt, "")
        for zeile in ohne.split("\n"):
            konflikt += [x.strip() for x in re.split(r"(?<=[.!?])\s+", zeile) if DIKTAT_KRUEMMUNG.search(x)]
    return block, konflikt


def _squirrel_einsetzen(zeilen, teile, i, b, e, ganz=""):
    """SQUIRREL-Text in die Wirbelsäulen-Untersuchung teile[i] einsetzen (Beschreibung an der Stelle des Achsensatzes bzw.
    Cobb-Satz hinter dem diktierten Satz, erster Ergebnispunkt, Schluss)."""
    a = teile[i]
    bt = b.befundtext
    diktat = a.segment or ganz or ""
    diktiert = squirrel_diktiert(diktat)
    neu = _squirrel_neu(b, diktiert)
    bs = (a.befund if a.befund >= 0 else a.start) + 1
    be = a.ergebnis if a.ergebnis >= 0 else a.ende
    alt = "\n".join(zeilen[bs:be])
    ersetzt = [z for z in e.nicht_entfernt if z and z in alt]
    eigene = [x for x in [bt["cobb_satz"], bt["coronal"]] + bt["saetze"] if x]
    block, konflikt = _squirrel_befund(alt, neu, diktiert, diktat, ersetzt + eigene)
    e.nicht_entfernt = [z for z in e.nicht_entfernt if z not in ersetzt]
    for satz in konflikt:
        e.hinweise.append(f"⚠ {b.name}: Befundtext „{_kurz(satz, 50)}“ nennt schon eine Krümmung (nicht diktiert) – "
                          "bitte prüfen")
    if diktiert:
        e.hinweise.append(f"{b.name}: Krümmung diktiert – Wortwahl bleibt, nur Cobb-Winkel eingesetzt (kein Ergebnissatz)")
    if block != alt:
        nz = block.split("\n")
        zeilen[bs:be] = nz
        _verschieben(teile, i, len(nz) - (be - bs))
    punkte = [bt["ergebnis"]] if bt["ergebnis"] and not diktiert else []
    weg = [bt["ergebnis"]] if bt["ergebnis"] and diktiert else []
    _verschieben(teile, i, _hippo_ergebnis(zeilen, a, punkte, bt["schluss"], b, e.hinweise, _SQ_ERG_NORMAL, weg),
                 nur_ende=True)
    da = "\n".join(zeilen[a.start:a.ende])
    e.eingesetzt[b.schluessel] = [s for s in neu if s in da] + punkte + ([bt["schluss"]] if bt["schluss"] else [])
    e.zuordnung[b.modul] = a.titel or "Befund"


def _squirrel_ende(b, diktat=""):
    """Ohne passende Untersuchung: Sätze (bzw. Cobb-Satz), Ergebnispunkt und Schluss als Zeilen für den Absatz am Ende."""
    bt = b.befundtext
    diktiert = squirrel_diktiert(diktat)
    return _squirrel_neu(b, diktiert) + ([bt["ergebnis"]] if bt["ergebnis"] and not diktiert else []) \
        + ([bt["schluss"]] if bt["schluss"] else [])


def _squirrel_geruest(b, vorlage=None, vorlage_ergebnis=""):
    """Gerüst vor dem Diktat: Vorlage der Wirbelsäulen-Leistung mit den Skoliose-Sätzen an der Stelle des Achsensatzes (bzw.
    ohne bekannte Vorlage nur die Sätze) → (Befundzeilen, Ergebnispunkte: Skoliose-Punkt, Schlussanmerkung)."""
    bt = b.befundtext
    punkte = [bt["ergebnis"]] if bt["ergebnis"] else ([vorlage_ergebnis] if vorlage_ergebnis else [])
    punkte += [bt["schluss"]] if bt["schluss"] else []
    if vorlage:
        rumpf = "\n".join(vorlage.split("\n")[1:]).strip("\n")
        if rumpf.strip():
            return _squirrel_befund(rumpf, bt["saetze"], False)[0].split("\n"), punkte
    return [" ".join(bt["saetze"])], punkte


# IB Lab PANDA (Georg Riegler 18.11.2026, Brief kaiscribe-panda-knochenalter-n1): der Abholer ≥ 1.3.10 (ris-mods
# ibl/panda_ergebnis.py) liefert den FERTIGEN Knochenalter-Text als einzigen Ergebnispunkt („Zum Zeitpunkt der Untersuchung
# beträgt das Alter des Jungen 13 Jahre und 6 Monate. Das ermittelte Knochenalter nach Greulich und Pyle beträgt … und ist
# damit altersentsprechend. Nach Bayley und Pinneau sind 89,0 % des Wachstumspotenzials erreicht.“; Wertung ±2·SD, Lebensalter
# lokal aus dem DICOM-Kopf). KaiScribe setzt ihn als ERGEBNISBEFUND ein: kein Befundteil (Vorlagen-Sätze zu Alter,
# Körpergröße, Knochenalter, Endgröße und Normalsätze der Hand-Vorlage entfallen), keine Zusatzzeile wie „Unauffälliger
# Befund.“, keine Messzeilen; der Text ist der erste Punkt, Diktiertes (Nebenbefunde) folgt, ein Punkt ohne Nummer.
# Kein Text (nur Anzeige): Sonderfälle des Abholers (NaN, mehrere Bilder, Geburtsdatum fehlt, IFU – dort als Hinweis) und
# eine CAS-Leistung, die nicht „Knochenalter“/handl ist (handgel, kahn, hand2 …) → „PANDA außerhalb Auftrag/IFU“.
PANDA_ANFANG = "Zum Zeitpunkt der Untersuchung beträgt das Alter des "   # = ris-mods ibl/panda_ergebnis.ANFANG
PANDA_IFU = "PANDA außerhalb Auftrag/IFU"
PANDA_TITEL = "Hand links, Knochenalterbestimmung"
PANDA_PROMPT = ("PANDA: Schreibe zur Knochenalterbestimmung KEINEN Befundteil – keinen Satz zu Lebensalter, Körpergröße, "
                "Knochenalter, Endgröße oder Wachstumspotenzial, keine Lücken („…“) und keine Ergebniszeile wie "
                "„Unauffälliger Befund.“. KaiScribe setzt den IB-Lab-Text als Ergebnisbefund ein; nur was der Arzt "
                "zusätzlich diktiert hat (z. B. Nebenbefunde), schreibst du als Ergebnispunkte.")
_PANDA_VORLAGE = re.compile(r"zum zeitpunkt der untersuchung|knochenalter|skelettalter|körpergröße|koerpergroesse|"
                            r"endkörpergröße|endgröße|endgroesse|wachstumspotenzial|greulich|bayley|…|\.\.\.", re.I)
_PANDA_ERG_NORMAL = re.compile(r"^(?:(?:unauffälliger|regelrechter|altersentsprechender)\s+)?(?:normal)?befund\.?$|"
                               r"^(?:regelrechte|unauffällige) darstellung\b", re.I)
_PANDA_AUFTRAG = re.compile(r"knochenalter|skelettalter", re.I)


def panda_auftrag_passt(b, cas_leistungen):
    """CAS-Leistung des PANDA-Bausteins: „Knochenalter“ bzw. Kürzel handl → True; andere Hand-Leistung (handgel, kahn,
    hand2 …) → False; ohne Leistung/Kürzel → None (unbekannt – die Weiche schickt PANDA nur bei handl)."""
    l = _leistung_zur_ziffer(b.ziffer, cas_leistungen) if cas_leistungen else None
    if not isinstance(l, dict):
        return None
    kurz = str(l.get("kurz") or "").strip().lower()
    if kurz == "handl" or _PANDA_AUFTRAG.search(f"{l.get('text') or ''} {l.get('vorlage') or ''}"):
        return True
    return False if kurz else None


def panda_text(b, cas_leistungen=None, hinweise=None):
    """Fertiger Knochenalter-Text des Abholers (oder „“); CAS-Leistung nicht Knochenalter → „“ + Hinweis."""
    if b.modul != "panda":
        return ""
    t = next((p for p in b.ergebnis if p.startswith(PANDA_ANFANG)), "")
    if t and panda_auftrag_passt(b, cas_leistungen) is False:
        if hinweise is not None:
            hinweise.append(f"{b.name}: {PANDA_IFU} (CAS-Leistung nicht Knochenalter/handl) – kein Text")
        return ""
    return t


def _panda_einsetzen(zeilen, teile, i, b, text, e):
    """Knochenalter-Text als Ergebnisbefund in teile[i]: Befundteil ohne Vorlagen-/Normalsätze (leer → weg), Text als
    erster Ergebnispunkt, Diktiertes danach, „Unauffälliger Befund.“ u. ä. entfallen; neu durchgezählt."""
    a = teile[i]
    kopf_ende = min(x for x in (a.befund, a.ergebnis, a.ende) if x >= 0)
    kopf = list(zeilen[a.start:kopf_ende])
    while kopf and not kopf[-1].strip():
        kopf.pop()
    rest_befund = []
    if a.befund >= 0:
        for z in zeilen[a.befund + 1:(a.ergebnis if a.ergebnis > a.befund else a.ende)]:
            saetze = [x for x in re.split(r"(?<=[.!?])\s+", z.strip()) if x]
            bleib = [x for x in saetze if not _PANDA_VORLAGE.search(x)
                     and not (_NORMAL.search(x) and not br.has_pathology(x))]
            if bleib:
                rest_befund.append(" ".join(bleib))
    rest_erg = []
    if a.ergebnis >= 0:
        for z in zeilen[a.ergebnis + 1:a.ende]:
            t = _NUM.sub("", z).strip()
            if not t or t == text:
                continue
            if _PANDA_VORLAGE.search(t) or (z[:1] not in (" ", "\t") and _PANDA_ERG_NORMAL.search(t)):
                e.hinweise.append(f"{b.name}: „{_kurz(t)}“ durch das IB-Lab-Ergebnis ersetzt")
                continue
            rest_erg.append(z)
    if rest_befund:
        e.hinweise.append(f"{b.name}: Befundteil mit diktiertem Text stehen gelassen („{_kurz(rest_befund[0], 50)}“) – "
                          "Knochenalter ist ein Ergebnisbefund, bitte prüfen")
    hinten = 0
    k = a.ende
    while k > a.start and not zeilen[k - 1].strip():
        hinten, k = hinten + 1, k - 1
    neu = kopf + ((["", "## Befund"] + rest_befund) if rest_befund else []) + ["", "## Ergebnis"]
    neu += br.ergebnis_nummerieren("## Ergebnis\n" + "\n".join([text] + rest_erg)).split("\n")[1:]
    neu += [""] * hinten
    d = len(neu) - (a.ende - a.start)
    zeilen[a.start:a.ende] = neu
    a.befund = a.start + neu.index("## Befund") if rest_befund else -1
    a.ergebnis = a.start + len(neu) - 1 - neu[::-1].index("## Ergebnis")
    a.ende = a.start + len(neu)
    for t in teile[i + 1:]:
        t.start, t.ende = t.start + d, t.ende + d
        t.befund += d if t.befund >= 0 else 0
        t.ergebnis += d if t.ergebnis >= 0 else 0
    e.eingesetzt[b.schluessel] = [text]
    e.zuordnung[b.modul] = a.titel or "Befund"


# kaiscribe-georg-2011-n1 (Georg 20.11.2026, Punkt 35): „Varus/Valgus/Varisierung“ nur außerhalb der Grenzen (HKA −2…4°,
# MAD 3…17 mm) – die prüft der Abholer (ris-mods lama_ergebnis.py: „Regelrechte Beinachse …“). Steht im Ganzbein-Ergebnis
# eine regelrechte Beinachse, fällt ein KI-Zusatz „mit Varisierung“ o. ä. für diese Seite im Befundtext weg.
_LAMA_REGELRECHT = re.compile(r"Regelrechte Beinachse(?: (rechts|links|beidseits))?", re.I)
_LAMA_ACHSWORT = re.compile(r"\s*,?\s*(?:mit|bei|im Sinne einer?|und)\s+(?:(?:einer?|geringe[rn]?|leichte[rn]?|diskrete[rn]?|"
                            r"minimale[rn]?)\s+)*(?:Varisierung|Valgisierung|Varus|Valgus|Varusabweichung|"
                            r"Valgusabweichung)(?:\s+(?:rechts|links|beidseits))?(?=[.,;]|\s*$)", re.I)


def lama_achsworte(report):
    """Ganzbein-Befund: Varus-/Valgus-Zusätze der KI weg, wenn LAMA die Achse dieser Seite regelrecht nennt."""
    if not report or "Beinachse" not in report:
        return report
    zeilen = report.split("\n")
    for a, e in reversed(br._abschnitt(zeilen, "befund")):
        titel = next((zeilen[j] for j in range(a - 2, -1, -1) if zeilen[j].startswith("## ")
                      and zeilen[j][3:].strip().lower() not in ("befund", "ergebnis")), "")
        if "ganzbein" not in titel.lower():
            continue
        erg = next(((x, y) for x, y in br._abschnitt(zeilen, "ergebnis") if x > a), None)
        text_erg = " ".join(zeilen[erg[0]:erg[1]]) if erg else ""
        seiten = set()
        for m in _LAMA_REGELRECHT.finditer(text_erg):
            seiten |= {"rechts", "links"} if m.group(1) in (None, "beidseits") else {m.group(1).lower()}
        if not seiten:
            continue
        for i in range(a, e):
            def weg(m, z=zeilen[i]):
                s = m.group(0).lower()
                genannt = {x for x in ("rechts", "links") if x in s} or \
                    ({x for x in ("rechts", "links") if x in z.lower()} if "beidseits" not in s else {"rechts", "links"})
                return "" if (genannt or {"rechts", "links"}) <= seiten else m.group(0)
            zeilen[i] = _LAMA_ACHSWORT.sub(weg, zeilen[i])
    return "\n".join(zeilen)


def anmerkung_absetzen(report):
    """Punkt 9: die Schlussanmerkung(en) jedes Ergebnisses ans Ende, mit einer Leerzeile davor; die erste beginnt mit
    „Anmerkung: “. Ohne Schlussanmerkung unverändert, zweimal angewandt gleich."""
    if not report or "## Ergebnis" not in report:
        return report
    zeilen = report.split("\n")
    for a, e in reversed(br._abschnitt(zeilen, "ergebnis")):
        idx = [i for i in range(a, e) if zeilen[i].strip() and ist_schluss(zeilen[i])]
        if not idx:
            continue
        texte = [_ohne_anmerkung(zeilen[i]) for i in idx]
        nach = e
        while nach > a and not zeilen[nach - 1].strip():
            nach -= 1
        rest = [zeilen[i] for i in range(a, nach) if i not in idx]
        while rest and not rest[-1].strip():
            rest.pop()
        vor = [""] if any(z.strip() for z in rest) else []
        zeilen[a:e] = rest + vor + [ANMERKUNG + texte[0]] + texte[1:] + zeilen[nach:e]
    return "\n".join(zeilen)


def befund_zeilen(b):
    """Befundzeilen, die von Baustein b in den Befund kommen: alle (Module außerhalb BEFUND_NUR_AUFFAELLIG, bit-gleich
    wie bis 3.18.7) bzw. nur die mit Ergebnispunkt; eine Beschriftung („Fuß d.p.:“) nur, wenn darunter noch eine
    Zeile steht."""
    if b.modul in BEFUND_OHNE_ZEILEN or _frog_text(b) or _hippo_text(b) or b.modul in ("koala", "panda"):
        return []
    if b.modul == "squirrel" and (_squirrel_text(b) or _squirrel_metall(b)):   # 20.11.2026: Text statt Messzeilen,
        return []                                                               # Metall: nur Prüfzeile
    if b.modul not in BEFUND_NUR_AUFFAELLIG:
        return list(b.befundteil)
    out = []
    for z, t in zip(b.befundteil, _treffer(b)):
        if _abschnitt_zeile(z) or t:
            out.append(z)
    return _ohne_leere_beschriftung(out)


def _ohne_leere_beschriftung(zeilen):
    return [z for i, z in enumerate(zeilen)
            if not _abschnitt_zeile(z) or (i + 1 < len(zeilen) and not _abschnitt_zeile(zeilen[i + 1]))]


def hat_inhalt(b):
    """Kommt von Baustein b etwas in den Befund (Befundzeilen nach dem Filter oder Ergebnispunkte)?"""
    if b.modul == "koala":
        return koala_hat_text(b)
    if b.modul == "panda":
        return bool(panda_text(b))
    if _hippo_text(b) or _squirrel_text(b) or frog_ohne_diagnose(b):   # RH 30: Messwerte ohne Diagnose
        return True
    return bool(befund_zeilen(b) or b.ergebnis)


def auffaellige_zeilen(bausteine):
    """Befundzeilen, aus deren Messwert ein Ergebnispunkt wurde, und die Ergebnispunkte selbst (in Baustein-Reihenfolge)."""
    out = []
    for b in bausteine or []:
        if _frog_text(b):                  # v3.19.8: die pathologischen Sätze und die lateinischen Begriffe
            bt = b.befundtext
            out += [s for s in bt["stellung"] + bt["gewoelbe"] if not _FROG_GEW_NORMAL.match(s) and s not in out]
            out += [t for t in (f"{x['text']} {x['seite']}".strip() for x in bt["begriffe"]) if t not in out]
            continue
        if _hippo_text(b):                 # v3.19.13: auffällige HIPPO-Sätze (nicht „Kein …“) und der Begriffe-Punkt
            bt = b.befundtext
            out += [s for s in bt["saetze"] + ([bt["ergebnis"]] if bt["ergebnis"] else [])
                    if not s.startswith(("Kein ", "Keine ")) and s not in out]
            continue
        if _squirrel_text(b):              # 20.11.2026: die Skoliose-Sätze und der Ergebnispunkt
            bt = b.befundtext
            out += [s for s in bt["saetze"] + ([bt["ergebnis"]] if bt["ergebnis"] else []) if s not in out]
            continue
        if b.modul == "panda":             # 19.11.2026: der Knochenalter-Text nur, wenn retardiert/akzeleriert
            t = panda_text(b)
            if t and re.search(r"\b(?:retardiert|akzeleriert)\.", t) and t not in out:
                out.append(t)
            continue
        if b.modul == "koala":             # 18.11.2026: der KOALA-Text (Sätze der K&L-Tabelle + Gonarthrose-Punkt)
            plan = _koala_plan(b, "", "", "", [])
            out += [s for s in (plan[0] + plan[1] if plan else []) if s not in out]
            continue
        for z, t in zip(b.befundteil, _treffer(b)):
            if t:
                out.append(z)
        out += [p for p in b.ergebnis if p not in out and not ist_schluss(p)]
    return out


# v3.18.0: Vorwerte. Der Abholer schreibt den früheren Wert derselben Messgröße in die Quellen-Klammer der Befundzeile
# („Cobb-Winkel 18° (IB Lab SQUIRREL; Vorwert 03/2024: 12°, IB Lab).“) – er steht damit wörtlich im Gerüst und im Befund (die
# Zeile bleibt 1:1, messwert()/messung_text() lesen sie unverändert). Neu ist nur die Anzeige: der Vorwert-Teil grau im
# Befund-Feld, die Liste in den IB-Lab-Details. Ohne Vorwerte bleibt alles bit-gleich.
_VORWERT = re.compile(r"Vorwert \d{2}/\d{4}: [^;()]+?(?=\)|;|$)")


def vorwert_stellen(bausteine):
    """Vorwert-Teile, die wörtlich in Befundzeilen stehen („Vorwert 03/2024: 12°, IB Lab“) — für die graue Anzeige."""
    out = []
    for b in bausteine or []:
        texte = [v["text"].strip() for v in b.vorwerte] + [m.group(0).strip() for z in b.befundteil
                                                           for m in _VORWERT.finditer(z)]
        for t in texte:
            if t and t not in out and any(t in z for z in b.befundteil):
                out.append(t)
    return out


def vorwert_zeilen(b):
    """„Cobb-Winkel 1. Krümmung: Vorwert 03/2024: 12°, IB Lab“ je Vorwert eines Bausteins (IB-Lab-Details)."""
    out = []
    for v in b.vorwerte:
        z = next((m for m in map(messwert, b.befundteil) if m and v["text"] in m.zeile), None)
        out.append(f"{z.name}: {v['text']}" if z else v["text"])
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
    mit_inhalt = [b for b in bausteine or [] if hat_inhalt(b)]     # v3.18.8: nach dem Filter (befund_zeilen)
    if not mit_inhalt:
        return None
    templates = templates or {}
    gruppen = []                                 # [(titel, [Bausteine])] in Reihenfolge
    vorlagen = {}                                # Baustein → Text der Vorlage seiner CAS-Leistung (KOALA)
    for b in mit_inhalt:
        l = _leistung_fuer(b, cas_leistungen, templates)
        lv = cv.leistung_vorlage(l, templates) if l else None   # wie die Vorlagenwahl (Patella axial, GWS seitlich)
        name = (templates.get(lv) or {}).get("display_name") if lv else None
        if name:
            vorlagen[b.schluessel] = (templates.get(lv) or {}).get("body")
        if b.modul == "panda":
            if not panda_text(b, cas_leistungen):
                continue
            name, l = PANDA_TITEL, {}       # Titel wie die Knochenalter-Befunde der Ordination
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
        je = {}                                  # Baustein → (Befundzeilen, Ergebnispunkte)
        for b in bs:
            if b.modul == "panda":               # 19.11.2026: nur der Knochenalter-Text als Ergebnisbefund
                je[b.schluessel] = ([], [panda_text(b, cas_leistungen)])
            elif b.modul == "koala":             # 18.11.2026: Knie-Vorlage mit KOALA-Text (bzw. nur die Sätze)
                je[b.schluessel] = _koala_geruest(b, titel, vorlagen.get(b.schluessel))
            elif _hippo_text(b):                 # v3.19.13: Becken-/Hüft-Vorlage mit den HIPPO-Sätzen (bzw. nur die Sätze)
                je[b.schluessel] = _hippo_geruest(b, titel, vorlagen.get(b.schluessel), _vorlage_ergebnis(
                    _leistung_fuer(b, cas_leistungen, templates), templates))
            elif _squirrel_text(b):              # 20.11.2026: Wirbelsäulen-Vorlage mit den Skoliose-Sätzen (bzw. nur die Sätze)
                je[b.schluessel] = _squirrel_geruest(b, vorlagen.get(b.schluessel), _vorlage_ergebnis(
                    _leistung_fuer(b, cas_leistungen, templates), templates))
            elif _frog_text(b):                  # v3.19.8: nur die FROG-Sätze (ohne Vorlagentext) + Begriffe + Schluss
                plan = _frog_plan(b, titel, Abschnitt(titel, 0, 0).seite, "", [])
                je[b.schluessel] = (_frog_zeilen(plan, punkte=False), _frog_punkte(plan)) if plan else ([], [])
            else:
                je[b.schluessel] = (befund_zeilen(b), list(b.ergebnis))
            e.behandelt[b.schluessel] = b.version
        befund = [z for b in bs for z in je[b.schluessel][0]]
        punkte = [p for b in bs for p in je[b.schluessel][1]]
        punkte = [p for p in punkte if not ist_schluss(p)] + [p for p in punkte if ist_schluss(p)]
        if not befund and not punkte:            # z. B. Vorfuß mit FROG nur seitlich auffällig: nichts für diese Untersuchung
            continue
        block = [f"## {titel}"]
        if befund:
            block += ["", "## Befund"] + befund
        if punkte:
            block += ["", br.ergebnis_nummerieren("## Ergebnis\n" + "\n".join(punkte))]
        teile.append("\n".join(block))
        for b in bs:
            e.eingesetzt[b.schluessel] = je[b.schluessel][0] + je[b.schluessel][1]
            e.zuordnung[b.modul] = titel
    if not teile:
        return None
    e.report = "\n\n".join(teile).strip()
    e.zeilen = [z for zs in e.eingesetzt.values() for z in zs]
    return e
