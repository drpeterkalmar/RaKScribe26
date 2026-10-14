## RaKScribe (Windows-EXE) - (c) 2025-2026 Dr. Peter Kalmar - Licensed under GPLv3
# Diktat → strukturierter Befund. STT: Google Streaming (Live-Anzeige) + chirp_3 (Endtext); LLM: Gemini 3.5 Flash (EU).
# Diese Datei = Oberfläche + main() (Umbau 06.10.2026). Logik ohne UI in: config, keys, detect, stt, gemini, pipeline,
# aufnahme, jobstate, clipboard_win, befund_regeln, normalbypass, misheard. Beim Import passiert nichts (init_runtime).

import keyboard
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import sounddevice as sd
import threading
import os
import sys
import time
import markdown
import re
import win32clipboard
import json
import sqlite3
import traceback
import gemini as _gem  # Umbau Schritt 14: Gemini-Request, parts-Join, Vollständigkeit, Retry
import stt as _stt  # Umbau Schritt 13: chirp_3, Segmentierung 50 s/4 s, Overlap-Stitch, Phrasenlisten
import detect as _detect  # Umbau Schritt 12: Vorlagen-Erkennung + Befundtitel (reine Funktionen)
import keys as _keys  # Umbau Schritt 11: Praxis-Schlüssel, STT-Credentials, Token-Cache
import config as _cfg  # Umbau Schritt 10 (Gutachten P2-4): config.ini mit Standardwerten
import befund_regeln as br  # v3.2: Regionen-Trenner, Ergebnis-Nummerierung, Prompt-Versionswahl (Sync: befundRegeln.ts)
import normalbypass as _nb  # v3.2 (Peter 05.10.): strenger Normalbefund-Bypass (Sync: normalbypass.ts)
import jobstate as _js  # Umbau Schritt 4 (Gutachten P1-2/P2-5): Zustandsmaschine F10/F9 + Generationsnummer je Lauf
import aufnahme as _af  # Umbau Schritt 6 (Gutachten P1-4): Mikrofon getrennt von der Streaming-Live-Anzeige
import einfuegen as _einf  # v3.5: Diktat an der Cursor-Stelle in den Befund einfügen
import korrektur as _korr  # v3.4: Nur-Text-Modus (Call 0 wie Web-App)
import pipeline as _pl  # Umbau Schritt 5: Mehr-Regionen-Befund zusammensetzen (Gutachten P2-6)
import protokoll as _prot  # Umbau Schritt 23: begrenztes Log, Diktatinhalt nur im Debug-Modus
import clipboard_win as _cb  # v3.2.3 (Gutachten P1-1): Zwischenablage mit Wiederholung + Gegenlesen
import speechmike as _sm  # v3.8.0: SpeechMike-Tasten + LEDs direkt (hidapi), ohne Konfiguration in SpeechControl
import segmente as _seg  # v3.8.0: Diktat-Anzeige mit reparierten Abschnitten nach SpeechMike-Pausen
import fensterziel as _fz  # v3.8.0: EOL fügt ins zuletzt aktive Fremdfenster (SpeechMagic/RIS) ein
import cas_auftrag as _cas  # v3.10.0: CAS-Auftrag der RaKScribe-Brücke — EOL schreibt eine Datei statt Strg+V
import cas_vorlagen as _cv  # v3.12.0: CAS-Leistungen als Vorrang-Hinweis für die Vorlagenwahl
import ibl_bausteine as _ibl  # v3.13.0: IB-Lab-Vorbefund-Bausteine der Brücke — nach der KI wörtlich einsetzen
import bereitschaft as _bs  # v3.11.0: wartet minimiert auf das nächste CAS-Diktat (Autostart, Einzelinstanz)

# =========================================================================
# === PFAD-LOGIK ===
# =========================================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    RESOURCES_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Wenn sich das Skript im Unterordner "source_code" befindet, verweisen wir auf das Hauptverzeichnis
    if os.path.basename(BASE_DIR) == "source_code":
        BASE_DIR = os.path.dirname(BASE_DIR)
    RESOURCES_DIR = BASE_DIR

# --- LOGGING SYSTEM ---
LOG_FILE_PATH = os.path.join(BASE_DIR, 'rakscribe.log')

def log(*args):
    # Umbau Schritt 23 (Gutachten P2-14): rakscribe.log begrenzt (5 × 1 MB, protokoll.py); Diktatinhalte nur mit
    # RAKSCRIBE_DEBUG=1 (Aufrufer nutzen _prot.diktat(text)).
    try:
        msg = " ".join(str(arg) for arg in args)
        try:
            sys.__stdout__.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
            sys.__stdout__.flush()
        except Exception:
            pass
        _prot.datei_logger(LOG_FILE_PATH).info(msg)
    except Exception:
        pass

def log_exception(label):
    try:
        tb = traceback.format_exc()
        log(f"EXCEPTION - {label}:\n{tb}")
    except:
        pass

# Override built-in print to automatically write to our log file
print = log

# Umbau Schritt 16 (Gutachten P2-1): beim Import passiert nichts — Start-Initialisierung in init_runtime() (main).
# Bis dahin gelten diese Standardwerte (Tests/Selbsttest setzen sie über init_runtime()).
google_speech_available = False
speech = None                    # google.cloud.speech (in init_runtime geladen)


CONFIG_FILE_PATH = os.path.join(BASE_DIR, 'config.ini')


def app_version():
    """Versionsnummer aus der Datei VERSION (Umbau Schritt 21: EINE Quelle für EXE-Titel, Badge, Web, Release-Tag).
    In der EXE gebündelt (--add-data VERSION), in der Entwicklung im Repo-Root."""
    for d in (RESOURCES_DIR, BASE_DIR):
        try:
            with open(os.path.join(d, "VERSION"), encoding="utf-8") as f:
                v = f.read().strip()
            if v:
                return v
        except OSError:
            continue
    return "?"

# =========================================================================
# === CONFIG LOADING === (Umbau Schritt 10: config.py — Standardwerte, nur Syntaxfehler sind fatal)
# =========================================================================
CFG = _cfg.Config()  # Standardwerte; init_runtime() liest config.ini
LLM_PROVIDER = CFG.llm_provider
LLM_MODEL = CFG.llm_model
API_KEY = CFG.api_key

# --- STT Engines Initialisierungs-Logik ---
# Schlüssel: seit v3.2.3 ausschließlich rakscribe-praxis-key.json (Gemini + STT in EINER Datei).
_read_text_robust = _keys.read_text_robust
USER_KEY_DIR, USER_KEY_PATH = _keys.user_key_paths()


def _praxis_key_path():
    return _keys.praxis_key_path(BASE_DIR, USER_KEY_PATH)


def _load_praxis_key():
    """(gemini_key, stt_dict) aus rakscribe-praxis-key.json (keys.py)."""
    return _keys.load_praxis_key(BASE_DIR, USER_KEY_PATH, log=print)


def _load_vertex_key():
    return _keys.load_vertex_key(BASE_DIR, USER_KEY_PATH, log=print)


speech_client = None
GOOGLE_CONFIG = None
STREAMING_CONFIG = None
_SA_CREDENTIALS = None
_STT_TOKEN_CACHE = _keys.SttTokenCache()

def init_google_speech():
    global speech_client, GOOGLE_CONFIG, STREAMING_CONFIG
    if speech_client is not None:
        return True
    if not google_speech_available:
        print("[INIT] Google Cloud Speech Bibliotheken nicht installiert.")
        return False
    # v3.2.3 (Peter 06.10.): STT-Schlüssel NUR aus rakscribe-praxis-key.json. Die alten Einzeldateien
    # (rakscribe-stt-key.json/.b64, config.ini GOOGLE_JSON_FILENAME) sind rotiert und werden nicht mehr gelesen.
    global _SA_CREDENTIALS
    _gk, _pstt = _load_praxis_key()
    if not _pstt:
        print("[INIT] Keine STT-Credentials: rakscribe-praxis-key.json fehlt (neben der EXE oder per Menü laden).")
        return False
    credentials = _keys.stt_credentials(_pstt)
    _SA_CREDENTIALS = credentials
    _STT_TOKEN_CACHE.leeren()  # neuer Schlüssel → kein Token des alten Service-Accounts weiterverwenden
    try:
        speech_client = speech.SpeechClient(credentials=credentials)
        
        GOOGLE_CONFIG = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000, 
            language_code="de-DE",
            model="latest_long",
            use_enhanced=True,
            enable_automatic_punctuation=True,
            speech_contexts=[
                speech.SpeechContext(
                    phrases=_stt.medical_phrases(),
                    boost=10.0
                )
            ]
        )
        
        STREAMING_CONFIG = speech.StreamingRecognitionConfig(
            config=GOOGLE_CONFIG,
            interim_results=True 
        )
        
        print("[INIT] Google SpeechClient erfolgreich initialisiert. [OK]")
        return True
    except Exception as e:
        print(f"[INIT] Fehler bei Google SpeechClient Initialisierung: {e}")
        return False

# --- LLM Client Initialisierung ---
openai_client = None
VERTEX_ENDPOINT = _gem.VERTEX_ENDPOINT  # Umbau Schritt 14: Gemini-Aufruf in gemini.py


def _init_llm():
    global openai_client
    try:
        if LLM_PROVIDER == 'gemini':
            if _load_vertex_key():
                print(f"[INIT] Gemini-Client via Vertex AI API-Key konfiguriert (Modell: {LLM_MODEL}) [OK]")
            else:
                print("[WARN] Kein Gemini-Key — rakscribe-praxis-key.json laden.")
        elif LLM_PROVIDER == 'openai':
            key = API_KEY if API_KEY else os.environ.get("OPENAI_API_KEY", "")
            if not key:
                print("[WARN] Kein OpenAI API-Key gefunden in config.ini oder OPENAI_API_KEY Umgebungsvariable.")
            from openai import OpenAI  # v3.3.2: nur laden, wenn LLM_PROVIDER = openai (Startzeit)
            openai_client = OpenAI(
                api_key=key if key else "dummy_key"
            )
            print(f"[INIT] OpenAI-Client konfiguriert (Modell: {LLM_MODEL}) [OK]")
        else:
            print("[WARN] Unbekannter oder nicht unterstützter LLM-Provider konfiguriert.")
    except Exception as e:
        messagebox.showerror("LLM Client Fehler", f"Fehler bei Initialisierung des LLM-Clients:\n{e}")

PROMPT_QUELLE = ""
PROMPT_HINWEIS = ""


def load_prompt_template(filename="radiology_prompt.txt"):
    """v3.2: versionierte Prompt-Wahl. Eingebaut = radiology_prompt.txt aus dem EXE-Bundle (Release-Stand).
    radiology_prompt_v4.txt / radiology_prompt.txt neben der EXE gewinnen nur noch, wenn ihr Versionsmarker
    (<!-- RAKSCRIBE_PROMPT_VERSION: … -->) mindestens so neu ist wie der eingebaute — eine alte Datei
    (z.B. früher im Prompt-Editor gespeichert) überlebt so kein Update mehr still."""
    global PROMPT_QUELLE, PROMPT_HINWEIS
    try:
        def _lies(pfad):
            return _read_text_robust(pfad) if os.path.exists(pfad) else ""
        builtin = _lies(os.path.join(RESOURCES_DIR, filename))
        lokale = [(name, _lies(os.path.join(BASE_DIR, name))) for name in ("radiology_prompt_v4.txt", filename)]
        text, PROMPT_QUELLE, PROMPT_HINWEIS = br.waehle_prompt(builtin, lokale)
        print(f"[INIT] Befund-Prompt {br.prompt_version(text) or '(ohne Version)'} aus {PROMPT_QUELLE or '-'}")
        if PROMPT_HINWEIS:
            print(f"[INIT] {PROMPT_HINWEIS}")
        if not text:
            raise FileNotFoundError(filename)
        return text
    except FileNotFoundError:
        return (
            "<role>Radiologe-Assistent</role>\n"
            "<instructions>\n"
            "Du bist ein präziser radiologischer Befundungsassistent. Strukturiere das Diktat "
            "unter Verwendung des bereitgestellten Normalbefund-Templates und orientiere dich für "
            "den Schreibstil und die Formatierung strikt an den Praxisbeispielen.\n"
            "</instructions>\n"
            "<normalbefund_template>\n"
            "{template_body}\n"
            "</normalbefund_template>\n\n"
            "{examples}\n\n"
            "<diktat>\n"
            "{roh_text}\n"
            "</diktat>"
        )
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Laden der Prompt-Datei: {e}")
        return ""

INITIAL_PROMPT_CONTENT = ""  # init_runtime(): load_prompt_template()

SYS_MSG = _gem.SYS_MSG  # wortgleich zur Web-App (tests/offline/befund_regeln_test.py prüft das)
# v3.2: RAG-Few-Shots aus practice_reports.db — Standard AUS (A/B 05.10.: alte Praxisbefunde ohne Nummerierung
# verschlechtern Format/Standardtext, Telegram-Referenz arbeitet ohne Beispiele). config.ini RAG_BEISPIELE = 1 schaltet ein.
RAG_BEISPIELE = 0  # init_runtime(): config.ini RAG_BEISPIELE

# v3.1: Fehlhör-Liste (misheard_words.json neben der EXE, sonst Bundle/Repo) — gleiche Datei und
# gleiche Semantik wie die Web-App (web_app/src/misheard.ts). auto-Regeln ersetzen deterministisch
# im chirp_3-Volltranskript, llm-Regeln gehen als <stt_hinweise> in den Gen-Prompt.
_misheard, MISHEARD_COMPILED, MISHEARD_HINTS = None, [], ""
MISHEARD_WEB_BLOCK = ""  # v3.4: Fehlhör-Block für Call 0 (Nur-Text-Modus), wortgleich zur Web-App


def _init_misheard():
    global _misheard, MISHEARD_COMPILED, MISHEARD_HINTS, MISHEARD_WEB_BLOCK
    try:
        import misheard as _mh
        daten = _mh.load(BASE_DIR)
        _misheard, MISHEARD_COMPILED, MISHEARD_HINTS = _mh, _mh.compile_rules(daten), _mh.prompt_block(daten)
        MISHEARD_WEB_BLOCK = _mh.prompt_block_web(daten)
        print(f"[INIT] Fehlhör-Liste {daten.get('version')}: {len(MISHEARD_COMPILED)} auto-Regeln aus {daten.get('_path')}")
    except Exception as _e_mh:
        print(f"[INIT] Fehlhör-Liste nicht geladen: {_e_mh}")
        _misheard, MISHEARD_COMPILED, MISHEARD_HINTS = None, [], ""


def apply_misheard(text):
    """Deterministische Fehlhör-Korrektur (mode 'auto'); ohne Liste unverändert."""
    if not text or not MISHEARD_COMPILED:
        return text
    fixed = _misheard.apply(text, MISHEARD_COMPILED)
    if fixed != text:
        print(f"[MISHEARD] auto-korrigiert: {_prot.diktat(text)} -> {_prot.diktat(fixed)}")
    return fixed

def load_templates():
    """v3.2.2 (Peter 05.10.: keine Extradateien): templates.json ist IN der EXE gebündelt und gewinnt immer.
    Eine alte templates.json neben der EXE wird ignoriert (sie stammte aus früheren Releases und hätte
    neuere Standardbefunde überdeckt). Ohne Bundle (Entwicklung): Datei neben dem Skript bzw. Repo-Root."""
    cands = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cands.append(os.path.join(meipass, "templates.json"))
    here = os.path.dirname(os.path.abspath(__file__))
    cands += [os.path.join(BASE_DIR, "templates.json"), os.path.join(here, "..", "templates.json")]
    for path in cands:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"[INIT] Vorlagen: {len(data)} aus {path}")
                return data
            except Exception:
                continue
    return {}

RADIOLOGY_TEMPLATES = {}  # init_runtime(): load_templates()
DISPLAY_NAMES = []
# Region nicht erkannt → Vorlage „allgemein“ aus templates.json (v3.2 Peter 05.10.: kein Skelett-Standardtext).
# Umbau Schritt 24 (Gutachten P3-1): die doppelt gepflegte Kopie ALLGEMEIN_FALLBACK entfällt.

def detect_template(text):
    """Vorlagen-Erkennung (detect.py) mit den gebündelten Vorlagen."""
    return _detect.detect_template(text, RADIOLOGY_TEMPLATES)


derive_untersuchungs_titel = _detect.derive_untersuchungs_titel


def classify_report(text):
    text_lower = text.lower()
    categories = {
        "Mammographie": ["mammographie", "mamma", "screening"],
        "LWS": ["lws", "lendenwirbel", "lumbal", "l4/5", "l5/s1"],
        "HWS": ["hws", "halswirbel", "cervical", "hwk"],
        "BWS": ["bws", "brustwirbel", "thorakal", "bwk"],
        "Thorax": ["thorax", "röntgen thorax", "lunge", "pulmo", "cor", "rö-th"],
        "Knie": ["knie", "gonarthrose", "meniskus", "patella"],
        "Schulter": ["schulter", "rotatorenmanschette", "humerus", "omarthrose"],
        "Sonographie Abdomen": ["sono abd", "sonografie abd", "ultraschall abd"],
        "Sonographie Schilddrüse": ["sono schild", "sonografie schilddrüse"],
        "Hüfte": ["hüft", "coxarthrose", "acetabulum"],
        "Sprunggelenk/Fuß": ["sprunggelenk", "calcaneus", "tarsus", "fuß", "zehe"],
        "Hand/Finger/Handgelenk": ["hand", "handgelenk", "karpaltunnel", "finger", "scaphoideum"],
        "CT": ["ct", "computertomographie", "cct"],
        "MRT": ["mrt", "mr des", "mr der", "mr des gehirns", "mr der lws"],
    }
    
    matched = []
    for cat, keywords in categories.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(cat)
                break
                
    if not matched:
        return "Andere"
    elif len(matched) == 1:
        return matched[0]
    else:
        if "MRT" in matched: return "MRT"
        if "CT" in matched: return "CT"
        return matched[0]

def get_few_shot_examples(dictation, category, db_path, limit=2):
    if not os.path.exists(db_path):
        return ""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Säubere und extrahiere Wörter aus dem Diktat
        words = re.findall(r"\b\w{3,}\b", dictation)
        if not words:
            conn.close()
            return ""
            
        clean_words = []
        for w in words:
            if w.upper() in ["AND", "OR", "NOT"]:
                continue
            clean_words.append(f'"{w}"')
            
        if not clean_words:
            conn.close()
            return ""
            
        match_query = " OR ".join(clean_words)
        
        # Abfrage der ähnlichsten Berichte
        if category == "allgemein" or not category or category == "Andere":
            c.execute("""
                SELECT content FROM reports_fts 
                WHERE reports_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """, (match_query, limit))
        else:
            c.execute("""
                SELECT content FROM reports_fts 
                WHERE category = ? AND reports_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """, (category, match_query, limit))
            
        rows = c.fetchall()
        conn.close()
        
        # Fallback auf kategorieunabhängige Suche
        if not rows and category != "allgemein":
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("""
                SELECT content FROM reports_fts 
                WHERE reports_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """, (match_query, limit))
            rows = c.fetchall()
            conn.close()
            
        if not rows:
            return ""
            
        examples_text = "\n### BEISPIELE FÜR TYPISCHE BERICHTE DIESER PRAXIS:\n"
        for i, r in enumerate(rows):
            examples_text += f"\nBeispiel {i+1}:\n{r[0]}\n---\n"
        return examples_text
    except Exception as e:
        print(f"Error in RAG search: {e}")
        return ""

_report_complete = _gem.report_complete


