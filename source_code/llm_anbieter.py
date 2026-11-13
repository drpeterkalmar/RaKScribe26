"""Befund-KI-Anbieter der EXE (kaiscribe-haiku-ab-n1, 13.11.2026) — ohne Tk/Windows importierbar, Netz austauschbar.

Einstellung LLM_ANBIETER (config.ini) = gemini (Standard, unverändert) | anthropic. Später kann ein dritter Anbieter
(lokales Modell in der VM) dazukommen: eigener Zweig in Weiche._anbieter_aufruf, Maskierung/Rückfall bleiben gleich.

Anthropic-Weg (Peters Entscheid 03.11.2026: Claude direkt bei Anthropic NUR mit maskiertem Text)
  1. Fester Prompt-Anfang (Regeln bis vor die Vorlage bzw. vor das Diktat) geht unverändert und als Prompt-Cache
     (cache_control) hinaus — er enthält nie Patientendaten.
  2. Der Rest (Vorlage, Beispiele/Widerspruch-Block, CAS-/IB-Lab-Block, Diktat) wird mit ki_maske.Maske maskiert
     (Namen, Daten, Nummern, Adressen, E-Mail → ⟦P1⟧ …) und unabhängig nachgeprüft (restpruefung).
  3. Antwort lokal zurücksetzen. Rückfall auf Gemini (und Protokollzeile, nur Kategorie, nie der Wert), wenn:
     Maske unsicher (Merkmal im Ausgang), ein Platzhalter des Diktats fehlt in der Antwort, ein unbekannter/
     kaputter Platzhalter übrig bleibt, die Antwort unvollständig ist, Anthropic ausfällt oder die Frist überschreitet.
  Nie ein Befund mit fehlendem Namen/Datum — dann lieber Gemini.

ki_maske.py ist eine KOPIE von ~/dev/ris-mods/bruecke/ki_maske.py (KaiFormat); tests/offline/test_llm_anbieter.py
prüft die Gleichheit, solange ris-mods daneben liegt.
"""
import json
import re
import time
import urllib.request

import ki_maske

ANBIETER = ("gemini", "anthropic")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODELL = "claude-haiku-5-5"
ANTHROPIC_FRIST_S = 20          # Live-Diktat darf nicht hängen: danach Gemini
MAX_TOKENS = 4000

# $ je 1 Mio Token (Input, Cache-Lesen, Cache-Schreiben 5 min, Output) — Anthropic-Preisliste; Haiku 5.5 bis 100k Prompt
PREISE = {
    "claude-haiku-5-5": (0.10, 0.01, 0.125, 0.50),
    "claude-sonnet-5-5": (2.00, 0.20, 2.50, 10.00),
}

_PH = re.compile(ki_maske.KLAMMER_AUF + r"[PDNAE]\d+" + ki_maske.KLAMMER_ZU)
_KORR_ANFANG = "Du bist ein medizinischer Lektor für radiologische Diktate"
_VAL_ANFANG = "Du bist ein radiologischer Qualitätskontrolleur"


class Rueckfall(Exception):
    """Anthropic-Antwort nicht verwendbar → Gemini. Text = Kategorie (ohne Patientendaten)."""


def kosten_usd(modell, usage):
    p_in, p_cr, p_cw, p_out = PREISE.get(modell, PREISE["claude-sonnet-5-5"])
    u = usage or {}
    return (int(u.get("input_tokens", 0) or 0) * p_in + int(u.get("cache_read_input_tokens", 0) or 0) * p_cr
            + int(u.get("cache_creation_input_tokens", 0) or 0) * p_cw + int(u.get("output_tokens", 0) or 0) * p_out) / 1e6


def fester_anfang(prompt):
    """Konstanter Prompt-Anfang ohne Patientendaten (geht unmaskiert + gecacht hinaus) oder "".
    Gen-Prompt: bis einschließlich '<normalbefund_template>\\n' — nur wenn das Diktat danach kommt.
    Call 0: bis einschließlich des letzten 'Roh: '. Validator: bis vor '<diktat>'."""
    p = prompt or ""
    if p.startswith(_KORR_ANFANG):
        i = p.rfind("\n\nRoh: ")
        return p[:i + 7] if i > 0 else ""
    if p.startswith(_VAL_ANFANG):
        i = p.find("\n<diktat>\n")
        return p[:i + 1] if i > 0 else ""
    marke = "<normalbefund_template>\n"
    i = p.find(marke)
    if i > 0 and "<diktat>" not in p[:i] and "<diktat>" in p[i:]:
        return p[:i + len(marke)]
    return ""


