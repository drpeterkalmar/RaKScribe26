"""befund_regeln.py — deterministische Befund-Regeln der EXE (v3.2).

Gleiche Semantik wie web_app/src/befundRegeln.ts (Web). Beide Engines laufen in
tests/offline/befund_regeln_test.py gegen dieselbe Tabelle befund_regeln_fixtures.json — Änderungen
IMMER an beiden Stellen + Fixture.

  split_regionen(text)        Diktat mit ≥2 Regionen ("Schulter rechts … Ellbogen rechts …")
                              → ein Segment je Region (je eigener Befund).
  ergebnis_nummerieren(rep)   Ergebnis-Zeilen ohne Nummer → "1. 2. 3."; ein einzelner
                              Normalbefund-Satz bleibt unnummeriert.
  has_pathology(text)         Pathologie-Stichwort ohne Negation (für den Normalsatz-Check der Nummerierung).
                              Die Bypass-Entscheidung selbst trifft normalbypass.is_pure_normal_finding (v3.2).
  ergebnis_mit_seite(e, raw)  Bypass-Ergebnis = Normal-Ergebnis des Templates + diktierte Seite.
  titel_mit_seite(t, raw)     Bypass-Überschrift bekommt die diktierte Seite.
  prompt_version / waehle_prompt   Versionierte Prompt-Datei: eine lokale Datei, die älter
                              als der eingebaute Prompt ist, gewinnt nicht mehr still.
"""
import re

# ── Prompt-Versionierung ─────────────────────────────────────────────────────
_MARKER_RE = re.compile(r"<!--\s*RAKSCRIBE_PROMPT_VERSION:\s*([\w.\-]+)\s*-->[ \t]*\r?\n?")


def prompt_version(text):
    """Versionsmarker der Prompt-Datei ('' wenn keiner)."""
    m = _MARKER_RE.search(text or "")
    return m.group(1) if m else ""


def version_kleiner(a, b):
    """Natürlicher Vergleich von Versionsmarkern: Zahlen als Zahlen (v3.3.2, Gutachten P3-5 — vorher gewann
    am selben Tag „…-v4“ gegen „…-v32“, weil Text verglichen wurde)."""
    def teile(s):
        return [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.findall(r"\d+|[^\d]+", s or "")]
    return teile(a) < teile(b)


def strip_prompt_marker(text):
    """Prompt ohne Markerzeile (der Marker geht nicht an Gemini)."""
    return _MARKER_RE.sub("", text or "", count=1)


def waehle_prompt(builtin_text, lokale):
    """Wählt den Gen-Prompt.

    builtin_text: Prompt aus dem EXE-Bundle (Release-Stand).
    lokale: Liste (pfad, text) der Dateien neben der EXE, in Prioritätsreihenfolge
            (radiology_prompt_v4.txt, radiology_prompt.txt).
    Regel: Eine lokale Datei gewinnt nur, wenn ihr Marker >= dem eingebauten ist
    (gleicher oder neuerer Stand — z.B. im Prompt-Editor gespeichert). Ohne Marker oder
    älter → eingebauter Prompt + Hinweis. Rückgabe (text, quelle, hinweis).
    """
    bv = prompt_version(builtin_text)
    veraltet = []
    for pfad, text in lokale:
        if not text:
            continue
        lv = prompt_version(text)
        if bv and (not lv or version_kleiner(lv, bv)):
            veraltet.append(f"{pfad} ({lv or 'ohne Version'})")
            continue
        return text, pfad, ""
    if builtin_text:
        hinweis = ""
        if veraltet:
            hinweis = ("Veraltete Prompt-Datei ignoriert: " + "; ".join(veraltet) +
                       f". Verwendet wird der eingebaute Befund-Prompt {bv}.")
        return builtin_text, "eingebaut", hinweis
    # Kein eingebauter Prompt (Entwicklung ohne Bundle): erste vorhandene lokale Datei
    for pfad, text in lokale:
        if text:
            return text, pfad, ""
    return "", "", ""


# ── Pathologie-Stichworte (Sync mit hasPathology in befundRegeln.ts) ──
_PATHO = [
    "arthrose", "fraktur", "osteo", "spondyl", "tendin", "calcarea", "bursitis",
    "tenosynovitis", "teppich", "ruptur", "luxation", "skoliose", "kyphose",
    "impression", "edgren", "scheuermann", "bi-rads", "morb", "thrombose",
    "mondor", "tumor", "metastas", "entzünd", "ödem", "erguss",
    "verschmäler", "skleros", "osteophyt", "beckenschief", "beinlängen",
    "listhesis", "chondr", "fissur", "kontusion", "depression", "n. ulnaris",
    "anconeus", "epitrochlear", "guyon", "flachbogig", "cobb", "schmorl",
    "patholog", "verdacht", "suspekt", "läsion", "herd", "verkalkung",
    "kalk", "fremdkörper", "emphysem", "infiltrat", "stauung",
    "thromb", "vene", "axillär", "axillar",
]
_NEG = [
    "kein ", "keine ", "keinem ", "keinen ", "keiner ", "kein nachweis",
    "nicht nachweisbar", "nicht vorhanden", "ausschluss", "frei von",
    "ohne nachweis", "ohne patholog", "ohne fraktur", "ohne arthrose",
    "kein hinweis", "keine zeichen", "nicht nachweis",
]
def has_pathology(text):
    tl = (text or "").lower()
    for kw in _PATHO:
        idx = tl.find(kw)
        if idx == -1:
            continue
        before = tl[max(0, idx - 30):idx]
        if not any(n in before for n in _NEG):
            return True
    return False


# ── Seite in der Bypass-Überschrift ──────────────────────────────────────────
_SEITE_IN_TITEL = re.compile(r"(?<!\w)(rechts|links|beidseits|bds\.?)(?!\w)", re.I)


def diktierte_seite(raw):
    tl = (raw or "").lower()
    if re.search(r"(?<!\w)(beidseits|bds\.?|beide[nr]?)(?!\w)", tl):
        return "beidseits"
    r = re.search(r"(?<!\w)rechts(?!\w)", tl)
    l = re.search(r"(?<!\w)links(?!\w)", tl)
    if r and l:
        return "beidseits"
    return "rechts" if r else ("links" if l else "")


def ergebnis_mit_seite(ergebnis, raw):
    """Bypass-Ergebnis (Peter 05.10.: NIE das Diktat abschreiben) = Normal-Ergebnis des Templates;
    'Regelrechte Darstellung des Kniegelenkes.' + Diktat 'Knie rechts unauffällig' →
    'Regelrechte Darstellung des Kniegelenkes rechts.'"""
    e = (ergebnis or "").strip() or "Unauffälliger Befund."
    seite = diktierte_seite(raw)
    if (not seite or _SEITE_IN_TITEL.search(e) or not e.startswith("Regelrechte Darstellung")
            or re.search(r"(?<!\w)beide[rnms]?(?!\w)", e, re.I)):
        return e
    i = e.find(".")
    return (e + " " + seite + ".") if i == -1 else (e[:i] + " " + seite + e[i:])


def titel_mit_seite(titel, raw):
    """'Kniegelenk in 2 Ebenen' + Diktat 'Knie links unauffällig' → 'Kniegelenk links in 2 Ebenen'."""
    seite = diktierte_seite(raw)
    if not seite or not titel or _SEITE_IN_TITEL.search(titel):
        return titel
    m = re.search(r"\s+in\s+(?:\d|zwei|einer|drei)\b", titel, re.I)
    if m:
        return titel[:m.start()] + " " + seite + titel[m.start():]
    return titel + " " + seite