def _get_stt_access_token():
    """Bearer-Token für chirp_3 (keys.SttTokenCache; Ablaufzeit als UTC, Gutachten P3-6)."""
    try:
        if GOOGLE_CONFIG is None:
            return None
        return _STT_TOKEN_CACHE.get(_SA_CREDENTIALS)
    except Exception:
        log_exception("[CHIRP3] Token-Fehler")
        return None

# Umbau Schritt 13: chirp_3-Aufruf, Segmentierung und Overlap-Stitch in stt.py (Namen hier für die Aufrufer)
_chirp3_request = _stt.chirp3_request
_stitch_overlaps = _stt.stitch_overlaps
_chirp3_worker = _stt.chirp3_worker


def _llm_aufruf(prompt):
    """Gen-Prompt → Rohbefund. Gemini (Standard): gemini.py; openai/ollama: Chat-Completions (Streaming)."""
    if LLM_PROVIDER == 'gemini':
        # gemini.py: alle Text-parts, Vollständigkeit + finishReason STOP, bis zu 3 Versuche, Abbruch bei 401
        return _gem.generate(prompt, SYS_MSG, _load_vertex_key(), log=print)
    p_full = prompt
    report = ""
    kwargs = {
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": SYS_MSG}, {"role": "user", "content": p_full}],
        "temperature": 0.0,
        "stream": True
    }
    if LLM_PROVIDER == 'ollama':
        kwargs["extra_body"] = {"options": {"num_ctx": 2048}}
    resp = openai_client.chat.completions.create(**kwargs)
    for chunk in resp:
        delta = chunk.choices[0].delta.content
        if delta:
            report += delta
    return report


def _rag_beispiele(seg):
    """RAG Few-Shot Beispiele (practice_reports.db) — v3.2: Standard AUS (RAG_BEISPIELE in config.ini)."""
    if RAG_BEISPIELE > 0 and not _nb.is_pure_normal_finding(seg, DISPLAY_NAMES):
        db_path = os.path.join(BASE_DIR, "practice_reports.db")
        return get_few_shot_examples(seg, classify_report(seg), db_path, limit=RAG_BEISPIELE)
    return ""


def _pipeline_kontext(cas=None, ibl=None):
    """Kontext für pipeline.befund_aus_diktat — bei jedem Lauf neu (Prompt kann im Editor geändert werden).
    v3.12.0: cas = CAS-Leistungen des offenen Auftrags (cas_vorlagen.CasHinweis) oder None (= wie bisher).
    v3.13.0: ibl = IB-Lab-Bausteine des offenen Auftrags (ibl_bausteine.IblKontext) oder None (= wie bisher)."""
    return _pl.Kontext(templates=RADIOLOGY_TEMPLATES, display_names=DISPLAY_NAMES, prompt=INITIAL_PROMPT_CONTENT,
                       llm=lambda p: _llm_aufruf(p), misheard=apply_misheard, hinweise=MISHEARD_HINTS,
                       beispiele=_rag_beispiele, log=print, ausnahme_log=log_exception,
                       korrektur=lambda t: _korr.korrigieren(t, _load_vertex_key(), MISHEARD_WEB_BLOCK, log=print),
                       cas=cas, ibl=ibl)


# v3.4.0 (Peter 07.10.): Schalter „Nur Text“ — Einstellung überlebt Neustart und Update (%APPDATA%\\RaKScribe)
def _einstellungen_pfad():
    return os.path.join(USER_KEY_DIR, "einstellungen.json")


def einstellung_lesen(name, standard=None):
    try:
        with open(_einstellungen_pfad(), encoding="utf-8") as f:
            return json.load(f).get(name, standard)
    except (OSError, ValueError, AttributeError):
        return standard


def einstellung_schreiben(name, wert):
    try:
        try:
            with open(_einstellungen_pfad(), encoding="utf-8") as f:
                daten = json.load(f)
            if not isinstance(daten, dict):
                daten = {}
        except (OSError, ValueError):
            daten = {}
        daten[name] = wert
        os.makedirs(USER_KEY_DIR, exist_ok=True)
        with open(_einstellungen_pfad(), "w", encoding="utf-8") as f:
            json.dump(daten, f)
    except OSError as e:
        print(f"[EINSTELLUNG] {name} nicht gespeichert: {e}")


# === v3.0 DESIGN-TOKENS (ruhig, kontrastreich, für abgedunkelte Befundräume) ===
BGC_MAIN = "#0D1016"
BGC_ELEV = "#141821"
BGC_CARD = "#171C26"
BGC_INPUT = "#10141C"
BORDER_COLOR = "#262D3B"
BORDER_STRONG = "#343D50"
ACCENT_PURPLE = "#4F8CFF"      # Name historisch — v3.0 Akzent ist Blau
ACCENT_HOVER = "#3F7AF0"
READY_GREEN = "#2FBF71"
WARN_AMBER = "#F2A93B"
RECORDING_RED = "#EF4444"
TEXT_PRIMARY = "#E8EBF1"
TEXT_MUTED = "#9AA3B5"
TEXT_FAINT = "#8791A6"
UI_FONT = "Segoe UI"
STATUS_STYLE = {  # Status → (Anzeigetext, Punktfarbe, Pill-Hintergrund)
    "READY": ("Bereit", READY_GREEN, "#15261F"),
    "RECORDING": ("Aufnahme läuft", RECORDING_RED, "#2E1618"),
    "PROCESSING": ("Befund wird erstellt…", WARN_AMBER, "#2D2413"),
    "COPIED": ("Kopiert & eingefügt", READY_GREEN, "#15261F"),
    "ERROR": ("Fehler", RECORDING_RED, "#2E1618"),
    "LOCKED": ("Gesperrt – Schlüssel fehlt", TEXT_FAINT, "#1B2030"),
    "PAUSED": ("Pause – Record: weiter · INS: Befund", RECORDING_RED, "#2A1A1D"),       # v3.8.0 SpeechMike
    "KONTROLLE": ("Befund prüfen – EOL schickt ihn weiter", READY_GREEN, "#15261F"),   # v3.8.0 nach INS
}
# v3.8.0 (Peter 11.10., Nachtrag 3/4): Hilfe-Zeilen im Menü — gleicher Text in der Web-App (App.tsx)
HILFE_SPEECHMIKE = ("SpeechMike: Record = Aufnahme/Pause · INS = Befund erstellen · EOL = fertig & weiter",
                    "F1 = Neu · F2 = Nur Text (dann zeigt INS den korrigierten Text)")
BESTAETIGUNG_MS = 4500  # v3.12.0 (Peter 13.10.): grünes Band „An CAS übergeben“ nach EOL, nicht zu übersehen
MINIMIEREN_NACH_EOL_MS = BESTAETIGUNG_MS + 100  # v3.11.0: danach wieder als Symbol in die Taskleiste (erst nach dem Band)
CAS_GRUEN = "#1E6B43"
KOPF_BREIT_AB = 1150   # v3.12.0: darunter schmale Kopfzeile (Mikrofon-Auswahl + SpeechMike-Hinweis kürzer)


def befund_titel(text, n=70):
    """v3.12.0: Untersuchungs-Überschriften eines Befunds („## Halswirbelsäule …“, ohne Befund/Ergebnis) für die
    Bestätigung nach EOL, z. B. „Halswirbelsäule in 2 Ebenen · Sonographie des Schultergelenkes rechts“."""
    titel = [z.strip()[3:].strip() for z in (text or "").splitlines()
             if z.strip().startswith("## ") and z.strip()[3:].strip().rstrip(":").lower() not in ("befund", "ergebnis")]
    t = " · ".join(t for t in titel if t)
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def _kurzpfad(pfad, n=64):
    return pfad if len(pfad) <= n else "…" + pfad[-(n - 1):]


GEMINI_401_TEXT = ("Gemini: HTTP 401 — der Praxis-Schlüssel ist ungültig oder veraltet.\n\n"
                   "Bitte die aktuelle rakscribe-praxis-key.json aus dem Drive-Ordner RaKScribe\n"
                   "über Menü → „Schlüssel-Datei laden…“ neu laden.")
def _fokus_ist_eigenes_fenster():
    """True, wenn das Vordergrundfenster zu RaKScribe selbst gehört (v3.3.2, Gutachten P3-4: Strg+V landete dann
    als zweite Kopie in der eigenen Befund-Box statt im RIS). Außerhalb von Windows immer False."""
    try:
        import ctypes
        u32 = ctypes.windll.user32
        hwnd = u32.GetForegroundWindow()
        pid = ctypes.c_ulong(0)
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return bool(hwnd) and pid.value == os.getpid()
    except Exception:
        return False


ZWISCHENABLAGE_GESPERRT = ("Die Zwischenablage ist durch ein anderes Programm gesperrt — Befund bitte mit "
                           "„Befund kopieren“ erneut kopieren und selbst einfügen.")


def _selbsttest_phrasen():
    try:
        return [len(_stt.medical_phrases()), len(_stt.chirp_phrases())]
    except Exception as e:
        return str(e)


def _js_vorschau_processing():
    """Selbsttest: was F10 im Zustand „Befund wird erstellt" auslöst (None = ignoriert)."""
    js = _js.JobState()
    js.simuliere_verarbeitung()
    return js.vorschau("toggle")


def _hid_version():
    """Selbsttest: ist hidapi (Modul hid) im EXE-Bündel?"""
    try:
        import hid
        return "hidapi " + str(hid.version_str())
    except Exception as e:
        return f"FEHLT: {e}"


def _zwischenablage_lesen():
    """Selbsttest: Text in der Zwischenablage (für die EOL-Prüfung auf echtem Windows)."""
    try:
        win32clipboard.OpenClipboard()
        try:
            return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT) or ""
        finally:
            win32clipboard.CloseClipboard()
    except Exception as e:
        return f"(nicht lesbar: {e})"


def _selbsttest_attrappen():
    """NUR Windows-UI-Test (RAKSCRIBE_SELFTEST + RAKSCRIBE_SELFTEST_FAKEAUDIO=1, Fall E): Mikrofon, Google-Streaming,
    chirp_3 und Gemini-Korrektur durch Attrappen ersetzen, damit Record → Pause → Weiter → INS → EOL auf dem
    GitHub-Windows-Rechner (ohne Mikrofon, mit Dummy-Schlüssel) durch DIESELBEN Handler läuft. Im Praxisbetrieb nie aktiv."""
    global sd, speech, speech_client, _chirp3_worker, _get_stt_access_token
    import types
    import numpy as np

    class Strom:
        def __init__(self, device=None, samplerate=16000, channels=1, dtype="int16", callback=None):
            self.cb, self.an = callback, False

        def __enter__(self):
            self.an = True

            def lauf():
                n = 0
                while self.an:
                    t = (np.arange(1600) + n) / 16000.0
                    self.cb((3000 * np.sin(2 * np.pi * 220 * t)).astype(np.int16).reshape(-1, 1), 1600, None, None)
                    n += 1600
                    time.sleep(0.1)
            threading.Thread(target=lauf, daemon=True).start()
            return self

        def __exit__(self, *a):
            self.an = False

    def antwort(text, final):
        alt = types.SimpleNamespace(transcript=text)
        return types.SimpleNamespace(results=[types.SimpleNamespace(alternatives=[alt], is_final=final)])

    class Client:
        def streaming_recognize(self, requests, config=None):
            for n, _ in enumerate(requests, 1):
                if n == 3:
                    yield antwort("Kniegelenk rechts", False)
                elif n == 6:
                    yield antwort("Kniegelenk rechts in 2 Ebenen", True)

    sd = types.SimpleNamespace(InputStream=Strom, default=getattr(sd, "default", None))
    speech = types.SimpleNamespace(StreamingRecognizeRequest=lambda audio_content: audio_content)
    speech_client = Client()
    _chirp3_worker = lambda pcm, sr, loc, token: "Kniegelenk rechts in 2 Ebenen unauffällig."  # noqa: E731
    _get_stt_access_token = lambda: "selbsttest"  # noqa: E731
    _korr.korrigieren = lambda text, key, block="", log=None: text
    log("[SELBSTTEST] Mikrofon, Google-Streaming, chirp_3 und Korrektur durch Attrappen ersetzt (FAKEAUDIO).")


def keys_ready():
    """v3.0: App ist nur bedienbar, wenn Gemini- UND STT-Schlüssel vorhanden sind."""
    return bool(_load_vertex_key()) and (_SA_CREDENTIALS is not None or speech_client is not None)


