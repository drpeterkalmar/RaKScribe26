"""Ordinations-Textbausteine (v3.3.0, Peter 06.10.2026): „Baustein Mammo 1“, „Baustein Ösophagus 2“ …

Quelle: ordi_bausteine.json (aus dem RIS-Ordner Standardbefunde/Textbausteine Ordi/Blockrtf, Grußformeln entfernt).
EINE Datei für EXE (gebündelt) und Web (importiert); Sync: web_app/src/bausteine.ts, gemeinsame Fälle in
ordi_bausteine_tests.json (Repo-Root), Gate tests/offline/test_ordi_bausteine.py.

- art "satz" (z. B. DEXA „Baustein A1“, „Baustein Fraktur“): Satz wird an der Stelle ins Diktat eingesetzt.
- art "befund"/"struktur": der Baustein ersetzt die Vorlage.
    * nur Baustein (+ Seite / „unauffällig“) diktiert → Befund WÖRTLICH aus dem Baustein, ohne KI.
    * mit Zusatz → KI bekommt den Baustein als verbindliche Vorlage und ändert nur das Diktierte.
"""
import json
import os
import re
import sys

_ZAHL = {"1": "eins|ein|eine", "2": "zwei|zwo", "3": "drei", "4": "vier", "5": "fünf|fuenf"}
_UML = (("ae", "(?:ä|ae)"), ("oe", "(?:ö|oe)"), ("ue", "(?:ü|ue)"), ("ss", "(?:ß|ss)"))
_W = "a-zäöüß0-9"
# Wörter, die bei „nur Baustein diktiert“ übrig bleiben dürfen
_FUELL = set("""unauffaellig unauffällig normal normalbefund regelrecht ok o b ob punkt komma ende danke bitte und
rechts links beidseits bds re li seite rechtsseitig linksseitig beidseitig""".split())


