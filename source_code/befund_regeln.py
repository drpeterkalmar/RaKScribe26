"""befund_regeln.py — deterministische Befund-Regeln der EXE (v3.2).

Gleiche Semantik wie web_app/src/befundRegeln.ts (Web). Beide Engines laufen in
tests/offline/befund_regeln_test.py gegen dieselbe Tabelle befund_regeln_fixtures.json — Änderungen
IMMER an beiden Stellen + Fixture.

  split_regionen(text)        Diktat mit ≥2 Regionen ("Schulter rechts … Ellbogen rechts …", seit 19.11.2026 auch
                              ohne Seite am Satzanfang: "LWS: … Becken: …") → ein Segment je Region (je eigener Befund).
  ergebnis_nummerieren(rep)   Ergebnis-Zeilen ohne Nummer → "1. 2. 3."; ein einzelner
                              Ergebnispunkt bleibt unnummeriert (v3.18.3, Peter 12.11.2026).
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
# Hand, Zehe im Fuß) teilen sich die Gruppe → trennen nicht. Regionen ohne Seite (Wirbelsäule, Becken, Thorax …):
# REGIONEN_OHNE_SEITE darunter (seit kaiscribe-mehrfach-seitenlos-n1).
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

# kaiscribe-mehrfach-seitenlos-n1 (Georg 19.11.2026, CAS lws+bü in EINEM Diktat → nur ein LWS-Befund, Becken hineingemischt):
# Regionen ohne Seite trennen jetzt auch – aber nur als Satzanfang (Diktatanfang, nach Satzzeichen/„Punkt“/„neue Zeile“,
# nicht nach Komma) und als eigenes Wort („Fibroostosen am Becken“, „Beckenschiefstand“ trennen nicht). Untersuchungen
# einer Familie mit Kombi-Vorlage trennen untereinander weiter nicht: HWS/BWS/LWS (hws_und_lws, wirbelsäule_gesamt),
# Becken + Hüfte (beckenübersicht_und_hüfte), Kreuzbein + Steißbein. Sync: befundRegeln.ts REGIONEN_OHNE_SEITE
REGIONEN_OHNE_SEITE = [
    ("becken", r"becken(?:übersicht)?|bü|hüften\s+(?:beidseits|bds\.?)|beide\s+hüften"),
    ("lws", r"lws|lendenwirbelsäule"),
    ("bws", r"bws|brustwirbelsäule"),
    ("hws", r"hws|halswirbelsäule"),
    ("gws", r"gws|ganzwirbelsäule|gesamte\s+wirbelsäule|wirbelsäule\s+gesamt"),
    ("thorax", r"thorax|lunge"),
    ("schaedel", r"schädel"),
    ("nnh", r"nnh|nasennebenhöhlen"),
    ("abdomen", r"abdomen"),
    ("kreuzbein", r"kreuzbein|sakrum|sacrum|os\s+sacrum"),
    ("steissbein", r"steißbein|steissbein"),
]
# Familie → trennen untereinander nicht (seitige Hüfte gehört zur Becken-Familie)
_FAMILIE = {"lws": "ws", "bws": "ws", "hws": "ws", "gws": "ws", "becken": "becken", "huefte": "becken",
            "kreuzbein": "sakrum", "steissbein": "sakrum"}
_GRENZE_SATZ = r"(?:^|[.!?:;\n]|(?<!\w)punkt(?!\w)|(?<!\w)neue\s+zeile(?!\w)|(?<!\w)neuzeile(?!\w)|(?<!\w)absatz(?!\w))"
_OHNE_SEITE_RE = re.compile(
    _GRENZE_SATZ + r"\s*(" + _MOD + r"(?:(?:der|die|das|des)\s+)?(?P<r>" +
    "|".join(f"(?P<o_{g}>{pat})" for g, pat in REGIONEN_OHNE_SEITE) + r"))(?!\w)", re.I)


def _familie(key):
    return _FAMILIE.get(key[0], key[0] + "|" + key[1])


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
    marker = []  # (pos, key) — seitige Regionen + (seit kaiscribe-mehrfach-seitenlos-n1) Regionen ohne Seite am Satzanfang
    for m in _REGION_MARKER_RE.finditer(t):
        region = m.group("r1") or m.group("r2")
        seite = m.group("s1") or m.group("s2")
        marker.append((m.end() - len(m.group(1)), (_gruppe(region), _seite_norm(seite))))
    for m in _OHNE_SEITE_RE.finditer(t):
        g = next(g for g, _ in REGIONEN_OHNE_SEITE if m.group("o_" + g))
        marker.append((m.end() - len(m.group(1)), (g, "")))
    for pos, key in sorted(marker):
        if saetze is None:
            saetze = diktat_saetze(t)
        if _kurz_marker(t, pos, saetze):
            continue  # v3.16.6: „Fuß rechts in 2 Ebenen empfohlen“ / „Fuß rechts nicht miterfasst“ → keine eigene Region
        if starts and starts[-1][1] == key:
            continue  # gleiche Region + Seite → derselbe Befund
        if any(k == key for _, k in starts):
            continue  # Region kommt wieder vor (z.B. Rückbezug) → nicht erneut trennen
        if any(_familie(k) == _familie(key) and "" in (k[1], key[1]) for _, k in starts):
            continue  # HWS + LWS, Becken + Hüfte rechts: Kombi-Vorlage → derselbe Befund
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
# v3.19.x (Georg 17.11.2026, IB Lab LAMA): die LAMA-Schlussanmerkung „HKA = Hüft-Knie-Sprunggelenk-Winkel, …“ steht
# ohne Nummer unter dem Ergebnis (zählt nicht mit: ein einzelner LAMA-Punkt bleibt unnummeriert). Sync: befundRegeln.ts
# v3.19.8 (Georg 17.11.2026, IB Lab FROG): ebenso „Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS …“.
# v3.19.13 (Georg 18.11.2026, IB Lab HIPPO): ebenso „LCE = lateraler Center-Edge-Winkel …“ / „AI = …“ / „CCD = …“.
_UNNUM_RE = re.compile(r"^(?:im\s+)?vergleich\s+zu[rm]?\s+vor|^HKA = Hüft-Knie-Sprunggelenk-Winkel"
                       r"|^Weitere Winkelmessungen sind den KI-Auswertungsbildern"
                       r"|^(?:LCE|AI|CCD) = (?:lateraler Center-Edge|Acetabulumindex|Caput-Collum)"
                       r"|^Anmerkung:", re.I)   # kaiscribe-georg-2011-n1 (Punkt 9): „Anmerkung: …“-Block

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
    if len(zaehlbar) == 1:  # v3.18.3 (Peter 12.11.2026): EIN Ergebnispunkt wird nie nummeriert, auch eine Pathologie
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


# kaiscribe-georg-2011-n1 (Georg 20.11.2026, Punkte 19/40c/31): Rho steht IMMER als eigener Einzelbefund ganz am Schluss
# (nach allen Untersuchungen, auch bei Mehrfach) mit eigener Überschrift, eigenem Text und eigenem Ergebnis – nie im
# LWS- oder Becken-Teil. Ein diktierter Score unter 7 bringt keinen Text (Regel seit 19.11., RH 21: Rho 6).
RHO_TITEL = "Opportunistisches Knochendichtescreening (KI)"
RHO_AB = 7


def rho_einfuegen(report, score):
    """Eigener Befund „## Opportunistisches Knochendichtescreening (KI)“ (Variante C + Ergebnis Variante 2) am Ende;
    Score < 7 → unverändert."""
    if not report or RHO_ERGEBNIS in report:
        return report
    if score and score.isdigit() and int(score) < RHO_AB:
        return report
    s = f"Der Score von {score} (Skala 1–10) zeigt" if score else "Der Score von ≥7 (Skala 1–10) zeigt"  # Georg 13.10.: ohne diktierten Score immer ≥7
    return befunde_zusammenfuegen([report, f"## {RHO_TITEL}\n\n## Befund\n{RHO_BEFUND.format(score=s)}\n\n"
                                           f"## Ergebnis\n{RHO_ERGEBNIS}"])


def rho_ans_ende(report):
    """Mehrfach-Befund: den Rho-Befund (aus dem Abschnitt, in dem „Rho“ diktiert wurde) ans Ende stellen."""
    if not report or f"## {RHO_TITEL}" not in report:
        return report
    zeilen = report.split("\n")
    a = next(i for i, z in enumerate(zeilen) if z.strip() == f"## {RHO_TITEL}")
    e = a + 1
    while e < len(zeilen) and not (zeilen[e].strip().startswith("## ")
                                   and zeilen[e].strip()[3:].strip().lower().rstrip(":") not in ("befund", "ergebnis")):
        e += 1
    if e >= len(zeilen):
        return report
    block = "\n".join(zeilen[a:e]).strip()
    rest = re.sub(r"\n{4,}", "\n\n\n", "\n".join(zeilen[:a] + zeilen[e:]).strip())
    return befunde_zusammenfuegen([rest, block])


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
        c = {"d": d, "kat": [], "merk": {}, "strukt": {}, "vorrang": d.get("strukturen_vorrang") or {}}
        for k in d.get("kategorien") or []:
            c["kat"].append(dict(k, _re=re.compile(k["muster"]), _aus=re.compile(k["ausser"]) if k.get("ausser") else None,
                                 _bef=re.compile(k["befund"]) if k.get("befund") else None,
                                 _str=re.compile(k["streichen"]) if k.get("streichen") else None))
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


def _wid_vorrang(g, c):
    """Befund-Lage: eine genauere Struktur verdrängt die gröbere (strukturen_vorrang: AC-Gelenk statt Schulter — eine
    Tossy-Luxation betrifft das AC-Gelenk, nicht „Der Humeruskopf steht in regelrechter Artikulation“). Nur für den Befund; ein
    Normalsatz über AC- UND Schultergelenk bleibt in beiden Gruppen."""
    for n, weg in c.get("vorrang", {}).items():
        if n in g:
            g = g - set(weg)
    return g


# v3.18.11 (kaiscribe-3187-echttest-n1b, Echttest 14.11.2026 „Becken im Stehen …“): Chirp 3 schreibt gesprochene
# Satzzeichen als Marken („Randanbauten {Komma} links unauffällig {Punkt}“, auch „{ Punkt}“, „{Klammer-auf}“).
# Wörtlich übernommene Diktat-Teilsätze (Arthrose-Wächter 3.18.10, Kurzsätze 3.16.6) hatten sonst „} … {Komma} … {.“
# im Ergebnis. Vor dem Zerlegen werden die Marken zu Satzzeichen. Ohne „{“/„}“ bleibt der Text unverändert.
# Sync: befundRegeln.ts sttSatzzeichen, Fixtures „stt_satzzeichen“.
_STT_ZEICHEN = {"punkt": ".", "komma": ",", "doppelpunkt": ":", "semikolon": ";", "fragezeichen": "?",
                "ausrufezeichen": "!", "klammer auf": "(", "klammer zu": ")", "bindestrich": "-", "schrägstrich": "/"}
_STT_MARKE = re.compile(r"[ \t]*\{[ \t]*([^{}\n]*?)[ \t]*\}([ \t]*)")


def _stt_marke(m):
    w = " ".join(m.group(1).replace("-", " ").split())
    z = _STT_ZEICHEN.get(w.lower())
    if z is None:                                   # unbekannte Marke → ihr Wort
        return (" " + w if w else "") + m.group(2)
    if z in "(/":
        return (" (" if z == "(" else "/")
    return (" -" if z == "-" else z) + m.group(2)


def stt_satzzeichen(text):
    """Chirp-Marken „{Punkt}“, „{Komma}“ … → Satzzeichen; übrige „{“/„}“ weg, doppelte Satzzeichen einfach."""
    if not text or ("{" not in text and "}" not in text):
        return text
    t = _STT_MARKE.sub(_stt_marke, text).replace("{", "").replace("}", "")
    return re.sub(r"([.,;:!?])\1+", r"\1", t)


def widerspruch_befunde(diktat, daten=None):
    """Diktat → umschriebene/degenerative Befunde aus dem Katalog, nicht verneint („kein Fersensporn“ zählt nicht).
    Je Befund: id, name, phrase (diktierter Teilsatz), gruppen (Strukturen des Teilsatzes + Standard der Kategorie),
    global (Lage unbekannt bzw. die ganze Region, z. B. Osteopenie)."""
    c = _wid(daten)
    out = []
    for teil in _WID_TRENNER.split(stt_satzzeichen(diktat) or ""):
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
                eigene = _wid_vorrang(_wid_gruppen(t, c), c)
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
            "mm", "li", "re", "bds", "vs", "st", "p", "i", "dr", "o", "s", "co", "e", "g", "ap", "pa", "bspw", "usw",
            "dig", "proc"}   # kaiscribe-georg-2011-n1: „Dig. V“, „Proc. …“


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
        weg = {(x0, x1) for x0, x1, ids in treffer
               if any(kat[i].get("_str") is not None and kat[i]["_str"].search(text[x0:x1].lower()) for i in ids)}
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
                if (s0, s1) in weg:                 # verneint den Befund ausdrücklich („keine Luxation“) → streichen
                    aenderungen.append(f"gestrichen: {text[s0:s1].strip()[:60]}")
                    if text[s1:s1 + 1] == " ":
                        s1 += 1
                    elif neu[-1].endswith(" "):
                        neu[-1] = neu[-1][:-1]
                else:
                    neu.append(satz_einschraenken(text[s0:s1]))
                    aenderungen.append(f"eingeschränkt: {text[s0:s1].strip()[:60]}")
            pos = s1
        neu.append(text[pos:])
        text = "".join(neu)
        if weg:                                     # nach dem Streichen keine Leerzeichen am Zeilenende
            text = re.sub(r"[ \t]+(?=\n|$)", "", text)
        # kaiscribe-georg-2011-n1 (Georg 20.11.2026, RH 78): Schreibvarianten (c/k/z, femoropatellar↔patellofemoral)
        # zählen als beschrieben, ein schon dastehender Satz wird nie ein zweites Mal angehängt
        fehlend = [b for b in befunde if b["id"] in kat
                   and not any(_beschreibt(v, kat[b["id"]], c) for v in schreibvarianten(text))
                   and not phrase_vorhanden(b["phrase"], text)]
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


# ── v3.18.13 Abschnittsprüfung (Peter 14.11.2026: „er hat einen pathologischen befund und einen normalbefund gemeinsam
# geschrieben“ – Kanban #314, Echtfälle 12.11.: Erguss im Ergebnis neben „Unauffällige Weichteile.“, Schulter-Normalsatz
# „Humeruskopf in regelrechter Artikulation.“ im Hüftbefund). Nach widersprueche_bereinigen, je Region (## Titel … ## Befund
# … ## Ergebnis), ohne die Diktat-Erkennung zu brauchen:
#  (1) Befunde, die der Abschnitt SELBST nennt (Befundteil + Ergebnis, nicht verneint), gegen die Normalsätze desselben
#      Befundteils: einschränken („Im Übrigen …“) bzw. streichen (verneint ihn ausdrücklich) – fängt Befunde, die die
#      Diktat-Erkennung nicht als Befund sah. Nichts wird ergänzt, das Ergebnis bleibt.
#  (2) Normalsatz einer FREMDEN Vorlage (wörtlich aus templates.json, aus keiner zum Titel passenden Vorlage), der eine
#      Struktur nennt, die weder im Titel noch sonst im Abschnitt noch im Diktat vorkommt → weg.
# Ohne Treffer bleibt alles Zeichen für Zeichen gleich. Sync: befundRegeln.ts abschnitteBereinigen, Fixtures
# „abschnitte“ in befund_regeln_fixtures.json.
_VORLAGEN_SAETZE = {}
# Frühere Wortlaute von Vorlagensätzen (alte Briefe, Diktate, KI mit altem Stand): zählen wie der heutige Satz.
# kaiscribe-humeruskopf-artikel-n1 (Georg 16.11.2026 „Der Humeruskopf. Bitte ändern“). Sync: befundRegeln.ts VORLAGEN_ALTFORMEN.
VORLAGEN_ALTFORMEN = {
    "Der Humeruskopf steht in regelrechter Artikulation.": ("Humeruskopf in regelrechter Artikulation.",),
}


def _vorlagen_saetze(templates):
    """templates.json → ({normalisierter Satz: {Vorlagen-Keys}}, {Key: Strukturgruppen des Anzeigenamens})."""
    c = _VORLAGEN_SAETZE.get(id(templates))
    if c is None:
        w, gruppen = {}, {}
        cc = _wid()
        for key, t in (templates or {}).items():
            body = (t or {}).get("body") or ""
            for a, b in saetze_mit_lage(body):
                n = vorlage_normalisieren(body[a:b])
                if n:
                    w.setdefault(n, set()).add(key)
            gruppen[key] = _wid_gruppen(((t or {}).get("display_name") or key).lower(), cc)
        for neu, alte in VORLAGEN_ALTFORMEN.items():
            keys = w.get(vorlage_normalisieren(neu))
            for alt in alte if keys else ():
                w.setdefault(vorlage_normalisieren(alt), set()).update(keys)
        c = _VORLAGEN_SAETZE[id(templates)] = (w, gruppen)
    return c


def _regionen_bloecke(zeilen):
    """[(Titelzeile, Befund von, bis, Ergebnis von, bis)] je Region („## Titel“); fehlende Teile = None."""
    out = []
    for i, z in enumerate(zeilen):
        if not z.lstrip().startswith("## "):
            continue
        s = z.strip().lower().rstrip(":")
        if s == "## befund":
            if out:
                out[-1]["b"] = i + 1
        elif s == "## ergebnis":
            if out:
                out[-1]["e"] = i + 1
        else:
            out.append({"t": i, "b": None, "e": None})
    bloecke = []
    for n, x in enumerate(out):
        ende = out[n + 1]["t"] if n + 1 < len(out) else len(zeilen)
        ba, ea = x["b"], x["e"]
        be = None if ba is None else ((ea - 1) if ea is not None and ea > ba else ende)
        bloecke.append((x["t"], ba, be, ea, None if ea is None else ende))
    return bloecke


def abschnitte_bereinigen(report, diktat="", templates=None, daten=None):
    """v3.18.13 → (report, Liste der Änderungen); siehe Kommentar oben."""
    if not report or "## Befund" not in report:
        return report, []
    c = _wid(daten)
    kat = {k["id"]: k for k in c["kat"]}
    zeilen = report.split("\n")
    aenderungen = []
    d_gruppen = _wid_gruppen(stt_satzzeichen(diktat or "").lower(), c) - _WID_GENERISCH
    w, v_gruppen = _vorlagen_saetze(templates) if templates else ({}, {})
    for t_i, ba, be, ea, ee in reversed(_regionen_bloecke(zeilen)):
        if ba is None:
            continue
        text = "\n".join(zeilen[ba:be])
        if not ist_skelett_text(text, daten):
            continue
        ergebnis = "\n".join(zeilen[ea:ee]) if ea is not None else ""
        stellen = []                            # (start, ende, art) im Befundteil: e einschränken, s streichen, f fremd
        # Befunde nur aus Sätzen, die nicht wörtlich aus einer Vorlage stammen („Fissura orbitalis“ der Orbita-Vorlage
        # ist keine Fraktur, „… -konvexe Skoliose“ der Ganzaufnahme kein Befund)
        eigen = text if not w else " ".join(text[a:b] for a, b in saetze_mit_lage(text)
                                            if vorlage_normalisieren(text[a:b]) not in w)
        befunde = widerspruch_befunde(kl_deskriptor_neutral(eigen) + "\n" + ergebnis, daten)
        for x0, x1, ids in widerspruch_saetze(text, befunde, daten):
            weg = any(kat[i].get("_str") is not None and kat[i]["_str"].search(text[x0:x1].lower()) for i in ids)
            stellen.append((x0, x1, "s" if weg else "e"))
        t_gruppen = _wid_gruppen(zeilen[t_i].strip()[3:].lower(), c) - _WID_GENERISCH
        if w and t_gruppen:
            saetze = saetze_mit_lage(text)
            belegt = t_gruppen | d_gruppen | (_wid_gruppen(ergebnis.lower(), c) - _WID_GENERISCH)
            for a, b in saetze:
                keys = w.get(vorlage_normalisieren(text[a:b]))
                if not keys or any(v_gruppen.get(k, set()) & t_gruppen for k in keys):
                    continue
                sg = _wid_gruppen(text[a:b].lower(), c) - _WID_GENERISCH
                rest = set()
                for a2, b2 in saetze:
                    if (a2, b2) != (a, b):
                        rest |= _wid_gruppen(text[a2:b2].lower(), c) - _WID_GENERISCH
                if sg and not sg & (belegt | rest) and not any(x0 <= a < x1 for x0, x1, _ in stellen):
                    stellen.append((a, b, "f"))
        if not stellen:
            continue
        neu, pos = [], 0
        for s0, s1, art in sorted(stellen):
            if s0 < pos:
                continue
            neu.append(text[pos:s0])
            if art == "e":
                neu.append(satz_einschraenken(text[s0:s1]))
                aenderungen.append(f"eingeschränkt: {text[s0:s1].strip()[:60]}")
            else:
                aenderungen.append(("gestrichen: " if art == "s" else "fremder Vorlagensatz weg: ")
                                   + text[s0:s1].strip()[:60])
                if text[s1:s1 + 1] == " ":
                    s1 += 1
                elif neu[-1].endswith(" "):
                    neu[-1] = neu[-1][:-1]
            pos = s1
        neu.append(text[pos:])
        text = "".join(neu)
        if any(art != "e" for _, _, art in stellen):
            text = re.sub(r"[ \t]+(?=\n|$)", "", text)
        zeilen[ba:be] = text.split("\n")
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
    t = re.sub(r"^(?:wie bei|vereinbar mit)\s", "Bild wie bei ", t, flags=re.I)   # Regel 3q: „Bild wie bei …“
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
    d = stt_satzzeichen(diktat or "")              # v3.18.11: Chirp-Marken nie wörtlich ins Ergebnis
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


# ── v3.18.4 Kellgren-&-Lawrence-Wächter (Peter 12.11.2026, RH 38: „KaiScribe konfabuliert noch zu viel“) ─────────────
# Ein K&L-Grad steht nur, wenn er diktiert ist oder aus einem IB-Lab-Baustein (KOALA) kommt — nie aus dem Wortlaut
# („mäßige“ → Grad 3). Nach der KI: Grad-Angaben der KI („(Arthrose Grad X nach Kellgren & Lawrence)“, „Grad X nach
# Kellgren“), deren Grad weder im Diktat noch in erlaubt (IB Lab) steht → bei genau einem erlaubten Grad wird er
# eingesetzt, ohne erlaubten Grad fällt die Angabe weg (die Diagnose bleibt). Zeilen mit „(IB Lab …)“ bleiben unberührt.
# Sync: web_app/src/befundRegeln.ts (klGrade, klBereinigen), Fixtures befund_regeln_fixtures.json „kl“.
_KL_G = r"(?:[0-4]|IV|III|II|I|null|eins|zwei|drei|vier)"
_KL_G_KI = r"(?:[0-4]|IV|III|II|I|null|eins|zwei|drei|vier|X)"   # KI-Ausgabe: auch der Prompt-Platzhalter „Grad X“
_KL_WERT = {"0": "0", "null": "0", "1": "1", "i": "1", "eins": "1", "2": "2", "ii": "2", "zwei": "2", "3": "3",
            "iii": "3", "drei": "3", "4": "4", "iv": "4", "vier": "4"}
_KL_NAME = r"kellgren(?:[\s-]*(?:&|und)?[\s-]*lawrence)?"
_KL_SEITE = r"(?:\s*(?:links|rechts|beidseits))?"
_KL_TEXT = re.compile(
    r"(?<![\wäöüß])grad\s+(" + _KL_G + r")\s+nach\s+" + _KL_NAME +
    r"|(?<![\wäöüß])" + _KL_NAME + r"(?:[\s-]*(?:grad|grade|score|stadium))?" + _KL_SEITE + r"\s*:?\s*(" + _KL_G +
    r")(?![\wäöüß])"
    r"|(?<![\wäöüß])(?:kl|k\s*&\s*l)(?:[\s-]*(?:grad|grade))?" + _KL_SEITE + r"\s*:?\s*(" + _KL_G + r")(?![\wäöüß])",
    re.I)
# Grad-Angabe der KI im Befund: Klammer „(Arthrose Grad 3 nach Kellgren & Lawrence)“ bzw. „…, Grad 3 nach Kellgren …“
_KL_KI = re.compile(r"\s*\(\s*(?:Arthrose\s+)?Grad\s+(" + _KL_G_KI + r")\s+nach\s+Kellgren(?:\s*(?:&|und)\s*Lawrence)?\s*\)"
                    r"|,?\s*(?:Arthrose\s+)?Grad\s+(" + _KL_G_KI + r")\s+nach\s+Kellgren(?:\s*(?:&|und)\s*Lawrence)?",
                    re.I)
# v3.18.5 (Nachtrag RH 99): Arthrose-Wort im Diktat, auch als Verhörer („Koxartrose“, „Ommatrose“, „Gonathrose“)
_ARTHROSE_DIKTAT = re.compile(r"th?ros|rthrot|rtrot", re.I)
# Grad-Adjektiv direkt vor einer diktierten Arthrose (höchstens zwei Wörter dazwischen, z.B. „mäßige mediale Gonarthrose“)
_KL_ADJ = [("1", r"beginnend\w*|initial\w*|minimal\w*"), ("2", r"gering\w*|leicht\w*"),
           ("3", r"m[äa]ß\w*|mittelgradig\w*"), ("4", r"hochgradig\w*|ausgeprägt\w*|schwer\w*")]
_KL_ADJ_RE = re.compile(r"(?<![\wäöüß])(" + "|".join(r for _g, r in _KL_ADJ) + r")\s+(?:[\wäöüß-]+\s+){0,2}?"
                        r"[\wäöüß-]*(?:th?ros|rthrot|rtrot)", re.I)


# K&L-Deskriptor-Tabelle (freigegeben Georg Riegler/Peter Kalmar; Skill radiology-shoulder-dictation; im Gen-Prompt
# radiology_prompt.txt Abschnitt ARTHROSE; 80a36ae hatte sie gestrichen, zurück seit kaiscribe-kl-tabelle-zurueck-n1
# 18.11.2026). Gelenkunabhängig, gilt auch für den IB-Lab-Grad (KOALA). Wächter: tests/regel_register.
KL_TABELLE = {
    0: "Unauffälliger Gelenksspalt, keine Osteophyten.",
    1: "Geringe Osteophytenbildung, fragliche Gelenksspaltverschmälerung.",
    2: "Geringe Osteophytenbildung mit geringer Gelenksspaltverschmälerung und geringer Randzuschärfung.",
    3: "Mäßiggradige Gelenksspaltverschmälerung mit multiplen Osteophyten und subchondraler Sklerosierung.",
    4: "Aufgehobener Gelenksspalt mit ausgeprägter subchondraler Sklerosierung, Zystenbildung und ausgeprägten Osteophyten.",
}
# Grad-Adjektiv der Diagnose im Ergebnis (Georg 18.11.2026: „Mäßiggradige Gonarthrose links medial (Arthrose Grad 3 …)“)
KL_ADJEKTIV = {2: "Geringgradige", 3: "Mäßiggradige", 4: "Hochgradige"}


# Für die Befund-Erkennung der Widerspruchs-Wächter ist ein Tabellensatz die Arthrose selbst: seine Osteophyten, Zysten
# und Sklerose sind kein umschriebener Befund, der Kortikalis-/Knochenstruktur-Normalsätze einschränkt (Georg 18.11.2026,
# Nr. 34: „Glatte und scharfe Kontur der Kortikalis …“ bleibt neben „… mit multiplen Osteophyten …“). Sync: befundRegeln.ts
_KL_TAB_RE = re.compile("|".join(re.escape(s[:-1]) for g, s in sorted(KL_TABELLE.items(), key=lambda x: -len(x[1])) if g),
                        re.I)


def kl_deskriptor_neutral(text):
    """K&L-Tabellensätze (Grad 1–4, auch klein weitergeschrieben) → „Gelenkspaltverschmälerung“."""
    return _KL_TAB_RE.sub("Gelenkspaltverschmälerung", text or "")


def kl_klammer(grad):
    """„(Arthrose Grad 3 nach Kellgren & Lawrence)“ — Ergebnisformat (Regel-Register)."""
    return f"(Arthrose Grad {grad} nach Kellgren & Lawrence)"


def kl_grade(text):
    """Alle Kellgren-&-Lawrence-Grade im Text als Ziffern-Strings („Grad 2 nach Kellgren“, „Kellgren-Lawrence 3“,
    „Kellgren-Lawrence-Grad links 1“, „KL 2“, römisch/als Wort) → sortierte Liste ohne Doppel."""
    out = set()
    for m in _KL_TEXT.finditer(text or ""):
        g = next(x for x in m.groups() if x)
        out.add(_KL_WERT[g.lower()])
    return sorted(out)


def arthrose_diktiert(diktat):
    """v3.18.5 (Nachtrag RH 99): nennt das Diktat eine Arthrose (auch als Verhörer)?"""
    return bool(_ARTHROSE_DIKTAT.search(diktat or ""))


_FEMOROPATELLAR = re.compile(r"patell|femoropat", re.I)


def kl_adjektiv_grade(diktat, femoropatellar=False):
    """v3.18.5 (Peter 12.11.2026, Nachtrag RH 99: „mäßige Coxarthrose beidseits“ → K&L 3 bleibt): Grade zum Grad-Adjektiv
    einer DIKTIERTEN Arthrose (beginnend 1, gering 2, mäßig 3, hochgradig 4) → sortierte Liste. Ohne Arthrose-Wort leer.
    femoropatellar=True: nur Femoropatellar-/Retropatellar-/patellofemorale Arthrosen (18.11.2026, neben KOALA)."""
    out = set()
    for m in _KL_ADJ_RE.finditer(diktat or ""):
        if femoropatellar and not _FEMOROPATELLAR.search(m.group(0)):
            continue
        w = m.group(1)
        out.update(g for g, r in _KL_ADJ if re.fullmatch(r, w, re.I))
    return sorted(out)


def kl_bereinigen(report, diktat, erlaubt=()):
    """Nach der KI: nicht gedeckte K&L-Grade entfernen bzw. auf den einzigen erlaubten Grad setzen. Gedeckt ist (in
    dieser Reihenfolge) ein diktierter Grad, sonst ein IB-Lab-Grad (erlaubt) und — v3.18.5 — der Grad zum
    Grad-Adjektiv einer diktierten Arthrose (seit 18.11.2026 beide zusammen: KOALA femorotibial, Adjektiv femoropatellar). Der Prompt-Platzhalter „Grad X“ ist nie gedeckt. → (report, Änderungen)."""
    if not report or not re.search(r"kellgren", report, re.I):
        return report, []
    # kaiscribe-kl-tabelle-zurueck-n1 (Georg 18.11.2026, Nr. 50: KOALA KL 2 femorotibial + diktierte „mäßige patellofemorale
    # Arthrose“ = Grad 3): der IB-Lab-Grad (KOALA = femorotibial) geht im selben Kompartiment weiter vor, der Adjektiv-Grad
    # einer diktierten FEMOROPATELLAR-Arthrose gilt daneben
    ok = kl_grade(diktat) or (sorted(set(erlaubt) | set(kl_adjektiv_grade(diktat, femoropatellar=True))) if erlaubt
                              else kl_adjektiv_grade(diktat))
    aend = []

    def ersetzen(m):
        roh = (m.group(1) or m.group(2)).lower()
        g = _KL_WERT.get(roh, "X")
        if g in ok:
            return m.group(0)
        if len(ok) == 1:
            aend.append(f"K&L-Grad {g} → {ok[0]}")
            return re.sub(_KL_G_KI + r"(?=\s+nach)", ok[0], m.group(0), count=1, flags=re.I)
        if ok and g != "X":
            aend.append(f"K&L-Grad {g} nicht diktiert (diktiert/IB Lab: {', '.join(ok)}) – stehen gelassen")
            return m.group(0)
        aend.append(f"K&L-Grad {g} ohne Diktat/IB Lab entfernt")
        return ""

    zeilen = report.split("\n")
    for i, z in enumerate(zeilen):
        if "(IB Lab" in z or "kellgren" not in z.lower():
            continue
        zeilen[i] = _KL_KI.sub(ersetzen, z)
    return "\n".join(zeilen), aend


# ── v3.18.5 Arthrose-Wächter (Peter 12.11.2026, Nachtrag RH 99: Becken stehend + HIPPO-Messwerte, keine Arthrose diktiert →
# KaiScribe schlug „Coxarthrose (Kellgren & Lawrence Grad 3) beidseits“ vor). Nach der KI: Nennt das Diktat KEINE
# Arthrose (auch nicht als Verhörer), fällt jeder Ergebnis-Punkt weg, der eine Arthrose positiv nennt („Coxarthrose
# beidseits.“); verneinte Nennungen („Keine Coxarthrosezeichen.“), IB-Lab-Zeilen und die K&L-Klammer („… (Arthrose Grad 1
# nach Kellgren & Lawrence)“ hinter einem diktierten Befund, Grad von IB Lab — den prüft kl_bereinigen) bleiben. Fail-open: bei einem
# Arthrose-Wort im Diktat greift der Wächter nie. Sync: befundRegeln.ts arthroseBereinigen, Fixtures „arthrose“.
_ARTHROSE_KI = re.compile(r"arthros|arthrot", re.I)
_VERNEINT = re.compile(r"(?<![\wäöüß])(?:kein\w*|ohne|nicht|frei von)(?![\wäöüß])", re.I)


def arthrose_bereinigen(report, diktat, daten=None, behalten=()):
    """→ (report, Änderungen). Nur im Abschnitt „## Ergebnis“; die Nummerierung wird danach neu gesetzt.
    behalten: Ergebnispunkte, die KaiScribe selbst aus IB Lab eingesetzt hat (KOALA, 18.11.2026) – bleiben stehen."""
    if not report or "## Ergebnis" not in report or arthrose_diktiert(diktat) or not _ARTHROSE_KI.search(report):
        return report, []
    zeilen = report.split("\n")
    aend, raus, im_erg, erg = [], set(), False, set()
    for i, z in enumerate(zeilen):
        if z.strip().startswith("## "):
            im_erg = z.strip().startswith("## Ergebnis")
            continue
        if im_erg:
            erg.add(i)
        ohne_kl = _KL_KI.sub("", z)   # erlaubte K&L-Klammer (IB Lab) ist keine Arthrose-Diagnose
        if not im_erg or "(IB Lab" in z or not _ARTHROSE_KI.search(ohne_kl) \
                or re.sub(r"^\s*\d+\.\s*", "", z).strip() in behalten:
            continue
        vor = ohne_kl[:_ARTHROSE_KI.search(ohne_kl).start()]
        if _VERNEINT.search(vor):
            continue
        raus.add(i)
        aend.append("Arthrose ohne Diktat entfernt: " + re.sub(r"^\s*\d+\.\s*", "", z).strip())
    if not raus:
        return report, []
    # kaiscribe-konfab-regress-n1 (13.11.2026, RH 99 „Beginnende degenerative Veränderungen … mit kleinen Randanbauten“ →
    # KI „Beginnende Coxarthrose rechts“ → Ergebnis leer): an die Stelle des entfernten Punkts tritt der DIKTIERTE
    # degenerative Befund (Katalog „arthrose“ der Widerspruchs-Regeln), wenn das Ergebnis ihn nicht schon nennt
    rest = " ".join(zeilen[i] for i in sorted(erg - raus)).lower()
    statt = [s for s in dict.fromkeys(_satz_aus_phrase(b["phrase"]) for b in widerspruch_befunde(diktat, daten)
                                      if b["id"] == "arthrose")
             if s and s[:-1].lower() not in rest]
    erste = min(raus)
    neu = []
    for i, z in enumerate(zeilen):
        if i == erste:
            neu += statt
        if i not in raus:
            neu.append(z)
    aend += [f"diktierter Befund statt Arthrose: {s}" for s in statt]
    return ergebnis_nummerieren("\n".join(neu)), aend


# ── kaiscribe-georg-2011-n1 (Georg Riegler 20.11.2026, Diktiertag, Sammelliste + Durchsprache 15:20) ──────────────────
# Grundregeln NACH allen anderen Wächtern (EXE: je Abschnitt und noch einmal nach dem Einsetzen der IB-Lab-Texte; Web: je
# Abschnitt). Ohne Treffer bleibt der Text Zeichen für Zeichen gleich. Sync: befundRegeln.ts grundregeln, Fixtures
# „georg_2011“ in befund_regeln_fixtures.json.
#  7/14b/21a/32/RH 22/RH 80: Der Befund beginnt NIE mit „Im Übrigen …“/„Ansonsten …“. „Ansonsten“ wandert hinter die erste
#     Pathologie, „Im Übrigen“ nur hinter eine pathologische Stellung (Fraktur, Fehlstellung, Hochstand, Skoliose …); sonst
#     fällt das Wort weg („Im Übrigen normale Form und Stellung …“ → „Normale Form und Stellung …“).
#  10 Pleuraerguss: Sinus-Satz der betroffenen Seite raus, „Ansonsten das Zwerchfell beidseits glatt begrenzt.“ hinter den
#     Erguss-Satz (Georg OK).
#  14a/18/37b/40a Widerspruchsregel (diktiert ODER von der KI im Befund gezeigt): Humeruskopfhochstand → „… regelrechter
#     Artikulation“ raus; Infiltrat/DD infiltrativ → „kein … Infiltrat“ raus; Beckenschiefstand → „Anatomisch normale und
#     symmetrische Form des Beckenskeletts“ und „Beide Beckenschaufeln/-kämme stehen gleich hoch“ raus; Skoliose/Cobb
#     (SQUIRREL) → „Normaler Achsenverlauf“/„achsengerechte Stellung“ raus (Kyphose BWS + Lordose LWS bleiben, Georg final).
#  20 Diktierte Abstufung: „skoliotische Asymmetrie“ ohne diktierte „Skoliose“ wird im Ergebnis nicht zur Skoliose.
#  21b/RH 69 KI-Hinweise („KI: Verdacht auf …“, RBfracture) sind nie ein Ergebnispunkt (nur Hinweis).
#  38 Schreibweise „SI-Gelenksarthrose“.
#  42 Wirbelsäule: nie ein Kellgren-&-Lawrence-Grad (Unkovertebral-, Facetten-, Wirbelgelenke).
UEBRIGEN_ANFANG = re.compile(r"^(Im [Üü]brigen|Ansonsten)\b,?\s+")
_STELLUNG_PATHO = re.compile(r"fraktur|luxation|fehlstellung|disloz|dislokation|hochstand|skolio|listhes|dissoziation|"
                             r"achsabweich|achsfehl|seitausbieg|kontinuitätsunterbrech|fragment|valgus|varus|fehlhaltung|"
                             r"streckhaltung|beckenschiefstand|abkippung|versatz")
_NEG_NAH = re.compile(r"(?<![a-zäöüß])(?:kein[a-zäöüß]*|ohne|nicht|ausschluss|frei von)(?![a-zäöüß])")
_WS_TITEL = re.compile(r"wirbelsäule|halswirbel|brustwirbel|lendenwirbel|(?<![a-zäöüß])(?:hws|bws|lws|gws)(?![a-zäöüß])", re.I)
_THORAX_TITEL = re.compile(r"thorax|lunge", re.I)
GEORG_STREICHEN = [
    # (id, bejahter Befund im Diktat oder Befundtext, Titel-Bedingung, Sätze, die dann wegfallen)
    ("humeruskopfhochstand", r"hochstand des humeruskopf|humeruskopf[a-zäöüß]*hochstand|humeruskopf[a-zäöüß ]{0,25}hochstand|"
                             r"schulterhochstand|kopfhochstand", None,
     [r"humeruskopf[^.]*regelrechte[rn]? artikulation"]),
    ("infiltrat", r"infiltrat", None, [r"(?<![a-zäöüß])kein(?:e[nmrs]?)?(?![a-zäöüß])[^.]*infiltrat"]),
    ("beckenschiefstand", r"beckenschiefstand|beckenkippung|beckenhochstand|becken[a-zäöüß ]{0,15}schief", None,
     [r"symmetrische form des beckenskelett", r"becken(?:schaufeln|kämme)[^.]*gleich ?hoch"]),
    ("skoliose", r"skolio|seitausbieg|cobb", _WS_TITEL,
     [r"^(?:(?:im übrigen|ansonsten),?\s+)?normaler achsenverlauf",
      r"^(?:(?:im übrigen|ansonsten),?\s+)?(?:annähernd\s+)?achsengerechte stellung"]),
]
_GEORG_RX = [(i, re.compile(w), t, [re.compile(s) for s in ss]) for i, w, t, ss in GEORG_STREICHEN]
_KEINE_SKOLIOSE = re.compile(r"keine skoliose|kein[a-zäöüß]* (?:hinweis auf|nachweis einer?) skoliose")
_PLEURA = re.compile(r"pleuraerg(?:u|ü)(?:ss|ß)|pleuraeffusion|erg(?:u|ü)ss[a-zäöüß ]{0,20}pleura")
_ERGUSS_SATZ = re.compile(r"erg(?:u|ü)(?:ss|ß)|stumpf|randwinkel|winkelerguss")
_SINUS_FREI = re.compile(r"(?<![a-zäöüß])sinus(?![a-zäöüß])[^.]*(?<![a-zäöüß])frei(?![a-zäöüß])")
_ZWERCHFELL_NORMAL = re.compile(r"^(?:(?:im übrigen|ansonsten),?\s+)?(?:das\s+|beide\s+)?zwerchfell[a-zäöüß]*[^.]*"
                                r"(?:normaler lage|scharf|glatt)")
ZWERCHFELL_ANSONSTEN = "Ansonsten das Zwerchfell beidseits glatt begrenzt."
_KI_PUNKT = re.compile(r"^\s*(?:\d+\s*[.)]\s*)?(?:KI\s*[:(-]|\(KI\)|RBfracture\b)", re.I)
_SI_ARTHROSE = re.compile(r"(?<![\wÄÖÜäöüß-])(?:ISG|SIG|SI|Iliosakral|Iliosacral|Sakroiliakal|Sacroiliacal)"
                          r"(?:[- ]?[Gg]elenk(?:s|e)?)?[- ]?[Aa]rthrose(n?)(?![\wäöüß])")
_KL_KLAMMER_WS = re.compile(r"\s*\((?:Arthrose\s+)?Grad\s+(?:\d|[IVX]+)\s+nach\s+Kellgren[^)]*\)")
_SKOL_ABSTUFUNG = re.compile(r"skoliotische[a-zäöüß]*\s+(asymmetrie|fehlhaltung|haltung|seitabweichung)")


def _bejaht(text, rx):
    """Kommt rx in text (klein) vor, ohne dass im selben Teilsatz davor „kein/ohne/nicht …“ steht?"""
    for m in rx.finditer(text or ""):
        vor = text[max(0, m.start() - 60):m.start()]
        vor = re.split(r"[.;:,\n]", vor)[-1]
        if not _NEG_NAH.search(vor):
            return True
    return False


def _satz_weg(text, a, b):
    """text[a:b] samt einem Leerzeichen (und einer dadurch leeren Zeile) herausnehmen."""
    vor, nach = text[:a], text[b:]
    if nach[:1] == " ":
        nach = nach[1:]
    elif vor[-1:] == " ":
        vor = vor[:-1]
    if (not vor or vor.endswith("\n")) and nach[:1] == "\n":
        nach = nach[1:]
    return vor + nach


def _titel_vor(zeilen, i):
    for j in range(i - 1, -1, -1):
        s = zeilen[j].strip()
        if s.startswith("## ") and s[3:].strip().lower().rstrip(":") not in ("befund", "ergebnis"):
            return s[3:].strip()
    return ""


_VORLAGEN_WORTE = {}


def _worte(s):
    return tuple(sorted(w for w in re.split(r"[^a-zäöüß0-9-]+", (s or "").lower()) if w))


def _vorlage_zurueck(rest, templates):
    """„sind die Gelenkflächen normal geformt.“ → Vorlagensatz mit denselben Wörtern („Die Gelenkflächen sind …“)."""
    if not templates:
        return None
    c = _VORLAGEN_WORTE.get(id(templates))
    if c is None:
        c = {}
        for v in templates.values():
            body = v.get("body") if isinstance(v, dict) else ""
            for a, b in saetze_mit_lage(body or ""):
                c.setdefault(_worte(body[a:b]), body[a:b].strip())
        _VORLAGEN_WORTE[id(templates)] = c
    return c.get(_worte(rest))


def befund_anfang(text, templates=None):
    """Befundtext einer Untersuchung → (text, Änderung oder ""). Beginnt er mit „Im Übrigen“/„Ansonsten“: hinter die erste
    passende Pathologie stellen, sonst das Wort weglassen."""
    spans = saetze_mit_lage(text or "")
    if not spans:
        return text, ""
    a, b = spans[0]
    s = text[a:b]
    m = UEBRIGEN_ANFANG.match(s)
    if not m:
        return text, ""
    ansonsten = m.group(1).lower().startswith("ansonsten")
    for x, y in spans[1:]:
        t = text[x:y]
        if UEBRIGEN_ANFANG.match(t):
            continue
        if has_pathology(t) if ansonsten else _bejaht(t.lower(), _STELLUNG_PATHO):
            ohne = _satz_weg(text, a, b)
            y2 = y - (len(text) - len(ohne))
            return ohne[:y2] + " " + s + ohne[y2:], f"hinter die Pathologie: {s[:50]}"
    rest = s[m.end():]
    if _WID_VERB.match(rest.split(" ", 1)[0].lower()):
        neu = _vorlage_zurueck(rest, templates)
        if neu is None:
            return text, ""
    else:
        neu = rest[:1].upper() + rest[1:]
    return text[:a] + neu + text[b:], f"ohne „{m.group(1)}“: {neu[:50]}"


def _saetze_streichen(text, rxs):
    aend = []
    for a, b in reversed(saetze_mit_lage(text)):
        s = text[a:b]
        if any(rx.search(s.lower()) for rx in rxs):
            text = _satz_weg(text, a, b)
            aend.append(f"gestrichen: {s.strip()[:60]}")
    return text, aend


def _pleura(text, diktat):
    """Thorax mit Pleuraerguss: Sinus-Satz der betroffenen Seite raus, „Ansonsten das Zwerchfell …“ hinter den Erguss."""
    quelle = diktat.lower()
    m = next((x for x in _PLEURA.finditer(quelle)), None)
    seite = diktierte_seite(quelle[max(0, m.start() - 60):m.end() + 60]) if m else diktierte_seite(text)
    aend = []
    for a, b in reversed(saetze_mit_lage(text)):
        s = text[a:b].lower()
        if not _SINUS_FREI.search(s) or _bejaht(s, _ERGUSS_SATZ):
            continue
        andere = {"rechts": "links", "links": "rechts"}.get(seite)
        if seite != "beidseits" and ("übrig" in s or (andere and andere in s and (seite or "-") not in s)):
            continue
        aend.append(f"gestrichen: {text[a:b][:60]}")
        text = _satz_weg(text, a, b)
    spans = saetze_mit_lage(text)
    erguss = next(((x, y) for x, y in spans if _bejaht(text[x:y].lower(), _ERGUSS_SATZ)
                   and not _ZWERCHFELL_NORMAL.search(text[x:y].lower())), None)
    if erguss is None or ZWERCHFELL_ANSONSTEN in text:
        return text, aend
    for a, b in reversed(spans):
        if _ZWERCHFELL_NORMAL.search(text[a:b].lower()) and (a, b) != erguss:
            aend.append(f"gestrichen: {text[a:b][:60]}")
            if a < erguss[0]:
                d = len(text)
                text = _satz_weg(text, a, b)
                erguss = (erguss[0] - (d - len(text)), erguss[1] - (d - len(text)))
            else:
                text = _satz_weg(text, a, b)
    y = erguss[1]
    aend.append("ergänzt: " + ZWERCHFELL_ANSONSTEN)
    return text[:y] + " " + ZWERCHFELL_ANSONSTEN + text[y:], aend


_DAUMEN = re.compile(r"(?<![a-zäöüß])daumen(?![a-zäöüß])")
_ANDERER_FINGER = re.compile(r"zeigefinger|mittelfinger|ringfinger|kleinfinger|(?<![a-zäöüß])dig(?:itus|\.)?\s*(?:ii|iii|iv|v|[2-5])(?![a-z0-9])")
_DAUMEN_SATZ = re.compile(r"Normale Form der Phalangen((?: beidseits)?) und im Rahmen der Varianz auch des Endgliedes "
                          r"bei achsengerechter Stellung\.")
DAUMEN_SATZ = "Normale Form der Phalangen{bds}, achsengerechte Stellung."


def _daumen(zeilen, dk, aend):
    """28b/29: diktierter Daumen statt CAS-„Finger“ in Überschrift und Ergebnis; Daumen-Normalsatz ohne Varianz-Endglied."""
    nur_daumen = _bejaht(dk, _DAUMEN) and not _ANDERER_FINGER.search(dk)
    titel = ""
    for i, z in enumerate(zeilen):
        s = z.strip()
        if s.startswith("## ") and s[3:].strip().lower().rstrip(":") not in ("befund", "ergebnis"):
            if nur_daumen and re.match(r"## Finger(?![a-zäöüß])", s):
                zeilen[i] = z.replace("## Finger", "## Daumen", 1)
                aend.append(f"Überschrift Daumen statt Finger: {zeilen[i].strip()[:50]}")
            titel = zeilen[i]
            continue
        if s.startswith("## ") or "daumen" not in titel.lower():
            continue
        neu = _DAUMEN_SATZ.sub(lambda m: DAUMEN_SATZ.format(bds=m.group(1)), z)
        if nur_daumen:
            neu = re.sub(r"(?<![\wäöüß])des Fingers(?![\wäöüß])", "des Daumens", neu)
            neu = re.sub(r"(?<![\wäöüß])Finger(?=\s+(?:rechts|links|beidseits)(?![\wäöüß]))", "Daumen", neu)
        if neu != z:
            aend.append(f"Daumen: {neu.strip()[:50]}")
            zeilen[i] = neu


def grundregeln(report, diktat="", templates=None):
    """→ (report, Änderungen). Siehe Kopf dieses Abschnitts."""
    if not report or "## " not in report:
        return report, []
    zeilen = report.split("\n")
    aend = []
    dk = (diktat or "").lower()
    _daumen(zeilen, dk, aend)
    for a, e in reversed(_abschnitt(zeilen, "befund")):
        titel = _titel_vor(zeilen, a - 1)
        text = "\n".join(zeilen[a:e])
        tl = text.lower()
        for i, wenn, nur_titel, saetze in _GEORG_RX:
            if nur_titel is not None and not nur_titel.search(titel):
                continue
            if not (_bejaht(dk, wenn) or _bejaht(tl, wenn)):
                continue
            if i == "skoliose" and (_KEINE_SKOLIOSE.search(dk) or _KEINE_SKOLIOSE.search(tl)):
                continue
            text, x = _saetze_streichen(text, saetze)
            aend += [f"{i}: {z}" for z in x]
            tl = text.lower()
        if _THORAX_TITEL.search(titel) and (_bejaht(dk, _PLEURA) or _bejaht(tl, _PLEURA)):
            text, x = _pleura(text, diktat or "")
            aend += [f"pleuraerguss: {z}" for z in x]
        lead = len(text) - len(text.lstrip())
        neu, x = befund_anfang(text[lead:], templates)
        if x:
            text = text[:lead] + neu
            aend.append(x)
        zeilen[a:e] = text.split("\n")
    # Ergebnis: KI-Hinweise nie als Punkt, diktierte Abstufung „skoliotische Asymmetrie“
    skol = _SKOL_ABSTUFUNG.search(dk) if not re.search(r"skoliose|flachprofil", dk) else None
    erg = False
    for a, e in reversed(_abschnitt(zeilen, "ergebnis")):
        for i in range(e - 1, a - 1, -1):
            z = zeilen[i]
            if _KI_PUNKT.match(z):
                aend.append(f"KI-Hinweis nicht im Ergebnis: {z.strip()[:60]}")
                del zeilen[i]
                erg = True
            elif skol and re.search(r"(?<![\wäöüß])Skoliose(?![\wäöüß])", z):
                zeilen[i] = re.sub(r"(?<![\wäöüß])Skoliose(?![\wäöüß])", "skoliotische " + skol.group(1).capitalize(), z)
                aend.append(f"diktierte Abstufung: {zeilen[i].strip()[:60]}")
                erg = True
    out = "\n".join(zeilen)
    # 38: SI-Gelenksarthrose; 42: an der Wirbelsäule kein K&L-Grad
    si = _SI_ARTHROSE.sub(lambda m: "SI-Gelenksarthrose" + m.group(1), out)
    if si != out:
        aend.append("Schreibweise SI-Gelenksarthrose")
        out = si
    if "Kellgren" in out:
        zeilen, titel = out.split("\n"), ""
        for i, z in enumerate(zeilen):
            s = z.strip()
            if s.startswith("## ") and s[3:].strip().lower().rstrip(":") not in ("befund", "ergebnis"):
                titel = s[3:]
            elif _WS_TITEL.search(titel) and _KL_KLAMMER_WS.search(z):
                zeilen[i] = _KL_KLAMMER_WS.sub("", z)
                aend.append("Wirbelsäule ohne K&L-Grad")
                erg = True
        out = "\n".join(zeilen)
    if erg:
        out = ergebnis_nummerieren(out)
    return out, aend


# 13 (RH 78): Schreibvarianten für die Nachprüfung „Befund fehlt im Text“ – c/k/z (Chondrocalcinose ↔ Chondrokalzinose)
# und vertauschte Wortteile (femoropatellar ↔ patellofemoral, femorotibial ↔ tibiofemoral)
_VERTAUSCHT = (("femoropatellar", "patellofemoral"), ("femorotibial", "tibiofemoral"), ("retropatellar", "femoropatellar"))


def schreibvarianten(text):
    t = (text or "").lower()
    out = [t, re.sub(r"[kz]", "c", t), re.sub(r"c(?!h)", "k", t)]
    for x, y in _VERTAUSCHT:
        out += [v.replace(x, y) for v in out[:3] if x in v] + [v.replace(y, x) for v in out[:3] if y in v]
    return list(dict.fromkeys(out))


def _inhaltsworte(t):
    return {w for w in re.split(r"[^a-zäöüß0-9]+", re.sub(r"[kz]", "c", (t or "").lower())) if len(w) >= 4}


def phrase_vorhanden(phrase, text):
    """Steht der diktierte Teilsatz (bis auf Schreibvarianten) schon im Text? Alle Inhaltswörter (≥ 4 Buchstaben, Wortteile
    vertauscht) kommen vor."""
    worte = _inhaltsworte(phrase)
    if not worte:
        return False
    rest = " ".join(schreibvarianten(text))
    rest_c = re.sub(r"[kz]", "c", rest)
    def da(w):
        if w in rest_c:
            return True
        for x, y in _VERTAUSCHT:
            for p, q in ((x, y), (y, x)):
                if p in w and w.replace(p, q) in rest_c:
                    return True
        return False
    return all(da(w) for w in worte)
