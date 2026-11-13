"""tools/testkosten.py — gemeinsamer Kostenzähler + EINZIGER Live-Zugang der KaiScribe-Testskripte (Peter-Go 13.11.2026).

Anlass: Google-Budgetalarm 13.11. — die Testläufe vom 12.11. (konfabulation-n1/n2) machten ~3.900 Gemini-Aufrufe
≈ 74 $ Listenpreis. Die Produktion (EXE/Web, Praxis-Schlüssel) läuft NICHT hierüber und bleibt unverändert.

Was das Modul tut
  gemini(prompt, system=…)   Vertex-Aufruf im TESTPROJEKT (Dienstkonto-Schlüssel rakscribe-test-sa-key.json), mit
                             429/5xx-Backoff, Kontext-Cache für den festen Gen-Prompt und Kostenbuchung je Aufruf.
  sonnet(prompt, system=…)   Gutachter-/Bewerter-Aufrufe über Anthropic (Sonnet 5.5, KaiFormat-Schlüssel). Gemini Pro /
                             Carbon als Gutachter ist gesperrt (KAISCRIBE_TEST_GEMINI_GUTACHTER=1 hebt das auf).
  laeufe(n, standard)        Wiederholungen: höchstens 5; bis 20 nur mit --release.
  Zähler                     Token aus usageMetadata/usage × Listenpreis, Buch je Job (JSONL), harte Obergrenze je Job
                             (Standard 5 $, KAISCRIBE_TEST_LIMIT_USD) → sauberer Abbruch mit Meldung, Exit-Code 7.

Umgebung
  KAISCRIBE_TEST_JOB          Job-Name fürs Kostenbuch (Standard: CLAUDE_JOB_NAME, sonst manuell-<Datum>)
  KAISCRIBE_TEST_LIMIT_USD    Obergrenze je Job in $ (Standard 5)
  KAISCRIBE_TEST_LOGDIR       Ordner fürs Kostenbuch (Standard ~/cj/work/testkosten bzw. ~/.kaiscribe-testkosten)
  KAISCRIBE_TEST_TAG_USD      Obergrenze je Kalendertag über ALLE Jobs dieses Rechners (Standard 15 $) — ersetzt die
                              Tagesquote, die Vertex für Gemini-Anfragen nicht anbietet (nur 60/Minute im Testprojekt)
  KAISCRIBE_TEST_SA_KEY       Schlüssel des Testprojekts (Standard ~/.hermes/secrets/ bzw. ~/cj/secrets/
                              rakscribe-test-sa-key.json; Vaultwarden „GCP rakscribe-test Dienstkonto-Schlüssel …“)
  KAISCRIBE_TEST_ALTPROJEKT=1 Notbehelf: altes Projekt rakscribe (vertex-sa-key.json), nur solange das Testprojekt fehlt
  KAISCRIBE_TEST_CACHE=0      Kontext-Cache aus (bit-gleiche Anfrage wie die Produktion)
  KAISCRIBE_TEST_RELEASE=1    wie --release
  KAISCRIBE_GUTACHTER_KEY     Anthropic-Schlüssel (sonst Vaultwarden „Anthropic API KaiFormat“ per vw_get)

Preise: Vertex-Preisseite (abgerufen 13.11.2026), Anthropic-Preisliste; „Non-global“ = Endpunkt eu/europe-west*.
"""
import atexit
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

try:
    import fcntl  # Kostenbuch-Sperre (Linux/macOS); unter Windows laufen keine Live-Tests
except ImportError:  # pragma: no cover
    fcntl = None

ROOT = pathlib.Path(__file__).resolve().parents[1]

# ─── --release aus argv nehmen, bevor die Skripte ihre Positionsargumente lesen ───
RELEASE = "--release" in sys.argv or os.environ.get("KAISCRIBE_TEST_RELEASE") == "1"
while "--release" in sys.argv:
    sys.argv.remove("--release")

MAX_LAEUFE = 5
MAX_LAEUFE_RELEASE = 20
EXIT_GRENZE = 7

