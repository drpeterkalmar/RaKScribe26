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
# kaiscribe-schulter-ergebnis-n1 (Georg 23.11.2026, Punkt 65): unnummeriert bleibt nur die Einleitung „Vergleich zur
# Voruntersuchung vom …:“ (endet mit Doppelpunkt); ein Verlaufsvergleich als Aussage ist der 1. Punkt (georg_2311).
_UNNUM_RE = re.compile(r"^(?:im\s+)?vergleich\s+zu[rm]?\s+vor[^\n]*:$|^HKA = Hüft-Knie-Sprunggelenk-Winkel"
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
    r = mammasono_beidseits(befund_ueberschrift_sichern(csa_bereinigen(ergebnis_text_sichern(report) if nummerieren else report)))
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


# kaiscribe-rho-osteopen-n1 (Georg 22.11.2026): „Wir haben immer den Standardsatz Regelrechte Knochenmineralisation oder so
# ähnlich bei den Röntgenuntersuchungen. Wenn der Rho score grösser/gleich 7 ist muss der Satz raus. Anstattdessen:
# Osteopenischer Knochenaspekt“ – „Überall ersetzen“ (alle Untersuchungen des Auftrags, auch Mehrfach). Steht der
# Rho-Schlussbefund (Score ≥ 7) im Befund, wird in der Beschreibung JEDER Untersuchung der Mineralisations-Normalsatz
# (alle Formen aus templates.json/Prompt) durch OSTEOPEN_SATZ ersetzt; weitere Normalsätze dazu im selben Teil fallen weg
# (nie doppelt). „Im Übrigen …“/„Ansonsten …“ bleibt davor. Diktat nennt Mineralisation/Osteopenie/Osteoporose selbst →
# nichts. Ergebnis bleibt unverändert. Sync: web_app/src/befundRegeln.ts osteopenErsetzen (Fixtures „rho“ → „osteopen“).
OSTEOPEN_SATZ = "Osteopenischer Knochenaspekt."
_OSTEO_WORT = re.compile(r"mineral|kalksalz|knochenstruktur|spongiosa", re.I)
_OSTEO_NORMAL = re.compile(r"^(?:regelrecht|unauffällig|normal|regulär|altersentsprechend|altersgerecht|homogen)"
                           r"(?:e|er|em|en|es)?$")
_OSTEO_ERLAUBT = frozenset((
    "im übrigen ansonsten sonst die der das des den mitdargestellten mitabgebildeten abgebildeten dargestellten erfassten "
    "miterfassten übrigen skelettabschnitte skelettanteile knochen knöchernen ist sind stellt stellen sich dar zeigt zeigen "
    "bezüglich hinsichtlich mineralgehalt mineralisation knochenmineralisation knochenmineralgehalt kalksalzgehalt "
    "knochenstruktur knochenstrukturen spongiosastruktur und sowie bei scharfer scharf abgrenzbarkeit abgrenzbar "
    "spongiosabälkchen soweit erfasst mitabgebildet beckens femurs").split())
_OSTEO_VORSATZ = re.compile(r"^(im übrigen|ansonsten|sonst)\s+", re.I)
# Diktat bzw. Befund nennt die Knochendichte selbst → Diktat gilt, nichts ersetzen (nie doppelt)
_OSTEO_DIKTIERT = re.compile(r"mineral|osteopen|osteopor|kalksalz|entkalk|kalkarm|knochenarm|knochendicht|"
                             r"knochenatroph|demineral", re.I)
_OSTEO_IM_BEFUND = re.compile(r"osteopen|osteopor|demineral|kalksalzminder|kalkarm|vermindert\w*\s+(?:knochen)?mineral",
                              re.I)


def _osteo_normal(satz):
    """Ist der Satz(teil) nur der Mineralisations-Normalsatz („Mineralgehalt und Knochenstruktur regelrecht.“)?"""
    w = re.findall(r"[a-zäöüß]+", satz.lower())
    return (bool(w) and _OSTEO_WORT.search(satz) is not None and any(_OSTEO_NORMAL.match(x) for x in w)
            and all(x in _OSTEO_ERLAUBT or _OSTEO_NORMAL.match(x) for x in w))


def _osteo_satz(satz, erster):
    """Ein Satz → (neuer Satz | '' (weg) | None (bleibt)). erster: noch kein Ersatz in diesem Teil."""
    kern = satz.strip()
    if _osteo_normal(kern):
        if not erster:
            return ""
        m = _OSTEO_VORSATZ.match(kern)
        return f"{m.group(0)}{OSTEOPEN_SATZ[0].lower()}{OSTEOPEN_SATZ[1:]}" if m else OSTEOPEN_SATZ
    kopf, komma, rest = kern.partition(", ")           # „Mineralgehalt regelrecht, keine Fraktur.“
    if komma and rest.strip() and _osteo_normal(kopf):
        rest = rest.strip()
        return (OSTEOPEN_SATZ + " " if erster else "") + rest[0].upper() + rest[1:]
    return None


def _rho_ab7_im_befund(report):
    if f"## {RHO_TITEL}" not in report or RHO_ERGEBNIS not in report:
        return False
    m = re.search(r"Der Score von (≥\s*7|\d{1,2})\b", report)
    return m is None or not m.group(1).isdigit() or int(m.group(1)) >= RHO_AB


def osteopen_ersetzen(report, diktat=""):
    """Rho-Schlussbefund (Score ≥ 7) im Befund → Mineralisations-Normalsatz in der Beschreibung aller Untersuchungen durch
    „Osteopenischer Knochenaspekt.“ ersetzen. → (report, [Titel der geänderten Teile])."""
    if not report or not _rho_ab7_im_befund(report):
        return report, []
    if _OSTEO_DIKTIERT.search(rho_erkennen(diktat or "")[0] or ""):
        return report, []
    zeilen = report.split("\n")
    teile, titel, im_befund, rho = [], "", True, False      # (Zeilenindex, Titel) je Zeile der Beschreibung
    for i, z in enumerate(zeilen):
        st = z.strip()
        if st.startswith("## "):
            kopf = st[3:].strip().rstrip(":").lower()
            if kopf == "befund":
                im_befund = True
            elif kopf == "ergebnis":
                im_befund = False
            else:
                titel, im_befund, rho = st[3:].strip(), True, st == f"## {RHO_TITEL}"
            continue
        if im_befund and not rho and st:
            teile.append((i, titel))
    if any(_OSTEO_IM_BEFUND.search(zeilen[i]) for i, _ in teile):
        return report, []
    geaendert, ersetzt, weg = [], set(), set()
    for i, t in teile:
        stuecke = re.split(r"(?<=[.!?])(\s+)(?=[A-ZÄÖÜ])", zeilen[i])
        neu, anders = [], False
        for k in range(0, len(stuecke), 2):
            r = _osteo_satz(stuecke[k], t not in ersetzt)
            if r is None:
                neu.append(stuecke[k])
            else:
                anders = True
                ersetzt.add(t)
                if r:
                    neu.append(r)
            if k + 1 < len(stuecke):
                neu.append(stuecke[k + 1])
        if anders:
            zeilen[i] = re.sub(r"\s{2,}", " ", "".join(neu)).strip()
            if not zeilen[i]:
                weg.add(i)
            if t not in geaendert:
                geaendert.append(t)
    if not geaendert:
        return report, []
    out = []
    for k, z in enumerate(zeilen):
        if k in weg:
            continue
        if not z.strip() and out and not out[-1].strip() and (k - 1) in weg:
            continue                                   # weggefallener Absatz: keine doppelte Leerzeile
        out.append(z)
    return "\n".join(out), geaendert


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
                sd = wid_seite(t)
                if sd:
                    out[-1]["seite"] = sd
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
        ss = wid_seite(s)
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
            if treffer and _wid_betrifft(sg, x) and not (x.get("seite") and ss and ss != x["seite"]):
                ids.append(x["id"])
        if ids:
            out.append((a, b, ids))
    return out


_WID_GENERISCH = {"gelenk", "weichteile"}
# 3.20.2 (Abnahme 21.11.2026, Knie beidseits: „links geringe Gonarthrose“ – die KI schrieb richtig „Rechts sind die
# Gelenkflächen normal …“, der Wächter machte daraus „Im Übrigen sind Rechts …“): ein Normalsatz, der ausdrücklich die
# ANDERE Seite nennt, widerspricht einem Befund mit Seite nicht.
_WID_RECHTS = re.compile(r"(?<![a-zäöüß])rechts(?:seitig[a-zäöüß]*)?(?![a-zäöüß])|(?<![a-zäöüß])rechte[nrsm]?(?![a-zäöüß])", re.I)
_WID_LINKS = re.compile(r"(?<![a-zäöüß])links(?:seitig[a-zäöüß]*)?(?![a-zäöüß])|(?<![a-zäöüß])linke[nrsm]?(?![a-zäöüß])", re.I)
_WID_BEIDE = re.compile(r"(?<![a-zäöüß])(?:beidseit[a-zäöüß]*|bds|beide[nrsm]?)(?![a-zäöüß])", re.I)


def wid_seite(t):
    """„rechts“ | „links“ | "" (keine bzw. beide Seiten genannt)."""
    r, l = bool(_WID_RECHTS.search(t or "")), bool(_WID_LINKS.search(t or ""))
    if r == l or _WID_BEIDE.search(t or ""):
        return ""
    return "rechts" if r else "links"


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
                        r"gute?[rsnm]?|erhaltene?[rsnm]?|beide[rn]?|die|der|das|den|dem|des|eine?[rsnm]?|sie|es|rechts|links)$", re.I)


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
    # #401 (Georg 16.11.2026 in 2 Briefen von Hand „Der AC-Gelenk …“ ergänzt): Satz mit Artikel; alte Formen bleiben erkannt
    "Das AC-Gelenk ist altersentsprechend, keine Luxation.": ("AC-Gelenk altersentsprechend, keine Luxation.",
                                                              "Der AC-Gelenk altersentsprechend, keine Luxation."),
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
    adj_ok = not kl_grade(diktat) and not erlaubt
    for i, z in enumerate(zeilen):
        if "(IB Lab" in z or "kellgren" not in z.lower():
            continue
        # kaiscribe-schulter-ergebnis-n1 (Georg 23.11.2026, Punkt 70, RH 94: „geringgradige MTP-I-Arthrose“ → KI Grad 3):
        # mehrere Grad-Adjektive im Diktat → der Grad zum Adjektiv DIESER Diagnose (gleiche Zeile), nie ein anderer
        g_zeile = _kl_grad_zeile(_KL_KI.sub("", z)) if adj_ok else None
        if g_zeile and g_zeile in ok:
            def zeile(m, g=g_zeile):
                roh = (m.group(1) or m.group(2)).lower()
                ist = _KL_WERT.get(roh, "X")
                if ist == g:
                    return m.group(0)
                aend.append(f"K&L-Grad {ist} → {g} (Adjektiv derselben Diagnose)")
                return re.sub(_KL_G_KI + r"(?=\s+nach)", g, m.group(0), count=1, flags=re.I)
            zeilen[i] = _KL_KI.sub(zeile, z)
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
    # kaiscribe-schulter-ergebnis-n1 (Punkt 60/69, RH 30/88): diktierte Coxarthrose → „Keine Coxarthrosezeichen.“ raus
    ("coxarthrose", r"co[xk]arthros", None, [r"^(?:(?:im übrigen|ansonsten),?\s+)?keine co[xk]arthrosezeichen"]),
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


