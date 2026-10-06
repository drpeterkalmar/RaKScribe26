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
import pipeline as _pl  # Umbau Schritt 5: Mehr-Regionen-Befund zusammensetzen (Gutachten P2-6)
import protokoll as _prot  # Umbau Schritt 23: begrenztes Log, Diktatinhalt nur im Debug-Modus
import clipboard_win as _cb  # v3.2.3 (Gutachten P1-1): Zwischenablage mit Wiederholung + Gegenlesen

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


def _init_misheard():
    global _misheard, MISHEARD_COMPILED, MISHEARD_HINTS
    try:
        import misheard as _mh
        daten = _mh.load(BASE_DIR)
        _misheard, MISHEARD_COMPILED, MISHEARD_HINTS = _mh, _mh.compile_rules(daten), _mh.prompt_block(daten)
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


def _pipeline_kontext():
    """Kontext für pipeline.befund_aus_diktat — bei jedem Lauf neu (Prompt kann im Editor geändert werden)."""
    return _pl.Kontext(templates=RADIOLOGY_TEMPLATES, display_names=DISPLAY_NAMES, prompt=INITIAL_PROMPT_CONTENT,
                       llm=lambda p: _llm_aufruf(p), misheard=apply_misheard, hinweise=MISHEARD_HINTS,
                       beispiele=_rag_beispiele, log=print, ausnahme_log=log_exception)


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
}


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


def keys_ready():
    """v3.0: App ist nur bedienbar, wenn Gemini- UND STT-Schlüssel vorhanden sind."""
    return bool(_load_vertex_key()) and (_SA_CREDENTIALS is not None or speech_client is not None)


