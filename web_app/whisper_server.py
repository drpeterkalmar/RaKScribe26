#!/usr/bin/env python3
"""
RaKScribe26 Whisper STT Server
Lokaler FastAPI-Server für faster-whisper large-v3.
Läuft auf localhost:8765 — kostenlos, offline, keine Cloud-API.

Endpoints:
  POST /whisper  — Audio-Datei empfangen, transkribieren, Text zurückgeben
  GET  /health   — Health check
"""

import os
import sys
import time
import tempfile
import logging
from pathlib import Path

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("whisper-server")

# FastAPI
from fastapi import FastAPI, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Whisper
from faster_whisper import WhisperModel

# ─────────────────────────────────────────────────────────────────────────
# Modell laden (einmalig, bleibt im RAM)
# ─────────────────────────────────────────────────────────────────────────
MODEL_SIZE = os.environ.get("WHISPER_MODEL", "large-v3")
DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE", "int8")

log.info(f"Lade Whisper Modell: {MODEL_SIZE} (device={DEVICE}, compute={COMPUTE_TYPE})")
t0 = time.time()
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
log.info(f"Modell geladen in {time.time()-t0:.1f}s — bereit für Transkriptionen")

# ─────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────
app = FastAPI(title="RaKScribe26 Whisper STT", version="1.0.0")

# CORS für die Web App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Localhost only, sicher
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_SIZE, "device": DEVICE}


@app.post("/whisper")
async def transcribe(file: UploadFile = File(...)):
    """Audio-Datei empfangen, transkribieren, Text zurückgeben."""
    t0 = time.time()
    
    # Audio in temp file speichern
    suffix = Path(file.filename or "audio.ogg").suffix or ".ogg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        log.info(f"Transkribiere: {file.filename} ({len(content)} bytes)")
        
        # Transkribieren
        segments, info = model.transcribe(
            tmp_path,
            language="de",
            beam_size=5,
            # initial_prompt für bessere Fachbegriff-Erkennung
            initial_prompt=(
                "Radiologisches Diktat. BWS, HWS, LWS, Skoliose, flachbogig, "
                "rechtskonvex, linkskonvex, Cobb-Winkel, lateraler Cobb-Winkel, "
                "Schmorl'sche Impressionen, Edgren-Vaino-Zeichen, Morbus Scheuermann, "
                "multisegmentale, Kyphose, Deckplattenimpressionen, Oberkante TH4, "
                "Oberkante TH8, Nervus ulnaris, Sulcus nervi ulnaris, anconeus epitrochlearis, "
                "Ellbogenflexion, Querschnittsfläche, Loge de Guyon, Tendinosis calcarea, "
                "Supraspinatussehne, Bizepssehne, Begleitbursitis, BI-RADS, Morbus Mondor, "
                "Mammasonographie, axillär, thrombosierte Hautvenen."
            ),
        )
        
        text = " ".join(seg.text.strip() for seg in segments).strip()
        
        elapsed = time.time() - t0
        log.info(f"Fertig in {elapsed:.1f}s: {len(text)} Zeichen — \"{text[:100]}...\"")
        
        return {
            "text": text,
            "language": info.language,
            "language_probability": round(info.language_probability, 2),
            "duration": round(info.duration, 1),
            "elapsed_seconds": round(elapsed, 1),
        }
        
    except Exception as e:
        log.error(f"Fehler: {e}")
        return Response(status_code=500, content=f'{{"error": "{str(e)}"}}')
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    port = int(os.environ.get("WHISPER_PORT", "8765"))
    log.info(f"Starte Server auf http://localhost:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")