def diktat_teil(maskiert):
    """Teil des maskierten Rests, dessen Platzhalter in der Antwort wiederkommen MÜSSEN (das Diktat)."""
    m = list(re.finditer(r"<diktat>\n?(.*?)\n?</diktat>", maskiert, re.S))
    if m:
        return m[-1].group(1)
    if maskiert.rstrip().endswith("Korrigiert:"):          # Call 0: Rest = '<Diktat>\n\nKorrigiert:'
        return maskiert.rstrip()[:-len("Korrigiert:")]
    return maskiert


# Call 0 für Claude: Der Gemini-Prompt endet mit „Roh: <Diktat>\n\nKorrigiert:“ (Vervollständigungs-Stil). Haiku 5.5
# hält das Diktat dann für ein weiteres Beispiel und fragt zurück („Bitte gib mir den Text …“, 13.11.2026 in 15 von 20
# Fällen, mit und ohne Systemanweisung). Mit dem Diktat in <diktat>-Tags 20/20 → nur auf dem Anthropic-Weg umgestellt,
# der Gemini-Prompt bleibt wortgleich (Snapshot).
KORR_KOPF = "## ZU KORRIGIERENDES DIKTAT (der Text in <diktat> — kein Beispiel):\n"
KORR_FUSS = "\n</diktat>\n\nGib NUR den korrigierten Text des Diktats aus."


def korrektur_plausibel(roh, text):
    """Call-0-Antwort taugt nur, wenn sie ≥ 60 % so lang ist wie der Rohtext UND mindestens die Hälfte seiner Wörter
    enthält (eine Rückfrage/Erklärung des Modells ist oft ähnlich lang, teilt aber kaum Wörter)."""
    if not text or len(text) < len((roh or "").strip()) * 0.6:
        return False
    w_roh = set(re.findall(r"\w+", (roh or "").lower()))
    return not w_roh or len(w_roh & set(re.findall(r"\w+", text.lower()))) >= 0.5 * len(w_roh)


def _anthropic_form(prompt, fest):
    """(fest, rest) so, wie sie an Claude gehen (Call 0 umgestellt, sonst unverändert)."""
    rest = prompt[len(fest):]
    if fest.startswith(_KORR_ANFANG) and fest.endswith("Roh: ") and rest.rstrip().endswith("Korrigiert:"):
        roh = rest.rstrip()[:-len("Korrigiert:")].rstrip("\n")
        return fest[:-len("Roh: ")] + KORR_KOPF, "<diktat>\n" + roh + KORR_FUSS
    return fest, rest


def maskieren(prompt):
    """→ (fest, maskierter Rest, Maske, Pflicht-Platzhalter). Wirft ki_maske.MaskeUnsicher."""
    fest, rest = _anthropic_form(prompt, fester_anfang(prompt))
    m = ki_maske.Maske()
    rest = m.maskieren(rest)
    m.restpruefung([rest])
    return fest, rest, m, sorted(set(_PH.findall(diktat_teil(rest))))


def zuruecksetzen(antwort, maske, pflicht):
    """Platzhalter zurück; Rueckfall, wenn einer des Diktats fehlt oder ein unbekannter/kaputter übrig bleibt."""
    fehlt = [p for p in pflicht if p not in antwort]
    if fehlt:
        raise Rueckfall(f"Platzhalter fehlt in der Antwort ({len(fehlt)} von {len(pflicht)})")
    unbekannt = [p for p in _PH.findall(antwort) if p not in maske.zu_wert]
    if unbekannt:
        raise Rueckfall("unbekannter Platzhalter in der Antwort")
    text = maske.zuruecksetzen(antwort)
    if ki_maske.KLAMMER_AUF in text or ki_maske.KLAMMER_ZU in text:
        raise Rueckfall("Platzhalter-Rest in der Antwort")
    return text


def anthropic_body(fest, rest, sys_msg, modell=ANTHROPIC_MODELL, max_tokens=MAX_TOKENS):
    """Messages-Body: fester Anfang als Cache-Breakpoint (System + Anfang gecacht), Nachdenken aus, kein temperature
    (Haiku/Sonnet 5.5 lehnen temperature ab)."""
    teile = ([{"type": "text", "text": fest, "cache_control": {"type": "ephemeral"}}] if fest else []) + \
        [{"type": "text", "text": rest}]
    body = {"model": modell, "max_tokens": max_tokens, "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": teile}]}
    if sys_msg:
        body["system"] = [{"type": "text", "text": sys_msg}]
    return body