# ── Regionen-Trenner ─────────────────────────────────────────────────────────
# Gruppe → Wortformen (ganze Wörter). Teilstrukturen derselben Untersuchung (Finger in der
# Hand, Zehe im Fuß) teilen sich die Gruppe → trennen nicht. Wirbelsäule/Thorax/Becken haben
# keine Seite und werden nie getrennt (eigene Kombi-Templates).
REGIONEN = [
    ("schulter", r"schulter(?:gelenk)?"),
    ("oberarm", r"oberarm|humerus"),
    ("ellbogen", r"el(?:l|le)n?bogen(?:gelenk)?"),
    ("unterarm", r"unterarm|vorderarm"),
    ("hand", r"hand(?:gelenk|wurzel)?|finger|daumen"),
    ("huefte", r"hüfte|hüftgelenk"),
    ("oberschenkel", r"oberschenkel|femur"),
    ("knie", r"knie(?:gelenk)?"),
    ("unterschenkel", r"unterschenkel"),
    ("sprunggelenk", r"(?:oberes\s+)?sprunggelenk|osg"),
    ("fuss", r"(?:vor|rück|mittel)?fu(?:ß|ss)|großzehe|zehe|calcaneus|kalkaneus|ferse"),
    ("clavicula", r"clavicula|klavikula|schlüsselbein"),
]
_REGION_ALT = "|".join(pat for _, pat in REGIONEN)
_MOD = r"(?:(?:röntgen|sonographie|sonografie|ultraschall)\s+(?:der\s+|des\s+|vom\s+)?)?"
_SEITE = r"(?:rechts|links|beidseits|bds\.?)(?:seitig)?"
_GRENZE = r"(?:^|[.!?:;,\n]|(?<!\w)punkt(?!\w)|(?<!\w)neue\s+zeile(?!\w)|(?<!\w)neuzeile(?!\w)|(?<!\w)absatz(?!\w))"
_REGION_MARKER_RE = re.compile(
    _GRENZE + r"\s*(" + _MOD +
    r"(?:(?:(?:der|die|das)\s+)?(?P<s1>rechte[nsmr]?|linke[nsmr]?)\s+(?P<r1>" + _REGION_ALT + r")" +
    r"|(?P<r2>" + _REGION_ALT + r")(?:\s+in\s+(?:2|zwei)\s+ebenen)?\s+(?P<s2>" + _SEITE + r")))(?!\w)",
    re.I)


def _gruppe(wort):
    w = wort.lower()
    for g, pat in REGIONEN:
        if re.fullmatch(pat, w, re.I):
            return g
    return w


def _seite_norm(s):
    s = s.lower()
    if s.startswith("recht"):
        return "rechts"
    if s.startswith("link"):
        return "links"
    return "beidseits"


_SEG_REST = re.compile(r"(?:\s*(?:(?<!\w)neue\s+zeile|(?<!\w)neuzeile|(?<!\w)absatz|[,;]))+\s*$", re.I)


def split_regionen(text):
    """Diktat → Liste von Segmenten (je eine Region). Ein-Region-Diktate: [text] unverändert."""
    t = text or ""
    starts = []  # (pos, key)
    saetze = None
    for m in _REGION_MARKER_RE.finditer(t):
        region = m.group("r1") or m.group("r2")
        seite = m.group("s1") or m.group("s2")
        key = (_gruppe(region), _seite_norm(seite))
        pos = m.end() - len(m.group(1))
        if saetze is None:
            saetze = diktat_saetze(t)
        if _kurz_marker(t, pos, saetze):
            continue  # v3.16.6: „Fuß rechts in 2 Ebenen empfohlen“ / „Fuß rechts nicht miterfasst“ → keine eigene Region
        if starts and starts[-1][1] == key:
            continue  # gleiche Region + Seite → derselbe Befund
        if any(k == key for _, k in starts):
            continue  # Region kommt wieder vor (z.B. Rückbezug) → nicht erneut trennen
        starts.append((pos, key))
    if len(starts) < 2:
        return [t]
    segs = []
    for i, (pos, _) in enumerate(starts):
        a = 0 if i == 0 else pos
        b = starts[i + 1][0] if i + 1 < len(starts) else len(t)
        seg = _SEG_REST.sub("", t[a:b]).strip()
        if seg:
            segs.append(seg)
    return segs if len(segs) >= 2 else [t]


# ── Ergebnis-Nummerierung ────────────────────────────────────────────────────
_NUM_RE = re.compile(r"^\s*(?:\*\*)?\s*\d+\s*[.)]\s*(?:\*\*)?\s*")
_BULLET_RE = re.compile(r"^\s*[-*•–]\s+")
_UNNUM_RE = re.compile(r"^(?:im\s+)?vergleich\s+zu[rm]?\s+vor", re.I)
_NORMALSATZ_RE = re.compile(r"(regelrecht|unauffällig|normal|altersentsprechend|ohne pathologisch|kein pathologisch)", re.I)


def _ist_normalsatz(s):
    return bool(_NORMALSATZ_RE.search(s)) and not has_pathology(s)


_SATZENDE = (".", "!", "?", ":", ";")


def satzform(s):
    """v3.7.4 (Georg 09.10.): Ergebnis-Punkt beginnt groß und endet mit Punkt. Sync: befundRegeln.ts satzform."""
    t = s.rstrip()
    if not t:
        return s
    if t[0].isalpha() and t[0].islower():
        t = t[0].upper() + t[1:]
    if not t.endswith(_SATZENDE) and not (t.endswith("**") and t[:-2].rstrip().endswith(_SATZENDE)):
        t += "."
    return t


def _satzanfang_gross(s):
    return s[0].upper() + s[1:] if s and s[0].isalpha() and s[0].islower() else s


def _nummeriere_block(lines):
    items = []  # (index_in_lines, text)
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if ln[:1] in (" ", "\t") and items:
            continue  # eingerückte Fortsetzung/Unterpunkt bleibt unverändert
        items.append(i)
    if not items:
        return lines
    texte = {i: _satzanfang_gross(_BULLET_RE.sub("", _NUM_RE.sub("", lines[i])).strip()) for i in items}
    zaehlbar = [i for i in items if not _UNNUM_RE.match(texte[i])]
    out = list(lines)
    if len(zaehlbar) == 1 and _ist_normalsatz(texte[zaehlbar[0]]):
        out[zaehlbar[0]] = texte[zaehlbar[0]]
    else:
        n = 0
        for i in items:
            if i in zaehlbar:
                n += 1
                out[i] = f"{n}. {texte[i]}"
            else:
                out[i] = texte[i]
    # v3.7.4: Punkt ans Ende jedes Ergebnis-Punkts (bei eingerückter Fortsetzung an deren letzte Zeile)
    for k, i in enumerate(items):
        ende = items[k + 1] if k + 1 < len(items) else len(lines)
        letzte = max(j for j in range(i, ende) if out[j].strip())
        einzug = out[letzte][:len(out[letzte]) - len(out[letzte].lstrip())]
        out[letzte] = einzug + satzform(out[letzte].lstrip())
    return out


