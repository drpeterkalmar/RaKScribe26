"""Gate (kaiscribe-testkosten-n1, 13.11.2026): Live-Testskripte laufen NUR über tools/testkosten.py — Testprojekt statt
Produktion, Kostenbuch je Job, harte Obergrenze, Wiederholungen ≤ 5 ohne --release, Gemini Pro/Carbon als Gutachter
gesperrt, Kontext-Cache für den festen Gen-Prompt. Ohne Netz. Aufruf: /usr/bin/python3 tests/offline/test_testkosten.py"""
import json, os, pathlib, re, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "source_code")]
TMP = tempfile.mkdtemp(prefix="testkosten_")
os.environ.update({"KAISCRIBE_TEST_LOGDIR": TMP, "KAISCRIBE_TEST_JOB": "offline-gate", "KAISCRIBE_TEST_LIMIT_USD": "1"})
os.environ.pop("KAISCRIBE_TEST_RELEASE", None)
import testkosten as tk  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


# 1) Kein Testskript nutzt mehr Produktionszugänge (Ausnahme: E2E von Web-App/EXE selbst — die brauchen die echte App
#    mit Praxis-Schlüssel und laufen nur am Mac/Windows-CI)
VERBOTEN = re.compile(r"vertex-sa-key\.json|projects/rakscribe/|projects/895690562186|VERTEX_API_KEY|STT_KEY|PRAXIS_KEY"
                      r"|x-goog-api-key")
AUSNAHMEN = {"testkosten.py", "e2e_v3_web.py", "e2e_einfuegen_web.py", "e2e_befund_aus_text_web.py",
             "e2e_speechmike_web.py", "exe_ui_smoke.py", "exe_speechmike_smoke.py"}
treffer = []
for f in sorted((ROOT / "tools").rglob("*.py")):
    if f.name in AUSNAHMEN or "buero" in f.parts:
        continue
    for i, z in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if VERBOTEN.search(z) and "kaiscribe-testkosten-n1" not in z and "Praxis-Schlüssel" not in z:
            treffer.append(f"{f.name}:{i}")
check("kein Testskript mit Praxis-Schlüssel / vertex-sa-key / Projekt rakscribe", not treffer, ", ".join(treffer[:12]))
roh = re.compile(r"urllib\.request\.urlopen|requests\.post")
gemini_direkt = [f.name for f in (ROOT / "tools").glob("*.py") if f.name not in AUSNAHMEN
                 and "generateContent" in f.read_text(encoding="utf-8") and roh.search(f.read_text(encoding="utf-8"))
                 and "testkosten.buche_vertex" not in f.read_text(encoding="utf-8")]
check("Gemini-REST nur über testkosten (oder mit testkosten.buche_vertex)", not gemini_direkt, str(gemini_direkt))

# 2) Kosten aus usageMetadata (Gemini 3.5 Flash eu: 1,65 / 0,165 / 9,90 $ je Mio)
usd, tin, tc, tout = tk.kosten_gemini("gemini-3.5-flash", "eu", {"promptTokenCount": 12800, "cachedContentTokenCount": 11800,
                                                              "candidatesTokenCount": 200})
check("Kosten mit Cache: 1.000×1,65 + 11.800×0,165 + 200×9,90 (je Mio)",
      abs(usd - (1000 * 1.65 + 11800 * 0.165 + 200 * 9.90) / 1e6) < 1e-12 and (tin, tc, tout) == (12800, 11800, 200), usd)
usd2 = tk.kosten_gemini("gemini-3.5-flash", "eu", {"promptTokenCount": 12800, "candidatesTokenCount": 200,
                                                   "thoughtsTokenCount": 100})[0]
check("Thinking-Token zählen als Output", abs(usd2 - (12800 * 1.65 + 300 * 9.90) / 1e6) < 1e-12)
check("unbekanntes Modell → vorsichtig hoher Preis", tk.preis("gemini-9-xyz", "eu") == tk.PREIS_UNBEKANNT)
ua = tk.kosten_anthropic("claude-sonnet-5-5", {"input_tokens": 1000, "output_tokens": 500, "cache_read_input_tokens": 4000})[0]
check("Sonnet 5.5: 2 $/10 $, Cache-Lesen 0,20 $", abs(ua - (1000 * 2 + 4000 * 0.2 + 500 * 10) / 1e6) < 1e-12, ua)

# 3) Wiederholungen
check("ohne --release: 20 → 5", tk.laeufe(20, 1) == 5)
check("ohne --release: Standard bleibt", tk.laeufe(None, 3) == 3)
tk.RELEASE = True
check("--release: 20 erlaubt, 50 → 20, Standard des Skripts bleibt",
      tk.laeufe(20) == 20 and tk.laeufe(50) == 20 and tk.laeufe(None, 3) == 3)
tk.RELEASE = False

# 4) Kostenbuch + harte Grenze
tk.BUCH.buchen("gemini", "gemini-3.5-flash", 0.97, 1, 0, 1)
check("Kostenbuch je Job (JSONL) summiert", abs(tk.job_summe() - 0.97) < 1e-9 and tk.BUCH.pfad.name == "offline-gate.jsonl")
try:
    tk.BUCH.pruefen(0.02)
    check("unter der Grenze kein Abbruch", True)
except SystemExit:
    check("unter der Grenze kein Abbruch", False)
