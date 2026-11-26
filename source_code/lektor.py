"""KaiScribe-Lektor (kaiscribe-lektor-einbau-n1, 26.11.2026) — ohne Tk/Windows importierbar und testbar.

Peter 26.11.2026 „Go: a“: Der Lektor kommt in KaiScribe. Scharf geschaltet wird er erst, wenn die KaiScribe-Kosten je
Aufruf im echten Betrieb belegt sind und Konto A (200 $/Monat API) beides trägt. Bis dahin: SCHALTER STANDARD AUS.

Was er tut (Messläufe ris-mods BERICHT_kaiscribe-lektor-messlauf-n1/-n2; gewählt Opus 5.5 medium, Prompt lektor-2,
Arzt-Filter im Code statt im Prompt, nur Nicht-Normal-/Nicht-Bausteinbefunde):
  1. Sobald der Befund rechts steht (nach „Hermi formt“ = KaiScribe-Befund-KI, vor EOL/CAS), läuft im Hintergrund EIN
     Aufruf an Claude Opus 5.5 (Anthropic, KaiScribe-Schlüssel = Konto A), maskiert wie der KaiScribe-Weg
     (ki_maske: Namen/Daten/Nummern → ⟦…⟧, Restprüfung). Der Arzt wartet nie.
  2. Die Antwort liefert Korrekturen (alt → neu) und Prüfzeilen. Korrekturen übernimmt NUR der Wächter
     (lektor_waechter.py = Kopie von ris-mods kaiscribe_lektor/waechter.py): keine Seite/Zahl/Verneinung/Normal-Aussage/
     Graduierung, kein neues Inhaltswort, keine Überschrift, keine Regel-Register- und keine Vorlagensätze. Dazu hier:
     ein Wortwechsel mit anderem Anfangsbuchstaben (n2: „Zelle“ → „Galle“) gilt nicht als Hörfehler.
  3. Stellen, die der Arzt inzwischen im Fenster geändert hat, bleiben unberührt (Zeichen-Diff Lektor-Eingabe ↔ jetzt):
     eine Korrektur nur, wo der Text samt Nachbarzeichen noch genau so steht; eine Prüfzeile nur, wenn ihr Zitat noch
     unverändert dasteht (= Arzt-Filter aus n2).
  4. Prüfzeilen erscheinen als rote Prüfzeile wie bisher (dieselbe Hinweiszeile wie die CAS-/Regel-Prüfzeilen, Endung
     „– bitte prüfen“). Sie stehen nie im Befundtext → nie in CAS/marc/ELGA.
  5. Ist der Lektor bei EOL nicht fertig oder fällt er aus: Befund unverändert. Kein zweiter Versuch, kein anderes
     Modell, kein Gemini.

Schalter (zentral auf X:, je Befunder): LEKTOR_DATEI (config.ini, Standard X:\\KaiScribe\\Daten\\lektor.json).
Fehlt die Datei, ist sie unlesbar oder fehlt X: → AUS. Inhalt z. B.
  {"befunder": {"kp": false, "rg": false}, "monatsdeckel_usd": 40}
Nur kp und rg können ihn bekommen (ERLAUBT, wie KaiScribe). Monatsdeckel: Lektor-$ des Monats über alle PCs
(nutzung.lektor_monat_usd) ≥ Deckel → kein Aufruf mehr in diesem Monat.
Kosten: je Aufruf über den Nutzungszähler mit Rolle „lektor“ (getrennt von den KaiScribe-Befund-Aufrufen, damit die
ct-je-Befund-Zahl von KaiScribe unverfälscht bleibt) → Tagesbericht-Zeile „Lektor …“ und kaiscribe_nutzung_lesen.py.
Im Protokoll stehen nur Zahlen, nie Befund- oder Diktattext.
"""
import difflib
import json
import os
import re
import threading
import time

import ki_maske
import lektor_waechter as W