# $ je 1 Mio Token: (Input, Input aus Cache, Output, Cache-Speicher je Stunde)
PREISE = {
    ("gemini-3.5-flash", "eu"): (1.65, 0.165, 9.90, 1.00),
    ("gemini-3.5-flash", "global"): (1.50, 0.15, 9.00, 1.00),
    ("gemini-3.5-flash-lite", "eu"): (0.33, 0.033, 2.75, 1.00),
    ("gemini-3.5-flash-lite", "global"): (0.30, 0.03, 2.50, 1.00),
    ("gemini-3.1-flash-lite", "eu"): (0.275, 0.0275, 1.65, 1.00),
    ("gemini-3.1-flash-lite", "global"): (0.25, 0.025, 1.50, 1.00),
    ("gemini-3.1-pro-preview", "global"): (4.00, 0.40, 18.00, 4.50),
    ("gemini-4-carbon", "eu"): (4.40, 0.22, 22.00, 4.50),      # ab 01.12.2026 (vorher 2,20/11,00)
    ("gemini-4-carbon", "global"): (4.00, 0.20, 20.00, 4.50),
    ("claude-sonnet-5-5", "anthropic"): (2.00, 0.20, 10.00, 0.0),   # Cache-Schreiben 2,50
    # Preisseite 13.11.2026: Cache-Schreiben 2,0625 (eu) erst ab 12.01.2027; Speicher je Stunde nicht ausgewiesen → wie Flash
    ("gemini-4-hydrogen", "eu"): (1.65, 0.0825, 8.25, 1.00),
    ("gemini-4-hydrogen", "global"): (1.50, 0.075, 7.50, 1.00),
}
PREIS_UNBEKANNT = (4.40, 0.44, 22.00, 4.50)  # vorsichtig hoch → Grenze greift eher zu früh als zu spät
GUTACHTER_MODELLE = ("pro", "carbon", "argon", "hydrogen")


class KostenGrenze(SystemExit):
    """Obergrenze erreicht. SystemExit, damit ein `except Exception` im Testskript den Abbruch nicht verschluckt;
    ThreadPoolExecutor reicht ihn an den Hauptfaden weiter."""


def _logdir():
    d = os.environ.get("KAISCRIBE_TEST_LOGDIR")
    if not d:
        cj = pathlib.Path.home() / "cj" / "work"
        d = str(cj / "testkosten") if cj.is_dir() else str(pathlib.Path.home() / ".kaiscribe-testkosten")
    p = pathlib.Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_name():
    j = os.environ.get("KAISCRIBE_TEST_JOB") or os.environ.get("CLAUDE_JOB_NAME")
    if not j:
        j = "manuell-" + datetime.date.today().isoformat()
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in j)


def grenze_usd():
    try:
        return float(os.environ.get("KAISCRIBE_TEST_LIMIT_USD", "5"))
    except ValueError:
        return 5.0


def grenze_tag_usd():
    try:
        return float(os.environ.get("KAISCRIBE_TEST_TAG_USD", "15"))
    except ValueError:
        return 15.0


def preis(modell, ort):
    ort = "eu" if ort not in ("global", "anthropic") else ort
    return PREISE.get((modell, ort)) or PREISE.get((modell, "global")) or PREIS_UNBEKANNT


def kosten_gemini(modell, ort, usage):
    """$ eines Vertex-Aufrufs aus usageMetadata (Thinking-Token zählen als Output)."""
    p_in, p_cache, p_out, _ = preis(modell, ort)
    gesamt = int(usage.get("promptTokenCount", 0) or 0)
    cache = int(usage.get("cachedContentTokenCount", 0) or 0)
    out = int(usage.get("candidatesTokenCount", 0) or 0) + int(usage.get("thoughtsTokenCount", 0) or 0)
    return ((gesamt - cache) * p_in + cache * p_cache + out * p_out) / 1e6, gesamt, cache, out


def kosten_anthropic(modell, usage):
    p_in, p_cache, p_out, _ = preis(modell, "anthropic")
    inp = int(usage.get("input_tokens", 0) or 0)
    cr = int(usage.get("cache_read_input_tokens", 0) or 0)
    cw = int(usage.get("cache_creation_input_tokens", 0) or 0)
    out = int(usage.get("output_tokens", 0) or 0)
    return (inp * p_in + cr * p_cache + cw * p_in * 1.25 + out * p_out) / 1e6, inp + cr + cw, cr, out


