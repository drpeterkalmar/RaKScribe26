"""Befund-KI-Anbieter der EXE (kaiscribe-haiku-ab-n1, 13.11.2026) — ohne Tk/Windows importierbar, Netz austauschbar.

Einstellung LLM_ANBIETER (config.ini) = anthropic (Standard seit kaiscribe-sonnet-n2, 16.11.2026: Claude Sonnet 5.5
maskiert, Peter 14.11. „go“ + „ich will nicht noch extra google zahlen“) | gemini (nur noch Rückfall bzw. von Hand). Später kann ein dritter Anbieter
(lokales Modell in der VM) dazukommen: eigener Zweig in Weiche._anbieter_aufruf, Maskierung/Rückfall bleiben gleich.

Anthropic-Weg (Peters Entscheid 03.11.2026: Claude direkt bei Anthropic NUR mit maskiertem Text)
  1. Fester Prompt-Anfang (Regeln bis vor die Vorlage bzw. vor das Diktat) geht unverändert und als Prompt-Cache
     (cache_control) hinaus — er enthält nie Patientendaten.
  2. Der Rest (Vorlage, Beispiele/Widerspruch-Block, CAS-/IB-Lab-Block, Diktat) wird mit ki_maske.Maske maskiert
     (Namen, Daten, Nummern, Adressen, E-Mail → ⟦P1⟧ …) und unabhängig nachgeprüft (restpruefung).
  3. Antwort lokal zurücksetzen. Rückfall auf Gemini (und Protokollzeile, nur Kategorie, nie der Wert), wenn:
     Maske unsicher (Merkmal im Ausgang), ein DATUM des Diktats fehlt in der Antwort, ein unbekannter/kaputter
     Platzhalter übrig bleibt, die Antwort unvollständig ist, Anthropic ausfällt oder die Frist überschreitet.
  Platzhalter-Regel (sonnet-n2, 16.11.2026): Pflicht sind nur die Daten (⟦D…⟧) des Diktats. Zuweiser-/Personennamen,
  Nummern, Adressen darf der Befund weglassen wie bei Gemini (das lässt sie selbst weg, Messung 13.11.: 0/5 bzw. 1/5) —
  sonst ginge jeder Befund mit Zuweiser im Diktat doppelt (erst Claude, dann Gemini auf Google-Kosten).

kaiscribe-ohne-gemini-n1 (Peter 23.11.2026 „no gemini please derzeit“): KI_RUECKFALL = aus (Standard) → nie mehr ein
automatischer Gemini-Aufruf. Statt Rückfall: Frist 45 s, bei Netzfehler/Zeitüberschreitung/HTTP 429/5xx/overloaded und bei
Rueckfall/MaskeUnsicher EIN zweiter Anthropic-Versuch nach kurzer Pause; geht auch der schief → OhneKi (der Aufrufer nimmt
den Diktattext ohne KI: Call 0 → Rohtext, Befund → Diktat unformatiert + rote Prüfzeile, Prüfung → entfällt).
KI_RUECKFALL = an = alter Weg (ein Versuch, dann Gemini). LLM_ANBIETER = gemini bleibt als Handschalter.

ki_maske.py ist eine KOPIE von ~/dev/ris-mods/bruecke/ki_maske.py (KaiFormat); tests/offline/test_llm_anbieter.py
prüft die Gleichheit, solange ris-mods daneben liegt.
"""
import json
import re
import socket
import time
import urllib.error
import urllib.request

import ki_maske

ANBIETER = ("gemini", "anthropic")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODELL = "claude-sonnet-5-5"   # Standard seit sonnet-n2 (vorher Haiku nur Messung)
ANTHROPIC_FRIST_S = 45          # ohne-gemini-n1: live wird im Hintergrund diktiert, der Roboter wartet (vorher 20 s → Gemini)
ZWEITVERSUCH_PAUSE_S = 2.0      # Pause vor dem einen zweiten Anthropic-Versuch
MAX_TOKENS = 4000

# $ je 1 Mio Token (Input, Cache-Lesen, Cache-Schreiben 5 min, Output) — Anthropic-Preisliste; Haiku 5.5 bis 100k Prompt.
# Cache-Schreiben 1 h = 2 × Input (statt 1,25 × für 5 min).
PREISE = {
    "claude-haiku-5-5": (0.10, 0.01, 0.125, 0.50),
    "claude-sonnet-5-5": (2.00, 0.20, 2.50, 10.00),
}

