"""Spracherkennung der EXE (Umbau Schritt 13) — ohne Tk/Windows/Google-Bibliotheken importierbar.

- medical_phrases(): Phrasen für das Streaming (Live-Anzeige, latest_long) — aus phrases.json (medical_exe).
- chirp_phrases(): kuratiertes chirp_3-PhraseSet (identisch zur Web-App) — aus phrases.json (chirp).
- chirp_sm_phrases(): chirp-fachwortliste-n1 (24.11.2026) – aus SpeechMagic-Briefen gewonnene Fachwortliste
  (phrases.json → chirp_sm), ZUSÄTZLICH zu den 85 kuratierten, mit niedrigerem Boost CHIRP_SM_BOOST; nur wenn der
  Schalter (config.ini CHIRP_SM = Kürzel-Liste) für den Befunder des Diktats an ist (SM_AKTIV, von der EXE gesetzt).
- chirp3_request / chirp3_worker: komplettes Diktat an chirp_3 (STT v2, Location eu); > 50 s in Segmenten
  50 s + 4 s Rückhören, Überlappung per Wortvergleich zusammengefügt (stitch_overlaps).
- kaiscribe-stt-tagesdeckel-n1 (24.11.2026): DECKEL (stt_deckel.Deckel, von der EXE gesetzt) – vor dem ganzen Diktat
  die Schleifenbremse, vor jedem 50-s-Stück die Tagesgrenze; gesperrt → None (kein Google-Aufruf) und letzte_sperre()
  liefert im selben Thread „grenze“/„schleife“ (die EXE behält dann das Audio und zeigt die rote Zeile).
- kaiscribe-live-anzeige-eu-n1 (24.11.2026): LIVE_API_ENDPOINT – die Live-Anzeige (Speech v1, latest_long, Streaming)
  läuft über den EU-Endpunkt eu-speech.googleapis.com (Daten bleiben in der EU), nie über den globalen Host.
  live_client_options() → client_options für speech.SpeechClient. Rückfall-Schutz: tests/offline/test_live_eu.py.
Der Streaming-Teil (Mikrofon → Live-Anzeige) liegt in aufnahme.py (Umbau Schritt 6).
Tests: tests/offline/test_stt.py, sync_fixtures.json (gleiche Fälle für die Web-App).
"""
import base64
import io
import json
import os
import sys
import threading
import urllib.request
import wave

# Phrasenlisten (Umbau Schritt 20, Gutachten P2-2): EINE Datei phrases.json für EXE + Web (im EXE-Bundle per
# --add-data). medical_exe = Streaming-Boost der EXE, chirp = kuratiertes chirp_3-PhraseSet (identisch zur Web-App).
_PHRASEN = None


def _phrasen():
    global _PHRASEN
    if _PHRASEN is None:
        hier = os.path.dirname(os.path.abspath(__file__))
        for d in (getattr(sys, "_MEIPASS", None), hier, os.path.dirname(hier)):
            if d and os.path.exists(os.path.join(d, "phrases.json")):
                with open(os.path.join(d, "phrases.json"), encoding="utf-8") as f:
                    _PHRASEN = json.load(f)
                break
        else:
            raise FileNotFoundError("phrases.json nicht gefunden (EXE-Bundle: --add-data phrases.json)")
    return _PHRASEN


def medical_phrases():
    """Streaming (Live-Anzeige, latest_long, Boost 10): medizinische Fachbegriffe der EXE (292)."""
    return _phrasen()["medical_exe"]


def chirp_phrases():
    """v2.10.15: kuratiertes chirp_3-PhraseSet (Speech Adaptation), identisch zur Web-App (68)."""
    return _phrasen()["chirp"]


# chirp-fachwortliste-n1: Boost der SpeechMagic-Fachwortliste (die 85 kuratierten bleiben bei 10). Gemessen am
# 24.11.2026 im Testprojekt (tools/vm/chirp_fachwort/cfw_messen.py, Bericht BERICHT-CHIRP-FACHWORTLISTE-N1.md).
# kaiscribe-live-anzeige-eu-n1: Live-Anzeige (Speech v1) nur über den EU-Endpunkt. Laut Google-Doku (speech-to-text/
# docs/v1/endpoints) bleiben die Daten nur beim regionalen Endpunkt in Europa, ohne Funktionsänderung der API.
# Web-App: web_app/src/stt.ts (gleicher Host). Nie auf den globalen Host zurück (Patientendaten nur EU).
LIVE_API_ENDPOINT = "eu-speech.googleapis.com"


