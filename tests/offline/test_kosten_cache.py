"""Gate (kaiscribe-kosten-je-befund-n1, 25.11.2026): Prompt-Cache auch im Windows-Bau + Token-Zähler.

Ursache der ~5–7 ct je Befund statt ~1,4 ct: Die EXE bündelt radiology_prompt.txt mit CRLF (Windows-Checkout,
.gitattributes „* text=auto“; belegt an X:\\RaKScribe\\rakscribe26.exe mit tools/vm/exe_prompt_zeilenenden.py). Dann fand
llm_anbieter.fester_anfang die Marke „<normalbefund_template>\\n“ nicht → kein cache_control → voller Input-Preis.
Geprüft: (1) Laden normalisiert auf LF und der feste Anfang ist dann bytegleich zum getesteten LF-Weg, (2) fester_anfang
findet die Marke auch mit CRLF, (3) .gitattributes hält den Prompt auf LF, (4) Zähler speichert Token/Cache-Art/
verworfene Antworten (nur Zahlen), Tagesbericht und VM-Leser zeigen sie.
Aufruf: python3 tests/offline/test_kosten_cache.py"""
import datetime
import importlib.util
import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source_code"))
import befund_regeln as br  # noqa: E402
import gemini  # noqa: E402
import llm_anbieter as la  # noqa: E402
import nutzung  # noqa: E402
import pipeline  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else str(detail)[:300])
    fails += (not ok)


LF = (ROOT / "radiology_prompt.txt").read_bytes().decode("utf-8")
CRLF = LF.replace("\n", "\r\n")
TPL = json.loads((ROOT / "templates.json").read_text(encoding="utf-8"))
DIKTAT = "Kniegelenk rechts, Vergleich vom 12.3.2025, mäßiggradige Gonarthrose medial."

check("Repo-Prompt hat LF (Ausgang aller Tests)", "\r" not in LF)

# (1) Laden wie RaKScribe.load_prompt_template: eingebaut (CRLF aus dem Bundle) bzw. lokale Datei mit CRLF
for name, (builtin, lokale) in {"eingebaut CRLF": (CRLF, []), "lokal CRLF gewinnt": (LF, [("radiology_prompt_v4.txt", CRLF)]),
                                "nur lokal CRLF (Entwicklung)": ("", [("radiology_prompt.txt", CRLF)])}.items():
    text, quelle, _ = br.waehle_prompt(builtin, lokale)
    check(f"waehle_prompt {name} → LF, Wortlaut gleich", text == LF, (quelle, text.count("\r")))
check("prompt_normalisieren: CRLF und einzelnes CR → LF, LF bleibt", br.prompt_normalisieren("a\r\nb\rc\nd") == "a\nb\nc\nd"
      and br.prompt_normalisieren(LF) == LF and br.prompt_normalisieren(None) == "")
src = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
check("RaKScribe.py lädt über waehle_prompt und normalisiert den Prompt-Editor",
      "br.waehle_prompt(builtin, lokale)" in src and 'br.prompt_normalisieren(txt.get("1.0", "end-1c"))' in src)

# fester Anfang: für alle Vorlagen gleich (ein Cache-Schlüssel), nach dem Laden bytegleich zum LF-Weg
geladen = br.waehle_prompt(CRLF, [])[0]
anf_lf, anf_exe = set(), set()
for key in list(TPL)[:25] + ["allgemein"]:
    anf_lf.add(la.fester_anfang(pipeline.gen_prompt(DIKTAT, TPL[key], LF)))
    anf_exe.add(la.fester_anfang(pipeline.gen_prompt(DIKTAT, TPL[key], geladen, "<stt_hinweise>x</stt_hinweise>",
                                                     "<widersprueche>y</widersprueche>", "<cas_untersuchungen>z</cas_untersuchungen>",
                                                     "<ibl_messwerte>w</ibl_messwerte>")))
check("fester Anfang: 26 Vorlagen + Blöcke → genau EIN Anfang, nicht leer, = LF-Weg", len(anf_lf) == 1 and anf_lf == anf_exe
      and len(next(iter(anf_lf))) > 40000, (len(anf_lf), len(anf_exe)))
fest = next(iter(anf_lf))
check("fester Anfang ohne Diktat/Vorlage (nur Regeln)", "12.3.2025" not in fest and "{template_body}" not in fest
      and fest.endswith("<normalbefund_template>\n"))

