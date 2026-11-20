"""Schlüssel der EXE (Umbau Schritt 11) — ohne Tk/Windows importierbar und testbar (tests/offline/test_keys.py).

Seit v3.2.3 (Peter 06.10.) gibt es nur noch EINE Quelle: kaiscribe-praxis-key.json (bis 3.19: rakscribe-praxis-key.json)
= {"vertex_api_key": "AQ…", "stt": {Service-Account-JSON}} — neben der EXE oder per Menü in %APPDATA%\\KaiScribe.
kaiscribe-umzug-n1-exe (20.11.2026): Der alte Dateiname wird als Rückfall weiter gelesen (neben der EXE und im
Benutzer-Ordner), der neue hat jeweils Vorrang; Ordner-Umzug %APPDATA%\\RaKScribe → KaiScribe in umzug.py.
Alte Einzeldateien (vertex-key.b64/.txt, rakscribe-stt-key.json/.b64, config.ini API_KEY) werden NICHT gelesen:
sie enthielten nur rotierte Schlüssel, und eine liegengebliebene Altdatei entsperrte sonst die App mit HTTP 401.
"""
import json
import os
import time
from datetime import timezone

import umzug as _umzug

PRAXIS_KEY_NAME = "kaiscribe-praxis-key.json"
ALT_KEY_NAME = "rakscribe-praxis-key.json"      # Rückfall (Drive, X:, alte Benutzer-Ordner)
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
    """(Ordner, Datei) des per Menü geladenen Schlüssels: %APPDATA%\\KaiScribe\\kaiscribe-praxis-key.json (ist die
    Kopie aus %APPDATA%\\RaKScribe gescheitert: der alte Ordner, umzug.benutzer_ordner_aktiv)."""
    ordner = _umzug.benutzer_ordner_aktiv(environ)
    return ordner, os.path.join(ordner, PRAXIS_KEY_NAME)


def kandidaten(base_dir, user_key_path):
    """Suchreihenfolge: neben der EXE (neu, alt), dann der Benutzer-Schlüssel (neu, alter Name im selben Ordner)."""
    aus = [os.path.join(base_dir, PRAXIS_KEY_NAME), os.path.join(base_dir, ALT_KEY_NAME), user_key_path]
    if os.path.basename(user_key_path or "") == PRAXIS_KEY_NAME:
        aus.append(os.path.join(os.path.dirname(user_key_path), ALT_KEY_NAME))
    return aus


def praxis_key_path(base_dir, user_key_path):
    """v3.0: neben der EXE (Vorrang) oder im Benutzerprofil (per Menü geladen — überlebt EXE-Updates)."""
    for p in kandidaten(base_dir, user_key_path):
        if p and os.path.exists(p):
            return p
    return None


def benutzer_schluessel(user_key_path):
    """Alle Benutzer-Schlüsseldateien (neuer und alter Name) — „Gespeicherten Schlüssel entfernen“ löscht beide."""
    return [user_key_path, os.path.join(os.path.dirname(user_key_path), ALT_KEY_NAME)]


def load_praxis_key(base_dir, user_key_path, log=None):
    """Liefert (gemini_key, stt_dict) aus kaiscribe-praxis-key.json (Rückfall rakscribe-praxis-key.json) — oder ("", None)."""
    log = log or (lambda *a: None)
    p = praxis_key_path(base_dir, user_key_path)
    try:
        if p:
            data = json.loads(read_text_robust(p))
            gk = str(data.get('vertex_api_key') or '').strip()
            stt = data.get('stt') if isinstance(data.get('stt'), dict) else None
            name = os.path.basename(p)
            if gk:
                log(f"[INIT] Gemini-Key aus {name} geladen ({len(gk)} Zeichen)")
            if stt:
                log(f"[INIT] STT-Key aus {name} geladen (SA-JSON)")
            return (gk, stt)
    except Exception as e:
        log(f"[INIT] {os.path.basename(p or PRAXIS_KEY_NAME)} nicht verwertbar: {e}")
    return ("", None)


def load_vertex_key(base_dir, user_key_path, log=None):
    gk, _stt = load_praxis_key(base_dir, user_key_path, log)
    if not gk and log:
        log(f"[INIT] Kein Gemini-Key: {PRAXIS_KEY_NAME} fehlt (neben der EXE oder per Menü laden).")
    return gk


def load_anthropic_key(base_dir, user_key_path):
    """kaiscribe-haiku-ab-n1: optionaler Anthropic-Schlüssel (Feld "anthropic_api_key" in kaiscribe-praxis-key.json),
    nur für LLM_ANBIETER = anthropic. Fehlt er → "" (die EXE bleibt bei Gemini)."""
    p = praxis_key_path(base_dir, user_key_path)
    try:
        if p:
            return str(json.loads(read_text_robust(p)).get("anthropic_api_key") or "").strip()
    except Exception:
        pass
    return ""


def ist_praxis_schluessel(data):
    """Prüfung beim Laden per Menü: kombinierter Schlüssel (Gemini + STT mit private_key)?"""
    return bool(str(data.get("vertex_api_key", "")).strip() and isinstance(data.get("stt"), dict)
                and data["stt"].get("private_key"))


def stt_credentials(stt_dict):
    """Service-Account-Credentials für Speech-to-Text (google-auth erst hier importiert). v3.15.4: MIT Scope — ohne
    Scope scheiterte jede Token-Erneuerung für chirp_3 mit „invalid_scope“ (Ordi-Protokoll 15.10.2026: 18 von 18
    Volltranskriptionen), die EXE nahm dann still das schwächere Streaming-Transkript. Der SpeechClient (Live-Anzeige)
    ergänzte sich den Scope selbst, darum fiel es nicht auf."""
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_info(stt_dict, scopes=[STT_SCOPE])


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
