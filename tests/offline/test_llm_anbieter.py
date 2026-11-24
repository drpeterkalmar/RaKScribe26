"""Gate (kaiscribe-haiku-ab-n1): Anbieter-Weiche gemini | anthropic — Maskierung, Rückmaskierung, Rückfall auf Gemini,
Prompt-Cache-Aufbau, Einstellung in config.ini, Anthropic-Schlüssel. Ohne Netz (Sender-Attrappen).
Aufruf: python3 tests/offline/test_llm_anbieter.py"""
import json
import pathlib
import re
import socket
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import config  # noqa: E402
import gemini  # noqa: E402
import keys  # noqa: E402
import ki_maske  # noqa: E402
import korrektur  # noqa: E402
import llm_anbieter as la  # noqa: E402
import befund_regeln as br  # noqa: E402
import pipeline  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# ── ki_maske = Kopie der KaiFormat-Maske (ris-mods) ──
quelle = pathlib.Path.home() / "dev" / "ris-mods" / "bruecke" / "ki_maske.py"
if quelle.exists():
    check("ki_maske.py wortgleich zu ris-mods/bruecke/ki_maske.py",
          quelle.read_text(encoding="utf-8") == (ROOT / "source_code" / "ki_maske.py").read_text(encoding="utf-8"))
else:
    print("ℹ️  ris-mods nicht daneben — Gleichheit von ki_maske.py nicht geprüft")

# ── echter Gen-Prompt wie die EXE ──
TPL = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
PROMPT = (ROOT / "radiology_prompt.txt").read_text(encoding="utf-8")
DIKTAT = ("Kniegelenk rechts, Patient Huber, Vergleich mit der Voruntersuchung vom 12.3.2025, RH 4711, "
          "mäßiggradige Gonarthrose medial betont")
gp = pipeline.gen_prompt(DIKTAT, TPL["knie"] if "knie" in TPL else next(iter(TPL.values())), PROMPT)
fest = la.fester_anfang(gp)
check("Gen-Prompt: fester Anfang endet mit <normalbefund_template>", fest.endswith("<normalbefund_template>\n")
      and len(fest) > 30000, len(fest))
check("Gen-Prompt: fester Anfang = Prompt-Datei bis {template_body} (gleich bei jedem Diktat)",
      fest == br.strip_prompt_marker(PROMPT)[:br.strip_prompt_marker(PROMPT).index("{template_body}")])
check("Gen-Prompt: Diktat nicht im festen Anfang", "Huber" not in fest and "12.3.2025" not in fest)
f2, rest, maske, pflicht = la.maskieren(gp)
check("maskierter Rest ohne Datum/Nummer", "12.3.2025" not in rest and "4711" not in rest, rest[-300:])
check("Pflicht-Platzhalter aus dem Diktat = nur das Datum (sonnet-n2: RH-Nummer darf fehlen)",
      len(pflicht) == 1 and pflicht[0].startswith("⟦D") and all(p in rest for p in pflicht), pflicht)

k0 = korrektur.prompt("<fehlhoer>Liste</fehlhoer>", DIKTAT)
f0 = la.fester_anfang(k0)
check("Call 0: fester Anfang bis 'Roh: ', Diktat danach", f0.endswith("\n\nRoh: ") and k0[len(f0):].startswith("Kniegelenk"))
f0a, r0, m0, p0 = la.maskieren(k0)
check("Call 0 (Claude): Diktat in <diktat>-Tags, fester Teil ohne 'Roh: '", f0a.endswith(la.KORR_KOPF) and
      r0.startswith("<diktat>\n") and r0.endswith(la.KORR_FUSS) and "Huber" not in f0a, (f0a[-80:], r0[-80:]))
check("Call 0: Pflicht = Datum des Diktats", len(p0) == 1 and p0[0].startswith("⟦D"), p0)
check("Call 0: Gemini-Prompt selbst unverändert ('Roh: … Korrigiert:')", k0.rstrip().endswith("Korrigiert:"))
VAL = re.search(r"export const validationPrompt = \(rawDictation: string, generatedReport: string\): string => `(.*?)`;",
                (ROOT / "web_app" / "src" / "gemini.ts").read_text(encoding="utf-8"), re.S).group(1)