def live_client_options():
    """client_options für speech.SpeechClient (Live-Anzeige) → EU-Endpunkt. ClientOptions aus google.api_core (kommt
    mit google-cloud-speech); ohne die Bibliothek (Tests) das gleichwertige dict, das der Client ebenso annimmt."""
    try:
        from google.api_core.client_options import ClientOptions
        return ClientOptions(api_endpoint=LIVE_API_ENDPOINT)
    except Exception:
        return {"api_endpoint": LIVE_API_ENDPOINT}


def client_host(client):
    """Host, den ein Google-Client tatsächlich anspricht (für die [INIT]-Zeile als Beleg); None, wenn unbekannt."""
    for weg in (lambda c: c.api_endpoint, lambda c: c.transport._host, lambda c: c._transport._host):
        try:
            h = weg(client)
            if h:
                return str(h)
        except Exception:
            pass
    return None


CHIRP_BOOST = 10
CHIRP_SM_BOOST = 5


def chirp_sm_phrases():
    """chirp-fachwortliste-n1: Fachwortliste aus den SpeechMagic-Briefen (phrases.json → chirp_sm), ohne die schon
    kuratierten (Groß/Klein egal). chirp_3 nimmt bis 1.000 Phrasen (Google-Doku 24.11.2026)."""
    schon = set(p.lower() for p in chirp_phrases())
    return [p for p in _phrasen().get("chirp_sm", []) if p.lower() not in schon]


def chirp_phrase_sets(sm=False):
    """PhraseSets für chirp_3: kuratiert (Boost 10), mit sm=True zusätzlich die SpeechMagic-Liste (eigener Boost)."""
    sets = [{"inlinePhraseSet": {"phrases": [{"value": p, "boost": CHIRP_BOOST} for p in chirp_phrases()]}}]
    if sm:
        sets.append({"inlinePhraseSet": {"phrases": [{"value": p, "boost": CHIRP_SM_BOOST} for p in chirp_sm_phrases()]}})
    return sets