class RaKScribeApp(ctk.CTk):
    def __init__(self, minimiert=False):
        super().__init__()

        self.title(f"RaKScribe {app_version()} – Röntgen am Kai")
        self.geometry("1240x820")
        self.minsize(900, 600)
        self.configure(fg_color=BGC_MAIN)
        self._status_raw = "READY"
        self.gate = None
        self._job = _js.JobState(log=log)  # veraltete Läufe schreiben/fügen nichts mehr ein (Gutachten P1-2/P2-5)

        # Audio settings
        self.samplerate = 16000
        self.is_recording = False
        self.final_transcript = ""   # Endtext für den Befund — NUR der Stopp-Pfad setzt ihn (chirp_3 oder Rettung)
        self.stream_transcript = ""  # Live-Anzeige: finale Streaming-Abschnitte (Gutachten P2-5: nie in final_transcript)
        self.stream_interim = ""     # Live-Anzeige: letzter Zwischenstand
        self._aufnahme = None        # aufnahme.Aufnahme der laufenden/letzten Aufnahme
        self._einfuegen_ziel = None  # v3.5: (start, ende) im Befund, wenn an der Cursor-Stelle diktiert wird
        self._live_aus = False       # Live-Anzeige ausgefallen (Aufnahme läuft weiter)
        # v3.8.0 SpeechMike: Nachdiktat, reparierte Abschnitte, Kontrollschritt (INS → prüfen → EOL)
        self._basis = ""             # bisheriges Diktat, an das eine SpeechMike-Aufnahme anschließt
        self._abschnitte = []        # reparierter Text je geschlossenem Abschnitt (None = offen/gescheitert)
        self._live = {}              # Abschnitt → [finale Streaming-Texte, Zwischenstand]
        self._kontroll_gen = None    # Lauf, dessen Ergebnis NICHT eingefügt wird (INS)
        self._befund_wartet = False  # Befund aus INS steht rechts und wartet auf EOL (LED grün)
        self._gesendet = False       # sichtbarer Befund wurde schon per Strg+V eingefügt
        self._einfuege_zaehler = 0   # Strg+V gesendet (Selbsttest)

        # Audio-Eingabegeräte sammeln
        self.device_names = []
        self.device_mapping = {}
        self.selected_device_index = None
        self.default_device_name = ""

        try:
            default_idx = sd.default.device[0]
            self.selected_device_index = default_idx
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    # Manche Gerätenamen haben Sonderzeichen, säubern für Anzeige
                    clean_name = dev['name'].encode('utf-8', 'ignore').decode('utf-8')
                    name_str = f"{idx}: {clean_name}"
                    self.device_names.append(name_str)
                    self.device_mapping[name_str] = idx
                    if idx == default_idx:
                        self.default_device_name = name_str
        except Exception as e:
            print(f"[AUDIO] Fehler bei Gerätesuche: {e}")
            self.device_names = ["0: Standard Mikrofon"]
            self.device_mapping = {"0: Standard Mikrofon": 0}
            self.selected_device_index = 0
        if not self.device_names:
            self.device_names = ["Kein Mikrofon gefunden"]
            self.device_mapping = {"Kein Mikrofon gefunden": None}
        if not self.default_device_name:
            self.default_device_name = self.device_names[0]
            self.default_device_name = "0: Standard Mikrofon"

        self.create_widgets()
        self.register_hotkey()
        self._fensterziel = _fz.Fensterziel(_fz.win32_oder_none())
        self.after(500, self._fenster_merken)
        # v3.10.0 (Peter 12.10.): CAS-Auftrag der RaKScribe-Brücke („Digitales Diktat“ ohne SpeechMagic). Mit offenem
        # Auftrag schickt EOL den Befund als Datei an die Brücke statt per Strg+V; ohne Auftrag bleibt alles wie bisher.
        self._cas, self._cas_aufnahmen, self._cas_test = None, [], False
        self._cas_kanal = _cas.Kanal(version=app_version(), log=log, prozess_lebt=_cas.prozess_lebt)
        self.after(700, self._cas_takt)
        # v3.11.0 (Peter 13.10.): Bereitschaft — ab der Windows-Anmeldung minimiert warten (Autostart über einen lokalen
        # Starter, der auf X: wartet), nach EOL im CAS-Modus wieder minimieren; ein zweiter Start holt dieses Fenster vor.
        self._minimiert_gestartet, self._zweitstarts = bool(minimiert), 0
        self._exe_pfad = _bs.exe_pfad()
        self._symbol_gesetzt = False
        if self._exe_pfad:  # wartet als Symbol in der Taskleiste → dort das RaKScribe-Symbol der EXE statt des CTk-Symbols
            try:
                self.iconbitmap(self._exe_pfad)
                self._symbol_gesetzt = True
            except Exception:
                self._iconbitmap_method_called = False  # CTk setzt dann wie bisher sein eigenes Symbol
                log_exception("[START] Fenstersymbol aus der EXE")
        self._autostart = _bs.Autostart(USER_KEY_DIR, log=log)
        self.autostart_var = tk.BooleanVar(value=False)  # beim Öffnen des Menüs aus der Verknüpfung gelesen
        self.nach_cas_minimieren_var = tk.BooleanVar(value=bool(einstellung_lesen("cas_minimieren", True)))
        # v3.13.0 (Peter 13.10.): IB-Lab-Bausteine der Brücke in den Befund übernehmen (Menü, Standard an)
        self.ibl_var = tk.BooleanVar(value=bool(einstellung_lesen("ibl_uebernehmen", True)))
        threading.Thread(target=self._autostart_nachziehen, daemon=True).start()
        # v3.8.2 (Peter 12.10.): SpeechMike-Steuerung im Menü abschaltbar (z. B. wenn SpeechMagic die Tasten braucht)
        self.speechmike_var = tk.BooleanVar(value=bool(einstellung_lesen("speechmike", True)))
        if self.speechmike_var.get():
            self._speechmike_starten()
        else:
            self._speechmike = None
            log("[SPEECHMIKE] Steuerung im Menü ausgeschaltet — Gerät wird nicht geöffnet.")
        self.protocol("WM_DELETE_WINDOW", self._schliessen)
        self.after(150, self.refresh_key_state)
        self.after(400, self._selftest_hook)
        # Umbau Schritt 24 (Gutachten P3-4): Hinweis auf die alte Prompt-Datei nur EINMAL je Datei/Version
        # (Merker in %APPDATA%\\RaKScribe), nicht bei jedem Start
        if PROMPT_HINWEIS and not os.environ.get("RAKSCRIBE_SELFTEST"):
            self.after(1200, self._prompt_hinweis)

    def _kopf_geometrie(self):
        """Selbsttest v3.12.0: [x, Breite] der Kopfzeilen-Elemente (Status-Pill darf nichts überdecken)."""
        out = {}
        for name in ("status_badge", "sm_chip", "key_chip", "device_dropdown", "menu_btn"):
            w = getattr(self, name, None)
            try:
                out[name] = [w.winfo_rootx(), w.winfo_width(), str(w.cget("text")).strip() if name.endswith(("badge", "chip")) else ""]
            except Exception:
                out[name] = None
        try:
            out["fenster"] = [self.winfo_rootx(), self.winfo_width()]
        except Exception:
            pass
        return out

    def _prompt_hinweis(self):
        """v3.11.0: erst zeigen, wenn das Fenster zu sehen ist und kein CAS-Diktat offen ist — minimiert wartend kein
        Dialog aus dem Nichts (z. B. mitten in die CAS-Anmeldung oder ins Diktat)."""
        if self.state() in ("iconic", "withdrawn") or getattr(self, "_cas", None) is not None:
            self.after(3000, self._prompt_hinweis)
            return
        if _cfg.einmalig(os.path.join(USER_KEY_DIR, "gezeigte_hinweise.json"), PROMPT_HINWEIS):
            messagebox.showinfo("Befund-Prompt aktualisiert",
                                PROMPT_HINWEIS + "\n\nDie alte Datei wird nicht mehr verwendet und kann gelöscht werden.")

    def create_widgets(self):
        # ── Kopfzeile ───────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=BGC_ELEV, corner_radius=0, height=64,
                              border_width=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkFrame(self, fg_color=BORDER_COLOR, height=1, corner_radius=0).pack(fill="x")

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="left", padx=(20, 0))
        ctk.CTkLabel(brand, text="≋", width=34, height=34, corner_radius=10, fg_color=ACCENT_PURPLE,
                     text_color="white", font=(UI_FONT, 18, "bold")).pack(side="left")
        names = ctk.CTkFrame(brand, fg_color="transparent")
        names.pack(side="left", padx=(10, 8))
        ctk.CTkLabel(names, text="RaKScribe", font=(UI_FONT, 16, "bold"), text_color=TEXT_PRIMARY,
                     height=18, anchor="w").pack(anchor="w")
        ctk.CTkLabel(names, text="Röntgen am Kai", font=(UI_FONT, 11), text_color=TEXT_FAINT,
                     height=14, anchor="w").pack(anchor="w")
        ctk.CTkLabel(brand, text=f" v{app_version()} ", font=(UI_FONT, 11, "bold"), text_color=ACCENT_PURPLE,
                     fg_color="#1A2640", corner_radius=9, height=20).pack(side="left")

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=(0, 20))
        self.menu_btn = ctk.CTkButton(right, text="☰", width=38, height=36, corner_radius=9,
                                      fg_color="transparent", hover_color=BGC_CARD, border_width=1,
                                      border_color=BORDER_COLOR, text_color=TEXT_MUTED,
                                      font=(UI_FONT, 16), command=self.open_menu)
        self.menu_btn.pack(side="right")
        self.device_dropdown = ctk.CTkComboBox(right, values=self.device_names, command=self.on_device_changed,
                                               width=250, height=36, corner_radius=9, fg_color=BGC_INPUT,
                                               border_color=BORDER_COLOR, button_color=BORDER_STRONG,
                                               dropdown_fg_color=BGC_ELEV, font=(UI_FONT, 12),
                                               dropdown_font=(UI_FONT, 12))
        self.device_dropdown.set(self.default_device_name)
        self.device_dropdown.pack(side="right", padx=10)
        self.key_chip = ctk.CTkLabel(right, text="", font=(UI_FONT, 12, "bold"), corner_radius=12, height=26)
        self.key_chip.pack(side="right")
        # v3.8.0: kleine Anzeige, solange ein SpeechMike verbunden ist
        self.sm_chip = ctk.CTkLabel(right, text="", font=(UI_FONT, 12, "bold"), corner_radius=12, height=26,
                                    text_color=ACCENT_PURPLE)
        self.sm_chip.pack(side="right", padx=(0, 8))

        self.status_badge = ctk.CTkLabel(header, text="", font=(UI_FONT, 13, "bold"), corner_radius=15,
                                         height=30, text_color=TEXT_PRIMARY)
        # v3.12.0 (Peter 13.10.: „Bereit“ überdeckte „SpeechMike verbunden“): nicht mehr mittig über die ganze Kopfzeile
        # gelegt, sondern in den freien Platz zwischen Marke und rechter Gruppe gepackt — überdeckt nie etwas
        self.status_badge.pack(side="left", expand=True, padx=12)
        header.bind("<Configure>", self._kopf_anpassen)

        # ── Arbeitsbereich: Diktat | Befund ─────────────────────────
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=18, pady=16)
        self.main_container.grid_columnconfigure(0, weight=1, uniform="col")
        self.main_container.grid_columnconfigure(1, weight=1, uniform="col")
        self.main_container.grid_rowconfigure(0, weight=1)

        def card(col, title):
            c = ctk.CTkFrame(self.main_container, fg_color=BGC_CARD, corner_radius=14,
                             border_width=1, border_color=BORDER_COLOR)
            c.grid(row=0, column=col, padx=(0, 8) if col == 0 else (8, 0), sticky="nsew")
            head = ctk.CTkFrame(c, fg_color="transparent", height=44)
            head.pack(fill="x", padx=16, pady=(8, 0))
            head.pack_propagate(False)
            ctk.CTkLabel(head, text=title, font=(UI_FONT, 12, "bold"), text_color=TEXT_MUTED).pack(side="left")
            ctk.CTkFrame(c, fg_color=BORDER_COLOR, height=1, corner_radius=0).pack(fill="x", padx=1)
            foot = ctk.CTkFrame(c, fg_color=BGC_ELEV, corner_radius=0, height=66)
            foot.pack(side="bottom", fill="x", padx=1, pady=(0, 1))
            foot.pack_propagate(False)
            ctk.CTkFrame(c, fg_color=BORDER_COLOR, height=1, corner_radius=0).pack(side="bottom", fill="x", padx=1)
            return c, head, foot

        left_card, left_head, left_foot = card(0, "DIKTAT")
        right_card, right_head, right_foot = card(1, "BEFUND")

        # v3.4.0 (Peter 07.10.): „Nur Text“ — rechts nur die korrigierte Spracherkennung, kein strukturierter Befund
        self.nur_text_var = tk.BooleanVar(value=bool(einstellung_lesen("nur_text", False)))
        self.nur_text_switch = ctk.CTkSwitch(right_head, text="Nur Text", variable=self.nur_text_var,
                                             command=self._nur_text_umgeschaltet, font=(UI_FONT, 12),
                                             text_color=TEXT_MUTED, progress_color=ACCENT_PURPLE)
        self.nur_text_switch.pack(side="right", pady=10)
        # v3.7.0 (Peter 07.10.): Option im Menü — beim Diktat in den Befund am Satzanfang groß beginnen
        self.gross_satzanfang_var = tk.BooleanVar(value=bool(einstellung_lesen("gross_satzanfang", True)))

        # Pegel im Diktat-Kopf
        self.level_container = ctk.CTkFrame(left_head, width=200, height=6, fg_color=BGC_INPUT, corner_radius=3)
        self.level_container.pack(side="right", pady=19)
        self.level_indicator = ctk.CTkFrame(self.level_container, width=0, height=6, fg_color=READY_GREEN, corner_radius=3)
        self.level_indicator.place(x=0, y=0)
        # v3.8.0: nach einer SpeechMike-Pause ist das bisher Diktierte repariert (chirp_3 + Fehlhör-Liste)
        self.repariert_label = ctk.CTkLabel(left_head, text="", font=(UI_FONT, 11, "bold"), text_color=READY_GREEN)
        self.repariert_label.pack(side="right", padx=(0, 12))

        box_kw = dict(font=(UI_FONT, 15), fg_color="transparent", text_color=TEXT_PRIMARY, wrap="word",
                      border_width=0, scrollbar_button_color=BORDER_STRONG)
        self.transcript_text = ctk.CTkTextbox(left_card, **box_kw)
        self.transcript_text.pack(fill="both", expand=True, padx=10, pady=8)
        self.result_text = ctk.CTkTextbox(right_card, **box_kw)
        self.result_text.pack(fill="both", expand=True, padx=10, pady=8)
        self._setup_report_formatting()

        # Diktat-Fußzeile
        self.record_btn = ctk.CTkButton(left_foot, text=" Aufnahme Starten (F10) ", height=44, width=230,
                                        font=(UI_FONT, 14, "bold"), fg_color=ACCENT_PURPLE,
                                        hover_color=ACCENT_HOVER, corner_radius=10, command=self.toggle_recording)
        self.record_btn.pack(side="left", padx=14, pady=11)
        ghost = dict(height=40, font=(UI_FONT, 13), fg_color="transparent", hover_color=BGC_CARD,
                     border_width=1, border_color=BORDER_STRONG, text_color=TEXT_PRIMARY, corner_radius=10)
        self.reset_btn = ctk.CTkButton(left_foot, text="↺  Neu (F9)", width=110, command=self.reset_dictation, **ghost)
        self.reset_btn.pack(side="right", padx=14)
        # v3.6.0 (Peter 07.10.): getippten/eingefügten Text strukturieren lassen (auch Strg+Enter im Diktat-Feld)
        self.text_btn = ctk.CTkButton(left_foot, text="✎  Befund aus Text", width=160, command=self.befund_aus_text, **ghost)
        self.text_btn.pack(side="right")
        self.transcript_text._textbox.bind("<Control-Return>", self.befund_aus_text)

        # Befund-Fußzeile
        ctk.CTkLabel(right_foot, text="Wird automatisch kopiert und eingefügt", font=(UI_FONT, 11),
                     text_color=TEXT_FAINT).pack(side="left", padx=16)
        self.copy_btn = ctk.CTkButton(right_foot, text="⧉  Befund kopieren", height=40, width=170,
                                      font=(UI_FONT, 13, "bold"), fg_color=ACCENT_PURPLE, hover_color=ACCENT_HOVER,
                                      corner_radius=10, command=lambda: self.copy_formatted_report(aus_knopf=True))
        self.copy_btn.pack(side="right", padx=14)
        self.prompt_window = None
        self.update_status("READY", "ready")

        # v3.10.0: Band für einen CAS-Auftrag der RaKScribe-Brücke — nur sichtbar, solange ein Auftrag offen ist.
        # Knöpfe + F11/F12 für den Fern-Test per Remotedesktop (kein SpeechMike); F11/F12 wirken nur mit Auftrag.
        self.cas_band = ctk.CTkFrame(self, fg_color="#1A2640", corner_radius=0, height=56)
        self.cas_band.pack_propagate(False)
        cas_text = ctk.CTkFrame(self.cas_band, fg_color="transparent")
        cas_text.pack(side="left", padx=18, fill="y")
        self.cas_label = ctk.CTkLabel(cas_text, text="", font=(UI_FONT, 14, "bold"), text_color="#FFFFFF", height=22,
                                      anchor="w")
        self.cas_label.pack(side="top", anchor="w", pady=(6, 0))
        # v3.12.0: Hinweise zur Vorlagenwahl mit CAS-Leistungen („LWS laut CAS, nicht diktiert“) — nur Anzeige
        self.cas_hinweis_label = ctk.CTkLabel(cas_text, text="", font=(UI_FONT, 12, "bold"), text_color=WARN_AMBER,
                                              height=18, anchor="w")
        self.cas_hinweis_label.pack(side="top", anchor="w")
        # v3.13.0: IB-Lab-Bausteine („IB Lab: FROG rechts ✓“, grün; kommt etwas nach → kurz hervorgehoben) + Hinweise
        # (amber, nur Anzeige). Eigene Zeile, nur sichtbar, solange der Auftrag Bausteine hat; Klick zeigt alles.
        self.ibl_zeile = ctk.CTkFrame(cas_text, fg_color="transparent")
        self.ibl_label = ctk.CTkLabel(self.ibl_zeile, text="", font=(UI_FONT, 12, "bold"), text_color=READY_GREEN,
                                      height=18, anchor="w", corner_radius=6)
        self.ibl_label.pack(side="left")
        self.ibl_hinweis_label = ctk.CTkLabel(self.ibl_zeile, text="", font=(UI_FONT, 12), text_color=WARN_AMBER,
                                              height=18, anchor="w")
        self.ibl_hinweis_label.pack(side="left", padx=(12, 0))
        for w in (self.ibl_label, self.ibl_hinweis_label):
            w.bind("<Button-1>", lambda e: self._ibl_details())
        # v3.12.0 (Peter 13.10.): nach EOL im CAS-Modus eine Bestätigung, die man nicht übersieht — grünes Band,
        # erst danach geht RaKScribe in die Taskleiste
        self.bestaetigung_band = ctk.CTkFrame(self, fg_color=CAS_GRUEN, corner_radius=0, height=56)
        self.bestaetigung_band.pack_propagate(False)
        self.bestaetigung_label = ctk.CTkLabel(self.bestaetigung_band, text="", font=(UI_FONT, 16, "bold"),
                                               text_color="#FFFFFF")
        self.bestaetigung_label.pack(side="left", padx=18)
        band_kw = dict(height=34, corner_radius=9, font=(UI_FONT, 12, "bold"))
        rand_kw = dict(fg_color="transparent", border_width=1, border_color=BORDER_STRONG, hover_color=BGC_CARD,
                       text_color=TEXT_PRIMARY)
        ctk.CTkButton(self.cas_band, text="✕ Abbrechen", width=110, command=self.cas_abbrechen, **rand_kw,
                      **band_kw).pack(side="right", padx=(6, 14))
        ctk.CTkButton(self.cas_band, text="EOL: an CAS (F12)", width=150, command=self.befund_fertig,
                      fg_color=READY_GREEN, hover_color="#27A862", text_color="#08130D", **band_kw).pack(side="right", padx=6)
        ctk.CTkButton(self.cas_band, text="INS: Befund (F11)", width=145, command=self.sm_ins, fg_color=ACCENT_PURPLE,
                      hover_color=ACCENT_HOVER, **band_kw).pack(side="right", padx=6)
        ctk.CTkButton(self.cas_band, text="Testbefund", width=110, command=self.cas_testbefund, **rand_kw,
                      **band_kw).pack(side="right", padx=6)
        # v3.13.0: IB-Lab-Werte, die erst nach dem Befund kamen, auf Knopfdruck einsetzen (nie still in einen
        # schon geprüften Befund — Peter 11.10.: nie etwas Ungesehenes weiterschicken)
        self.ibl_knopf = ctk.CTkButton(self.cas_band, text="＋ IB Lab einfügen", width=150, command=self.ibl_einfuegen,
                                       fg_color="#1E6B43", hover_color="#27A862", **band_kw)
        self.bind_all("<F11>", lambda e: self._cas_taste("ins"))
        self.bind_all("<F12>", lambda e: self._cas_taste("eol"))

    # ── v3.0: Selbsttest-Modus für den automatischen Windows-UI-Test (tests/windows/exe_ui_test.py).
    # NUR aktiv, wenn die Umgebungsvariable RAKSCRIBE_SELFTEST gesetzt ist — im Praxisbetrieb wirkungslos.
    # Schreibt den UI-Zustand als JSON (Sperre, Aufnahme-Button, Status, Schlüssel) und füllt optional Demo-Text.
    def _selftest_hook(self):
        path = os.environ.get("RAKSCRIBE_SELFTEST")
        if not path:
            return
        if not getattr(self, "_minimiert_gestartet", False):  # v3.11.0 Fall G: --minimiert bleibt Taskleisten-Symbol
            geo = os.environ.get("RAKSCRIBE_SELFTEST_GEOMETRY")
            if geo == "zoomed":
                self.state("zoomed")
            elif geo:
                self.geometry(geo)
            self.lift()
            self.attributes("-topmost", True)
            self.focus_force()
        if os.environ.get("RAKSCRIBE_SELFTEST_FAKEAUDIO") == "1":
            _selbsttest_attrappen()  # v3.8.0 Fall E: SpeechMike-Ablauf ohne Mikrofon/Google

        def dump(phase):
            try:
                data = {}
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                tb = self.result_text._textbox
                data[phase] = {
                    "title": self.title(),
                    "gate_visible": self.gate is not None,
                    "record_btn_state": str(self.record_btn.cget("state")),
                    "status": self._status_raw,
                    "keys_ready": bool(keys_ready()),
                    "key_chip": self.key_chip.cget("text").strip(),
                    "geometry": self.winfo_geometry(),
                    "screen": [self.winfo_screenwidth(), self.winfo_screenheight()],
                    "report_heading_tags": (len(tb.tag_ranges("md_title")) + len(tb.tag_ranges("md_title_n"))
                                            + len(tb.tag_ranges("md_head"))) // 2,
                    "report_title_tags": (len(tb.tag_ranges("md_title")) + len(tb.tag_ranges("md_title_n"))) // 2,
                    "report_hidden_hash_tags": len(tb.tag_ranges("md_hidden")) // 2,
                    "report_text_keeps_markdown": self.result_text.get("1.0", "end").lstrip().startswith("##"),
                    "toggle_calls": getattr(self, "_toggle_calls", 0),
                    "mic_dropdown": self.device_dropdown.get(),
                    # v3.2: gebündelter Prompt + Regel-Modul auf echtem Windows nachweisen
                    "prompt_version": br.prompt_version(INITIAL_PROMPT_CONTENT),
                    "prompt_quelle": PROMPT_QUELLE,
                    "multi_region_segmente": len(br.split_regionen(
                        "Schulter rechts Punkt Omarthrose Punkt Ellbogen rechts Punkt Ellbogengelenksarthrose")),
                    "ergebnis_nummeriert": br.ergebnis_nummerieren("## Ergebnis\nOmarthrose.\nKalkdepot.").endswith("2. Kalkdepot."),
                    # v3.2.3: gebündelte vorlagen_vorrang.json + Zustandsmodul auf echtem Windows nachweisen
                    "vorlage_vorfuss": detect_template("Vorfuß rechts in 2 Ebenen unauffällig"),
                    "vorlage_mrt_knie": detect_template("MRT Knie rechts unauffällig"),
                    "f10_waehrend_verarbeitung": "ignorieren" if _js_vorschau_processing() is None else "start",
                    # Umbau Schritt 20: gebündelte phrases.json (Streaming / chirp_3)
                    "phrasen": _selbsttest_phrasen(),
                    "is_recording": bool(self.is_recording),
                    "job_zustand": self._job.zustand,
                    # v3.8.0 SpeechMike: hidapi im Bündel, Lese-Thread läuft ohne Gerät, LED-Soll, Kontrollschritt, EOL
                    "hid": _hid_version(),
                    "speechmike_thread": bool(getattr(self, "_speechmike", None) and self._speechmike._thread
                                              and self._speechmike._thread.is_alive()),
                    "speechmike_verbunden": getattr(getattr(self, "_speechmike", None), "verbunden", None),
                    "led": getattr(getattr(self, "_speechmike", None), "led_soll", None),
                    "transcript": self.transcript_text.get("1.0", "end-1c")[:400],
                    "result": self.result_text.get("1.0", "end-1c")[:600],
                    "result_ende": self.result_text.get("1.0", "end-1c")[-600:],  # v3.13.0: IB-Lab-Zeilen stehen hinten
                    "befund_wartet": bool(getattr(self, "_befund_wartet", False)),
                    "nur_text": bool(self.nur_text_aktiv()),
                    "einfuegungen": getattr(self, "_einfuege_zaehler", 0),
                    "hinweis": getattr(self, "_letzter_hinweis", ""),
                    "repariert": str(self.repariert_label.cget("text")),
                    "zwischenablage": _zwischenablage_lesen()[:600],
                    "status_text": str(self.status_badge.cget("text")).strip(),
                    # v3.10.0: CAS-Auftrag der Brücke (Nummer, Bandtext, Band sichtbar)
                    "cas": self._cas.nr if getattr(self, "_cas", None) is not None else None,
                    "cas_band": str(self.cas_label.cget("text")).strip() if getattr(self, "cas_label", None) else "",
                    "cas_band_sichtbar": bool(getattr(self, "cas_band", None) and self.cas_band.winfo_ismapped()),
                    # v3.12.0: CAS-Leistungen, Hinweise zur Vorlagenwahl, Bestätigung nach EOL, Kopfzeile
                    "cas_leistungen": (self._cas.labels() if getattr(self, "_cas", None) is not None else None),
                    "cas_hinweise": list(getattr(self, "_cas_hinweise", []) or []),
                    "cas_hinweis_label": str(self.cas_hinweis_label.cget("text")).strip()
                    if getattr(self, "cas_hinweis_label", None) else "",
                    "bestaetigung": str(self.bestaetigung_label.cget("text")).strip()
                    if getattr(self, "bestaetigung_label", None) else "",
                    "bestaetigung_sichtbar": bool(getattr(self, "bestaetigung_band", None)
                                                  and self.bestaetigung_band.winfo_ismapped()),
                    "kopf": self._kopf_geometrie(),
                    # v3.13.0: IB-Lab-Bausteine (Band-Zeile, Hinweise, Knopf, Stand im Befund, Menü-Schalter)
                    "ibl_band": str(self.ibl_label.cget("text")).strip() if getattr(self, "ibl_label", None) else "",
                    "ibl_band_sichtbar": bool(getattr(self, "ibl_zeile", None) and self.ibl_zeile.winfo_ismapped()),
                    "ibl_hinweise": list(getattr(self, "_ibl_hinweise", []) or []),
                    "ibl_hinweis_label": str(self.ibl_hinweis_label.cget("text")).strip()
                    if getattr(self, "ibl_hinweis_label", None) else "",
                    "ibl_knopf_sichtbar": bool(getattr(self, "ibl_knopf", None) and self.ibl_knopf.winfo_ismapped()),
                    "ibl_im_befund": {f"{k[1]}": v for k, v in (getattr(self, "_ibl_im_befund", {}) or {}).items()},
                    "ibl_hervorgehoben": int(getattr(self, "_ibl_hervorgehoben", 0)),
                    "ibl_uebernehmen": bool(self._ibl_an()),
                    "befund_titel": befund_titel(self.result_text.get("1.0", "end-1c"), 400),
                    # v3.11.0: Bereitschaft (Fensterzustand, Zweitstarts, Autostart, Minimieren nach CAS-EOL)
                    "fenster": self.state(),
                    "minimiert_gestartet": bool(getattr(self, "_minimiert_gestartet", False)),
                    "zweitstarts": getattr(self, "_zweitstarts", 0),
                    "autostart": bool(self._autostart.an()),
                    "autostart_ziel": self._autostart.ziel(),
                    "autostart_lnk": self._autostart.lnk,
                    "autostart_meldung": getattr(self, "_autostart_meldung", ""),
                    "exe": self._exe_pfad,
                    "symbol": bool(getattr(self, "_symbol_gesetzt", False)),
                    "cas_minimieren": bool(self.nach_cas_minimieren_var.get()),
                    "aufnahme_offen": getattr(self, "_aufnahme", None) is not None,
                    "pid": os.getpid(),
                    "time": time.strftime("%H:%M:%S"),
                }
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
            except Exception as e:
                with open(path + ".err", "a", encoding="utf-8") as f:
                    f.write(f"{phase}: {e}\n")

        def demo():
            if os.environ.get("RAKSCRIBE_SELFTEST_DEMO") == "1":
                self.transcript_text.insert("1.0", "Röntgen und Sonographie des linken Schultergelenkes: Tenosynovitis der langen "
                                                   "Bizepssehne, Tendinopathie und Tendinosis calcarea der Supraspinatussehne mit "
                                                   "Begleitbursitis, ansonsten unauffällig.")
                self.result_text.insert("1.0", "## Röntgen und Sonographie des Schultergelenkes links\n\n## Befund\n"
                                               "Flüssigkeitsansammlung in der Sehnenscheide des Caput longum des M. biceps brachii. "
                                               "Supraspinatussehne echoarm verdickt mit intratendinösen Verkalkungen. Bursa "
                                               "subacromialis-subdeltoidea verdickt. Übrige Sehnen der Rotatorenmanschette intakt.\n\n"
                                               "## Ergebnis\n1. Tenosynovitis der langen Bizepssehne links.\n"
                                               "2. Tendinopathie und Tendinosis calcarea der Supraspinatussehne.\n"
                                               "3. Begleitbursitis subacromialis-subdeltoidea.")
                self.update_level_bar(4500)
            self.after(800, lambda: dump("ready"))

        self.after(1200, lambda: (dump("start"), demo()))
        # Testskript legt <state>.trigger mit Phasen-Namen an → Zustand erneut festhalten
        def poll_trigger():
            trig = path + ".trigger"
            if os.path.exists(trig):
                try:
                    with open(trig, "r", encoding="utf-8") as f:
                        phase = f.read().strip() or "trigger"
                    os.remove(trig)
                    if phase == "simulate_processing":
                        # Fall D (Umbau Schritt 4): „Befund wird erstellt" ohne Aufnahme — danach drückt der Test F10/F9
                        self._job.simuliere_verarbeitung()
                        self.update_status("PROCESSING", "busy")
                        self.record_btn.configure(state="disabled", text=" Verarbeite... (Selbsttest) ")
                    if phase in ("taste_f10", "taste_f9"):
                        # gleicher Handler wie der F10/F9-Hotkey; Zustand erst nach dessen Ausführung festhalten
                        self._hotkeys[phase[-3:].lstrip("_")]()
                        self.after(800, lambda p=phase: dump(p))
                    elif phase.startswith("sm_"):
                        # v3.8.0: SpeechMike-Taste wie vom Gerät (Bericht → Dekodierer → derselbe Handler), z. B. sm_RECORD#1
                        self._selbsttest_taste(phase[3:].split("#")[0])
                        self.after(1500, lambda p=phase: dump(p))
                    elif phase == "befund_aendern":
                        self.result_text.insert("end", "\nVon Hand ergänzt.")
                        dump(phase)
                    elif phase.startswith("cas_"):
                        # v3.10.0: Knöpfe im CAS-Band (cas_testbefund, cas_eol, cas_ins, cas_abbrechen) bzw. nur Zustand
                        aktion = {"cas_testbefund": self.cas_testbefund, "cas_eol": self.befund_fertig,
                                  "cas_ins": self.sm_ins, "cas_abbrechen": self.cas_abbrechen,
                                  "cas_ibl_einfuegen": self.ibl_einfuegen}.get(phase.split("#")[0])  # v3.13.0 Knopf
                        if aktion:
                            aktion()
                        self.after(1500, lambda p=phase: dump(p))
                    elif phase.startswith("kopfzeile#"):
                        # v3.12.0: Kopfzeile bei Fensterbreite <n> mit „SpeechMike verbunden“ und langem Status
                        breite = int(phase.split("#", 1)[1])
                        self.state("normal")
                        self.geometry(f"{breite}x760")
                        self._speechmike_status("Selbsttest")
                        self.update_status("KONTROLLE", "ready")
                        self.after(1200, lambda p=phase: dump(p))
                    elif phase.startswith("text_ins#"):
                        # v3.12.0: getippter Text → INS (wie SpeechMike-INS aus dem Diktat-Feld), z. B. mit CAS-Leistungen
                        text = phase.partition("|")[2]
                        self.transcript_text.delete("1.0", "end")
                        self.transcript_text.insert("1.0", text)
                        self.befund_aus_text(kontrolle=True)
                        self.after(2500, lambda p=phase: dump(p))
                    elif phase.startswith(("autostart_an", "autostart_aus")):
                        # v3.11.0: derselbe Handler wie der Menü-Haken „Mit Windows starten (wartet minimiert)“
                        self.autostart_var.set(phase.startswith("autostart_an"))
                        self._autostart_umschalten()
                        self.after(800, lambda p=phase: dump(p))
                    elif phase.startswith("minimieren"):
                        self.iconify()
                        self.after(800, lambda p=phase: dump(p))
                    elif phase == "ende":  # v3.13.0: Selbsttest beendet sich selbst (wie Fenster schließen)
                        dump(phase)
                        self._schliessen()
                        return
                    else:
                        dump(phase)
                except Exception:
                    pass
            self.after(300, poll_trigger)
        self.after(1500, poll_trigger)
        # v3.13.0 (Ordi-Probelauf am Büro-PC: nur Läufe, die von selbst enden): RAKSCRIBE_SELFTEST_ENDE=<Sekunden> →
        # Zustand „ende“ festhalten und RaKScribe schließen wie mit X (offener CAS-Auftrag → „abgebrochen“)
        try:
            ende_ms = int(float(os.environ.get("RAKSCRIBE_SELFTEST_ENDE") or 0) * 1000)
        except ValueError:
            ende_ms = 0
        if ende_ms > 0:
            self.after(ende_ms, lambda: (dump("ende"), self._schliessen()))

    def _selbsttest_taste(self, taste):
        """Selbsttest: Druck- und Loslass-Bericht einer SpeechMike-Taste durch den echten Dekodierer schicken."""
        smk = getattr(self, "_speechmike", None)
        if smk is None:
            return
        bit = dict(_sm.TASTEN)[taste]
        self._st_zeit = getattr(self, "_st_zeit", 1000.0) + 1.0
        smk.einspeisen([0x80, 0, 0, 0, 0, 0, 0, bit & 0xFF, bit >> 8], self._st_zeit)
        smk.einspeisen([0x80, 0, 0, 0, 0, 0, 0, 0, 0], self._st_zeit + 0.1)

    # ── v3.0: Befund-Formatierung (## versteckt, Überschriften fett) — Text bleibt Markdown für Kopieren ──
    def _setup_report_formatting(self):
        tb = self.result_text._textbox
        tb.tag_configure("md_hidden", elide=True)
        tb.tag_configure("md_title", font=(UI_FONT, 17, "bold"), foreground=ACCENT_PURPLE, spacing1=2, spacing3=6)
        tb.tag_configure("md_head", font=(UI_FONT, 15, "bold"), foreground="#FFFFFF", spacing1=12, spacing3=4)
        # v3.13.2 (Peter 14.10.: „die Titel BWS und LWS sind unterschiedlich eingefärbt“): JEDER Untersuchungstitel wie der
        # erste – nur „Befund“/„Ergebnis“ sind Zwischenüberschriften; ab dem zweiten Titel mit Abstand nach oben
        tb.tag_configure("md_title_n", font=(UI_FONT, 17, "bold"), foreground=ACCENT_PURPLE, spacing1=22, spacing3=6)
        tb.configure(spacing2=3, padx=10, pady=8)
        self.transcript_text._textbox.configure(spacing2=3, padx=10, pady=8)

        def on_modified(_evt=None):
            try:
                if not tb.edit_modified():
                    return
                for tag in ("md_hidden", "md_title", "md_title_n", "md_head"):
                    tb.tag_remove(tag, "1.0", "end")
                first = True
                last = int(tb.index("end-1c").split(".")[0])
                for ln in range(1, last + 1):
                    line = tb.get(f"{ln}.0", f"{ln}.end")
                    stripped = line.lstrip()
                    if stripped.startswith("#"):
                        lead = len(line) - len(stripped)
                        hashes = len(stripped) - len(stripped.lstrip("#"))
                        pre = lead + hashes + (1 if stripped[hashes:hashes + 1] == " " else 0)
                        tb.tag_add("md_hidden", f"{ln}.0", f"{ln}.{pre}")
                        kopf = line[pre:].strip().rstrip(":").strip().lower()
                        if kopf in ("befund", "ergebnis"):
                            tag = "md_head"
                        else:
                            tag = "md_title" if first else "md_title_n"
                        tb.tag_add(tag, f"{ln}.{pre}", f"{ln}.end")
                        first = False
                    elif stripped:
                        first = False
                tb.edit_modified(False)
            except Exception:
                pass

        tb.bind("<<Modified>>", on_modified)

    # ── v3.0: Menü ──
    def open_menu(self):
        m = tk.Menu(self, tearoff=0, bg=BGC_ELEV, fg=TEXT_PRIMARY, activebackground=BGC_CARD,
                    activeforeground="#FFFFFF", bd=0, font=(UI_FONT, 11))
        m.add_command(label="Schlüssel-Datei laden…", command=self.load_key_dialog)
        if _praxis_key_path() == USER_KEY_PATH:
            m.add_command(label="Gespeicherten Schlüssel entfernen", command=self.remove_user_key)
        m.add_separator()
        m.add_checkbutton(label="Diktat in den Befund: Satzanfang groß", variable=self.gross_satzanfang_var,
                          command=lambda: einstellung_schreiben("gross_satzanfang", bool(self.gross_satzanfang_var.get())))
        m.add_separator()
        # v3.11.0 (Peter 13.10.): Bereitschaft. „An“ heißt: die Verknüpfung liegt im Benutzer-Autostart.
        self.autostart_var.set(self._autostart.an())
        m.add_checkbutton(label="Mit Windows starten (wartet minimiert)", variable=self.autostart_var,
                          command=self._autostart_umschalten, state="normal" if self._exe_pfad else "disabled")
        if self.autostart_var.get():
            ziel = self._autostart.ziel()
            m.add_command(label="   wartet auf: " + _kurzpfad(ziel or "? (Starter fehlt)"), state="disabled")
            if self._exe_pfad and not _bs.gleicher_pfad(ziel, self._exe_pfad):
                m.add_command(label="   → auf diese EXE umstellen", command=self._autostart_umstellen)
        m.add_checkbutton(label="Nach CAS-Befund minimieren", variable=self.nach_cas_minimieren_var,
                          command=lambda: einstellung_schreiben("cas_minimieren", bool(self.nach_cas_minimieren_var.get())))
        m.add_checkbutton(label="IB-Lab-Bausteine übernehmen", variable=self.ibl_var,  # v3.13.0
                          command=self._ibl_umgeschaltet)
        m.add_separator()
        m.add_command(label="Prompt bearbeiten…", command=self.toggle_prompt_view)
        m.add_command(label="Web-App öffnen", command=lambda: __import__("webbrowser").open(
            "https://drpeterkalmar.github.io/RaKScribe26/"))
        m.add_separator()
        m.add_checkbutton(label="SpeechMike-Steuerung (Tasten + Lämpchen)", variable=self.speechmike_var,
                          command=self._speechmike_umschalten)
        smk = getattr(self, "_speechmike", None)
        m.add_command(label="SpeechMike-Diagnose…" + (f"  ({smk.verbunden})" if smk is not None and smk.verbunden
                                                      else "  (nicht verbunden)"), command=self.speechmike_diagnose)
        m.add_separator()
        m.add_command(label=f"STT: Google chirp_3 · LLM: Gemini 3.5 Flash (EU)", state="disabled")
        m.add_command(label="F10 Aufnahme · F9 Neu", state="disabled")
        for zeile in HILFE_SPEECHMIKE:
            m.add_command(label=zeile, state="disabled")
        m.add_command(label="CAS-Diktat (blaues Band): F11 = INS · F12 = EOL → an CAS", state="disabled")  # v3.10.0
        x = self.menu_btn.winfo_rootx()
        y = self.menu_btn.winfo_rooty() + self.menu_btn.winfo_height() + 4
        try:
            m.tk_popup(x - 250, y)
        finally:
            m.grab_release()

    # ── v3.0: Schlüssel laden / Sperre ──
    def load_key_dialog(self):
        from tkinter import filedialog
        import shutil
        path = filedialog.askopenfilename(title="rakscribe-praxis-key.json wählen",
                                          filetypes=[("Praxis-Schlüssel", "*.json"), ("Alle Dateien", "*.*")])
        if not path:
            return
        try:
            data = json.loads(_read_text_robust(path))
            if not _keys.ist_praxis_schluessel(data):
                raise ValueError("kein kombinierter Praxis-Schlüssel")
            os.makedirs(USER_KEY_DIR, exist_ok=True)
            shutil.copyfile(path, USER_KEY_PATH)
        except Exception as e:
            messagebox.showerror("Schlüssel nicht erkannt",
                                 "Bitte rakscribe-praxis-key.json aus dem Drive-Ordner „RaKScribe“ wählen.\n\n"
                                 f"Details: {e}")
            return
        global speech_client
        speech_client = None
        init_google_speech()
        self.refresh_key_state()
        if keys_ready():
            messagebox.showinfo("Schlüssel geladen", "Praxis-Schlüssel gespeichert — RaKScribe ist bereit.\n"
                                "Er bleibt auch nach EXE-Updates erhalten.")

    def remove_user_key(self):
        if not messagebox.askyesno("Schlüssel entfernen", "Gespeicherten Praxis-Schlüssel entfernen?"):
            return
        try:
            os.remove(USER_KEY_PATH)
        except Exception:
            pass
        global speech_client, _SA_CREDENTIALS
        speech_client = None
        _SA_CREDENTIALS = None
        init_google_speech()
        self.refresh_key_state()

    def refresh_key_state(self):
        ok = keys_ready()
        if ok:
            self._job.entsperren()
            self.key_chip.configure(text="  ✓ Schlüssel aktiv  ", fg_color="#15261F", text_color=READY_GREEN)
            if self.gate is not None:
                self.gate.destroy()
                self.gate = None
            if not self.is_recording and self._status_raw in ("LOCKED", "READY"):
                self.update_status("READY", "ready")
            self.record_btn.configure(state="normal")
        else:
            self._job.sperren()
            self.key_chip.configure(text="  Kein Schlüssel  ", fg_color="#2D2413", text_color=WARN_AMBER)
            self.record_btn.configure(state="disabled")
            self.update_status("LOCKED", "ready")
            self._show_gate()

    def _show_gate(self):
        if self.gate is not None:
            return
        self.gate = ctk.CTkFrame(self.main_container, fg_color=BGC_MAIN, corner_radius=0)
        self.gate.place(relx=0, rely=0, relwidth=1, relheight=1)
        box = ctk.CTkFrame(self.gate, fg_color=BGC_ELEV, corner_radius=18, border_width=1,
                           border_color=BORDER_STRONG, width=460, height=330)
        box.place(relx=0.5, rely=0.46, anchor="center")
        box.pack_propagate(False)
        ctk.CTkLabel(box, text="🔑", font=(UI_FONT, 30), width=58, height=58, corner_radius=16,
                     fg_color="#1A2640").pack(pady=(28, 10))
        ctk.CTkLabel(box, text="Praxis-Schlüssel laden", font=(UI_FONT, 20, "bold"),
                     text_color=TEXT_PRIMARY).pack()
        ctk.CTkLabel(box, text="RaKScribe ist gesperrt, bis der Schlüssel geladen ist.\n"
                               "Datei: rakscribe-praxis-key.json (Drive-Ordner „RaKScribe“)",
                     font=(UI_FONT, 13), text_color=TEXT_MUTED, justify="center").pack(pady=(8, 18))
        ctk.CTkButton(box, text="Schlüssel-Datei wählen…", height=46, width=320, corner_radius=10,
                      font=(UI_FONT, 14, "bold"), fg_color=ACCENT_PURPLE, hover_color=ACCENT_HOVER,
                      command=self.load_key_dialog).pack()
        ctk.CTkLabel(box, text="Einmal laden genügt — bleibt auch nach Updates gespeichert.",
                     font=(UI_FONT, 11), text_color=TEXT_FAINT).pack(pady=(14, 0))

    def on_device_changed(self, choice):
        self.selected_device_index = self.device_mapping.get(choice, sd.default.device[0])
        print(f"[AUDIO] Eingabegerät geändert auf: {choice} (Index: {self.selected_device_index})")

    def toggle_prompt_view(self):
        if self.prompt_window is None or not self.prompt_window.winfo_exists():
            self.prompt_window = ctk.CTkToplevel(self)
            self.prompt_window.title("System Prompt Konfiguration")
            self.prompt_window.geometry("600x500")
            self.prompt_window.after(10, lambda: self.prompt_window.focus())
            
            txt = ctk.CTkTextbox(self.prompt_window, font=("Consolas", 12))
            txt.pack(fill="both", expand=True, padx=20, pady=20)
            txt.insert("1.0", INITIAL_PROMPT_CONTENT)
            
            def save():
                global INITIAL_PROMPT_CONTENT
                INITIAL_PROMPT_CONTENT = txt.get("1.0", "end-1c")
                try:
                    with open(os.path.join(BASE_DIR, "radiology_prompt.txt"), 'w', encoding='utf-8') as f:
                        f.write(INITIAL_PROMPT_CONTENT)
                except: pass
                self.prompt_window.destroy()

            ctk.CTkButton(self.prompt_window, text="Speichern", command=save, fg_color=ACCENT_PURPLE).pack(pady=(0, 20))
        else:
            self.prompt_window.focus()

    def update_status(self, text, type="ready"):
        raw = (text or "").upper()
        self._status_raw = raw
        label, dot, bg = STATUS_STYLE.get(raw, (text, {"busy": WARN_AMBER, "recording": RECORDING_RED}.get(type, READY_GREEN), "#1B2030"))
        if raw == "RECORDING" and getattr(self, "_live_aus", False):
            label += " · Live-Anzeige ausgefallen"  # Umbau Schritt 6: Aufnahme läuft trotzdem weiter
        self.status_badge.configure(text=f"   ●  {label}   ", fg_color=bg, text_color=TEXT_PRIMARY)
        # farbiger Punkt: CTkLabel kann nur eine Textfarbe → Pill-Rand über Hintergrund, Punkt in Textfarbe des Status
        self.status_badge.configure(text_color=dot if raw in ("RECORDING", "PAUSED", "ERROR", "PROCESSING", "LOCKED")
                                    else TEXT_PRIMARY)
        self._led_aktualisieren()  # v3.8.0: SpeechMike-LED folgt dem Zustand

    def update_recording_timer(self):
        if self.is_recording:
            elapsed = int(time.time() - self.recording_start_time)
            pause = self._job.zustand == _js.PAUSED  # v3.8.0
            self.record_btn.configure(text=" Aufnahme Stoppen (F10) · Pause " if pause
                                      else f" Aufnahme Stoppen (F10) ({elapsed}s) ")
            self.after(1000, self.update_recording_timer)

    def update_processing_timer(self):
        if not self.is_recording and self._status_raw == "PROCESSING":
            elapsed = int(time.time() - self.processing_start_time)
            remaining = max(0, self.eta_seconds - elapsed)
            if remaining > 0:
                self.record_btn.configure(text=f" Verarbeite... {elapsed}s (ca. {remaining}s verbleibend) ")
            else:
                self.record_btn.configure(text=f" Fast fertig... {elapsed}s ")
            self.after(1000, self.update_processing_timer)

    def reset_dictation(self):
        # F9/Neu: läuft eine Aufnahme → Mikrofon zu, nichts verarbeiten; läuft die Verarbeitung → Lauf abbrechen
        # (v3.2.3, Gutachten P1-2: Ergebnis wird verworfen, nichts eingefügt). Die Generationsnummer steigt in jedem Fall.
        aktion = self._job.ereignis("reset")
        if aktion == "stop_und_reset":
            self.is_recording = False
            self._aufnahme_stoppen()
        elif aktion == "abbrechen":
            log("[UI] Verarbeitung abgebrochen (F9) — Ergebnis wird verworfen.")
        log("[UI] Zurücksetzen angefordert. Lösche Transkription, Befund und Aufnahmedaten.")
        self.final_transcript = ""
        self.stream_transcript = ""
        self.stream_interim = ""
        self._einfuegen_ziel = None
        self._sm_sitzung_leeren()  # v3.8.0: Nachdiktat/Abschnitte/Kontrollschritt verwerfen
        if getattr(self, "_cas", None) is not None:  # v3.10.0: F9 leert nur das Diktat, der CAS-Auftrag bleibt offen
            self._cas_aufnahmen, self._cas_test = [], False
            self._cas_hinweise_zeigen([])
            self._ibl_befund_leeren()  # v3.13.0: die Bausteine bleiben beim Auftrag, nur ihr Stand im Befund geht
        self.transcript_text.delete("1.0", "end")
        self.result_text.delete("1.0", "end")
        if getattr(self, "_cas", None) is not None:
            self._ibl_band_zeigen()
        if self._job.zustand == _js.LOCKED:
            self.refresh_key_state()
        else:
            self.update_status("READY", "ready")
            self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE)
        self.level_indicator.configure(width=0)

    def _aufnahme_stoppen(self):
        if self._aufnahme is not None:
            self._aufnahme.stop()  # der Capture-Thread schließt das Mikrofon

    def _aufnahme_starten(self, gen):
        """Mikrofon (Capture-Thread) und Live-Anzeige (Streaming-Thread) getrennt starten (Gutachten P1-4)."""
        a = _af.Aufnahme(
            sd, self.samplerate, self.selected_device_index,
            streaming=lambda reqs: speech_client.streaming_recognize(requests=reqs, config=STREAMING_CONFIG),
            request_bauen=lambda b: speech.StreamingRecognizeRequest(audio_content=b),
            on_level=lambda rms: self.after(0, self.update_level_bar, rms),
            on_stream_fehler=lambda e: self._live_anzeige_fehler(gen, e),
            on_capture_fehler=lambda e: self._capture_fehler(gen, e),
            log=log)
        # Streaming-Text mit der Abschnittsnummer seiner Sitzung (v3.8.0: Anzeige nach SpeechMike-Pausen)
        a.on_text = lambda text, is_final: self.after(0, self.update_interim_text, text, is_final, gen, a.stream_abschnitt)
        self._aufnahme = a
        if getattr(self, "_cas", None) is not None:  # v3.10.0: Aufnahmen dieses CAS-Diktats sammeln (→ <Nr>.wav)
            if not self._basis:
                self._cas_aufnahmen = []  # neues Diktat statt Nachdiktat: frühere Aufnahmen gehören nicht dazu
            self._cas_aufnahmen.append(a)
        a.start()

    def _live_anzeige_fehler(self, gen, e):
        """Streaming-Thread: Fehler der Live-Anzeige — nur loggen und anzeigen, die Aufnahme läuft weiter (P1-4)."""
        log_exception("[GOOGLE] Live-Anzeige ausgefallen — Aufnahme läuft weiter")

        def zeigen():
            self._live_aus = True
            if self._status_raw == "RECORDING":
                self.update_status("RECORDING", "recording")
        self._ui(gen, zeigen)

    def _capture_fehler(self, gen, e):
        """Capture-Thread: Mikrofon nicht nutzbar → Aufnahme abbrechen (wie bisher)."""
        log_exception("[RECORD] Fehler im Capture-Thread")
        self._ui(gen, lambda: messagebox.showerror("Aufnahme-Fehler", f"Das Mikrofon konnte nicht genutzt werden:\n{e}"))
        self.after(0, self.cancel_recording_due_to_error, gen)

    def _ui(self, gen, fn):
        """UI-Änderung aus einem Hintergrund-Thread — nur, wenn der Lauf gen noch aktuell ist."""
        self.after(0, lambda: fn() if self._job.aktuell(gen) else None)

    def toggle_recording(self):
        self._toggle_calls = getattr(self, "_toggle_calls", 0) + 1
        aktion = self._job.vorschau("toggle")
        if aktion is None:
            if self._job.zustand == _js.PROCESSING:
                # v3.2.3 (Gutachten P1-2): F10 während "Befund wird erstellt" ignorieren — sonst startete eine neue
                # Aufnahme in den laufenden Job hinein (vermischte/leere Befunde, "Bereit" bei laufendem Mikrofon).
                log("[RECORD] F10 während der Verarbeitung ignoriert.")
            else:
                self.refresh_key_state()  # gesperrt: Schlüssel fehlt
            return
        self._aufnahme_umschalten("toggle", aktion)

    def _aufnahme_umschalten(self, ereignis, aktion, basis="", kontrolle=False):
        """Aufnahme starten bzw. beenden — F10 (ereignis "toggle") und SpeechMike (record/ins) über DENSELBEN Weg.
        v3.8.0: basis = bisheriges Diktat (SpeechMike-Nachdiktat, F10: immer leer), kontrolle = Ergebnis nur anzeigen
        und NICHT einfügen (SpeechMike-INS; F10: False = wie bisher kopieren + einfügen)."""
        if aktion == "start" and not keys_ready():
            self.refresh_key_state()
            return
        if not speech_client:
            if not init_google_speech():
                messagebox.showerror("Fehler", "Google Cloud Speech-to-Text konnte nicht initialisiert werden. Bitte prüfen Sie Ihre Credentials (JSON-Datei) und die Internetverbindung.")
                return
        self._job.ereignis(ereignis)
        gen = self._job.gen

        if aktion == "start":
            log("[RECORD] Aufnahme wird gestartet...")
            self._einfuegen_ziel = self._einfuege_ziel_ermitteln()
            if self._einfuegen_ziel is not None:
                log(f"[EINFÜGEN] Diktat wird an Stelle {self._einfuegen_ziel} in den Befund eingefügt.")
            self.final_transcript = ""
            self.stream_transcript = ""
            self.stream_interim = ""
            self._live_aus = False
            self._basis, self._abschnitte, self._live = basis, [], {}
            self._kontroll_gen, self._befund_wartet, self._gesendet = None, False, False
            if getattr(self, "_cas", None) is not None:
                self._cas_hinweise_zeigen([])  # v3.12.0: Hinweise gehören zum vorigen Befund
                self._ibl_befund_leeren()      # v3.13.0: ebenso der Stand der IB-Lab-Werte im Befund
            self.transcript_text.delete("1.0", "end")
            if basis:
                self.transcript_text.insert("1.0", basis)  # Nachdiktat: bisheriges Diktat bleibt stehen
            if self._einfuegen_ziel is None and not basis:  # Nachdiktat: alter Befund bleibt bis zum nächsten INS
                self.result_text.delete("1.0", "end")
            self.is_recording = True
            
            self.update_status("RECORDING", "recording")
            if self._einfuegen_ziel is not None:
                self.status_badge.configure(text="   ●  Diktat wird an der Cursor-Stelle eingefügt   ")
            self.record_btn.configure(text=" Aufnahme Stoppen (F10) (0s) ", fg_color=RECORDING_RED)
            self.level_indicator.configure(fg_color=READY_GREEN, width=0)

            self.recording_start_time = time.time()
            self.update_recording_timer()

            self._aufnahme_starten(gen)
            log("[RECORD] Aufnahme- und Live-Anzeige-Thread gestartet.")
        else:
            if kontrolle:
                self._kontroll_gen = gen  # v3.8.0 INS: Befund nur anzeigen, EOL schickt ihn weiter
            log("[RECORD] Aufnahme wird beendet...")
            self.is_recording = False
            self._aufnahme_stoppen()
            self._repariert_anzeigen()

            self.update_status("PROCESSING", "busy")
            
            # Schätze ETA basierend darauf, ob es ein Normalbefund ist
            raw_est = self.transcript_text.get("1.0", "end-1c").strip()
            if raw_est.startswith("[..") and raw_est.endswith("..]"):
                raw_est = raw_est[3:-3].strip()
            
            is_normal = _nb.is_pure_normal_finding(raw_est, DISPLAY_NAMES) if raw_est else False
            if is_normal:
                self.eta_seconds = 1
            else:
                self.eta_seconds = 120

            self.processing_start_time = time.time()
            self.record_btn.configure(state="disabled", text=f" Verarbeite... (ca. {self.eta_seconds}s) ")
            self.update_processing_timer()

            def wait_and_process():
                try:
                    self._warten_und_verarbeiten(gen)
                except Exception as e:
                    log_exception("[PROCESS] Unerwarteter Fehler")
                    self.after(0, lambda m=f"Fehler bei der Verarbeitung:\n{e}": self._ende_fehler(gen, m))

            threading.Thread(target=wait_and_process, daemon=True).start()

    def _warten_und_verarbeiten(self, gen):
        log("[PROCESS] Warte auf Mikrofon und Live-Anzeige...")
        aufnahme = self._aufnahme
        if aufnahme is not None:
            aufnahme.warten(timeout_stream=6.0)  # letzte Streaming-Antworten dürfen noch eintreffen
        log("[PROCESS] Aufnahme-Threads beendet oder Timeout erreicht.")

        # ═══ CHIRP 3 Volltranskription (v2.9.10) ═══
        # Das Streaming dient nur der Live-Anzeige. Für die finale Transkription wird die KOMPLETTE Aufnahme
        # noch einmal an chirp_3 (STT v2, WER 2,4% vs 16,7%) geschickt.
        chirp_text = None
        try:
            all_pcm = aufnahme.samples() if aufnahme is not None else None  # vollständiger Puffer, auch nach Streaming-Fehler
            if all_pcm is not None and len(all_pcm) > 16000:
                log(f"[CHIRP3] Volltranskription: {len(all_pcm)/16000:.0f}s Audio")
                self._ui(gen, lambda: self.update_status("PROCESSING", "busy"))
                token = _get_stt_access_token()
                chirp_text = _chirp3_worker(all_pcm, 16000, 'eu', token) if token else None
        except Exception:
            log_exception("[CHIRP3] Volltranskription fehlgeschlagen — Streaming-Transkript bleibt.")
        if not self._job.aktuell(gen):
            log("[PROCESS] Lauf abgebrochen — chirp_3-Ergebnis verworfen, keine Befund-Erstellung.")
            return

        # Endtext festlegen: ab hier keine Streaming-Antworten mehr übernehmen (Gutachten P2-5)
        self._job.ereignis("chirp_done", gen)
        basis = getattr(self, "_basis", "")
        self._neuer_text = ""  # v3.8.0: nur das in DIESER Aufnahme Diktierte (Einfügen an der Cursor-Stelle)
        if chirp_text and chirp_text.strip():
            self._neuer_text = chirp_text.strip()
            self.final_transcript = (basis + " " + self._neuer_text).strip()  # v3.8.0: Nachdiktat hängt an
            log(f"[CHIRP3] OK: {len(self.final_transcript)} Zeichen")
            text = self.final_transcript
            self._ui(gen, lambda: (
                self.transcript_text.delete("1.0", "end"),
                self.transcript_text.insert("1.0", text)
            ))
        else:
            log("[CHIRP3] Kein Ergebnis — nutze Streaming-Transkript weiter.")
            # Rettung: finale Streaming-Abschnitte, sonst der letzte Zwischenstand (wie bisher aus der Anzeige)
            if basis or getattr(self, "_abschnitte", []):  # v3.8.0: Nachdiktat / reparierte Abschnitte nach Pausen
                self._neuer_text = _seg.rettung("", self._abschnitte, getattr(self, "_live", {}))
                salvaged = (basis + " " + self._neuer_text).strip()
            else:
                salvaged = self.stream_transcript.strip() or self.stream_interim.strip()
                self._neuer_text = salvaged
            if salvaged:
                self.final_transcript = salvaged
                log(f"[GOOGLE] Text gerettet: {len(salvaged)} Zeichen")

        self.process_dictation(gen)

    def cancel_recording_due_to_error(self, gen):
        if self._job.ereignis("capture_failed", gen) is None:
            return  # Fehler einer alten Aufnahme — die laufende nicht abwürgen
        log("[RECORD] Aufnahme aufgrund eines Fehlers abgebrochen.")
        self.is_recording = False
        self._aufnahme_stoppen()
        self.update_status("ERROR", "busy")
        self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE)
        self.level_indicator.configure(fg_color=READY_GREEN, width=0)

    def update_interim_text(self, transcript, is_final, gen, abschnitt=0):
        # Gutachten P2-5: Streaming-Text nur für die Anzeige (stream_transcript), nie in final_transcript; nach dem
        # Endtext (chirp_3) oder aus einem alten Lauf verwirft die Zustandsmaschine verspätete Antworten.
        # v3.8.0: je Abschnitt (SpeechMike-Pausen) — ein reparierter Abschnitt ersetzt seinen Live-Text (segmente.py).
        if self._job.ereignis("stream_final" if is_final else "stream_interim", gen) is None:
            return
        live = self._live.setdefault(abschnitt, ["", ""])
        if not is_final:
            self.stream_interim = transcript
            live[1] = transcript
        else:
            log(f"[GOOGLE] Finaler Zwischenabschnitt erkannt: {len(transcript)} Zeichen")
            self.stream_transcript += transcript + " "
            self.stream_interim = ""
            live[0] += transcript + " "
            live[1] = ""
        self._diktat_anzeigen()

    def update_level_bar(self, rms):
        max_val = 10000  # Kalibriert auf typische Sprachlautstärke (vorher 1500)
        level = min(rms / max_val, 1.0)
        self.level_indicator.configure(width=level * self.level_container.winfo_width())
        # Dynamische Pegel-Farben (Grün -> Gelb -> Rot)
        color = READY_GREEN
        if level > 0.8:
            color = RECORDING_RED
        elif level > 0.4:
            color = "#F39C12"
        self.level_indicator.configure(fg_color=color)

    def _einfuege_ziel_ermitteln(self):
        """v3.5.0 (Peter 07.10.): Steht der Cursor im Befund-Feld (Fokus dort, RaKScribe vorne, Befund nicht leer),
        wird das nächste Diktat als korrigierter Text an dieser Stelle eingefügt bzw. ersetzt die Markierung.
        Rückgabe (start, ende) als Zeichen-Offsets im Befundtext oder None (= normales Diktat)."""
        try:
            tb = self.result_text._textbox
            if not self.result_text.get("1.0", "end-1c").strip():
                return None
            if self.focus_get() is not tb or not _fokus_ist_eigenes_fenster():
                return None
            if tb.tag_ranges("sel"):
                a, b = tb.index("sel.first"), tb.index("sel.last")
            else:
                a = b = tb.index("insert")
            # Tk-Marken wandern mit, falls während der Aufnahme im Befund getippt wird
            tb.mark_set("diktat_a", a)
            tb.mark_gravity("diktat_a", "left")
            tb.mark_set("diktat_b", b)
            tb.mark_gravity("diktat_b", "right")
            return self._offset(a), self._offset(b)
        except Exception as e:
            log(f"[EINFÜGEN] Cursor-Stelle nicht lesbar: {e}")
            return None

    def _offset(self, index):
        r = self.result_text._textbox.count("1.0", index, "chars")
        return int((r[0] if isinstance(r, tuple) else r) or 0)

    def _einfuegen_an_ziel(self, gen, ziel, text):
        """Läuft im UI-Thread: korrigierten Text an der gemerkten Stelle einsetzen, Cursor dahinter."""
        if not self._job.aktuell(gen):
            return
        try:  # aktuelle Lage der Marken (falls inzwischen getippt wurde)
            ziel = (self._offset("diktat_a"), self._offset("diktat_b"))
        except Exception:
            pass
        v = getattr(self, "gross_satzanfang_var", None)
        gross = bool(v.get()) if v is not None else True
        neu, cursor = _einf.einfuegen(self.result_text.get("1.0", "end-1c"), ziel[0], ziel[1], text, gross=gross)
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", neu)
        try:
            tb = self.result_text._textbox
            tb.mark_set("insert", f"1.0+{cursor}c")
            tb.see("insert")
            tb.focus_set()
        except Exception:
            pass

    def nur_text_aktiv(self):
        v = getattr(self, "nur_text_var", None)
        return bool(v.get()) if v is not None else False

    def _nur_text_umgeschaltet(self):
        an = self.nur_text_aktiv()
        einstellung_schreiben("nur_text", an)
        log(f"[MODUS] Nur Text {'an' if an else 'aus'}")

    def befund_aus_text(self, _evt=None, kontrolle=False):
        """v3.6.0 (Peter 07.10.): getippten/eingefügten Text im Diktat-Feld ohne Aufnahme zu einem strukturierten
        Befund machen (Knopf „Befund aus Text“ bzw. Strg+Enter im Diktat-Feld). Gleiche Kette wie nach einer Aufnahme
        (Fehlhör-Liste → Bausteine → Regionen → Bypass/Gemini), immer strukturiert — auch wenn „Nur Text“ an ist."""
        text = self.transcript_text.get("1.0", "end-1c").strip()
        if not text:
            if kontrolle:  # v3.8.0 SpeechMike-INS ohne Diktat: Hinweis statt Dialog
                self._kurzhinweis("Kein Diktat – erst Record drücken")
                return "break"
            messagebox.showinfo("Befund aus Text", "Bitte zuerst den Diktattext links eintippen oder einfügen.")
            return "break"
        if not keys_ready():
            self.refresh_key_state()
            return "break"
        if self._job.ereignis("ins" if kontrolle else "text") is None:  # Aufnahme oder Verarbeitung läuft
            return "break"
        gen = self._job.gen
        # v3.8.0 SpeechMike-INS: Ergebnis nur anzeigen (EOL schickt weiter); bei „Nur Text“ der korrigierte Text
        self._kontroll_gen = gen if kontrolle else None
        self._befund_wartet = self._gesendet = False
        nur_befund = not (kontrolle and self.nur_text_aktiv())
        log(f"[TEXT] Befund aus getipptem Text ({len(text)} Zeichen).")
        self.final_transcript = text
        self._einfuegen_ziel = None
        self.result_text.delete("1.0", "end")
        self.update_status("PROCESSING", "busy")
        self.record_btn.configure(state="disabled", text=" Verarbeite... ")
        threading.Thread(target=lambda: self.process_dictation(gen, nur_befund=nur_befund), daemon=True).start()
        return "break"

    def process_dictation(self, gen, nur_befund=False):
        try:
            # Umbau Schritt 15: die ganze Kette ohne Oberfläche in pipeline.py (dieselbe Funktion wie prod_pipeline)
            ziel = None if nur_befund else getattr(self, "_einfuegen_ziel", None)
            if ziel is not None:  # v3.5.0: Diktat an der Cursor-Stelle in den bestehenden Befund (korrigierter Text)
                # v3.8.0: nur das NEU Diktierte einfügen — beim SpeechMike-Nachdiktat steht links das Gesamtdiktat
                erg = _pl.nur_text_aus_diktat(getattr(self, "_neuer_text", "") or self.final_transcript, _pipeline_kontext())
                if erg.leer:
                    self.after(0, lambda: self._ende_kein_text(gen))
                    return
                if not self._job.aktuell(gen):
                    log("[PROCESS] Lauf abgebrochen — Text verworfen, nichts eingefügt.")
                    return
                self.after(0, lambda t=erg.report: self._einfuegen_an_ziel(gen, ziel, t))
                self.after(0, lambda: self._lauf_fertig(gen))
                return
            if self.nur_text_aktiv() and not nur_befund:  # v3.4.0: nur korrigierte Spracherkennung (Call 0), kein Befund
                self._ui(gen, lambda: (self.result_text.delete("1.0", "end"),
                                       self.result_text.insert("1.0", "... Text wird korrigiert ...")))
                erg = _pl.nur_text_aus_diktat(self.final_transcript, _pipeline_kontext())
                if erg.leer:
                    self.after(0, lambda: self._ende_kein_text(gen))
                    return
                if not self._job.aktuell(gen):
                    log("[PROCESS] Lauf abgebrochen — Text verworfen, nichts eingefügt.")
                    return
                self._ui(gen, lambda r=erg.report: (self.result_text.delete("1.0", "end"),
                                                    self.result_text.insert("1.0", r)))
                self.after(0, lambda: self._lauf_fertig(gen))
                return
            cas = self._cas_hinweis_fuer_lauf()  # v3.12.0: CAS-Leistungen als Vorrang-Hinweis (None = wie bisher)
            ibl = self._ibl_fuer_lauf()  # v3.13.0: IB-Lab-Bausteine, nach der KI wörtlich eingesetzt (None = wie bisher)
            erg = _pl.befund_aus_diktat(self.final_transcript, _pipeline_kontext(cas, ibl), beim_start=lambda: self._ui(gen, lambda: (
                self.result_text.delete("1.0", "end"),
                self.result_text.insert("1.0", "... Befund wird geladen ...")
            )))
            if erg.leer:
                self.after(0, lambda: self._ende_kein_text(gen))
                return
            report, fehler, ausnahmen = erg.report, erg.fehler, erg.ausnahmen
            if cas is not None:
                self._ui(gen, lambda h=erg.cas_hinweise: self._cas_hinweise_zeigen(h))
            if getattr(self, "_cas", None) is not None:  # v3.13.0: Stand der IB-Lab-Werte gehört zu diesem Befund
                self._ui(gen, lambda e=erg: self._ibl_nach_lauf(e))

            if not self._job.aktuell(gen):
                log("[PROCESS] Lauf abgebrochen — Befund verworfen, nichts eingefügt.")
                return
            if report:
                self._ui(gen, lambda r=report: (
                    self.result_text.delete("1.0", "end"),
                    self.result_text.insert("1.0", r)
                ))
            if fehler:  # Mehr-Regionen-Befund unvollständig: fertige Teile stehen in der Box, NICHT einfügen
                msg = ("Befund für Region " + ", ".join(f"„{f}“" for f in fehler)
                       + " konnte nicht erstellt werden — bitte erneut diktieren.\n\n"
                       "Die übrigen Regionen stehen im Befund-Feld; es wurde nichts eingefügt.")
                if any("401" in str(e) or "Unauthorized" in str(e) for e in ausnahmen):
                    msg += "\n\n" + GEMINI_401_TEXT
                elif ausnahmen:
                    msg += f"\n\nFehler: {ausnahmen[0]}"
                self.after(0, lambda m=msg: self._ende_fehler(gen, m))
                return
            # v2.11.1 (Prüfbericht W4): leeren/unvollständigen Befund NIE ins Zielprogramm einfügen
            if not erg.vollstaendig:
                self.after(0, lambda: self._ende_fehler(gen, None))
                return
            self.after(0, lambda: self._lauf_fertig(gen))
        except Exception as e:
            log_exception("Befund-Generierung")
            if "401" in str(e) or "Unauthorized" in str(e):
                msg = GEMINI_401_TEXT
            else:
                msg = f"Fehler bei der Befund-Generierung:\n{e}"
            self.after(0, lambda m=msg: self._ende_fehler(gen, m))

    def _ende_kein_text(self, gen):
        if self._job.ereignis("kein_text", gen) is None:
            return
        messagebox.showinfo("Info", "Kein Text diktiert.")
        self.update_status("READY", "ready")
        self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE)
        self.level_indicator.configure(fg_color=READY_GREEN, width=0)

    def _ende_fehler(self, gen, msg):
        """Läuft im UI-Thread: Befund gescheitert → Status Fehler, Knopf wieder frei, ggf. Dialog."""
        if self._job.ereignis("report_failed", gen) is None:
            return
        if msg:
            messagebox.showerror("Generierungs-Fehler", msg)
        self.update_status("ERROR", "busy")
        self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE)
        self.level_indicator.configure(fg_color=READY_GREEN, width=0)

    def copy_formatted_report(self, aus_knopf=False):
        """Befund (Markdown + HTML für Word) in die Zwischenablage. v3.2.3 (Gutachten P1-1): gibt True/False zurück,
        versucht es mehrmals (RIS/Teams halten die Zwischenablage oft kurz fest) und liest gegen (clipboard_win.py)."""
        md_text = self.result_text.get("1.0", "end-1c").strip()
        if not md_text:
            return False
        ok = _cb.clipboard_set(md_text, cb=win32clipboard, md_to_html=markdown.markdown, log=log)
        if ok:
            self.update_status("COPIED", "ready")
        else:
            log("[COPY] Zwischenablage nach mehreren Versuchen nicht gesetzt (von anderem Programm belegt?)")
            if aus_knopf:  # Knopf „Befund kopieren“: Fehlschlag sichtbar machen, sonst fügt der Arzt den alten Inhalt ein
                self.update_status("ERROR", "busy")
                messagebox.showerror("Nicht kopiert", ZWISCHENABLAGE_GESPERRT)
        return ok

    def _lauf_fertig(self, gen):
        """v3.8.0: Ende eines Laufs. F10 und „Befund aus Text“: kopieren + einfügen (wie bisher). SpeechMike-INS: nur
        anzeigen — der Befund wartet auf EOL (Peter 11.10.: nie etwas Ungesehenes weiterschicken).
        v3.10.0: Mit offenem CAS-Auftrag nie Strg+V (auch nicht nach F10) — EOL schickt den Befund an die Brücke."""
        if gen == getattr(self, "_kontroll_gen", None) or getattr(self, "_cas", None) is not None:
            self._fertig_zur_kontrolle(gen)
        else:
            self._fertig_kopieren_einfuegen(gen)

    def _fertig_zur_kontrolle(self, gen):
        if self._job.ereignis("report_done", gen) is None:
            return
        self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE)
        self.level_indicator.configure(fg_color=READY_GREEN, width=0)
        self._befund_wartet, self._gesendet = True, False
        self.update_status("KONTROLLE", "ready")
        log("[SPEECHMIKE] Ergebnis steht rechts zur Kontrolle — nichts eingefügt, EOL schickt es weiter.")

    def _fertig_kopieren_einfuegen(self, gen):
        """Läuft im UI-Thread. Nur einfügen, wenn der Lauf noch aktuell ist UND das Kopieren nachweislich klappte —
        sonst würde Strg+V den vorigen Zwischenablage-Inhalt (= letzten Befund) ins RIS schreiben."""
        if self._job.ereignis("report_done", gen) is None:
            return
        self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE)
        self.level_indicator.configure(fg_color=READY_GREEN, width=0)
        if self.copy_formatted_report():
            self.after(500, lambda: self._job.aktuell(gen) and self._einfuegen())
        else:
            self.update_status("ERROR", "busy")
            messagebox.showerror("Nicht eingefügt", "Der Befund ist fertig, wurde aber NICHT eingefügt.\n\n"
                                 + ZWISCHENABLAGE_GESPERRT)

    def _einfuegen(self):
        """Strg+V ins Vordergrundfenster — außer RaKScribe selbst hat den Fokus (dann liegt der Befund nur kopiert bereit)."""
        if _fokus_ist_eigenes_fenster():
            log("[PASTE] RaKScribe selbst im Vordergrund — kein Strg+V, Befund liegt in der Zwischenablage.")
            self.status_badge.configure(text="   ●  Befund kopiert — im RIS mit Strg+V einfügen   ", text_color=TEXT_PRIMARY)
            return
        self._strg_v()
        self._gesendet = True  # v3.8.0: dieser Befund ist eingefügt — SpeechMike-EOL schickt ihn nicht noch einmal

    def _strg_v(self):
        """Die EINZIGE Stelle, die Strg+V sendet — Aufrufer haben vorher nachweislich erfolgreich kopiert."""
        keyboard.press_and_release('ctrl+v')
        self._einfuege_zaehler = getattr(self, "_einfuege_zaehler", 0) + 1

    # ── v3.8.0: SpeechMike (Peter 11.10., Nachtrag 1–4) ────────────────────────────────────────────────────────────
    # Record = Aufnahme / Pause / Weiter (Pause repariert das bisher Diktierte nur für die Anzeige), Stop = Pause,
    # INS = Befund rechts erstellen (nichts einfügen), EOL = sichtbaren Befund weiterschicken + alles leeren,
    # F1 = Neu, F2 = Nur Text. F10/F9 bleiben exakt wie bisher (register_hotkey).
    def _speechmike_starten(self):
        """Lese-Thread fürs SpeechMike (ohne Gerät/ohne hidapi: eine Protokollzeile, F10/F9 unberührt)."""
        try:
            self._speechmike = _sm.SpeechMikeLeser(
                on_taste=lambda t, gedrueckt, roh: self.after(0, self.speechmike_taste, t, gedrueckt, roh),
                log=log, on_verbindung=lambda b: self.after(0, self._speechmike_status, b))
            self._speechmike.starten()
        except Exception:
            log_exception("[SPEECHMIKE] Start fehlgeschlagen")
            self._speechmike = None

    def _speechmike_umschalten(self):
        """v3.8.2: Menü-Schalter SpeechMike-Steuerung. Aus = Lese-Thread beenden (Lämpchen aus, Gerät geschlossen),
        RaKScribe reagiert auf keine SpeechMike-Taste mehr; F10/F9 bleiben. Die Wahl bleibt gespeichert."""
        an = bool(self.speechmike_var.get())
        einstellung_schreiben("speechmike", an)
        smk = getattr(self, "_speechmike", None)
        if an and smk is None:
            log("[SPEECHMIKE] Steuerung eingeschaltet.")
            self._speechmike_starten()
        elif not an and smk is not None:
            try:
                smk.beenden()
            except Exception:
                log_exception("[SPEECHMIKE] Beenden fehlgeschlagen")
            self._speechmike = None
            log("[SPEECHMIKE] Steuerung ausgeschaltet — Gerät freigegeben.")
            self._speechmike_status(None)

    def _speechmike_status(self, beschreibung):
        self._sm_beschreibung = beschreibung
        chip = getattr(self, "sm_chip", None)
        if chip is not None:
            kurz = getattr(self, "_kopf_breit", True) is False   # v3.12.0: schmales Fenster → kurzer Hinweis
            chip.configure(text=("  SpeechMike ✓  " if kurz else "  SpeechMike verbunden  ") if beschreibung else "",
                           fg_color="#1A2640" if beschreibung else "transparent")
        self._led_aktualisieren()

    def _kopf_anpassen(self, event=None):
        """v3.12.0 (Peter 13.10.: „Bereit“ und „SpeechMike verbunden“ beide lesbar): in einem schmalen Fenster werden
        Mikrofon-Auswahl und SpeechMike-Hinweis kürzer, damit der Status in der Mitte Platz behält."""
        try:
            breit = (event.width if event is not None else self.winfo_width()) >= KOPF_BREIT_AB
        except Exception:
            return
        if breit == getattr(self, "_kopf_breit", None):
            return
        self._kopf_breit = breit
        try:
            self.device_dropdown.configure(width=250 if breit else 130)
        except Exception:
            pass
        if getattr(self, "_sm_beschreibung", None):
            self._speechmike_status(self._sm_beschreibung)

    def speechmike_taste(self, taste, gedrueckt, roh=""):
        """SpeechMike-Taste (aus dem Lese-Thread per after(0)). Belegung speechmike.BELEGUNG — Loslassen und unbelegte
        Tasten (Play, Spulen, INSTR, F3, F4, Command) stehen nur im Protokoll ([SPEECHMIKE]-Zeile mit Rohdaten)."""
        ereignis = _sm.BELEGUNG.get(taste) if gedrueckt else None
        if ereignis is None:
            return
        {"record": self.sm_record, "stop": self.sm_stop, "ins": self.sm_ins, "eol": self.befund_fertig,
         "reset": self.reset_dictation, "nur_text": self.nur_text_umschalten}[ereignis]()

    def sm_record(self):
        """Record = Aufnahme starten / pausieren / weiter. Ein neuer Start hängt an das Diktat-Feld an (Nachdiktat:
        INS erstellt den Befund dann aus dem Gesamtdiktat) — außer der Befund wurde schon eingefügt."""
        aktion = self._job.vorschau("record")
        if aktion is None:
            if self._job.zustand == _js.PROCESSING:
                self._kurzhinweis("Befund wird erstellt – bitte kurz warten")
            elif self._job.zustand == _js.LOCKED:
                self.refresh_key_state()
            return
        if aktion == "pause":
            self._pausieren("record")
        elif aktion == "weiter":
            self._fortsetzen()
        else:
            bisher = self.transcript_text.get("1.0", "end-1c").strip()
            self._aufnahme_umschalten("record", "start", basis="" if self._gesendet else bisher)

    def sm_stop(self):
        """Stop-Taste bzw. Schieber auf STOP = Pause (nur während der Aufnahme)."""
        if self._job.vorschau("stop") == "pause":
            self._pausieren("stop")

    def sm_ins(self):
        """INS = „ins rechte Fenster“: Aufnahme beenden bzw. aus dem Diktat-Feld → Befund (bei „Nur Text“: korrigierter
        Text) erscheint rechts zur Kontrolle, editierbar. Es wird NICHTS eingefügt. Steht der Cursor beim Start im
        Befund, wird wie bei F10 (v3.5.0) an der Cursor-Stelle eingefügt."""
        aktion = self._job.vorschau("ins")
        if aktion is None:
            if self._job.zustand == _js.PROCESSING:
                self._kurzhinweis("Befund wird schon erstellt")
            elif self._job.zustand == _js.LOCKED:
                self.refresh_key_state()
            return
        if aktion == "stop":
            self._aufnahme_umschalten("ins", "stop", kontrolle=True)
        else:
            self.befund_aus_text(kontrolle=True)

    def befund_fertig(self):
        """SpeechMike-EOL = „alles fertig“ (Peter 11.10., Nachtrag 3): den SICHTBAREN, ggf. von Hand geänderten Befund
        (bzw. Nur-Text-Inhalt) weiterschicken und danach alles leeren — bereit für den nächsten Patienten. Nur mit
        fertigem Befund und ohne laufende Aufnahme/Verarbeitung; nie etwas Ungesehenes, kein Doppeldruck.
        ZENTRALE STELLE für den nächsten Schritt: hier kommt später „Formatierung → Vidierliste“ hinein (heute: kopieren
        + Strg+V ins SpeechMagic-/RIS-Fenster, das vor RaKScribe vorne war).
        v3.10.0: Mit offenem CAS-Auftrag geht der Befund als Datei an die RaKScribe-Brücke (kein Strg+V)."""
        if getattr(self, "_cas", None) is not None:
            return self._cas_senden()
        text = self.result_text.get("1.0", "end-1c").strip()
        if self._job.vorschau("eol") is None or not _sm.sendefaehig(text):
            self._kurzhinweis("Erst INS, Befund prüfen, dann EOL")
            return
        if self._gesendet:  # F10 hat genau diesen Befund schon eingefügt → nicht doppelt
            self._job.ereignis("eol")
            self._felder_leeren()
            self._kurzhinweis("Befund war schon eingefügt – Felder geleert, bereit")
            return
        if not self.copy_formatted_report():
            self.update_status("ERROR", "busy")
            messagebox.showerror("Nicht weitergeschickt", "Der Befund wurde NICHT weitergeschickt.\n\n"
                                 + ZWISCHENABLAGE_GESPERRT)
            return
        fz = getattr(self, "_fensterziel", None)
        hwnd, titel, aktivieren = fz.ziel() if fz is not None else (None, "kein Fensterziel", False)
        log(f"[SPEECHMIKE] EOL: Befund ({len(text)} Zeichen) weiterschicken → "
            + (f"Fenster „{titel}“" if hwnd else f"nur kopiert ({titel})"))
        self._job.ereignis("eol")
        self._felder_leeren()
        if hwnd:
            self.after(150, lambda: self._eol_einfuegen(hwnd, titel, aktivieren))
        else:
            self._kurzhinweis("Befund kopiert – im RIS mit Strg+V einfügen", 8000)

    def _eol_einfuegen(self, hwnd, titel, aktivieren):
        """Strg+V nur, wenn das Zielfenster nachweislich vorne ist — sonst bleibt es beim Kopieren (+ Hinweis)."""
        fz = self._fensterziel
        if (aktivieren and not fz.aktivieren_und_pruefen(hwnd)) or not fz.ist_vorne(hwnd):
            log(f"[SPEECHMIKE] Zielfenster „{titel}“ nicht sicher vorne — nur kopiert.")
            self._kurzhinweis("Befund kopiert – im RIS mit Strg+V einfügen", 8000)
            return
        self._strg_v()
        self.update_status("COPIED", "ready")
        self._kurzhinweis(f"Befund eingefügt in „{titel[:40]}“ – bereit", 6000)

    def nur_text_umschalten(self):
        """F2 = „Nur Text“ an/aus. Ein schon erstellter Befund bleibt unverändert — der Wechsel wirkt beim nächsten INS
        (Peter 11.10., Nachtrag 4: nichts still über Änderungen hinweg neu erzeugen)."""
        v = getattr(self, "nur_text_var", None)
        if v is None:
            return
        v.set(not bool(v.get()))
        self._nur_text_umgeschaltet()
        self._kurzhinweis("Nur Text: an" if v.get() else "Nur Text: aus (strukturierter Befund)")

    def _pausieren(self, ereignis):
        """Pause: das Mikrofon nimmt nichts mehr auf, das Diktat bleibt. Das bisher Diktierte (Abschnitt seit Start/
        Weiter) wird sofort repariert — chirp_3 + Fehlhör-Liste, NUR für die Anzeige; der Endtext kommt beim Beenden wie
        bisher aus der ganzen Aufnahme (Messung 11.10., docs/benchmarks/pause_segmente_2026-10-11.txt)."""
        if self._job.ereignis(ereignis) != "pause":
            return
        gen, a = self._job.gen, self._aufnahme
        k, start, ende = a.pausieren() if a is not None else (len(self._abschnitte), 0, 0)
        while len(self._abschnitte) <= k:
            self._abschnitte.append(None)
        log(f"[SPEECHMIKE] Pause nach Abschnitt {k + 1} ({(ende - start) / self.samplerate:.1f} s).")
        self.update_status("PAUSED", "recording")
        self.level_indicator.configure(width=0)
        self._diktat_anzeigen()
        if a is not None and ende - start >= _seg.MIN_SAMPLES:
            self._repariert_anzeigen(laeuft=True)
            threading.Thread(target=self._abschnitt_reparieren, args=(gen, a, k, start, ende), daemon=True).start()

    def _abschnitt_reparieren(self, gen, a, k, start, ende):
        """Hintergrund-Thread: Abschnitt k mit chirp_3 (gleiche Engine und Phrasen wie der Endtext) + Fehlhör-Liste."""
        text = None
        try:
            pcm = a.samples()
            token = _get_stt_access_token()
            roh = _chirp3_worker(pcm[start:ende], self.samplerate, 'eu', token) if (pcm is not None and token) else None
            text = apply_misheard(roh.strip()) if roh and roh.strip() else None
        except Exception:
            log_exception("[SPEECHMIKE] Reparatur des Abschnitts fehlgeschlagen — Live-Text bleibt stehen")
        self._ui(gen, lambda: self._abschnitt_fertig(gen, k, text))

    def _abschnitt_fertig(self, gen, k, text):
        if self._job.ereignis("segment_fertig", gen) is None:
            return  # Endtext steht schon oder alter Lauf
        if text:
            self._abschnitte[k] = text
            log(f"[SPEECHMIKE] Abschnitt {k + 1} repariert ({len(text)} Zeichen).")
        self._diktat_anzeigen()
        self._repariert_anzeigen()

    def _fortsetzen(self):
        if self._job.ereignis("record") != "weiter":
            return
        if self._aufnahme is not None:
            self._aufnahme.fortsetzen()
        log("[SPEECHMIKE] Weiter diktieren (gleiche Aufnahme).")
        self.update_status("RECORDING", "recording")
        if self._einfuegen_ziel is not None:
            self.status_badge.configure(text="   ●  Diktat wird an der Cursor-Stelle eingefügt   ")
        self._repariert_anzeigen()

    def _diktat_anzeigen(self):
        text = _seg.anzeige(self._basis, self._abschnitte, self._live)
        self.transcript_text.delete("1.0", "end")
        self.transcript_text.insert("1.0", text)

    def _repariert_anzeigen(self, laeuft=False):
        lbl = getattr(self, "repariert_label", None)
        if lbl is None:
            return
        if laeuft:
            lbl.configure(text="Repariere bisheriges Diktat …", text_color=TEXT_MUTED)
        elif any(self._abschnitte) and self._job.zustand in (_js.RECORDING, _js.PAUSED):
            lbl.configure(text="✓ bis zur Pause repariert", text_color=READY_GREEN)
        else:
            lbl.configure(text="")

    def _sm_sitzung_leeren(self):
        self._basis, self._abschnitte, self._live = "", [], {}
        self._kontroll_gen, self._befund_wartet, self._gesendet = None, False, False
        self._repariert_anzeigen()

    def _felder_leeren(self):
        """Nach EOL: alles leeren — bereit für den nächsten Patienten."""
        self.final_transcript = self.stream_transcript = self.stream_interim = ""
        self._einfuegen_ziel = None
        self._sm_sitzung_leeren()
        self.transcript_text.delete("1.0", "end")
        self.result_text.delete("1.0", "end")
        self.update_status("READY", "ready")
        self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE)
        self.level_indicator.configure(width=0)

    def _kurzhinweis(self, text, ms=4000):
        """Kurzer Hinweis in der Statuszeile (SpeechMike), danach wieder der normale Status."""
        self._hinweis_nr = getattr(self, "_hinweis_nr", 0) + 1
        nr, raw = self._hinweis_nr, self._status_raw
        self._letzter_hinweis = text
        log(f"[HINWEIS] {text}")
        self.status_badge.configure(text=f"   ●  {text}   ")
        self.after(ms, lambda: self._hinweis_nr == nr and self._status_raw == raw and self.update_status(raw, "ready"))

    def _led_aktualisieren(self):
        smk = getattr(self, "_speechmike", None)
        if smk is not None:
            smk.led(_sm.led_fuer(self._job.zustand, getattr(self, "_befund_wartet", False)))

    def _fenster_merken(self):
        try:
            self._fensterziel.merken()
        except Exception:
            pass
        self.after(500, self._fenster_merken)

    def _schliessen(self):
        """Fenster schließen: SpeechMike-LED aus, Lese-Thread beenden. v3.10.0: offener CAS-Auftrag → „abgebrochen“
        (die Brücke startet dann das normale Diktatprogramm)."""
        try:
            if getattr(self, "_cas", None) is not None:
                self._cas_kanal.antworten(self._cas, "abgebrochen", grund="fenster_zu")
        except Exception:
            log_exception("[CAS] Abbruch beim Schließen nicht gemeldet")
        try:
            if getattr(self, "_speechmike", None) is not None:
                self._speechmike.beenden()
        except Exception:
            pass
        self.destroy()

    # ── v3.10.0: CAS-Auftrag der RaKScribe-Brücke (Peter 12.10.: „Digitales Diktat“ ohne SpeechMagic) ────────────────
    # Die Brücke legt cas_auftrag.json ab (cas_auftrag.py). RaKScribe nimmt ihn an, zeigt das Band und holt sich den
    # Fokus; Diktat wie gewohnt (Record/INS/EOL bzw. F10, F11/F12); EOL schreibt den sichtbaren Befund + Aufnahme als
    # Datei und meldet „fertig“. Ein Diktat für Patient A landet nie still bei Patient B (cas_auftrag.entscheidung).
    def _cas_takt(self):
        try:
            self._cas_einmal()
        except Exception:
            log_exception("[CAS] Auftragsprüfung")
        self.after(500, self._cas_takt)

    def _cas_einmal(self):
        k = getattr(self, "_cas_kanal", None)
        if k is None:
            return
        if self._cas is not None:
            grund = k.zurueckgezogen(self._cas)
            if grund:
                nr = self._cas.nr
                self._cas_beenden()
                self._kurzhinweis(f"CAS-Auftrag {nr} beendet ({grund}) – der Text bleibt stehen", 10000)
            else:
                if self._cas.leistungen is None:
                    self._cas_leistungen_holen()
                self._ibl_holen()  # v3.13.0: Bausteine kommen beim Start oder später, neue Fassungen ersetzen alte
        neu = k.abholen()
        if neu is not None:
            self._cas_neu(neu)
        bitte = _bs.nach_vorne_abholen(k.ordner)  # v3.11.0: RaKScribe wurde ein zweites Mal gestartet
        if bitte is not None:
            self._zweiter_start(bitte)

    def _cas_leistungen_holen(self):
        """v3.12.0 (Brücke 1.1.0): CAS-Leistungen kommen Sekunden nach dem Auftrag — im CAS-Takt abholen, Band ergänzen.
        Ohne Datei (ältere Brücke, Abfrage gescheitert) bleibt alles wie bisher."""
        liste = self._cas_kanal.leistungen_lesen(self._cas)
        if liste is None:
            return
        self._cas.leistungen = liste
        log(f"[CAS] Leistungen {self._cas.nr}: " + (", ".join(
            f"{l.get('kurz')}({'-' if l.get('ohne_vorlage') else (l.get('vorlage') or '?')})" for l in liste) or "keine"))
        self._cas_band_zeigen()

    def _cas_hinweis_fuer_lauf(self):
        """Vorrang-Hinweis für pipeline.befund_aus_diktat: nur mit offenem Auftrag UND Leistungen, sonst None."""
        a = getattr(self, "_cas", None)
        if a is None or not a.leistungen:
            return None
        h = _cv.CasHinweis(a.leistungen, RADIOLOGY_TEMPLATES)
        return h if h else None

    def _cas_hinweise_zeigen(self, hinweise):
        lbl = getattr(self, "cas_hinweis_label", None)
        self._cas_hinweise = list(hinweise or [])
        if lbl is not None:
            text = "⚠  " + "  ·  ".join(self._cas_hinweise) if self._cas_hinweise else ""
            lbl.configure(text=text if len(text) <= 150 else text[:149] + "…")
        if self._cas_hinweise:
            log("[CAS] Hinweis: " + " | ".join(self._cas_hinweise))

    # ── v3.13.0: IB-Lab-Vorbefund-Bausteine (Peter 13.10.: „… gleich eventuell vorhandene Bausteine von IBL holt“) ─────────
    # Die Brücke 1.2.0 legt cas_ibl_<id>.json neben den Auftrag (beim Start oder später, neue Fassung = neue Datei).
    # Band-Zeile „IB Lab: FROG rechts ✓“; beim INS setzt pipeline.ibl_anwenden die Messwerte NACH der KI wörtlich ein.
    # Kommen Werte erst nach dem Befund: Knopf „＋ IB Lab einfügen“ (nie still in einen schon geprüften Befund).
    def _ibl_an(self):
        v = getattr(self, "ibl_var", None)
        return True if v is None else bool(v.get())

    def _ibl_bausteine(self):
        a = getattr(self, "_cas", None)
        return _ibl.aus_liste(a.ibl) if (a is not None and a.ibl) else []

    def _ibl_holen(self):
        """CAS-Takt: hat die Brücke eine neue Fassung der Bausteine geschrieben? → übernehmen, Band kurz hervorheben."""
        a = getattr(self, "_cas", None)
        if a is None:
            return
        liste = self._cas_kanal.ibl_lesen(a)
        if liste is None:
            return
        alt = {b.schluessel: b.version for b in self._ibl_bausteine()}
        a.ibl = liste
        neu = self._ibl_bausteine()
        log(f"[IBL] Bausteine {a.nr}: " + (", ".join(f"{b.name} v{b.version} (Ziffer {b.ziffer})" for b in neu) or "keine"))
        self._ibl_band_zeigen(hervorheben=any(alt.get(b.schluessel) != b.version for b in neu))

    def _ibl_fuer_lauf(self):
        """Für pipeline.befund_aus_diktat: nur mit offenem Auftrag, Bausteinen mit Inhalt und Menü-Schalter an."""
        a = getattr(self, "_cas", None)
        if a is None or not a.ibl or not self._ibl_an():
            return None
        k = _ibl.IblKontext(self._ibl_bausteine(), cas_leistungen=list(a.leistungen or []))
        return k if k else None

    def _ibl_nach_lauf(self, erg):
        """UI-Thread nach jedem Befund mit offenem Auftrag: Stand der eingesetzten Werte merken (ohne Bausteine bzw.
        Übernahme aus: nichts im Befund), Hinweise zeigen (nur Anzeige), Band/Knopf nachziehen."""
        e = getattr(erg, "ibl", None)
        a = getattr(self, "_cas", None)
        self._ibl_lauf_auftrag = a.auftrag_id if a is not None else None   # dieser Befund gehört zu diesem Auftrag
        self._ibl_im_befund = dict(e.behandelt) if e is not None else {}
        self._ibl_zeilen = {k: list(v) for k, v in e.eingesetzt.items()} if e is not None else {}
        hinweise = list(e.hinweise) if e is not None else []
        if self._ibl_an():
            hinweise += _ibl.anzeige_hinweise(self._ibl_bausteine())
        self._ibl_hinweise_zeigen(hinweise)
        self._ibl_band_zeigen()
        # läuft noch im Zustand „Verarbeitung“: Knopf erst danach prüfen (Fassung, die während der KI kam)
        self.after(800, self._ibl_band_zeigen)

    def _ibl_befund_leeren(self):
        """F9, neue Aufnahme, neuer/beendeter Auftrag: der Stand im (alten) Befund und seine Hinweise gelten nicht mehr."""
        self._ibl_im_befund, self._ibl_zeilen, self._ibl_lauf_auftrag = {}, {}, None
        self._ibl_hinweise_zeigen([])

    def _ibl_offen(self):
        """Bausteine (mit Inhalt), die im sichtbaren Befund noch fehlen bzw. dort in einer älteren Fassung stehen — nur für
        einen Befund, der in DIESEM Auftrag entstanden ist (Text von vorher, z. B. nach „Abbrechen“ stehen geblieben,
        bekommt die Werte erst beim nächsten INS, nie per Knopf)."""
        a = getattr(self, "_cas", None)
        if (a is None or getattr(self, "_ibl_lauf_auftrag", None) != a.auftrag_id
                or not self.result_text.get("1.0", "end-1c").strip()
                or self._job.zustand in (_js.RECORDING, _js.PAUSED, _js.PROCESSING)):
            return []
        im = getattr(self, "_ibl_im_befund", {}) or {}
        return [b for b in self._ibl_bausteine() if (b.befundteil or b.ergebnis) and im.get(b.schluessel) != b.version]

    def _ibl_band_zeigen(self, hervorheben=False):
        zeile, lbl = getattr(self, "ibl_zeile", None), getattr(self, "ibl_label", None)
        if lbl is None:
            return
        try:
            bausteine = self._ibl_bausteine()
            an = self._ibl_an()
            offen = self._ibl_offen() if (bausteine and an) else []
            text = _ibl.band_text(bausteine, an)
            if offen:
                text += "  ·  neu, nicht im Befund"
            lbl.configure(text=text, text_color=READY_GREEN if an else TEXT_FAINT)
            knopf = getattr(self, "ibl_knopf", None)
            if knopf is not None:
                if offen and an:
                    knopf.pack(side="right", padx=6)
                else:
                    knopf.pack_forget()
            if zeile is not None:
                if bausteine:
                    zeile.pack(side="top", anchor="w")
                else:
                    zeile.pack_forget()
            band = getattr(self, "cas_band", None)
            if band is not None and hasattr(band, "configure"):
                band.configure(height=76 if bausteine else 56)
            if hervorheben and bausteine and an:
                self._ibl_hervorheben()
        except Exception:
            log_exception("[IBL] Band")

    def _ibl_hervorheben(self):
        """Kommt etwas nach: Band-Zeile 2,5 s grün hinterlegt (Peter: „kurz hervorheben“)."""
        self._ibl_hervorgehoben = getattr(self, "_ibl_hervorgehoben", 0) + 1
        nr = self._ibl_hervorgehoben
        lbl = self.ibl_label
        lbl.configure(fg_color=READY_GREEN, text_color="#08130D")
        self.after(2500, lambda: self._ibl_hervorgehoben == nr and lbl.configure(
            fg_color="transparent", text_color=READY_GREEN if self._ibl_an() else TEXT_FAINT))

    def _ibl_hinweise_zeigen(self, hinweise):
        self._ibl_hinweise = list(dict.fromkeys(hinweise or []))
        lbl = getattr(self, "ibl_hinweis_label", None)
        if lbl is not None:
            t = "⚠  " + "  ·  ".join(self._ibl_hinweise) if self._ibl_hinweise else ""
            lbl.configure(text=t if len(t) <= 140 else t[:126].rstrip() + "…  (Klick: alle)")
        if self._ibl_hinweise:  # Protokoll ohne Befundinhalt (Umbau Schritt 23): nur Zahl und Module
            module = sorted({h.split(":", 1)[0] for h in self._ibl_hinweise if ":" in h[:24]})
            log(f"[IBL] Hinweise: {len(self._ibl_hinweise)}" + (f" ({', '.join(module)})" if module else ""))

    def _ibl_umgeschaltet(self):
        einstellung_schreiben("ibl_uebernehmen", self._ibl_an())
        log(f"[IBL] IB-Lab-Bausteine übernehmen: {'an' if self._ibl_an() else 'aus'}")
        self._ibl_band_zeigen()

    def ibl_einfuegen(self):
        """Knopf „＋ IB Lab einfügen“: Werte, die nach dem Befund kamen (bzw. eine neue Fassung), in den SICHTBAREN Befund
        einsetzen — dieselben Regeln wie beim INS; eine ältere Fassung wird wörtlich ersetzt."""
        offen = self._ibl_offen()
        if not offen or not self._ibl_an():
            self._ibl_band_zeigen()
            return
        zeilen = getattr(self, "_ibl_zeilen", {}) or {}
        alte = [z for b in offen for z in zeilen.get(b.schluessel, [])]
        a = self._cas
        e = _ibl.einsetzen(self.result_text.get("1.0", "end-1c"), offen,
                           diktat=self.final_transcript or self.transcript_text.get("1.0", "end-1c"),
                           cas_leistungen=list(a.leistungen or []), templates=RADIOLOGY_TEMPLATES, entfernen=alte)
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", e.report)
        self._ibl_im_befund = {**(getattr(self, "_ibl_im_befund", {}) or {}), **e.behandelt}
        self._ibl_zeilen = {**zeilen, **e.eingesetzt}
        hinweise = list(e.hinweise)
        if e.nicht_entfernt:
            hinweise.insert(0, f"ältere IB-Lab-Werte ({len(e.nicht_entfernt)} Zeile(n)) nicht mehr wörtlich im Befund – "
                               "bitte prüfen")
        self._ibl_hinweise_zeigen(hinweise + _ibl.anzeige_hinweise(self._ibl_bausteine()))
        self._befund_wartet, self._gesendet = True, False
        log("[IBL] von Hand eingesetzt: " + ", ".join(f"{b.name} v{b.version}" for b in offen)
            + f" · {len(e.zeilen)} Zeile(n)")
        self._ibl_band_zeigen()

    def _ibl_details(self):
        """Klick auf die IB-Lab-Zeile: alle Bausteine, Werte und Hinweise (nur lesen)."""
        bausteine = self._ibl_bausteine()
        if not bausteine:
            return
        zeilen = []
        for b in bausteine:
            zeilen.append(f"{b.label} – Version {b.version}" + ("" if (getattr(self, "_ibl_im_befund", {}) or {}).get(
                b.schluessel) != b.version else " (im Befund)"))
            zeilen += [f"   {z}" for z in b.befundteil + b.ergebnis]
            zeilen += [f"   Nicht zugeordnet: {z}" for z in b.nicht_zugeordnet]
        h = getattr(self, "_ibl_hinweise", []) or []
        if h:
            zeilen += ["", "Hinweise (nicht im Befund):"] + [f" • {x}" for x in h]
        if not self._ibl_an():
            zeilen += ["", "Übernahme ist aus (Menü ☰ „IB-Lab-Bausteine übernehmen“)."]
        messagebox.showinfo("IB Lab", "\n".join(zeilen))

    def _ibl_eol_pruefen(self, text):
        """EOL: stehen die eingesetzten IB-Lab-Zeilen noch wörtlich im Befund? Nur fürs Protokoll (von Hand Geändertes
        ist die Entscheidung des Arztes)."""
        zeilen = [z for zs in (getattr(self, "_ibl_zeilen", {}) or {}).values() for z in zs]
        if zeilen:
            fehlt = _ibl.gate(text, zeilen)
            log(f"[IBL] EOL: {len(zeilen) - len(fehlt)}/{len(zeilen)} IB-Lab-Zeilen wörtlich im Befund"
                + (" (übrige von Hand geändert)" if fehlt else ""))

    def _cas_hat_inhalt(self):
        if self._job.zustand in (_js.RECORDING, _js.PAUSED, _js.PROCESSING):
            return True
        return bool(self.transcript_text.get("1.0", "end-1c").strip() or self.result_text.get("1.0", "end-1c").strip())

    def _cas_neu(self, a):
        k = self._cas_kanal
        e = _cas.entscheidung(self._cas, self._cas_hat_inhalt())
        if e == "ablehnen":
            k.antworten(a, "abgelehnt", grund="anderes CAS-Diktat offen", offen_nr=self._cas.nr)
            self._cas_nach_vorne()
            self._kurzhinweis(f"Neues CAS-Diktat {a.nr} abgelehnt – erst {self._cas.nr} mit EOL abschließen "
                              "oder im Band abbrechen", 10000)
            return
        if e == "ersetzen":
            k.antworten(self._cas, "ersetzt", grund=f"neuer Auftrag {a.nr}")
        laeuft = self._job.zustand in (_js.RECORDING, _js.PAUSED, _js.PROCESSING)
        if self._gesendet and not laeuft:
            self._felder_leeren()  # schon eingefügter Befund gehört zum vorigen Patienten → frisch beginnen
        inhalt = laeuft or self._cas_hat_inhalt()
        self._bestaetigung_weg()
        self._cas_hinweise_zeigen([])
        self._ibl_befund_leeren()
        self._cas, self._cas_test = a, False
        self._cas_aufnahmen = [self._aufnahme] if (inhalt and self._aufnahme is not None) else []
        k.antworten(a, "angenommen")
        log(f"[CAS] Auftrag {a.nr} ({a.benutzer or '-'}) angenommen" + (" – Diktat läuft bzw. Text steht schon da"
                                                                         if inhalt else ""))
        self._cas_band_zeigen()
        self._ibl_band_zeigen()
        self._cas_nach_vorne()
        if not keys_ready():  # v3.11.0: minimiert ohne Schlüssel gewartet → Sperre + Hinweis erst jetzt zeigen
            self.refresh_key_state()
            self._kurzhinweis(f"CAS-Diktat {a.nr}: erst den Praxis-Schlüssel laden, dann diktieren", 10000)

    def _cas_beenden(self):
        self._cas, self._cas_aufnahmen, self._cas_test = None, [], False
        self._cas_hinweise_zeigen([])
        self._ibl_befund_leeren()
        self._ibl_band_zeigen()
        band = getattr(self, "cas_band", None)
        if band is not None:
            try:
                band.pack_forget()
            except Exception:
                pass

    def _cas_band_zeigen(self):
        band = getattr(self, "cas_band", None)
        if band is None or self._cas is None:
            return
        try:
            text = "●  " + self._cas.band_text()
            if not self._cas.labels():   # ohne Leistungen wie bisher; mit Leistungen sagt es der EOL-Knopf
                text += "   ·   EOL schickt den Befund an CAS"
            self.cas_label.configure(text=text)
            band.pack(fill="x", before=self.main_container)
        except Exception:
            log_exception("[CAS] Band")

    def _cas_nach_vorne(self):
        """RaKScribe nach vorne holen (die Brücke hat das Recht dazu per AllowSetForegroundWindow weitergegeben)."""
        try:
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(500, lambda: self.attributes("-topmost", False))
            self.focus_force()
            import ctypes
            ctypes.windll.user32.SetForegroundWindow(ctypes.windll.user32.GetParent(self.winfo_id()))
        except Exception:
            pass

    def _cas_taste(self, was):
        """F11 = INS, F12 = EOL — nur mit offenem CAS-Auftrag (ohne Auftrag bleibt alles wie bisher)."""
        if getattr(self, "_cas", None) is None:
            return None
        (self.sm_ins if was == "ins" else self.befund_fertig)()
        return "break"

    def cas_testbefund(self):
        """Knopf „Testbefund“ im Band (Fern-Test ohne Mikrofon): fester, als TEST markierter Text rechts; EOL schickt ihn."""
        if getattr(self, "_cas", None) is None:
            return
        if self._job.zustand not in (_js.READY, _js.ERROR):
            self._kurzhinweis("Testbefund: erst Aufnahme bzw. Verarbeitung abwarten")
            return
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", _cas.TESTBEFUND)
        self._cas_test, self._cas_aufnahmen = True, []
        self._befund_wartet, self._gesendet = True, False
        self.update_status("KONTROLLE", "ready")
        log("[CAS] Testbefund eingesetzt.")

    def cas_abbrechen(self):
        """Knopf „Abbrechen“ im Band: Auftrag zurückgeben — die Brücke startet das normale Diktatprogramm."""
        if getattr(self, "_cas", None) is None:
            return
        nr = self._cas.nr
        try:
            self._cas_kanal.antworten(self._cas, "abgebrochen", grund="knopf")
        except OSError:
            log_exception("[CAS] Abbruch nicht gemeldet")
        self._cas_beenden()
        self._kurzhinweis(f"CAS-Diktat {nr} abgebrochen – CAS startet das normale Diktat", 8000)

    def _cas_pcm(self):
        teile = []
        for a in getattr(self, "_cas_aufnahmen", []) or []:
            try:
                s = a.samples()
            except Exception:
                s = None
            if s is not None and len(s):
                teile.append(s.astype("<i2").tobytes())
        return b"".join(teile) or None

    def _cas_senden(self):
        """EOL mit CAS-Auftrag: sichtbaren Befund (+ Aufnahme) als Datei an die Brücke, „fertig“ melden, alles leeren.
        Die Zwischenablage bekommt den Text zusätzlich (Sicherheitsnetz), es wird NICHT eingefügt."""
        text = self.result_text.get("1.0", "end-1c").strip()
        if self._job.vorschau("eol") is None or not _sm.sendefaehig(text):
            self._kurzhinweis("Erst INS, Befund prüfen, dann EOL")
            return
        a = self._cas
        pcm = self._cas_pcm()
        self._ibl_eol_pruefen(text)
        try:
            self._cas_kanal.ergebnis_schreiben(a, text, pcm, self.samplerate,
                                               test=self._cas_test or text == _cas.TESTBEFUND)
        except OSError as e:
            log_exception("[CAS] Ergebnis nicht geschrieben")
            kopiert = self.copy_formatted_report()
            messagebox.showerror("Nicht an CAS übergeben", f"Der Befund konnte nicht an die Brücke übergeben werden:\n{e}"
                                 "\n\n" + ("Er liegt in der Zwischenablage." if kopiert else ZWISCHENABLAGE_GESPERRT))
            return
        log(f"[CAS] EOL: Befund ({len(text)} Zeichen) an CAS-Diktat {a.nr} übergeben"
            + (f", Aufnahme {len(pcm) / 2 / self.samplerate:.1f} s" if pcm else ", ohne Aufnahme"))
        self.copy_formatted_report()
        self._job.ereignis("eol")
        self._cas_beenden()
        self._felder_leeren()
        self._kurzhinweis(f"An CAS übergeben: Diktat {a.nr} – bereit", 6000)
        titel = befund_titel(text)
        self._bestaetigung_zeigen(f"✓  An CAS übergeben: {a.nr}" + (f"  ·  {titel}" if titel else ""))
        self._nach_cas_minimieren()

    def _bestaetigung_zeigen(self, text):
        """v3.12.0 (Peter 13.10.): grünes Band nach EOL im CAS-Modus, BESTAETIGUNG_MS lang — erst danach minimieren."""
        self._bestaetigung_nr = getattr(self, "_bestaetigung_nr", 0) + 1
        nr = self._bestaetigung_nr
        self._bestaetigung_text = text
        band = getattr(self, "bestaetigung_band", None)
        if band is not None:
            try:
                self.bestaetigung_label.configure(text=text)
                band.pack(fill="x", before=self.main_container)
            except Exception:
                log_exception("[CAS] Bestätigung")
        self.after(BESTAETIGUNG_MS, lambda: self._bestaetigung_nr == nr and self._bestaetigung_weg())

    def _bestaetigung_weg(self):
        self._bestaetigung_text = ""
        band = getattr(self, "bestaetigung_band", None)
        if band is not None:
            try:
                band.pack_forget()
            except Exception:
                pass

    # ── v3.11.0: Bereitschaft (Peter 13.10.: „als Symbol in der Taskleiste warten, bis der nächste Befund diktiert
    # werden soll“). Autostart über den lokalen Starter (bereitschaft.py), Einzelinstanz in main(), nach CAS-EOL minimieren.
    def _nach_cas_minimieren(self):
        """Nach EOL im CAS-Modus wieder als Symbol in die Taskleiste (Menü „Nach CAS-Befund minimieren“, Standard an) —
        v3.12.0: erst nach dem grünen Bestätigungsband (~4,6 s) und nur, wenn bis dahin nichts Neues begonnen hat.
        Ohne CAS-Auftrag ändert sich nichts."""
        v = getattr(self, "nach_cas_minimieren_var", None)
        if v is not None and v.get():
            self.after(MINIMIEREN_NACH_EOL_MS, self._minimieren_wenn_ruhig)

    def _minimieren_wenn_ruhig(self):
        if (getattr(self, "_cas", None) is not None or self._job.zustand in (_js.RECORDING, _js.PAUSED, _js.PROCESSING)
                or self.transcript_text.get("1.0", "end-1c").strip() or self.result_text.get("1.0", "end-1c").strip()):
            return  # neuer Auftrag, Aufnahme oder Text seit dem EOL → Fenster bleibt
        log("[BEREITSCHAFT] Nach dem CAS-Befund minimiert – wartet auf das nächste Diktat.")
        self._bestaetigung_weg()
        self.iconify()

    def _zweiter_start(self, bitte):
        """RaKScribe wurde noch einmal gestartet (Doppelklick, Brücke): keine zweite Instanz — zwei würden um denselben
        CAS-Auftrag konkurrieren —, sondern dieses Fenster nach vorne. War es eine andere EXE: Hinweis zum Wechseln."""
        self._zweitstarts = getattr(self, "_zweitstarts", 0) + 1
        exe = bitte.get("exe") or ""
        log(f"[START] Zweiter Start ({exe or '?'}, v{bitte.get('version') or '?'}) – dieses Fenster nach vorne.")
        self._cas_nach_vorne()
        if exe and getattr(self, "_exe_pfad", None) and not _bs.gleicher_pfad(exe, self._exe_pfad):
            self._kurzhinweis(f"RaKScribe {app_version()} läuft schon – für die andere EXE erst dieses Fenster schließen",
                              10000)

    def _autostart_nachziehen(self):
        """Hintergrund-Thread beim Start (Autostart an): Starter auf Stand halten — prüft ggf. X:, darum nicht im UI-Thread."""
        try:
            meldung = self._autostart.nachziehen(self._exe_pfad)
            if meldung:
                log(meldung)
        except Exception:
            log_exception("[AUTOSTART] Nachziehen")

    def _autostart_umschalten(self):
        """Menü-Haken „Mit Windows starten (wartet minimiert)“: an = Verknüpfung im Benutzer-Autostart auf den lokalen
        Starter, der auf DIESE EXE wartet (X: gibt es erst nach dem CAS-Login); aus = Verknüpfung und Starter weg."""
        if self.autostart_var.get():
            self._autostart_ergebnis(*self._autostart.einrichten(self._exe_pfad))
        else:
            self._autostart_ergebnis(*self._autostart.entfernen())

    def _autostart_umstellen(self):
        """Menü „→ auf diese EXE umstellen“: der Starter wartet bisher auf eine andere Datei (z. B. eine alte Kopie)."""
        self._autostart_ergebnis(*self._autostart.einrichten(self._exe_pfad))

    def _autostart_ergebnis(self, ok, text):
        self._autostart_meldung = text
        an = self._autostart.an()
        self.autostart_var.set(an)
        einstellung_schreiben("autostart", an)
        if ok:
            self._kurzhinweis(text, 8000)
        else:
            log(f"[AUTOSTART] {text}")
            messagebox.showerror("Mit Windows starten", text)

    def speechmike_diagnose(self):
        smk = getattr(self, "_speechmike", None)
        if smk is None:
            info = ("SpeechMike-Steuerung ist im Menü ausgeschaltet." if not self.speechmike_var.get()
                    else "SpeechMike-Unterstützung ist nicht gestartet — Details in rakscribe.log.")
        else:
            zeilen = list(smk.verlauf)[-15:]
            info = (f"Gerät: {smk.verbunden or 'nicht verbunden (Anstecken genügt)'}\nLED: {smk.led_soll}\n\n"
                    "Letzte Tasten:\n" + ("\n".join(zeilen) or "(noch keine)") + "\n\n" + "\n".join(HILFE_SPEECHMIKE)
                    + f"\n\nAlle Tasten mit Rohdaten: {LOG_FILE_PATH} (Zeilen [SPEECHMIKE]).")
        messagebox.showinfo("SpeechMike-Diagnose", info)

    def register_hotkey(self):
        # Selbsttest ruft dieselben Handler (auf GitHub-Windows erreichen künstliche Tasten den Hook nicht)
        self._hotkeys = {'f10': lambda: self.after(0, self.toggle_recording),
                         'f9': lambda: self.after(0, self.reset_dictation)}
        keyboard.add_hotkey('f10', self._hotkeys['f10'], suppress=True)
        keyboard.add_hotkey('f9', self._hotkeys['f9'], suppress=True)