# ─── Kostenbuch ───
class _Buch:
    def __init__(self):
        self.lock = threading.Lock()
        self.lauf = {"aufrufe": 0, "usd": 0.0, "in": 0, "cache": 0, "out": 0}
        self.start = time.time()
        self.skript = pathlib.Path(sys.argv[0] or "python").name
        self.gemeldet = False
        self.benutzt = False

    @property
    def pfad(self):
        return _logdir() / f"{job_name()}.jsonl"

    def summe_job(self):
        try:
            with open(self.pfad, encoding="utf-8") as f:
                return sum(json.loads(z).get("usd", 0.0) for z in f if z.strip())
        except FileNotFoundError:
            return 0.0

    def summe_tag(self):
        """Heute über alle Kostenbücher (alle Jobs) dieses Rechners."""
        heute, s = datetime.date.today().isoformat(), 0.0
        for f in _logdir().glob("*.jsonl"):
            try:
                with open(f, encoding="utf-8") as fh:
                    s += sum(z.get("usd", 0.0) for z in map(json.loads, filter(str.strip, fh))
                             if z.get("ts", "").startswith(heute))
            except (OSError, ValueError):
                pass
        return s

    def pruefen(self, schaetzung=0.0):
        """Vor jedem Aufruf: Job-Summe bzw. Tagessumme + Schätzung dieses Aufrufs über der Grenze → Abbruch."""
        tag, gt = self.summe_tag(), grenze_tag_usd()
        if tag + schaetzung > gt:
            with self.lock:
                if not self.gemeldet:
                    self.gemeldet = True
                    print(f"\n[testkosten] ABBRUCH: heute schon {tag:.2f} $ Testkosten über alle Jobs, Tagesgrenze "
                          f"{gt:.2f} $ (KAISCRIBE_TEST_TAG_USD). Morgen weiter oder bewusst anheben.", file=sys.stderr, flush=True)
            raise KostenGrenze(EXIT_GRENZE)
        summe, g = self.summe_job(), grenze_usd()
        if summe + schaetzung > g:
            with self.lock:
                if not self.gemeldet:
                    self.gemeldet = True
                    print(f"\n[testkosten] ABBRUCH: Job „{job_name()}“ hat {summe:.2f} $ verbraucht, Grenze {g:.2f} $ "
                          f"(KAISCRIBE_TEST_LIMIT_USD). Weniger Läufe/Fälle wählen oder die Grenze bewusst anheben. "
                          f"Kostenbuch: {self.pfad}", file=sys.stderr, flush=True)
            raise KostenGrenze(EXIT_GRENZE)

    def buchen(self, art, modell, usd, tin, tcache, tout, **extra):
        self.benutzt = True
        zeile = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "skript": self.skript, "pid": os.getpid(),
                 "art": art, "modell": modell, "in": tin, "cache": tcache, "out": tout, "usd": round(usd, 6), **extra}
        with self.lock:
            for k, v in (("aufrufe", 1), ("usd", usd), ("in", tin), ("cache", tcache), ("out", tout)):
                self.lauf[k] += v
            with open(self.pfad, "a", encoding="utf-8") as f:
                if fcntl:
                    fcntl.flock(f, fcntl.LOCK_EX)
                f.write(json.dumps(zeile, ensure_ascii=False) + "\n")

    def bilanz(self):
        if not self.benutzt:
            return
        l = self.lauf
        n = lambda x: f"{x:,}".replace(",", ".")  # noqa: E731  deutsche Tausenderpunkte
        txt = (f"[testkosten] {self.skript}: {l['aufrufe']} Aufrufe, {n(l['in'])} Token Input (davon {n(l['cache'])} aus "
               f"Cache), {n(l['out'])} Output = {l['usd']:.3f} $ | Job „{job_name()}“ gesamt {self.summe_job():.2f} $ "
               f"von {grenze_usd():.2f} $")
        print(txt, file=sys.stderr, flush=True)
        try:
            with open(_logdir() / f"{job_name()}.laeufe.log", "a", encoding="utf-8") as f:
                f.write(datetime.datetime.now().isoformat(timespec="seconds") + " " + " ".join(sys.argv[1:])
                        + " " + txt + "\n")
        except OSError:
            pass


BUCH = _Buch()
atexit.register(BUCH.bilanz)


def job_summe():
    return BUCH.summe_job()


