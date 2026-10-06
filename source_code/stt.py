"""Spracherkennung der EXE (Umbau Schritt 13) — ohne Tk/Windows/Google-Bibliotheken importierbar.

- medical_phrases(): Phrasen für das Streaming (Live-Anzeige, latest_long) — aus phrases.json (medical_exe).
- chirp_phrases(): kuratiertes chirp_3-PhraseSet (identisch zur Web-App) — aus phrases.json (chirp).
- chirp3_request / chirp3_worker: komplettes Diktat an chirp_3 (STT v2, Location eu); > 50 s in Segmenten
  50 s + 4 s Rückhören, Überlappung per Wortvergleich zusammengefügt (stitch_overlaps).
Der Streaming-Teil (Mikrofon → Live-Anzeige) liegt in aufnahme.py (Umbau Schritt 6).
Tests: tests/offline/test_stt.py, sync_fixtures.json (gleiche Fälle für die Web-App).
"""
import base64
import io
import json
import os
import sys
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


def chirp3_request(token, loc, wav_b64, timeout=60, urlopen=None):
    """Ein chirp_3-Request (≤ 60 s Audio). urlopen ist für Tests austauschbar."""
    urlopen = urlopen or urllib.request.urlopen
    host = 'speech' if loc == 'global' else loc + '-speech'
    url = (f"https://{host}.googleapis.com/v2/projects/rakscribe/"
           f"locations/{loc}/recognizers/_:recognize")
    cfg = {"languageCodes": ["de-DE"], "model": "chirp_3",
           "autoDecodingConfig": {},
           "features": {"enableAutomaticPunctuation": True},
           "adaptation": {"phraseSets": [{"inlinePhraseSet": {"phrases": [
               {"value": p, "boost": 10} for p in chirp_phrases()]}}]}}
    body = json.dumps({"config": cfg, "content": wav_b64}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        j = json.loads(resp.read())
    return " ".join(res["alternatives"][0]["transcript"]
                    for res in j.get("results", []))


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


def chirp3_worker(pcm_int16, samplerate, loc, token, request=None):
    """Komplettes Diktat (int16-Array) → Text. 50-s-Segmente mit 4 s Rückhören (chirp_3: max. 60 s je Request)."""
    request = request or chirp3_request
    SEG = 50 * samplerate      # 50s Segmente
    OV = 4 * samplerate        # 4s Rueckhoeren
    texts = []
    start = 0
    while start < len(pcm_int16):
        end = min(start + SEG, len(pcm_int16))
        txt = request(token, loc, wav_b64(pcm_int16[start:end], samplerate))
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