vp = VAL.replace("${rawDictation}", DIKTAT).replace("${generatedReport}", "## Knie\n## Befund\nText.\n## Ergebnis\n1. X")
fv = la.fester_anfang(vp)
check("Validator: fester Anfang endet vor <diktat>", fv and "<diktat>" not in fv and vp[len(fv):].startswith("<diktat>"))

# Vorlage mit Literatur-Jahreszahl: wird maskiert, ist aber KEIN Pflicht-Platzhalter
tj = {"body": "Gezielte Blockade nach Leitlinie 2018.", "display_name": "Ultraschall gezielte Blockade", "ergebnis": "x"}
_, rj, mj, pj = la.maskieren(pipeline.gen_prompt("Blockade rechts unauffällig", tj, PROMPT))
check("Jahreszahl der Vorlage maskiert, aber nicht Pflicht", "2018" not in rj and pj == [], pj)


_, rn, mn, pn = la.maskieren(pipeline.gen_prompt("Kniegelenk rechts, Zuweisung Gruber, unauffällig", tj, PROMPT), namen=["Gruber Anna"])
check("bekannter Name (CAS-Zuweiser) maskiert, aber nicht Pflicht (Gemini lässt Zuweiser auch weg)",
      "Gruber" not in rn and "⟦P" in rn and not pn, pn)

# ── Weiche ──
def antwort(text, stop="end_turn", usage=None):
    return {"type": "message", "stop_reason": stop, "content": [{"type": "text", "text": text}],
            "usage": usage or {"input_tokens": 900, "cache_read_input_tokens": 11000, "output_tokens": 300}}


class Sender:
    def __init__(self, fn):
        self.fn, self.bodies = fn, []

    def __call__(self, body, frist):
        self.bodies.append(body)
        return self.fn(body)


def echo(body):
    """Antwort mit allen Platzhaltern des Diktats (wie ein braves Modell)."""
    rest = body["messages"][0]["content"][-1]["text"]
    ph = re.findall(r"⟦[PDNAE]\d+⟧", la.diktat_teil(rest))
    return antwort("## Kniegelenk rechts\n\n## Befund\nVergleich mit der Voruntersuchung vom " + " ".join(ph)
                   + ". Gelenkspaltverschmälerung medial.\n\n## Ergebnis\n1. Mäßiggradige Gonarthrose rechts.")


gem_aufrufe, logs, infos = [], [], []


def gem(p, s):
    gem_aufrufe.append(p)
    return "## Kniegelenk rechts\n\n## Befund\nGemini-Befund Text lang genug.\n\n## Ergebnis\n1. Gemini."


pausen = []


def weiche(sender, anbieter="anthropic", rueckfall=False):
    """rueckfall=True = KI_RUECKFALL = an (alter Weg, Rückweg); Standard seit ohne-gemini-n1: aus."""
    return la.Weiche(anbieter, gemini_fn=gem, sender=sender, log=logs.append, beobachter=infos.append,
                     rueckfall=rueckfall, schlafen=pausen.append)


s = Sender(echo)
w = weiche(s, "gemini")
w(gp, gemini.SYS_MSG, pruefen=gemini.report_complete)
check("Standard gemini: Anthropic wird nie gerufen", not s.bodies and len(gem_aufrufe) == 1)
check("unbekannter Anbieter → gemini", la.Weiche("openai").anbieter == "gemini")

gem_aufrufe.clear()
s = Sender(echo)
t = weiche(s)(gp, gemini.SYS_MSG, pruefen=gemini.report_complete, strip=gemini.strip_fences)
b = s.bodies[0]
gesendet = json.dumps(b, ensure_ascii=False)
check("anthropic: Antwort zurückgesetzt (Datum + RH-Nummer wieder da)", "12.3.2025" in t and "4711" in t and "⟦" not in t, t)
check("anthropic: kein Gemini-Aufruf", not gem_aufrufe)
check("anthropic: Logzeile Anbieter=anthropic (ohne Inhalt), zuletzt = anthropic/Sonnet",
      any("Anbieter=anthropic claude-sonnet-5-5 maskiert" in z for z in logs) and not any("12.3" in z for z in logs),
      logs[-2:])