MODELL = "claude-opus-5-5"
DENKEN = "medium"            # output_config.effort (Opus 5.5 kennt kein „Denken aus“)
MAX_TOKENS = 8000
FRIST_S = 90                 # läuft im Hintergrund; EOL vorher → Ergebnis verworfen
PROMPT_VERSION = "lektor-2"
ERLAUBT = ("kp", "rg")       # Peter 26.11.2026: nur kp + rg (wie KaiScribe)
DECKEL_STANDARD_USD = 40.0   # Monatsdeckel, falls die Schalter-Datei keinen nennt (Messung n2: ≈ 32 $/Monat)
MAX_PRUEFZEILEN = 5
EOL_SPERRE_S = 3.0           # Korrekturen eben erst eingesetzt → EOL braucht eine zweite Bestätigung (wie IB Lab)
SCHALTER_DATEI_STANDARD = "X:\\KaiScribe\\Daten\\lektor.json"
CACHE = {"type": "ephemeral", "ttl": "1h"}
_AUS = ("", "aus", "-", "0", "nein", "off")

# Prompt lektor-2 (ris-mods kaiscribe_lektor/lektor.py SYSTEM_2, wortgleich; gemessen in n1, empfohlen in n2 §5)
SYSTEM = """Du bist Lektor für radiologische Befunde einer österreichischen Röntgenordination. Du bekommst einen fertigen \
Befund (Markdown: „## Titel“, Befundtext, „## Ergebnis“) und das Diktat des Arztes (rohe Spracherkennung). Danach geht der \
Befund zur Vidierung. Persönliche Daten sind durch Platzhalter wie ⟦D1⟧ ersetzt.

Du darfst NUR korrigieren:
1. Grammatik: Kongruenz (Fall, Zahl, Geschlecht von Artikel/Adjektiv/Nomen, z. B. „mit osseäre Ausziehung“ → „mit \
osseärer Ausziehung“, „des Daumen“ → „des Daumens“). Der Telegrammstil ohne Verb („Die Weichteile unauffällig.“, „Im \
Übrigen die Gelenkflächen regelrecht.“) ist Hausstil: KEIN „ist/sind“ ergänzen, keine Artikel ergänzen.
2. Rechtschreibung (Tippfehler wie „Asymetrie“, „Recessuss“, Getrennt-/Zusammenschreibung, Bindestrich, eindeutige \
Groß-/Kleinschreibfehler) und fehlende Satzzeichen zwischen zwei Sätzen. Leerzeichen nicht korrigieren.
3. Offensichtliche Hörfehler der Spracherkennung, wenn der gemeinte Fachbegriff eindeutig ist (z. B. „radikarpal“ → \
„radiokarpal“, „Zusschärfung“ → „Zuschärfung“).
4. Fachbegriff-Schreibweise: lateinische Knochen-/Strukturnamen lateinisch (Clavicula, Os metatarsale, Processus \
styloideus ulnae, Spatia intervertebralia). Kortikalis, Kompakta und Spongiosa schreibt die Praxis wie in den Vorlagen \
mit K – nicht ändern.

Niemals ändern: Seitenangaben und Lage (rechts, links, beidseits, medial, lateral …), Zahlen, Maße, Einheiten, \
Platzhalter ⟦…⟧, Verneinungen (kein, keine, ohne, nicht), Normal-Aussagen (unauffällig, regelrecht …), Graduierungen \
und Abstufungen (gering, mäßig, hochgradig, beginnend, Grad, Kellgren & Lawrence, BI-RADS …), Unsicherheit (Verdacht, \
fraglich, DD), Überschriften (Zeilen mit ##), Reihenfolge, Abkürzungen (weder auflösen noch einführen). Kein Umformulieren, \
kein „schöner schreiben“, nichts ergänzen, nichts kürzen: Der Befund gibt das Diktat wörtlich wieder und wird nie \
verschärft oder abgeschwächt. Feste Vorlagensätze (Normalbefund-Bausteine) bleiben wortgleich, außer bei einem echten \
Rechtschreibfehler. Im Zweifel: nicht ändern.

Inhaltlich Fragliches änderst du NICHT, sondern meldest es als Prüfzeile – nur bei einem klaren Fehler, den ein \
Radiologe sofort korrigieren würde; keine Stilhinweise, keine Vermutungen, im Zweifel keine Prüfzeile. Ein Ergebnis \
darf den Befund zusammenfassen oder gewichten (das ist kein Widerspruch). Ein Befund, der ausführlicher ist als das \
Diktat, ist normal (Vorlage + Diktat):
- seite: Seite widersprüchlich (Titel, Befund, Ergebnis, Diktat)
- normalsatz_trotz_pathologie: ein Normalsatz über eine Struktur, zu der eine Pathologie im Befund oder Diktat steht
- widerspruch: Befund und Ergebnis widersprechen sich
- konfabulation: krankhafter Befund, Grad oder Messwert, der weder im Diktat steht noch aus einem IB-Lab-Block stammt \
(Normalbefund-Vorlagensätze sind gewollt und KEINE Konfabulation)
- fehlt: im Diktat genannter Befund fehlt im Text

Antworte NUR mit JSON, ohne Erklärung:
{"korrekturen": [{"alt": "<exakter, möglichst kurzer, eindeutiger Ausschnitt aus dem Befund>", "neu": "<Ersatz>", \
"art": "grammatik|rechtschreibung|hoerfehler|fachbegriff"}],
 "pruefen": [{"zitat": "<exakter Ausschnitt aus dem Befund>", "art": "seite|normalsatz_trotz_pathologie|widerspruch|\
konfabulation|fehlt", "hinweis": "<kurz>"}]}
Leere Listen, wenn nichts zu tun ist."""