def _datei(name):
    for d in (getattr(sys, "_MEIPASS", None), os.path.dirname(os.path.abspath(__file__)),
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")):
        if d and os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    return None


def laden(pfad=None):
    pfad = pfad or _datei("ordi_bausteine.json")
    if not pfad:
        return {}
    with open(pfad, encoding="utf-8") as f:
        return json.load(f).get("bausteine", {})


def _token_re(t):
    if t.isdigit():
        return "(?:" + t + ("|" + _ZAHL[t] if t in _ZAHL else "") + ")"
    s = t
    for a, b in _UML:
        s = s.replace(a, b)
    return s


def _alias_re(alias):
    toks = alias.split()
    return "[\\s\\-_.+/]*".join(_token_re(t) for t in toks)


_CACHE = {}


def _muster(bausteine):
    """Liste (key, regex) — längster Alias zuerst (Mammo 1 a vor Mammo 1)."""
    k = id(bausteine)
    if k not in _CACHE:
        # längster Alias zuerst (ohne Leerzeichen gezählt); bei Gleichstand der zusammengeschriebene (thosw vor th-osw)
        paare = [(len(a.replace(" ", "")), len(a.split()), key, a) for key, b in bausteine.items() for a in b.get("sprich", [])]
        paare.sort(key=lambda x: (-x[0], x[1], x[2]))
        _CACHE[k] = [(key, re.compile("(^|[^" + _W + "])baustein[\\s:,.\\-]*(" + _alias_re(a) + ")(?![" + _W + "])",
                                      re.I)) for _, _, key, a in paare]
    return _CACHE[k]


def finden(text, bausteine):
    """Alle Baustein-Treffer: [(start, ende, key)] ohne Überlappung, im Text von vorne nach hinten.
    start zeigt auf „baustein“ (Trennzeichen davor gehört nicht dazu)."""
    treffer = []
    for key, rx in _muster(bausteine):
        for m in rx.finditer(text or ""):
            s, e = m.start() + len(m.group(1)), m.end()
            if not any(s < te and ts < e for ts, te, _ in treffer):
                treffer.append((s, e, key))
    return sorted(treffer)


def saetze_einsetzen(text, bausteine):
    """art 'satz': „… Baustein Fraktur …“ → Satz aus dem Baustein an derselben Stelle."""
    for s, e, key in reversed(finden(text, bausteine)):
        b = bausteine[key]
        if b.get("art") == "satz":
            text = text[:s] + b.get("text", "") + text[e:]
    return text


def befund_baustein(seg, bausteine):
    """Erster Befund-Baustein im Segment → (key, rest_ohne_baustein) oder (None, seg)."""
    for s, e, key in finden(seg, bausteine):
        if bausteine[key].get("art") != "satz":
            return key, (seg[:s] + " " + seg[e:]).strip(" ,.;:-\n")
    return None, seg


def nur_baustein(rest):
    """True, wenn nach dem Baustein nichts Inhaltliches diktiert wurde."""
    worte = re.findall("[" + _W + "]+", (rest or "").lower())
    return all(w in _FUELL for w in worte)


def _seite(text):
    t = (text or "").lower()
    if re.search(r"(?<![a-zäöü])(beidseits|beidseitig|bds)(?![a-zäöü])", t):
        return "beidseits"
    r = re.search(r"(?<![a-zäöü])(rechts|rechtsseitig)(?![a-zäöü])", t)
    l = re.search(r"(?<![a-zäöü])(links|linksseitig)(?![a-zäöü])", t)
    if r and not l:
        return "rechts"
    if l and not r:
        return "links"
    return None


def _seite_tauschen(txt, nach):
    """Baustein für rechts, Diktat sagt links (oder umgekehrt) → Seitenwörter tauschen."""
    von = "links" if nach == "rechts" else "rechts"
    return re.sub(r"(?<![a-zäöü])" + von + r"(?![a-zäöü])", nach, txt)


# Untersuchungen ohne Seite — „Pleuraerguss rechts“ im Zusatz macht keinen „Thorax rechts“
UNPAARIG = (r"thorax|abdomen|oberbauch|nieren|becken|sch[äa]del|hws|bws|lws|wirbels[äa]ule|halsgef|schilddr|"
            r"oesophag|ösophag|magen|darm|schluck|nnh|nebenh[öo]hle|fernr[öo]ntgen|zahn|lymph|urograph|harntrakt|hyster")


def vorlage(key, bausteine, diktat=""):
    """Baustein als Vorlage {titel, body, display_name, ergebnis} — Seite aus dem Diktat übernommen."""
    b = bausteine[key]
    titel, befund, ergebnis = b.get("titel", ""), b.get("befund", ""), b.get("ergebnis", "")
    seite = _seite(diktat)
    eigen = _seite(titel)
    if seite in ("rechts", "links") and eigen in ("rechts", "links") and seite != eigen:
        titel, befund, ergebnis = (_seite_tauschen(x, seite) for x in (titel, befund, ergebnis))
    elif seite and not eigen and not re.search(r"(?<![a-zäöü])(beidseits|bds\.?)(?![a-zäöü])", titel, re.I) \
            and not re.search(UNPAARIG, titel, re.I):
        m = re.search(r"\s+in\s+(?:\d|zwei|einer|drei)\b", titel, re.I)
        titel = titel[:m.start()] + " " + seite + titel[m.start():] if m else titel + " " + seite
    return {"titel": titel, "body": titel + "\n" + befund, "display_name": titel,
            "ergebnis": ergebnis or "Unauffälliger Befund.", "befund": befund}


def bericht(key, bausteine, diktat=""):
    """Nur-Baustein-Diktat → fertiger Befund (vor nachbearbeiten), wortwörtlich."""
    v = vorlage(key, bausteine, diktat)
    return f"## {v['titel']}\n\n## Befund\n{v['befund']}\n\n## Ergebnis\n{v['ergebnis']}"


KI_HINWEIS = ("<ordi_baustein>Die Vorlage ist ein Textbaustein der Ordination ({key}). Übernimm ihren Wortlaut "
              "unverändert und ändere oder ergänze NUR, was im Diktat steht. Nicht diktierte Sätze des Bausteins "
              "bleiben wörtlich stehen.</ordi_baustein>")