check("Ausgang ohne Datum/Nummer/Name", "12.3.2025" not in gesendet and "4711" not in gesendet)
check("Body: fester Anfang mit 1-h-cache_control, Rest ohne",
      b["messages"][0]["content"][0].get("cache_control") == {"type": "ephemeral", "ttl": "1h"}
      and b["messages"][0]["content"][0]["text"] == fest and "cache_control" not in b["messages"][0]["content"][1])
check("Body: Nachdenken aus, kein temperature, System = SYS_MSG, Standard Sonnet 5.5",
      b["thinking"] == {"type": "between_tools"} and "temperature" not in b and b["system"][0]["text"] == gemini.SYS_MSG
      and b["model"] == "claude-sonnet-5-5")
check("Beobachter: Kosten aus usage inkl. Cache-Lesen (Sonnet)", infos[-1]["anbieter"] == "anthropic"
      and abs(infos[-1]["usd"] - (900 * 2.00 + 11000 * 0.20 + 300 * 10.00) / 1e6) < 1e-12, infos[-1])
check("Kosten: 1-h-Cache-Schreiben = 2 × Input, 5 min = 1,25 ×",
      abs(la.kosten_usd("claude-sonnet-5-5", {"cache_creation_input_tokens": 3000, "cache_creation": {
          "ephemeral_5m_input_tokens": 1000, "ephemeral_1h_input_tokens": 2000}}) - (1000 * 2.50 + 2000 * 4.00) / 1e6) < 1e-12)
check("Weiche: Standard = anthropic", la.Weiche().anbieter == "anthropic" and la.Weiche(None).anbieter == "anthropic")


def fall(name, fn, erwartet_grund):
    """KI_RUECKFALL = an (Rückweg): alter Weg unverändert — ein Versuch, dann Gemini."""
    gem_aufrufe.clear()
    logs.clear()
    s = Sender(fn)
    t = weiche(s, rueckfall=True)(gp, gemini.SYS_MSG, pruefen=gemini.report_complete, strip=gemini.strip_fences)
    check(f"KI_RUECKFALL = an, Rückfall Gemini: {name} (ein Versuch)", len(s.bodies) <= 1 and t.startswith("## Kniegelenk") and "Gemini" in t and len(gem_aufrufe) == 1
          and logs and erwartet_grund in logs[-1] and "12.3" not in logs[-1], logs[-1:] if logs else "kein Log")
    return s


w_rf = fall("Datum fehlt", lambda b: antwort("## Knie\n\n## Befund\nVergleich ohne Datum, Text lang genug.\n\n## Ergebnis\n1. X."),
     "Platzhalter fehlt")
check("Rückfall: Logzeile endet mit (Rückfall)", logs and logs[-1].endswith("→ Gemini (Rückfall)"), logs[-1:])
gem_aufrufe.clear()
t = weiche(Sender(lambda b: antwort("## Kniegelenk rechts\n\n## Befund\nVergleich mit der Voruntersuchung vom " + " ".join(
    re.findall(r"⟦D\d+⟧", la.diktat_teil(b["messages"][0]["content"][-1]["text"])))
    + ". Gelenkspalt medial schmal.\n\n## Ergebnis\n1. Mäßiggradige Gonarthrose rechts.")))(
    gp, gemini.SYS_MSG, pruefen=gemini.report_complete, strip=gemini.strip_fences)
check("RH-Nummer fehlt in der Antwort, Datum da → Claude-Befund gilt (kein Gemini)", not gem_aufrufe and "12.3.2025" in t
      and "4711" not in t and "⟦" not in t, t)