def ergebnis_nummerieren(report):
    """Nummeriert jeden '## Ergebnis'-Abschnitt (mehrere bei Mehr-Regionen-Befunden)."""
    if not report or "## Ergebnis" not in report:
        return report
    lines = report.split("\n")
    out, i = [], 0
    while i < len(lines):
        out.append(lines[i])
        if lines[i].strip().startswith("## Ergebnis"):
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("#"):
                j += 1
            block = lines[i + 1:j]
            # führende/abschließende Leerzeilen erhalten
            out.extend(_nummeriere_block(block))
            i = j
            continue
        i += 1
    return "\n".join(out)


def befund_ueberschrift_sichern(report):
    """Fehlt in einem Block zwischen '## Titel' und '## Ergebnis' die Zeile '## Befund' (Gemini lässt sie
    gelegentlich weg), wird sie direkt nach der Titelzeile ergänzt."""
    if not report or "## Ergebnis" not in report:
        return report
    lines = report.split("\n")
    out, titel_idx, hat_befund = [], None, False
    for ln in lines:
        st = ln.strip()
        if st.startswith("## "):
            kopf = st[3:].strip().rstrip(":").lower()
            if kopf == "befund":
                hat_befund = True
            elif kopf == "ergebnis":
                if titel_idx is not None and not hat_befund:
                    out.insert(titel_idx + 1, "")
                    out.insert(titel_idx + 2, "## Befund")
                titel_idx, hat_befund = None, False
            else:
                titel_idx, hat_befund = len(out), False
        out.append(ln)
    return "\n".join(out)


def csa_bereinigen(report):
    """v3.2.2 (Skill-Regel 3ac, Georg 05.10.): Nicht diktierte Querschnittsflächen dürfen nicht im Befund stehen.
    - Klammerzusatz mit Platzhalter '(Querschnittsfläche …: [CSA_x] mm²; Normwert < n mm²)' → komplett entfernen.
    - Satzteil 'mit regelrechter/normaler Querschnittsfläche von [CSA_x] mm² (Normwert …)' → entfernen.
    - Ganzer Satz mit übrig gebliebenem [CSA_…]-Platzhalter → entfernen.
    - Im '## Ergebnis' werden Querschnittsflächen-Angaben gestrichen (Ergebnis = Diagnose, kein Messwert)."""
    if not report or "CSA" not in report and "Querschnittsfläche" not in report:
        return report
    r = re.sub(r"\s*\((?:[^()]*?)\[CSA_[^\]]*\][^()]*\)", "", report)
    r = re.sub(r"\s+mit\s+(?:regelrechter|normaler)\s+Querschnittsfläche\s+von\s+\[CSA_[^\]]*\]\s*mm²\s*(?:\([^()]*\))?", "", r)
    # Satz-Einheit: alles außer Punkt/Zeilenende, aber Abkürzungen wie "N. medianus", "Lig." gehören zum Satz
    u = r"(?:[^.\n]|\b(?:N|n|Nn|M|Mm|Lig|Ligg|ca|bzw)\.|\.\d)"
    satz = r"[^.\n\s]" + u + r"*?\[CSA_[^\]]*\]" + u + r"*\."
    r = re.sub(r"(?m)^[ \t]*" + satz + r"[ \t]*", "", r)   # Satz am Zeilenanfang: folgendes Leerzeichen mit
    r = re.sub(r"[ \t]*" + satz, "", r)                    # Satz mitten in der Zeile: vorangehendes Leerzeichen mit
    if "## Ergebnis" in r:
        kopf, erg = r.split("## Ergebnis", 1)
        erg = re.sub(r",?\s*(?:mit\s+(?:einer\s+)?)?(?:Querschnittsfläche|CSA)[^.,;\n]*?\d+(?:[.,]\d+)?\s*mm²(?:\s*\([^()]*\))?", "", erg)
        r = kopf + "## Ergebnis" + erg
    return r


_MAMMASONO_TITEL = re.compile(r"(?m)^##[ \t]+Mamma[- ]?sono(?:graph|graf)ie\b[^\n]*$", re.I)


def mammasono_beidseits(report):
    """v3.7.2 (Peter 07.10.: „Mammasono ist eigentlich immer beidseits“): Überschrift immer
    'Mammasonographie beidseits', auch wenn nur die Seite des Befunds diktiert wurde."""
    return _MAMMASONO_TITEL.sub("## Mammasonographie beidseits", report or "")


def nachbearbeiten(report, nummerieren=True):
    """Deterministische Nachbearbeitung jedes Befundes (EXE + Web gleich): CSA-Regel, '## Befund' sichern,
    Ergebnis nummerieren. v3.7.2 (Peter 07.10.): wörtliche Ordi-Bausteine bleiben unnummeriert (nummerieren=False)."""
    r = mammasono_beidseits(befund_ueberschrift_sichern(csa_bereinigen(report)))
    return ergebnis_nummerieren(r) if nummerieren else r


# ── v3.9.0 (Georg 13.10.): Rho-Textbaustein (opportunistisches Knochendichtescreening, KI-Software Rho) ──────
# Auslöser im Diktat: „Rho“ (gesprochen „ro“, STT auch „Ro“/„Roh“/„Row“) mit optionalem Score, „zusätzliche DEXA/DXA“,
# „opportunistisches Knochen(dichte)screening“. Der Auslöser wird aus dem Diktat genommen (die KI sieht ihn nicht),
# danach Variante C ans Ende des Befundtexts und Variante 2 als letzter Ergebnis-Punkt (Georg: „C und 2“).
# Sync: web_app/src/befundRegeln.ts rhoErkennen/rhoEinfuegen (gleiche Regexe, gleiche Fixtures „rho“).
RHO_BEFUND = ("Opportunistisches Knochendichtescreening mittels CE-zertifizierter, klinisch validierter KI-Software "
              "(Rho): {score} eine erhöhte Wahrscheinlichkeit für eine verminderte Knochendichte. Der Score korreliert "
              "in Studien eng mit dem DEXA-T-Score, ersetzt diesen jedoch nicht. Da keine Knochendichtemessung aus den "
              "letzten 2 Jahren vorliegt, wird eine weiterführende Abklärung mittels DEXA empfohlen.")
RHO_ERGEBNIS = "Opportunistisches Knochendichtescreening auffällig. Abklärung mittels DEXA empfohlen."
_RHO_NUM = r"(?:[\s:,-]*(?:score|skor|stufe|wert)?[\s:,-]*(?:von\s+)?(\d{1,2})(?!\s*(?:mm|cm|%|grad|°)))?"
_RHO_RE = re.compile(
    r"(?<![\w-])(?:"
    r"(?:rho|ro|roh|row)(?:[\s-]*(?:score|skor|stufe))?" + _RHO_NUM +
    r"|zus[äa]tzlich(?:e[nrsm]?)?\s+(?:dexa|dxa|dexa-?messung|knochendichtemessung)(?:[\s-]*empfehlung)?(?:\s+empfohlen)?" + _RHO_NUM +
    r"|opportunistische[sn]?\s+knochen(?:dichte)?[\s-]*screening(?:[\s-]*(?:auff[äa]llig|positiv))?" + _RHO_NUM +
    r")(?![\w-])(?:\s*(?:punkt|\.))?", re.I)