# ─── Wiederholungen ───
def laeufe(angefragt=None, standard=1):
    """Wiederholungen je Fall: ohne --release höchstens 5, mit --release bis 20 (Standard bleibt der des Skripts)."""
    if RELEASE:
        n = int(angefragt) if angefragt else standard
        if n > MAX_LAEUFE_RELEASE:
            print(f"[testkosten] {n} Läufe angefragt → {MAX_LAEUFE_RELEASE} (Obergrenze auch mit --release)", file=sys.stderr)
        return max(1, min(n, MAX_LAEUFE_RELEASE))
    n = int(angefragt) if angefragt else standard
    if n > MAX_LAEUFE:
        print(f"[testkosten] {n} Läufe angefragt → {MAX_LAEUFE} (mehr nur mit --release)", file=sys.stderr)
        n = MAX_LAEUFE
    return max(1, n)


def argv_laeufe(pos=1, standard=1):
    """Läufe aus sys.argv[pos] (wenn Zahl), sonst standard — durch laeufe() begrenzt."""
    a = sys.argv[pos] if len(sys.argv) > pos and sys.argv[pos].isdigit() else None
    return laeufe(int(a) if a else None, standard)


# ─── Offline-Gates vor Release-Läufen ───
def baum_stand():
    """HEAD + Hash der uncommitteten Änderungen (ohne docs/benchmarks) → Stempel der grünen Offline-Gates."""
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=20).stdout.strip()
        diff = subprocess.run(["git", "-C", str(ROOT), "diff", "HEAD", "--", ".", ":(exclude)docs/benchmarks"],
                              capture_output=True, timeout=20).stdout
        return head[:12] + "-" + hashlib.sha256(diff).hexdigest()[:12]
    except Exception:
        return "unbekannt"


def gate_stempel():
    return _logdir() / f"offline_gruen_{baum_stand()}"


def gate_pruefen():
    if RELEASE and os.environ.get("KAISCRIBE_TEST_OHNE_GATE") != "1" and not gate_stempel().exists():
        print("[testkosten] ABBRUCH: --release braucht grüne Offline-Gates für genau diesen Stand. Erst "
              "`python3 tools/testlauf.py --nur-offline` (oder den ganzen tools/testlauf.py --release).", file=sys.stderr)
        raise KostenGrenze(EXIT_GRENZE)


# ─── Zugang Testprojekt ───
_AUTH = {"creds": None, "projekt": None}
_AUTH_LOCK = threading.Lock()


def _schluessel():
    kandidaten = [os.environ.get("KAISCRIBE_TEST_SA_KEY")] + [str(pathlib.Path.home() / d / "rakscribe-test-sa-key.json")
                                                             for d in (".hermes/secrets", "cj/secrets")]
    for test in filter(None, kandidaten):
        if os.path.exists(test):
            return test, False
    test = kandidaten[1]
    if os.environ.get("KAISCRIBE_TEST_ALTPROJEKT") == "1":
        alt = os.environ.get("VERTEX_SA_KEY") or str(pathlib.Path.home() / ".hermes" / "secrets" / "vertex-sa-key.json")
        print("[testkosten] WARNUNG: Testprojekt-Schlüssel fehlt — KAISCRIBE_TEST_ALTPROJEKT=1 nutzt das "
              "Produktionsprojekt rakscribe (ohne Tagesquote)", file=sys.stderr)
        return alt, True
    print(f"[testkosten] ABBRUCH: Schlüssel des Testprojekts fehlt ({test}). Live-Tests laufen nur im Projekt "
          f"rakscribe-test; Notbehelf KAISCRIBE_TEST_ALTPROJEKT=1.", file=sys.stderr)
    raise KostenGrenze(EXIT_GRENZE)


def projekt():
    _token()
    return _AUTH["projekt"]


def _token():
    with _AUTH_LOCK:
        c = _AUTH["creds"]
        if c is None:
            from google.oauth2 import service_account
            pfad, _alt = _schluessel()
            c = service_account.Credentials.from_service_account_file(
                pfad, scopes=["https://www.googleapis.com/auth/cloud-platform"])
            _AUTH["creds"] = c
            _AUTH["projekt"] = json.load(open(pfad)).get("project_id")
        if not c.valid:
            import google.auth.transport.requests as tr
            c.refresh(tr.Request())
        return c.token


def bearer():
    """Bearer-Token des Testprojekts (für Skripte mit eigenen REST-Aufrufen, z. B. Speech)."""
    return _token()