PRUEF_ARTEN = {"seite": "Seite", "normalsatz_trotz_pathologie": "Normalsatz trotz Befund", "widerspruch": "Widerspruch",
               "konfabulation": "nicht diktiert", "fehlt": "Diktat fehlt im Text"}


# ───────────────────────────── Schalter + Deckel ─────────────────────────────
class Schalter:
    """Zentrale Schalter-Datei auf X: (je Befunder). Gelesen höchstens alle LESE_S Sekunden; jeder Fehler → AUS."""
    LESE_S = 30

    def __init__(self, pfad, jetzt=time.monotonic, x_pfad=None):
        self.pfad, self.jetzt = pfad, jetzt
        self._x_pfad = x_pfad
        self._stand, self._zeit = None, -1e9

    def _lesen(self):
        p = str(self.pfad or "").strip().strip('"')
        if p.lower() in _AUS:
            return {}
        if self._x_pfad:
            p = self._x_pfad(p)
        try:
            with open(p, encoding="utf-8-sig") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def stand(self):
        t = self.jetzt()
        if self._stand is None or t - self._zeit >= self.LESE_S:
            self._stand, self._zeit = self._lesen(), t
        return self._stand

    def an_fuer(self, kuerzel):
        return befunder_an(self.stand(), kuerzel)

    def deckel_usd(self):
        return deckel_aus(self.stand())


def befunder_an(d, kuerzel):
    """{"befunder": {"kp": true}} oder {"befunder": ["kp"]} → True nur für ERLAUBT-Kürzel mit ausdrücklichem an."""
    k = str(kuerzel or "").strip().lower()
    if not k or k not in ERLAUBT or not isinstance(d, dict):
        return False
    b = d.get("befunder")
    if isinstance(b, dict):
        v = b.get(k, b.get(k.upper()))
        return v is True or str(v).strip().lower() in ("an", "ja", "true", "1")
    if isinstance(b, list):
        return k in [str(x).strip().lower() for x in b]
    return False


def deckel_aus(d):
    try:
        v = float((d or {}).get("monatsdeckel_usd", DECKEL_STANDARD_USD))
    except (TypeError, ValueError):
        v = DECKEL_STANDARD_USD
    return max(0.0, v)


# ───────────────────────────── Normal-/Bausteinbefund (Variante D) ─────────────────────────────
def _saetze(t):
    t = re.sub(r"\s+", " ", W._nfc(t))
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]