# sonnet-n2: fester Prompt-Anfang 1 Stunde im Cache (Schreiben 2 × Input statt 1,25 ×, Lesen 0,1 ×). Im Ordi liegen
# zwischen zwei Befunden oft > 5 min (Pausen, Ultraschall) — mit 5 min würde der ~11k-Token-Anfang dann jedes Mal neu
# geschrieben. Messung + Rechnung: docs/benchmarks/BERICHT-sonnet-n2.md.
CACHE = {"type": "ephemeral", "ttl": "1h"}
PFLICHT_ARTEN = "D"     # Platzhalter-Arten, die in der Antwort wiederkommen MÜSSEN (Daten), siehe Kopf

# „Nachdenken aus“ je Modell: Haiku 5.5 nimmt {"type": "disabled"}, Sonnet 5.5 lehnt das ab (HTTP 400) → between_tools
DENKEN_AUS = {"claude-sonnet-5-5": {"type": "between_tools"}}

_PH = re.compile(ki_maske.KLAMMER_AUF + r"[PDNAE]\d+" + ki_maske.KLAMMER_ZU)
_KORR_ANFANG = "Du bist ein medizinischer Lektor für radiologische Diktate"
_VAL_ANFANG = "Du bist ein radiologischer Qualitätskontrolleur"


class Rueckfall(Exception):
    """Anthropic-Antwort nicht verwendbar (→ zweiter Versuch, dann ohne KI bzw. mit KI_RUECKFALL = an Gemini).
    Text = Kategorie (ohne Patientendaten). kosten = {usage, usd, cache, fest}, wenn Anthropic schon geantwortet (und
    damit abgerechnet) hatte — die Weiche meldet das als „verworfen“ an den Zähler (kosten-je-befund-n1)."""
    kosten = None


class OhneKi(Exception):
    """ohne-gemini-n1: Anthropic auch im zweiten Versuch nicht verwendbar, KI_RUECKFALL = aus → kein Gemini. Der Aufrufer
    nimmt den Text ohne KI weiter (nie einen Befund verlieren). grund = Kategorie (ohne Werte), rolle = korr/gen/val."""

    def __init__(self, grund, rolle="gen"):
        super().__init__(grund)
        self.grund, self.rolle = grund, rolle


# Wortlaut der roten Prüfzeile (Regel-Register „ohne-ki-pruefzeile“; Web: llmAnbieter.ts OHNE_KI_ZEILE)
OHNE_KI_ZEILE = "KI nicht verfügbar – Diktat unformatiert übernommen, bitte prüfen."


class HttpFehler(Exception):
    """HTTP-Fehler von Anthropic (nur Statuscode/Typ, nie der Inhalt)."""

    def __init__(self, status, typ=""):
        super().__init__(f"Anthropic HTTP {status}" + (f" {typ}" if typ else ""))
        self.status, self.typ = status, typ


def kategorie(e):
    """Fehler → kurze Kategorie ohne Patientendaten (Log, Zähler): Frist, HTTP 429/5xx/…, Netz, Platzhalter, Maske,
    abgebrochen, unvollständig, Schlüssel, Fehlerantwort."""
    if isinstance(e, ki_maske.MaskeUnsicher):
        return "Maske unsicher"
    if isinstance(e, HttpFehler):
        return f"HTTP {e.status}" + (" overloaded" if "overloaded" in (e.typ or "") and e.status != 529 else "")
    if isinstance(e, Rueckfall):
        t = str(e)
        for wort, kat in (("Platzhalter", "Platzhalter"), ("abgebrochen", "abgebrochen"), ("unvollständig", "unvollständig"),
                          ("Schlüssel", "Schlüssel"), ("overloaded", "overloaded"), ("Fehlerantwort", "Fehlerantwort"),
                          ("Frist", "Frist")):
            if wort in t:
                return kat
        return re.sub(r"\(\d+ von \d+\)", "", t).strip()[:40] or "Rueckfall"
    if isinstance(e, (socket.timeout, TimeoutError)) or "timed out" in str(e).lower():
        return "Frist"
    if isinstance(e, urllib.error.URLError) and isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError)):
        return "Frist"
    if isinstance(e, (urllib.error.URLError, ConnectionError, OSError)):
        return "Netz"
    return f"Anthropic-Ausfall ({type(e).__name__})"