# (2) fester_anfang direkt mit CRLF-Prompt (falls ein Weg das Laden umgeht)
g_crlf = pipeline.gen_prompt(DIKTAT, TPL["allgemein"], CRLF)
f_crlf = la.fester_anfang(g_crlf)
check("fester_anfang findet die Marke auch mit CRLF", f_crlf.endswith("<normalbefund_template>\r\n") and len(f_crlf) > 40000)
fest_m, rest_m, _m, pflicht = la.maskieren(g_crlf)
check("CRLF-Weg: Regeln gecacht, Diktat maskiert, Datum Pflicht", fest_m == f_crlf and "12.3.2025" not in rest_m
      and len(pflicht) == 1)

# Body des EXE-Wegs: cache_control am festen Anfang
gesendet = []


def sender(body, frist):
    gesendet.append(body)
    rest = body["messages"][0]["content"][-1]["text"]
    ph = " ".join(re.findall(r"⟦[PDNAE]\d+⟧", la.diktat_teil(rest)))
    return {"type": "message", "stop_reason": "end_turn", "content": [{"type": "text", "text":
            "## Kniegelenk rechts\n\n## Befund\nVergleich vom " + ph + ". Mäßige Gelenkspaltverschmälerung medial.\n\n"
            "## Ergebnis\n1. Mäßiggradige Gonarthrose rechts."}],
            "usage": {"input_tokens": 1500, "cache_read_input_tokens": 29203, "output_tokens": 400}}


infos, logs = [], []
w = la.Weiche("anthropic", sender=sender, log=logs.append, beobachter=infos.append, schlafen=lambda s: None)
w(pipeline.gen_prompt(DIKTAT, TPL["allgemein"], geladen), gemini.SYS_MSG, pruefen=gemini.report_complete, rolle="gen")
teile = gesendet[-1]["messages"][0]["content"]
check("EXE-Weg (geladen aus CRLF): cache_control 1 h am festen Anfang", len(teile) == 2 and teile[0].get("cache_control")
      == {"type": "ephemeral", "ttl": "1h"} and teile[0]["text"] == fest)
check("Info: cache=treffer, fest=True, Kosten mit Cache-Lesen",
      infos[-1].get("cache") == "treffer" and infos[-1].get("fest") is True
      and abs(infos[-1]["usd"] - (1500 * 2 + 29203 * 0.2 + 400 * 10) / 1e6) < 1e-12, infos[-1])
check("Logzeile [KI] gen nennt den Cache-Status (Abnahme-Beleg im rakscribe.log)",
      any("maskiert (" in z and "Cache treffer)" in z for z in logs), logs)
check("cache_art: treffer/neu/ohne", la.cache_art({"cache_read_input_tokens": 5}) == "treffer"
      and la.cache_art({"cache_creation_input_tokens": 5}) == "neu" and la.cache_art({"input_tokens": 9}) == "ohne"
      and la.cache_art(None) == "ohne")

# (3) .gitattributes
ga = (ROOT / ".gitattributes").read_text(encoding="utf-8")
check(".gitattributes: radiology_prompt.txt eol=lf", re.search(r"^radiology_prompt\.txt\s+text\s+eol=lf\s*$", ga, re.M))

# (4) Zähler: Token, Cache-Art, verworfene (abgerechnete) Antworten
d = tempfile.mkdtemp(prefix="rks_kosten_")
T = datetime.datetime(2026, 11, 26, 9, 0)
z = nutzung.Zaehler(d, "CASWS08", jetzt=lambda: T)
n = {"i": 0}


