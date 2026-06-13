## RaKScribe 2.0 Offline - (c) 2025 Dr. Peter Kalmar - Licensed under GPLv3
# Hybrid Streaming Diktat und Structured Reporting - Vollständig Offline
# STT: Faster-Whisper large-v3-turbo (Pseudo-Streaming mit Chunks)
# LLM: MedGemma via Ollama (lokale OpenAI-kompatible API)

import keyboard
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import sounddevice as sd
import numpy as np
import threading
import os
import sys
import time
import queue
import io
import wave
import pyperclip
import markdown
import re
import win32clipboard
import json
import sqlite3
from difflib import get_close_matches
import traceback
import configparser
from faster_whisper import WhisperModel
from openai import OpenAI

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
    try:
        msg = " ".join(str(arg) for arg in args)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        try:
            sys.__stdout__.write(line + "\n")
            sys.__stdout__.flush()
        except:
            pass
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except:
        pass

def log_exception(label):
    try:
        tb = traceback.format_exc()
        log(f"EXCEPTION - {label}:\n{tb}")
    except:
        pass

# Override built-in print to automatically write to our log file
print = log

log(f"--- RaKScribe26 Startup (Frozen: {getattr(sys, 'frozen', False)}) ---")
log(f"BASE_DIR: {BASE_DIR}")
log(f"RESOURCES_DIR: {RESOURCES_DIR}")

# Google Cloud Imports (optional, dynamically checked)
google_speech_available = False
try:
    from google.cloud import speech
    from google.oauth2 import service_account
    google_speech_available = True
    log("[INIT] Google Cloud Speech Bibliotheken erfolgreich geladen.")
except Exception as e:
    log_exception("[INIT] Fehler beim Laden der Google Cloud Speech Bibliotheken")


# -------------------------------------------------------------
# --- Liste wichtiger medizinischer Fachbegriffe ---
# -------------------------------------------------------------
MEDICAL_PHRASES = [
    "Hochauflösender Nervenschall", "Thorax pa/seitlich", "MRT", "MR", "CT", "Computertomografie", "DXA", "Knochendichtemessung",
    "Humerus", "Femur", "Tibia", "Fibula", "Patella", "Karpaltunnel", "Rotatorenmanschette",
    "Achillessehne", "Kalkaneus", "Acromioclaviculargelenk", "Sacroiliacalgelenk", "Halswirbelsäule (HWS)",
    "Brustwirbelsäule (BWS)", "Lendenwirbelsäule (LWS)", "Kreuzband", "Tarsus", "Metatarsus",
    "Fraktur", "Spondylarthrose", "Spondylodese", "Spondyolyse", "Spondylosis deformans", "pontifizierend", "pontifizierende", "Arthrose", "Coxarthrose", "Gonarthrose", "Meniskus", "Hinterhorn-Läsion",
    "Korbhenkelriss", "Bandscheibenprolaps", "Spinalkanalstenose", "Osteochondrose", "Nearthrosis interspinosa",
    "Osteomyelitis", "Rheumatoide Arthritis", "Kapsel-Band-Läsion", "Osteoporose", "Bakerzyste",
    "Knochenödem", "Einklemmungssyndrom", "Arthrographie", "Szintigraphie", "Vertebroplastie",
    "Facetteninfiltration", "CT-gesteuerte Biopsie", "MR-Arthrographie", "Skelettaufnahme", "Ganzbeinaufnahme",
    "Gelenkspaltverschmälerung", "Subluxation", "Wirbelkörperkompression", "Rotatorenmanschettenruptur",
    "Labrumläsion", "Subchondrale Sklerosierung", "Nervus medianus", "Nervus radialis",
    "Liquor", "Zerebrospinalflüssigkeit", "Kortex", "Großhirnrinde", "Weiße Substanz", "Basalganglien",
    "Hypophyse", "Corpus callosum", "Sinus cavernosus", "Aorta", "Arteria carotis interna", "Arteria carotis externa",
    "Pulmonalarterie", "Vena cava superior", "Vena cava inferior", "A. vertebralis",
    "Aneurysma", "Intrakranielles Aneurysma", "Ischämie", "Ischämischer Infarkt", "Intracranielle Blutung",
    "Subarachnoidalblutung (SAB)", "Subduralhämatom (SDH)", "Epiduralhämatom (EDH)", "Multiple Sklerose (MS)",
    "Hypophysenadenom", "Hydrozephalus", "Normaldruckhydrozephalus", "Vaskulitis", "Stenose", "Carotisstenose",
    "Koronarstenose", "Dissektion", "Aortendissektion", "Thrombus", "Thrombose", "Embolie", "PAE", "Plaqubildung", "Softplaque",
    "gemischte Plaqueformation", "IMT-Komplex", "Intima-Media-Hyperplasie", "Intimahyperplasie",
    "Varizen", "T1-gewichtete Sequenz", "T2-gewichtete Sequenz", "Flair-Sequenz", "Diffusion-weighted Imaging (DWI)",
    "Time-of-Flight (TOF) Angio", "MRA", "CTA", "Kontrastmittel (KM)", "Plaque", "Atherosklerotische Plaque",
    "Angioplastie", "Sakkuläres Aneurysma", "Gefäßokklusion",
    "Lunge", "Oberlappen", "Unterlappen", "Trachea", "Bronchien", "Mediastinum", "Herz", "Ventrikel",
    "Perikard", "Leber", "Gallenblase", "Pankreas", "Niere", "Milz", "Uterus", "Adnexe", "Appendix",
    "Schilddrüse", "Infiltrat", "Pulmonales Infiltrat", "Pleuraerguss", "Pneumothorax", "Spannungspneumothorax",
    "Kardiomegalie", "Aortenklappeninsuffizienz", "Leberzirrhose", "Cholezystitis", "Pankreatitis",
    "Nierenstein", "Ureterstein", "Nephrolithiasis", "Adnexitis", "Ovarielle Zyste", "Lymphknoten",
    "Lymphadenopathie", "Appendizitis", "Struma", "Verschattung", "Milzruptur", "Hernie", "Hiatushernie",
    "Inguinalhernie", "Dilatation", "Aszites", "Zystische Läsion", "Liquidation", "Faszienverdickung",
    "Hydronephrose", "Peritonealkarzinose", "Fokale Raumforderung (FRF)", "Hyperdens", "Hypodens", "Isodens",
    "Echoarm", "Echogen",
    "Malignität", "Benignität", "Tumor", "Karzinom", "Metastase", "Läsion", "Atypisch", "unspezifisch",
    "Degenerativ", "entzündlich", "Chronisch", "akut", "Ödem", "Hämatom", "Abszess", "Kalzifizierung",
    "Sklerosierung", "Nekrose", "Atrophie", "Randscharf", "unscharf begrenzt", "Rückbildung", "Progression",
    "V. a.", "Verdacht auf", "Differenzialdiagnose (DD)", "Interventionell", "Biopsie", "Drainage",
    "Normalbefund", "kein Nachweis für", "Axial", "koronar", "sagittal", "Anamnese", "Indikation",
    "Kontraindikation", "Artefakt", "Pixel", "Voxel", "Echoarmut", "Echogenität", "Hyperintens", "Hypointens",
    "Dosis-Längen-Produkt (DLP)", "Field of View (FOV)", "Standard-Abweichung (SD)", "Flüssigkeitsspiegel",
    "Röntgen-Thorax", "Projektionsaufnahme", "Z.n.", "Zustand nach", "Adenokarzinom", "Cholangiokarzinom",
    "Fibrose", "Hämangiom", "Atelektase", "Bronchiektasen", "Emphysem", "Sarkom", "Neurofibrom", "Lipom",
    "Aortenaneurysma", "Klaustrophobie", "Sequester", "Vollbild", "Partialruptur", "Tendinose", "Impingement"
]

