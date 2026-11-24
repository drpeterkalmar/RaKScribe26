"""Gate kaiscribe-live-anzeige-eu-n1 (24.11.2026, Peter „aber chirp ist in der eu?“): die Live-Anzeige (Speech v1,
latest_long) läuft über den EU-Endpunkt eu-speech.googleapis.com – EXE (SpeechClient mit client_options) und Web
(web_app/src/stt.ts). Rückfall-Schutz: schlägt fehl, sobald in source_code/ oder web_app/src/ ein Speech-Aufruf an den
globalen Host (//speech.googleapis.com) oder ein SpeechClient ohne EU-Endpunkt steht, oder chirp_3 nicht mehr mit
Location 'eu' aufgerufen wird. Dazu echter init_google_speech() mit Attrappe: client_options = EU, Erkennung unverändert
(latest_long, use_enhanced, Boost 10, interim_results), [INIT]-Zeile mit dem EU-Host. Keine Google-Aufrufe.
Aufruf: python tests/offline/test_live_eu.py"""
import ast, contextlib, io, pathlib, re, sys, types
HIER = pathlib.Path(__file__).resolve().parent
ROOT = HIER.parents[1]
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(ROOT / "source_code"))
import stt  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("✅" if ok else "❌"), name, "" if ok else detail)
    fails += (not ok)


EU = "eu-speech.googleapis.com"
GLOBAL_HOST = re.compile(r"(?<![\w.-])speech\.googleapis\.com")   # speech.googleapis.com ohne „eu-“ davor

# 1. Kein globaler Host im Code (Python + Web)
dateien = sorted(ROOT.glob("source_code/**/*.py")) + sorted(
    p for ext in ("ts", "tsx", "js", "mjs") for p in ROOT.glob(f"web_app/src/**/*.{ext}"))
check("Quelldateien gefunden (source_code + web_app/src)", len(dateien) > 20, str(len(dateien)))
treffer = [f"{p.relative_to(ROOT)}:{i}" for p in dateien
           for i, z in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1) if GLOBAL_HOST.search(z)]
check("kein Speech-Aufruf an den globalen Host speech.googleapis.com", not treffer, ", ".join(treffer))

# 2. Jeder SpeechClient (auch Async/v2) im Python-Code mit EU-Endpunkt
clients, ohne_eu = 0, []
for p in sorted(ROOT.glob("source_code/**/*.py")):
    baum = ast.parse(p.read_text(encoding="utf-8"), str(p))
    for n in ast.walk(baum):
        if isinstance(n, ast.Call):
            name = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
            if re.fullmatch(r"Speech(Async)?Client", name or ""):
                clients += 1
                kw = {k.arg: ast.unparse(k.value) for k in n.keywords}
                co = kw.get("client_options", "")
                if not ("live_client_options()" in co or EU in co):
                    ohne_eu.append(f"{p.relative_to(ROOT)}:{n.lineno} {ast.unparse(n)}")
check("SpeechClient im Code gefunden", clients >= 1, str(clients))
check("jeder SpeechClient hat client_options → EU-Endpunkt", not ohne_eu, "; ".join(ohne_eu))

# 3. stt.py: Endpunkt + client_options
check("stt.LIVE_API_ENDPOINT = eu-speech.googleapis.com", stt.LIVE_API_ENDPOINT == EU, stt.LIVE_API_ENDPOINT)
co = stt.live_client_options()
ep = co.get("api_endpoint") if isinstance(co, dict) else getattr(co, "api_endpoint", None)
check("live_client_options() → api_endpoint eu-speech.googleapis.com", ep == EU, repr(co))
check("client_host: api_endpoint bzw. transport._host",
      stt.client_host(types.SimpleNamespace(api_endpoint=EU)) == EU
      and stt.client_host(types.SimpleNamespace(transport=types.SimpleNamespace(_host=EU + ":443"))) == EU + ":443"
      and stt.client_host(object()) is None)