# 37c (Georg 20.11.2026; Abnahme 3.20.2 am 21.11., Knie beidseits: „Zarte Fibroostose … Im Übrigen normale Form und
# Stellung …“): die erste Zeile ist die Stellung – steht der Stellungssatz eingeschränkt hinter Pathologien, die die
# Stellung NICHT betreffen, kommt er ohne „Im Übrigen“ nach vorn.
STELLUNG_UEBRIGEN = re.compile(r"^Im [Üü]brigen,?\s+(normale[rn]?\s+(?:Form\s+und\s+)?Stellung\b.*)$", re.S)


def _stellung_vor(text, spans):
    for k, (x, y) in enumerate(spans[1:], 1):
        m = STELLUNG_UEBRIGEN.match(text[x:y])
        if not m:
            continue
        if any(_bejaht(text[p:q].lower(), _STELLUNG_PATHO) for p, q in spans[:k]):
            return text, ""
        satz = m.group(1)[:1].upper() + m.group(1)[1:]
        ohne = _satz_weg(text, x, y)
        a = spans[0][0]
        return ohne[:a] + satz + " " + ohne[a:], f"Stellung zuerst: {satz[:50]}"
    return text, ""


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
        return _stellung_vor(text, spans)
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


# 26 (RH 49, Georg): Titel der Kombi Becken + Hüfte mit einer Seite
_KOMBI_TITEL = re.compile(r"^## Beckenübersicht und Hüfte (rechts|links)(?: in 2 Ebenen)?[ \t]*$")
KOMBI_TITEL = "## Becken sowie Hüftgelenk in 2 Ebenen {seite}"


_SEITE_ADJ = re.compile(r"((?:^|[.!?]\s+|\n)(?:Rechts|Links|Beidseits)\s+)(Degenerative[nrs]?|Geringe[nrs]?|Geringgradige[nrs]?|"
                        r"Mäßige[nrs]?|Mäßiggradige[nrs]?|Deutliche[nrs]?|Ausgeprägte[nrs]?|Beginnende[nrs]?|"
                        r"Fortgeschrittene[nrs]?|Zarte[nrs]?|Kleine[nrs]?|Diskrete[nrs]?)(?=\s+[A-ZÄÖÜ])")
_SKOL_DIKTIERT = re.compile(r"(?<![a-zäöüß])skoliose(?![a-zäöüß])")
_SEITAUSBIEGUNG = re.compile(r"(?<![A-Za-zÄÖÜäöüß])Seitausbiegung(?![a-zäöüß])")
_GWS_AP_TITEL = re.compile(r"ganzaufnahme der wirbelsäule a\.?-?p", re.I)
_GWS_ERSTE = re.compile(r"(?:Normale Stellung|Alignementlinien|Rechtskonvexe skoliotische|Linkskonvexe skoliotische|"
                        r"Flachbogige|Skoliose)")
_KNIE_BDS_TITEL = re.compile(r"knie[a-zäöüß]*.*(?:beidseit|bds)", re.I)
_ANMERKUNG_ZEILE = re.compile(r"^(?:Anmerkung:|Weitere Winkelmessungen|HKA = |LCE = )")


def _seiten_rang(z):
    """Ergebnispunkt → 0 nur rechts, 1 beide/keine Seite, 2 nur links (stabil sortiert)."""
    sd = wid_seite(z)
    return 0 if sd == "rechts" else 2 if sd == "links" else 1


def grundregeln(report, diktat="", templates=None):
    """→ (report, Änderungen). Siehe Kopf dieses Abschnitts."""
    if not report or "## " not in report:
        return report, []
    zeilen = report.split("\n")
    aend = []
    for i, z in enumerate(zeilen):
        m = _KOMBI_TITEL.match(z.strip())
        if m:
            zeilen[i] = KOMBI_TITEL.format(seite=m.group(1))
            aend.append(f"Titel {zeilen[i][3:]}")
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
        if _SKOL_DIKTIERT.search(dk) and "skoliose" not in tl and _SEITAUSBIEGUNG.search(text):   # Diktat wörtlich
            text = _SEITAUSBIEGUNG.sub("Skoliose", text)
            aend.append("diktierte Skoliose statt „Seitausbiegung“")
            tl = text.lower()
        lead = len(text) - len(text.lstrip())
        neu, x = befund_anfang(text[lead:], templates)
        if x:
            text = text[:lead] + neu
            aend.append(x)
        if _GWS_AP_TITEL.search(titel):          # GWS a.p.: Beschriftung „Wirbelsäule:“ der Vorlage (KI ließ sie weg)
            lead = len(text) - len(text.lstrip())
            if _GWS_ERSTE.match(text[lead:]):
                text = text[:lead] + "Wirbelsäule: " + text[lead:]
                aend.append("GWS a.p.: Beschriftung „Wirbelsäule:“")
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
    # 33 (Georg 20.11.2026, Abnahme 21.11.: KI schrieb links vor rechts): Knie beidseits – im Ergebnis rechts zuerst
    for a, e in _abschnitt(zeilen, "ergebnis"):
        if not _KNIE_BDS_TITEL.search(_titel_vor(zeilen, a - 1)):
            continue
        idx = [i for i in range(a, e) if zeilen[i].strip() and not _ANMERKUNG_ZEILE.match(zeilen[i].strip())]
        alt = [zeilen[i] for i in idx]
        neu = sorted(alt, key=_seiten_rang)
        if neu != alt:
            for i, z in zip(idx, neu):
                zeilen[i] = z
            aend.append("Knie beidseits: Ergebnis rechts zuerst")
            erg = True
    out = "\n".join(zeilen)
    # Abnahme 21.11.: „Links Degenerative Veränderungen …“ → Adjektiv nach Seitenwort am Satzanfang klein
    klein = _SEITE_ADJ.sub(lambda m: m.group(1) + m.group(2).lower(), out)
    if klein != out:
        aend.append("Adjektiv nach Seitenwort klein")
        out = klein
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
    out, x = georg_2311(out, diktat, templates)   # kaiscribe-schulter-ergebnis-n1 (Georg 22./23.11.2026, Punkte 48–70)
    out, y = ursula_2011(out, templates)          # kaiscribe-ursula-2011-text-n1 (Ursula 20.11.2026, Punkte 3/4/7/10)
    return out, aend + x + y


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