def rho_erkennen(seg):
    """→ (Diktat ohne Auslöser, Score-Text oder '' , aktiv)."""
    if not seg:
        return seg, "", False
    score, gefunden = "", False
    for m in _RHO_RE.finditer(seg):
        gefunden = True
        z = next((g for g in m.groups() if g), "")
        if z and not score:
            score = z
    if not gefunden:
        return seg, "", False
    rest = _RHO_RE.sub(" ", seg)
    rest = re.sub(r"\s+([.,;:])", r"\1", re.sub(r"[ \t]{2,}", " ", rest))
    rest = re.sub(r"(?:^|(?<=[.,;:]))\s*[.,;:](?=\s|$)", "", rest).strip(" ,;:")
    return (rest or seg), score, True


def rho_einfuegen(report, score):
    """Variante C ans Ende des (letzten) Befundtexts, Variante 2 als letzter Ergebnis-Punkt."""
    if not report or RHO_ERGEBNIS in report:
        return report
    s = f"Der Score von {score} (Skala 1–10) zeigt" if score else "Der Score von ≥7 (Skala 1–10) zeigt"  # Georg 13.10.: ohne diktierten Score immer ≥7
    befund = RHO_BEFUND.format(score=s)
    if "## Ergebnis" not in report:
        return report.rstrip() + "\n\n" + befund + "\n\n## Ergebnis\n" + RHO_ERGEBNIS
    i = report.rfind("## Ergebnis")
    kopf, erg = report[:i].rstrip(), report[i + len("## Ergebnis"):]
    zeilen = [z for z in erg.split("\n") if z.strip()]
    nummeriert = any(_NUM_RE.match(z) for z in zeilen)
    erg = erg.rstrip() + "\n" + RHO_ERGEBNIS
    neu = kopf + "\n\n" + befund + "\n\n## Ergebnis" + erg
    # nummerierte Ergebnisse oder ein einzelner Punkt → neu durchzählen; mehrere unnummerierte (wörtlicher
    # Ordi-Baustein) bleiben unnummeriert
    return ergebnis_nummerieren(neu) if (nummeriert or len(zeilen) <= 1) else neu


def befunde_zusammenfuegen(reports):
    """Mehrere Einzelbefunde (je ## Titel/## Befund/## Ergebnis) untereinander."""
    return "\n\n\n".join(r.strip() for r in reports if r and r.strip())


# ── v3.2.3 (Peter 06.10.: alle Vorlagen erreichbar + korrekt priorisiert) ─────────────────────────────────
# Vorrang-Regeln + Namens-Treffer aus vorlagen_vorrang.json (EINE Datei für EXE + Web).
# Sync: web_app/src/befundRegeln.ts vorrangVorlage (gleiche Normalisierung, gleiche Regex, gleiche Fixtures).
import json as _json
import os as _os
import sys as _sys
import unicodedata as _ud

_VORRANG = None


def _vorrang_laden():
    global _VORRANG
    if _VORRANG is None:
        kandidaten = [getattr(_sys, "_MEIPASS", None), _os.path.dirname(_os.path.abspath(__file__)),
                      _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))]
        for d in kandidaten:
            if d and _os.path.exists(_os.path.join(d, "vorlagen_vorrang.json")):
                with open(_os.path.join(d, "vorlagen_vorrang.json"), encoding="utf-8") as f:
                    _VORRANG = _json.load(f)
                break
        else:
            _VORRANG = {"regeln": [], "fuellwoerter": [], "kopf_woerter": 5, "name_ausnahmen": {}}
    return _VORRANG


def vorlage_normalisieren(text):
    """klein, ä→ae, ö→oe, ü→ue, ß→ss, Akzente weg, ph→f, alles außer a-z0-9 → Leerzeichen."""
    t = (text or "").lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    t = "".join(c for c in _ud.normalize("NFD", t) if not _ud.combining(c))
    t = t.replace("ph", "f")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()


def vorrang_vorlage(text, templates, daten=None):
    """Gibt den Vorlagen-Key zurück, wenn eine Vorrang-Regel oder ein diktierter Vorlagenname greift, sonst None
    (dann entscheidet die bisherige Erkennung)."""
    d = daten or _vorrang_laden()
    woerter = vorlage_normalisieren(text).split()
    fuell = set(d.get("fuellwoerter", []))
    while woerter and woerter[0] in fuell:
        woerter = woerter[1:]
    voll = " ".join(woerter)
    kopf = " ".join(woerter[:d.get("kopf_woerter", 5)])
    for r in d.get("regeln", []):
        if r["key"] not in templates:
            continue
        ziel = voll if r.get("bereich") == "text" else kopf
        if all(re.search(p, ziel) for p in r.get("alle", [])) and not any(re.search(p, voll) for p in r.get("keins", [])):
            return r["key"]
    # Namens-Treffer: längster diktierter Vorlagenname (≥ 2 Wörter), Beginn in den ersten 3 Wörtern
    best, best_len = None, 0
    ausnahmen = d.get("name_ausnahmen", {})
    for key, v in templates.items():
        dn = v.get("display_name", "")
        if key == "allgemein" or "(allgemein)" in dn.lower():
            continue
        n = vorlage_normalisieren(dn)
        if len(n.split()) < 2 or len(n) <= best_len:
            continue
        m = re.search(r"(?:^| )" + re.escape(n) + r"(?: |$)", voll)
        if not m or len(voll[:m.start()].split()) > 2:
            continue
        if key in ausnahmen and re.search(ausnahmen[key], voll):
            continue
        best, best_len = key, len(n)
    return best


# ── v3.15.5 Widerspruchs-Prüfung Pathologie ↔ Normalsatz (Peter 15.10.2026: „wenn ich fersensporne diktiere sollte im
# befundtext nicht stehen dass die ferse eine normale kontur hat“ … „Fibroostosen, Exostosen, Spondylosen usw. können in
# praktisch jeder Knochenregion auftreten.“) — Katalog und Normalsatz-Merkmale: vorlagen_vorrang.json „widersprueche“.
# Vor der KI: die widersprechenden Sätze der Vorlage stehen im Gen-Prompt (<widersprueche>). Nach der KI: übrig gebliebene
# widersprechende Normalsätze werden auf „Im Übrigen …“ eingeschränkt, der Befund fehlt nie im Befundtext und im
# Ergebnis steht er statt „Regelrechte Darstellung …“. Ohne diktierten Befund bleibt alles Zeichen für Zeichen gleich.
# Sync: web_app/src/befundRegeln.ts (widerspruchBefunde, widerspruchSaetze, satzEinschraenken, widersprucheBereinigen,
# widerspruchPrompt), Fälle befund_regeln_fixtures.json „widerspruch“, Matrix tests/offline/widerspruch_matrix_test.py.
_WID_CACHE = {}


def _wid(daten=None):
    d = (daten if daten is not None else _vorrang_laden()).get("widersprueche") or {}
    c = _WID_CACHE.get(id(d))
    if c is None:
        c = {"d": d, "kat": [], "merk": {}, "strukt": {}}
        for k in d.get("kategorien") or []:
            c["kat"].append(dict(k, _re=re.compile(k["muster"]), _aus=re.compile(k["ausser"]) if k.get("ausser") else None,
                                 _bef=re.compile(k["befund"]) if k.get("befund") else None))
        for n, m in (d.get("merkmale") or {}).items():
            c["merk"][n] = (re.compile(m["muster"]), re.compile(m["ausser"]) if m.get("ausser") else None)
        for n, m in (d.get("strukturen") or {}).items():
            c["strukt"][n] = re.compile(m)
        for n in ("einschraenkung", "verneinung_vor", "verneinung_nach", "skelett"):
            c[n] = re.compile(d[n]) if d.get(n) else None
        _WID_CACHE[id(d)] = c
    return c


