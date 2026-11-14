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

# 8) Anthropic nur über den Testschlüssel KaiTest / Konto B (kaiscribe-testkosten-n2, 13.11.2026). Der KaiFormat-Schlüssel
#    (Konto A) ist Betrieb: kein Testskript darf ihn lesen, auch nicht über ANTHROPIC_API_KEY; Anthropic-REST nur in
#    testkosten.py (dort mit Kostenbuch + Monatsgrenze).
KAIFORMAT = re.compile("Anthropic API " + "KaiFormat" + r"|ANTHROPIC_API_KEY|KAIFORMAT_[A-Z_]*KEY")
ANTH_REST = re.compile(r"api\.anthropic\.com|x-api-key")
DIESE = pathlib.Path(__file__).resolve()
treffer, rest = [], []
dateien = [f for d in ("tools", "tests") for e in ("*.py", "*.sh", "*.ps1", "*.js", "*.mjs")
           for f in (ROOT / d).rglob(e) if "node_modules" not in f.parts]
dateien += [f for f in ROOT.glob("*.py")]
for f in sorted(set(dateien)):
    if f.resolve() == DIESE:
        continue
    txt = f.read_text(encoding="utf-8", errors="replace")
    treffer += [f"{f.relative_to(ROOT)}:{i}" for i, z in enumerate(txt.splitlines(), 1) if KAIFORMAT.search(z)]
    if f.name != "testkosten.py" and ANTH_REST.search(txt):
        rest.append(str(f.relative_to(ROOT)))
check("kein Testskript liest den KaiFormat-Schlüssel (Vaultwarden „…KaiFormat“ / ANTHROPIC_API_KEY)", not treffer,
      ", ".join(treffer[:12]))
check("Anthropic-REST nur in tools/testkosten.py", not rest, str(rest))
check("Vaultwarden-Name des Testschlüssels exakt", tk.VW_TESTSCHLUESSEL == "Anthropic API KaiTest (Konto B)")
geholt = []
fake_vw = type(sys)("vw_get")
fake_vw.get_login = lambda name, cache_ttl=0: (geholt.append(name), ("", "sk-test-B"))[1]
sys.modules["vw_get"] = fake_vw
os.environ.pop("KAISCRIBE_GUTACHTER_KEY", None)
tk._ANTH["key"] = None
check("_anthropic_key holt „Anthropic API KaiTest (Konto B)“", tk._anthropic_key() == "sk-test-B"
      and geholt == ["Anthropic API KaiTest (Konto B)"], str(geholt))

# 9) Kostenbuch je Konto + harte Monatsgrenze Konto B (150 $), bestehende Job-/Tagesgrenzen bleiben
os.environ.update({"KAISCRIBE_TEST_LOGDIR": tempfile.mkdtemp(prefix="testkosten_konto_"), "KAISCRIBE_TEST_LIMIT_USD": "1000",
                   "KAISCRIBE_TEST_TAG_USD": "1000"})
gesendet_a = []