# ══ kaiscribe-schulter-ergebnis-n1 (Georg Riegler 22./23.11.2026, Punkte 48–70) ═══════════════════════════════════════
# Läuft am Ende von grundregeln (EXE: je Abschnitt und nach den IB-Lab-Texten; Web: je Abschnitt). Ohne Treffer bleibt der
# Text Zeichen für Zeichen gleich, zweimal angewandt gleich. Sync: befundRegeln.ts georg2311, Fixtures „georg_2311“.
#  48a Schulter (Röntgen): Gelenksätze (glenohumeral/K&L) → AC-Gelenk → „Ansonsten die Gelenkflächen regelrecht
#      konturiert.“ → Enthesiopathie-Satz.
#  48b Röntgen, alle Orte: „Enthesiopathie(zeichen) <Ort>“ im BEFUND → „<Grad> kortikale Unregelmäßigkeiten und vermehrte
#      Sklerosierung am <Ort>.“ – Grad nur diktiert (gering→Geringe, mäßig→Mäßige, hochgradig→Hochgradige), sonst ohne.
#  48c Schulter-Ergebnis: Omarthrose → AC-Gelenk → Enthesiopathie.
#  50  Sono: diktierte Bursa-Pathologie streicht den Bursa-Normalsatz, der diktierte Satz steht an dessen Stelle;
#      „Kein Nachweis eines Step-sign …“ nur weg bei positivem Step-sign/Impingement.
#  51  Röntgen: Fraktur/Ausriss an die Stelle der Kortikalis-Beschreibung, unmittelbar danach KORTIKALIS_UEBRIGEN;
#      „Im Übrigen“/„Ansonsten“ nur nach einer Pathologie (sonst ohne das Wort).
#  53b Nervensono: Nerv unauffällig → eigener Ergebnispunkt „Unauffälliger Befund am N. <Name> <Seite>.“ (zuerst).
#  55b/60 Wortlaut: „Keine Zeichen einer periprothetischen Fraktur.“, „keine sichere periprothetische Fraktur“, „des Materials“.
#  58b/60b HIPPO: Beckenschiefstand ≥ 10 mm zusätzlich ins Ergebnis („Beckenschiefstand von 12 mm, links tiefer.“), das
#      Normal-Ergebnis entfällt; < 10 mm nur Beschreibung; HIPPO-Sätze nie im Wirbelsäulen-Teil.
#  60/68 Hüfte: Prothese, Coxarthrose oder auffälliger LCE-/AI-Winkel einer Seite → Normalsatz „Ordnungsgemäße Stellung der
#      normal geformten Hüftköpfe“ (bzw. Gelenkspalt-Satz) gilt nur noch für die andere Seite; beide Seiten → Satz raus.
#  56  Diktat „Dunn“ → Überschrift „… sowie Dunn-Aufnahme“ (beidseits: „Dunn-Aufnahmen beidseits“).
#  65  Verlaufsvergleich („unverändert zur Voruntersuchung …“) IMMER 1. Ergebnispunkt.
#  69/70 K&L: Grad im Ergebnis IMMER aus dem Adjektiv derselben Diagnose (beginnend 1, gering 2, mäßig 3, hochgradig 4)
#      bzw. aus dem diktierten Grad; fehlt die Klammer, kommt sie dazu; „A links und B rechts“ → zwei Punkte; im Befund der
#      K&L-Standardsatz je Seite statt des Diagnose-Satzes. Wirbelsäule/AC/ISG/Symphyse nie; Rhizarthrose ohne Klammer.
KORTIKALIS_UEBRIGEN = "Im Übrigen glatte und scharfe Begrenzung der normal breiten Kortikalis ohne pathologische Konturunterbrechung."
ENTHESIO_SATZ = "kortikale Unregelmäßigkeiten und vermehrte Sklerosierung"
NERV_UNAUFFAELLIG = "Unauffälliger Befund am N. {name}{seite}."
DUNN_TITEL = " sowie Dunn-Aufnahme"
DUNN_TITEL_BDS = " sowie Dunn-Aufnahmen beidseits"
# 56: Zusatzprojektionen, die (künftig auch aus dem Bildkopf) in die Überschrift kommen – aktiv nur Dunn (Georg 23.11.)
ZUSATZPROJEKTIONEN = {"dunn": {"aktiv": True, "diktat": r"(?<![a-zäöüß])dunn(?![a-zäöüß])", "region": r"hüft|becken"}}
_SCHNITT_TITEL = re.compile(r"sonogra|ultraschall|(?<![a-zäöüß])(?:mr|mrt|ct)(?![a-zäöüß])|magnetres|computertomo", re.I)
_SONO_TITEL = re.compile(r"sonogra|ultraschall", re.I)
_SCHULTER_TITEL = re.compile(r"schulter", re.I)
_BECKEN_TITEL = re.compile(r"becken|hüft", re.I)
_ANS_KONTUR = re.compile(r"^(?:ansonsten|im übrigen),?\s+(?:sind\s+)?die gelenkfl[äa]chen\s+(?:sind\s+)?regelrecht konturiert")
_ENTH_RX = re.compile(r"enthesiopath")
_AC_RX = re.compile(r"(?<![a-zäöüß])ac-|(?<![a-zäöüß])acg(?![a-zäöüß])|acromioclavicular|akromioklavikular")
_GELENK_RX = re.compile(r"glenohumeral|omarthros|gelenks?spalt|osteophyt|humeruskopf")
_ENTH_SATZ = re.compile(r"^(?:(?:im übrigen|ansonsten),?\s+)?(?:(?:geringe|mäßige|zarte|diskrete)\s+)?(?:zeichen\s+(?:einer|der)\s+)?"
                        r"(?:(gering\w*|leicht\w*|mäßig\w*|mittelgradig\w*|hochgradig\w*|ausgeprägt\w*|deutlich\w*|beginnend\w*)\s+)?"
                        r"enthesiopathi\w*\s+(.+?)\s*\.?$", re.I)
_ENTH_ADJ = [(r"gering|leicht", "Geringe"), (r"mäßig|mittelgradig", "Mäßige"), (r"hochgradig|ausgeprägt", "Hochgradige"),
             (r"beginnend", "Beginnende"), (r"deutlich", "Deutliche")]
_ENTH_DIKTAT = re.compile(r"(gering\w*|leicht\w*|mäßig\w*|mittelgradig\w*|hochgradig\w*|ausgeprägt\w*|deutlich\w*|beginnend\w*)"
                          r"\s+(?:\w+\s+)?enthesiopath", re.I)
_BURSA_PATHO = re.compile(r"bursitis|bursaverdick|bursa[a-zäöüß -]{0,40}(?:verdick|flüssigkeit|erguss|distendiert|distension)|"
                          r"(?:flüssigkeit|erguss)[a-zäöüß ]{0,30}bursa|step-?sign[a-zäöüß ]{0,15}positiv|positive[sn]? step-?sign")
_BURSA_NORMAL = re.compile(r"bursa[^.]*(?:ohne|kein\w*)\s[^.]*(?:wandverdick|flüssigkeit|erguss|bursitis|verdick)|"
                           r"(?:kein\w*|ohne)\s[^.]*(?:bursitis|flüssigkeit[^.]*bursa)")
_STEP_NORMAL = re.compile(r"^(?:(?:im übrigen|ansonsten),?\s+)?kein nachweis eines step-?sign")
_STEP_PATHO = re.compile(r"step-?sign[a-zäöüß ]{0,15}positiv|positive[sn]? step-?sign|impingement")
_FRAKTUR_RX = re.compile(r"fraktur|ausriss|fissur|infraktion|(?<![a-zäöüß])fragment")
_NICHT_DISLOZIERT = re.compile(r"(?<![a-zäöüß])nicht[- ](?:disloziert|dislociert|verschoben|verlagert)[a-zäöüß]*")
_KL_ADJ_SEITE = re.compile(r"(?<![a-zäöüß])(" + "|".join(r for _g, r in _KL_ADJ) + r")\s+(?:rechts|links|beidseits)(?![a-zäöüß])",
                           re.I)
_PATHO_EXTRA = re.compile(r"status post|zustand nach|(?<![a-zäöüß])(?:st\.|z\.)\s?[pn]\.|enthesi|unregelmäßig|prothes|(?<![a-zäöüß])tep(?![a-zäöüß])|"
                          r"ausriss|fragment|verdick|bursitis|degenerat|stenose|hypertroph|zyste|erosion|lockerung|sklerosier|"
                          r"osteophyt|randanbau|randzack|dysplas|steiles pfannendach|überdachung|coxa (?:valga|vara)|beckenschief|"
                          r"beinlängen|fibroostos|tendinos|ruptur|ganglion|lipom|tumor|raumforder|hämatom|serom|abszess")
_NERV_TITEL = re.compile(r"(?:sonogra|ultraschall)[^\n]*(?:(?<![a-zäöüß])n\.|nerv)", re.I)
_NERV_NAME = re.compile(r"(?:(?<![a-zäöüß])n\.|nervus|nerv)\s*(medianus|ulnaris|radialis|ischiadicus|peroneus|fibularis|tibialis|"
                        r"femoralis|suralis|pudendus|saphenus|obturatorius|axillaris|musculocutaneus|suprascapularis|"
                        r"iliohypogastricus|ilioinguinalis|cutaneus femoris lateralis|femoralis cutaneus lateralis)", re.I)
_NERV_PATHO = re.compile(r"verdick|auftreib|aufgetrieben|schwell|kompression|engpass|neurom|ödem|vergrößer|erhöht|hypoechogen|"
                         r"hyperäm|läsion|neuritis|irritation|luxation|instabil|einengung|kaliberschwank|neuropath|kompressions")
_BS_GROSS = re.compile(r"Beckenschiefstand von (\d+) mm(?:,\s*(rechts|links) tiefer(?:stehend)?)?")
_HIPPO_SATZ = re.compile(r"^(?:Geringer Beckenschiefstand|Beckenschiefstand von|Kein Beckenschiefstand|Beinlängendifferenz von|"
                         r"Keine Beinlängendifferenz)")
_VERLAUF = re.compile(r"unverändert\w*[^.]{0,60}(?:vor(?:untersuchung|befund|aufnahme)|vergleich)|"
                      r"vergleich zu[rm]? vor(?:untersuchung|aufnahme|befund)|befund(?:änderung|konstanz|progredienz)|"
                      r"zur voruntersuchung|größenkonstant", re.I)
_HUEFTKOPF_BDS = re.compile(r"^(?:(?:Im [Üü]brigen|Ansonsten),?\s+)?(?:[Oo]rdnungsgemäße|[Nn]ormale|[Rr]egelrechte) Stellung der normal "
                            r"geformten Hüftköpfe\.$")
_HUEFTKOPF_EIN = re.compile(r"^(?:(?:Im [Üü]brigen|Ansonsten),?\s+)?(?:[Oo]rdnungsgemäße|[Nn]ormale|[Rr]egelrechte) Stellung des normal "
                            r"geformten (rechten|linken) Hüftkopfes\.$")