HOSTS = {"eu": "https://aiplatform.eu.rep.googleapis.com", "global": "https://aiplatform.googleapis.com",
         "europe-west3": "https://europe-west3-aiplatform.googleapis.com",
         "europe-west4": "https://europe-west4-aiplatform.googleapis.com"}


def basis(ort="eu"):
    return f"{HOSTS[ort]}/v1/projects/{projekt()}/locations/{ort}"


def modell_url(modell="gemini-3.5-flash", ort="eu"):
    return f"{basis(ort)}/publishers/google/models/{modell}:generateContent"


def _post(url, body, methode="POST", timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=methode,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + _token()})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def credentials():
    """google-auth-Credentials des Testprojekts (z. B. für speech_v1.SpeechClient in Messskripten)."""
    _token()
    return _AUTH["creds"]


# ─── Speech (chirp_3) im Testprojekt ───
STT_USD_JE_MINUTE = 0.016   # Speech-to-Text v2 Standard (chirp_3), Listenpreis


def speech_url(ort="eu"):
    host = "speech" if ort == "global" else ort + "-speech"
    return f"https://{host}.googleapis.com/v2/projects/{projekt()}/locations/{ort}/recognizers/_:recognize"


def buche_stt(audio_bytes, art="stt", modell="chirp_3", bytes_je_sekunde=32000):
    """Kosten eines STT-Aufrufs aus der Audiogröße (Standard: 16 kHz mono 16 bit = 32.000 B/s)."""
    sek = max(1.0, audio_bytes / bytes_je_sekunde)
    BUCH.buchen(art, modell, sek / 60 * STT_USD_JE_MINUTE, 0, 0, 0)


def stt_urlopen(req, timeout=60):
    """urlopen-Ersatz für source_code/stt.chirp3_request: Projekt rakscribe → Testprojekt, Token des Testprojekts,
    Kostenbuchung. So messen die Skripte die ECHTE Produktionsfunktion, aber auf Kosten/Quote des Testprojekts."""
    gate_pruefen()
    BUCH.pruefen(0.02)
    url = req.full_url.replace("/projects/rakscribe/", f"/projects/{projekt()}/")
    body = req.data or b""
    neu = urllib.request.Request(url, data=body, method=req.get_method(), headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + _token()})
    try:
        b64 = len(json.loads(body).get("content", "")) if body else 0
    except ValueError:
        b64 = 0
    buche_stt(b64 * 3 / 4)
    return urllib.request.urlopen(neu, timeout=timeout)


def chirp3_test(_token_ignoriert, loc, wav_b64, timeout=60):
    """stt.chirp3_request im Testprojekt (als request= für stt.chirp3_worker)."""
    sys.path.insert(0, str(ROOT / "source_code"))
    import stt as _stt
    return _stt.chirp3_request(_token(), loc, wav_b64, timeout=timeout, urlopen=stt_urlopen)


def buche_vertex(modell, ort, antwort):
    """Für Skripte mit eigenem REST-Aufruf: Antwort-JSON eines generateContent buchen; gibt $ zurück."""
    usd, tin, tc, tout = kosten_gemini(modell, ort, (antwort or {}).get("usageMetadata", {}))
    BUCH.buchen("gemini", modell, usd, tin, tc, tout)
    return usd


def vorab(schaetzung_usd=0.01):
    """Für Skripte mit eigenem REST-Aufruf: vor dem Aufruf Grenze + Release-Gate prüfen."""
    gate_pruefen()
    BUCH.pruefen(schaetzung_usd)


# ─── Kontext-Cache (fester Gen-Prompt) ───
_PRAEFIXE = []          # [(praefix, system)]
_CACHE_LOCK = threading.Lock()
CACHE_TTL = 3600
OHNE_EXPLIZITEN_CACHE = ("gemini-4-hydrogen",)
CACHE_MIN_ZEICHEN = 8000   # Vertex verlangt ≥ 1.024 Token (Flash); kurze Präfixe lohnen nicht


def cache_praefix(praefix, system=None):
    """Festen Prompt-Anfang anmelden (prod_pipeline: Gen-Prompt bis zur Vorlage). Passt ein Aufruf darauf, geht der
    Anfang als Vertex-cachedContent (90 % billiger) und nur der Rest als Anfrage."""
    if praefix and len(praefix) >= CACHE_MIN_ZEICHEN and (praefix, system) not in _PRAEFIXE:
        _PRAEFIXE.append((praefix, system))