def init_runtime():
    """Start der EXE (Umbau Schritt 16): Log-Kopf, Google-Bibliotheken, config.ini, Schlüssel + Speech-Client,
    LLM-Client, Befund-Prompt, Fehlhör-Liste, Vorlagen — in dieser Reihenfolge wie bisher beim Import."""
    global google_speech_available, speech, CFG, LLM_PROVIDER, LLM_MODEL, API_KEY
    global INITIAL_PROMPT_CONTENT, RAG_BEISPIELE, RADIOLOGY_TEMPLATES, DISPLAY_NAMES
    log(f"--- RaKScribe26 Startup (Frozen: {getattr(sys, 'frozen', False)}) ---")
    log(f"BASE_DIR: {BASE_DIR}")
    log(f"RESOURCES_DIR: {RESOURCES_DIR}")
    # Google Cloud Imports (optional, dynamically checked)
    try:
        from google.cloud import speech as _speech
        from google.oauth2 import service_account  # noqa: F401  (Verfügbarkeit prüfen)
        speech = _speech
        google_speech_available = True
        log("[INIT] Google Cloud Speech Bibliotheken erfolgreich geladen.")
    except Exception:
        log_exception("[INIT] Fehler beim Laden der Google Cloud Speech Bibliotheken")
    # config.ini (Umbau Schritt 10: config.py — Standardwerte, nur Syntaxfehler sind fatal)
    try:
        CFG = _cfg.load_config(CONFIG_FILE_PATH)
    except _cfg.KonfigFehler as e_cfg:
        messagebox.showerror("Konfigurations-Fehler", str(e_cfg))
        sys.exit()
    if CFG.angelegt:
        print(f"[INIT] config.ini fehlte und wurde neu angelegt: {CONFIG_FILE_PATH}")
    for w in CFG.warnungen:
        print(f"[INIT] WARNUNG: {w}")
    LLM_PROVIDER, LLM_MODEL, API_KEY = CFG.llm_provider, CFG.llm_model, CFG.api_key
    print(f"[INIT] Konfiguration: LLM {LLM_PROVIDER} / {LLM_MODEL}")
    # Initialisiere die Google Cloud Speech Engine beim Start
    if not init_google_speech():
        print("[INIT] Warnung: Google STT konnte beim Start nicht initialisiert werden.")
    _init_llm()
    INITIAL_PROMPT_CONTENT = load_prompt_template()
    # v3.2: RAG-Few-Shots aus practice_reports.db — Standard AUS (A/B 05.10.). config.ini RAG_BEISPIELE = 1 schaltet ein.
    RAG_BEISPIELE = CFG.rag_beispiele
    _init_misheard()
    RADIOLOGY_TEMPLATES = load_templates()
    DISPLAY_NAMES = [v.get("display_name", "") for v in RADIOLOGY_TEMPLATES.values()]
    try:  # Umbau Schritt 20: gebündelte phrases.json früh prüfen (sonst fiele erst die Spracherkennung aus)
        print(f"[INIT] Phrasen: {len(_stt.medical_phrases())} Streaming, {len(_stt.chirp_phrases())} chirp_3")
    except Exception:
        log_exception("[INIT] phrases.json nicht ladbar")