# 4. chirp_3 bleibt EU: alle Aufrufe mit Location 'eu', Web-URL eu
code = (ROOT / "source_code" / "RaKScribe.py").read_text(encoding="utf-8")
aufrufe = re.findall(r"_chirp3_worker\(([^()]*(?:\([^()]*\)[^()]*)*)\)", code)
check("chirp_3-Aufrufe der EXE gefunden", len(aufrufe) >= 3, str(len(aufrufe)))
nicht_eu = [a for a in aufrufe if "'eu'" not in a and '"eu"' not in a]
check("jeder chirp_3-Aufruf der EXE mit Location 'eu'", not nicht_eu, "; ".join(nicht_eu))
ts = (ROOT / "web_app" / "src" / "stt.ts").read_text(encoding="utf-8")
check("Web chirp_3: eu-speech …/locations/eu", f"https://{EU}/v2/projects/rakscribe/locations/eu/recognizers/_:recognize" in ts)

# 5. Web Live-Anzeige: eu-speech v1, Erkennung unverändert
check("Web Live-Anzeige: LIVE_RECOGNIZE_URL = https://eu-speech.googleapis.com/v1/speech:recognize",
      f"LIVE_RECOGNIZE_URL = 'https://{EU}/v1/speech:recognize'" in ts and "fetchWithRetry(LIVE_RECOGNIZE_URL" in ts)
check("Web Live-Anzeige: latest_long + useEnhanced + speechContexts Boost 15 unverändert",
      "model: 'latest_long', useEnhanced: true" in ts and "boost: 15.0" in ts)

# 6. Echter init_google_speech() der EXE mit Attrappe
import exe_stubs as S  # noqa: E402
mod = S.lade_rakscribe()
gesehen = {}


class FakeClient:
    def __init__(self, **kw):
        gesehen.update(kw)
        o = kw.get("client_options")
        self.api_endpoint = o.get("api_endpoint") if isinstance(o, dict) else getattr(o, "api_endpoint", None)


class RecCfg:
    class AudioEncoding:
        LINEAR16 = "LINEAR16"

    def __init__(self, **kw):
        self.kw = kw


fake = types.SimpleNamespace(SpeechClient=FakeClient, RecognitionConfig=RecCfg,
                             SpeechContext=lambda **kw: kw, StreamingRecognitionConfig=lambda **kw: kw)
mod.speech, mod.speech_client, mod.google_speech_available = fake, None, True
mod._load_praxis_key = lambda: (None, {"type": "service_account"})
mod._keys = types.SimpleNamespace(**{k: getattr(mod._keys, k) for k in dir(mod._keys) if not k.startswith("__")})
mod._keys.stt_credentials = lambda d: "CRED"
mod._STT_TOKEN_CACHE = types.SimpleNamespace(leeren=lambda: None)
ausgabe = []
mod.print = lambda *a, **k: ausgabe.append(" ".join(str(x) for x in a))
ok = mod.init_google_speech()
check("init_google_speech() → True", ok is True, "\n".join(ausgabe))
o = gesehen.get("client_options")
ep = o.get("api_endpoint") if isinstance(o, dict) else getattr(o, "api_endpoint", None)
check("SpeechClient(credentials=…, client_options → eu-speech.googleapis.com)",
      gesehen.get("credentials") == "CRED" and ep == EU, repr(gesehen))
check("[INIT]-Zeile nennt den EU-Host (Beleg im Log)",
      any(z.startswith("[INIT] Live-Anzeige (Speech v1) über eu-speech.googleapis.com") for z in ausgabe), "\n".join(ausgabe))
k = mod.GOOGLE_CONFIG.kw
check("Erkennung unverändert: latest_long, use_enhanced, de-DE, 16 kHz, Satzzeichen",
      k["model"] == "latest_long" and k["use_enhanced"] is True and k["language_code"] == "de-DE"
      and k["sample_rate_hertz"] == 16000 and k["enable_automatic_punctuation"] is True, repr(k))
sc = k["speech_contexts"][0]
check("Fachwortliste unverändert: medical_exe, Boost 10",
      sc["boost"] == 10.0 and sc["phrases"] == stt.medical_phrases(), repr(sc)[:200])
check("Streaming: interim_results an, gleiche Config",
      mod.STREAMING_CONFIG == {"config": mod.GOOGLE_CONFIG, "interim_results": True}, repr(mod.STREAMING_CONFIG))
check("_streaming() nutzt diesen Client", mod.speech_client.__class__ is FakeClient)

print(f"\n{'ALLE OK' if not fails else f'{fails} FEHLER'} (live-anzeige-eu)")
sys.exit(1 if fails else 0)