fall("erfundener Platzhalter", lambda b: (lambda a: (a["content"][0].update(text=a["content"][0]["text"] + " ⟦D9⟧"), a)[1])(echo(b)),
     "unbekannter Platzhalter")
fall("unvollständig (kein Ergebnis)", lambda b: antwort("## Knie\n\n## Befund\n" + " ".join(
    re.findall(r"⟦[PDNAE]\d+⟧", b["messages"][0]["content"][-1]["text"]))), "unvollständig")
fall("abgeschnitten (max_tokens)", lambda b: dict(echo(b), stop_reason="max_tokens"), "abgebrochen")


def zeit(b):
    raise socket.timeout("timed out")


fall("Zeitüberschreitung", zeit, "Anthropic-Ausfall")


def http(b):
    raise OSError("HTTP 529 overloaded")


fall("Überlastung/Netz", http, "Anthropic-Ausfall")
gem_aufrufe.clear()
s = Sender(echo)
weiche(s, rueckfall=True)(gp.replace("mäßiggradige", "⟦X⟧ mäßiggradige"), gemini.SYS_MSG, pruefen=gemini.report_complete)
check("KI_RUECKFALL = an: Maske unsicher → kein Anthropic-Aufruf, Gemini", not s.bodies and len(gem_aufrufe) == 1)
s = Sender(echo)
w = la.Weiche("anthropic", gemini_fn=gem, sender=la.anthropic_sender(lambda: ""), log=logs.append, rueckfall=True)
gem_aufrufe.clear()
w(gp, gemini.SYS_MSG)
check("KI_RUECKFALL = an: kein Anthropic-Schlüssel → Gemini", len(gem_aufrufe) == 1 and "Schlüssel" in logs[-1])

# ── kaiscribe-ohne-gemini-n1: KI_RUECKFALL = aus (Standard) — nie Gemini, ein zweiter Versuch, dann ohne KI ──
def nie_gemini(p, s_):
    raise AssertionError("Gemini darf bei KI_RUECKFALL = aus nie gerufen werden")


def aus_fall(name, fn, kat, versuche=2):
    """Spion: gemini_fn und gemini= werfen, falls sie gerufen würden."""
    logs.clear()
    infos.clear()
    pausen.clear()
    s = Sender(fn)
    w = la.Weiche("anthropic", gemini_fn=nie_gemini, sender=s, log=logs.append, beobachter=infos.append, schlafen=pausen.append)
    try:
        w(gp, gemini.SYS_MSG, pruefen=gemini.report_complete, strip=gemini.strip_fences, gemini=nie_gemini)
        erg = "kein OhneKi"
    except la.OhneKi as e:
        erg = e
    check(f"KI_RUECKFALL = aus: {name} → {versuche} Versuch(e), dann OhneKi({kat}), kein Gemini",
          isinstance(erg, la.OhneKi) and erg.grund == kat and erg.rolle == "gen" and len(s.bodies) == versuche
          and len(pausen) == versuche - 1 and w.zuletzt == "ohne KI" and w.zaehler["ohne_ki"] == 1
          and logs[-1] == f"[KI] gen: Anthropic nicht verwendet — {kat} → ohne KI (kein Rückfall)"
          and infos[-1].get("ohne_ki") == kat and infos[-1].get("anbieter") == "ohne_ki"
          and not any("12.3" in z or "4711" in z for z in logs), (erg, len(s.bodies), pausen, logs[-2:], infos[-1:]))
    return s


aus_fall("Zeitüberschreitung (Frist)", zeit, "Frist")
aus_fall("Netzfehler", http, "Netz")
aus_fall("HTTP 529 overloaded", lambda b: (_ for _ in ()).throw(la.HttpFehler(529, "overloaded_error")), "HTTP 529")
aus_fall("HTTP 429", lambda b: (_ for _ in ()).throw(la.HttpFehler(429, "rate_limit_error")), "HTTP 429")
aus_fall("HTTP 400 (dieselbe Anfrage scheitert wieder)", lambda b: (_ for _ in ()).throw(la.HttpFehler(400, "invalid_request_error")),
         "HTTP 400", versuche=1)