_HUEFT_SPALT = re.compile(r"^(?:(?:Im [Üü]brigen|Ansonsten),?\s+)?(?:(Rechts|Links) )?[Nn]ormal konfigurierte, glatte Gelenkflächen mit "
                          r"allseits normal weitem Gelenkspalt\.$")
_HUEFT_EIN_FORM = re.compile(r"^(?:(?:Im [Üü]brigen|Ansonsten),?\s+)?Anatomisch normale Form des Hüftgelenkes mit regelrechter "
                             r"Stellung des Hüftkopfes in der Pfanne\.$")
_HUEFT_BETROFFEN = re.compile(r"prothes|(?<![a-zäöüß])tep(?![a-zäöüß])|endoprothes|coxarthros|koxarthros|dysplas|steiles pfannendach|"
                              r"grenzwertige überdachung|lce-winkel beträgt|ai-winkel beträgt|acetabulumindex beträgt|"
                              r"(?<![a-zäöüß])(?:lce|ai)(?:-winkel)?\s+(?:von\s+)?(?:rechts\s+|links\s+)?\d")
_KL_AUSNAHME = re.compile(r"(?<![a-zäöüß])(?:ac|acg|si|isg)(?![a-zäöüß])|acromioclavicular|akromioklavikular|iliosakral|sakroiliakal|"
                          r"symphys|facetten|spondyl|unkovertebral|uncovertebral|wirbel|rhizarthros|daumensattel", re.I)
_KL_DOPPEL = re.compile(r"^((?:[A-ZÄÖÜ][a-zäöüß]+\s+)?)([A-ZÄÖÜa-zäöüß-]*[Aa]rthrose)\s+(rechts|links)\s+und\s+([a-zäöüß]+)\s+"
                        r"(?:(?:[A-ZÄÖÜa-zäöüß-]*[Aa]rthrose)\s+)?(rechts|links)\s*\.?$")
_WORT_ERSETZEN = [
    (re.compile(r"(?<![A-Za-zÄÖÜäöüß])([Kk])einerlei Zeichen einer (?:peri)?(?:prothetischen|peripherischen|periprothetischen) Fraktur"),
     lambda m: m.group(1) + "eine Zeichen einer periprothetischen Fraktur"),
    (re.compile(r"(?<![A-Za-zÄÖÜäöüß])(?:peripherischen|prothetischen)(?= Fraktur)"), lambda m: "periprothetischen"),
    (re.compile(r"(?<![A-Za-zÄÖÜäöüß])([Kk])ein(?:e)? sicheres? periprothetische[n]? Fraktur"),
     lambda m: m.group(1) + "eine sichere periprothetische Fraktur"),
    (re.compile(r"(?<![A-Za-zÄÖÜäöüß])des Material post(?![A-Za-zÄÖÜäöüß])|(?<![A-Za-zÄÖÜäöüß])des Material(?=[.,;])"),
     lambda m: "des Materials"),
]


def _patho_satz(s):
    t = re.sub(r"^(?:im übrigen|ansonsten),?\s+", "", (s or "").lower())
    return has_pathology(t) or _bejaht(t, _PATHO_EXTRA)


def _zerlegen(text):
    """Befundtext → Zeilen als Satzlisten (None = Leerzeile)."""
    return [None if not z.strip() else [z[a:b].strip() for a, b in saetze_mit_lage(z)] for z in text.split("\n")]


def _flach(L):
    return [(i, k) for i, z in enumerate(L) if z for k in range(len(z))]


def _zusammen(L):
    out, leer = [], False
    for z in L:
        if z is None:
            if not leer or not out:
                out.append("")
            leer = True
        elif z:
            out.append(" ".join(z))
            leer = False
    return "\n".join(out)


def _umstellen(L, raus, nach, neue):
    """Sätze (flache Indizes raus) herausnehmen und neue hinter den Satz mit flachem Index nach (−1 = vorn) setzen."""
    pos = _flach(L)
    ziel = pos[nach] if 0 <= nach < len(pos) else None
    M = [None if z is None else [(s, (i, k)) for k, s in enumerate(z)] for i, z in enumerate(L)]
    weg = {pos[r] for r in raus}
    for i, z in enumerate(M):
        if z is not None:
            M[i] = [x for x in z if x[1] not in weg]
    if ziel is None:
        i0 = next((i for i, z in enumerate(M) if z is not None), None)
        if i0 is None:
            return L
        M[i0] = [(s, None) for s in neue] + M[i0]
    else:
        z = M[ziel[0]]
        j = next(j for j, x in enumerate(z) if x[1] == ziel)
        M[ziel[0]] = z[:j + 1] + [(s, None) for s in neue] + z[j + 1:]
    return [None if z is None else ([s for s, _ in z] if z else []) for z in M]


def _saetze_von(L):
    return [L[i][k] for i, k in _flach(L)]


def _schulter_ordnen(L):
    s = _saetze_von(L)
    kat = []
    for x in s:
        t = x.lower()
        if _ANS_KONTUR.match(t):
            kat.append("ans")
        elif ENTHESIO_SATZ.lower() in t or _bejaht(t, _ENTH_RX):
            kat.append("ent")
        elif _AC_RX.search(t):
            kat.append("ac")
        elif _GELENK_RX.search(t) or _KL_TAB_RE.search(x):
            kat.append("g")
        else:
            kat.append("")
    if "ans" not in kat and "ent" not in kat:
        return L
    g = [i for i, k in enumerate(kat) if k == "g"]
    letzt_g = g[-1] if g else -1
    acs = [i for i, k in enumerate(kat) if k == "ac" and i < letzt_g]
    raus = [i for i, k in enumerate(kat) if k in ("ans", "ent")] + acs
    anker = [i for i, k in enumerate(kat) if k in ("g", "ac") and i not in raus]
    if not anker:
        return L
    neu = [s[i] for i in acs] + [s[i] for i, k in enumerate(kat) if k == "ans"] + [s[i] for i, k in enumerate(kat) if k == "ent"]
    reihe = [i for i in range(len(s)) if i not in raus]
    p = reihe.index(anker[-1]) + 1
    if [s[i] for i in reihe[:p]] + neu + [s[i] for i in reihe[p:]] == s:
        return L
    return _umstellen(L, raus, anker[-1], neu)


def _enthesio(satz, dk):
    m = _ENTH_SATZ.match(satz)
    if not m or not m.group(2):
        return None
    ort = m.group(2).strip().rstrip(".")
    ol = ort.lower()
    if re.match(r"(?:am|an der|an den|an|im bereich)\s", ol):
        pass
    elif ol.startswith("des "):
        ort = "am " + ort[4:]
    elif ol.startswith("der "):
        ort = "an der " + ort[4:]
    elif ol.startswith("vom "):
        ort = "am " + ort[4:]
    elif ol.startswith("von der "):
        ort = "an der " + ort[8:]
    else:
        ort = "am " + ort
    adj = m.group(1)
    if not adj:
        md = _ENTH_DIKTAT.search(dk or "")
        adj = md.group(1) if md else ""
    wort = next((w for rx, w in _ENTH_ADJ if adj and re.match(rx, adj, re.I)), "")
    return (f"{wort} {ENTHESIO_SATZ} {ort}." if wort else f"{ENTHESIO_SATZ[0].upper()}{ENTHESIO_SATZ[1:]} {ort}.")


def _bursa(L, dk):
    s = _saetze_von(L)
    n = next((i for i, x in enumerate(s) if "bursa" in x.lower() and _BURSA_NORMAL.search(x.lower())
              and not _STEP_NORMAL.match(x.lower())), None)
    st = next((i for i, x in enumerate(s) if _STEP_NORMAL.match(x.lower())), None)
    rest = " ".join(x.lower() for i, x in enumerate(s) if i not in (n, st))
    aend = []
    raus, neu, nach = [], [], -1
    if st is not None and (_bejaht(dk, _STEP_PATHO) or _bejaht(rest, _STEP_PATHO)):
        raus.append(st)
        aend.append(f"Step-sign-Normalsatz gestrichen: {s[st][:50]}")
    if n is not None and (_bejaht(dk, _BURSA_PATHO) or _bejaht(rest, _BURSA_PATHO)):
        p = next((i for i, x in enumerate(s) if i not in (n, st) and _bejaht(x.lower(), _BURSA_PATHO)), None)
        raus.append(n)
        aend.append(f"Bursa-Normalsatz gestrichen: {s[n][:50]}")
        if p is not None:
            raus.append(p)
            neu = [s[p]]
            vor = [i for i in range(n) if i not in raus]
            nach = vor[-1] if vor else -1
    if not raus:
        return L, []
    return _umstellen(L, sorted(set(raus)), nach, neu), aend


def _fraktur(L):
    s = _saetze_von(L)
    f = [i for i, x in enumerate(s) if _bejaht(_NICHT_DISLOZIERT.sub("", x.lower()), _FRAKTUR_RX) and not UEBRIGEN_ANFANG.match(x)]
    k = next((i for i, x in enumerate(s) if "kortikalis" in x.lower() and re.search(r"glatt|scharf|regelrecht", x.lower())
              and i not in f), None)
    if not f or k is None:
        return L, []
    nach_k = [i for i in f if i > k]
    if not nach_k:
        if k == f[-1] + 1 and s[k] == KORTIKALIS_UEBRIGEN:
            return L, []
        return _umstellen(L, [k], f[-1], [KORTIKALIS_UEBRIGEN]), ["Kortikalis-Satz direkt hinter die Fraktur"]
    vor = [i for i in range(k) if i not in nach_k]
    return (_umstellen(L, nach_k + [k], vor[-1] if vor else -1, [s[i] for i in nach_k] + [KORTIKALIS_UEBRIGEN]),
            ["Fraktur an die Stelle der Kortikalis-Beschreibung"])


