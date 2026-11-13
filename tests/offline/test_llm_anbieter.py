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
check("Pflicht-Platzhalter aus dem Diktat (Datum + RH-Nummer)", len(pflicht) >= 2 and all(p in rest for p in pflicht), pflicht)

k0 = korrektur.prompt("<fehlhoer>Liste</fehlhoer>", DIKTAT)
f0 = la.fester_anfang(k0)
check("Call 0: fester Anfang bis 'Roh: ', Diktat danach", f0.endswith("\n\nRoh: ") and k0[len(f0):].startswith("Kniegelenk"))
f0a, r0, m0, p0 = la.maskieren(k0)
check("Call 0 (Claude): Diktat in <diktat>-Tags, fester Teil ohne 'Roh: '", f0a.endswith(la.KORR_KOPF) and
      r0.startswith("<diktat>\n") and r0.endswith(la.KORR_FUSS) and "Huber" not in f0a, (f0a[-80:], r0[-80:]))
check("Call 0: Pflicht = Platzhalter des Diktats", len(p0) >= 2, p0)
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
check("bekannter Name (CAS-Zuweiser) maskiert und Pflicht", "Gruber" not in rn and any(p.startswith("⟦P") for p in pn), pn)

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


def weiche(sender, anbieter="anthropic"):
    return la.Weiche(anbieter, gemini_fn=gem, sender=sender, log=logs.append, beobachter=infos.append)


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
check("Ausgang ohne Datum/Nummer/Name", "12.3.2025" not in gesendet and "4711" not in gesendet)
check("Body: fester Anfang mit cache_control, Rest ohne", b["messages"][0]["content"][0].get("cache_control") == {"type": "ephemeral"}
      and b["messages"][0]["content"][0]["text"] == fest and "cache_control" not in b["messages"][0]["content"][1])
check("Body: Nachdenken aus, kein temperature, System = SYS_MSG, Haiku 5.5",
      b["thinking"] == {"type": "disabled"} and "temperature" not in b and b["system"][0]["text"] == gemini.SYS_MSG
      and b["model"] == "claude-haiku-5-5")
check("Beobachter: Kosten aus usage inkl. Cache-Lesen", infos[-1]["anbieter"] == "anthropic"
      and abs(infos[-1]["usd"] - (900 * 0.10 + 11000 * 0.01 + 300 * 0.50) / 1e6) < 1e-12, infos[-1])


def fall(name, fn, erwartet_grund):
    gem_aufrufe.clear()
    logs.clear()
    s = Sender(fn)
    t = weiche(s)(gp, gemini.SYS_MSG, pruefen=gemini.report_complete, strip=gemini.strip_fences)
    check(f"Rückfall Gemini: {name}", t.startswith("## Kniegelenk") and "Gemini" in t and len(gem_aufrufe) == 1
          and logs and erwartet_grund in logs[-1] and "12.3" not in logs[-1], logs[-1:] if logs else "kein Log")
    return s


fall("Platzhalter fehlt", lambda b: antwort("## Knie\n\n## Befund\nVergleich ohne Datum, Text lang genug.\n\n## Ergebnis\n1. X."),
     "Platzhalter fehlt")
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
weiche(s)(gp.replace("mäßiggradige", "⟦X⟧ mäßiggradige"), gemini.SYS_MSG, pruefen=gemini.report_complete)
check("Maske unsicher → kein Anthropic-Aufruf, Gemini", not s.bodies and len(gem_aufrufe) == 1)
s = Sender(echo)
w = la.Weiche("anthropic", gemini_fn=gem, sender=la.anthropic_sender(lambda: ""), log=logs.append)
gem_aufrufe.clear()
w(gp, gemini.SYS_MSG)
check("kein Anthropic-Schlüssel → Gemini", len(gem_aufrufe) == 1 and "Schlüssel" in logs[-1])

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
kk = korrektur.korrigieren_ki(roh, weiche(s), "AQ", "")
check("Call 0 anthropic zu kurz (< 60 %) → Gemini-Korrektur", kk == "GEMINI:" + roh, kk)
s = Sender(lambda b: antwort("Bitte gib mir den Text, den du korrigiert haben möchtest, dann helfe ich gern weiter."))
kk = korrektur.korrigieren_ki(roh, weiche(s), "AQ", "")
check("Call 0 anthropic Rückfrage statt Korrektur (gleich lang) → Gemini-Korrektur", kk == "GEMINI:" + roh, kk)
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
check("config: Standard gemini, Haiku 5.5, Frist 20 s", (c.llm_anbieter, c.llm_anbieter_korrektur, c.anthropic_modell,
                                                         c.anthropic_frist) == ("gemini", "", "claude-haiku-5-5", 20))
c = cfg("[SETTINGS]\nLLM_ANBIETER = Anthropic\nLLM_ANBIETER_KORREKTUR = gemini\nANTHROPIC_MODELL = claude-sonnet-5-5\n"
        "ANTHROPIC_FRIST = 8\n")
check("config: anthropic + Korrektur gemini + Modell + Frist", (c.llm_anbieter, c.llm_anbieter_korrektur, c.anthropic_modell,
                                                                c.anthropic_frist) == ("anthropic", "gemini", "claude-sonnet-5-5", 8))
c = cfg("[SETTINGS]\nLLM_ANBIETER = chatgpt\n")
check("config: unbekannter Anbieter → gemini + Warnung", c.llm_anbieter == "gemini" and c.warnungen)
ini = (ROOT / "config.ini").read_text(encoding="utf-8")
check("mitgelieferte config.ini: LLM_ANBIETER = gemini", re.search(r"^LLM_ANBIETER = gemini$", ini, re.M) is not None)
check("Standard-config.ini (neu angelegt): LLM_ANBIETER = gemini", "LLM_ANBIETER = gemini" in config.STANDARD_INHALT)
(d / keys.PRAXIS_KEY_NAME).write_text(json.dumps({"vertex_api_key": "AQ.x", "anthropic_api_key": " sk-ant-test "}))
check("Schlüssel: anthropic_api_key aus rakscribe-praxis-key.json", keys.load_anthropic_key(str(d), str(d / "nix")) == "sk-ant-test")
check("Schlüssel: fehlt → leer", keys.load_anthropic_key(str(d / "leer"), str(d / "nix")) == "")

exe = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("EXE: Gen + Korrektur laufen über die Weiche", "KI_GEN(prompt, SYS_MSG" in exe and "korrektur=_korrektur" in exe
      and "_korr.korrigieren_ki(" in exe)
wf = (ROOT / ".github" / "workflows" / "build-exe.yml").read_text(encoding="utf-8")
check("Build: llm_anbieter + ki_maske als hidden-import", "--hidden-import=llm_anbieter" in wf and "--hidden-import=ki_maske" in wf)

print(f"\n{'❌ ' + str(fails) + ' Fehler' if fails else '✅ alle grün'}")
sys.exit(1 if fails else 0)