_WID_TRENNER = re.compile(r"[.;,:!?\n]+|(?<![a-zäöüß])(?:punkt|neue zeile|neuzeile|absatz)(?![a-zäöüß])|\s[–-]\s", re.I)
_WID_VORSPANN = re.compile(r"^(?:und|sowie|mit|zusätzlich|außerdem|ausserdem|auch|dazu|bei)\s+", re.I)
# Vorspann eines diktierten Teilsatzes, der nicht zum Befund gehört („Knie rechts Osteophyt …“ → „Osteophyt …“)
_WID_REGION_SEITE = re.compile(
    r"(?<![a-zäöüß])(?:rechts|links|beidseits|beidseitig|bds|re|li|röntgen|sono[a-zäöüß]*|ultraschall|ct|mrt?|"
    r"(?:knie|hüft|hand|sprung|ellbogen|ellenbogen|schulter|iliosakral|kiefer)(?:gelenk[a-zäöüß]*)?|knie|hüfte|ferse|"
    r"calcaneus|kalkaneus|becken[a-zäöüß]*|[hbl]ws|wirbelsäule|schulter|ellbogen|hand|finger|daumen|fuß|fuss|vorfuß|"
    r"mittelfuß|zehe[a-zäöüß]*|osg|usg|unterschenkel|oberschenkel|oberarm|unterarm|schädel|thorax|clavicula|patella|"
    r"in (?:2|zwei) ebenen|befund)(?![a-zäöüß])", re.I)


def _wid_phrase(roh, start):
    """Diktierter Befund ab dem Ende des Vorspanns (Region/Seite) vor dem Treffer bis zum Ende des Teilsatzes."""
    vor = roh[:start]
    ende = 0
    for m in _WID_REGION_SEITE.finditer(vor):
        ende = m.end()
    return roh[ende:].strip(" ,;:")


def _wid_gruppen(text, c):
    return {n for n, rx in c["strukt"].items() if rx.search(text)}


def widerspruch_befunde(diktat, daten=None):
    """Diktat → umschriebene/degenerative Befunde aus dem Katalog, nicht verneint („kein Fersensporn“ zählt nicht).
    Je Befund: id, name, phrase (diktierter Teilsatz), gruppen (Strukturen des Teilsatzes + Standard der Kategorie),
    global (Lage unbekannt bzw. die ganze Region, z. B. Osteopenie)."""
    c = _wid(daten)
    out = []
    for teil in _WID_TRENNER.split(diktat or ""):
        roh = _WID_VORSPANN.sub("", " ".join(teil.split()))
        t = roh.lower()
        if not t:
            continue
        for k in c["kat"]:
            if k["_aus"] is not None and k["_aus"].search(t):
                continue
            for m in k["_re"].finditer(t):
                if c["verneinung_vor"] is not None and c["verneinung_vor"].search(t[:m.start()]):
                    continue
                if c["verneinung_nach"] is not None and c["verneinung_nach"].search(t[m.end():]):
                    continue
                eigene = _wid_gruppen(t, c)
                out.append({"id": k["id"], "name": k["name"], "phrase": _wid_phrase(roh, m.start()) or roh,
                            "gruppen": sorted(eigene | set(k.get("gruppen") or [])),
                            "global": bool(k.get("global")) or not (eigene | set(k.get("gruppen") or []))})
                break
    return out


_WID_TEILSATZ = re.compile(r"[.,;:\n]")


def _nennt(text, k, c, rx=None):
    """Nennt text (klein) den Befund der Kategorie k NICHT verneint? („Keine periartikulären Verkalkungen“ ist ein
    Normalsatz, kein Befund.) Verneinung und Ausnahmen gelten im Teilsatz des Treffers. rx = anderes Muster
    (Deskriptoren)."""
    for m in (rx or k["_re"]).finditer(text):
        a = max((x.end() for x in _WID_TEILSATZ.finditer(text, 0, m.start())), default=0)
        e = next((x.start() for x in _WID_TEILSATZ.finditer(text, m.end())), len(text))
        teil = text[a:e]
        if k["_aus"] is not None and k["_aus"].search(teil):
            continue
        if c["verneinung_vor"] is not None and c["verneinung_vor"].search(text[a:m.start()]):
            continue
        if c["verneinung_nach"] is not None and c["verneinung_nach"].search(text[m.end():e]):
            continue
        return True
    return False


def _beschreibt(text, k, c):
    """Befund genannt ODER mit seinen Deskriptoren beschrieben („Verschmälerung des Gelenkspaltes mit Osteophyten“ statt
    „Gonarthrose“ — Diagnosen gehören laut Prompt ins Ergebnis, der Befundtext beschreibt)."""
    return _nennt(text, k, c) or (k.get("_bef") is not None and _nennt(text, k, c, k["_bef"]))


def ist_skelett_text(text, daten=None):
    """Beschreibt der Text (Vorlage bzw. Befundteil) Skelett (Kortikalis, Gelenkspalt, Wirbelkörper …)?"""
    rx = _wid(daten)["skelett"]
    return bool(rx is not None and rx.search((text or "").lower()))


_WID_ABK = {"bzw", "ca", "z", "b", "u", "a", "v", "d", "h", "evtl", "ggf", "inkl", "max", "min", "lig", "n", "nn", "m",
            "mm", "li", "re", "bds", "vs", "st", "p", "i", "dr", "o", "s", "co", "e", "g", "ap", "pa", "bspw", "usw"}


def saetze_mit_lage(text):
    """Text → [(start, ende)] je Satz (nicht nach Abkürzungen wie „bzw.“, „a.-p.“, „z. B.“; Zeilen sind Grenzen)."""
    out, start, i, n = [], 0, 0, len(text or "")
    while i < n:
        ch = text[i]
        if ch == "\n":
            if text[start:i].strip():
                out.append((start, i))
            start = i + 1
        elif ch in ".!?" and (i + 1 == n or text[i + 1] in " \n"):
            wort = re.split(r"[\s(/]", text[start:i])[-1].lower().strip("-.")
            if ch != "." or not (wort in _WID_ABK or re.fullmatch(r"[a-zäöü](?:\.-?[a-zäöü])*", wort or "-")):
                out.append((start, i + 1))
                start = i + 1
        i += 1
    if text[start:n].strip():
        out.append((start, n))
    return [(a + len(text[a:b]) - len(text[a:b].lstrip()), b) for a, b in out if text[a:b].strip()]


def widerspruch_saetze(text, befunde, daten=None):
    """Sätze in text (Vorlage oder Befundteil), die einem diktierten Befund widersprechen: Normalsatz-Merkmal der
    Kategorie, nicht schon eingeschränkt („im Übrigen“, „ansonsten“ …), nennt den Befund nicht selbst, und betrifft die
    Lage (allgemeiner Satz oder dieselbe Struktur; ein Satz über eine BESTIMMTE andere Struktur bleibt).
    → [(start, ende, [befund-ids])]."""
    if not befunde:
        return []
    c = _wid(daten)
    kat = {k["id"]: k for k in c["kat"]}
    out = []
    for a, b in saetze_mit_lage(text or ""):
        s = text[a:b].lower()
        if c["einschraenkung"] is not None and c["einschraenkung"].search(s):
            continue
        if any(_beschreibt(s, kat[x["id"]], c) for x in befunde if x["id"] in kat):
            continue                                   # beschreibt den Befund selbst (Pathologie-Satz)
        sg = _wid_gruppen(s, c)
        ids = []
        for x in befunde:
            k = kat.get(x["id"])
            if k is None:
                continue
            treffer = False
            for mn in k.get("merkmale") or []:
                rx = c["merk"].get(mn)
                if rx and rx[0].search(s) and not (rx[1] is not None and rx[1].search(s)):
                    treffer = True
                    break
            if treffer and _wid_betrifft(sg, x):
                ids.append(x["id"])
        if ids:
            out.append((a, b, ids))
    return out