def _cache_an():
    return os.environ.get("KAISCRIBE_TEST_CACHE", "1") != "0"


def _cache_name(modell, ort, praefix, system, neu=False):
    key = hashlib.sha256(f"{projekt()}|{modell}|{ort}|{system}|{praefix}".encode()).hexdigest()[:24]
    datei = _logdir() / "gemini_caches.json"
    with _CACHE_LOCK:
        with open(str(datei) + ".lock", "a") as lk:
            if fcntl:
                fcntl.flock(lk, fcntl.LOCK_EX)
            try:
                alle = json.loads(datei.read_text())
            except (FileNotFoundError, ValueError):
                alle = {}
            e = alle.get(key)
            if e and not neu and e.get("ablauf", 0) > time.time() + 300:
                return e["name"]
            BUCH.pruefen(0.05)
            body = {"model": f"projects/{projekt()}/locations/{ort}/publishers/google/models/{modell}",
                    "contents": [{"role": "user", "parts": [{"text": praefix}]}], "ttl": f"{CACHE_TTL}s"}
            if system:
                body["systemInstruction"] = {"parts": [{"text": system}]}
            c = _post(f"{basis(ort)}/cachedContents", body)
            tok = int(c.get("usageMetadata", {}).get("totalTokenCount", 0))
            p_in, _pc, _po, p_speicher = preis(modell, ort)
            BUCH.buchen("cache-anlegen", modell, tok * (p_in + p_speicher * CACHE_TTL / 3600) / 1e6, tok, 0, 0)
            alle[key] = {"name": c["name"], "ablauf": time.time() + CACHE_TTL, "token": tok}
            alle = {k: v for k, v in alle.items() if v.get("ablauf", 0) > time.time()}
            datei.write_text(json.dumps(alle, indent=1))
            return c["name"]


def _passender_praefix(prompt, system):
    if not _cache_an():
        return None
    for praefix, sys_p in _PRAEFIXE:
        if sys_p == system and prompt.startswith(praefix) and len(prompt) > len(praefix):
            return praefix
    return None


def _text(data):
    cands = data.get("candidates") or [{}]
    return "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", [])
                   if isinstance(p.get("text"), str) and not p.get("thought")).strip()


# ─── Modell-Weiche je Aufrufart (kaiscribe-modellvergleich-n1, nur Messung) ───
# KAISCRIBE_TEST_ROUTE="korr=gemini-3.5-flash@eu,gen=gemini-4-hydrogen@eu~LOW,val=claude-sonnet-5-5"  (oder alle=…)
# Rollen: korr = Call 0 (STT-Korrektur), gen = Befund-Generierung (SYS_MSG bzw. fester Gen-Prompt), val = Web-Validator.
# ~X = Denkstufe: Gemini 4 thinkingLevel (LOW/MEDIUM/HIGH), Gemini 3.x thinkingBudget (Zahl). Ohne Weiche: unverändert.
_ROLLEN_ANFANG = {"val": "Du bist ein radiologischer Qualitätskontrolleur",
                  "korr": "Du bist ein medizinischer Lektor für radiologische Diktate"}
_GEN_SYSTEM = "Du bist ein präziser Radiologie-Assistent"


def rolle_von(prompt, system=None):
    p = (prompt or "").lstrip()
    for rolle, anfang in _ROLLEN_ANFANG.items():
        if p.startswith(anfang):
            return rolle
    if (system or "").startswith(_GEN_SYSTEM) or any(p.startswith(pr.lstrip()) for pr, _s in _PRAEFIXE):
        return "gen"
    return "sonst"


def route():
    """{rolle: (modell, ort, denkstufe)} aus KAISCRIBE_TEST_ROUTE."""
    r = {}
    for teil in filter(None, (t.strip() for t in os.environ.get("KAISCRIBE_TEST_ROUTE", "").split(","))):
        rolle, _, ziel = teil.partition("=")
        ziel, _, denk = ziel.partition("~")
        modell, _, ort = ziel.partition("@")
        r[rolle.strip()] = (modell.strip(), (ort or ("anthropic" if modell.startswith("claude") else "eu")).strip(),
                            denk.strip() or None)
    return r