aus_fall("Datum fehlt (Platzhalter)", lambda b: antwort("## Knie\n\n## Befund\nVergleich ohne Datum, Text lang genug.\n\n## Ergebnis\n1. X."),
         "Platzhalter")
aus_fall("abgeschnitten (max_tokens)", lambda b: dict(echo(b), stop_reason="max_tokens"), "abgebrochen")
aus_fall("unvollständig", lambda b: antwort("## Knie\n\n## Befund\n" + " ".join(
    re.findall(r"⟦[PDNAE]\d+⟧", b["messages"][0]["content"][-1]["text"]))), "unvollständig")
aus_fall("Fehlerantwort overloaded im Body", lambda b: {"type": "error", "error": {"type": "overloaded_error"}}, "overloaded")

# Frist im 1. Versuch, 2. Versuch gut → Claude-Text, gezählt als Zweitversuch
logs.clear(); infos.clear(); pausen.clear()
s2 = Sender(lambda b: zeit(b) if len(s2.bodies) == 1 else echo(b))
w2 = la.Weiche("anthropic", gemini_fn=nie_gemini, sender=s2, log=logs.append, beobachter=infos.append, schlafen=pausen.append)
t2 = w2(gp, gemini.SYS_MSG, pruefen=gemini.report_complete, strip=gemini.strip_fences, gemini=nie_gemini)
check("KI_RUECKFALL = aus: Frist → zweiter Versuch nach Pause liefert den Claude-Befund (zweitversuch gezählt)",
      "12.3.2025" in t2 and len(s2.bodies) == 2 and pausen == [la.ZWEITVERSUCH_PAUSE_S] and w2.zaehler["zweitversuch"] == 1
      and infos[-1].get("zweitversuch") is True and any("zweiter Versuch" in z for z in logs)
      and w2.zuletzt == "anthropic/claude-sonnet-5-5", (logs, infos[-1:]))

# Maske unsicher → zweiter (frischer) Versuch, dann ohne KI — Anthropic sieht den Text nie, Gemini auch nicht
logs.clear(); pausen.clear()
s3 = Sender(echo)
w3 = la.Weiche("anthropic", gemini_fn=nie_gemini, sender=s3, log=logs.append, schlafen=pausen.append)
try:
    w3(gp.replace("mäßiggradige", "⟦X⟧ mäßiggradige"), gemini.SYS_MSG, pruefen=gemini.report_complete, gemini=nie_gemini)
    e3 = None
except la.OhneKi as e:
    e3 = e
check("KI_RUECKFALL = aus: Maske unsicher → kein Anthropic-Aufruf, kein Gemini, OhneKi(Maske unsicher)",
      e3 is not None and e3.grund == "Maske unsicher" and not s3.bodies and len(pausen) == 1, (e3, logs))
w4 = la.Weiche("anthropic", gemini_fn=nie_gemini, sender=la.anthropic_sender(lambda: ""), log=logs.append, schlafen=pausen.append)
try:
    w4(gp, gemini.SYS_MSG)
    e4 = None
except la.OhneKi as e:
    e4 = e
check("KI_RUECKFALL = aus: kein Anthropic-Schlüssel → sofort ohne KI (kein zweiter Versuch, kein Gemini)",
      e4 is not None and e4.grund == "Schlüssel", e4)
w5 = la.Weiche("anthropic", gemini_fn=nie_gemini, sender=None, schlafen=pausen.append)
try:
    w5(gp, gemini.SYS_MSG)
    e5 = None
except la.OhneKi as e:
    e5 = e
check("KI_RUECKFALL = aus: Weiche ohne Sender → ohne KI statt Gemini", e5 is not None)
gem_aufrufe.clear()
t6 = la.Weiche("gemini", gemini_fn=gem, sender=Sender(echo))(gp, gemini.SYS_MSG)
check("Handschalter LLM_ANBIETER = gemini wirkt weiter (auch bei KI_RUECKFALL = aus)", "Gemini" in t6 and len(gem_aufrufe) == 1)
check("Weiche Standard: KI_RUECKFALL aus, Frist 45 s", la.Weiche().rueckfall is False and la.Weiche().frist == 45
      and la.ANTHROPIC_FRIST_S == 45)