def zweiter_versuch_sinnvoll(e):
    """Ein zweiter Versuch nur bei Netzfehler/Zeitüberschreitung/HTTP 429/5xx/overloaded und Rueckfall/MaskeUnsicher —
    nicht bei fehlendem Schlüssel und nicht bei HTTP 400/401/403/404 (dieselbe Anfrage scheitert wieder)."""
    if isinstance(e, HttpFehler):
        return e.status == 429 or e.status >= 500 or "overloaded" in (e.typ or "")
    if isinstance(e, Rueckfall):
        return "Schlüssel" not in str(e)
    return True


def kosten_usd(modell, usage):
    p_in, p_cr, p_cw, p_out = PREISE.get(modell, PREISE["claude-sonnet-5-5"])
    u = usage or {}
    cw = int(u.get("cache_creation_input_tokens", 0) or 0) * p_cw
    teil = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else None
    if teil:     # Aufschlüsselung 5 min / 1 h (Antwort der API) → 1 h zum 2-fachen Input-Preis
        cw = (int(teil.get("ephemeral_5m_input_tokens", 0) or 0) * p_cw
              + int(teil.get("ephemeral_1h_input_tokens", 0) or 0) * 2 * p_in)
    return (int(u.get("input_tokens", 0) or 0) * p_in + int(u.get("cache_read_input_tokens", 0) or 0) * p_cr
            + cw + int(u.get("output_tokens", 0) or 0) * p_out) / 1e6


def fester_anfang(prompt):
    """Konstanter Prompt-Anfang ohne Patientendaten (geht unmaskiert + gecacht hinaus) oder "".
    Gen-Prompt: bis einschließlich '<normalbefund_template>\\n' — nur wenn das Diktat danach kommt.
    Call 0: bis einschließlich des letzten 'Roh: '. Validator: bis vor '<diktat>'.
    kosten-je-befund-n1: Die Marke wird auch mit CRLF gefunden (EXE-Prompt aus dem Windows-Checkout) — vorher lieferte
    der Gen-Prompt der EXE hier immer "" → nie Cache, voller Input-Preis (RaKScribe.py normalisiert jetzt zusätzlich)."""
    p = prompt or ""
    if p.startswith(_KORR_ANFANG):
        i = p.rfind("\n\nRoh: ")
        return p[:i + 7] if i > 0 else ""
    if p.startswith(_VAL_ANFANG):
        i = p.find("\n<diktat>\n")
        return p[:i + 1] if i > 0 else ""
    for marke in ("<normalbefund_template>\n", "<normalbefund_template>\r\n"):
        i = p.find(marke)
        if i > 0 and "<diktat>" not in p[:i] and "<diktat>" in p[i:]:
            return p[:i + len(marke)]
    return ""


def cache_art(usage):
    """Cache-Ergebnis eines Aufrufs aus usage: „treffer“ (Anfang aus dem Cache gelesen), „neu“ (Anfang neu geschrieben)
    oder „ohne“ (weder noch — kein fester Anfang/cache_control, voller Input-Preis)."""
    u = usage or {}
    if int(u.get("cache_read_input_tokens", 0) or 0) > 0:
        return "treffer"
    if int(u.get("cache_creation_input_tokens", 0) or 0) > 0:
        return "neu"
    return "ohne"


def _kosten_info(modell, usage, fest):
    return {"usage": usage, "usd": kosten_usd(modell, usage), "cache": cache_art(usage), "fest": bool(fest)}


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


def maskieren(prompt, namen=(), geburtsdatum=None):
    """→ (fest, maskierter Rest, Maske, Pflicht-Platzhalter). Wirft ki_maske.MaskeUnsicher.
    namen/geburtsdatum: bekannte Personendaten (z. B. Zuweiser/Befunder aus dem CAS-Auftrag) → immer ⟦P…⟧ und Restprüfung."""
    fest, rest = _anthropic_form(prompt, fester_anfang(prompt))
    m = ki_maske.Maske(namen, geburtsdatum)
    rest = m.maskieren(rest)
    m.restpruefung([rest])
    pflicht = sorted(p for p in set(_PH.findall(diktat_teil(rest))) if p[1] in PFLICHT_ARTEN)
    return fest, rest, m, pflicht