def vorlagen_pool(*quellen):
    """Alle Sätze aus Vorlagen/Bausteinen (templates.json, ordi_bausteine …), klein geschrieben."""
    pool = set()

    def rein(x):
        if isinstance(x, str):
            for s in _saetze(x.replace("\n", " ")):
                pool.add(" ".join(s.lower().split()))
        elif isinstance(x, dict):
            for v in x.values():
                rein(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                rein(v)
    for q in quellen:
        rein(q)
    return pool


NORMAL_ERGEBNIS = re.compile(r"unauff|regelrecht|normalbefund|altersentsprechend|kein(?:e|en)?\s+(?:pathologisch|hinweis|"
                             r"nachweis)|ohne\s+(?:pathologisch|befund)|birads:?\s*[12]\b|bi-rads\s*[12]\b|acr:?\s*[a-d1-4]", re.I)
_PATHO_ERG = re.compile(r"arthros|fraktur|verdacht|zustand nach|status post|skoliose|osteochondrose|spondyl", re.I)


def normal_oder_baustein(befund, diktat, pool, ist_normal_diktat=None):
    """True = reiner Normalbefund bzw. nur Vorlagen-/Bausteinsätze mit Normal-Ergebnis → kein Lektor (n1, Variante D).
    ist_normal_diktat(diktat, titel) = normalbypass.is_pure_normal_finding."""
    titel = [z.strip("# ").strip() for z in (befund or "").splitlines() if z.startswith("## ")
             and z.strip("# :").strip().lower() not in ("befund", "ergebnis")]
    if ist_normal_diktat and diktat and ist_normal_diktat(diktat, titel):
        return True
    befundteil, ergebnis, teil = [], [], "befund"
    for z in (befund or "").splitlines():
        k = z.strip().lower()
        if k.startswith("## "):
            teil = "ergebnis" if k.strip("# :").strip() == "ergebnis" else "titel"
            continue
        (ergebnis if teil == "ergebnis" else befundteil).append(z)
    saetze = [s for s in _saetze(" ".join(befundteil)) if len(s.split()) > 2]
    erg = " ".join(ergebnis).strip()
    if not saetze or not erg:
        return False
    if any(" ".join(s.lower().split()) not in pool for s in saetze):
        return False
    return all(NORMAL_ERGEBNIS.search(s) and not _PATHO_ERG.search(s)
               for s in (re.sub(r"^\d+[.)]\s*", "", s) for s in _saetze(erg)))


# ───────────────────────────── Aufruf ─────────────────────────────
def nachricht(befund, diktat):
    d = (diktat or "").strip() or "(kein Diktat-Text vorhanden)"
    return f"<befund>\n{befund.strip()}\n</befund>\n\n<diktat>\n{d}\n</diktat>"


def body(text):
    """Messages-Body: Systemprompt (ohne Patientendaten) 1 h im Cache, Opus 5.5 mit effort medium, kein temperature."""
    return {"model": MODELL, "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": SYSTEM, "cache_control": dict(CACHE)}],
            "output_config": {"effort": DENKEN},
            "messages": [{"role": "user", "content": text}]}


def antwort_lesen(text):
    """JSON aus der Antwort (auch mit ```-Zaun; mehrere JSON → letzte gültige Antwort) → dict oder None."""
    t = (text or "").strip()
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        d = json.loads(t[a:b + 1])
    except ValueError:
        d, dec, i = None, json.JSONDecoder(), a
        while i >= 0:
            try:
                x, ende = dec.raw_decode(t, i)
                if isinstance(x, dict) and ("korrekturen" in x or "pruefen" in x):
                    d = x
                i = t.find("{", ende)
            except ValueError:
                i = t.find("{", i + 1)
        if d is None:
            return None
    if not isinstance(d, dict):
        return None
    return {"korrekturen": [k for k in d.get("korrekturen") or [] if isinstance(k, dict)],
            "pruefen": [k for k in d.get("pruefen") or [] if isinstance(k, dict)]}


class Ausfall(Exception):
    """Lektor nicht verwendbar (Netz, HTTP, Frist, Maske unsicher, Antwort unlesbar) → Befund bleibt unverändert."""

    def __init__(self, grund, kosten=None):
        super().__init__(grund)
        self.grund, self.kosten = grund, kosten


def kategorie(e):
    """Ausfall-Kategorie ohne Werte (fürs Protokoll/den Zähler)."""
    if isinstance(e, Ausfall):
        return e.grund
    if isinstance(e, ki_maske.MaskeUnsicher):
        return "Maske unsicher"
    status = getattr(e, "status", None)
    if status:
        return f"HTTP {status}"
    if isinstance(e, (TimeoutError,)) or "timed out" in str(e).lower():
        return "Zeitüberschreitung"
    return f"Ausfall ({type(e).__name__})"