# Produktions-Sender: HTTPError → HttpFehler (nur Status + Typ, nie Inhalt)
import io  # noqa: E402
import urllib.error  # noqa: E402


def http_fehler(req, timeout=None):
    raise urllib.error.HTTPError(req.full_url, 529, "Overloaded", {}, io.BytesIO(b'{"type":"error","error":{"type":"overloaded_error"}}'))


try:
    la.anthropic_sender(lambda: "sk", urlopen=http_fehler)({"x": 1}, 5)
    hf = None
except la.HttpFehler as e:
    hf = e
check("anthropic_sender: HTTP 529 → HttpFehler(529, overloaded_error), zweiter Versuch sinnvoll",
      hf is not None and hf.status == 529 and hf.typ == "overloaded_error" and la.zweiter_versuch_sinnvoll(hf)
      and not la.zweiter_versuch_sinnvoll(la.HttpFehler(401)), hf)
check("Kategorie: URLError(timeout) = Frist", la.kategorie(urllib.error.URLError(socket.timeout("timed out"))) == "Frist")

# Pipeline: Befund ohne KI → Diktat unverändert + rote Prüfzeile, nichts verloren, nicht „vollständig“ (kein Einfügen)
CTX = dict(templates=TPL, display_names=[], prompt=PROMPT, log=lambda *a: None)


def llm_ohne(p):
    raise la.OhneKi("Frist")


d1 = "Kniegelenk rechts, Erguss im Recessus suprapatellaris, mäßiggradige Gonarthrose medial betont"
e1 = pipeline.befund_aus_diktat(d1, pipeline.Kontext(llm=llm_ohne, **CTX))
check("Pipeline ohne KI: Befund = Diktat unverändert, rote Prüfzeile (Wortlaut Register), nicht vollständig",
      e1.report == d1 and e1.ohne_ki == "Frist" and e1.cas_hinweise[:1] == [la.OHNE_KI_ZEILE] and not e1.vollstaendig
      and "bitte prüfen" in la.OHNE_KI_ZEILE, (e1.report, e1.cas_hinweise))
d2 = "Schulter rechts: Tendinopathie der Supraspinatussehne. Kniegelenk links: Erguss, mäßiggradige Gonarthrose."
e2 = pipeline.befund_aus_diktat(d2, pipeline.Kontext(llm=llm_ohne, **CTX))
check("Pipeline ohne KI, mehrere Regionen: ganzes Diktat unverändert + Prüfzeile", e2.report == d2 and e2.ohne_ki
      and e2.cas_hinweise[:1] == [la.OHNE_KI_ZEILE], (e2.report, e2.cas_hinweise))
e3n = pipeline.befund_aus_diktat("Kniegelenk rechts unauffällig", pipeline.Kontext(llm=llm_ohne, **CTX))
check("Normalbefund (Bypass ohne KI) unberührt", not e3n.ohne_ki and e3n.vollstaendig, e3n.report)

# ── Call 0 über die Weiche ──
roh = "Kniegelenk rechts Voruntersuchung vom 12.3.2025 mäßiggradige Gonarthrose medial betont"


def korr_echo(b):
    rest = b["messages"][0]["content"][-1]["text"]
    return antwort(la.diktat_teil(rest).strip().replace("mäßiggradige", "Mäßiggradige"))