def zuruecksetzen(antwort, maske, pflicht):
    """Platzhalter zurück; Rueckfall, wenn ein Pflicht-Platzhalter (Datum) des Diktats fehlt oder ein unbekannter/kaputter
    übrig bleibt."""
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
    """Messages-Body: fester Anfang als Cache-Breakpoint (System + Anfang 1 h gecacht), Nachdenken aus, kein temperature
    (Haiku/Sonnet 5.5 lehnen temperature ab)."""
    teile = ([{"type": "text", "text": fest, "cache_control": dict(CACHE)}] if fest else []) + \
        [{"type": "text", "text": rest}]
    body = {"model": modell, "max_tokens": max_tokens, "thinking": DENKEN_AUS.get(modell, {"type": "disabled"}),
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
        try:
            with (urlopen or urllib.request.urlopen)(req, timeout=frist) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:      # nur Status + Fehlertyp weiter (z. B. 529 overloaded_error)
            typ = ""
            try:
                typ = str((json.loads(e.read() or b"{}").get("error") or {}).get("type") or "")[:40]
            except Exception:
                pass
            raise HttpFehler(e.code, typ) from None
    return senden


def maskiert_anthropic(prompt, sys_msg, sender, modell=ANTHROPIC_MODELL, frist=ANTHROPIC_FRIST_S, pruefen=None,
                       strip=None, namen=()):
    """Ein maskierter Anthropic-Aufruf → (Text, Info). Wirft Rueckfall/MaskeUnsicher/Netzfehler."""
    fest, rest, maske, pflicht = maskieren(prompt, namen)
    t0 = time.time()
    data = sender(anthropic_body(fest, rest, sys_msg, modell), frist)
    dauer = time.time() - t0
    if data.get("type") == "error" or "error" in data:
        typ = str(((data.get("error") or {}) if isinstance(data.get("error"), dict) else {}).get("type") or "")
        raise Rueckfall("Anthropic-Fehlerantwort" + (" overloaded" if "overloaded" in typ else ""))
    kosten = _kosten_info(modell, data.get("usage") or {}, fest)
    try:
        if data.get("stop_reason") not in ("end_turn", "stop_sequence"):
            raise Rueckfall(f"Antwort abgebrochen ({data.get('stop_reason')})")
        roh = anthropic_text(data)
        roh = strip(roh) if strip else roh
        text = zuruecksetzen(roh, maske, pflicht)
        if pruefen is not None and not pruefen(text):
            raise Rueckfall("Antwort unvollständig")
    except Rueckfall as e:
        e.kosten = kosten          # abgerechnet, aber verworfen → Zähler (kosten-je-befund-n1)
        raise
    return text, dict(kosten, anbieter="anthropic", modell=modell, s=round(dauer, 2), platzhalter=len(maske.zu_wert),
                      pflicht=len(pflicht), zaehlung=maske.zaehlung())


class Weiche:
    """LLM-Aufruf je Anbieter. gemini_fn(prompt, sys_msg) → Text (wirft bei Fehler) — nur für LLM_ANBIETER = gemini bzw.
    KI_RUECKFALL = an. rueckfall=False (Standard seit ohne-gemini-n1): Anthropic, bei Problemen EIN zweiter Versuch, dann
    OhneKi (nie Gemini). beobachter(info) bekommt je Aufruf {rolle, anbieter, modell, s, usage, usd, cache, fest, rueckfall,
    ohne_ki, zweitversuch, platzhalter, pflicht}; kosten-je-befund-n1: zusätzlich je verworfener, aber abgerechneter
    Anthropic-Antwort {rolle, anbieter, usage, usd, cache, fest, verworfen=<Kategorie>, zweitversuch} (vor dem Ergebnis)."""

    def __init__(self, anbieter="anthropic", modell=ANTHROPIC_MODELL, gemini_fn=None, sender=None, log=None,
                 frist=ANTHROPIC_FRIST_S, beobachter=None, rueckfall=False, pause=ZWEITVERSUCH_PAUSE_S, schlafen=None):
        self.anbieter = (anbieter or "anthropic").strip().lower()
        if self.anbieter not in ANBIETER:
            self.anbieter = "gemini"
        self.modell = modell or ANTHROPIC_MODELL
        self.gemini_fn, self.sender, self.frist = gemini_fn, sender, frist
        self.rueckfall = bool(rueckfall)
        self.pause, self.schlafen = pause, schlafen or time.sleep
        self.log = log or (lambda *a: None)
        self.beobachter = beobachter
        self.zaehler = {"anthropic": 0, "rueckfall": 0, "ohne_ki": 0, "zweitversuch": 0}
        self.namen = []          # bekannte Namen des laufenden Auftrags (CAS: Zuweiser/Befunder) → immer maskiert
        self.zuletzt = ""        # sonnet-n2: wer den letzten Text wirklich geschrieben hat (Lauf-Protokoll „modell“)

    def name(self):
        return "gemini/gemini-3.5-flash" if self.anbieter == "gemini" else f"anthropic/{self.modell}"

    def rueckfall_text(self):
        """Für die [INIT]-Zeile: „Rückfall: aus“ bzw. „Rückfall: Gemini“ (nur bei anthropic sinnvoll)."""
        return "Rückfall: Gemini" if self.rueckfall else "Rückfall: aus"

    def _melden(self, info):
        if self.beobachter:
            try:
                self.beobachter(info)
            except Exception:
                pass

    def _anthropic(self, prompt, sys_msg, pruefen, strip):
        return maskiert_anthropic(prompt, sys_msg, self.sender, self.modell, self.frist, pruefen, strip, self.namen)

    def __call__(self, prompt, sys_msg=None, pruefen=None, rolle="gen", strip=None, gemini=None):
        if self.anbieter == "anthropic" and (self.sender is not None or not self.rueckfall):
            versuche = 1 if self.rueckfall else 2
            fehler = None
            for nr in range(1, versuche + 1):
                try:
                    if self.sender is None:
                        raise Rueckfall("kein Anthropic-Schlüssel")
                    text, info = self._anthropic(prompt, sys_msg, pruefen, strip)
                    self.zaehler["anthropic"] += 1
                    if nr > 1:
                        self.zaehler["zweitversuch"] += 1
                    self.zuletzt = f"anthropic/{self.modell}"
                    self.log(f"[KI] {rolle}: Anbieter=anthropic {self.modell} maskiert ({info['s']:.1f} s, "
                             f"{info['platzhalter']} Platzhalter)" + (" — im zweiten Versuch" if nr > 1 else ""))
                    self._melden(dict(info, rolle=rolle, rueckfall=None, zweitversuch=nr > 1))
                    return text
                except Exception as e:
                    if isinstance(e, SystemExit):     # Kostengrenze der Tests nicht verschlucken
                        raise
                    fehler = e
                    if getattr(e, "kosten", None):    # Antwort kam, wurde verworfen — kostet trotzdem
                        self._melden(dict(e.kosten, rolle=rolle, anbieter="anthropic", modell=self.modell,
                                          verworfen=kategorie(e), zweitversuch=nr > 1))
                    if nr < versuche and zweiter_versuch_sinnvoll(e):
                        self.log(f"[KI] {rolle}: Anthropic-Versuch 1 nicht verwendbar — {kategorie(e)} → zweiter Versuch")
                        self.schlafen(self.pause)
                        continue
                    break
            grund = kategorie(fehler)
            if not self.rueckfall:
                self.zaehler["ohne_ki"] += 1
                self.zuletzt = "ohne KI"
                self.log(f"[KI] {rolle}: Anthropic nicht verwendet — {grund} → ohne KI (kein Rückfall)")
                self._melden({"rolle": rolle, "anbieter": "ohne_ki", "rueckfall": None, "ohne_ki": grund,
                              "zweitversuch": versuche > 1 and nr > 1})
                raise OhneKi(grund, rolle)
            grund_alt = str(fehler) if isinstance(fehler, (Rueckfall, ki_maske.MaskeUnsicher)) \
                else f"Anthropic-Ausfall ({type(fehler).__name__})" if not isinstance(fehler, HttpFehler) else grund
            self.zaehler["rueckfall"] += 1
            self.log(f"[KI] {rolle}: Anthropic nicht verwendet — {grund_alt} → Gemini (Rückfall)")
            self._melden({"rolle": rolle, "anbieter": "gemini", "rueckfall": grund_alt})
        t0 = time.time()
        text = (gemini or self.gemini_fn)(prompt, sys_msg)
        self.zuletzt = "gemini/gemini-3.5-flash" + (" (Rückfall)" if self.anbieter != "gemini" else "")
        if self.anbieter == "gemini":
            self._melden({"rolle": rolle, "anbieter": "gemini", "s": round(time.time() - t0, 2), "rueckfall": None})
        return text
