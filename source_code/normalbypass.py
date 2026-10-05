"""normalbypass.py — v3.2: Wann darf der Normalbefund-Bypass (ohne LLM) laufen?

Pendant: web_app/src/normalbypass.ts (gleiche Semantik, gleiche Fixtures: normal_bypass_tests.json).

Peter 05.10.: Der alte Bypass schrieb das Diktat 1:1 ins Ergebnis und griff auch bei Diktaten wie
"Thorax: Kardiomegalie, sonst unauffällig" (Kardiomegalie stand auf keiner Pathologie-Liste).
Jetzt steht im Bypass-Ergebnis der Normal-Ergebnis-Satz des Templates — deshalb darf der Bypass
NUR noch greifen, wenn das Diktat ausschließlich aus Untersuchungsbezeichnung + Normal-Worten
besteht. Jedes unbekannte Wort (Pathologie, Beschreibung, "sonst") → LLM-Strukturierung.
Lieber einmal zu oft das LLM als eine verschluckte Pathologie.
"""
import re

NORMAL_MARKERS = re.compile(
    r"unauff(?:ae|ä)?llig|\bnormal|regelrecht|\bob\b|ohne (?:pathologischen )?befund|kein pathologischer befund|normalbefund"
)
# Wörter, die einen Rest-/Ausnahme-Befund ankündigen → nie Bypass
RESTWORTE = {"sonst", "ansonsten", "übrigen", "übrigens", "abgesehen", "außer", "ausser", "bis", "aber", "jedoch",
             "bei", "mit", "wie", "vereinbar", "verdacht", "v.a", "va", "dd", "z.n", "zn", "zustand", "nach"}
FUELL = {
    "und", "in", "der", "die", "das", "des", "dem", "den", "ist", "sind", "im", "am", "zum", "zur", "vom", "von",
    "beider", "beide", "beidseits", "beidseitig", "bds", "links", "rechts", "li", "re", "linkes", "rechtes",
    "linken", "rechten", "linke", "rechte", "seitlich", "seitl", "pa", "p", "a", "ap", "lateral", "axial",
    "ebenen", "ebene", "zwei", "2", "1", "3", "eine", "ein", "röntgen", "rö", "roentgen", "aufnahme", "aufnahmen",
    "befund", "ohne", "kein", "keine", "pathologisch", "pathologischen", "pathologischer", "sono", "sonographie",
    "sonografie", "ultraschall", "untersuchung", "stehend", "liegend", "stand", "liegen", "vollkommen", "völlig",
    "komplett", "insgesamt", "altersentsprechend", "altersentsprechender", "darstellung", "dargestellt",
    "unauffällig", "unauffällige", "unauffälliger", "unauffälliges", "unauffaellig", "unauffällig.", "normal",
    "normale", "normaler", "normales", "regelrecht", "regelrechte", "regelrechter", "regelrechtes", "ob",
    "normalbefund", "also", "hier", "heute", "punkt", "es", "sich", "zeigt", "zeigen", "sowie",
}
SYNONYME = {
    "lunge", "lungen", "herz", "brustkorb", "thorax", "torax", "hws", "bws", "lws", "hw", "osg", "usg", "isg",
    "knie", "hüfte", "hüft", "hüften", "schulter", "schultern", "ellbogen", "ellenbogen", "sprunggelenk",
    "handgelenk", "hand", "fuß", "fuss", "finger", "daumen", "zehe", "zehen", "becken", "schädel", "kopf",
    "nnh", "nebenhöhlen", "wirbelsäule", "halswirbelsäule", "brustwirbelsäule", "lendenwirbelsäule",
    "gelenk", "gelenke", "gelenks", "skelett", "mamma", "mammae", "brust", "brüste", "abdomen", "bauch",
    "schilddrüse", "sd", "nerv", "nervus", "n", "m", "muskel", "muskulatur", "weichteile", "weichteil",
    "unterschenkel", "oberschenkel", "unterarm", "oberarm", "venen", "beinvenen", "halsgefäße", "carotis",
    "carotiden", "duplex", "rippen", "sternum", "kreuzbein", "steißbein", "calcaneus", "ferse", "kahnbein",
    "skaphoid", "scaphoid", "orbita", "orbitae", "jochbein", "jochbogen", "nasenbein", "kiefer", "opg",
}
WORTTEILE = {"röntgen", "roentgen", "aufnahme", "aufnahmen", "sonographie", "sonografie", "sono", "schall",
             "ultraschall", "gelenk", "gelenks", "gelenke", "bild", "untersuchung"}
FUGEN = ("", "s", "n", "en", "e")


def _region_words(display_names):
    w = set(SYNONYME)
    for dn in display_names:
        for t in re.findall(r"[a-zäöüß]+", (dn or "").lower()):
            if len(t) >= 2 and t not in RESTWORTE:
                w.add(t)
    return w


def _tokens(text):
    t = text.lower()
    t = re.sub(r"o\.\s*b\.?", " ob ", t)            # o.B. / o. B.
    t = re.sub(r"p\.\s*a\.?", " pa ", t)             # p.a.
    t = re.sub(r"a\.\s*-?\s*p\.?", " ap ", t)        # a.p. / a.-p.
    t = re.sub(r"[^\wäöüß]+", " ", t)
    out = []
    for tok in t.split():
        out.extend([x for x in tok.split("_") if x])
    return out


def _compound_ok(tok, allowed):
    parts = allowed | WORTTEILE
    for i in range(2, len(tok) - 1):
        a, b = tok[:i], tok[i:]
        if b not in parts:
            continue
        for f in FUGEN:
            if f and a.endswith(f) and a[: -len(f)] in parts:
                return True
            if not f and a in parts:
                return True
    return False


def is_pure_normal_finding(text, display_names=()):
    """True = Diktat ist ein reiner Normalbefund (nur Untersuchung + Normal-Worte) → Bypass erlaubt."""
    if not text or not text.strip():
        return False
    low = text.lower()
    if not NORMAL_MARKERS.search(low.replace("o. b", "ob").replace("o.b", "ob")):
        return False
    toks = _tokens(text)
    if not toks or len(toks) > 16:
        return False
    region = _region_words(display_names)
    for tok in toks:
        if tok in RESTWORTE:
            return False
        if tok in FUELL or tok in region or tok.isdigit():
            continue
        if _compound_ok(tok, region):
            continue
        return False
    return True