CONFIG_FILE_PATH = os.path.join(BASE_DIR, 'config.ini')

# =========================================================================
# === CONFIG LOADING ===
# =========================================================================
config = configparser.ConfigParser()

try:
    config.read(CONFIG_FILE_PATH)
    if not config.sections():
        raise FileNotFoundError

    OLLAMA_URL = config['SETTINGS']['OLLAMA_URL'].strip()
    LLM_PROVIDER = config['SETTINGS'].get('LLM_PROVIDER', 'ollama').strip().lower()
    LLM_MODEL = config['SETTINGS']['LLM_MODEL'].strip()
    API_KEY = config['SETTINGS'].get('API_KEY', '').strip().replace('"', '')
    WHISPER_MODEL_SIZE = config['SETTINGS']['WHISPER_MODEL'].strip()
    WHISPER_COMPUTE_TYPE = config['SETTINGS']['WHISPER_COMPUTE_TYPE'].strip()
    CHUNK_DURATION = int(config['SETTINGS']['CHUNK_DURATION'].strip())
    STT_ENGINE = config['SETTINGS'].get('STT_ENGINE', 'google').strip().lower()
    GOOGLE_JSON_FILENAME = config['SETTINGS'].get('GOOGLE_JSON_FILENAME', 'rakscribe-0ff1ffd128a1.json').strip().replace('"', '')

except (KeyError, FileNotFoundError):
    if not os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write("[SETTINGS]\n"
                    "OLLAMA_URL = http://localhost:11434\n"
                    "LLM_PROVIDER = gemini\n"
                    "LLM_MODEL = gemini-1.5-flash\n"
                    "API_KEY = \n"
                    "WHISPER_MODEL = large-v3-turbo\n"
                    "WHISPER_COMPUTE_TYPE = int8\n"
                    "CHUNK_DURATION = 7\n"
                    "STT_ENGINE = google\n"
                    "GOOGLE_JSON_FILENAME = rakscribe-0ff1ffd128a1.json\n")

    messagebox.showerror("Konfigurations-Fehler",
                         f"Datei 'config.ini' fehlt oder ist fehlerhaft.\n\nPfad: {BASE_DIR}\n\nBitte Einstellungen prüfen und neustarten.")
    sys.exit()

# --- STT Engines Initialisierungs-Logik ---
whisper_model = None
speech_client = None
GOOGLE_CONFIG = None
STREAMING_CONFIG = None