def _uebrigen_nur_nach_patho(L, templates):
    s = _saetze_von(L)
    aend = []
    for j in range(1, len(s)):
        m = UEBRIGEN_ANFANG.match(s[j])
        if not m or any(_patho_satz(x) for x in s[:j]):
            continue
        rest = s[j][m.end():]
        if _WID_VERB.match(rest.split(" ", 1)[0].lower()):
            neu = _vorlage_zurueck(rest, templates)
            if neu is None:
                continue
        else:
            neu = rest[:1].upper() + rest[1:]
        aend.append(f"ohne „{m.group(1)}“ (keine Pathologie davor): {neu[:50]}")
        pos = _flach(L)[j]
        L[pos[0]][pos[1]] = neu
        s[j] = neu
    return L, aend


def _seiten_aus(t, titel_seite=""):
    t = (t or "").lower()
    if re.search(r"beidseit|(?<![a-zäöüß])bds(?![a-zäöüß])|beider", t):
        return {"rechts", "links"}
    out = set()
    if _WID_RECHTS.search(t):
        out.add("rechts")
    if _WID_LINKS.search(t):
        out.add("links")
    return out or ({titel_seite} if titel_seite in ("rechts", "links") else set())


def _huefte_seiten(L, titel):
    """60/68: Hüftseiten mit Prothese, Coxarthrose oder auffälligem LCE-/AI-Winkel → Normalsätze nur für die andere Seite."""
    ts = wid_seite(titel)
    s = _saetze_von(L)
    betr = set()
    for x in s:
        t = x.lower()
        if _HUEFTKOPF_BDS.match(x) or _HUEFTKOPF_EIN.match(x) or _HUEFT_SPALT.match(x) or _HUEFT_EIN_FORM.match(x):
            continue
        for m in _HUEFT_BETROFFEN.finditer(t):
            vor = re.split(r"[.;:,\n]", t[max(0, m.start() - 60):m.start()])[-1]
            if _NEG_NAH.search(vor):
                continue
            betr |= _seiten_aus(t, ts)
    if not betr:
        return L, []
    aend = []
    einzeln = "becken" not in titel.lower()          # ein Hüftgelenk (Titel mit Seite), kein Becken
    beide = betr >= {"rechts", "links"}
    andere = ({"rechts", "links"} - betr).pop() if not beide else ""
    adj = {"rechts": "rechten", "links": "linken"}
    for idx, (i, k) in reversed(list(enumerate(_flach(L)))):
        x = L[i][k]
        neu = x
        if _HUEFTKOPF_BDS.match(x):
            neu = "" if beide else f"Ordnungsgemäße Stellung des normal geformten {adj[andere]} Hüftkopfes."
        elif _HUEFTKOPF_EIN.match(x):
            seite = "rechts" if _HUEFTKOPF_EIN.match(x).group(1) == "rechten" else "links"
            if seite in betr:
                neu = ""
        elif _HUEFT_SPALT.match(x):
            sm = _HUEFT_SPALT.match(x).group(1)
            if sm:
                if sm.lower() in betr:
                    neu = ""
            elif einzeln:
                if ts in betr or not ts:
                    neu = ""
            elif beide:
                neu = ""
            else:
                neu = f"{andere.capitalize()} normal konfigurierte, glatte Gelenkflächen mit allseits normal weitem Gelenkspalt."
        elif _HUEFT_EIN_FORM.match(x) and einzeln and (ts in betr or not ts):
            neu = ""
        if neu != x:
            aend.append(f"Hüfte {'/'.join(sorted(betr))}: {x[:45]} → {neu[:45] or 'gestrichen'}")
            if neu:
                L[i][k] = neu
            else:
                del L[i][k]
    return L, aend


def _kl_grad_zeile(z):
    m = _KL_ADJ_RE.search(z or "")
    if not m:
        return None
    w = m.group(1)
    return next((g for g, r in _KL_ADJ if re.fullmatch(r, w, re.I)), None)


def _befund_ops(text, titel, dk, templates):
    """Befundtext eines Teils → (text, Änderungen)."""
    L = _zerlegen(text)
    if not _flach(L):
        return text, []
    aend = []
    schnitt = bool(_SCHNITT_TITEL.search(titel))
    if not schnitt:
        for i, k in _flach(L):
            x = L[i][k]
            if _bejaht(x.lower(), _ENTH_RX) and not x.lower().startswith(("kein", "ohne")):
                neu = _enthesio(x, dk)
                if neu and neu != x:
                    L[i][k] = neu
                    aend.append(f"Enthesiopathie beschreibend: {neu[:50]}")
        if _SCHULTER_TITEL.search(titel):
            L2 = _schulter_ordnen(L)
            if L2 is not L:
                L = L2
                aend.append("Schulter: Gelenk → AC → „Ansonsten …“ → Enthesiopathie")
        if not _WS_TITEL.search(titel) and not _THORAX_TITEL.search(titel):
            L, x = _fraktur(L)
            aend += x
    if _SONO_TITEL.search(titel):
        L, x = _bursa(L, dk)
        aend += x
    if _BECKEN_TITEL.search(titel) and not schnitt:
        L, x = _huefte_seiten(L, titel)
        aend += x
    L, x = _uebrigen_nur_nach_patho(L, templates)
    aend += x
    if not aend:
        return text, []
    lead = text[:len(text) - len(text.lstrip("\n"))]
    trail = text[len(text.rstrip("\n")):]
    return lead + _zusammen(L).strip("\n") + trail, aend


def _teile(zeilen):
    """[(titel_index, titel, (b0, b1) | None, (e0, e1) | None)] je Untersuchung (Zeilenbereiche ohne Überschrift)."""
    out, akt = [], None
    for i, z in enumerate(zeilen):
        s = z.strip()
        if not s.startswith("## "):
            continue
        k = s[3:].strip().lower().rstrip(":")
        if k in ("befund", "ergebnis"):
            if akt is None:
                akt = [-1, "", None, None]
                out.append(akt)
            j = i + 1
            while j < len(zeilen) and not zeilen[j].lstrip().startswith("## "):
                j += 1
            akt[2 if k == "befund" else 3] = (i + 1, j)
        else:
            akt = [i, s[3:].strip(), None, None]
            out.append(akt)
    return out


def _erg_zeilen(zeilen, e):
    return [i for i in range(e[0], e[1]) if zeilen[i].strip()]


def _punkt(z):
    return _NUM_RE.sub("", z).strip()


