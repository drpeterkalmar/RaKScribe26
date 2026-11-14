"""Kosten-Bremse für Test-/Verify-Skripte (Peter 14.11.2026: Vertex-Guthaben nur 20 $/Monat).

Hintergrund: Am 12.11.2026 haben Testläufe (verify_konfabulation 9×20, test_all_regions …) ~74 $ Listenpreis
verbraucht – mehr als das ganze Monatsguthaben. Die Praxis (KaiScribe im Betrieb) braucht nur wenige $.
Regel: Tests ≤ 5 $ pro Monat (Lagebild Abschnitt 2).

Wirkung: Beim Import werden urllib.request.urlopen und requests.Session.request umhüllt. Jeder Aufruf an
Vertex/Gemini/Speech wird VOR dem Senden konservativ geschätzt (Body-Zeichen/4 = Tokens, Pro-Modelle ×4,
plus Ausgabe-Pauschale) und in ~/.kaiscribe_testkosten/JJJJ-MM.json mitgeschrieben. Ist die Monatsgrenze
erreicht, bricht das Skript mit SystemExit ab, bevor gesendet wird.

Grenze: Umgebungsvariable KAISCRIBE_TEST_CAP_USD (Standard 5.0). Nur der Praxisbetrieb (EXE/Web-App)
importiert dieses Modul NICHT – die Bremse trifft ausschließlich Tests.
gRPC-Aufrufe (google-cloud-speech Client) werden nicht gesehen; die zugehörigen Skripte zählen pauschal
pro Import einen Lauf (PAUSCHALE_GRPC_USD).
"""
import datetime
import fcntl
import json
import os
import pathlib
import sys
import urllib.request

CAP_USD = float(os.environ.get("KAISCRIBE_TEST_CAP_USD", "5.0"))
LEDGER_DIR = pathlib.Path.home() / ".kaiscribe_testkosten"
HOSTS = ("aiplatform", "generativelanguage", "speech.googleapis")
USD_PRO_MIO_IN = 1.0        # konservativ (Flash-Listenpreis liegt darunter)
FAKTOR_PRO = 4.0            # Pro-/Carbon-Modelle
USD_AUSGABE_PAUSCHAL = 0.003
USD_SPEECH_AUFRUF = 0.02
PAUSCHALE_GRPC_USD = 0.10


def _ledger():
    LEDGER_DIR.mkdir(exist_ok=True)
    return LEDGER_DIR / (datetime.date.today().strftime("%Y-%m") + ".json")


def schaetzen(url, body):
    url = str(url)
    if "speech" in url:
        return USD_SPEECH_AUFRUF
    n = len(body) if isinstance(body, (bytes, str)) else 0
    usd = n / 4 / 1e6 * USD_PRO_MIO_IN + USD_AUSGABE_PAUSCHAL
    if "pro" in url.lower() or "carbon" in url.lower():
        usd *= FAKTOR_PRO
    return usd


def buchen(usd, wofuer):
    p = _ledger()
    with open(p, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        raw = f.read()
        d = json.loads(raw) if raw.strip() else {"usd": 0.0, "aufrufe": 0}
        if d["usd"] + usd > CAP_USD:
            raise SystemExit(
                f"KOSTEN-BREMSE: Test-Budget {CAP_USD:.2f} $ für {p.stem} erreicht "
                f"(bisher ~{d['usd']:.2f} $, {d['aufrufe']} Aufrufe). Abbruch vor dem Senden ({wofuer}). "
                f"Vertex-Guthaben ist nur 20 $/Monat – mehr nur mit Peters Go (KAISCRIBE_TEST_CAP_USD)."
            )
        d["usd"] = round(d["usd"] + usd, 4)
        d["aufrufe"] += 1
        d["zuletzt"] = f"{datetime.datetime.now():%Y-%m-%d %H:%M} {wofuer}"
        f.seek(0)
        f.truncate()
        json.dump(d, f, indent=1)


def stand():
    p = _ledger()
    raw = p.read_text() if p.exists() else ""
    return json.loads(raw) if raw.strip() else {"usd": 0.0, "aufrufe": 0}


def _relevant(url):
    return any(h in str(url) for h in HOSTS)


_orig_urlopen = urllib.request.urlopen


def _urlopen(req, *a, **kw):
    url = req.full_url if isinstance(req, urllib.request.Request) else req
    if _relevant(url):
        body = req.data if isinstance(req, urllib.request.Request) else kw.get("data", a[0] if a else None)
        buchen(schaetzen(url, body), pathlib.Path(sys.argv[0]).name)
    return _orig_urlopen(req, *a, **kw)


urllib.request.urlopen = _urlopen

try:
    import requests

    _orig_req = requests.Session.request

    def _request(self, method, url, *a, **kw):
        if _relevant(url):
            body = kw.get("data")
            if body is None and kw.get("json") is not None:
                body = json.dumps(kw["json"])
            buchen(schaetzen(url, body), pathlib.Path(sys.argv[0]).name)
        return _orig_req(self, method, url, *a, **kw)

    requests.Session.request = _request
except ImportError:
    pass

try:  # gRPC-Speech-Client ist nicht abfangbar → pauschal pro Skriptlauf
    _src = pathlib.Path(sys.argv[0]).read_text(errors="ignore") if sys.argv and sys.argv[0].endswith(".py") else ""
    if "SpeechClient" in _src and not sys.argv[0].endswith("kosten_bremse.py"):
        buchen(PAUSCHALE_GRPC_USD, pathlib.Path(sys.argv[0]).name + " (gRPC pauschal)")
except OSError:
    pass

if __name__ == "__main__":
    s = stand()
    print(f"Test-Kosten {datetime.date.today():%Y-%m}: ~{s['usd']:.2f} $ von {CAP_USD:.2f} $ ({s['aufrufe']} Aufrufe)")