_WID_GENERISCH = {"gelenk", "weichteile"}


def _wid_betrifft(sg, befund):
    """Betrifft ein Satz mit den Strukturgruppen sg die Lage des Befunds? Allgemeiner Satz (keine Gruppe) bzw. Befund
    ohne bekannte Lage → ja. Nennt der Satz eine bestimmte Struktur (z. B. Hüftgelenk), muss der Befund dort liegen
    (Fibroostose am Trochanter ≠ Hüftgelenk; ISG-Arthrose ≠ Hüftgelenke); nur „Gelenk“/„Weichteile“ → Kategorie passt."""
    fg = set(befund["gruppen"])
    if befund["global"] or not sg:
        return True
    sg_spez, fg_spez = sg - _WID_GENERISCH, fg - _WID_GENERISCH
    if sg_spez:
        return bool(sg_spez & fg_spez) or (not fg_spez and bool(sg & fg))
    return bool(sg & fg)


_WID_VERB = re.compile(r"^(?:ist|sind|zeigt|zeigen|weist|weisen|stellt|stellen|steht|stehen|liegt|liegen|erscheint|"
                       r"erscheinen|endet|enden|besteht|bestehen|findet|finden|ragt|ragen)$")
_WID_KLEIN = re.compile(r"^(?:normale?[rsnm]?|normal|regelrechte?[rsnm]?|regelrecht|glatte?[rsnm]?|scharfe?[rsnm]?|"
                        r"anatomisch[a-zäöüß]*|ordnungsgemäße?[rsnm]?|keine?[rsnm]?|kein|unauffällige?[rsnm]?|"
                        r"altersentsprechende?[rsnm]?|symmetrische?[rsnm]?|achsengerechte?[rsnm]?|allseits|"
                        r"harmonische?[rsnm]?|regulär[a-zäöüß]*|intakte?[rsnm]?|"
                        r"gute?[rsnm]?|erhaltene?[rsnm]?|beide[rn]?|die|der|das|den|dem|des|eine?[rsnm]?|sie|es)$", re.I)


def _klein_anfang(t):
    w = t.split(" ", 1)[0]
    return (w[:1].lower() + t[1:]) if _WID_KLEIN.match(w.rstrip(",:")) else t


def satz_einschraenken(satz):
    """Normalsatz nur noch für den Rest gelten lassen: „Im Übrigen …“ (Verb an zweiter Stelle bleibt: „Die Gelenkflächen
    sind glatt.“ → „Im Übrigen sind die Gelenkflächen glatt.“; Label-Stil „Kortikalis: glatte Kontur.“ → „Kortikalis: im
    Übrigen glatte Kontur.“)."""
    t = (satz or "").strip()
    m = re.match(r"^([A-ZÄÖÜ][^:.]{0,48}):\s+(\S.*)$", t, re.S)
    if m and not any(_WID_VERB.match(w.lower()) for w in m.group(1).split()):
        return f"{m.group(1)}: im Übrigen {_klein_anfang(m.group(2))}"
    w = t.split(" ")
    for i in range(1, min(13, len(w))):
        if _WID_VERB.match(w[i].lower()):
            subjekt = " ".join(w[:i])
            return "Im Übrigen " + w[i] + " " + _klein_anfang(subjekt) + ("" if i + 1 >= len(w) else " " + " ".join(w[i + 1:]))
    return "Im Übrigen " + _klein_anfang(t)


def widerspruch_prompt(befunde, vorlage, daten=None):
    """<widersprueche> für den Gen-Prompt — nur, wenn die Vorlage einem diktierten Befund widerspricht (sonst bleibt
    der Prompt bit-gleich)."""
    if not befunde or not ist_skelett_text(vorlage, daten):
        return ""
    saetze = widerspruch_saetze(vorlage, befunde, daten)
    if not saetze:
        return ""
    diktiert = "; ".join(f"„{b['phrase']}“ ({b['name']})" for b in befunde)
    liste = " ".join(f"„{(vorlage or '')[a:e].strip()}“" for a, e, _ in saetze)
    return ("<widersprueche>\n"
            f"Diktiert: {diktiert}.\n"
            f"Diese Sätze der Vorlage widersprechen dem diktierten Befund und dürfen so NICHT stehen bleiben: {liste}\n"
            "Regeln: Schränke jeden dieser Sätze nur im betroffenen Teil ein („Im Übrigen …“ bzw. „…, abgesehen von …“) "
            "oder lass den betroffenen Teil weg; den übrigen Normaltext der Vorlage übernimmst du wörtlich. Der Befund "
            "steht als eigener Satz an der Stelle des betroffenen Normalsatzes. Im Ergebnis steht er als nummerierter "
            "Punkt (mit Seite) — nie „Regelrechte Darstellung …“ oder „unauffällig“ für die ganze Untersuchung.\n"
            "</widersprueche>")


_WID_NORMAL_ERG = re.compile(r"regelrechte darstellung|unauffällige[rsn]? (?:befund|darstellung)|ohne pathologischen befund|"
                             r"normalbefund|altersentsprechend unauffällig|regelrechter befund", re.I)


def _abschnitt(zeilen, name):
    """[(start, ende)] der Zeilen nach „## name“ bis zur nächsten Überschrift."""
    out = []
    for i, z in enumerate(zeilen):
        if z.strip().lower().rstrip(":") == "## " + name:
            j = i + 1
            while j < len(zeilen) and not zeilen[j].lstrip().startswith("## "):
                j += 1
            out.append((i + 1, j))
    return out