def aufrufen(befund, diktat, sender, namen=(), frist=FRIST_S, kosten_fn=None):
    """EIN maskierter Lektor-Aufruf → (antwort_dict mit zurückgesetzten Texten, info). Wirft Ausfall.
    sender(body, frist) = llm_anbieter.anthropic_sender (KaiScribe-Schlüssel, Konto A)."""
    try:
        m = ki_maske.Maske(list(namen or ()))
        text = m.maskieren(nachricht(befund, diktat))
        m.restpruefung([text])
    except ki_maske.MaskeUnsicher:
        raise Ausfall("Maske unsicher") from None
    t0 = time.time()
    try:
        data = sender(body(text), frist)
    except Exception as e:      # noqa: BLE001 — jeder Fehler = Ausfall, kein zweiter Versuch
        raise Ausfall(kategorie(e)) from None
    dauer = time.time() - t0
    usage = (data or {}).get("usage") or {}
    kosten = {"usage": usage, "usd": kosten_fn(MODELL, usage) if kosten_fn else 0.0, "s": round(dauer, 2)}
    if (data or {}).get("type") == "error" or "error" in (data or {}):
        raise Ausfall("Fehlerantwort", kosten)
    if data.get("stop_reason") not in ("end_turn", "stop_sequence"):
        raise Ausfall(f"Antwort abgebrochen ({data.get('stop_reason')})", kosten)
    roh = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    d = antwort_lesen(roh)
    if d is None:
        raise Ausfall("Antwort unlesbar", kosten)
    return zuruecksetzen(d, m), dict(kosten, platzhalter=len(m.zu_wert))


_PH = re.compile(ki_maske.KLAMMER_AUF + r"[PDNAE]\d+" + ki_maske.KLAMMER_ZU)


def zuruecksetzen(d, maske):
    """Korrekturen mit Platzhalter fallen weg (der Wächter darf nie Personendaten ändern). Prüfzeilen: Platzhalter
    zurück (nur lokale Anzeige); unbekannter/kaputter Platzhalter → Zeile weg."""
    korr = []
    for k in d.get("korrekturen") or []:
        alt, neu = str(k.get("alt") or ""), str(k.get("neu") or "")
        if ki_maske.KLAMMER_AUF in alt + neu or ki_maske.KLAMMER_ZU in alt + neu:
            continue
        korr.append({"alt": alt, "neu": neu, "art": str(k.get("art") or "")[:20]})
    pr = []
    for q in d.get("pruefen") or []:
        z, h = str(q.get("zitat") or ""), str(q.get("hinweis") or "")
        if any(p not in maske.zu_wert for p in _PH.findall(z + h)):
            continue
        z, h = maske.zuruecksetzen(z), maske.zuruecksetzen(h)
        if ki_maske.KLAMMER_AUF in z + h or ki_maske.KLAMMER_ZU in z + h:
            continue
        pr.append({"zitat": z, "hinweis": h, "art": str(q.get("art") or "")[:40]})
    return {"korrekturen": korr, "pruefen": pr}


# ───────────────────────────── Wächter + Arzt-Filter ─────────────────────────────
def _anfang(w):
    return W._norm_wort(w)[:1]


def wortwechsel(alt, neu):
    """n2 §5 (Wächter ergänzen): „Zelle“ → „Galle“ ist kein Hörfehler, sondern ein anderes Wort. Ein geändertes
    Inhaltswort muss mit demselben Buchstaben beginnen (c/k, z/k, ph/f gleich) – außer es ist fast gleich (≥ 0,85)."""
    wa, wn = W._inhalt(W.woerter(alt)), W._inhalt(W.woerter(neu))
    for x in wn:
        if any(W._norm_wort(x) == W._norm_wort(y) for y in wa):
            continue
        nahe = max(wa, key=lambda y: difflib.SequenceMatcher(None, W._norm_wort(x), W._norm_wort(y)).ratio(), default="")
        if nahe and _anfang(nahe) != _anfang(x) and \
                difflib.SequenceMatcher(None, W._norm_wort(x), W._norm_wort(nahe)).ratio() < 0.85:
            return True
    return False


def pruefen_korrektur(basis, alt, neu, register=(), vorlagen=None):
    """Wächter (Pflicht) + Wortwechsel-Regel → (ok, grund)."""
    ok, grund = W.pruefen_eine(basis, alt, neu, register, vorlagen)
    if ok and wortwechsel(alt, neu):
        return False, "Wortwechsel (kein Hörfehler)"
    return ok, grund


def _gleich_bloecke(basis, jetzt):
    """Bereiche (i1, i2, j1) aus basis, die in jetzt unverändert stehen (Zeichen-Diff)."""
    sm = difflib.SequenceMatcher(None, basis, jetzt, autojunk=False)
    return [(i1, i2, j1) for tag, i1, i2, j1, _j2 in sm.get_opcodes() if tag == "equal"]


def _abbilden(bloecke, a, b, basis_len):
    """Position a..b der basis → Position in jetzt, nur wenn a-1..b+1 (Nachbarzeichen) in EINEM gleichen Block liegt."""
    lo, hi = max(0, a - 1), min(basis_len, b + 1)
    for i1, i2, j1 in bloecke:
        if i1 <= lo and hi <= i2:
            return j1 + (a - i1)
    return None