def main():
    # v3.11.0: nur EINE RaKScribe je Windows-Sitzung (zwei würden um denselben CAS-Auftrag konkurrieren). Ein zweiter
    # Start holt die laufende nach vorne; der Autostart-Starter (--minimiert) endet dann still.
    minimiert = _bs.minimiert_gewuenscht(sys.argv[1:])
    if not _bs.einzelinstanz_sichern():
        try:
            if not minimiert:
                _bs.nach_vorne_bitten(_cas.ordner_standard(), exe=_bs.exe_pfad(), version=app_version())
            log("[START] RaKScribe läuft schon – " + ("Autostart: nichts zu tun." if minimiert
                                                       else "das laufende Fenster wird nach vorne geholt."))
        except Exception:
            log_exception("[START] Zweiter Start")
        return
    init_runtime()
    ctk.set_appearance_mode("dark")
    app = RaKScribeApp(minimiert=minimiert)
    if minimiert:
        # Nur als Symbol in die Taskleiste, ohne Fenster im Vordergrund (kein Fokus-Klau, z. B. bei der CAS-Anmeldung).
        # CTk 6.0.0 versteckt das Fenster in mainloop() (withdraw für die dunkle Titelleiste) und zeigt es nur ohne
        # vorheriges iconify() wieder: das erste iconify() verhindert das Aufblitzen, das zweite legt danach das Symbol
        # in die Taskleiste (Windows-UI-Test Fall G prüft: Fenster minimiert, nicht vorne).
        app.iconify()
        app.after(0, app.iconify)
        log("[START] --minimiert: wartet als Symbol in der Taskleiste.")
    app.mainloop()


if __name__ == "__main__":
    main()