def chirp3_request(token, loc, wav_b64, timeout=60, urlopen=None, sm=False):
    """Ein chirp_3-Request (≤ 60 s Audio). urlopen ist für Tests austauschbar. sm=True: + SpeechMagic-Fachwortliste."""
    urlopen = urlopen or urllib.request.urlopen
    host = 'speech' if loc == 'global' else loc + '-speech'
    url = (f"https://{host}.googleapis.com/v2/projects/rakscribe/"
           f"locations/{loc}/recognizers/_:recognize")
    cfg = {"languageCodes": ["de-DE"], "model": "chirp_3",
           "autoDecodingConfig": {},
           "features": {"enableAutomaticPunctuation": True},
           "adaptation": {"phraseSets": chirp_phrase_sets(sm)}}
    body = json.dumps({"config": cfg, "content": wav_b64}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        j = json.loads(resp.read())
    return transkript_aus(j)


def transkript_aus(j):
    """v3.16.8 (Peter 19.10., Diktat 20261019019, Mammo-Maske): chirp_3 liefert für stille oder unverständliche Stücke
    Ergebnisse OHNE „transcript“ (nur languageCode/resultEndOffset) bzw. ohne „alternatives“ — das warf KeyError
    'transcript' und die Feld-Erkennung fiel aus. Solche Stücke zählen als leer; nur echte Texte werden verbunden."""
    teile = []
    for res in (j or {}).get("results") or []:
        alts = (res or {}).get("alternatives") or []
        t = (alts[0] or {}).get("transcript") if alts and isinstance(alts[0], dict) else None
        if isinstance(t, str) and t.strip():
            teile.append(t.strip())
    return " ".join(teile)


def stitch_overlaps(a, b, window=14):
    """Segment-Texte zusammenfügen: gleiche Wörter am Ende von a / Anfang von b (≥ 80 %) nur einmal."""
    aw, bw = a.split(), b.split()
    best = 0
    for L in range(min(window, len(aw), len(bw)), 0, -1):
        tail = [w.lower().strip('.,:;') for w in aw[-L:]]
        head = [w.lower().strip('.,:;') for w in bw[:L]]
        if sum(1 for x, y in zip(tail, head) if x == y) >= max(1, int(L * 0.8)):  # v3.3.2: ohne max(1,…) galt L=1 immer als Treffer
            best = L
            break
    return (a + " " + " ".join(bw[best:])) if best else (a + " " + b)


def wav_b64(pcm_int16, samplerate):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(samplerate)
        wf.writeframes(pcm_int16.tobytes())
    return base64.b64encode(buf.getvalue()).decode()


# kaiscribe-sonnet-n2: Zähler für die an Chirp geschickten Audiosekunden (nutzung.Zaehler.stt), von der EXE gesetzt
ZAEHLER = None
# chirp-fachwortliste-n1: von der EXE gesetzt – () → True, wenn für den Befunder dieses Diktats die SpeechMagic-
# Fachwortliste an ist (config.ini CHIRP_SM). None/Fehler → aus (nur die 85 kuratierten Phrasen, wie bisher).
SM_AKTIV = None
# kaiscribe-stt-tagesdeckel-n1: harter Tagesdeckel + Schleifenbremse (stt_deckel.Deckel), von der EXE gesetzt
DECKEL = None
_SPERRE = threading.local()


def letzte_sperre():
    """„grenze“ | „schleife“, wenn der letzte chirp3_worker-Aufruf in DIESEM Thread vom Deckel gestoppt wurde, sonst None."""
    return getattr(_SPERRE, "grund", None)


def _deckel_vorher(pcm=None):
    if DECKEL is None:
        return None
    try:
        return DECKEL.vorher(pcm)
    except Exception:
        return None


def sm_aktiv():
    try:
        return bool(SM_AKTIV()) if SM_AKTIV is not None else False
    except Exception:
        return False


def _buchen(sekunden):
    if ZAEHLER is not None:
        try:
            ZAEHLER(sekunden)
        except Exception:
            pass
    if DECKEL is not None:          # tagesdeckel-n1: auch Fehlversuche/Wiederholungen zählen
        try:
            DECKEL.buchen(sekunden, "chirp")
        except Exception:
            pass


def chirp3_worker(pcm_int16, samplerate, loc, token, request=None, sm=None):
    """Komplettes Diktat (int16-Array) → Text. 50-s-Segmente mit 4 s Rückhören (chirp_3: max. 60 s je Request).
    sm=None → Schalter SM_AKTIV der EXE; nur bei an bekommt request das Argument sm=True (alte Attrappen bleiben gültig)."""
    request = request or chirp3_request
    _SPERRE.grund = _deckel_vorher(pcm_int16)        # tagesdeckel-n1: Schleifenbremse + Tagesgrenze vor dem Diktat
    if _SPERRE.grund:
        return None
    sm = sm_aktiv() if sm is None else bool(sm)
    SEG = 50 * samplerate      # 50s Segmente
    OV = 4 * samplerate        # 4s Rueckhoeren
    texts = []
    start = 0
    while start < len(pcm_int16):
        end = min(start + SEG, len(pcm_int16))
        if start > 0:
            _SPERRE.grund = _deckel_vorher()          # tagesdeckel-n1: Grenze auch mitten in einem langen Diktat
            if _SPERRE.grund:
                return None
        b64 = wav_b64(pcm_int16[start:end], samplerate)
        try:
            txt = request(token, loc, b64, sm=True) if sm else request(token, loc, b64)
        finally:
            _buchen((end - start) / float(samplerate))   # auch ein leeres/fehlgeschlagenes Stück hat Google bekommen
        if txt is None:
            return None
        texts.append(txt)
        if end >= len(pcm_int16):
            break
        start = end - OV
    full = texts[0]
    for nxt in texts[1:]:
        full = stitch_overlaps(full, nxt)
    return full