def georg_2311(report, diktat="", templates=None):
    """→ (report, Änderungen). Siehe Kopf dieses Abschnitts."""
    if not report or "## " not in report:
        return report, []
    out = report
    aend = []
    for rx, f in _WORT_ERSETZEN:
        neu = rx.sub(f, out)
        if neu != out:
            aend.append("Wortlaut periprothetisch/Material")
            out = neu
    dk = (diktat or "").lower()
    zeilen = out.split("\n")
    erg_neu = False
    teile = _teile(zeilen)
    becken_da = any(_BECKEN_TITEL.search(t) and not _SCHNITT_TITEL.search(t) for _i, t, _b, _e in teile)
    # Befund je Teil (rückwärts, Zeilenzahl ändert sich)
    for ti, titel, b, e in reversed(teile):
        if b is None:
            continue
        text = "\n".join(zeilen[b[0]:b[1]])
        neu, x = _befund_ops(text, titel, dk, templates)
        if x:
            zeilen[b[0]:b[1]] = neu.split("\n")
            aend += x
    # 58b: HIPPO-Sätze nie im Wirbelsäulen-Teil (gehören in die Beckenübersicht)
    teile = _teile(zeilen)
    if becken_da:
        wandern = []
        for ti, titel, b, e in teile:
            if not _WS_TITEL.search(titel):
                continue
            for rng in (b, e):
                if rng is None:
                    continue
                for i in range(rng[0], rng[1]):
                    t = _punkt(zeilen[i])
                    if _HIPPO_SATZ.match(t):
                        wandern.append(satzform(t))
                        zeilen[i] = "\x00"
        if wandern:
            zeilen = [z for z in zeilen if z != "\x00"]
            teile = _teile(zeilen)
            ziel = next((t for t in teile if _BECKEN_TITEL.search(t[1]) and not _SCHNITT_TITEL.search(t[1]) and t[2]), None)
            if ziel is not None:
                b0, b1 = ziel[2]
                schon = "\n".join(zeilen[b0:b1])
                rein = [w for w in dict.fromkeys(wandern) if w not in schon]
                k = next((i for i in range(b0, b1) if zeilen[i].strip()), None)
                if rein and k is not None:
                    zeilen[k] = " ".join(rein) + " " + zeilen[k].lstrip()
                aend.append(f"HIPPO-Sätze aus dem Wirbelsäulen-Teil in die Beckenübersicht ({len(wandern)})")
            erg_neu = True
            teile = _teile(zeilen)
    # Ergebnis je Teil
    for ti, titel, b, e in reversed(teile):
        if e is None:
            continue
        idx = _erg_zeilen(zeilen, e)
        bef = "\n".join(zeilen[b[0]:b[1]]) if b else ""
        punkte = [zeilen[i] for i in idx]
        alt = list(punkte)
        schnitt = bool(_SCHNITT_TITEL.search(titel))
        # 58b/60b: Beckenschiefstand ≥ 10 mm ins Ergebnis
        if _BECKEN_TITEL.search(titel) and not schnitt:
            m = next((m for m in _BS_GROSS.finditer(bef) if int(m.group(1)) >= 10), None)
            if m and not any("beckenschiefstand" in p.lower() for p in punkte):
                satz = f"Beckenschiefstand von {m.group(1)} mm" + (f", {m.group(2)} tiefer." if m.group(2) else ".")
                punkte = [p for p in punkte if not (_WID_NORMAL_ERG.search(p) and not has_pathology(p))]
                punkte.insert(0, satz)
                aend.append(f"HIPPO ≥ 10 mm ins Ergebnis: {satz}")
        # 69/70: K&L je Diagnose
        if not schnitt and not _WS_TITEL.search(titel):
            punkte, x = _kl_ergebnis(punkte, dk)
            aend += x
        # 48c Schulter: Omarthrose → AC → Enthesiopathie
        if _SCHULTER_TITEL.search(titel) and not schnitt:
            def rang(p):
                t = p.lower()
                return 0 if re.search(r"omarthros|glenohumeral", t) else 1 if _AC_RX.search(t) else 2 if "enthesiopath" in t else None
            slots = [k for k, p in enumerate(punkte) if rang(p) is not None]
            sortiert = sorted((punkte[k] for k in slots), key=rang)
            for k, p in zip(slots, sortiert):
                punkte[k] = p
        # 53b Nerv unauffällig
        if _NERV_TITEL.search(titel):
            mn = _NERV_NAME.search(titel) or _NERV_NAME.search(bef)
            if mn:
                name = mn.group(1).lower()
                nerv_patho = any(_bejaht(x.lower(), _NERV_PATHO) and (name in x.lower() or "nerv" in x.lower())
                                 for x in [(diktat or "")[a:c] for a, c in diktat_saetze(diktat or "")]
                                 + [bef[a:c] for a, c in saetze_mit_lage(bef)])
                if not nerv_patho and not any(name in p.lower() and "unauffällig" in p.lower() for p in punkte):
                    sd = wid_seite(titel) or (diktierte_seite(dk) if diktierte_seite(dk) in ("rechts", "links") else "")
                    satz = NERV_UNAUFFAELLIG.format(name=name, seite=(" " + sd) if sd else "")
                    punkte = [p for p in punkte if _punkt(p).rstrip(".").lower() not in ("unauffälliger befund",
                                                                                          "regelrechte darstellung")]
                    punkte.insert(0, satz)
                    aend.append(f"Nerv unauffällig: {satz}")
        # 65 Verlauf zuerst
        v = [k for k, p in enumerate(punkte) if _VERLAUF.search(_punkt(p)) and not _UNNUM_RE.match(_punkt(p))]
        if v and v[0] != 0:
            p = punkte.pop(v[0])
            punkte.insert(0, p)
            aend.append(f"Verlauf als 1. Punkt: {_punkt(p)[:50]}")
        if punkte != alt:
            erg_neu = True
            if idx:
                zeilen[idx[0]:idx[-1] + 1] = punkte
            else:
                zeilen[e[0]:e[0]] = punkte
    # 69: Befund-Deskriptor je Seite (nach dem Ergebnis, eigene Schleife)
    teile = _teile(zeilen)
    for ti, titel, b, e in reversed(teile):
        if not dk or b is None or e is None or _SCHNITT_TITEL.search(titel) or _WS_TITEL.search(titel):
            continue
        neu, x = _kl_befund("\n".join(zeilen[b[0]:b[1]]), [zeilen[i] for i in _erg_zeilen(zeilen, e)], titel)
        if x:
            zeilen[b[0]:b[1]] = neu.split("\n")
            aend += x
    # 56 Dunn
    if ZUSATZPROJEKTIONEN["dunn"]["aktiv"] and re.search(ZUSATZPROJEKTIONEN["dunn"]["diktat"], dk):
        for ti, titel, b, e in _teile(zeilen):
            if ti >= 0 and re.search(ZUSATZPROJEKTIONEN["dunn"]["region"], titel, re.I) and "dunn" not in titel.lower():
                bds = re.search(r"dunn[^.]{0,40}(?:beidseit|bds)|(?:beidseit|bds)[^.]{0,40}dunn", dk)
                zeilen[ti] = zeilen[ti].rstrip() + (DUNN_TITEL_BDS if bds else DUNN_TITEL)
                aend.append("Titel mit Dunn-Aufnahme")
    out = "\n".join(zeilen)
    if erg_neu:
        out = ergebnis_nummerieren(out)
    return out, aend


def _kl_ergebnis(punkte, dk):
    """69: „A links und B rechts“ → zwei Punkte; fehlt die K&L-Klammer einer DIKTIERTEN Arthrose mit Grad-Adjektiv, kommt
    sie dazu (diktierter Grad vor dem Adjektiv derselben Diagnose). Den falschen Grad korrigiert kl_bereinigen (70)."""
    if not dk or not arthrose_diktiert(dk):
        return punkte, []
    aend, out = [], []
    diktiert = kl_grade(dk)
    adj = set(kl_adjektiv_grade(dk))      # „… Coxarthrose links und geringgradige rechts“: Adjektiv + Seite zählt mit
    adj |= {g for m in _KL_ADJ_SEITE.finditer(dk) for g, r in _KL_ADJ if re.fullmatch(r, m.group(1), re.I)}
    for p in punkte:
        t = _punkt(p)
        md = _KL_DOPPEL.match(t)
        if md and _kl_grad_zeile(t):
            adj1, diag, s1, adj2, s2 = md.groups()
            if s1 != s2:
                a = f"{adj1}{diag} {s1}."
                b2 = f"{adj2[:1].upper()}{adj2[1:]} {diag} {s2}."
                out += [a, b2]
                aend.append(f"Arthrose je Seite: {a} / {b2}")
                continue
        out.append(p)
    fertig = []
    for p in out:
        t = _punkt(p)
        if _KL_AUSNAHME.search(t) or not _ARTHROSE_KI.search(t) or _VERNEINT.search(t.split("rthros")[0]) \
                or _KL_KI.search(t) or re.search(r"kellgren", t, re.I):
            fertig.append(p)
            continue
        g = diktiert[0] if len(diktiert) == 1 else (_kl_grad_zeile(t) if not diktiert else None)
        if g and (diktiert or g in adj):
            kern = p.rstrip()
            kern = kern[:-1] if kern.endswith(".") else kern
            p = f"{kern} {kl_klammer(g)}."
            aend.append(f"K&L-Klammer ergänzt (Grad {g})")
        fertig.append(p)
    return fertig, aend


# eigener Arthrose-Deskriptor der KI („Verschmälerung des medialen Gelenkspaltes mit Osteophyten …“) → Standardsatz statt
_KL_KOMP = re.compile(r"(?<![a-zäöüß])(medial|lateral|femoropatellar|femorotibial|retropatellar|patellofemoral)")
_KL_EIGEN = re.compile(r"osteophyt|gelenks?spalt\w*verschmäler|verschmälerung des [a-zäöüß]+ gelenks?spalt|subchondral")


def _kl_befund(text, punkte, titel):
    """69: je Ergebnis-Diagnose mit K&L-Grad der Standardsatz im Befund (Seite davor, wenn der Teil nicht genau diese eine
    Seite hat): an die Stelle des Diagnose-Satzes („Hochgradige Coxarthrose links …“), sonst hinter den Satz derselben
    Seite mit „degenerativ“, sonst hinter den ersten Satz."""
    je = []
    for p in punkte:
        t = _punkt(p)
        m = _KL_KI.search(t)
        if not m or _KL_AUSNAHME.search(t):
            continue
        g = int(_KL_WERT.get((m.group(1) or m.group(2) or "").lower(), "0") or 0)
        if g in KL_TABELLE and g:
            je.append((wid_seite(t), g))
    if not je:
        return text, []
    L = _zerlegen(text)
    fehlt = [(sd, g) for sd, g in dict.fromkeys(je)
             if not any(KL_TABELLE[g][:-1].lower() in x.lower() for x in _saetze_von(L))]
    if not fehlt:
        return text, []
    mehr = len({sd for sd, _g in je}) > 1
    ts = wid_seite(titel)
    aend = []
    for sd, g in fehlt:
        satz = KL_TABELLE[g]
        s = _saetze_von(L)
        passt = lambda x: not sd or wid_seite(x) in (sd, "")
        diag = [i for i, x in enumerate(s) if (_bejaht(x.lower(), _ARTHROSE_KI) or _bejaht(x.lower(), _KL_EIGEN))
                and not _KL_TAB_RE.search(x) and not _KL_AUSNAHME.search(x) and passt(x)
                and (not mehr or wid_seite(x) == sd or not wid_seite(x))]
        vor = [sd] if (sd and (mehr or ts != sd)) else []
        mk = _KL_KOMP.search(s[diag[0]].lower()) if diag else None    # Kompartiment bleibt („Medial …“, kl-knie-betont)
        vor += [mk.group(1)] if mk else []
        neu = (" ".join(vor)[:1].upper() + " ".join(vor)[1:] + " " + satz[:1].lower() + satz[1:]) if vor else satz
        if diag:
            L = _umstellen(L, diag[:1], diag[0] - 1, [neu])
        else:
            deg = next((i for i, x in enumerate(s) if "degenerativ" in x.lower() and sd and wid_seite(x) == sd), None)
            if deg is None:   # sonst hinter den Gelenk-Satz („Gelenkflächen …/Gelenkspalt …“), sonst hinter den ersten Satz
                deg = next((i for i, x in enumerate(s) if re.search(r"gelenkfl|gelenks?spalt", x.lower())), None)
            L = _umstellen(L, [], deg if deg is not None else (0 if s else -1), [neu])
        aend.append(f"K&L-Standardsatz im Befund: {neu[:50]}")
    lead = text[:len(text) - len(text.lstrip("\n"))]
    trail = text[len(text.rstrip("\n")):]
    return lead + _zusammen(L).strip("\n") + trail, aend


