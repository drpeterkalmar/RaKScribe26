"""CAS-Leistungen als Vorrang-Hinweis für die Vorlagenwahl (v3.12.0) — reine Funktionen, ohne Tk/Windows testbar.

Peter 13.10.2026: „Könnte RaKScribe von CAS erfahren, welche Untersuchungsart wir gleich diktieren werden, damit er sich
besser darauf vorbereiten kann? … Allerdings musst du bedenken, dass du vielleicht teilweise eine Mischung aus
verschiedenen Untersuchungen in einem Diktat hast.“
Die RaKScribe-Brücke reicht die Leistungen des CAS-Eintrags nach (cas_auftrag.py: cas_leistungen_<id>.json, je Leistung
Kürzel, Kurztext, Modalität, Seite und die RaKScribe-Vorlage aus der privaten Zuordnung der Praxis). Hier gilt:
  - Die Liste ist ein VORRANG-HINWEIS, kein Zwang. Die Erkennung aus dem Diktat (detect.py) läuft immer.
  - Erkennt das Diktat eine Region aus der CAS-Liste → diese Vorlage (bei gleicher Region und Modalität die genauere des
    Diktats, z. B. Knie-TEP). Nennt das Diktat nur die Region, CAS aber eine andere Modalität (Knie + „Sono Knie“) →
    CAS-Vorlage. Erkennt es nur „allgemein“ → die CAS-Vorlage, wenn es genau eine gibt.
  - Nennt das Diktat klar eine Region, die NICHT in der CAS-Liste steht → Diktat gewinnt, Hinweis „nicht in den
    CAS-Leistungen“. CAS-Leistung ohne passenden Diktat-Abschnitt → Hinweis „<Leistung> laut CAS, nicht diktiert“.
  - Mehrere CAS-Vorlagen: das Diktat wird zusätzlich zum Regionen-Trenner an Satzanfängen geteilt, die eine andere
    CAS-Untersuchung nennen (z. B. „Fuß links: … LWS: …“) → je Untersuchung ein eigener Befund in Diktat-Reihenfolge.
  - Leistungen „ohne Vorlage“ (Abrechnungsposten) werden ignoriert.
Ohne Leistungen (keine Datei, alte Brücke, leer) wird diese Datei gar nicht benutzt — Einzelbefunde bleiben bit-gleich.
Keine Praxis-Kataloge hier: nur allgemeine Anatomie-Wörter (öffentliches Repo).
Tests: tests/offline/test_cas_leistungen.py
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

import befund_regeln as br

# Region einer Vorlage bzw. Leistung (Schlüssel + Anzeigename bzw. Kurztext). Allgemeine Anatomie, keine Praxisdaten.
REGIONEN = [
    ("hws", r"\bhws\b|halswirbel|zervikal|cervikal|zerviko|cervico|\bhw\b"),
    ("bws", r"\bbws\b|brustwirbel"),
    ("lws", r"\blws\b|lendenwirbel|lumbal"),
    ("ws", r"wirbelsäule gesamt|gesamte wirbelsäule|ganzaufnahme der wirbelsäule|\bwirbelsäule\b|\bws\b"),
    ("becken", r"becken|iliosakral|sakroiliak|kreuzbein|steißbein|steissbein|sacrum|sakrum"),
    ("huefte", r"hüft|hueft|coxa|coxarthr|femurkopf|schenkelhals"),
    ("oberschenkel", r"oberschenkel|\bfemur\b"),
    ("knie", r"knie|patella|gonarthr"),
    ("unterschenkel", r"unterschenkel|tibia|fibula|ganzbein"),
    ("sprunggelenk", r"sprunggelenk|\bosg\b|\busg\b|malleol"),
    # kaiscribe-georg-2011-n1 (RH 84, RH 30): Metatarsale/Jones-Fraktur und akzessorische Fußknochen gehören zum Fuß
    ("fuss", r"fuß|fuss|zehe|calcaneus|kalkaneus|ferse|achilles|hallux|metatars|\bjones|os tibiale|os trigonum|"
             r"os peroneum|naviculare cornutum|os intermetatarse|os vesalian"),
    ("schulter", r"schulter|akromio|acromio|clavicula|klavikula|schlüsselbein|scapula|skapula|supraspinatus|rotatoren"),
    ("oberarm", r"oberarm|\bhumerus\b"),
    ("ellbogen", r"el(?:l|le)n?bogen|olecranon"),
    ("unterarm", r"unterarm|vorderarm|\bradius\b|\bulna\b"),
    ("hand", r"\bhand|finger|daumen|karpal|scaphoid|skaphoid|navicular(?!e cornutum)|kahnbein|mittelhand|handwurzel"),
    ("thorax", r"thorax|lunge|pulmo|rippe|sternum"),
    ("abdomen", r"abdomen|bauch|leber|galle|pankreas|milz|niere|harnblase|urogramm|pyelogra|retroperit"),
    ("mamma", r"mamma|mammo"),
    ("schaedel", r"schädel|schaedel|orbita|nasenbein|jochb|sella|felsenbein|schläfenbein|fernröntgen|\bcct\b|gehirn"),
    ("nnh", r"nasennebenhöhle|\bnnh\b"),
    ("kiefer", r"kiefer|zahn|orthopantomogramm|\bopg\b|\bdvt\b|volumentomogr"),
    ("schilddruese", r"schilddrüse"),
    ("halsweichteile", r"halsweichteil|halsorgan"),
    ("halsgefaesse", r"halsgef|halsarter|carotis|karotis|vertebral"),
    ("beinvenen", r"beinvene|extremitätenvene|varize|varik|phlebo|poplitea"),
    ("nerv", r"\bnerv|nervus|\bn\. |plexus|medianus|ulnaris|radialis|ischiadicus|peroneus|tibialis|femoralis|pudendus"),
    ("weichteile", r"weichteil|muskel|muskul|gastrocnem|lymphknoten|hämatom|bauchdecke"),
    ("dexa", r"dexa|knochendichte|densitometr"),
    ("schluck", r"ösophag|oesophag|schluck|breischluck"),
    ("magen_darm", r"magen|duoden|dünndarm|darmpassage|\bmdp\b|kolon|colon|irrigo"),
]
_REGIONEN_RE = [(name, re.compile(muster)) for name, muster in REGIONEN]
# Kombi-Vorlagen gehören zu mehreren Regionen (Ganzaufnahme = alle Wirbelsäulenabschnitte)
_WS_ALLE = {"hws", "bws", "lws"}

# Füllwörter am Satzanfang (zählen nicht zu den ersten zwei Wörtern, an denen ein Abschnitt erkannt wird)
_FUELL = {"röntgen", "roentgen", "rö", "sonographie", "sonografie", "sono", "ultraschall", "duplex", "farbduplex",
          "der", "die", "das", "des", "dem", "den", "vom", "von", "beim", "bei", "im", "am", "in", "2", "zwei",
          "ebenen", "ebene", "und", "mit", "rechts", "links", "beidseits", "bds", "rechte", "rechten", "rechter",
          "rechtes", "linke", "linken", "linker", "linkes", "beide", "beiden", "beider", "aufnahme", "aufnahmen",
          "untersuchung", "ct", "mr", "mrt", "a.-p.", "ap", "seitlich", "zusätzlich", "zusaetzlich", "dann", "nun"}
# v3.13.1: Wörter, nach denen eine Region NICHT einen neuen Abschnitt beginnt („Ausstrahlung in die BWS“, „HWS und BWS“)
_KEIN_SCHNITT_NACH = {"in", "ins", "die", "der", "das", "den", "dem", "des", "zur", "zum", "zu", "bis", "und", "sowie",
                      "oder", "bzw", "bzw.", "auch", "mit", "ohne", "von", "vom", "im", "am", "an", "auf", "über",
                      "ueber", "nach", "gegen", "beider", "beide", "beiden", "als", "wie", "aus", "durch", "entlang",
                      "unterhalb", "oberhalb", "höhe", "hoehe", "bereich", "übergang", "uebergang", "richtung",
                      "betont", "betonter", "betonte", "nicht", "kein", "keine", "keiner", "einer", "eine", "ein",
                      "seiner", "ihrer", "zwischen", "bei", "beim", "ganze", "ganzen", "gesamte", "gesamten"}
_MODWORT = {"röntgen", "roentgen", "rö", "sonographie", "sonografie", "sono", "ultraschall", "duplex", "farbduplex",
            "ct", "mr", "mrt"}
_SEITENWORT = {"rechts", "links", "beidseits", "bds", "rechte", "rechten", "rechter", "rechtes", "linke", "linken",
               "linker", "linkes", "beide", "beiden", "beider"}
# Vorspann eines neuen Abschnitts („Sonographie der rechten Schulter“, „Röntgen der LWS“) — zählt nur mit Modalitäts-
# oder Seitenwort; reine Artikel davor („in die BWS“) sind Rückbezug
_VORSPANN = _MODWORT | _SEITENWORT | {"der", "die", "das", "des", "dem", "den", "2", "zwei", "ebenen"}
_SATZGRENZE = re.compile(r"[.!?;:\n]+|(?<!\w)(?:punkt|neue\s+zeile|neuzeile|absatz)(?!\w)", re.I)
_SEITE_GEGEN = {"rechts": "links", "links": "rechts"}


def regionen(text):
    """Regionen (Namen aus REGIONEN) in einem Text: Vorlagen-Key + Anzeigename, CAS-Kurztext oder Diktat-Abschnitt.
    „Wirbelsäule“ ohne Abschnitt (Ganzaufnahme, gesamte WS) zählt zu HWS, BWS und LWS."""
    t = (text or "").lower().replace("_", " ")
    out = {name for name, rx in _REGIONEN_RE if rx.search(t)}
    if "ws" in out:
        out.discard("ws")
        out |= _WS_ALLE
    return out


def _anzeige(key, templates):
    return (templates.get(key) or {}).get("display_name", "") if key else ""


def vorlagen_text(key, templates):
    return f"{key or ''} {_anzeige(key, templates)}"


def modalitaet_key(key, templates):
    """Modalität einer Vorlage: Sono | CT | MR | Röntgen (inkl. Durchleuchtung, Mammographie, DEXA, OPG/DVT) | None."""
    if not key or key == "allgemein" or key.startswith("baustein:"):
        return None
    t = vorlagen_text(key, templates).lower()
    if re.search(r"sono|ultraschall|duplex|varizen", t):
        return "Sono"
    if key.startswith(("mr_", "mr-")):
        return "MR"
    if key.startswith(("ct_", "cct", "polytrauma_ct")):
        return "CT"
    return "Röntgen"


def modalitaet_text(text):
    """Modalität, die ein Diktat-Abschnitt selbst nennt (genau eine), sonst None."""
    t = (text or "").lower()
    gefunden = set()
    if re.search(r"sono|ultraschall|duplex|doppler|echograph", t):
        gefunden.add("Sono")
    if re.search(r"röntgen|roentgen|(?<!\w)rö(?!\w)|aufnahme|in (?:2|zwei) ebenen|mammogra(?:ph|f)|durchleucht", t):
        gefunden.add("Röntgen")
    if re.search(r"(?<!\w)c?ct(?!\w)|computertomogra", t):
        gefunden.add("CT")
    if re.search(r"(?<!\w)mrt?(?!\w)|magnetresonanz|kernspin", t):
        gefunden.add("MR")
    return gefunden.pop() if len(gefunden) == 1 else None


def generisch(key, templates):
    """Sammel-Vorlage ohne eigene Region: allgemein bzw. „(Allgemein)“ im Anzeigenamen."""
    return not key or key == "allgemein" or "(allgemein)" in _anzeige(key, templates).lower()


# ── CAS-Leistungen aufbereiten ──────────────────────────────────────────────────────────────────────────────────────
@dataclass
class Leistung:
    kurz: str
    label: str                     # Anzeige im Band und im Hinweis, z. B. „HWS“, „Schulter re. (Sono)“
    vorlage: Optional[str]         # gültiger Vorlagen-Key oder None (unsicher/unbekannt)
    modalitaet: Optional[str]
    seite: Optional[str]
    regionen: set = field(default_factory=set)
    funktion_grund: Optional[str] = None   # kaiscribe-funktion-n1: Funktionsaufnahmen-Leistung → Grund-Vorlage (HWS/LWS in 2 Ebenen)

    @property
    def spezifisch(self):
        return self.vorlage is not None and self.vorlage != "allgemein"


_BEIDSEITS_TEXT = re.compile(r"(?<![a-zäöü])(?:bds|beidseits|beidseitig\w*|bilateral\w*|beide[nr]?)(?![a-zäöü])", re.I)


def seite_aus_text(text):
    """v3.15.4: „beidseits“, wenn der Leistungstext beidseitig ist (bds./beidseits/bilateral) und die Brücke keine Seite
    mitgab (die Brücke kennt „bilateral“ nicht) — sonst None (die Brücke entscheidet rechts/links)."""
    return "beidseits" if _BEIDSEITS_TEXT.search(text or "") else None


# paarige Regionen (Extremitäten/Gelenke) — Wirbelsäule, Becken, Thorax, Schädel bekommen nie eine Seite
PAARIG = {"schulter", "oberarm", "ellbogen", "unterarm", "hand", "huefte", "oberschenkel", "knie", "unterschenkel",
          "sprunggelenk", "fuss"}


# #344 (kniepatl/kniepatr/kniepat2 „Knie li mit Patella axial“): Die Brücke ordnet der Leistung die Grund-
# Vorlage zu (kniegelenk_in_2_ebenen) → Titel ohne „Patella axial“. Nennt der Leistungstext den Zusatz, gilt die genauere
# Vorlage (erweitert → Grund-Vorlage, Muster im CAS-Text); das Diktat mit der Grund-Vorlage bestätigt sie (abgleich).
ZUSATZ_VORLAGEN = {
    "kniegelenk_in_2_ebenen_mit_patella_axial": ("kniegelenk_in_2_ebenen",
                                                 re.compile(r"patella\w*\.?\s*(?:ax|tang)|(?:axial|tangential)\w*\s+patella", re.I)),
}


def zusatz_vorlage(v, text, templates):
    """CAS-Vorlage v mit Zusatz aus dem Leistungstext („mit Patella axial“) → erweiterte Vorlage, sonst v."""
    for erweitert, (grund, muster) in ZUSATZ_VORLAGEN.items():
        if v == grund and erweitert in templates and muster.search(text or ""):
            return erweitert
    return v


# kaiscribe-funktion-n1 (RH 97, Peter 17.11.2026: „KaiScribe hat Funktion vergessen“): Die Brücke ordnet „HWS ap u. seitl.
# incl.Funktion“ (auch „HWS + Funktion“, „LWS mit Funktionaufnahmen“) der Funktions-Vorlage zu. Das Diktat „HWS …“ erkennt
# die Grund-Vorlage, abgleich nahm sie als die genauere – die Funktionsaufnahmen fielen still weg (Titel + Befund).
# Jetzt: Leistungstext mit Grund-Untersuchung UND „Funktion“ = zwei Untersuchungen (Grund-Vorlage + Funktions-Vorlage),
# je ein eigener Abschnitt. Nur „Funktionsaufnahmen HWS“ (keine Grund-Untersuchung) = nur die Funktions-Vorlage, das
# Diktat „HWS …“ bestätigt sie (wie #344 Patella axial). Nur der Leistungstext zählt, nie das Diktat („Funktionsaufnahmen
# empfohlen“ macht keinen Abschnitt). BWS hat keine Funktions-Vorlage → unverändert.
FUNKTION_VORLAGEN = {"hws": ("halswirbelsäule_in_2_ebenen", "funktionsaufnahmen_der_halswirbelsäule"),
                     "lws": ("lendenwirbelsäule_in_2_ebenen", "funktionsaufnahmen_der_lendenwirbelsäule")}
FUNKTION_LABEL = {"hws": "Funktion HWS", "lws": "Funktion LWS"}
_FUNKTION_TEXT = re.compile(r"funktion", re.I)
_NUR_FUNKTION = re.compile(r"^\W*funktion", re.I)
# diktierte Sätze über die Funktionsaufnahmen (Beuge-/Streckaufnahmen)
_FUNKTION_DIKTAT = re.compile(r"funktion|flexion|inklination|reklination|beugeaufnahme|bewegungsdiagramm", re.I)


def funktion_region(text, v, templates):
    """„hws“/„lws“, wenn der Leistungstext Funktionsaufnahmen nennt und die Brücke die Grund- oder Funktions-Vorlage
    dieser Region zuordnete (bzw. keine), sonst None."""
    if not _FUNKTION_TEXT.search(text or ""):
        return None
    reg = regionen(text) & set(FUNKTION_VORLAGEN)
    if len(reg) != 1:
        return None
    r = reg.pop()
    grund, funk = FUNKTION_VORLAGEN[r]
    if grund not in templates or funk not in templates or v not in (None, grund, funk):
        return None
    return r


def beidseits(w):
    """v3.15.4 (Peter 15.10., „Handgelenk bds.“ + Diktat „SL-Spalt links“ → nur „Handgelenk links“): Vorlagenwahl mit
    beidseitiger CAS-Leistung einer paarigen Region → der Befund ist IMMER beidseitig (deterministisch, nicht der KI
    überlassen)."""
    return (w is not None and w.leistung is not None and w.leistung.seite == "beidseits"
            and bool(w.leistung.regionen & PAARIG))


_TITEL_SEITE = re.compile(r"(?<![\wäöüß])(?:rechts|links|re\.|li\.|rechte[rsnm]?|linke[rsnm]?|bds\.?|beidseitig\w*)"
                          r"(?![\wäöüß])\s*", re.I)


def titel_beidseits(titel):
    """„Handgelenk links in 2 Ebenen“ → „Handgelenk beidseits in 2 Ebenen“ (Seite ersetzt bzw. ergänzt)."""
    t = " ".join(_TITEL_SEITE.sub("", titel or "").split())
    return br.titel_mit_seite(t, "beidseits") if "beidseits" not in t.lower() else t


def report_beidseits(report):
    """Untersuchungs-Überschrift(en) eines Befunds (nicht Befund/Ergebnis) auf „beidseits“ setzen."""
    out = []
    for z in (report or "").split("\n"):
        k = z.strip()
        if k.startswith("## ") and k[3:].strip().rstrip(":").lower() not in ("befund", "ergebnis"):
            z = "## " + titel_beidseits(k[3:].strip())
        out.append(z)
    return "\n".join(out)


def beidseits_block(w):
    """<cas_beidseits> für den Gen-Prompt (nur mit beidseitiger CAS-Leistung; sonst bleibt der Prompt bit-gleich)."""
    return ("<cas_beidseits>\n"
            f"Die CAS-Leistung „{w.leistung.label}“ ist BEIDSEITS: Es entsteht EIN beidseitiger Befund. Die Überschrift "
            "enthält „beidseits“ (z. B. „## Handgelenk beidseits in 2 Ebenen“), auch wenn das Diktat nur eine Seite "
            "nennt. Befundtext: Die Normalbefund-Sätze der Vorlage gelten für beide Seiten (wo nötig „beidseits“); eine "
            "diktierte Pathologie steht mit ihrer Seite („Links …“) an der Stelle des betroffenen Normalsatzes, der Rest "
            "dieses Satzes bleibt als „ansonsten …“ bzw. „rechts …“ stehen; die nicht diktierte Seite ist unauffällig. "
            "Ergebnis: jede Pathologie mit ihrer Seite als nummerierter Punkt; bei einer auffälligen Seite KEIN "
            "„Regelrechte Darstellung …“ für die ganze Untersuchung.\n"
            "</cas_beidseits>")


def label(text, kurz, modalitaet):
    """Kurzname für Band/Hinweis aus dem CAS-Kurztext: „Sonographie der Schulter re.“ → „Schulter re. (Sono)“."""
    t = (text or "").strip() or (kurz or "").strip()
    if modalitaet == "Sono":
        rest = re.sub(r"^(?:sonographie|sonografie|sonogr\.|sono|ultraschall)\s+(?:der|des|d\.)?\s*", "", t, flags=re.I)
        if rest != t and rest:
            t = rest[0].upper() + rest[1:] + " (Sono)"
        elif not re.search(r"sono|ultraschall|duplex|doppler", t, re.I):
            t += " (Sono)"
    elif modalitaet in ("CT", "MR") and not re.search(rf"(?<!\w){modalitaet}(?!\w)", t, re.I):
        t += f" ({modalitaet})"
    return t if len(t) <= 34 else t[:33].rstrip() + "…"


class CasHinweis:
    """Die für die Vorlagenwahl relevanten CAS-Leistungen eines Auftrags (ohne Abrechnungsposten)."""

    def __init__(self, leistungen, templates):
        self.alle = []
        for l in leistungen or []:
            d = l if isinstance(l, dict) else vars(l)
            if d.get("ohne_vorlage"):
                continue
            v = d.get("vorlage")
            if v is not None and v not in templates:
                v = None                     # Key aus einer neueren Zuordnung, den diese RaKScribe nicht kennt
            text = d.get("text") or ""
            v = zusatz_vorlage(v, text, templates)
            fr = funktion_region(text, v, templates)
            if fr:                           # kaiscribe-funktion-n1: Grund-Untersuchung + Funktionsaufnahmen
                grund, funk = FUNKTION_VORLAGEN[fr]
                if not _NUR_FUNKTION.match(text):
                    self._neu(d, text, grund, templates)
                self._neu(d, text, funk, templates, funktion_grund=grund,
                          anzeige=None if _NUR_FUNKTION.match(text) else FUNKTION_LABEL[fr])
                continue
            self._neu(d, text, v, templates)

    def _neu(self, d, text, v, templates, funktion_grund=None, anzeige=None):
        mod = modalitaet_key(v, templates) if v and not generisch(v, templates) else None
        mod = mod or d.get("modalitaet")
        self.alle.append(Leistung(
            kurz=str(d.get("kurz") or ""), label=anzeige or label(text, d.get("kurz"), mod), vorlage=v, modalitaet=mod,
            seite=d.get("seite") or seite_aus_text(text),
            regionen=regionen(text + " " + (vorlagen_text(v, templates) if v else "")), funktion_grund=funktion_grund))

    def __bool__(self):
        return bool(self.alle)

    @property
    def mit_vorlage(self):
        return [l for l in self.alle if l.spezifisch]

    def vorlagen(self):
        """Verschiedene spezifische CAS-Vorlagen in CAS-Reihenfolge."""
        out = []
        for l in self.mit_vorlage:
            if l.vorlage not in out:
                out.append(l.vorlage)
        return out


# ── Abgleich Diktat ↔ CAS ───────────────────────────────────────────────────────────────────────────────────────────
_GESCHLECHT = re.compile(r"_(?:weiblich|maennlich)$")
_GESCHLECHT_DIKTIERT = re.compile(r"weiblich|männlich|maennlich|\bfrau\b|\bmann\b|prostata|uterus|ovar|adnex", re.I)


def _nur_geschlecht_offen(key, cas_vorlage, text):
    """v3.16.2 (Ordi-E2E 15.10.: CAS „Sono Abdomen F.“ = weiblich, RaKScribe nahm „männlich“): Diktat- und CAS-Vorlage
    unterscheiden sich nur in der Geschlechts-Endung, und das Diktat nennt kein Geschlecht (detect nimmt dann immer
    „männlich“) → die CAS-Leistung kennt das Geschlecht, ihre Vorlage gilt."""
    return (bool(cas_vorlage) and cas_vorlage != key and bool(_GESCHLECHT.search(key or ""))
            and _GESCHLECHT.sub("", key) == _GESCHLECHT.sub("", cas_vorlage) and not _GESCHLECHT_DIKTIERT.search(text or ""))


def abgleich(key, text, cas, templates):
    """Passt die erkannte Vorlage key (Abschnitt text) zu einer CAS-Leistung? → (Leistung, gewählte Vorlage) | (None, None).
    Gleiche Vorlage → sie. Gleiche Region + gleiche Modalität → die des Diktats (genauer, z. B. Knie-TEP statt Knie),
    außer sie ist eine Sammel-Vorlage oder unterscheidet sich nur im nicht diktierten Geschlecht (v3.16.2: dann CAS). Gleiche Region, andere Modalität → die CAS-Vorlage, wenn das Diktat selbst keine
    andere Modalität nennt (Diktat „Knie rechts: Baker-Zyste“, CAS „Sono Knie“)."""
    if not key or key.startswith("baustein:"):
        return None, None
    for l in cas.alle:
        if l.vorlage and l.vorlage == key:
            return l, key
    for l in cas.alle:   # #344: Diktat „Knie links …“ ↔ CAS „Knie li mit Patella axial“ → die erweiterte CAS-Vorlage
        if l.vorlage in ZUSATZ_VORLAGEN and ZUSATZ_VORLAGEN[l.vorlage][0] == key:
            return l, l.vorlage
    for l in cas.alle:   # kaiscribe-funktion-n1: Diktat „HWS …“ ↔ nur „Funktionsaufnahmen HWS“ laut CAS → Funktions-Vorlage
        if l.funktion_grund and l.funktion_grund == key:
            return l, l.vorlage
    reg = regionen(vorlagen_text(key, templates))
    if not reg:
        return None, None
    mod_k = modalitaet_key(key, templates)
    mod_t = modalitaet_text(text)
    for l in cas.alle:
        if not (reg & l.regionen):
            continue
        if l.modalitaet is None or mod_k == l.modalitaet:
            if _nur_geschlecht_offen(key, l.vorlage, text):
                return l, l.vorlage
            return l, (key if not generisch(key, templates) else (l.vorlage or key))
        if mod_t is None or mod_t == l.modalitaet:
            return l, (l.vorlage or key)
    return None, None


def saetze(text):
    """[(start, satz)] — Satzgrenzen wie der Regionen-Trenner (Satzzeichen, Doppelpunkt, „Punkt“, „neue Zeile“)."""
    out, start = [], 0
    for m in _SATZGRENZE.finditer(text or ""):
        if m.start() > start and text[start:m.start()].strip():
            out.append((start, text[start:m.start()]))
        start = m.end()
    if start < len(text or "") and text[start:].strip():
        out.append((start, text[start:]))
    return out


def kopf(satz):
    """Satzanfang bis einschließlich des zweiten inhaltlichen Wortes (Füllwörter wie „Röntgen der rechten“ zählen nicht),
    höchstens 8 Wörter: „Sonographie der rechten Schulter“, „HWS in 2 Ebenen“, aber nicht „Keine Ausstrahlung in die HWS“."""
    worte = (satz or "").split()
    n, out = 0, []
    for w in worte[:8]:
        out.append(w)
        if w.lower().strip(",()") not in _FUELL:
            n += 1
            if n == 2:
                break
    return " ".join(out)


def mehr_regionen(key, leistung, text, templates):
    """v3.18.7: Regionen der Vorlage key, die die CAS-Leistung nicht hat und die der Diktat-Abschnitt text selbst nennt
    (Beckenübersicht und Hüfte ↔ CAS „Becken“ + „Hüfte“ im Diktat) → nicht leer. Fingerendgelenke ↔ Hand: gleiche Region."""
    extra = regionen(vorlagen_text(key, templates)) - leistung.regionen
    return extra & regionen(text)


@dataclass
class Wahl:
    vorlage: str
    art: str                       # bestaetigt | kopf | cas | satz | unklar | diktat | baustein
    leistung: Optional[Leistung] = None
    erkannt: str = ""              # was detect.py allein gewählt hätte


def wahl(seg, cas, templates, erkennen):
    """Vorlage für EINEN Diktat-Abschnitt (Rho-Auslöser schon entfernt). erkennen = detect.detect_template(text)."""
    d = erkennen(seg)
    l, v = abgleich(d, seg, cas, templates)
    s = saetze(seg)
    if l and l.vorlage and v != l.vorlage and s:
        # v3.16.5 (Edge-Case-Runde 1 am Büro-PC 17.10., CAS „Hand inkl. Mittelhand li.“, Diktat „Hand in zwei Ebenen …
        # Arthrose der Fingerendgelenke“ → Titel „Finger …“): nennt der Abschnitt GLEICH AM ANFANG genau die
        # Untersuchung der CAS-Leistung, gilt deren Vorlage – ein Befundwort weiter hinten („Fingerendgelenke“) macht
        # daraus keine andere Untersuchung. Eine genauere Untersuchung am Anfang („Knie-TEP rechts …“) bleibt.
        # v3.18.7 (RH 99/128, Peter 12.11.2026: CAS „Becken“, Diktat „Beckenübersicht … Hüftgelenk rechts …“ → nur
        # „Beckenübersicht stehend“, die Hüfte fiel weg): deckt die Vorlage des ganzen Abschnitts (Beckenübersicht und
        # Hüfte) zusätzlich eine Region ab, die das Diktat auch nennt, bleibt sie – der Satzanfang stuft nicht herunter.
        if erkennen(kopf(s[0][1])) == l.vorlage and not mehr_regionen(v, l, seg, templates):
            return Wahl(l.vorlage, "kopf", l, d)
    if l:
        return Wahl(v, "bestaetigt", l, d)
    if s:
        dk = erkennen(kopf(s[0][1]))
        if dk != d:
            l, v = abgleich(dk, seg, cas, templates)
            if l:
                return Wahl(v, "kopf", l, d)
    if generisch(d, templates):
        mod_d = modalitaet_key(d, templates) or modalitaet_text(seg)
        # kaiscribe-funktion-n1: der Funktions-Teil von „HWS + Funktion“ zählt nicht als eigene Kandidatin (er folgt der
        # Grund-Untersuchung, funktion_ergaenzen)
        kandidaten = [l for l in cas.mit_vorlage if (mod_d is None or l.modalitaet == mod_d) and not _funktion_teil(l, cas)]
        if len({l.vorlage for l in kandidaten}) == 1:
            return Wahl(kandidaten[0].vorlage, "cas", kandidaten[0], d)
        for _, satz in s[1:]:
            ds = erkennen(kopf(satz))
            if not generisch(ds, templates):
                l, v = abgleich(ds, seg, cas, templates)
                if l:
                    return Wahl(v, "satz", l, d)
        return Wahl(d, "unklar", None, d)
    return Wahl(d, "diktat", None, d)


def _wort(w):
    return w.lower().strip(",;:()\"'")


def _innen_starts(satz, cas, templates, erkennen, annehmen):
    """v3.13.1 (Peter 14.10.: „BWS Röntgen unauffällig LWS Röntgen Hyperlordose, ansonsten unauffällig“ — ohne
    Satzzeichen, BWS fiel still weg): Stellen IM Satz, an denen eine CAS-Region als neuer Abschnitt beginnt →
    [(pos_im_satz, leistung)]. Nur wenn (1) das Regionswort selbst zu dieser CAS-Leistung gehört, (2) davor kein
    Bindewort/keine Präposition steht („in die BWS“, „HWS und BWS“) und kein Bindestrich-Kompositum vorliegt
    („BWS-Kyphose“), (3) seit dem letzten Abschnittsbeginn schon Befundtext steht („BWS LWS unauffällig“ trennt nicht).
    Modalitätswörter direkt davor („… unauffällig Röntgen LWS …“) gehören zum neuen Abschnitt.
    annehmen(leistung) → True, wenn der Aufrufer dort wirklich einen neuen Abschnitt beginnt (andere, noch nicht
    befundete Untersuchung); nur dann zählt der Befundtext neu."""
    worte = list(re.finditer(r"\S+", satz))
    out, inhalt = [], False
    for i, m in enumerate(worte):
        w = _wort(m.group())
        reg = regionen(w) if "-" not in m.group().strip(",;:") else set()
        if i > 0 and reg:
            s = i
            while s > 0 and _wort(worte[s - 1].group()) in _VORSPANN:
                s -= 1
            if not any(_wort(x.group()) in (_MODWORT | _SEITENWORT) for x in worte[s:i]):
                s = i                    # nur Artikel davor → kein Vorspann
            davor = _wort(worte[s - 1].group()) if s > 0 else ""
            if s > 0 and inhalt and davor not in _KEIN_SCHNITT_NACH and not davor.endswith("-"):
                rest = satz[worte[s].start():]
                k = kopf(rest)
                l, _ = abgleich(erkennen(br.rho_erkennen(k)[0]), k, cas, templates)
                if l is not None and (reg & l.regionen) and annehmen(worte[s].start(), l):
                    out.append((worte[s].start(), l))
                    inhalt = False
                    continue
        if reg:
            continue                     # Regionswort zählt nicht als Befundtext
        if w and w not in _FUELL:
            inhalt = True
    return out


def aufteilen(segmente, cas, templates, erkennen):
    """Mehrere CAS-Untersuchungen: Abschnitte zusätzlich an Satzanfängen teilen, die eine ANDERE, noch nicht befundete
    CAS-Untersuchung nennen — seit v3.13.1 auch mitten im Satz, wenn das Diktat ohne Satzzeichen ankommt (siehe
    _innen_starts). Eine Untersuchung beginnt nur einmal (Rückbezug trennt nicht). Text bleibt unverändert."""
    if len(set(l.vorlage or l.kurz for l in cas.alle if (l.spezifisch or l.regionen) and not _funktion_teil(l, cas))) < 2:
        return list(segmente)
    out, benutzt = [], set()
    for seg in segmente:
        starts, aktuell = [0], None
        for pos, satz in saetze(seg):
            k = kopf(satz)
            l, _ = abgleich(erkennen(br.rho_erkennen(k)[0]), k, cas, templates)
            if l is not None:
                ident = l.vorlage or l.kurz
                if aktuell is None:
                    aktuell = ident
                    benutzt.add(ident)
                elif ident != aktuell and ident not in benutzt:
                    starts.append(pos)
                    aktuell = ident
                    benutzt.add(ident)
            def annehmen(ipos, li, pos=pos):
                nonlocal aktuell
                ident = li.vorlage or li.kurz
                if aktuell is None or ident == aktuell or ident in benutzt:
                    return False
                starts.append(pos + ipos)
                aktuell = ident
                benutzt.add(ident)
                return True
            _innen_starts(satz, cas, templates, erkennen, annehmen)
        teile = [seg[a:b].strip(" ,;\n") for a, b in zip(starts, starts[1:] + [len(seg)])]
        out.extend(t for t in teile if t)
    return out


# ── kaiscribe-mehrfach-seitenlos-n1: Sätze nach Inhalt zuordnen ─────────────────────────────────────────────────────
# Georg 19.11.2026: „Wie funktioniert es, wenn ich 2 Untersuchungen habe?“ – CAS lws + bü, fließend diktiert ohne
# Regionsnennung („geringe Coxarthrose links, Osteochondrose L5/S1, Fibroostosen am Trochanter major beidseits, …“).
# Die CAS-Leistungen bestimmen, welche Befunde es gibt; jeder Satz/Teilsatz geht über seine Anatomie-Begriffe zu genau
# einer davon. Regionsnennung im Diktat hat Vorrang (Abschnitte aus split_regionen/aufteilen bleiben, ihr Satzanfang
# zählt als Begriff). Ohne Begriff (Osteopenie, „unauffällige Weichteile“, „rechts tiefer“) → zum vorangehenden
# Satz/Abschnitt. Begriffe zweier CAS-Untersuchungen in einem Satz → bleibt stehen + Prüfzeile; Begriff einer Region,
# die im CAS-Auftrag fehlt → bleibt stehen + Prüfzeile. Allgemeine Anatomie, keine Praxisdaten.
_INHALT_REGIONEN = {"hws", "bws", "lws", "becken", "huefte", "knie", "schulter", "ellbogen", "hand", "fuss",
                    "sprunggelenk", "thorax", "schaedel", "nnh"}
_INHALT_BEGRIFFE = [
    ({"lws"}, re.compile(r"(?<![a-zäöüß])(?:l\s?[1-5]|s\s?1|lwk\s?[1-5]?)(?![\d])", re.I)),
    ({"bws"}, re.compile(r"(?<![a-zäöüß])(?:th\s?(?:1[0-2]|[1-9])|bwk\s?(?:1[0-2]|[1-9])?)(?![\d])", re.I)),
    ({"hws"}, re.compile(r"(?<![a-zäöüß])(?:c\s?[1-7]|hwk\s?[1-7]?)(?![\d])", re.I)),
    ({"becken", "huefte"}, re.compile(r"coxarthr|koxarthr|hüftkopf|hueftkopf|pfannendach|acetabul|azetabul|(?<![a-zäöüß])isg"
                                      r"|iliosakral|symphyse|trochanter|spina\s+iliaca|(?<![a-zäöüß])sias(?![a-zäöüß])"
                                      r"|beckenschaufel|beckenkamm|beckenschiefstand|schenkelhals|femurkopf|sitzbein"
                                      r"|schambein|darmbein|(?<![a-zäöüß])os\s+ilium", re.I)),
    ({"knie"}, re.compile(r"kniegelenk|patell|femoropatell|femorotibial|gonarthr|tibiaplateau|menisk|kreuzband", re.I)),
]
# Wirbelsäulen-Begriffe ohne Höhe → die Wirbelsäulen-Untersuchung des Auftrags (nur wenn es genau eine gibt)
_INHALT_WS = re.compile(r"spondyl|osteochondro|lordose|kyphose|skoliose|wirbelkörper|bandscheib|intervertebral"
                        r"|deckplatte|grundplatte|facettengelenk|dornfortsatz|uncovertebral|unkovertebral", re.I)
_TEILSATZ = re.compile(r"[.!?;:\n]+|,(?!\d)|(?<!\w)(?:punkt|neue\s+zeile|neuzeile|absatz)(?!\w)", re.I)


def inhalt_regionen(text):
    """Anatomie-Regionen eines (Teil-)Satzes → (genau: Regionsname/Höhe/Begriff, allgemein: Wirbelsäulen-Begriff)."""
    genau = regionen(text) & _INHALT_REGIONEN
    if regionen(text) >= _WS_ALLE and not re.search(r"hws|bws|lws|hals|brust|lenden", text or "", re.I):
        genau -= _WS_ALLE                # „Wirbelsäule“ allein = allgemein
    for reg, rx in _INHALT_BEGRIFFE:
        if rx.search(text or ""):
            genau |= reg
    if genau & {"becken", "huefte"}:
        genau |= {"becken", "huefte"}
    allgemein = set(_WS_ALLE) if (_INHALT_WS.search(text or "") or regionen(text) >= _WS_ALLE) else set()
    return genau, allgemein


def _teilsaetze(seg):
    """[(a, b)] lückenlos über seg: je Teilsatz bis einschließlich seines Trenners (Satzzeichen, Komma, „Punkt“)."""
    out, a = [], 0
    for m in _TEILSATZ.finditer(seg):
        if seg[a:m.start()].strip():
            out.append((a, m.end()))
            a = m.end()
        elif out:
            out[-1] = (out[-1][0], m.end())
            a = m.end()
    if seg[a:].strip():
        out.append((a, len(seg)))
    elif out:
        out[-1] = (out[-1][0], len(seg))
    return out


def _untersuchungen(cas):
    out = []
    for l in cas.mit_vorlage:
        if not l.regionen or _funktion_teil(l, cas) or any((x.vorlage or x.kurz) == (l.vorlage or l.kurz) for x in out):
            continue
        out.append(l)
    return out


def _ziel(text, unters):
    """Ziel-Untersuchung eines Teilsatzes → (Leistung | None, Art): ziel | leer | unklar | fremd."""
    if br.rho_erkennen(text)[2]:
        ws = [u for u in unters if u.regionen & _WS_ALLE]
        return (ws[0], "ziel") if len(ws) == 1 else (None, "leer")
    genau, allgemein = inhalt_regionen(text)
    for reg in (genau, allgemein):
        if not reg:
            continue
        k = [u for u in unters if u.regionen & reg]
        if len(k) == 1:
            return k[0], "ziel"
        if len(k) > 1:
            return None, "unklar"
        if reg is genau:
            return None, "fremd"
    return None, "leer"


def _region_name(reg):
    namen = {"lws": "LWS", "bws": "BWS", "hws": "HWS", "becken": "Becken/Hüfte", "huefte": "Becken/Hüfte", "knie": "Knie",
             "schulter": "Schulter", "ellbogen": "Ellbogen", "hand": "Hand", "fuss": "Fuß", "sprunggelenk": "Sprunggelenk",
             "thorax": "Thorax", "schaedel": "Schädel", "nnh": "NNH"}
    return "/".join(dict.fromkeys(namen.get(r, r) for r in sorted(reg)))


def inhalt_zuordnen(segmente, cas, templates, erkennen):
    """Mehrere CAS-Untersuchungen: Teilsätze nach Inhalt auf die Untersuchungen verteilen (siehe oben).
    → (segmente, leistungen, hinweise): leistungen[i] = Untersuchung des Abschnitts i, wenn die Zuordnung ihn gebildet oder
    verändert hat (sonst None = Vorlagenwahl wie bisher); hinweise = Prüfzeilen. Nichts zu verteilen → unverändert."""
    unters = _untersuchungen(cas)
    if len(unters) < 2:
        return list(segmente), [None] * len(segmente), []
    ident = lambda l: l.vorlage or l.kurz  # noqa: E731
    heim = []
    for seg in segmente:
        w = wahl(br.rho_erkennen(seg)[0], cas, templates, erkennen)
        heim.append(next((u for u in unters if w.leistung is not None and ident(u) == ident(w.leistung)), None))
    einheiten, hinweise = [], []        # (Abschnitt, a, b, Ziel)
    for i, seg in enumerate(segmente):
        teile = _teilsaetze(seg)
        ziele = [_ziel(seg[a:b], unters) for a, b in teile]
        erstes = next((l for l, art in ziele if art == "ziel"), None)
        aktuell = heim[i] or erstes
        for (a, b), (l, art) in zip(teile, ziele):
            if art == "ziel":
                aktuell = l
            elif aktuell is not None and art in ("unklar", "fremd"):
                t = " ".join(seg[a:b].strip(" ,;:.").split())
                kurz_t = t if len(t) <= 40 else t[:39].rstrip() + "…"
                if art == "unklar":
                    hinweise.append(f"„{kurz_t}“: nicht eindeutig zuzuordnen, steht bei {aktuell.label} – bitte prüfen")
                else:
                    hinweise.append(f"„{kurz_t}“: {_region_name(inhalt_regionen(t)[0])} nicht im CAS-Auftrag, steht bei "
                                    f"{aktuell.label} – bitte prüfen")
            einheiten.append((i, a, b, aktuell))
    # Abschnitt bleibt bit-gleich, wenn alle seine Teilsätze bei ihm bleiben
    if all(z is None or (heim[i] is not None and ident(z) == ident(heim[i])) for i, _, _, z in einheiten) and \
            all(heim[i] is not None or all(z is None for j, _, _, z in einheiten if j == i) for i in range(len(segmente))):
        return list(segmente), [None] * len(segmente), hinweise
    eimer = {}                           # Schlüssel → [(Abschnitt, a, b)]
    for i, a, b, z in einheiten:
        if z is None or (heim[i] is not None and ident(z) == ident(heim[i])):
            k = ("seg", i)
        else:
            j = next((j for j, h in enumerate(heim) if h is not None and ident(h) == ident(z)), None)
            k = ("seg", j) if j is not None else ("neu", ident(z))
        eimer.setdefault(k, []).append((i, a, b))
    ziel_von = {("neu", ident(u)): u for u in unters}
    out, leist = [], []
    for k, teile in sorted(eimer.items(), key=lambda kv: min((i, a) for i, a, _ in kv[1])):
        teile.sort()
        if k[0] == "seg" and teile == [(k[1], a, b) for a, b in _teilsaetze(segmente[k[1]])]:
            out.append(segmente[k[1]])   # unverändert
            leist.append(None)
            continue
        text = " ".join(segmente[i][a:b].strip() for i, a, b in teile).strip(" ,;\n")
        out.append(text)
        leist.append(heim[k[1]] if k[0] == "seg" else ziel_von[k])
    return out, leist, hinweise


def hinweise(segmente, wahlen, cas, templates):
    """Sichtbare Hinweise (nichts wird ergänzt): Diktat-Region nicht in CAS, CAS-Leistung nicht diktiert, Seite."""
    out = []
    for w in wahlen:
        if w.art == "diktat":
            out.append(f"{_anzeige(w.vorlage, templates) or w.vorlage}: nicht in den CAS-Leistungen")
    if any(w.art == "baustein" for w in wahlen):
        return out                   # Ordi-Baustein: Region nicht sicher bestimmbar → keine „nicht diktiert“-Hinweise
    for l in cas.alle:
        if not (l.vorlage or l.regionen):
            continue
        if _funktion_teil(l, cas):
            continue                     # kaiscribe-funktion-n1: folgt der Grund-Untersuchung (funktion_ergaenzen)
        diktiert = erwaehnt = False
        for seg, w in zip(segmente, wahlen):
            if w.leistung is l or (l.vorlage and w.vorlage == l.vorlage) or \
                    (l.regionen & regionen(vorlagen_text(w.vorlage, templates))):
                diktiert = True
                break
            if l.regionen & regionen(seg):
                if not l.spezifisch or generisch(w.vorlage, templates):
                    diktiert = True      # unsichere Leistung bzw. Sammel-Vorlage: Region im Text genügt (wie bisher)
                    break
                erwaehnt = True
        if diktiert:
            continue
        # v3.13.1: Region steht im Diktat, hat aber keinen eigenen Befund bekommen → nicht mehr still schlucken
        out.append(f"{l.label}: im Diktat genannt, aber KEIN eigener Befund – bitte prüfen" if erwaehnt
                   else f"{l.label} laut CAS, nicht diktiert")
    for seg, w in zip(segmente, wahlen):
        if w.leistung is not None and w.leistung.seite in _SEITE_GEGEN:
            s = br.diktierte_seite(seg)
            if s == _SEITE_GEGEN[w.leistung.seite]:
                out.append(f"Seite: diktiert {s}, laut CAS {w.leistung.seite} ({w.leistung.label})")
        elif beidseits(w) and br.diktierte_seite(seg) in _SEITE_GEGEN:
            out.append(f"Laut CAS beidseits ({w.leistung.label}): Befund beidseits, diktiert nur {br.diktierte_seite(seg)}")
    return out


def _funktion_teil(l, cas):
    """Funktions-Teil einer Leistung mit Grund-Untersuchung („HWS ap u. seitl. incl.Funktion“)?"""
    return bool(l.funktion_grund) and any(x is not l and x.kurz == l.kurz and x.vorlage == l.funktion_grund
                                          for x in cas.alle)


def _empfehlung(satz):
    rx = br._kurz()["empf"]
    return bool(rx is not None and rx.search(satz.lower()))


def funktion_saetze(seg):
    """Diktierte Sätze über die Funktionsaufnahmen in einem Abschnitt → (Funktions-Text, Rest) bzw. (None, seg).
    „Funktionsaufnahmen: Instabilität C4/5“ – der Satz nach dem Doppelpunkt gehört dazu. Empfehlungssätze („Funktions-
    aufnahmen empfohlen“) zählen nicht (EMPFOHLEN ≠ GEMACHT). Der erste Satz nennt die Untersuchung und bleibt auch im Rest."""
    s = saetze(seg)
    funk, k = [], 0
    while k < len(s):
        a, t = s[k]
        if _FUNKTION_DIKTAT.search(t) and not _empfehlung(t):
            b = a + len(t)
            while k + 1 < len(s) and seg[b:s[k + 1][0]].strip() == ":":
                k += 1
                b = s[k][0] + len(s[k][1])
            funk.append((k == 0 or a == s[0][0], a, b))
        k += 1
    if not funk:
        return None, seg
    teil = ". ".join(seg[a:b].strip(" ,;") for _, a, b in funk).strip() + "."
    rest, pos = [], 0
    for erster, a, b in funk:
        if not erster:
            rest.append(seg[pos:a])
            pos = b
    rest.append(seg[pos:])
    return teil, re.sub(r"(?:\s*[.;:]){2,}", ".", "".join(rest)).strip(" ,;\n")


NICHT_DIKTIERT_NORMAL = "laut CAS, nicht diktiert – Normalbefund der Vorlage eingesetzt, bitte prüfen"


def nicht_diktiert_ergaenzen(segmente, wahlen, hinweise, cas, templates):
    """kaiscribe-georg-2011-n1 (Georg 20.11.2026, Punkte 16/17/26/36/37a, RH 84/77/37): mehrere CAS-Untersuchungen, aber nur
    ein Teil diktiert → jede nicht diktierte Untersuchung mit eigener Vorlage bekommt ihren eigenen Befund (Titel aus
    der CAS-Leistung, Normalsätze der Vorlage, ohne KI); IB-Lab-Werte (z. B. LAMA im Ganzbein) setzt KaiScribe danach
    dort ein. Sichtbare Prüfzeile statt „laut CAS, nicht diktiert“. Ohne diktierten Abschnitt mit CAS-Leistung
    (Ordi-Baustein, nichts zugeordnet) bleibt alles wie bisher. → (segmente, wahlen, hinweise, [Log])."""
    if not any(w.leistung is not None for w in wahlen) or any(w.art == "baustein" for w in wahlen):
        return segmente, wahlen, hinweise, []
    segmente, wahlen, hinweise, log = list(segmente), list(wahlen), list(hinweise), []
    for l in cas.alle:
        alt = f"{l.label} laut CAS, nicht diktiert"
        if alt not in hinweise or not l.vorlage or l.vorlage not in templates or l.vorlage == "allgemein" \
                or l.funktion_grund or _funktion_teil(l, cas) \
                or any(x.funktion_grund and x.kurz == l.kurz for x in cas.alle):
            continue                     # Funktions-Kombi: Regel kaiscribe-funktion-n1 bleibt (nicht diktiert → nichts)
        seite = l.seite if (l.seite and l.regionen & PAARIG) else ""
        segmente.append(f"{_anzeige(l.vorlage, templates) or l.vorlage}{' ' + seite if seite else ''} unauffällig.")
        wahlen.append(Wahl(l.vorlage, "cas", l, l.vorlage))
        hinweise[hinweise.index(alt)] = f"{l.label} {NICHT_DIKTIERT_NORMAL}"
        log.append(f"{l.label}: nicht diktiert → Normalbefund der Vorlage {l.vorlage}")
    return segmente, wahlen, hinweise, log


def funktion_ergaenzen(segmente, wahlen, cas, templates):
    """kaiscribe-funktion-n1 (RH 97): Funktionsaufnahmen laut CAS, aber kein eigener Abschnitt → einer direkt nach dem
    Abschnitt der Grund-Untersuchung (HWS/LWS in 2 Ebenen). Diktierte Sätze über die Funktion („In Funktion keine
    Instabilität“, „Funktionsaufnahmen: …“) gehen in diesen Abschnitt (Vorrang vor dem Normaltext, siehe
    funktion_saetze). Ohne diktierte Funktion: Normalbefund der Funktions-Vorlage (Titel + Normaltext, ohne KI).
    Hat bei „HWS … incl.Funktion“ der ganze Abschnitt die Funktions-Vorlage bekommen (Diktat nennt „Funktionsaufnahmen“),
    wird er geteilt: Rest → Grund-Vorlage, Funktions-Sätze → Funktions-Abschnitt dahinter.
    Grund-Untersuchung nicht diktiert → nichts (Hinweis „laut CAS, nicht diktiert“ wie bisher).
    → (segmente, wahlen, [Log-Zeilen]); ohne Funktions-Leistung unverändert."""
    segmente, wahlen, log = list(segmente), list(wahlen), []
    for l in cas.alle:
        if not l.funktion_grund:
            continue
        name = _anzeige(l.vorlage, templates)
        i_f = next((j for j, w in enumerate(wahlen) if w.vorlage == l.vorlage), None)
        i_g = next((j for j, w in enumerate(wahlen) if w.vorlage == l.funktion_grund), None)
        if i_f is not None:
            grund = next((x for x in cas.alle if x is not l and x.kurz == l.kurz and x.vorlage == l.funktion_grund), None)
            if i_g is not None or grund is None:
                continue                 # beide Abschnitte da bzw. nur Funktionsaufnahmen bestellt
            teil, rest = funktion_saetze(segmente[i_f])
            if not teil or not rest or teil.rstrip(". ") == rest.rstrip(". "):
                continue                 # nur über die Funktion diktiert → ein Abschnitt
            segmente[i_f] = rest
            wahlen[i_f] = Wahl(grund.vorlage, "bestaetigt", grund, wahlen[i_f].erkannt)
            i = i_f
            log.append(f"{name}: Abschnitt geteilt, Grund-Untersuchung + diktierte Funktion")
        elif i_g is not None:
            i = i_g
            teil, rest = funktion_saetze(segmente[i])
            if teil:
                segmente[i] = rest or segmente[i]
                log.append(f"{name}: diktierte Funktion als eigener Abschnitt")
            else:
                teil = f"{name} unauffällig."
                log.append(f"{name}: laut CAS ({l.kurz}), nichts Abweichendes diktiert → Normalbefund der Vorlage")
        else:
            continue
        segmente.insert(i + 1, teil)
        wahlen.insert(i + 1, Wahl(l.vorlage, "funktion", l, l.vorlage))
    return segmente, wahlen, log


def prompt_block(cas, templates):
    """<cas_untersuchungen> für den Gen-Prompt — nur mit CAS-Leistungen (sonst bleibt der Prompt bit-gleich)."""
    zeilen = []
    for l in cas.alle:
        if l.vorlage and not generisch(l.vorlage, templates):
            zeilen.append(f"- {l.label} – Vorlage: {_anzeige(l.vorlage, templates)}")
        else:
            zeilen.append(f"- {l.label}")
    return ("<cas_untersuchungen>\n"
            "Im CAS sind zu diesem Diktat folgende Untersuchungen angelegt:\n" + "\n".join(zeilen) + "\n"
            "Regeln: Nur Untersuchungen befunden, die diktiert wurden; keine Untersuchung und keinen Befund erfinden. "
            "Eine nicht diktierte CAS-Untersuchung bekommt keinen Abschnitt und keinen Text. Dieser Befund betrifft nur "
            "die oben als untersuchung angegebene Untersuchung. Nennt das Diktat keine Seite, gilt die Seite der "
            "passenden CAS-Untersuchung.\n"
            "</cas_untersuchungen>")