def arzt_spannen(basis, jetzt):
    """Zeichenbereiche in jetzt, die der Arzt gegenüber der Lektor-Eingabe neu geschrieben/geändert hat."""
    sm = difflib.SequenceMatcher(None, basis, jetzt, autojunk=False)
    return [(j1, j2) for tag, _i1, _i2, j1, j2 in sm.get_opcodes() if tag in ("replace", "insert") and j2 > j1] + \
        [(j1, j1) for tag, _i1, _i2, j1, _j2 in sm.get_opcodes() if tag == "delete"]


def _in_titel(text, pos):
    a = text.rfind("\n", 0, pos) + 1
    return bool(W.TITEL.match(text[a:text.find("\n", pos) if text.find("\n", pos) >= 0 else len(text)]))


def zusammenfuehren(basis, jetzt, antwort, register=(), vorlagen=None):
    """Lektor-Antwort (auf basis) in den jetzigen Feldtext einarbeiten.
    → (aenderungen [(pos, laenge, neu)] absteigend nach pos für das Textfeld, pruefzeilen [Text], zaehler {…})."""
    basis, jetzt = W._nfc(basis), W._nfc(jetzt)
    z = {"korrekturen": 0, "uebernommen": 0, "waechter": 0, "arzt": 0, "pruefen": 0, "pruefzeilen": 0, "pruef_arzt": 0,
         "pruef_hausregel": 0}
    bloecke = _gleich_bloecke(basis, jetzt) if basis != jetzt else [(0, len(basis), 0)]
    belegt, plan = [], []
    for k in (antwort or {}).get("korrekturen") or []:
        z["korrekturen"] += 1
        alt, neu = W._nfc(str(k.get("alt") or "")), W._nfc(str(k.get("neu") or ""))
        ok, _grund = pruefen_korrektur(basis, alt, neu, register, vorlagen)
        if not ok:
            z["waechter"] += 1
            continue
        treffer = False
        for m in W._muster(alt).finditer(basis):
            a, b = m.start(), m.end()
            if _in_titel(basis, a) or any(a < y and b > x for x, y in belegt):
                continue
            pos = _abbilden(bloecke, a, b, len(basis))
            if pos is None:
                continue
            belegt.append((a, b))
            plan.append((pos, b - a, neu))
            treffer = True
        z["uebernommen" if treffer else "arzt"] += 1
    plan.sort(key=lambda x: -x[0])
    # Prüfzeilen: nur, wenn das Zitat im jetzigen Text unverändert steht und nicht auf einer Arzt-Stelle liegt
    sp = arzt_spannen(basis, jetzt) if basis != jetzt else []
    zeilen = []
    for q in (antwort or {}).get("pruefen") or []:
        z["pruefen"] += 1
        zitat = " ".join(W._nfc(str(q.get("zitat") or "")).split())
        if len(zitat) < 3:
            continue
        muster = re.compile(r"\s+".join(re.escape(t) for t in zitat.split()))
        fund = list(muster.finditer(jetzt))
        if not fund or all(any(m.start() < y and m.end() > x or (x == y and m.start() < x < m.end()) for x, y in sp)
                           for m in fund):
            z["pruef_arzt"] += 1
            continue
        if hausregel(zitat, str(q.get("art") or ""), jetzt, register):
            z["pruef_hausregel"] += 1
            continue
        zeile = pruefzeile(zitat, str(q.get("hinweis") or ""), str(q.get("art") or ""))
        if zeile not in zeilen and len(zeilen) < MAX_PRUEFZEILEN:
            zeilen.append(zeile)
    z["pruefzeilen"] = len(zeilen)
    return plan, zeilen, z


_KL = re.compile(r"Grad\s*(?:[0-4]|I{1,3}|IV)\s*nach\s*Kellgren", re.I)


def hausregel(zitat, art, text, register=()):
    """„nicht diktiert“ (konfabulation) auf einem K&L-Grad oder einem Regel-Register-Wortlaut (K&L-Tabellensatz, IB-Lab-
    Satz) ist ein Fehlalarm: die Hausregel leitet den Grad aus dem diktierten Adjektiv ab (n2: P52). Ein Widerspruch
    Adjektiv ↔ Grad kommt als „widerspruch“ und bleibt."""
    if art != "konfabulation":
        return False
    if _KL.search(zitat):
        return True
    zn = " ".join(W._nfc(zitat).split()).lower()
    return any(zn in " ".join(r.split()).lower() or " ".join(r.split()).lower() in zn for r in register if len(r) >= 15)