def teile_zusammenlegen(report, diktat=""):
    """58a: zwei Untersuchungsteile mit derselben Überschrift → EIN Teil (Befundsätze/Ergebnispunkte ohne Doppel).
    64: ein „Unterarm“-Teil neben Handgelenk/Ellbogen, obwohl „Unterarm“ nicht diktiert ist → fällt weg.
    → (report, Änderungen). Sync: befundRegeln.ts teileZusammenlegen."""
    if not report or report.count("## ") < 4:
        return report, []
    bloecke = [b for b in re.split(r"\n{2,}(?=## (?!Befund\b|Ergebnis\b))", report.strip()) if b.strip()]
    if len(bloecke) < 2:
        return report, []
    def kopf(b):
        z = b.strip().split("\n", 1)[0].strip()
        return z[3:].strip().lower() if z.startswith("## ") and z[3:].strip().lower().rstrip(":") not in ("befund", "ergebnis") else ""
    aend, out, gesehen = [], [], {}
    titel_alle = [kopf(b) for b in bloecke]
    for b in bloecke:
        k = kopf(b)
        if k and "unterarm" in k and "unterarm" not in (diktat or "").lower() and diktat \
                and any(re.search(r"handgelenk|ellbogen", t) for t in titel_alle if t != k):
            aend.append("Teil „Unterarm“ ohne diktierten Unterarm entfernt")
            continue
        if k and k in gesehen:
            ziel = gesehen[k]
            out[ziel] = _bloecke_vereinen(out[ziel], b)
            aend.append(f"doppelter Teil zusammengelegt: {k[:40]}")
            continue
        if k:
            gesehen[k] = len(out)
        out.append(b)
    if not aend:
        return report, []
    return ergebnis_nummerieren("\n\n\n".join(x.strip() for x in out)), aend


def _abschnitte_von(b):
    teile = {"befund": [], "ergebnis": []}
    akt = None
    for z in b.split("\n"):
        s = z.strip()
        k = s[3:].strip().lower().rstrip(":") if s.startswith("## ") else None
        if k in teile:
            akt = k
            continue
        if akt and s:
            teile[akt].append(s)
    return teile


def _bloecke_vereinen(a, b):
    ta, tb = _abschnitte_von(a), _abschnitte_von(b)
    alt_text = " ".join(ta["befund"])
    dazu = []
    for z in tb["befund"]:
        for x0, x1 in saetze_mit_lage(z):
            x = z[x0:x1].strip()
            if x and x not in alt_text and vorlage_normalisieren(x) not in vorlage_normalisieren(alt_text):
                dazu.append(x)
    erg_alt = [_punkt(z) for z in ta["ergebnis"]]
    erg_dazu = [_punkt(z) for z in tb["ergebnis"] if _punkt(z) not in erg_alt
                and not (_WID_NORMAL_ERG.search(_punkt(z)) and any(not _WID_NORMAL_ERG.search(e) for e in erg_alt))]
    if any(not _WID_NORMAL_ERG.search(e) for e in erg_dazu):
        erg_alt = [e for e in erg_alt if not (_WID_NORMAL_ERG.search(e) and not has_pathology(e))]
    kopf = a.strip().split("\n", 1)[0]
    bef = " ".join(ta["befund"] + dazu) if len(ta["befund"]) <= 1 else "\n".join(ta["befund"] + ([" ".join(dazu)] if dazu else []))
    return f"{kopf}\n\n## Befund\n{bef}\n\n## Ergebnis\n" + "\n".join(erg_alt + erg_dazu)


def pruefzeilen_2311(report, diktat="", templates=None):
    """60/60b: sichtbare Prüfzeilen (nur Anzeige) – Teil mit leerem Ergebnis, „Regelrechte Darstellung“ trotz Pathologie
    im Befund (Befund nicht geformt). Sync: befundRegeln.ts pruefzeilen2311."""
    out = []
    zeilen = (report or "").split("\n")
    for ti, titel, b, e in _teile(zeilen):
        name = titel or "Befund"
        if e is not None and not _erg_zeilen(zeilen, e):
            out.append(f"{name}: Ergebnis leer – bitte prüfen")
            continue
        if b is None or e is None:
            continue
        punkte = [_punkt(zeilen[i]) for i in _erg_zeilen(zeilen, e)]
        nur_normal = punkte and all(_WID_NORMAL_ERG.search(p) and not has_pathology(p) for p in punkte if not _UNNUM_RE.match(p))
        bef = " ".join(zeilen[b[0]:b[1]])
        vorlagen = _vorlagen_saetze(templates)[0] if templates else set()
        patho = [bef[x:y] for x, y in saetze_mit_lage(bef) if _patho_satz(bef[x:y]) and not _HIPPO_SATZ.match(bef[x:y])
                 and not _BS_GROSS.search(bef[x:y]) and not UEBRIGEN_ANFANG.match(bef[x:y])
                 and OSTEOPEN_SATZ not in bef[x:y] and vorlage_normalisieren(bef[x:y]) not in vorlagen
                 and not re.match(r"^(?:normale?|regelrechte?|unauffällige?)\b", bef[x:y], re.I)]
        if nur_normal and patho:
            out.append(f"{name}: Befund nicht geformt – „Regelrechte Darstellung“ trotz Pathologie, bitte prüfen")
    return out


# 49a/52 (Georg 22./23.11.2026, Foto Sono Weichteile mit „Nur Text“ AN: „Die Überschriften immer fett“): im Nur-Text-Weg
# werden Überschriften-Zeilen zu „## …“ (Anzeige fett, Zwischenablage/HTML <h2>, Brief wie jede Untersuchung):
# „Ergebnis:“/„Befund:“ (auch „Ergebnis: Text …“ → Überschrift + Text darunter) und kurze Untersuchungstitel, die mit
# Doppelpunkt enden („Sonographie Weichteile:“). Sonst bleibt der Text Zeichen für Zeichen. Sync: befundRegeln.ts.
_NT_KOPF = re.compile(r"^\s*(?:\*\*)?\s*(Befund|Ergebnis|Beurteilung)\s*:?\s*(?:\*\*)?\s*$", re.I)
_NT_KOPF_TEXT = re.compile(r"^\s*(?:\*\*)?\s*(Ergebnis|Beurteilung)\s*:\s*(?:\*\*)?\s*(\S.*)$", re.I)
_NT_TITEL = re.compile(r"^\s*(?:\*\*)?\s*([A-ZÄÖÜ][^.:;!?\n]{2,80}?)\s*:\s*(?:\*\*)?\s*$")
_NT_UNTERSUCHUNG = re.compile(r"röntgen|sonogra|ultraschall|(?<![a-zäöüß])(?:mr|mrt|ct)(?![a-zäöüß])|aufnahme|übersicht|"
                              r"ebenen|ganzbein|mammogra|weichteil|gelenk|wirbelsäule|thorax|abdomen|schulter|hüft|knie|"
                              r"becken|hand|fuß|fuss|ellbogen|sprung|unterarm|unterschenkel|oberarm|oberschenkel|nerv|"
                              r"(?<![a-zäöüß])(?:hws|bws|lws|gws|n\.)(?![a-zäöüß])", re.I)


def nur_text_ueberschriften(text):
    if not text or "## " in text:
        return text
    aus, geaendert = [], False
    for z in text.split("\n"):
        m = _NT_KOPF.match(z)
        mt = _NT_KOPF_TEXT.match(z)
        mu = _NT_TITEL.match(z)
        if m:
            aus.append("## " + m.group(1)[:1].upper() + m.group(1)[1:].lower())
        elif mt:
            aus += ["## " + mt.group(1)[:1].upper() + mt.group(1)[1:].lower(), mt.group(2)]
        elif mu and len(mu.group(1).split()) <= 8 and _NT_UNTERSUCHUNG.search(mu.group(1)):
            aus.append("## " + mu.group(1).strip())
        else:
            aus.append(z)
            continue
        geaendert = True
    return "\n".join(aus) if geaendert else text


# ══ kaiscribe-ursula-2011-text-n1 (Ursula Hofmeister, Durchsicht der KaiScribe-Briefe vom 20.11.2026) ══════════════
# Sync: befundRegeln.ts (gleiche Regexe), Fixtures „ursula_2011“. Ohne Treffer bleibt der Text Zeichen für Zeichen gleich.
#  4b  Zahl + „-prozentig“ → „%ig“ („50-prozentiger“ → „50%iger“, auch „50 %-ige“, „50prozentige“)
#  4c  Wirbelsäule bekommt nie eine Seite in der Überschrift („HWS beidseits in 2 Ebenen“ → „HWS in 2 Ebenen“) – nicht bei
#      Titeln, die auch eine paarige Region nennen („LWS sowie Hüftgelenk links“)
#  4a  „Im Übrigen …“ nicht mehrfach hintereinander: folgt ein „Im Übrigen“-Satz einem anderen ohne neue Pathologie
#      dazwischen, verliert er das „Im Übrigen“ (Vorlagensatz zurück); nach einer neuen Pathologie bleibt es (Kortikalis-
#      Satz hinter der Fraktur, georg-fraktur-kortikalis)
#  3/7 Schreibweisen: „trochanter(e)“ als Adjektiv → „trochantär(e)“ (auch per-/inter-/sub-/peri-), „Trochanter major“ und
#      „Bursitis trochanterica“ bleiben; „Verklakung“ → „Verkalkung“
#  10  Brustwirbel „Th“ + Zahl (Peter 23.11.2026): „TH12“/„Th 12“ → „Th12“
#  1   (nachbearbeiten) Ergebnistext nie als Überschrift: „## Osteochondrose L4/5.“ im Ergebnis → Text; „## Ergebnis: Text“
#      → „## Ergebnis“ + Text
#  8/5 (befund_schluss, ganz am Ende der Kette): keine Leerzeile zwischen „## Ergebnis“ und dem Ergebnistext; Teile ohne
#      jeden Inhalt (nur Überschrift) fallen weg; ein loses Regions-Wort als letzte Zeile eines Teils („Becken“) fällt weg
_PROZENTIG = re.compile(r"(?<![\d,])(\d+(?:,\d+)?)[ \t]?-?[ \t]?(?:[Pp]rozent|%)[ \t]?-?[ \t]?ig(e[nrsm]?)?(?![a-zäöüß])")
_WS_SEITE = re.compile(r"[ \t]*(?<![A-Za-z0-9_ÄÖÜäöüß-])(?:beidseits|beidseitig|bds\.|bds|rechts|links|re\.|li\.)"
                       r"(?![A-Za-z0-9_ÄÖÜäöüß-])", re.I)