def init_whisper_model():
    global whisper_model
    if whisper_model is not None:
        return True
    MODEL_PATH = os.path.join(RESOURCES_DIR, "models", WHISPER_MODEL_SIZE)
    if not os.path.exists(MODEL_PATH):
        MODEL_PATH = WHISPER_MODEL_SIZE
    print(f"[INIT] Lade Whisper-Modell von '{MODEL_PATH}' ({WHISPER_COMPUTE_TYPE})...")
    try:
        whisper_model = WhisperModel(MODEL_PATH, device="cuda", compute_type=WHISPER_COMPUTE_TYPE)
        print("[INIT] Whisper-Modell geladen (CUDA) [OK]")
        return True
    except Exception as e:
        print(f"[INIT] CUDA nicht verfügbar oder Fehler: {e}")
        try:
            whisper_model = WhisperModel(MODEL_PATH, device="cpu", compute_type="int8")
            print("[INIT] Whisper-Modell geladen (CPU-Modus) [OK]")
            return True
        except Exception as e2:
            print(f"[INIT] Whisper-Fehler: {e2}")
            return False

def init_google_speech():
    global speech_client, GOOGLE_CONFIG, STREAMING_CONFIG
    if speech_client is not None:
        return True
    if not google_speech_available:
        print("[INIT] Google Cloud Speech Bibliotheken nicht installiert.")
        return False
    SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, GOOGLE_JSON_FILENAME)
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"[INIT] Google Credentials Datei nicht gefunden unter: {SERVICE_ACCOUNT_FILE}")
        return False
    try:
        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
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
                    phrases=MEDICAL_PHRASES,
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

# Initialisiere die aktive Engine beim Start
if STT_ENGINE == 'google':
    if not init_google_speech():
        print("[INIT] Fallback: Initialisiere Whisper, da Google STT nicht geladen werden konnte.")
        STT_ENGINE = 'whisper'
        init_whisper_model()
else:
    if not init_whisper_model():
        print("[INIT] Warnung: Whisper konnte nicht geladen werden.")

# --- LLM Client Initialisierung ---
openai_client = None
try:
    if LLM_PROVIDER == 'gemini':
        key = API_KEY if API_KEY else os.environ.get("GEMINI_API_KEY", "")
        if key:
            import google.generativeai as genai
            genai.configure(api_key=key)
            print(f"[INIT] Gemini-Client via API-Key konfiguriert (Modell: {LLM_MODEL}) [OK]")
        else:
            SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, GOOGLE_JSON_FILENAME)
            if os.path.exists(SERVICE_ACCOUNT_FILE):
                import google.generativeai as genai
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
                genai.configure(credentials=credentials)
                print(f"[INIT] Gemini-Client via Service-Account '{GOOGLE_JSON_FILENAME}' konfiguriert (Modell: {LLM_MODEL}) [OK]")
            else:
                print("[WARN] Kein Gemini API-Key oder Service-Account JSON gefunden.")
    elif LLM_PROVIDER == 'openai':
        key = API_KEY if API_KEY else os.environ.get("OPENAI_API_KEY", "")
        if not key:
            print("[WARN] Kein OpenAI API-Key gefunden in config.ini oder OPENAI_API_KEY Umgebungsvariable.")
        openai_client = OpenAI(
            api_key=key if key else "dummy_key"
        )
        print(f"[INIT] OpenAI-Client konfiguriert (Modell: {LLM_MODEL}) [OK]")
    else: # ollama
        openai_client = OpenAI(base_url=f"{OLLAMA_URL}/v1", api_key="ollama")
        print(f"[INIT] Ollama-Client konfiguriert -> {OLLAMA_URL} (Modell: {LLM_MODEL}) [OK]")
except Exception as e:
    messagebox.showerror("LLM Client Fehler", f"Fehler bei Initialisierung des LLM-Clients:\n{e}")

def load_prompt_template(filename="radiology_prompt.txt"):
    try:
        prompt_path = os.path.join(BASE_DIR, "radiology_prompt_v4.txt")
        if not os.path.exists(prompt_path):
            prompt_path = os.path.join(BASE_DIR, "radiology_prompt.txt") # Fallback
            
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
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

INITIAL_PROMPT_CONTENT = load_prompt_template()

def load_templates():
    path = os.path.join(BASE_DIR, "templates.json")
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

RADIOLOGY_TEMPLATES = load_templates()

