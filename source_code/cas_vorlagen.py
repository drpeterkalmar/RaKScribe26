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
    ("fuss", r"fuß|fuss|zehe|calcaneus|kalkaneus|ferse|achilles|hallux"),
    ("schulter", r"schulter|akromio|acromio|clavicula|klavikula|schlüsselbein|scapula|skapula|supraspinatus|rotatoren"),
    ("oberarm", r"oberarm|\bhumerus\b"),
    ("ellbogen", r"el(?:l|le)n?bogen|olecranon"),
    ("unterarm", r"unterarm|vorderarm|\bradius\b|\bulna\b"),
    ("hand", r"\bhand|finger|daumen|karpal|scaphoid|skaphoid|navicular|kahnbein|mittelhand|handwurzel"),
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

    @property
    def spezifisch(self):
        return self.vorlage is not None and self.vorlage != "allgemein"


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
            mod = modalitaet_key(v, templates) if v and not generisch(v, templates) else None
            mod = mod or d.get("modalitaet")
            text = d.get("text") or ""
            self.alle.append(Leistung(
                kurz=str(d.get("kurz") or ""), label=label(text, d.get("kurz"), mod), vorlage=v, modalitaet=mod,
                seite=d.get("seite"), regionen=regionen(text + " " + (vorlagen_text(v, templates) if v else ""))))

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
def abgleich(key, text, cas, templates):
    """Passt die erkannte Vorlage key (Abschnitt text) zu einer CAS-Leistung? → (Leistung, gewählte Vorlage) | (None, None).
    Gleiche Vorlage → sie. Gleiche Region + gleiche Modalität → die des Diktats (genauer, z. B. Knie-TEP statt Knie),
    außer sie ist eine Sammel-Vorlage. Gleiche Region, andere Modalität → die CAS-Vorlage, wenn das Diktat selbst keine
    andere Modalität nennt (Diktat „Knie rechts: Baker-Zyste“, CAS „Sono Knie“)."""
    if not key or key.startswith("baustein:"):
        return None, None
    for l in cas.alle:
        if l.vorlage and l.vorlage == key:
            return l, key
    reg = regionen(vorlagen_text(key, templates))
    if not reg:
        return None, None
    mod_k = modalitaet_key(key, templates)
    mod_t = modalitaet_text(text)
    for l in cas.alle:
        if not (reg & l.regionen):
            continue
        if l.modalitaet is None or mod_k == l.modalitaet:
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
    if l:
        return Wahl(v, "bestaetigt", l, d)
    s = saetze(seg)
    if s:
        dk = erkennen(kopf(s[0][1]))
        if dk != d:
            l, v = abgleich(dk, seg, cas, templates)
            if l:
                return Wahl(v, "kopf", l, d)
    if generisch(d, templates):
        mod_d = modalitaet_key(d, templates) or modalitaet_text(seg)
        kandidaten = [l for l in cas.mit_vorlage if mod_d is None or l.modalitaet == mod_d]
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
    if len(set(l.vorlage or l.kurz for l in cas.alle if l.spezifisch or l.regionen)) < 2:
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
    return out


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