s = Sender(korr_echo)
kk = korrektur.korrigieren_ki(roh, weiche(s), "AQ", "")
check("Call 0 anthropic: korrigiert + Datum zurück", "12.3.2025" in kk and "Mäßiggradige" in kk and s.bodies, kk)
alt = korrektur.korrigieren
korrektur.korrigieren = lambda r, k, blk="", log=None, **kw: "GEMINI:" + r
s = Sender(lambda b: antwort("kurz ⟦D1⟧"))
kk = korrektur.korrigieren_ki(roh, weiche(s, rueckfall=True), "AQ", "")
check("KI_RUECKFALL = an: Call 0 anthropic zu kurz (< 60 %) → Gemini-Korrektur", kk == "GEMINI:" + roh, kk)
s = Sender(lambda b: antwort("Bitte gib mir den Text, den du korrigiert haben möchtest, dann helfe ich gern weiter."))
kk = korrektur.korrigieren_ki(roh, weiche(s, rueckfall=True), "AQ", "")
check("KI_RUECKFALL = an: Call 0 Rückfrage statt Korrektur (gleich lang) → Gemini-Korrektur", kk == "GEMINI:" + roh, kk)
# ohne-gemini-n1 (Standard aus): Call 0 zweimal unbrauchbar → Rohtext, Gemini-Korrektur nie gerufen (Spion)
s = Sender(lambda b: antwort("Bitte gib mir den Text, den du korrigiert haben möchtest, dann helfe ich gern weiter."))
logs.clear()
kk = korrektur.korrigieren_ki(roh, weiche(s), "AQ", "", log=logs.append)
check("KI_RUECKFALL = aus: Call 0 zweimal Rückfrage → Rohtext, 2 Anthropic-Versuche, keine Gemini-Korrektur",
      kk == roh and len(s.bodies) == 2 and any("ohne KI (kein Rückfall)" in z for z in logs), (kk, len(s.bodies), logs))
s = Sender(lambda b: (_ for _ in ()).throw(socket.timeout("timed out")) if len(s.bodies) == 1 else korr_echo(b))
kk = korrektur.korrigieren_ki(roh, weiche(s), "AQ", "")
check("KI_RUECKFALL = aus: Call 0 Frist im 1. Versuch → 2. Versuch korrigiert", "Mäßiggradige" in kk and len(s.bodies) == 2, kk)
check("korrektur_plausibel: Rückfrage nein, Korrektur ja", not la.korrektur_plausibel(roh, "Bitte gib mir den Text, den "
      "du korrigiert haben möchtest, dann helfe ich gern weiter.") and la.korrektur_plausibel(roh, roh.replace("mäßig", "Mäßig")))
kk = korrektur.korrigieren_ki(roh, weiche(Sender(echo), "gemini"), "AQ", "")
check("Call 0 gemini → unverändert korrigieren()", kk == "GEMINI:" + roh)
korrektur.korrigieren = alt

# ── config.ini + Schlüssel ──
d = pathlib.Path(tempfile.mkdtemp(prefix="rks_anb_"))


def cfg(text):
    p = d / "config.ini"
    p.write_text(text, encoding="utf-8")
    return config.load_config(str(p))


c = cfg("[SETTINGS]\nLLM_PROVIDER = gemini\n")
check("config: Standard anthropic, Sonnet 5.5, Frist 45 s, KI_RUECKFALL aus (ohne-gemini-n1)", (c.llm_anbieter,
      c.llm_anbieter_korrektur, c.anthropic_modell, c.anthropic_frist, c.ki_rueckfall)
      == ("anthropic", "", "claude-sonnet-5-5", 45, False))
c = cfg("[SETTINGS]\nANTHROPIC_FRIST = 20\n")
check("config: alte Standardzeile ANTHROPIC_FRIST = 20 der Ordi-PCs → 45 s", c.anthropic_frist == 45, c.anthropic_frist)
c = cfg("[SETTINGS]\nKI_RUECKFALL = an\nANTHROPIC_FRIST = 30\n")
check("config: KI_RUECKFALL = an (Rückweg) + eigene Frist", c.ki_rueckfall is True and c.anthropic_frist == 30)
c = cfg("[SETTINGS]\nKI_RUECKFALL = vielleicht\n")
check("config: KI_RUECKFALL unbekannt → aus + Warnung", c.ki_rueckfall is False and c.warnungen)
c = cfg("[SETTINGS]\nLLM_ANBIETER = gemini\n")
check("config: LLM_ANBIETER = gemini schaltet von Hand zurück", c.llm_anbieter == "gemini")
c = cfg("[SETTINGS]\nLLM_ANBIETER = Anthropic\nLLM_ANBIETER_KORREKTUR = gemini\nANTHROPIC_MODELL = claude-sonnet-5-5\n"
        "ANTHROPIC_FRIST = 8\n")