def detect_template(text):
    """Bessere Erkennungslogik für den Untersuchungstyp."""
    text_lower = text.lower()
    
    # Priorisiertes Mapping: spezifischere Begriffe zuerst prüfen
    mappings = [
        # MRT / CT (am spezifischsten)
        ("mr_des_gehirnschädels:", ["mrt schädel", "mr schädel", "mrt kopf", "mr kopf", "mrt gehirn", "mr gehirn"]),
        ("mr_der_lendenwirbelsäule:", ["mrt lws", "mr lws"]),
        ("mr_der_halswirbelsäule:", ["mrt hws", "mr hws"]),
        ("mr_des_kniegelenkes:", ["mrt knie", "mr knie"]),
        ("mr_des_schultergelenkes:", ["mrt schulter", "mr schulter"]),
        ("mr_handgelenk:", ["mrt handgelenk", "mr handgelenk"]),
        ("mr_hüftgelenk:", ["mrt hüfte", "mr hüfte", "mrt hüftgelenk", "mr hüftgelenk"]),
        ("cct:", ["cct", "craniales ct", "ct kopf", "ct schädel", "ct gehirn"]),
        ("ct_thorax:", ["ct thorax", "ct lunge", "ct brustkorb"]),
        ("ct_abdomen:", ["ct abdomen", "ct bauch"]),
        
        # Sonografie
        ("sonografie_abdomen_komplett", ["sono abd", "sonografie abd", "ultraschall abd", "abdomen-sono", "sono abdomen", "sonografie abdomen"]),
        ("sonografie_schilddrüse", ["sono schild", "sonografie schild", "ultraschall schild", "sono hals", "sonografie hals"]),
        
        # Röntgen (Wirbelsäule)
        ("lendenwirbelsäule_in_2_ebenen", ["lws", "lumbal", "lendenwirbel"]),
        ("halswirbelsäule_in_2_ebenen", ["hws", "cervical", "halswirbel"]),
        ("brustwirbelsäule_in_2_ebenen", ["bws", "thorakal", "brustwirbel"]),
        ("thorax_in_2_ebenen", ["thorax", "lunge", "herz", "rö-th", "rö thor"]),
        
        # Obere Extremitäten Röntgen (Reihenfolge: Finger/Handgelenk vor Hand!)
        ("handgelenk_in_2_ebenen", ["handgelenk"]),
        ("finger_in_2_ebenen", ["finger", "daumen", "kleinfinger", "zeigefinger", "mittelfinger", "ringfinger"]),
        ("hand_in_2_ebenen", ["hand", "mittelhand"]),
        ("ellbogengelenk_in_2_ebenen", ["ellbogen", "ellenbogen"]),
        ("unterarm_in_2_ebenen", ["unterarm", "radius", "ulna"]),
        ("oberarm_in_2_ebenen", ["oberarm", "humerus"]),
        ("schultergelenk_in_2_ebenen", ["schulter", "omarthrose"]),
        
        # Untere Extremitäten Röntgen
        ("sprunggelenk_in_2_ebenen", ["sprunggelenk", "osg", "usg", "malleolar", "malleolus"]),
        ("fuß_in_2_ebenen", ["fuß", "fuss", "mittelfuß", "vorfuß", "rückfuß"]),
        ("zehe_in_2_ebenen", ["zehe", "großzehe"]),
        ("kniegelenk_in_2_ebenen", ["knie", "gonarthrose"]),
        ("hüftgelenk_in_2_ebenen", ["hüfte", "hft", "coxarthrose"]),
        ("beckenübersicht_stehend", ["becken", "pelvis"]),
    ]
    
    # 1. Prüfe die priorisierten Schlagwort-Mappings
    for key, keywords in mappings:
        for kw in keywords:
            if kw in text_lower:
                return key
                
    # 2. Direkte Treffer auf Keys (als Fallback)
    for key in RADIOLOGY_TEMPLATES.keys():
        search_key = key.replace('_', ' ')
        if search_key in text_lower:
            return key
            
    return "allgemein"

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

def numpy_to_wav_bytes(audio_np, samplerate=16000):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(audio_np.tobytes())
    buf.seek(0)
    return buf

# === CUSTOM COLORS (Deepc AIR Inspired) ===
BGC_MAIN = "#0B0D17"
BGC_CARD = "#16192C"
ACCENT_PURPLE = "#8C52FF"
BORDER_COLOR = "#2D314D"
READY_GREEN = "#12B76A"
RECORDING_RED = "#F04438"
TEXT_PRIMARY = "#E0E0E0"

class RaKScribeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RaKScribe26")
        self.geometry("1100x800")
        self.configure(fg_color=BGC_MAIN)

        # Audio settings
        self.samplerate = 16000
        self.is_recording = False
        self.final_transcript = ""
        self.audio_queue = queue.Queue()
        self.chunk_worker_thread = None
        self.stream = None
        self.recorded_audio_chunks = []

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
            self.default_device_name = "0: Standard Mikrofon"

        self.create_widgets()
        self.register_hotkey()

    def create_widgets(self):
        # Header Area
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(30, 10))

        title_label = ctk.CTkLabel(header, text="RaKScribe AIR", font=("Segoe UI", 28, "bold"), text_color="white")
        title_label.pack(side="left")

        self.status_badge = ctk.CTkLabel(header, text=" READY ", 
                                         font=("Segoe UI", 12, "bold"),
                                         fg_color=READY_GREEN,
                                         text_color="white",
                                         corner_radius=6)
        self.status_badge.pack(side="left", padx=20)

        # Active Engine Label
        engine_str = f"Engine: {STT_ENGINE.upper()}"
        self.engine_label = ctk.CTkLabel(header, text=engine_str, font=("Segoe UI", 12, "italic"), text_color="#A0A0A0")
        self.engine_label.pack(side="left", padx=10)

        # Eingabegerät Dropdown
        self.device_dropdown = ctk.CTkComboBox(header, values=self.device_names, command=self.on_device_changed, width=280)
        self.device_dropdown.set(self.default_device_name)
        self.device_dropdown.pack(side="right")

        # Main Paned Area (Live Transcription / Structured Report)
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=25, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # LEFT CARD: Transcription
        left_card = ctk.CTkFrame(self.main_container, fg_color=BGC_CARD, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        left_card.grid(row=0, column=0, padx=5, sticky="nsew")
        
        ctk.CTkLabel(left_card, text="LIVE TRANSSKRIPTION", font=("Segoe UI", 11, "bold"), text_color="#707070").pack(anchor="w", padx=20, pady=(15, 5))
        
        self.transcript_text = ctk.CTkTextbox(left_card, font=("Segoe UI", 14), fg_color="transparent", text_color=TEXT_PRIMARY, wrap="word")
        self.transcript_text.pack(fill="both", expand=True, padx=15, pady=10)

        # RIGHT CARD: Structured Report
        right_card = ctk.CTkFrame(self.main_container, fg_color=BGC_CARD, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        right_card.grid(row=0, column=1, padx=5, sticky="nsew")
        
        ctk.CTkLabel(right_card, text="STRUKTURIERTER BEFUND", font=("Segoe UI", 11, "bold"), text_color="#707070").pack(anchor="w", padx=20, pady=(15, 5))
        
        self.result_text = ctk.CTkTextbox(right_card, font=("Segoe UI", 14), fg_color="transparent", text_color=TEXT_PRIMARY, wrap="word")
        self.result_text.pack(fill="both", expand=True, padx=15, pady=10)

        # Footer Area: Level, Buttons
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=30, pady=30)

        # Level bar
        self.level_container = ctk.CTkFrame(footer, height=4, fg_color="#1E2235", corner_radius=2)
        self.level_container.pack(fill="x", pady=(0, 20))
        self.level_indicator = ctk.CTkFrame(self.level_container, width=0, height=4, fg_color=READY_GREEN, corner_radius=2)
        self.level_indicator.place(x=0, y=0)

        # Controls
        ctrl_frame = ctk.CTkFrame(footer, fg_color="transparent")
        ctrl_frame.pack(fill="x")

        self.record_btn = ctk.CTkButton(ctrl_frame, text=" Aufnahme Starten (F10) ", 
                                         height=50, width=220,
                                         font=("Segoe UI", 14, "bold"),
                                         fg_color=ACCENT_PURPLE,
                                         hover_color="#7A45E5",
                                         corner_radius=10,
                                         command=self.toggle_recording)
        self.record_btn.pack(side="left")

        self.reset_btn = ctk.CTkButton(ctrl_frame, text=" Zurücksetzen ",
                                        height=50,
                                        font=("Segoe UI", 14),
                                        fg_color="#2D314D",
                                        hover_color="#E74C3C",
                                        corner_radius=10,
                                        command=self.reset_dictation)
        self.reset_btn.pack(side="left", padx=10)

        self.copy_btn = ctk.CTkButton(ctrl_frame, text=" Befund kopieren ",
                                       height=50,
                                       font=("Segoe UI", 14),
                                       fg_color="#2D314D",
                                       hover_color="#3D416D",
                                       corner_radius=10,
                                       command=self.copy_formatted_report)
        self.copy_btn.pack(side="right", padx=10)

        # Prompt Editing Toggle
        self.prompt_toggle = ctk.CTkButton(ctrl_frame, text="⚙", width=50, height=50, 
                                           fg_color="transparent", border_width=1, border_color=BORDER_COLOR,
                                           command=self.toggle_prompt_view)
        self.prompt_toggle.pack(side="right")

        # Hidden Prompt View
        self.prompt_window = None

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
        if type == "ready":
            self.status_badge.configure(text=f" {text.upper()} ", fg_color=READY_GREEN)
        elif type == "busy":
            self.status_badge.configure(text=f" {text.upper()} ", fg_color="#F39C12")
        elif type == "recording":
            self.status_badge.configure(text=f" {text.upper()} ", fg_color=RECORDING_RED)

    def update_recording_timer(self):
        if self.is_recording:
            elapsed = int(time.time() - self.recording_start_time)
            self.record_btn.configure(text=f" Aufnahme Stoppen (F10) ({elapsed}s) ")
            self.after(1000, self.update_recording_timer)

    def update_processing_timer(self):
        if not self.is_recording and self.status_badge.cget("text").strip() == "PROCESSING":
            elapsed = int(time.time() - self.processing_start_time)
            remaining = max(0, self.eta_seconds - elapsed)
            if remaining > 0:
                self.record_btn.configure(text=f" Verarbeite... {elapsed}s (ca. {remaining}s verbleibend) ")
            else:
                self.record_btn.configure(text=f" Fast fertig... {elapsed}s ")
            self.after(1000, self.update_processing_timer)

    def reset_dictation(self):
        if self.is_recording:
            self.toggle_recording()
        
        log("[UI] Zurücksetzen angefordert. Lösche Transkription, Befund und Aufnahmedaten.")
        self.final_transcript = ""
        self.recorded_audio_chunks = []
        self.transcript_text.delete("1.0", "end")
        self.result_text.delete("1.0", "end")
        self.update_status("READY", "ready")
        self.level_indicator.configure(width=0)
        self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE)

    def toggle_recording(self):
        global STT_ENGINE
        if STT_ENGINE == 'google' and not speech_client:
            if not init_google_speech():
                messagebox.showerror("Fehler", "Google Cloud Speech-to-Text konnte nicht initialisiert werden. Bitte prüfen Sie Ihre Credentials (JSON-Datei) und die Internetverbindung.")
                return
        elif STT_ENGINE == 'whisper' and not whisper_model:
            if not init_whisper_model():
                messagebox.showerror("Fehler", "Whisper-Modell konnte nicht initialisiert werden.")
                return

        if not self.is_recording:
            log("[RECORD] Aufnahme wird gestartet...")
            self.final_transcript = ""
            self.recorded_audio_chunks = []
            self.transcript_text.delete("1.0", "end")
            self.result_text.delete("1.0", "end")
            self.is_recording = True
            self.first_callback_logged = False
            
            self.update_status("RECORDING", "recording")
            self.record_btn.configure(text=" Aufnahme Stoppen (F10) (0s) ", fg_color=RECORDING_RED)
            self.level_indicator.configure(fg_color=READY_GREEN, width=0)

            self.recording_start_time = time.time()
            self.update_recording_timer()

            # Store thread reference to join later
            self.record_thread = threading.Thread(target=self.record, daemon=True)
            self.record_thread.start()
            log("[RECORD] Aufnahme-Thread wurde gestartet.")
        else:
            log("[RECORD] Aufnahme wird beendet...")
            self.is_recording = False
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                    log("[RECORD] sounddevice InputStream erfolgreich gestoppt und geschlossen.")
                except Exception as stream_err:
                    log_exception("[RECORD] Fehler beim Stoppen des Streams")
                self.stream = None

            self.update_status("PROCESSING", "busy")
            
            # Schätze ETA basierend darauf, ob es ein Normalbefund ist
            def is_normal_finding(text):
                text_lower = text.lower()
                normal_keywords = ["unauffällig", "normal", "regelrecht", "ohne befund", "kein nachweis", "unauffaellig"]
                has_normal = any(kw in text_lower for kw in normal_keywords)
                is_short = len(text_lower.split()) < 12
                return has_normal and is_short

            raw_est = ""
            if STT_ENGINE == 'google':
                raw_est = self.transcript_text.get("1.0", "end-1c").strip()
                if raw_est.startswith("[..") and raw_est.endswith("..]"):
                    raw_est = raw_est[3:-3].strip()
            
            is_normal = is_normal_finding(raw_est) if raw_est else False
            if is_normal:
                self.eta_seconds = 1
            else:
                self.eta_seconds = 120 if STT_ENGINE == 'google' else 130

            self.processing_start_time = time.time()
            self.record_btn.configure(state="disabled", text=f" Verarbeite... (ca. {self.eta_seconds}s) ")
            self.update_processing_timer()
            
            # Run wait and process in background thread
            def wait_and_process():
                log("[PROCESS] Warte auf Beendigung des Aufnahme-Threads...")
                if hasattr(self, 'record_thread') and self.record_thread:
                    self.record_thread.join(timeout=6.0) # Wait for generator to finish yielding and responses to drain
                log("[PROCESS] Aufnahme-Thread beendet oder Timeout erreicht.")
                
                # Safety net: If final_transcript is empty but they saw text, salvage it
                if not self.final_transcript.strip():
                    salvaged = self.transcript_text.get("1.0", "end-1c").strip()
                    # Wenn der gesamte Text in [.. ..] eingeschlossen ist, extrahieren wir ihn
                    if salvaged.startswith("[..") and salvaged.endswith("..]"):
                        salvaged = salvaged[3:-3].strip()
                    else:
                        # Ansonsten entfernen wir verbleibende interimistische [.. ..] Blöcke
                        salvaged = re.sub(r'\[\.\..*?\.\.\]', '', salvaged).strip()
                    if salvaged:
                        self.final_transcript = salvaged
                        log(f"[GOOGLE] Text gerettet: '{salvaged}'")

                if STT_ENGINE == 'google':
                    self.process_dictation()
                else:
                    self.transcribe_and_process_dictation()

            threading.Thread(target=wait_and_process, daemon=True).start()

    def cancel_recording_due_to_error(self):
        log("[RECORD] Aufnahme aufgrund eines Fehlers abgebrochen.")
        self.is_recording = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.stream = None
        self.update_status("ERROR", "busy")
        self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE)
        self.level_indicator.configure(fg_color=READY_GREEN, width=0)

    def google_streaming_generator(self):
        log("[GOOGLE] google_streaming_generator gestartet.")
        # Keep yielding as long as we are recording OR there are remaining chunks to send
        yield_count = 0
        while self.is_recording or self.recorded_audio_chunks:
            if self.recorded_audio_chunks:
                chunks_to_send = self.recorded_audio_chunks
                self.recorded_audio_chunks = []
                if chunks_to_send:
                    chunk_bytes = np.concatenate(chunks_to_send, axis=0).tobytes()
                    yield_count += 1
                    if yield_count % 50 == 0:
                        log(f"[GOOGLE] Yielded {yield_count} request chunks to Google STT.")
                    yield speech.StreamingRecognizeRequest(audio_content=chunk_bytes)
            else:
                time.sleep(0.02)
        log(f"[GOOGLE] google_streaming_generator beendet. Insgesamt {yield_count} Chunks gesendet.")

    def update_interim_text(self, transcript, is_final):
        if not is_final:
            self.transcript_text.delete("1.0", "end")
            self.transcript_text.insert("1.0", self.final_transcript + " [.. " + transcript + " ..]")
        if is_final:
            log(f"[GOOGLE] Finaler Zwischenabschnitt erkannt: '{transcript}'")
            self.final_transcript += transcript + " "
            self.transcript_text.delete("1.0", "end")
            self.transcript_text.insert("1.0", self.final_transcript.strip())

    def record(self):
        def callback(indata, frames, time_info, status):
            if self.is_recording:
                if not getattr(self, 'first_callback_logged', False):
                    self.first_callback_logged = True
                    rms = np.sqrt(np.mean(indata.astype(np.float64)**2))
                    log(f"[AUDIO] Erster Audio-Callback empfangen. RMS-Pegel: {rms:.2f}")
                self.recorded_audio_chunks.append(indata.copy())
                rms = np.sqrt(np.mean(indata.astype(np.float64)**2))
                self.after(0, self.update_level_bar, rms)

        try:
            log(f"[RECORD] Versuche sounddevice InputStream zu öffnen. Device Index: {self.selected_device_index}")
            self.stream = sd.InputStream(device=self.selected_device_index, samplerate=self.samplerate, channels=1, dtype='int16', callback=callback)
            log("[RECORD] sounddevice InputStream erfolgreich erzeugt. Starte Stream...")
            with self.stream:
                log("[RECORD] Stream ist aktiv. STT_ENGINE ist " + STT_ENGINE)
                if STT_ENGINE == 'google':
                    requests = self.google_streaming_generator()
                    log("[GOOGLE] Rufe streaming_recognize auf...")
                    responses = speech_client.streaming_recognize(requests=requests, config=STREAMING_CONFIG)
                    log("[GOOGLE] streaming_recognize aufgerufen. Starte response-Schleife...")
                    for response in responses:
                        if not response.results:
                            continue
                        result = response.results[0]
                        if not result.alternatives:
                            continue
                        transcript = result.alternatives[0].transcript
                        self.after(0, self.update_interim_text, transcript, result.is_final)
                    log("[GOOGLE] response-Schleife regulär beendet.")
                else:
                    log("[RECORD] Whisper-Aufnahmeschleife aktiv...")
                    while self.is_recording:
                        time.sleep(0.05)
                    log("[RECORD] Whisper-Aufnahmeschleife beendet.")
            log("[RECORD] sounddevice InputStream block verlassen.")
        except Exception as e:
            log_exception("[RECORD] Fehler im record-Thread")
            if self.is_recording:
                self.after(0, lambda: messagebox.showerror("Streaming Fehler", f"Fehler bei der Google-Spracherkennung:\n{e}"))
                self.after(0, self.cancel_recording_due_to_error)

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

    def transcribe_and_process_dictation(self):
        try:
            if not self.recorded_audio_chunks:
                self.after(0, lambda: (
                    messagebox.showinfo("Info", "Keine Audio-Aufnahme vorhanden."),
                    self.update_status("READY", "ready"),
                    self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE),
                    self.level_indicator.configure(fg_color=READY_GREEN, width=0)
                ))
                return

            self.after(0, lambda: self.record_btn.configure(text=" Transkribiere... "))

            # Chunks zusammenfügen und in float32 [-1.0, 1.0] konvertieren
            audio_data = np.concatenate(self.recorded_audio_chunks, axis=0)
            audio_float32 = audio_data.flatten().astype(np.float32) / 32768.0

            # Transkribieren mit vollem Kontext und VAD-Filter
            hint = ", ".join(MEDICAL_PHRASES[:120])
            segments, _ = whisper_model.transcribe(
                audio_float32, language="de", initial_prompt=hint, 
                vad_filter=True
            )
            
            transcript = " ".join([s.text.strip() for s in segments]).strip()
            self.final_transcript = transcript

            if not transcript:
                self.after(0, lambda: (
                    messagebox.showinfo("Info", "Kein Text erkannt."),
                    self.update_status("READY", "ready"),
                    self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE),
                    self.level_indicator.configure(fg_color=READY_GREEN, width=0)
                ))
                return

            # Text in die linke Textbox einfügen
            self.after(0, lambda t=transcript: (
                self.transcript_text.delete("1.0", "end"),
                self.transcript_text.insert("1.0", t)
            ))

            # Fortfahren mit der LLM-Verarbeitung
            self.process_dictation()

        except Exception as e:
            self.after(0, lambda e=e: (
                messagebox.showerror("Transkriptions-Fehler", str(e)),
                self.update_status("ERROR", "busy"),
                self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE),
                self.level_indicator.configure(fg_color=READY_GREEN, width=0)
            ))

    def process_dictation(self):
        try:
            raw = self.final_transcript.strip()
            if not raw:
                self.after(0, lambda: (
                    messagebox.showinfo("Info", "Kein Text diktiert."),
                    self.update_status("READY", "ready"),
                    self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE),
                    self.level_indicator.configure(fg_color=READY_GREEN, width=0)
                ))
                return

            self.after(0, lambda: (
                self.result_text.delete("1.0", "end"),
                self.result_text.insert("1.0", "... Befund wird geladen ...")
            ))

            # Helferfunktion: Erkennt ob es sich um einen reinen Normalbefund handelt
            def is_normal_finding(text):
                text_lower = text.lower()
                normal_keywords = ["unauffällig", "normal", "regelrecht", "ohne befund", "kein nachweis", "unauffaellig"]
                has_normal = any(kw in text_lower for kw in normal_keywords)
                is_short = len(text_lower.split()) < 12
                return has_normal and is_short

            # Dynamische Template-Auswahl
            template_key = detect_template(raw)
            template_data = RADIOLOGY_TEMPLATES.get(template_key, {
                "display_name": "Allgemeine Untersuchung",
                "body": "Befund der untersuchten Region entsprechend dem Standardvorgehen.\nBeurteilung der radiologischen Pathologien."
            })

            # RAG-Bypass-Shortcut für reine Normalbefunde
            if is_normal_finding(raw):
                print(f"[BYPASS] Normalbefund erkannt: '{raw}'. Generiere direkt aus Template '{template_key}'.")
                formatted_raw = raw.strip()
                if formatted_raw:
                    # Ersten Buchstaben großschreiben
                    formatted_raw = formatted_raw[0].upper() + formatted_raw[1:]
                    # Punkt am Ende sicherstellen
                    if not formatted_raw.endswith('.'):
                        formatted_raw += '.'
                
                report = f"## Befund\n{template_data['body']}\n\n## Beurteilung\n{formatted_raw}"
                
                # Live in die Textbox schreiben und Status zurücksetzen
                self.after(0, lambda r=report: (
                    self.result_text.delete("1.0", "end"),
                    self.result_text.insert("1.0", r),
                    self.update_status("READY", "ready"),
                    self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE),
                    self.level_indicator.configure(fg_color=READY_GREEN, width=0),
                    self.copy_formatted_report(),
                    self.after(500, lambda: keyboard.press_and_release('ctrl+v'))
                ))
                return
            
            p_base = INITIAL_PROMPT_CONTENT
            p_full = p_base.replace('{roh_text}', raw)
            p_full = p_full.replace('{template_body}', template_data['body'])
            p_full = p_full.replace('{region_name}', template_data['display_name'])
            
            # RAG Few-Shot Beispiele laden (limit=0 für Normalbefunde, limit=1 für pathologische Befunde)
            limit_examples = 0 if is_normal_finding(raw) else 1
            db_path = os.path.join(BASE_DIR, "practice_reports.db")
            cat = classify_report(raw)
            examples_str = get_few_shot_examples(raw, cat, db_path, limit=limit_examples)
            
            if "{examples}" in p_full:
                p_full = p_full.replace("{examples}", examples_str)
            else:
                p_full = p_full + "\n\n" + examples_str
            
            sys_msg = (
                "Du bist ein präziser Radiologie-Assistent. Strukturiere das Diktat unter "
                "Verwendung des bereitgestellten Normalbefund-Templates. "
                "Nutze ## Befund und ## Beurteilung als Haupttitel."
            )

            report = ""
            if LLM_PROVIDER == 'gemini':
                import google.generativeai as genai
                model_id = LLM_MODEL
                if model_id == "gemini-1.5-flash":
                    model_id = "gemini-flash-latest"
                elif model_id == "gemini-1.5-pro":
                    model_id = "gemini-pro-latest"
                
                model = genai.GenerativeModel(
                    model_name=model_id,
                    system_instruction=sys_msg
                )
                resp = model.generate_content(
                    p_full,
                    generation_config={"temperature": 0.0},
                    stream=True
                )
                for chunk in resp:
                    try:
                        delta = chunk.text
                        if delta:
                            report += delta
                            self.after(0, lambda r=report: (
                                self.result_text.delete("1.0", "end"),
                                self.result_text.insert("1.0", r)
                            ))
                    except (AttributeError, ValueError, KeyError):
                        pass
            else:
                kwargs = {
                    "model": LLM_MODEL,
                    "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": p_full}],
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
                        self.after(0, lambda r=report: (
                            self.result_text.delete("1.0", "end"),
                            self.result_text.insert("1.0", r)
                        ))

            # Nach erfolgreichem Streaming
            self.after(0, lambda: (
                self.update_status("READY", "ready"),
                self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE),
                self.level_indicator.configure(fg_color=READY_GREEN, width=0),
                self.copy_formatted_report(),
                self.after(500, lambda: keyboard.press_and_release('ctrl+v'))
            ))
        except Exception as e:
            self.after(0, lambda e=e: (
                messagebox.showerror("LLM Error", str(e)),
                self.update_status("ERROR", "busy"),
                self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE),
                self.level_indicator.configure(fg_color=READY_GREEN, width=0)
            ))

    def copy_formatted_report(self):
        try:
            md_text = self.result_text.get("1.0", "end-1c").strip()
            if not md_text: return
            html = markdown.markdown(md_text)
            frag = f"<html><head><meta charset='utf-8'></head><body>{html}</body></html>"
            header = "Version:1.0\r\nStartHTML:{0:08d}\r\nEndHTML:{1:08d}\r\nStartFragment:{2:08d}\r\nEndFragment:{3:08d}\r\nSourceURL:none\r\n"
            s_html = len(header.format(0, 0, 0, 0))
            s_frag = s_html + frag.find("<body>") + 6
            e_frag = s_html + frag.find("</body>")
            e_html = s_html + len(frag)
            final = header.format(s_html, e_html, s_frag, e_frag) + frag
            
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.RegisterClipboardFormat("HTML Format"), final.encode('utf-8'))
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, md_text)
            win32clipboard.CloseClipboard()
            self.update_status("COPIED", "ready")
        except: pass

    def register_hotkey(self):
        keyboard.add_hotkey('f10', lambda: self.after(0, self.toggle_recording), suppress=True)

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = RaKScribeApp()
    app.mainloop()