def sender2(body, frist):
    """1. Antwort ohne das Datum (→ verworfen, aber abgerechnet, Cache neu), 2. ok (Cache-Treffer)."""
    n["i"] += 1
    rest = body["messages"][0]["content"][-1]["text"]
    ph = " ".join(re.findall(r"⟦[PDNAE]\d+⟧", la.diktat_teil(rest))) if n["i"] > 1 else ""
    u = ({"input_tokens": 1500, "cache_creation_input_tokens": 29203, "output_tokens": 300,
          "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 29203}} if n["i"] == 1 else
         {"input_tokens": 1500, "cache_read_input_tokens": 29203, "output_tokens": 400})
    return {"type": "message", "stop_reason": "end_turn", "usage": u, "content": [{"type": "text", "text":
            "## Kniegelenk rechts\n\n## Befund\nVergleich vom " + ph + ". Mäßige Gelenkspaltverschmälerung medial.\n\n"
            "## Ergebnis\n1. Mäßiggradige Gonarthrose rechts."}]}


infos2 = []
w2 = la.Weiche("anthropic", sender=sender2, log=lambda *a: None, schlafen=lambda s: None,
               beobachter=lambda i: (infos2.append(i), z.ki(i)))
w2(pipeline.gen_prompt(DIKTAT, TPL["allgemein"], geladen), gemini.SYS_MSG, pruefen=gemini.report_complete, rolle="gen")
check("Weiche meldet die verworfene Antwort (Kategorie, Kosten) vor dem Ergebnis",
      len(infos2) == 2 and infos2[0].get("verworfen") == "Platzhalter" and infos2[0]["usd"] > 0.1
      and infos2[1].get("zweitversuch") is True and not infos2[1].get("verworfen"), infos2)
z.ki({"rolle": "gen", "anbieter": "anthropic", "usage": {"input_tokens": 30000, "output_tokens": 500}, "usd": 0.065})
roh = json.loads(pathlib.Path(d, "2026-11_CASWS08.json").read_text(encoding="utf-8"))
td = roh["tage"]["2026-11-26"]
check("Zähler: Token-Summen je Tag (Input, Cache lesen, schreiben 1h/5m, Output)",
      td["token"] == {"input": 33000, "cache_lesen": 29203, "cache_schreiben_5m": 0, "cache_schreiben_1h": 29203,
                      "output": 1200}, td.get("token"))
check("Zähler: Cache-Art je Antwort (treffer/neu/ohne)", td["cache"] == {"neu": 1, "treffer": 1, "ohne": 1}, td.get("cache"))
check("Zähler: verworfen zählt in $, nicht als Aufruf/Befund", td["ki"].get("verworfen") == 1 and td["ki"]["anthropic"] == 2
      and td["befunde"] == 2 and abs(td["anthropic_usd"] - (infos2[0]["usd"] + infos2[1]["usd"] + 0.065)) < 1e-6, td)
check("Zähler: Cache-Schreiben ohne Aufschlüsselung zählt als 1h",
      (lambda t: nutzung._token_zaehlen(t, {"cache_creation_input_tokens": 7}) or t["token"]["cache_schreiben_1h"] == 7)({}))
alles = json.dumps(roh, ensure_ascii=False)
check("Zählerdatei ohne Diktat/Datum/Text", "12.3.2025" not in alles and "Gonarthrose" not in alles and "Knie" not in alles)
text, _w = nutzung.tagesbericht(d, "2026-11-26")
zeile = next((x for x in text.splitlines() if x.startswith("Claude-Token heute")), "")
check("Tagesbericht: Zeile Claude-Token mit Cache-Treffer/neu/ohne, verworfen, ct je Aufruf",
      "Input 33000" in zeile and "Cache lesen 29203" in zeile and "Cache schreiben 1h 29203" in zeile
      and "Cache-Treffer 1, neu 1, ohne 1" in zeile and "verworfen 1" in zeile and "ct je Aufruf" in zeile
      and "Monat: Cache-Treffer 1" in zeile, zeile)
check("Tagesbericht: alte Tage ohne Token-Felder gehen weiter", nutzung._summe({"2026-11-20": {"ki": {"anthropic": 3}}})["token"]["input"] == 0)

spec = importlib.util.spec_from_file_location("kl", ROOT / "tools" / "vm" / "kaiscribe_nutzung_lesen.py")
kl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kl)
import contextlib  # noqa: E402
import io  # noqa: E402
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    kl.nutzung(d, ["2026-11-26"])
nz = next((x for x in buf.getvalue().splitlines() if x.startswith("NUTZUNG ")), "")
felder = dict(x.split("=", 1) for x in nz.split() if "=" in x)
check("VM-Leser: NUTZUNG-Zeile mit Token/Cache/verworfen (key=wert, ohne Leerzeichen)",
      felder.get("tok_in") == "33000" and felder.get("tok_cache_lesen") == "29203" and felder.get("tok_cache_1h") == "29203"
      and felder.get("cache_ohne") == "1" and felder.get("verworfen") == "1" and felder.get("befunde") == "2", nz)

print(f"\n{'✅ alle grün' if not fails else f'❌ {fails} rot'}")
sys.exit(1 if fails else 0)