class RaKScribeApp(ctk.CTk):
    def __init__(self):
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
        self._live_aus = False       # Live-Anzeige ausgefallen (Aufnahme läuft weiter)

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
        self.after(150, self.refresh_key_state)
        self.after(400, self._selftest_hook)
        # Umbau Schritt 24 (Gutachten P3-4): Hinweis auf die alte Prompt-Datei nur EINMAL je Datei/Version
        # (Merker in %APPDATA%\\RaKScribe), nicht bei jedem Start
        if (PROMPT_HINWEIS and not os.environ.get("RAKSCRIBE_SELFTEST")
                and _cfg.einmalig(os.path.join(USER_KEY_DIR, "gezeigte_hinweise.json"), PROMPT_HINWEIS)):
            self.after(1200, lambda: messagebox.showinfo(
                "Befund-Prompt aktualisiert",
                PROMPT_HINWEIS + "\n\nDie alte Datei wird nicht mehr verwendet und kann gelöscht werden."))

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

        self.status_badge = ctk.CTkLabel(header, text="", font=(UI_FONT, 13, "bold"), corner_radius=15,
                                         height=30, text_color=TEXT_PRIMARY)
        self.status_badge.place(relx=0.5, rely=0.5, anchor="center")

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

        # Pegel im Diktat-Kopf
        self.level_container = ctk.CTkFrame(left_head, width=200, height=6, fg_color=BGC_INPUT, corner_radius=3)
        self.level_container.pack(side="right", pady=19)
        self.level_indicator = ctk.CTkFrame(self.level_container, width=0, height=6, fg_color=READY_GREEN, corner_radius=3)
        self.level_indicator.place(x=0, y=0)

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

        # Befund-Fußzeile
        ctk.CTkLabel(right_foot, text="Wird automatisch kopiert und eingefügt", font=(UI_FONT, 11),
                     text_color=TEXT_FAINT).pack(side="left", padx=16)
        self.copy_btn = ctk.CTkButton(right_foot, text="⧉  Befund kopieren", height=40, width=170,
                                      font=(UI_FONT, 13, "bold"), fg_color=ACCENT_PURPLE, hover_color=ACCENT_HOVER,
                                      corner_radius=10, command=lambda: self.copy_formatted_report(aus_knopf=True))
        self.copy_btn.pack(side="right", padx=14)
        self.prompt_window = None
        self.update_status("READY", "ready")

    # ── v3.0: Selbsttest-Modus für den automatischen Windows-UI-Test (tests/windows/exe_ui_test.py).
    # NUR aktiv, wenn die Umgebungsvariable RAKSCRIBE_SELFTEST gesetzt ist — im Praxisbetrieb wirkungslos.
    # Schreibt den UI-Zustand als JSON (Sperre, Aufnahme-Button, Status, Schlüssel) und füllt optional Demo-Text.
    def _selftest_hook(self):
        path = os.environ.get("RAKSCRIBE_SELFTEST")
        if not path:
            return
        geo = os.environ.get("RAKSCRIBE_SELFTEST_GEOMETRY")
        if geo == "zoomed":
            self.state("zoomed")
        elif geo:
            self.geometry(geo)
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()

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
                    "report_heading_tags": len(tb.tag_ranges("md_title")) // 2 + len(tb.tag_ranges("md_head")) // 2,
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
                    else:
                        dump(phase)
                except Exception:
                    pass
            self.after(300, poll_trigger)
        self.after(1500, poll_trigger)

    # ── v3.0: Befund-Formatierung (## versteckt, Überschriften fett) — Text bleibt Markdown für Kopieren ──
    def _setup_report_formatting(self):
        tb = self.result_text._textbox
        tb.tag_configure("md_hidden", elide=True)
        tb.tag_configure("md_title", font=(UI_FONT, 17, "bold"), foreground=ACCENT_PURPLE, spacing1=2, spacing3=6)
        tb.tag_configure("md_head", font=(UI_FONT, 15, "bold"), foreground="#FFFFFF", spacing1=12, spacing3=4)
        tb.configure(spacing2=3, padx=10, pady=8)
        self.transcript_text._textbox.configure(spacing2=3, padx=10, pady=8)

        def on_modified(_evt=None):
            try:
                if not tb.edit_modified():
                    return
                for tag in ("md_hidden", "md_title", "md_head"):
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
                        tb.tag_add("md_title" if first else "md_head", f"{ln}.{pre}", f"{ln}.end")
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
        m.add_command(label="Prompt bearbeiten…", command=self.toggle_prompt_view)
        m.add_command(label="Web-App öffnen", command=lambda: __import__("webbrowser").open(
            "https://drpeterkalmar.github.io/RaKScribe26/"))
        m.add_separator()
        m.add_command(label=f"STT: Google chirp_3 · LLM: Gemini 3.5 Flash (EU)", state="disabled")
        m.add_command(label="F10 Aufnahme · F9 Neu", state="disabled")
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
        self.status_badge.configure(text_color=dot if raw in ("RECORDING", "ERROR", "PROCESSING", "LOCKED") else TEXT_PRIMARY)

    def update_recording_timer(self):
        if self.is_recording:
            elapsed = int(time.time() - self.recording_start_time)
            self.record_btn.configure(text=f" Aufnahme Stoppen (F10) ({elapsed}s) ")
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
        self.transcript_text.delete("1.0", "end")
        self.result_text.delete("1.0", "end")
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
        self._aufnahme = _af.Aufnahme(
            sd, self.samplerate, self.selected_device_index,
            streaming=lambda reqs: speech_client.streaming_recognize(requests=reqs, config=STREAMING_CONFIG),
            request_bauen=lambda b: speech.StreamingRecognizeRequest(audio_content=b),
            on_level=lambda rms: self.after(0, self.update_level_bar, rms),
            on_text=lambda text, is_final: self.after(0, self.update_interim_text, text, is_final, gen),
            on_stream_fehler=lambda e: self._live_anzeige_fehler(gen, e),
            on_capture_fehler=lambda e: self._capture_fehler(gen, e),
            log=log)
        self._aufnahme.start()

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
        if aktion == "start" and not keys_ready():
            self.refresh_key_state()
            return
        if not speech_client:
            if not init_google_speech():
                messagebox.showerror("Fehler", "Google Cloud Speech-to-Text konnte nicht initialisiert werden. Bitte prüfen Sie Ihre Credentials (JSON-Datei) und die Internetverbindung.")
                return
        self._job.ereignis("toggle")
        gen = self._job.gen

        if aktion == "start":
            log("[RECORD] Aufnahme wird gestartet...")
            self.final_transcript = ""
            self.stream_transcript = ""
            self.stream_interim = ""
            self._live_aus = False
            self.transcript_text.delete("1.0", "end")
            self.result_text.delete("1.0", "end")
            self.is_recording = True
            
            self.update_status("RECORDING", "recording")
            self.record_btn.configure(text=" Aufnahme Stoppen (F10) (0s) ", fg_color=RECORDING_RED)
            self.level_indicator.configure(fg_color=READY_GREEN, width=0)

            self.recording_start_time = time.time()
            self.update_recording_timer()

            self._aufnahme_starten(gen)
            log("[RECORD] Aufnahme- und Live-Anzeige-Thread gestartet.")
        else:
            log("[RECORD] Aufnahme wird beendet...")
            self.is_recording = False
            self._aufnahme_stoppen()

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
        if chirp_text and chirp_text.strip():
            self.final_transcript = chirp_text.strip()
            log(f"[CHIRP3] OK: {len(self.final_transcript)} Zeichen")
            text = self.final_transcript
            self._ui(gen, lambda: (
                self.transcript_text.delete("1.0", "end"),
                self.transcript_text.insert("1.0", text)
            ))
        else:
            log("[CHIRP3] Kein Ergebnis — nutze Streaming-Transkript weiter.")
            # Rettung: finale Streaming-Abschnitte, sonst der letzte Zwischenstand (wie bisher aus der Anzeige)
            salvaged = self.stream_transcript.strip() or self.stream_interim.strip()
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

    def update_interim_text(self, transcript, is_final, gen):
        # Gutachten P2-5: Streaming-Text nur für die Anzeige (stream_transcript), nie in final_transcript; nach dem
        # Endtext (chirp_3) oder aus einem alten Lauf verwirft die Zustandsmaschine verspätete Antworten.
        if self._job.ereignis("stream_final" if is_final else "stream_interim", gen) is None:
            return
        if not is_final:
            self.stream_interim = transcript
            self.transcript_text.delete("1.0", "end")
            self.transcript_text.insert("1.0", self.stream_transcript + " [.. " + transcript + " ..]")
        else:
            log(f"[GOOGLE] Finaler Zwischenabschnitt erkannt: {len(transcript)} Zeichen")
            self.stream_transcript += transcript + " "
            self.stream_interim = ""
            self.transcript_text.delete("1.0", "end")
            self.transcript_text.insert("1.0", self.stream_transcript.strip())

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

    def process_dictation(self, gen):
        try:
            # Umbau Schritt 15: die ganze Kette ohne Oberfläche in pipeline.py (dieselbe Funktion wie prod_pipeline)
            erg = _pl.befund_aus_diktat(self.final_transcript, _pipeline_kontext(), beim_start=lambda: self._ui(gen, lambda: (
                self.result_text.delete("1.0", "end"),
                self.result_text.insert("1.0", "... Befund wird geladen ...")
            )))
            if erg.leer:
                self.after(0, lambda: self._ende_kein_text(gen))
                return
            report, fehler, ausnahmen = erg.report, erg.fehler, erg.ausnahmen

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
            self.after(0, lambda: self._fertig_kopieren_einfuegen(gen))
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
        keyboard.press_and_release('ctrl+v')

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
    init_runtime()
    ctk.set_appearance_mode("dark")
    app = RaKScribeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