def widersprueche_bereinigen(report, diktat, daten=None):
    """Nach der KI (EXE + Web gleich): widersprechende Normalsätze im Befundteil → „Im Übrigen …“, fehlender Befund →
    eigener Satz, Ergebnis nennt den Befund statt „Regelrechte Darstellung …“. → (report, Liste der Änderungen).
    Ohne diktierten Befund bzw. ohne Skelett-Befundteil unverändert."""
    befunde = widerspruch_befunde(diktat, daten)
    if not befunde or not report or "## Befund" not in report:
        return report, []
    c = _wid(daten)
    kat = {k["id"]: k for k in c["kat"]}
    zeilen = report.split("\n")
    aenderungen = []
    seite = diktierte_seite(diktat)
    for a, e in _abschnitt(zeilen, "befund"):
        text = "\n".join(zeilen[a:e])
        if not ist_skelett_text(text, daten):
            continue
        treffer = widerspruch_saetze(text, befunde, daten)
        vor = _befundsaetze_danach(text, treffer, befunde, kat, c)
        neu, pos, erste = [], 0, None
        for s0, s1, art in sorted([(x[0], x[1], "e") for x in treffer] + [(x[0], x[1], "v") for x in vor]):
            stueck = text[pos:s0]
            if art == "v":                          # Befundsatz: wandert vor den ersten eingeschränkten Satz
                neu.append(stueck[:-1] if stueck.endswith(" ") else stueck)
                aenderungen.append(f"vorgezogen: {text[s0:s1].strip()[:60]}")
            else:
                neu.append(stueck)
                if erste is None:
                    neu.append("".join(text[x0:x1] + " " for x0, x1 in vor))
                    erste = sum(len(x) for x in neu)
                neu.append(satz_einschraenken(text[s0:s1]))
                aenderungen.append(f"eingeschränkt: {text[s0:s1].strip()[:60]}")
            pos = s1
        neu.append(text[pos:])
        text = "".join(neu)
        fehlend = [b for b in befunde if b["id"] in kat and not _beschreibt(text.lower(), kat[b["id"]], c)]
        if fehlend:
            satz = " ".join(_satz_aus_phrase(b["phrase"]) for b in fehlend)
            if erste is not None:                   # vor dem ersten eingeschränkten Normalsatz
                text = text[:erste] + satz + " " + text[erste:]
            else:                                   # sonst ans Ende des ersten Absatzes
                anfang = len(text) - len(text.lstrip())
                absatz = text.find("\n\n", anfang)
                stelle = absatz if absatz > 0 else len(text.rstrip())
                text = text[:stelle].rstrip() + " " + satz + text[stelle:]
            aenderungen.append(f"Befund ergänzt: {satz[:60]}")
        zeilen[a:e] = text.split("\n")
        break
    for a, e in _abschnitt(zeilen, "ergebnis"):
        inhalt = [i for i in range(a, e) if zeilen[i].strip()]
        nennt = [i for i in inhalt if any(_nennt(zeilen[i].lower(), kat[b["id"]], c) or
                                          (re.search(kat[b["id"]].get("ergebnis") or "$^", zeilen[i].lower())
                                           and not _WID_NORMAL_ERG.search(zeilen[i]))
                                          for b in befunde if b["id"] in kat)]
        normal = [i for i in inhalt if _WID_NORMAL_ERG.search(zeilen[i]) and i not in nennt]
        if normal:
            for i in reversed(normal):
                aenderungen.append(f"Ergebnis ohne Normalsatz: {zeilen[i].strip()[:60]}")
                del zeilen[i]
            e -= len(normal)
        if not nennt:
            punkte = [_satz_aus_phrase(b["phrase"], seite) for b in befunde]
            stelle = e
            while stelle > a and not zeilen[stelle - 1].strip():
                stelle -= 1
            zeilen[stelle:stelle] = punkte
            aenderungen.append("Ergebnis ergänzt: " + "; ".join(p[:40] for p in punkte))
        block = "\n".join(zeilen)
        zeilen = ergebnis_nummerieren(block).split("\n")
        break
    return "\n".join(zeilen), aenderungen


def _befundsaetze_danach(text, treffer, befunde, kat, c):
    """Sätze, die den diktierten Befund nennen/beschreiben und in derselben Zeile NACH dem ersten eingeschränkten
    Normalsatz stehen — die stellt widersprueche_bereinigen vor ihn („Plantarer Fersensporn. Im Übrigen normale Form
    des Calcaneus …“ statt „Im Übrigen …“, bevor der Befund überhaupt genannt ist)."""
    if not treffer:
        return []
    erste = treffer[0][0]
    ende = text.find("\n", erste)
    ende = len(text) if ende < 0 else ende
    eingeschraenkt = {(x[0], x[1]) for x in treffer}
    return [(a, b) for a, b in saetze_mit_lage(text) if erste < a and b <= ende and (a, b) not in eingeschraenkt
            and any(_beschreibt(text[a:b].lower(), kat[x["id"]], c) for x in befunde if x["id"] in kat)]


def _satz_aus_phrase(phrase, seite=""):
    t = " ".join((phrase or "").split()).strip(" ,;:.")
    if seite and not re.search(r"(?<![a-zäöüß])(?:rechts|links|beidseits|beidseitig|bds)(?![a-zäöüß])", t, re.I):
        t = f"{t} {seite}"
    return (t[:1].upper() + t[1:] + ".") if t else ""


# ── v3.16.6 Kurzsätze (Peter 18.10.2026: „Diktierte Kurzsätze dürfen im Befund nie wegfallen.“) ─────────────────────
# Empfehlungs- und Einschränkungssätze, Muster in vorlagen_vorrang.json „kurzsaetze“ (EINE Quelle für EXE + Web).
# (1) ohne_empfehlungen: Text für die Vorlagenwahl ohne diese Sätze — „Gehaltene Aufnahmen … empfohlen“ löst nicht die
#     Stress-Vorlage aus (sonst befundet die KI nie gemachte Aufnahmen), „Die Hüfte ist nicht miterfasst“ nicht Becken+Hüfte.
# (2) kurzsaetze_sichern: fehlt nach der KI ein diktierter Empfehlungs-/Einschränkungssatz, kommt er wörtlich zurück.
# Sync: web_app/src/befundRegeln.ts (diktatSaetze, ohneEmpfehlungen, kurzsaetzeSichern), Fälle befund_regeln_fixtures.json
# „kurzsaetze“.
_KURZ_CACHE = {}
# Satzgrenzen zusätzlich zu saetze_mit_lage: „;“, gesprochenes „Punkt“ …, „12 mm.“ (mm/cm stehen dort als Abkürzung)
_KURZ_GRENZE = re.compile(r";|(?<![a-zäöüßA-ZÄÖÜ])(?:[pP]unkt|PUNKT|[nN]eue [zZ]eile|[nN]euzeile|[aA]bsatz)(?![a-zäöüßA-ZÄÖÜ])|(?<=[0-9] mm)\.(?=\s)|(?<=[0-9]mm)\.(?=\s)|(?<=[0-9] cm)\.(?=\s)|(?<=[0-9]cm)\.(?=\s)")


def _kurz(daten=None):
    d = (daten if daten is not None else _vorrang_laden()).get("kurzsaetze") or {}
    c = _KURZ_CACHE.get(id(d))
    if c is None:
        rx = lambda k: re.compile(d[k]) if d.get(k) else None  # noqa: E731
        c = {"d": d, "empf": rx("empfehlung"), "ein": rx("einschraenkung"), "vern": rx("verneinung"),
             "stopp": set(d.get("stoppwoerter") or []), "syn": d.get("synonyme") or {},
             "anteil": d.get("anteil", 0.5), "stamm": d.get("stamm", 5)}
        _KURZ_CACHE[id(d)] = c
    return c


def diktat_saetze(text):
    """Sätze eines Diktats [(start, ende)]: wie saetze_mit_lage, dazu „;“, gesprochenes „Punkt“/„neue Zeile“/„Absatz“
    und „15 mm.“ am Satzende."""
    out = []
    for a, b in saetze_mit_lage(text or ""):
        pos = a
        for m in _KURZ_GRENZE.finditer(text[a:b]):
            if text[pos:a + m.start()].strip():
                out.append((pos, a + m.start()))
            pos = a + m.end()
        if text[pos:b].strip():
            out.append((pos, b))
    return [(a + len(text[a:b]) - len(text[a:b].lstrip()), a + len(text[a:b].rstrip())) for a, b in out]