def gemini_roh(prompt, system=None, temperature=0.0, modell="gemini-3.5-flash", ort="eu", timeout=120,
               thinking_budget=0, generation_config=None, parts=None, cache=True):
    """Vertex generateContent im Testprojekt → (Text, Antwort-JSON). Bucht die Kosten, hält die Grenze ein."""
    rolle = rolle_von(prompt, system)
    weiche = route()
    ziel = None if (generation_config or parts) else (weiche.get(rolle) or weiche.get("alle"))
    if ziel:
        modell, ort, denk = ziel
        if modell.startswith("claude"):
            return sonnet_roh(prompt, system, max_tokens=6000, modell=modell, timeout=timeout,
                              rolle=rolle, praefix_cache=cache, denk=denk)
        if modell.startswith("gemini-4"):
            thinking_budget = None
            generation_config = {"temperature": temperature,
                                 "thinkingConfig": {"thinkingLevel": (denk or "LOW").upper()}}
        elif denk is not None:
            thinking_budget = int(denk)
    if not ziel and any(w in modell for w in GUTACHTER_MODELLE) and os.environ.get("KAISCRIBE_TEST_GEMINI_GUTACHTER") != "1":
        print(f"[testkosten] ABBRUCH: {modell} ist für Tests gesperrt — Gutachter/Bewerter laufen über "
              f"testkosten.sonnet() (Anthropic, KaiFormat-Guthaben).", file=sys.stderr)
        raise KostenGrenze(EXIT_GRENZE)
    gate_pruefen()
    p_in, _pc, p_out, _ = preis(modell, ort)
    BUCH.pruefen((len(prompt) / 3.5 * p_in + 600 * p_out) / 1e6)
    gc = dict(generation_config) if generation_config else {"temperature": temperature}
    if thinking_budget is not None and "thinkingConfig" not in gc:
        gc["thinkingConfig"] = {"thinkingBudget": thinking_budget}
    # Gemini 4 Hydrogen: „does not support explicit context caching“ (HTTP 400, 13.11.2026) → nur implizites Caching
    praefix = None if (parts or not cache or modell in OHNE_EXPLIZITEN_CACHE) else _passender_praefix(prompt, system)
    versuche_cache = 0
    retries = 0
    while True:
        body = {"generationConfig": gc}
        if praefix:
            body["cachedContent"] = _cache_name(modell, ort, praefix, system, neu=versuche_cache > 0)
            body["contents"] = [{"role": "user", "parts": [{"text": prompt[len(praefix):]}]}]
        else:
            body["contents"] = [{"role": "user", "parts": parts or [{"text": prompt}]}]
            if system:
                body["systemInstruction"] = {"parts": [{"text": system}]}
        try:
            t0 = time.time()
            data = _post(modell_url(modell, ort), body, timeout=timeout)
            dauer = time.time() - t0
            break
        except urllib.error.HTTPError as e:
            info = e.read()[:300].decode(errors="replace")
            if praefix and e.code in (400, 404) and "cache" in info.lower() and versuche_cache < 1:
                versuche_cache += 1      # Cache abgelaufen/gelöscht → einmal neu anlegen
                continue
            if praefix and e.code in (400, 404) and versuche_cache >= 1:
                praefix = None           # Cache geht gar nicht → ohne Cache
                continue
            if e.code in (429, 500, 503) and retries < 3:
                retries += 1
                time.sleep(30 * retries)
                continue
            raise Exception(f"Gemini HTTP {e.code}: {info}") from None
    if "error" in data:
        raise Exception(f"Gemini API error: {data['error'].get('message', data['error'])}")
    usd, tin, tc, tout = kosten_gemini(modell, ort, data.get("usageMetadata", {}))
    BUCH.buchen("gemini", modell, usd, tin, tc, tout, rolle=rolle, s=round(dauer, 2),
                denk=int(data.get("usageMetadata", {}).get("thoughtsTokenCount", 0) or 0))
    return _text(data), data


def gemini(prompt, system=None, temperature=0.0, modell="gemini-3.5-flash", ort="eu", timeout=120, **kw):
    return gemini_roh(prompt, system, temperature, modell, ort, timeout, **kw)[0]


# ─── Gutachter über Anthropic ───
_ANTH = {"key": None}
SONNET = "claude-sonnet-5-5"


_ANTH_LOCK = threading.Lock()