class _Antwort:
    def __init__(self, data):
        self.data = data

    def read(self):
        return json.dumps(self.data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_urlopen(req, timeout=None):
    gesendet_a.append(req)
    return _Antwort({"content": [{"type": "text", "text": "OK"}],
                     "usage": {"input_tokens": 1000, "output_tokens": 100}})


urlopen_orig = tk.urllib.request.urlopen
tk.urllib.request.urlopen = fake_urlopen
try:
    antwort = tk.sonnet("Synthetischer Testtext.", system="Gutachter")
finally:
    tk.urllib.request.urlopen = urlopen_orig
zeilen = [json.loads(z) for z in open(tk.BUCH.pfad, encoding="utf-8") if z.strip()]
check("sonnet(): Schlüssel aus Konto B im Header, Buchung mit konto=anthropic-b",
      antwort == "OK" and gesendet_a[-1].get_header("X-api-key") == "sk-test-B"
      and zeilen[-1]["konto"] == "anthropic-b" and zeilen[-1]["art"] == "anthropic", str(zeilen[-1:]))
tk.BUCH.buchen("gemini", "gemini-3.5-flash", 0.01, 1, 0, 1)
check("Gemini-Buchung → konto=gcp-test", json.loads(open(tk.BUCH.pfad).read().splitlines()[-1])["konto"] == "gcp-test")
check("Altbuchung ohne Konto-Feld (vor n2) zählt als Konto A, nicht B",
      tk.konto_von({"art": "anthropic"}) == "anthropic-a" and tk.konto_von({"art": "gemini"}) == "gcp-test")
os.environ["KAISCRIBE_TEST_KONTO_B_MONAT_USD"] = "500"
check("Monatsgrenze Konto B per Umgebung nicht über 150 $ anhebbar", tk.grenze_konto_b_usd() == 150.0)
os.environ["KAISCRIBE_TEST_KONTO_B_MONAT_USD"] = "20"
check("… aber senkbar", tk.grenze_konto_b_usd() == 20.0)
os.environ.pop("KAISCRIBE_TEST_KONTO_B_MONAT_USD")
# anderer Job im selben Monat verbraucht Konto B fast ganz; Vormonat und Konto A zählen nicht
anderer = pathlib.Path(os.environ["KAISCRIBE_TEST_LOGDIR"]) / "anderer-job.jsonl"
monat = tk.datetime.date.today().isoformat()[:7]
anderer.write_text("\n".join(json.dumps(z) for z in [
    {"ts": monat + "-01T08:00:00", "art": "anthropic", "konto": "anthropic-b", "usd": 149.0},
    {"ts": "2000-01-01T08:00:00", "art": "anthropic", "konto": "anthropic-b", "usd": 500.0},
    {"ts": monat + "-01T08:00:00", "art": "anthropic", "usd": 500.0},
    {"ts": monat + "-01T08:00:00", "art": "gemini", "konto": "gcp-test", "usd": 500.0}]) + "\n")
b = tk.BUCH.summe_monat("anthropic-b")
check("Monatssumme Konto B über alle Jobs, ohne Vormonat/Konto A/Gemini", abs(b - (149.0 + zeilen[-1]["usd"])) < 1e-9, b)
tk.BUCH.gemeldet = False
try:
    tk.BUCH.pruefen(0.01, konto="anthropic-b")
    check("unter 150 $ kein Abbruch", True)
except SystemExit:
    check("unter 150 $ kein Abbruch", False)
try:
    tk.BUCH.pruefen(1.5, konto="anthropic-b")
    check("Konto B über 150 $/Monat → Abbruch", False)
except tk.KostenGrenze as e:
    check("Konto B über 150 $/Monat → KostenGrenze (Exit 7)", e.code == 7)
_gcp_alt = tk.GCP_MONAT_USD
tk.GCP_MONAT_USD = 1000.0  # nur für diese Prüfung: Google-Monatsgrenze ausblenden
try:
    tk.BUCH.pruefen(1.5)
    check("Gemini-Aufrufe hängen nicht an der Konto-B-Grenze", True)
except SystemExit:
    check("Gemini-Aufrufe hängen nicht an der Konto-B-Grenze", False)
tk.GCP_MONAT_USD = _gcp_alt

# Peter 14.11.2026: Google-Testkosten höchstens 5 $/Monat (Vertex-Guthaben 20 $ gehört der Praxis)
os.environ["KAISCRIBE_TEST_GCP_MONAT_USD"] = "50"
check("Google-Monatsgrenze per Umgebung nicht über 5 $ anhebbar", tk.grenze_gcp_monat_usd() == 5.0)
os.environ["KAISCRIBE_TEST_GCP_MONAT_USD"] = "2"
check("… aber senkbar", tk.grenze_gcp_monat_usd() == 2.0)
del os.environ["KAISCRIBE_TEST_GCP_MONAT_USD"]
_gm = tk.BUCH.summe_monat("gcp-test")
try:
    tk.BUCH.pruefen(5.0 - _gm + 0.01)
    check("Google über 5 $/Monat → Abbruch", False)
except tk.KostenGrenze as e:
    check("Google über 5 $/Monat → KostenGrenze (Exit 7)", e.code == 7)
with open(anderer, "a") as fh:
    fh.write(json.dumps({"ts": monat + "-02T08:00:00", "art": "anthropic", "konto": "anthropic-b", "usd": 0.99}) + "\n")
tk.urllib.request.urlopen = fake_urlopen
try:
    tk.sonnet("Synthetischer Testtext.")
    check("sonnet() über der Monatsgrenze bricht VOR dem Aufruf ab", False)
except tk.KostenGrenze:
    check("sonnet() über der Monatsgrenze bricht VOR dem Aufruf ab", len(gesendet_a) == 1)
finally:
    tk.urllib.request.urlopen = urlopen_orig

print("\n" + ("✅ TESTKOSTEN PASS" if not fails else f"❌ {fails} FAIL"))
sys.exit(1 if fails else 0)