def anthropic_text(data):
    return "".join(b.get("text", "") for b in (data or {}).get("content", []) if b.get("type") == "text").strip()


def anthropic_sender(key_fn, urlopen=None):
    """Produktions-Sender: body, frist → Antwort-JSON (wirft bei HTTP-Fehler/Zeitüberschreitung)."""
    def senden(body, frist):
        key = key_fn() if callable(key_fn) else key_fn
        if not key:
            raise Rueckfall("kein Anthropic-Schlüssel")
        req = urllib.request.Request(ANTHROPIC_URL, data=json.dumps(body).encode(), method="POST", headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with (urlopen or urllib.request.urlopen)(req, timeout=frist) as r:
            return json.loads(r.read())
    return senden


def maskiert_anthropic(prompt, sys_msg, sender, modell=ANTHROPIC_MODELL, frist=ANTHROPIC_FRIST_S, pruefen=None,
                       strip=None):
    """Ein maskierter Anthropic-Aufruf → (Text, Info). Wirft Rueckfall/MaskeUnsicher/Netzfehler."""
    fest, rest, maske, pflicht = maskieren(prompt)
    t0 = time.time()
    data = sender(anthropic_body(fest, rest, sys_msg, modell), frist)
    dauer = time.time() - t0
    if data.get("type") == "error" or "error" in data:
        raise Rueckfall("Anthropic-Fehlerantwort")
    if data.get("stop_reason") not in ("end_turn", "stop_sequence"):
        raise Rueckfall(f"Antwort abgebrochen ({data.get('stop_reason')})")
    roh = anthropic_text(data)
    roh = strip(roh) if strip else roh
    text = zuruecksetzen(roh, maske, pflicht)
    if pruefen is not None and not pruefen(text):
        raise Rueckfall("Antwort unvollständig")
    usage = data.get("usage", {})
    return text, {"anbieter": "anthropic", "modell": modell, "s": round(dauer, 2), "usage": usage,
                  "usd": kosten_usd(modell, usage), "platzhalter": len(maske.zu_wert), "pflicht": len(pflicht),
                  "zaehlung": maske.zaehlung()}


class Weiche:
    """LLM-Aufruf je Anbieter mit Rückfall. gemini_fn(prompt, sys_msg) → Text (wirft bei Fehler).
    beobachter(info) bekommt je Aufruf {rolle, anbieter, modell, s, usage, usd, rueckfall, platzhalter, pflicht}."""

    def __init__(self, anbieter="gemini", modell=ANTHROPIC_MODELL, gemini_fn=None, sender=None, log=None,
                 frist=ANTHROPIC_FRIST_S, beobachter=None):
        self.anbieter = (anbieter or "gemini").strip().lower()
        if self.anbieter not in ANBIETER:
            self.anbieter = "gemini"
        self.modell = modell or ANTHROPIC_MODELL
        self.gemini_fn, self.sender, self.frist = gemini_fn, sender, frist
        self.log = log or (lambda *a: None)
        self.beobachter = beobachter
        self.zaehler = {"anthropic": 0, "rueckfall": 0}

    def name(self):
        return "gemini/gemini-3.5-flash" if self.anbieter == "gemini" else f"anthropic/{self.modell}"

    def _melden(self, info):
        if self.beobachter:
            try:
                self.beobachter(info)
            except Exception:
                pass

    def __call__(self, prompt, sys_msg=None, pruefen=None, rolle="gen", strip=None, gemini=None):
        if self.anbieter == "anthropic" and self.sender is not None:
            try:
                text, info = maskiert_anthropic(prompt, sys_msg, self.sender, self.modell, self.frist, pruefen, strip)
                self.zaehler["anthropic"] += 1
                self._melden(dict(info, rolle=rolle, rueckfall=None))
                return text
            except Exception as e:
                if isinstance(e, SystemExit):     # Kostengrenze der Tests nicht verschlucken
                    raise
                grund = str(e) if isinstance(e, (Rueckfall, ki_maske.MaskeUnsicher)) else f"Anthropic-Ausfall ({type(e).__name__})"
                self.zaehler["rueckfall"] += 1
                self.log(f"[KI] {rolle}: Anthropic nicht verwendet — {grund} → Gemini")
                self._melden({"rolle": rolle, "anbieter": "gemini", "rueckfall": grund})
        t0 = time.time()
        text = (gemini or self.gemini_fn)(prompt, sys_msg)
        if self.anbieter == "gemini":
            self._melden({"rolle": rolle, "anbieter": "gemini", "s": round(time.time() - t0, 2), "rueckfall": None})
        return text
