"""Schlüssel der EXE (Umbau Schritt 11) — ohne Tk/Windows importierbar und testbar (tests/offline/test_keys.py).

Seit v3.2.3 (Peter 06.10.) gibt es nur noch EINE Quelle: rakscribe-praxis-key.json
= {"vertex_api_key": "AQ…", "stt": {Service-Account-JSON}} — neben der EXE oder per Menü in %APPDATA%\\RaKScribe.
Alte Einzeldateien (vertex-key.b64/.txt, rakscribe-stt-key.json/.b64, config.ini API_KEY) werden NICHT gelesen:
sie enthielten nur rotierte Schlüssel, und eine liegengebliebene Altdatei entsperrte sonst die App mit HTTP 401.
"""
import json
import os
import time
from datetime import timezone

PRAXIS_KEY_NAME = "rakscribe-praxis-key.json"
STT_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def read_text_robust(path):
    """Windows-Editoren speichern gern UTF-16/BOM/CRLF — alle Varianten vertragen."""
    with open(path, 'rb') as f:
        raw = f.read()
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        raw = raw.decode('utf-16').encode('utf-8')
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    return raw.decode('utf-8', errors='replace')


def user_key_paths(environ=None):
    """(Ordner, Datei) des per Menü geladenen Schlüssels: %APPDATA%\\RaKScribe\\rakscribe-praxis-key.json."""
    env = os.environ if environ is None else environ
    ordner = os.path.join(env.get('APPDATA') or os.path.expanduser('~'), 'RaKScribe')
    return ordner, os.path.join(ordner, PRAXIS_KEY_NAME)


def praxis_key_path(base_dir, user_key_path):
    """v3.0: neben der EXE (Vorrang) oder im Benutzerprofil (per Menü geladen — überlebt EXE-Updates)."""
    for p in (os.path.join(base_dir, PRAXIS_KEY_NAME), user_key_path):
        if os.path.exists(p):
            return p
    return None


def load_praxis_key(base_dir, user_key_path, log=None):
    """Liefert (gemini_key, stt_dict) aus rakscribe-praxis-key.json — oder ("", None)."""
    log = log or (lambda *a: None)
    p = praxis_key_path(base_dir, user_key_path)
    try:
        if p:
            data = json.loads(read_text_robust(p))
            gk = str(data.get('vertex_api_key') or '').strip()
            stt = data.get('stt') if isinstance(data.get('stt'), dict) else None
            if gk:
                log(f"[INIT] Gemini-Key aus {PRAXIS_KEY_NAME} geladen ({len(gk)} Zeichen)")
            if stt:
                log(f"[INIT] STT-Key aus {PRAXIS_KEY_NAME} geladen (SA-JSON)")
            return (gk, stt)
    except Exception as e:
        log(f"[INIT] {PRAXIS_KEY_NAME} nicht verwertbar: {e}")
    return ("", None)


def load_vertex_key(base_dir, user_key_path, log=None):
    gk, _stt = load_praxis_key(base_dir, user_key_path, log)
    if not gk and log:
        log(f"[INIT] Kein Gemini-Key: {PRAXIS_KEY_NAME} fehlt (neben der EXE oder per Menü laden).")
    return gk


def ist_praxis_schluessel(data):
    """Prüfung beim Laden per Menü: kombinierter Schlüssel (Gemini + STT mit private_key)?"""
    return bool(str(data.get("vertex_api_key", "")).strip() and isinstance(data.get("stt"), dict)
                and data["stt"].get("private_key"))


def stt_credentials(stt_dict):
    """Service-Account-Credentials für Speech-to-Text (google-auth erst hier importiert)."""
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_info(stt_dict)


def expiry_timestamp(expiry, fallback):
    """google-auth liefert expiry als NAIVE UTC-Zeit. datetime.timestamp() würde sie als Ortszeit lesen
    (Gutachten P3-6: westlich von UTC käme ein abgelaufenes Token aus dem Cache) → ausdrücklich UTC."""
    if expiry is None:
        return fallback
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry.timestamp()


class SttTokenCache:
    """Bearer-Token für chirp_3 (REST): gecacht, erneuert 120 s vor Ablauf."""

    def __init__(self):
        self.token = None
        self.exp = 0

    def get(self, creds, now=None, request_factory=None):
        now = time.time() if now is None else now
        if self.token and self.exp > now + 120:
            return self.token
        if creds is None:
            return None
        if not creds.valid:
            if request_factory is None:
                from google.auth.transport.requests import Request as request_factory
            creds.refresh(request_factory())
        self.token = creds.token
        self.exp = expiry_timestamp(creds.expiry, now + 3000)
        return self.token

    def leeren(self):
        self.token, self.exp = None, 0
