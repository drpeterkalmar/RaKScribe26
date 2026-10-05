"""befund_regeln.py — deterministische Befund-Regeln der EXE (v3.2).

Gleiche Semantik wie web_app/src/befundRegeln.ts (Web). Beide Engines laufen in
befund_regeln_test.py gegen dieselbe Tabelle befund_regeln_fixtures.json — Änderungen
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
        if bv and (not lv or lv < bv):
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
    for m in _REGION_MARKER_RE.finditer(t):
        region = m.group("r1") or m.group("r2")
        seite = m.group("s1") or m.group("s2")
        key = (_gruppe(region), _seite_norm(seite))
        pos = m.end() - len(m.group(1))
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
    texte = {i: _BULLET_RE.sub("", _NUM_RE.sub("", lines[i])).strip() for i in items}
    zaehlbar = [i for i in items if not _UNNUM_RE.match(texte[i])]
    if len(zaehlbar) == 1 and _ist_normalsatz(texte[zaehlbar[0]]):
        out = list(lines)
        out[zaehlbar[0]] = texte[zaehlbar[0]]
        return out
    out = list(lines)
    n = 0
    for i in items:
        if i in zaehlbar:
            n += 1
            out[i] = f"{n}. {texte[i]}"
        else:
            out[i] = texte[i]
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


def nachbearbeiten(report):
    """Deterministische Nachbearbeitung jedes Befundes (EXE + Web gleich): CSA-Regel, '## Befund' sichern,
    Ergebnis nummerieren."""
    return ergebnis_nummerieren(befund_ueberschrift_sichern(csa_bereinigen(report)))


def befunde_zusammenfuegen(reports):
    """Mehrere Einzelbefunde (je ## Titel/## Befund/## Ergebnis) untereinander."""
    return "\n\n\n".join(r.strip() for r in reports if r and r.strip())