def anwenden_auf(text, plan):
    """plan (absteigend) auf einen String anwenden (Tests, Stand für Restructure)."""
    for pos, n, neu in plan:
        text = text[:pos] + neu + text[pos + n:]
    return text


def pruefzeile(zitat, hinweis="", art=""):
    """Rote Prüfzeile im bisherigen Format („…“ … – bitte prüfen), mit Herkunft „Lektor“."""
    z = zitat if len(zitat) <= 60 else zitat[:59] + "…"
    h = " ".join((hinweis or PRUEF_ARTEN.get(art, "")).split())
    h = h if len(h) <= 70 else h[:69] + "…"
    return f"„{z}“: {h} (Lektor) – bitte prüfen" if h else f"„{z}“ (Lektor) – bitte prüfen"


# ───────────────────────────── Lauf je Befund ─────────────────────────────
class Lauf:
    """Ein Lektor-Lauf für den Befund, der gerade rechts steht. Der Thread ruft nur aufrufen(); eingearbeitet wird im
    UI-Thread (fertig_fn). abbrechen() (EOL, neues Diktat, Felder leeren) → das Ergebnis wird verworfen."""

    def __init__(self, basis, diktat, sender, namen=(), frist=FRIST_S, kosten_fn=None, fertig_fn=None,
                 melden=None, log=None, starten=True):
        self.basis, self.diktat = basis, diktat
        self.sender, self.namen, self.frist, self.kosten_fn = sender, namen, frist, kosten_fn
        self.fertig_fn, self.melden = fertig_fn, melden or (lambda *a: None)
        self.log = log or (lambda *a: None)
        self.ergebnis = self.info = self.fehler = None
        self.abgebrochen, self.fertig = False, False
        self.start = time.monotonic()
        self._sperre = threading.Lock()
        if starten:
            threading.Thread(target=self.laufen, daemon=True, name="lektor").start()

    def laufen(self):
        try:
            self.ergebnis, self.info = aufrufen(self.basis, self.diktat, self.sender, self.namen, self.frist,
                                                self.kosten_fn)
        except Ausfall as e:
            self.fehler = e
        except Exception as e:  # noqa: BLE001
            self.fehler = Ausfall(kategorie(e))
        with self._sperre:
            self.fertig = True
            spaet = self.abgebrochen
        kosten = self.info if self.fehler is None else (self.fehler.kosten or {})
        if kosten:      # abgerechnet (auch wenn verworfen oder zu spät) → Kosten zählen
            self.melden({"rolle": "lektor", "anbieter": "anthropic", "modell": MODELL, "usage": kosten.get("usage"),
                         "usd": kosten.get("usd", 0.0), "s": kosten.get("s")})
        if self.fehler is not None:
            self.melden({"rolle": "lektor", "lektor": "ausfall", "grund": self.fehler.grund})
            self.log(f"[LEKTOR] ausgefallen – {self.fehler.grund} → Befund unverändert (kein zweiter Versuch, kein "
                     "anderes Modell)")
            return
        if spaet:
            self.melden({"rolle": "lektor", "lektor": "zu_spaet"})
            self.log(f"[LEKTOR] Antwort nach EOL/Abbruch ({time.monotonic() - self.start:.1f} s) – verworfen")
            return
        if self.fertig_fn:
            self.fertig_fn(self)

    def abbrechen(self, wodurch="EOL"):
        """True = lief noch (Ergebnis wird verworfen)."""
        with self._sperre:
            if self.fertig or self.abgebrochen:
                self.abgebrochen = True
                return False
            self.abgebrochen = True
        self.log(f"[LEKTOR] bei {wodurch} noch nicht fertig ({time.monotonic() - self.start:.1f} s) – Befund unverändert")
        return True


def register_saetze_laden(pfad):
    """Regel-Register-Wortlaute (regeln.json, in der EXE gebündelt) → Liste; fehlt die Datei → []."""
    try:
        return W.register_saetze(pfad) if pfad and os.path.exists(pfad) else []
    except (OSError, ValueError, KeyError, TypeError):
        return []