def _teilsaetze(text, a, b):
    """Teilsätze (Komma-Grenzen) im Bereich [a, b)."""
    out, pos = [], a
    for i in range(a, b):
        if text[i] == ",":
            out.append((pos, i))
            pos = i + 1
    out.append((pos, b))
    return [(x, y) for x, y in out if text[x:y].strip()]


def _kurz_treffer(text, c):
    """Bereiche [(start, ende, art)] der Empfehlungs- (art 'e', ganzer Satz) und Einschränkungs-Teilsätze (art 'n')."""
    out = []
    for i, (a, b) in enumerate(diktat_saetze(text)):
        s = text[a:b].lower()
        if c["empf"] is not None and c["empf"].search(s):
            teile = _teilsaetze(text, a, b)
            if i == 0:     # Satz 1 nennt die Untersuchung: nur Teilsätze nach dem ersten Komma
                out += [(x, y, "e") for x, y in teile[1:] if c["empf"].search(text[x:y].lower())]
            else:
                out.append((a, b, "e"))
            continue
        if c["ein"] is not None and c["ein"].search(s):
            for j, (x, y) in enumerate(_teilsaetze(text, a, b)):
                if (i or j) and c["ein"].search(text[x:y].lower()):
                    out.append((x, y, "n"))
    return out


def _kurz_marker(t, pos, saetze, daten=None):
    """Steht die Regionsnennung an pos in einem Empfehlungs- oder Einschränkungs-Teilsatz (ab pos bis zum Komma)?"""
    c = _kurz(daten)
    for a, b in saetze:
        if a <= pos < b:
            for x, y in _teilsaetze(t, a, b):
                if x <= pos < y:
                    s = t[pos:y].lower()
                    return bool((c["empf"] is not None and c["empf"].search(s)) or (c["ein"] is not None and c["ein"].search(s)))
    return False


def ohne_empfehlungen(text, daten=None):
    """Text für die Vorlagenwahl: Empfehlungssätze und Einschränkungs-Teilsätze („… nicht miterfasst“) entfernt.
    Ohne solche Sätze kommt der Text unverändert zurück."""
    t = text or ""
    treffer = _kurz_treffer(t, _kurz(daten))
    if not treffer:
        return text
    neu, pos = [], 0
    for a, b, _ in sorted(treffer):
        neu.append(t[pos:a])
        pos = max(pos, b)
    neu.append(t[pos:])
    rest = "".join(neu)
    return rest if rest.strip() else text


def _kurz_woerter(text):
    return vorlage_normalisieren(text).split()


def _kurz_stamm(c, w):
    return [w[:c["stamm"]]] + list(c["syn"].get(w, []))


def _kurz_inhalt(text, c):
    """Inhaltswörter eines diktierten Satzes → je Wort die Liste erlaubter Wortanfänge."""
    return [_kurz_stamm(c, w) for w in _kurz_woerter(text)
            if (len(w) >= 3 or w in c["syn"]) and w not in c["stopp"] and not w.isdigit()]


def _kurz_vorhanden(einheit, art, report_saetze, c):
    inhalt = _kurz_inhalt(einheit, c)
    rx = c["empf"] if art == "e" else c["ein"]
    if not inhalt:
        return any(rx is not None and rx.search(s.lower()) for s in report_saetze)
    noetig = max(1, -int(-len(inhalt) * c["anteil"] // 1))
    for s in report_saetze:
        ws = _kurz_woerter(s)
        hits = sum(1 for alt in inhalt if any(w.startswith(a) for w in ws for a in alt))
        low = s.lower()
        if art == "e":
            if hits >= noetig or (hits and rx is not None and rx.search(low)):
                return True
        elif hits >= noetig and c["vern"] is not None and c["vern"].search(low):
            return True
    return False


_KURZ_WEICHTEIL = re.compile(r"weichteil|weichgewebe|subkutan|subcutan|hautmantel", re.I)


def _befund_einfuegen(zeilen, a, e, satz):
    """Satz als letzten Befundsatz vor den Weichteil-Satz (der bleibt am Ende) in die Zeilen [a, e) einfügen."""
    inhalt = [i for i in range(a, e) if zeilen[i].strip() and not zeilen[i].lstrip().startswith("#")]
    if not inhalt:
        zeilen.insert(e, satz)
        return
    i = inhalt[-1]
    z = zeilen[i]
    lage = saetze_mit_lage(z)
    if lage and _KURZ_WEICHTEIL.search(z[lage[-1][0]:lage[-1][1]]):
        s0 = lage[-1][0]
        if z[:s0].strip():
            zeilen[i] = z[:s0] + satz + " " + z[s0:]
        elif len(inhalt) > 1:
            j = inhalt[-2]
            zeilen[j] = zeilen[j].rstrip() + " " + satz
        else:
            zeilen.insert(i, satz)
        return
    zeilen[i] = z.rstrip() + " " + satz


def kurzsaetze_sichern(report, diktat, daten=None):
    """Nach der KI (EXE + Web gleich): fehlt ein diktierter Empfehlungssatz → wörtlich als letzter Ergebnis-Punkt;
    fehlt eine diktierte Einschränkung („die BWS ist nicht abgebildet“) → wörtlich als Befundsatz vor dem Weichteil-Satz.
    → (report, Liste der Ergänzungen). Ohne solche Sätze im Diktat unverändert."""
    if not report or "## Ergebnis" not in report:
        return report, []
    c = _kurz(daten)
    d = diktat or ""
    treffer = _kurz_treffer(d, c)
    if not treffer:
        return report, []
    zeilen = report.split("\n")
    text_zeilen = [z for z in zeilen if not z.lstrip().startswith("#")]
    rtext = "\n".join(text_zeilen)
    rsaetze = [rtext[a:b] for a, b in saetze_mit_lage(rtext)]
    satz_lage = diktat_saetze(d)
    neu_erg, neu_bef = [], []
    for a, b, art in treffer:
        einheit = d[a:b]
        if _kurz_vorhanden(einheit, art, rsaetze, c):
            continue
        if art == "n" and not _kurz_inhalt(einheit, c):   # „eingeschränkt beurteilbar“ allein → ganzer Satz
            einheit = next((d[x:y] for x, y in satz_lage if x <= a < y), einheit)
        satz = satzform(" ".join(einheit.split()).strip(" ,;:"))
        if satz and satz not in neu_erg and satz not in neu_bef:
            (neu_erg if art == "e" else neu_bef).append(satz)
    if not neu_erg and not neu_bef:
        return report, []
    if neu_bef:
        bef = _abschnitt(zeilen, "befund")
        if bef:
            a, e = bef[0]
        else:   # ohne „## Befund“: alles zwischen Titel und Ergebnis
            e = next(i for i, z in enumerate(zeilen) if z.strip().lower().rstrip(":") == "## ergebnis")
            a = 0
        for s in neu_bef:
            _befund_einfuegen(zeilen, a, e, s)
            e = next(i for i, z in enumerate(zeilen) if z.strip().lower().rstrip(":") == "## ergebnis")
    if neu_erg:
        erg = _abschnitt(zeilen, "ergebnis")
        a, e = erg[-1]
        stelle = e
        while stelle > a and not zeilen[stelle - 1].strip():
            stelle -= 1
        zeilen[stelle:stelle] = neu_erg
        report = ergebnis_nummerieren("\n".join(zeilen))
    else:
        report = "\n".join(zeilen)
    return report, ["Befund ergänzt: " + s for s in neu_bef] + ["Ergebnis ergänzt: " + s for s in neu_erg]