check("config: anthropic + Korrektur gemini + Modell + Frist", (c.llm_anbieter, c.llm_anbieter_korrektur, c.anthropic_modell,
                                                                c.anthropic_frist) == ("anthropic", "gemini", "claude-sonnet-5-5", 8))
c = cfg("[SETTINGS]\nLLM_ANBIETER = chatgpt\n")
check("config: unbekannter Anbieter → gemini + Warnung", c.llm_anbieter == "gemini" and c.warnungen)
ini = (ROOT / "config.ini").read_text(encoding="utf-8")
check("mitgelieferte config.ini: LLM_ANBIETER = anthropic, Sonnet", re.search(r"^LLM_ANBIETER = anthropic$", ini, re.M)
      is not None and re.search(r"^ANTHROPIC_MODELL = claude-sonnet-5-5$", ini, re.M) is not None)
check("Standard-config.ini (neu angelegt): LLM_ANBIETER = anthropic", "LLM_ANBIETER = anthropic\n" in config.STANDARD_INHALT
      and "ANTHROPIC_MODELL = claude-sonnet-5-5" in config.STANDARD_INHALT)
c = cfg(config.STANDARD_INHALT)
check("Standard-config.ini liest sich als anthropic/Sonnet, Rückfall aus, 45 s", (c.llm_anbieter, c.anthropic_modell,
      c.ki_rueckfall, c.anthropic_frist) == ("anthropic", "claude-sonnet-5-5", False, 45))
check("mitgelieferte config.ini: KI_RUECKFALL = aus, ANTHROPIC_FRIST = 45", re.search(r"^KI_RUECKFALL = aus$", ini, re.M)
      is not None and re.search(r"^ANTHROPIC_FRIST = 45$", ini, re.M) is not None)
(d / keys.PRAXIS_KEY_NAME).write_text(json.dumps({"vertex_api_key": "AQ.x", "anthropic_api_key": " sk-ant-test "}))
check("Schlüssel: anthropic_api_key aus rakscribe-praxis-key.json", keys.load_anthropic_key(str(d), str(d / "nix")) == "sk-ant-test")
check("Schlüssel: fehlt → leer", keys.load_anthropic_key(str(d / "leer"), str(d / "nix")) == "")

exe = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE: Gen + Korrektur laufen über die Weiche", "KI_GEN(prompt, SYS_MSG" in exe and "korrektur=_korrektur" in exe
      and "_korr.korrigieren_ki(" in exe)
wf = (ROOT / ".github" / "workflows" / "build-exe.yml").read_text(encoding="utf-8")
check("Build: llm_anbieter + ki_maske + nutzung als hidden-import", "--hidden-import=llm_anbieter" in wf
      and "--hidden-import=ki_maske" in wf and "--hidden-import=nutzung" in wf)
check("EXE: Weiche mit KI_RUECKFALL aus config.ini, [INIT] zeigt „Rückfall: aus“", "rueckfall=CFG.ki_rueckfall" in exe
      and "KI_GEN.rueckfall_text()" in exe and la.Weiche().rueckfall_text() == "Rückfall: aus")
check("EXE: Befund ohne KI → kein Einfügen, rote Prüfzeile, Restructure ohne KI behält den Text",
      "if erg.ohne_ki:" in exe and "_la.OHNE_KI_ZEILE" in exe and "isinstance(e, _la.OhneKi)" in exe)
check("EXE: Weiche meldet an den Nutzungszähler, Chirp zählt Sekunden", "NUTZUNG.ki(info)" in exe and "_stt.ZAEHLER = NUTZUNG.stt" in exe)

print(f"\n{'❌ ' + str(fails) + ' Fehler' if fails else '✅ alle grün'}")
sys.exit(1 if fails else 0)