def _anthropic_key():
    with _ANTH_LOCK:   # mehrere Fäden gleichzeitig → sonst parallele vw-Abrufe, einer liefert leer (HTTP 401)
        if _ANTH["key"]:
            return _ANTH["key"]
        k = os.environ.get("KAISCRIBE_GUTACHTER_KEY", "").strip()
        if not k:
            sys.path.insert(0, str(pathlib.Path.home() / ".hermes" / "scripts"))
            from vw_get import get_login  # Vaultwarden, Eintrag „Anthropic API KaiFormat“
            k = (get_login("Anthropic API KaiFormat")[1] or "").strip()
        if not k:
            raise Exception("Anthropic-Schlüssel leer (Vaultwarden „Anthropic API KaiFormat“ / KAISCRIBE_GUTACHTER_KEY)")
        _ANTH["key"] = k
        return k


def sonnet_roh(prompt, system=None, max_tokens=2000, modell=SONNET, timeout=180, rolle="gutachter", praefix_cache=False,
               denk=None):
    """Gutachter/Bewerter: Anthropic Messages API (nur synthetische Testtexte!) → (Text, Antwort-JSON).
    praefix_cache=True (Modell-Weiche): fester Gen-Prompt-Anfang als Cache-Breakpoint (System + Präfix gecacht)."""
    p_in, _pc, p_out, _ = preis(modell, "anthropic")
    BUCH.pruefen((len(prompt) / 3.5 * p_in + 1500 * p_out) / 1e6)
    praefix = _passender_praefix(prompt, system) if praefix_cache else None
    content = ([{"type": "text", "text": praefix, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": prompt[len(praefix):]}] if praefix else prompt)
    body = {"model": modell, "max_tokens": max_tokens,   # Sonnet 5.5: kein temperature-Parameter mehr (HTTP 400)
            "messages": [{"role": "user", "content": content}]}
    if system:  # fester Gutachter-Text → Prompt-Cache
        body["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    # Denkstufe: Sonnet 5.5 denkt ohne Angabe adaptiv (≈1.500 Denk-Token je Befund). „aus“ = {"type": "between_tools"}
    # (die API lehnt "disabled" ab), low/medium/high = output_config.effort.
    if denk and denk.lower() == "aus":
        body["thinking"] = {"type": "between_tools"}
    elif denk:
        body["output_config"] = {"effort": denk.lower()}
    retries = 0
    while True:
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                     headers={"x-api-key": _anthropic_key(), "anthropic-version": "2023-06-01",
                                              "content-type": "application/json"}, method="POST")
        try:
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            dauer = time.time() - t0
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 529) and retries < 3:
                retries += 1
                time.sleep(20 * retries)
                continue
            raise Exception(f"Anthropic HTTP {e.code}: {e.read()[:300].decode(errors='replace')}") from None
    usd, tin, tc, tout = kosten_anthropic(modell, data.get("usage", {}))
    BUCH.buchen("anthropic", modell, usd, tin, tc, tout, rolle=rolle, s=round(dauer, 2),
                cache_schreiben=int(data.get("usage", {}).get("cache_creation_input_tokens", 0) or 0),
                denk=int((data.get("usage", {}).get("output_tokens_details") or {}).get("thinking_tokens", 0) or 0))
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip(), data


def sonnet(prompt, system=None, max_tokens=2000, **kw):
    return sonnet_roh(prompt, system, max_tokens, **kw)[0]


if __name__ == "__main__":
    # tools/testkosten.py [job]  → Kostenbuch eines Jobs zusammenfassen
    if len(sys.argv) > 1:
        os.environ["KAISCRIBE_TEST_JOB"] = sys.argv[1]
    try:
        zeilen = [json.loads(z) for z in open(BUCH.pfad, encoding="utf-8") if z.strip()]
    except FileNotFoundError:
        zeilen = []
    proskript = {}
    for z in zeilen:
        s = proskript.setdefault((z["skript"], z["modell"]), [0, 0.0, 0, 0])
        s[0] += 1; s[1] += z["usd"]; s[2] += z["in"]; s[3] += z["cache"]
    for (sk, m), (n, usd, tin, tc) in sorted(proskript.items(), key=lambda x: -x[1][1]):
        print(f"{sk:34s} {m:22s} {n:5d} Aufrufe {tin:>11,} Token ({tc:,} Cache) {usd:8.3f} $")
    print(f"Job {job_name()}: {sum(z['usd'] for z in zeilen):.3f} $ / Grenze {grenze_usd():.2f} $ ({BUCH.pfad})")