_WS_PAARIG = re.compile(r"hüft|becken|knie|schulter|sprung|fu(?:ß|ss)|hand|finger|zehe|ellbogen|iliosakral|rippe|clavicula|"
                        r"klavikula|(?<![a-zäöüß])(?:isg|sig)(?![a-zäöüß])", re.I)
_IM_UEBRIGEN = re.compile(r"^Im [Üü]brigen,?\s+")
_LABEL_UEBRIGEN = re.compile(r"^([A-ZÄÖÜ][^:.]{0,48}):\s+im [Üü]brigen\s+")
_TROCHANTER = re.compile(r"(?<![A-Za-zÄÖÜäöüß])((?:[Pp]er|[Ii]nter|[Ss]ub|[Pp]eri)?)([Tt])rochanter(e[nrsm]?)?(?![A-Za-zäöüß])")
_VERKLAKUNG = re.compile(r"(?<![A-Za-zÄÖÜäöüß])([Vv])erklak(ung(?:en)?|t(?:e[nrsm]?)?)(?![a-zäöüß])")
_TH_WIRBEL = re.compile(r"(?<![A-Za-zÄÖÜäöüß])T[Hh][ \t]?(1[0-2]|[1-9])(?!\d)")


def _trochantaer(m):
    vor, t, endung = m.group(1), m.group(2), m.group(3) or ""
    if not vor and t == "T" and not endung:
        return m.group(0)                # „Trochanter major“ (Nomen) bleibt
    return vor + t + "rochantär" + endung


def _uebrigen_folge(L, templates):
    """4a: „Im Übrigen …“ nur einmal je Folge (ohne neue Pathologie dazwischen)."""
    s, pos, aend = _saetze_von(L), _flach(L), []
    davor = False
    for j, x in enumerate(s):
        m, ml = _IM_UEBRIGEN.match(x), _LABEL_UEBRIGEN.match(x)
        if m or ml:
            if davor:
                if m:
                    rest = x[m.end():]
                    neu = _vorlage_zurueck(rest, templates) if _WID_VERB.match(rest.split(" ", 1)[0].lower()) \
                        else (_vorlage_zurueck(rest, templates) or rest[:1].upper() + rest[1:])
                else:
                    kurz = ml.group(1) + ": " + x[ml.end():]
                    neu = _vorlage_zurueck(kurz, templates) or kurz
                if neu:
                    aend.append(f"„Im Übrigen“ nicht doppelt: {neu[:50]}")
                    L[pos[j][0]][pos[j][1]] = neu
                    s[j] = neu
            davor = True
        elif _patho_satz(x):
            davor = False
    return L, aend


def ursula_2011(report, templates=None):
    """→ (report, Änderungen). Siehe Kopf dieses Abschnitts (4a/4b/4c/3/7/10)."""
    if not report:
        return report, []
    aend = []
    zeilen = report.split("\n")
    for i, z in enumerate(zeilen):
        s = z.strip()
        if s.startswith("## ") and s[3:].strip().lower().rstrip(":") not in ("befund", "ergebnis") \
                and _WS_TITEL.search(s) and not _WS_PAARIG.search(s) and _WS_SEITE.search(s[3:]):
            neu = "## " + " ".join(_WS_SEITE.sub(" ", s[3:]).split())
            if neu != s:
                zeilen[i] = neu
                aend.append(f"Wirbelsäule ohne Seite: {neu[3:]}")
    for a, e in reversed(_abschnitt(zeilen, "befund")):
        text = "\n".join(zeilen[a:e])
        L = _zerlegen(text)
        if not _flach(L):
            continue
        L, x = _uebrigen_folge(L, templates)
        if x:
            aend += x
            lead = text[:len(text) - len(text.lstrip("\n"))]
            trail = text[len(text.rstrip("\n")):]
            zeilen[a:e] = (lead + _zusammen(L).strip("\n") + trail).split("\n")
    out = "\n".join(zeilen)
    for name, rx, ers in (("Prozent", _PROZENTIG, lambda m: m.group(1) + "%ig" + (m.group(2) or "")),
                          ("trochantär", _TROCHANTER, _trochantaer),
                          ("Verkalkung", _VERKLAKUNG, lambda m: m.group(1) + "erkalk" + m.group(2)),
                          ("Th + Zahl", _TH_WIRBEL, lambda m: "Th" + m.group(1))):
        neu = rx.sub(ers, out)
        if neu != out:
            aend.append(f"Schreibweise {name}")
            out = neu
    return out, aend


def ergebnis_text_sichern(report):
    """1 (RH 31/119): Ergebnistext nie als Überschrift – „## <Satz>.“ bzw. „## 1. …“ im Ergebnis → Text; „## Ergebnis: Text“
    → „## Ergebnis“ + Text. Eine Zeile, auf die „## Befund“/„## Ergebnis“ folgt, ist ein Untersuchungstitel und bleibt."""
    if not report or "## " not in report:
        return report
    out, im_erg = [], False
    zeilen = report.split("\n")

    def naechster_kopf(i):
        for z2 in zeilen[i + 1:]:
            if z2.strip().startswith("## "):
                return z2.strip()[3:].strip().lower().rstrip(":")
        return None

    for i, z in enumerate(zeilen):
        s = z.strip()
        if not s.startswith("## "):
            out.append(z)
            continue
        k = s[3:].strip()
        m = re.match(r"^ergebnis\s*:\s*(\S.*)$", k, re.I)
        if m:
            out += ["## Ergebnis", m.group(1)]
            im_erg = True
            continue
        kl = k.lower().rstrip(":")
        if kl == "ergebnis":
            im_erg = True
        elif kl == "befund":
            im_erg = False
        elif im_erg and (k.endswith((".", "!", "?")) or re.match(r"^\d+[.)]\s", k)) \
                and naechster_kopf(i) not in ("befund", "ergebnis"):     # „## Hüftgelenke bds. ap/ax.“ + Befund = Titel
            out.append(k)
            continue
        else:
            im_erg = False
        out.append(z)
    return "\n".join(out)


_LOSE_REGION = re.compile(r"(?:" + _MOD + r"(?:(?:der|die|das|des)\s+)?(?:" + _REGION_ALT + "|" +
                          "|".join(pat for _, pat in REGIONEN_OHNE_SEITE) + r")(?:\s+in\s+(?:2|zwei)\s+ebenen)?(?:\s+" +
                          _SEITE + r")?)\s*[.:]?", re.I)


def befund_schluss(report):
    """8/5 (RH 37, RH 47, RH 120): ganz am Ende der Befundkette (nach IB Lab, Rho). → (report, Änderungen)."""
    if not report or "## " not in report:
        return report, []
    zeilen, aend = report.split("\n"), []
    i = 0
    while i < len(zeilen):                       # 8: keine Leerzeile zwischen „## Ergebnis“ und dem Text
        if zeilen[i].strip().lower().rstrip(":") == "## ergebnis":
            j = i + 1
            while j < len(zeilen) and not zeilen[j].strip():
                j += 1
            if j > i + 1 and j < len(zeilen) and not zeilen[j].lstrip().startswith("## "):
                del zeilen[i + 1:j]
                aend.append("Leerzeile nach „Ergebnis“ weg")
        i += 1
    kopf = lambda z: z.strip().startswith("## ") and z.strip()[3:].strip().lower().rstrip(":") not in ("befund", "ergebnis")  # noqa: E731
    titel = [i for i, z in enumerate(zeilen) if kopf(z)]
    teile = [(t, titel[k + 1] if k + 1 < len(titel) else len(zeilen)) for k, t in enumerate(titel)]
    inhalt = lambda a, b: [j for j in range(a, b) if zeilen[j].strip() and not zeilen[j].strip().startswith("## ")]  # noqa: E731
    weg = set()
    for a, b in teile:                           # 5: loses Regions-Wort als letzte Zeile eines Teils
        c = inhalt(a + 1, b)
        if c and _LOSE_REGION.fullmatch(zeilen[c[-1]].strip()):
            aend.append(f"loses Wort weg: {zeilen[c[-1]].strip()[:30]}")
            weg.add(c[-1])
    voll = [(a, b) for a, b in teile if [j for j in inhalt(a + 1, b) if j not in weg]]
    if voll:
        for a, b in teile:                       # 5: Teil ohne Inhalt (nur Überschrift) weg
            if (a, b) not in voll:
                aend.append(f"Überschrift ohne Inhalt weg: {zeilen[a].strip()[3:][:40]}")
                weg.update(range(a, b))
    if not weg:
        return ("\n".join(zeilen), aend)
    neu = [z for j, z in enumerate(zeilen) if j not in weg]
    while neu and not neu[-1].strip():
        neu.pop()
    return "\n".join(neu), aend