tk.BUCH.buchen("gemini", "gemini-3.5-flash", 0.05, 1, 0, 1)
try:
    tk.BUCH.pruefen(0.0)
    check("über der Grenze → Abbruch", False)
except tk.KostenGrenze as e:
    check("über der Grenze → KostenGrenze (SystemExit 7, kein `except Exception` verschluckt sie)",
          e.code == 7 and not isinstance(e, Exception))

os.environ["KAISCRIBE_TEST_LIMIT_USD"] = "100"
os.environ["KAISCRIBE_TEST_TAG_USD"] = "1.0"
tk.BUCH.gemeldet = False
try:
    tk.BUCH.pruefen(0.0)
    check("Tagesgrenze über alle Jobs", False)
except tk.KostenGrenze:
    check("Tagesgrenze über alle Jobs greift (KAISCRIBE_TEST_TAG_USD)", abs(tk.BUCH.summe_tag() - 1.02) < 1e-9)
os.environ["KAISCRIBE_TEST_TAG_USD"] = "1000"

# 5) Gutachter-Sperre: Gemini Pro/Carbon nicht in Tests
try:
    tk.gemini_roh("x", modell="gemini-3.1-pro-preview", ort="global")
    check("Gemini 3.1 Pro gesperrt", False)
except tk.KostenGrenze:
    check("Gemini 3.1 Pro / 4 Carbon als Gutachter gesperrt → testkosten.sonnet", True)

# 6) Kontext-Cache: Gen-Prompt beginnt mit dem angemeldeten festen Anfang; Anfrage = cachedContent + Rest
os.environ["KAISCRIBE_TEST_LIMIT_USD"] = "100"
import prod_pipeline as pp  # noqa: E402
p = pp.gen_prompt("Kniegelenk links. Mäßige Gelenkspaltverschmälerung medial, im Übrigen unauffällig.")
check("Gen-Prompt (EXE) beginnt mit GEN_PRAEFIX", p.startswith(pp.GEN_PRAEFIX) and len(pp.GEN_PRAEFIX) > 30000)
check("Gen-Prompt (Web, ohne Hinweise) ebenso", pp.gen_prompt("Schulter rechts, Omarthrose.", hints=False).startswith(pp.GEN_PRAEFIX))
gesendet = []
tk._token = lambda: "TOKEN"
tk._AUTH["projekt"] = "rakscribe-test"
tk._cache_name = lambda modell, ort, praefix, system, neu=False: "projects/rakscribe-test/locations/eu/cachedContents/1"


def fake_post(url, body, methode="POST", timeout=120):
    gesendet.append((url, body))
    return {"candidates": [{"content": {"parts": [{"text": "## Befund\nx"}]}}],
            "usageMetadata": {"promptTokenCount": 12800, "cachedContentTokenCount": 11800, "candidatesTokenCount": 150}}


tk._post = fake_post
vorher = tk.job_summe()
txt = tk.gemini(p, system=pp.SYS_MSG)
url, body = gesendet[-1]
check("Aufruf geht ans Testprojekt (eu, gemini-3.5-flash)", "/projects/rakscribe-test/locations/eu/" in url
      and "gemini-3.5-flash:generateContent" in url, url)
check("Anfrage: cachedContent + nur der variable Rest, thinkingBudget 0",
      body.get("cachedContent", "").endswith("/cachedContents/1") and "systemInstruction" not in body
      and body["contents"][0]["parts"][0]["text"] == p[len(pp.GEN_PRAEFIX):]
      and body["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}, json.dumps(body)[:200])
check("Aufruf gebucht", tk.job_summe() > vorher and txt == "## Befund\nx")
os.environ["KAISCRIBE_TEST_CACHE"] = "0"
tk.gemini(p, system=pp.SYS_MSG)
body = gesendet[-1][1]
check("KAISCRIBE_TEST_CACHE=0 → bit-gleiche Anfrage wie die Produktion (gemini.request_body)",
      "cachedContent" not in body and body["contents"][0]["parts"][0]["text"] == p
      and body["systemInstruction"]["parts"][0]["text"] == pp.SYS_MSG
      and json.loads(pp._gemini.request_body(p, pp.SYS_MSG)) == body, json.dumps(body)[:200])
os.environ.pop("KAISCRIBE_TEST_CACHE")
tk.gemini("kurzer Validator-Prompt")
check("andere Prompts ohne Cache", "cachedContent" not in gesendet[-1][1])

# 7) Harness + verify-Skripte hängen am Modul
import test_all_regions as h  # noqa: E402
h.call_gemini("Validator", system=None)
check("test_all_regions.call_gemini → testkosten", gesendet[-1][1]["contents"][0]["parts"][0]["text"] == "Validator")
for f in ("verify_knie.py", "verify_sprunggelenk.py", "verify_flachprofil.py", "verify_konfabulation.py", "verify_kurzsaetze.py",
          "verify_k2k3.py", "verify_peter_ergebnis.py", "verify_georg_schulter_ellbogen.py", "model_ab.py"):
    s = (ROOT / "tools" / f).read_text(encoding="utf-8")
    check(f"{f}: Wiederholungen über testkosten.laeufe", "testkosten.laeufe" in s or "testkosten.argv_laeufe" in s)

print("\n" + ("✅ TESTKOSTEN PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
