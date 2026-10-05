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
import base64
import urllib.request
import urllib.error
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
import befund_regeln as br  # v3.2: Regionen-Trenner, Ergebnis-Nummerierung, Prompt-Versionswahl (Sync: befundRegeln.ts)
import normalbypass as _nb  # v3.2 (Peter 05.10.): strenger Normalbefund-Bypass (Sync: normalbypass.ts)

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
    "Fraktur", "Spondylarthrose", "Spondylarthrosen", "Spondylodese", "Spondyolyse", "Spondylosis deformans", "Spondylose", "pontifizierend", "pontifizierende", "Arthrose", "Coxarthrose", "Gonarthrose", "Meniskus", "Hinterhorn-Läsion",
    "Korbhenkelriss", "Bandscheibenprolaps", "Spinalkanalstenose", "Osteochondrose", "Osteochondrosen", "Nearthrosis interspinosa",
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
    "Degenerativ", "entzündlich", "Chronisch", "akut", "Ödem", "Hämatom", "Abszess", "Kalzifizierung", "Fibroostose", "Fibroostosen", "Thorax p.a.", "Thorax p.a./seitlich",
    "Sklerosierung", "Nekrose", "Atrophie", "Randscharf", "unscharf begrenzt", "Rückbildung", "Progression",
    "V. a.", "Verdacht auf", "Differenzialdiagnose (DD)", "Interventionell", "Biopsie", "Drainage",
    "Normalbefund", "kein Nachweis für", "Axial", "koronar", "sagittal", "Anamnese", "Indikation",
    "Kontraindikation", "Artefakt", "Pixel", "Voxel", "Echoarmut", "Echogenität", "Hyperintens", "Hypointens",
    "Dosis-Längen-Produkt (DLP)", "Field of View (FOV)", "Standard-Abweichung (SD)", "Flüssigkeitsspiegel",
    "Röntgen-Thorax", "Projektionsaufnahme", "Z.n.", "Zustand nach", "Adenokarzinom", "Cholangiokarzinom",
    "Fibrose", "Hämangiom", "Atelektase", "Bronchiektasen", "Emphysem", "Sarkom", "Neurofibrom", "Lipom",
    "Aortenaneurysma", "Klaustrophobie", "Sequester", "Vollbild", "Partialruptur", "Tendinose", "Impingement",
    "zerviko", "torako", "thoraco", "lumbal", "zervikothorakal", "zervikolumbal", "zervikotorakolumbal",
    "zervikal", "thorakal", "Skoliose", "Retrolisthese", "Retrolisthesis", "Foramenstenose", "Foramenstenosen",
    "Foraminalstenose", "Foraminalstenosen", "Ganzaufnahme", "Ganzaufnahmen", "L4 gegenüber L5", "L5/S1",
    "Flachbogig", "S-förmige", "HWS", "HWK",
    "Flachbogige Skoliose", "flachbogige Skoliose", "Kyphose", "kyphotische Fehlhaltung", "Fehlhaltung",
    "Kellgren", "Lawrence", "Kellgren & Lawrence", "Kellgren-Lawrence",
    "Discopathiezeichen", "Diskopathiezeichen",
    "Neoarthrosis interspinosa", "Neoarthrosen interspinosa", "Neoarthrose interspinosa"
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

    LLM_PROVIDER = config['SETTINGS'].get('LLM_PROVIDER', 'gemini').strip().lower()
    LLM_MODEL = config['SETTINGS']['LLM_MODEL'].strip()
    API_KEY = config['SETTINGS'].get('API_KEY', '').strip().replace('"', '')
    CHUNK_DURATION = int(config['SETTINGS'].get('CHUNK_DURATION', '7').strip())
    GOOGLE_JSON_FILENAME = config['SETTINGS'].get('GOOGLE_JSON_FILENAME', 'rakscribe-0ff1ffd128a1.json').strip().replace('"', '')
    STT_ENGINE = 'google'

except (KeyError, FileNotFoundError):
    # Fehlende/unvollständige config.ini wird automatisch neu angelegt — kein Neustart nötig.
    # (Nur wenn eine vorhanden-Datei PARSE-Fehler hat, warnen wir.)
    config_was_corrupt = os.path.exists(CONFIG_FILE_PATH)
    if not config_was_corrupt:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write("[SETTINGS]\n"
                    "LLM_PROVIDER = gemini\n"
                    "LLM_MODEL = gemini-3.5-flash\n"
                    "API_KEY = \n"
                    "CHUNK_DURATION = 7\n"
                    "GOOGLE_JSON_FILENAME = rakscribe-0ff1ffd128a1.json\n")
        print(f"[INIT] config.ini fehlte und wurde neu angelegt: {CONFIG_FILE_PATH}")

    if config_was_corrupt:
        messagebox.showerror("Konfigurations-Fehler",
                             f"Datei 'config.ini' ist fehlerhaft (ungültige Werte).\n\nPfad: {CONFIG_FILE_PATH}\n\n"
                             f"Bitte prüfen oder die Datei löschen — beim nächsten Start wird sie neu angelegt.")
        sys.exit()

    # Frisch angelegte Defaults verwenden
    LLM_PROVIDER = 'gemini'
    LLM_MODEL = 'gemini-3.5-flash'
    API_KEY = ''
    CHUNK_DURATION = 7
    GOOGLE_JSON_FILENAME = 'rakscribe-0ff1ffd128a1.json'
    STT_ENGINE = 'google'
    print("[INIT] Standard-Konfiguration aktiv (LLM: gemini-3.5-flash).")

# --- STT Engines Initialisierungs-Logik ---
# Vertex API-Key: Auto-Load aus vertex-key.b64 (Base64, liegt neben der EXE) oder
# vertex-key.txt (Klartext). Damit muss der Key NICHT in config.ini eingetragen werden.
def _read_text_robust(path):
    # Windows-Editoren speichern gern UTF-16/BOM/CRLF — alle Varianten vertragen
    with open(path, 'rb') as f:
        raw = f.read()
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        raw = raw.decode('utf-16').encode('utf-8')
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    return raw.decode('utf-8', errors='replace')

USER_KEY_DIR = os.path.join(os.environ.get('APPDATA') or os.path.expanduser('~'), 'RaKScribe')
USER_KEY_PATH = os.path.join(USER_KEY_DIR, 'rakscribe-praxis-key.json')


def _praxis_key_path():
    # v3.0: neben der EXE (wie bisher) ODER im Benutzerprofil (%APPDATA%\RaKScribe, per Menü geladen —
    # überlebt EXE-Updates, kein erneutes Kopieren nach jedem Download).
    for p in (os.path.join(BASE_DIR, 'rakscribe-praxis-key.json'), USER_KEY_PATH):
        if os.path.exists(p):
            return p
    return None


def _load_praxis_key():
    # EIN-Key-Setup (v2.9.9): rakscribe-praxis-key.json = {"vertex_api_key": "AQ...",
    # "stt": {SA-JSON}} — dieselbe Datei wie im Web (v2.9.4). EINE Datei
    # versorgt Gemini UND Speech-to-Text. Liefert (gemini_key, stt_dict).
    p = _praxis_key_path()
    try:
        if p:
            data = json.loads(_read_text_robust(p))
            gk = str(data.get('vertex_api_key') or '').strip()
            stt = data.get('stt') if isinstance(data.get('stt'), dict) else None
            if gk:
                print(f"[INIT] Gemini-Key aus rakscribe-praxis-key.json geladen ({len(gk)} Zeichen)")
            if stt:
                print("[INIT] STT-Key aus rakscribe-praxis-key.json geladen (SA-JSON)")
            return (gk, stt)
    except Exception as e:
        print(f"[INIT] rakscribe-praxis-key.json nicht verwertbar: {e}")
    return ("", None)

def _load_vertex_key():
    # PRIORITAET (Fix 03.09.26): Datei-Keys VOR config.ini — eine alte config.ini
    # mit totem API_KEY darf den frischen vertex-key.b64 nicht mehr überstimmen.
    # v2.9.9: rakscribe-praxis-key.json (EIN-Key-Setup) hat oberste Priorität.
    _praxis_gemini, _praxis_stt = _load_praxis_key()
    if _praxis_gemini:
        return _praxis_gemini
    b64_path = os.path.join(BASE_DIR, 'vertex-key.b64')
    txt_path = os.path.join(BASE_DIR, 'vertex-key.txt')
    try:
        if os.path.exists(b64_path):
            content = _read_text_robust(b64_path).strip()
            k = base64.b64decode(content).decode('utf-8').strip()
            if k:
                print(f"[INIT] Gemini-Key aus vertex-key.b64 geladen ({len(k)} Zeichen)")
                return k
            else:
                print("[INIT] vertex-key.b64 ist LEER.")
    except Exception as e:
        print(f"[INIT] Konnte vertex-key.b64 nicht lesen: {e}")
    try:
        if os.path.exists(txt_path):
            k = _read_text_robust(txt_path).strip()
            if k:
                print(f"[INIT] Gemini-Key aus vertex-key.txt geladen ({len(k)} Zeichen)")
                return k
    except Exception as e:
        print(f"[INIT] Konnte vertex-key.txt nicht lesen: {e}")
    # config.ini nur als LETZTE Rückfallebene (Legacy-Verhalten)
    k = API_KEY.strip()
    if k:
        print("[INIT] Gemini-Key aus config.ini API_KEY geladen (Legacy — bitte vertex-key.b64 nutzen)")
        return k
    print(f"[INIT] WARNUNG: Kein Gemini-Key gefunden (gesucht: {b64_path}, {txt_path}, config.ini API_KEY).")
    return ""

VERTEX_KEY_FILE = _load_vertex_key()

speech_client = None
GOOGLE_CONFIG = None
STREAMING_CONFIG = None
_SA_CREDENTIALS = None
_STT_TOKEN_CACHE = {'token': None, 'exp': 0}

def init_google_speech():
    global speech_client, GOOGLE_CONFIG, STREAMING_CONFIG
    if speech_client is not None:
        return True
    if not google_speech_available:
        print("[INIT] Google Cloud Speech Bibliotheken nicht installiert.")
        return False
    # STT-Key-Reihenfolge (v2.9.9): rakscribe-praxis-key.json (EIN-Key-Setup) >
    # rakscribe-stt-key.json (Drive) > rakscribe-stt-key.b64 (Base64-JSON) >
    # config.ini-GOOGLE_JSON_FILENAME (Legacy). Alles im EXE-Verzeichnis (BASE_DIR).
    stt_json = os.path.join(BASE_DIR, 'rakscribe-stt-key.json')
    stt_b64 = os.path.join(BASE_DIR, 'rakscribe-stt-key.b64')
    legacy_json = os.path.join(BASE_DIR, GOOGLE_JSON_FILENAME)
    SERVICE_ACCOUNT_FILE = None
    credentials = None
    global _SA_CREDENTIALS
    _gk, _pstt = _load_praxis_key()
    if _pstt:
        credentials = service_account.Credentials.from_service_account_info(_pstt)
        _SA_CREDENTIALS = credentials
        SERVICE_ACCOUNT_FILE = 'rakscribe-praxis-key.json'
    elif os.path.exists(stt_json):
        SERVICE_ACCOUNT_FILE = stt_json
        credentials = service_account.Credentials.from_service_account_file(stt_json)
    elif os.path.exists(stt_b64):
        key_data = json.loads(base64.b64decode(_read_text_robust(stt_b64).strip()).decode('utf-8'))
        credentials = service_account.Credentials.from_service_account_info(key_data)
        SERVICE_ACCOUNT_FILE = stt_b64
        print("[INIT] STT-Key aus rakscribe-stt-key.b64 geladen (Base64)")
    elif os.path.exists(legacy_json):
        SERVICE_ACCOUNT_FILE = legacy_json
        credentials = service_account.Credentials.from_service_account_file(legacy_json)
    else:
        print(f"[INIT] Keine STT-Credentials gefunden. Gesucht in {BASE_DIR}:")
        print("       - rakscribe-praxis-key.json (Drive-Ordner RaKScribe — EIN-Key-Setup)")
        print("       - rakscribe-stt-key.json (Drive-Ordner RaKScribe)")
        print("       - rakscribe-stt-key.b64 (Drive-Ordner RaKScribe)")
        print(f"       - {GOOGLE_JSON_FILENAME} (Legacy)")
        return False
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

# Initialisiere die Google Cloud Speech Engine beim Start
if not init_google_speech():
    print("[INIT] Warnung: Google STT konnte beim Start nicht initialisiert werden.")

# --- LLM Client Initialisierung ---
openai_client = None
# Vertex AI Endpoint für Gemini (REST API, Auth via x-goog-api-key Header)
VERTEX_ENDPOINT = (
    # v2.11.0: gemini-3.5-flash am EU-Multi-Region-Endpoint (EU-Datenresidenz), Web-Parität
    "https://aiplatform.eu.rep.googleapis.com/v1/projects/895690562186/"
    "locations/eu/publishers/google/models/gemini-3.5-flash:generateContent"
)
try:
    if LLM_PROVIDER == 'gemini':
        key = _load_vertex_key() or API_KEY or os.environ.get("GEMINI_API_KEY", "")
        if key:
            VERTEX_API_KEY = key
            print(f"[INIT] Gemini-Client via Vertex AI API-Key konfiguriert (Modell: {LLM_MODEL}) [OK]")
        else:
            print("[WARN] Kein Gemini/Vertex API-Key gefunden in config.ini oder GEMINI_API_KEY Umgebungsvariable.")
    elif LLM_PROVIDER == 'openai':
        key = API_KEY if API_KEY else os.environ.get("OPENAI_API_KEY", "")
        if not key:
            print("[WARN] Kein OpenAI API-Key gefunden in config.ini oder OPENAI_API_KEY Umgebungsvariable.")
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

INITIAL_PROMPT_CONTENT = load_prompt_template()

# v3.2: systemInstruction — WORTGLEICH zu SYS_MSG in web_app/src/App.tsx (befund_regeln_test.py prüft das)
SYS_MSG = (
    "Du bist ein präziser Radiologie-Assistent der Praxis 'Röntgen am Kai' – Dr. P. Kalmar / Dr. G. Riegler. "
    "Strukturiere das Diktat nach den Regeln im Prompt mit dem Normalbefund-Template als vollständigem Gerüst. "
    "Ausgabe: zuerst '## ' + kanonische Untersuchungsbezeichnung mit diktierter Seite, dann '## Befund' als Fließtext "
    "ohne Labels und '## Ergebnis' nummeriert (1. 2. 3.) mit den diktierten Begriffen 1:1 inklusive Grad und Messwerten. "
    "Gib ausschließlich den fertigen Befundtext aus – keine Kommentare, keine Einleitung."
)
# v3.2: RAG-Few-Shots aus practice_reports.db — Standard AUS (A/B 05.10.: alte Praxisbefunde ohne Nummerierung
# verschlechtern Format/Standardtext, Telegram-Referenz arbeitet ohne Beispiele). config.ini RAG_BEISPIELE = 1 schaltet ein.
try:
    RAG_BEISPIELE = int(config['SETTINGS'].get('RAG_BEISPIELE', '0').strip() or 0)
except Exception:
    RAG_BEISPIELE = 0

# v3.1: Fehlhör-Liste (misheard_words.json neben der EXE, sonst Bundle/Repo) — gleiche Datei und
# gleiche Semantik wie die Web-App (web_app/src/misheard.ts). auto-Regeln ersetzen deterministisch
# im chirp_3-Volltranskript, llm-Regeln gehen als <stt_hinweise> in den Gen-Prompt.
try:
    import misheard as _misheard
    MISHEARD = _misheard.load(BASE_DIR)
    MISHEARD_COMPILED = _misheard.compile_rules(MISHEARD)
    MISHEARD_HINTS = _misheard.prompt_block(MISHEARD)
    print(f"[INIT] Fehlhör-Liste {MISHEARD.get('version')}: {len(MISHEARD_COMPILED)} auto-Regeln aus {MISHEARD.get('_path')}")
except Exception as _e_mh:
    print(f"[INIT] Fehlhör-Liste nicht geladen: {_e_mh}")
    _misheard, MISHEARD_COMPILED, MISHEARD_HINTS = None, [], ""


def apply_misheard(text):
    """Deterministische Fehlhör-Korrektur (mode 'auto'); ohne Liste unverändert."""
    if not text or not MISHEARD_COMPILED:
        return text
    fixed = _misheard.apply(text, MISHEARD_COMPILED)
    if fixed != text:
        print(f"[MISHEARD] auto-korrigiert: {text[:120]!r} -> {fixed[:120]!r}")
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

RADIOLOGY_TEMPLATES = load_templates()
DISPLAY_NAMES = [v.get("display_name", "") for v in RADIOLOGY_TEMPLATES.values()]
# v3.2 (Peter 05.10.): Region nicht erkannt → KEIN Skelett-Standardtext (Lungenröntgen wurde sonst als Skelett befundet)
ALLGEMEIN_FALLBACK = {
    "display_name": "Allgemeine Untersuchung",
    "body": "Allgemeine Untersuchung\n\nKein Nachweis pathologischer Veränderungen.",
    "ergebnis": "Unauffälliger Befund.",
}

def derive_untersuchungs_titel(raw: str, display_name: str) -> str:
    """Befundtitel fuer Bypass & <untersuchung>-Embed (v2.10.12/13, Peter 09.09.).

    Generische Sammel-Templates (display_name mit '(Allgemein)') duerfen ihren
    internen Namen NICHT als Befundtitel ausgeben — dann wird die
    Untersuchungsbezeichnung aus dem DIKTAT gebildet: 'Unterschenkel-
    Sonographie rechts unauffaellig' → 'Unterschenkel-Sonographie rechts'.
    Konkrete Templates (HWS, Orbita, ...) behalten den kanonischen Namen.
    """
    if not re.search(r"\(allgemein\)", display_name or "", re.I):
        return display_name
    # v2.10.13 (K3-Review): Negations-Guard ("nicht unauffällig" kappselt das
    # NICHT), Loop über alle Findings statt break, ':'-Strip,
    # (Allgemein)-Leak aus dem Diktat entfernen, Newline-Falt, Cap 80.
    t = re.sub(r"\bHW\b", "HWS", (raw or "").strip())
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[.?!]\s*$", "", t).strip()
    for _ in range(3):
        stripped = False
        for f in (r"unauff(?:ae|ä)?llig", r"o\.?\s?B\.?", r"ohne pathologischen Befund",
                  r"ohne pathologischem Befund", r"kein pathologischer Befund",
                  r"regelrecht", r"normal"):
            m = re.search(r"(?:^|[\s,])" + f + r"\s*$", t, re.I)
            if m:
                pre = t[:m.start()].strip()
                if re.search(r"\bnicht\s*$", pre, re.I):
                    continue  # Negation: "nicht unauffällig" nicht kappseln
                t = pre.strip()
                stripped = True
        if not stripped:
            break
    t = re.sub(r"[.,?!:]+$", "", t).strip()
    t = re.sub(r"\(\s*allgemein\s*\)", "", t, flags=re.I).strip()
    if len(t) > 80:
        t = t[:80].strip()
    return t or re.sub(r"\s*\(Allgemein\)", "", display_name, flags=re.I).strip()


def detect_template(text):
    """Bessere Erkennungslogik für den Untersuchungstyp."""
    text_lower = text.lower()

    # v3.2.2 (Georg 05.10.): Nerven-Diktate OHNE "Sono"-Wort ("N. medianus rechts unauffällig",
    # "Nervus ulnaris links …") fielen in allgemein/Unterarm/HWS → Standardbefund fehlte. Nerven-Kontext
    # (Nervus/N./Plexus/Nervensono) + Nervenname → Nerven-Template, VOR allen Röntgen-Regeln.
    # Sync: web_app/src/App.tsx detectTemplate (gleiche Liste, gleiche Reihenfolge).
    if (re.search(r"\bnerv(?:us|i|en)?\b|\bn\.\s*[a-zäöü]|\bplexus\b|nervenson|nervenschall|nervenultraschall|tarsaltunnel", text_lower)
            and not any(x in text_lower for x in ["injektion", "infiltration"])):
        if "blockade" in text_lower:  # Skill 3ae: ultraschallgezielte Blockade hat eigenes Template
            return "ultraschall_gezielte_blockade"
        for keys, tkey in [
            (["cutaneus femoris", "femoris cutaneus", "cutaneus lateralis", "femoralis cutaneus", "meralgi"], "sonografie_nerv_femoralis_cutaneus_lateralis"),
            (["medianus", "karpaltunnelsyndrom"], "sonografie_nerv_medianus"),
            (["ulnaris", "guyon"], "sonografie_nerv_ulnaris"),
            (["radialis", "frohse", "wartenberg"], "sonografie_nerv_radialis"),
            (["plexus cervicalis"], "sonografie_plexus_cervicalis"),
            (["plexus"], "sonografie_plexus_brachialis"),
            (["ischiadicus"], "sonografie_nerv_ischiadicus"),
            (["peroneus", "fibularis"], "sonografie_nerv_peroneus"),
            (["tibialis", "tarsaltunnel"], "sonografie_nerv_tibialis"),
            (["femoralis"], "sonografie_nerv_femoralis"),
            (["pudendus"], "sonografie_nervus_pudendus"),
            (["iliohypogastricus", "ilioinguinalis"], "sonografie_nervus_iliohypogastricus_ilioinguinalis"),
        ]:
            if any(k in text_lower for k in keys):
                return tkey

    # 0.0. Kombinierte Untersuchungen vorab prüfen
    if any(x in text_lower for x in ["becken", "wecken", "pelvis"]):
        if any(x in text_lower for x in ["tep", "prothese", "endoprothese", "h-tep"]):
            if any(x in text_lower for x in ["beidseits", "bds", "beide"]):
                return "beckenübersicht_mit_beidseitiger_hüftprothese"
            else:
                return "beckenübersicht_mit_einseitiger_hüftprothese"
        elif any(x in text_lower for x in ["hüfte", "hüftgelenk", "hfte", "hft"]):
            return "beckenübersicht_und_hüfte"

    # ── Gesamtwirbelsäule / Multi-Segment Erkennung (erweiterte Keywords) ──────
    # Deckt ab: "Wirbelsäulen ganz Aufnahme", "zerviko-thorako-lumbal",
    #           "toracco lumbal Skoliose", "Ganzwirbelsäule" etc.
    has_cervical  = any(x in text_lower for x in ["hws", "hwk", "zervik", "zerviko", "cervik", "cervico", "halswirbel"]) or re.search(r'\bhw\b', text_lower)
    has_thoracic  = any(x in text_lower for x in ["bws", "thorakal", "thorako", "thoraco", "toracco", "brustwirbel"])
    has_lumbar    = any(x in text_lower for x in ["lws", "lumbal", "lendenwirbel"])
    is_full_spine = any(x in text_lower for x in ["ganzaufnahme", "gesamtwirbel", "ganzwirbel"]) or \
                   ("ganz" in text_lower and "wirbels" in text_lower) or \
                   ("gesamt" in text_lower and "wirbel" in text_lower) or \
                   ("komplett" in text_lower and "wirbel" in text_lower)

    if is_full_spine or (has_cervical and has_thoracic and has_lumbar):
        return "wirbelsäule_gesamt"
    if has_cervical and has_lumbar:
        return "hws_und_lws"
    if has_cervical and has_thoracic:
        return "wirbelsäule_gesamt"
    # ─────────────────────────────────────────────────────────────────────────
    if re.search(r'\bhw\b', text_lower):
        # STT schreibt HWS oft nur als "HW" (z.B. "HW ist unauffällig")
        return "halswirbelsäule_in_2_ebenen"

    if "hws" in text_lower and "lws" in text_lower:
        if "bws" in text_lower:
            return "wirbelsäule_gesamt"
        else:
            return "hws_und_lws"
    
    # 0. Spezialregeln für Sonographie vorab prüfen (da sehr häufig)
    if any(x in text_lower for x in ["sono", "schall", "ultraschall", "duplex"]):
        # v3.2.2: Schulter-Sonographie (Web-Parität — die EXE fiel hier bisher auf sonografie_allgemein)
        if any(x in text_lower for x in ["schulter", "supraspinatus", "infraspinatus", "bizepssehne",
                                          "rotatorenmanschette", "subacromial", "subakromial"]):
            return "sonografie_schultergelenk"
        # Bauchdecke (vor abdomen/bauch, sonst greift das Allgemein-Abdomen)
        if "bauchdeck" in text_lower or "hernie" in text_lower or "rektusdiastase" in text_lower or "rectusdiastase" in text_lower:
            return "sonografie_bauchdecke"
        # Abdomen-Sonographie
        if "abdomen" in text_lower or "bauch" in text_lower or "abd" in text_lower:
            if "weiblich" in text_lower:
                return "sonografie_abdomen_weiblich"
            else:
                return "sonografie_abdomen_maennlich"
        # Halsgefäße / Carotis
        if any(x in text_lower for x in ["carotis", "halsgef", "halsart", "extracran", "commun"]):
            return "sonografie_halsgefaesse"
        # Varizensonographie
        if any(x in text_lower for x in ["varizen", "variko", "variz"]):
            return "varizensonografie"
        # Mamma VOR dem generischen "venen"-Trigger (K3-Befund 2-Familie:
        # "Hautvenen" im Mamma-Diktat matcht "venen" → falsches Beinvenen-Template).
        # Trigger 'mamma' (nicht 'mammo'): 'Mammasonographie' enthält 'mamma',
        # aber NIE 'mammo' (m-a-m-m-a + sono)!
        if "mamma" in text_lower:
            if any(x in text_lower for x in ["sono", "schall", "ultraschall", "mammasono"]):
                return "mammasonographie_beidseits"
            return "mammographie_beidseits"
        # Beinvenen
        if any(x in text_lower for x in ["beinven", "v. femoralis", "poplitea", "fibularis", "venen"]):
            return "sonografie_beinvenen"
        # Muskel-/Weichteil-Sonographie (Pedret/BAMIC-Regionen)
        if any(x in text_lower for x in ["muskel", "muskul", "gastrocnem", "soleus", "quadriceps", "ischio", "faserriss"]):
            if "dorsal" in text_lower and "unterschenkel" in text_lower:
                return "sonografie_dorsaler_unterschenkel"
            if "gastrocnem" in text_lower:
                return "sonografie_gastrocnemius_medialis"
            if "dorsal" in text_lower and "oberschenkel" in text_lower:
                return "sonografie_dorsaler_oberschenkel"
            if "anterior" in text_lower and "oberschenkel" in text_lower:
                return "sonografie_anteriorer_oberschenkel"
            return "sonografie_weichteile"
        # Halsweichteile vs Schilddrüse
        if "halsweichteil" in text_lower or "hals-weichteil" in text_lower:
            return "sonografie_halsweichteile"
        if "schilddr" in text_lower or "sd-" in text_lower:
            return "sonografie_schilddrüse"
        # Weichteilschall allgemein
        if "weichteil" in text_lower:
            return "sonografie_weichteile"
        # Nerven
        if "medianus" in text_lower or "karpal" in text_lower or "cts" in text_lower:
            return "sonografie_nerv_medianus"
        if "ulnaris" in text_lower or "sulcus" in text_lower or "loge" in text_lower or "guyon" in text_lower:
            return "sonografie_nerv_ulnaris"
        if "radialis" in text_lower or "supinator" in text_lower or "frohse" in text_lower or "wartenberg" in text_lower:
            return "sonografie_nerv_radialis"
        if "plexus" in text_lower and "cervicalis" in text_lower:
            return "sonografie_plexus_cervicalis"
        if "plexus" in text_lower:
            return "sonografie_plexus_brachialis"
        if "ischiadicus" in text_lower:
            return "sonografie_nerv_ischiadicus"
        if "peroneus" in text_lower:
            return "sonografie_nerv_peroneus"
        if "tibialis" in text_lower:
            return "sonografie_nerv_tibialis"
        if "femoralis" in text_lower and "cutaneus" in text_lower:
            return "sonografie_nerv_femoralis_cutaneus_lateralis"
        if "femoralis" in text_lower:
            return "sonografie_nerv_femoralis"
        if "pudendus" in text_lower:
            return "sonografie_nervus_pudendus"
        if "iliohypogastricus" in text_lower or "ilioinguinalis" in text_lower:
            return "sonografie_nervus_iliohypogastricus_ilioinguinalis"
        if "blockade" in text_lower or "injektion" in text_lower:
            return "ultraschall_gezielte_blockade"
        if any(x in text_lower for x in ["nerv", "neuro", "suralis"]):
            return "sonografie_nerv_allgemein"
        # Unterschenkel-Weichteil-Sono (v2.10.13-fix2, Peter: eigenes Template)
        if "unterschenkel" in text_lower:
            return "sonografie_unterschenkel"
        # Sonographie Allgemein
        return "sonografie_allgemein"

    # 1. DVT / Digitale Volumentomographie / Zahnröntgen / OPG / Zahnstatus
    if "dvt" in text_lower or "volumentomographie" in text_lower:
        if "oberkiefer" in text_lower or "ok" in text_lower:
            return "dvt_oberkiefer"
        if "unterkiefer" in text_lower or "uk" in text_lower:
            return "dvt_unterkiefer"
        return "dvt_oberkiefer"  # Default
        
    if any(x in text_lower for x in ["opg", "zahnröntgen", "zahnstatus", "orthopantomogramm"]):
        return "orthopantomogramm_des_kiefer-_und_gesichtsschädels"
        
    # 2. DEXA / Knochendichtemessung / Osteodensitometrie
    if any(x in text_lower for x in ["dexa", "knochendichte", "densitometrie", "odm"]):
        return "knochendichtemessung_dexa"
        
    # 3. Mammographie / Fernröntgen
    if "mamma" in text_lower:
        if any(x in text_lower for x in ["sono", "schall", "ultraschall", "mammasono"]):
            return "mammasonographie_beidseits"
        return "mammographie_beidseits"
        
    if "fernröntgen" in text_lower or "fern-röntgen" in text_lower or "frs" in text_lower:
        return "schädelfernröntgen"

    # 2b. Röntgen-Regionen mit eigenen Normalbefund-Templates (v2.10.12/13)
    if "orbita" in text_lower:
        return "orbita_pa_aufnahme"
    if any(x in text_lower for x in ["calcaneus", "kalkaneus", "ferse"]):
        if "seitlich" in text_lower and "2 ebenen" not in text_lower:
            return "calcaneus_seitlich"
        return "calcaneus_in_2_ebenen"
    if "mortise" in text_lower:
        return "sprunggelenk_mortise_view"
    if "gehaltene" in text_lower:
        return "sprunggelenk_gehaltene_aufnahmen"
    if ("sprunggelenk" in text_lower or "osg" in text_lower) and ("fuß" in text_lower or "fuss" in text_lower):
        return "sprunggelenk_mit_fuss"
    if any(x in text_lower for x in ["naviculare", "skaphoid", "scaphoid", "kahnbein"]):
        return "naviculareserie"

    # Peters Diktat-Kürzel: "Visa" = Videokinematographie des Schluckaktes (Konvention 3x)
    if any(x in text_lower for x in ["visa", "wiederschluck", "videokinematographie"]):
        return "videokinematographie_schluckakt"

    # 4. Durchleuchtungen (Fluoroscopy)
    if "breischluck" in text_lower or "ösophagus" in text_lower or "schluckakt" in text_lower:
        if any(x in text_lower for x in ["videokinematographie", "video", "vis-a-vis", "wiederschluck", "visa"]):
            return "videokinematographie_schluckakt"
        if any(x in text_lower for x in ["magen", "duodenum", "magenduodenum"]):
            return "oesophagus_magenduodenum_doppelkontrast"
        return "durchleuchtung:_ösophagus-breischluck"
    if "mdp" in text_lower or "magen-darm" in text_lower or "magen" in text_lower:
        return "durchleuchtung:_magen-darm-passage_mdp"
    if "urogramm" in text_lower or "ivu" in text_lower or "ivp" in text_lower:
        return "intravenöses_urogramm"
    if "phlebographie" in text_lower or "phlebo" in text_lower:
        if any(x in text_lower for x in ["press", "aszendier", "aufsteigend"]):
            return "aszendierende_pressphlebographie"
        return "beinphlebographie"
    if "hsg" in text_lower or "hysterosalpingographie" in text_lower:
        return "hysterosalpingographie"

    # Priorisiertes Mapping: spezifischere Begriffe zuerst prüfen
    mappings = [
        ("beckenübersicht_stehend", ["becken", "wecken", "pelvis"]),
        # Prothesen / TEP / Varizen
        ("varizensonografie", ["varizen", "variko", "variz"]),
        ("schulterprothese", ["schulterprothese", "schulter-tep", "schulter tep", "schulterendoprothese"]),
        ("daumensattelprothese", ["daumensattel", "sattelprothese", "sattelgelenk"]),
        ("knieprothese", ["knieprothese", "knie-tep", "knie tep", "knieendoprothese"]),
        ("hüftprothese", ["hüftprothese", "hüft-tep", "hüft tep", "hüftendoprothese", "h-tep"]),

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
        
        # Röntgen (Wirbelsäule)
        ("lendenwirbelsäule_in_2_ebenen", ["lws", "lumbal", "lendenwirbel"]),
        ("halswirbelsäule_in_2_ebenen", ["hws", "cervical", "halswirbel"]),
        ("brustwirbelsäule_in_2_ebenen", ["bws", "thorakal", "brustwirbel"]),
        # v3.2: knöcherner Hemithorax VOR Thorax ("Hemithorax" enthält "thorax")
        ("knöcherner_hemithorax", ["hemithorax", "rippenaufnahme", "rippenserie", "rippen in 2"]),
        ("thorax_in_2_ebenen", ["thorax", "torax", "lunge", "pulmo", "brustkorb", "herz", "rö-th", "rö thor"]),
        
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

# =========================================================================
# === CHIRP 3 Volltranskription (v2.9.10, 04.09.26) ===
# WER-Test 04.09.: chirp_3 (STT v2, Location eu) = 2,4% WER (auch bei Echo/
# Daempfung), latest_long = 16,7%. Kein Phrasen-Boost moeglich, dafuer
# Dragon-Niveau. Max 60s pro Request -> Segmentierung 50s + 4s Rueckhoeren,
# Ueberlappung wird per Wortvergleich gestitched.
# =========================================================================
def transcribe_full_chirp3(pcm_int16, samplerate=16000, loc='eu'):
    try:
        token = _get_stt_access_token()
        if not token:
            return None
        import urllib.request as _ur
        total = len(pcm_int16) if False else len(pcm_int16)
        return _chirp3_worker(pcm_int16, samplerate, loc, token)
    except Exception as e:
        log_exception("[CHIRP3] Fehler in transcribe_full_chirp3")
        return None

# v2.10.15: kuratiertes chirp_3-PhraseSet (Speech Adaptation), identisch zur Web-App (CHIRP_PHRASES).
CHIRP_PHRASES = [
    "flachbogig",
    "flachbogige Skoliose",
    "rechtskonvex",
    "linkskonvex",
    "Cobb-Winkel",
    "Th1",
    "Th2",
    "Th3",
    "Th4",
    "Th5",
    "Th6",
    "Th7",
    "Th8",
    "Th9",
    "Th10",
    "Th11",
    "Th12",
    "Schmorlsche Impressionen",
    "Edgren-Vaino-Zeichen",
    "Morbus Scheuermann",
    "Osteochondrose",
    "Spondylosis deformans",
    "Spondylarthrose",
    "Unkovertebralgelenksarthrose",
    "Facettengelenksarthrose",
    "Discopathiezeichen",
    "Diskopathie",
    "Antelisthese",
    "Retrolisthese",
    "Neoarthrosis interspinosa",
    "kyphotische Fehlhaltung",
    "Streckhaltung",
    "Fibroostosen",
    "Kellgren und Lawrence",
    "Gonarthrose",
    "Coxarthrose",
    "Omarthrose",
    "Rhizarthrose",
    "Retropatellararthrose",
    "Femorotibialkompartiment",
    "Scaphoidtaille",
    "Kahnbeintaille",
    "Collum chirurgicum",
    "Radiusköpfchen",
    "Humeruskopfhochstand",
    "Garden",
    "Supraspinatussehne",
    "Infraspinatussehne",
    "Subscapularissehne",
    "lange Bizepssehne",
    "Tenosynovitis",
    "Tendinopathie",
    "Tendinosis calcarea",
    "Begleitbursitis",
    "Enthesiopathie",
    "Plantarfaszie",
    "Arthro-Broström",
    "Mammasonographie",
    "BI-RADS",
    "Morbus Mondor",
    "Sulcus nervi ulnaris",
    "Nervus ulnaris",
    "Musculus anconeus epitrochlearis",
    "Hoffmann-Tinel-Zeichen",
    "Kiloh-Nevin",
    "Hypothenarmuskulatur",
    "faszikulär",
    "Thorax p.a.",
]


def _report_complete(t):
    """v2.11.1: vollständig = '## Befund' + nicht-leeres '## Ergebnis'."""
    t = t or ""
    if "## Ergebnis" not in t or len(t.split("## Ergebnis")[1].strip()) <= 5:
        return False
    pre = t.split("## Ergebnis")[0]
    body = pre.split("## Befund")[1] if "## Befund" in pre else "\n".join(l for l in pre.splitlines() if not l.strip().startswith("#"))
    return len(body.strip()) > 20


def _chirp3_request(token, loc, wav_b64, timeout=60):
    import urllib.request as _ur
    host = 'speech' if loc == 'global' else loc + '-speech'
    url = (f"https://{host}.googleapis.com/v2/projects/rakscribe/"
           f"locations/{loc}/recognizers/_:recognize")
    cfg = {"languageCodes": ["de-DE"], "model": "chirp_3",
           "autoDecodingConfig": {},
           "features": {"enableAutomaticPunctuation": True},
           "adaptation": {"phraseSets": [{"inlinePhraseSet": {"phrases": [
               {"value": p, "boost": 10} for p in CHIRP_PHRASES]}}]}}
    body = json.dumps({"config": cfg, "content": wav_b64}).encode()
    req = _ur.Request(url, data=body, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"})
    with _ur.urlopen(req, timeout=timeout) as resp:
        j = json.loads(resp.read())
    return " ".join(res["alternatives"][0]["transcript"]
                    for res in j.get("results", []))

def _get_stt_access_token():
    try:
        if GOOGLE_CONFIG is None:
            return None
        # JWT-Flow: SA-JSON direkt aus dem geladenen Service-Account-File
        from google.oauth2 import service_account as _sa
        from google.auth.transport.requests import Request as _Req
        global _STT_TOKEN_CACHE
        now = time.time()
        if _STT_TOKEN_CACHE.get('token') and _STT_TOKEN_CACHE.get('exp', 0) > now + 120:
            return _STT_TOKEN_CACHE['token']
        creds = _SA_CREDENTIALS
        if creds is None:
            return None
        if not creds.valid:
            creds.refresh(_Req())
        _STT_TOKEN_CACHE['token'] = creds.token
        _STT_TOKEN_CACHE['exp'] = creds.expiry.timestamp() if creds.expiry else now + 3000
        return _STT_TOKEN_CACHE['token']
    except Exception as e:
        log_exception("[CHIRP3] Token-Fehler")
        return None

def _stitch_overlaps(a, b, window=14):
    aw, bw = a.split(), b.split()
    best = 0
    for L in range(min(window, len(aw), len(bw)), 0, -1):
        tail = [w.lower().strip('.,:;') for w in aw[-L:]]
        head = [w.lower().strip('.,:;') for w in bw[:L]]
        if sum(1 for x, y in zip(tail, head) if x == y) >= int(L * 0.8):
            best = L
            break
    return (a + " " + " ".join(bw[best:])) if best else (a + " " + b)

def _chirp3_worker(pcm_int16, samplerate, loc, token):
    import urllib.request as _ur
    raw = pcm_int16.tobytes()
    total = len(raw) // 2
    SEG = 50 * samplerate      # 50s Segmente
    OV = 4 * samplerate        # 4s Rueckhoeren
    texts = []
    start = 0
    while start < len(pcm_int16):
        end = min(start + SEG, len(pcm_int16))
        seg = pcm_int16[start:end]
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(samplerate)
            wf.writeframes(seg.tobytes())
        import base64 as _b64
        b64 = _b64.b64encode(buf.getvalue()).decode()
        txt = _chirp3_request(token, loc, b64)
        if txt is None:
            return None
        texts.append(txt)
        if end >= len(pcm_int16):
            break
        start = end - OV
    full = texts[0]
    for nxt in texts[1:]:
        full = _stitch_overlaps(full, nxt)
    return full

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


def keys_ready():
    """v3.0: App ist nur bedienbar, wenn Gemini- UND STT-Schlüssel vorhanden sind."""
    return bool(_load_vertex_key()) and (_SA_CREDENTIALS is not None or speech_client is not None)


class RaKScribeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RaKScribe 3.2.2 – Röntgen am Kai")
        self.geometry("1240x820")
        self.minsize(900, 600)
        self.configure(fg_color=BGC_MAIN)
        self._status_raw = "READY"
        self.gate = None

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
        if PROMPT_HINWEIS and not os.environ.get("RAKSCRIBE_SELFTEST"):
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
        ctk.CTkLabel(brand, text=" v3.0 ", font=(UI_FONT, 11, "bold"), text_color=ACCENT_PURPLE,
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
        # Engine-Info (historischer Name, liegt jetzt im Menü/Tooltip-Text)
        self.engine_label = ctk.CTkLabel(right, text="", width=0)

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
                                      corner_radius=10, command=self.copy_formatted_report)
        self.copy_btn.pack(side="right", padx=14)
        # historischer Name: Prompt-Editor liegt jetzt im Menü
        self.prompt_toggle = self.menu_btn
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
            if not (str(data.get("vertex_api_key", "")).strip() and isinstance(data.get("stt"), dict)
                    and data["stt"].get("private_key")):
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
            self.key_chip.configure(text="  ✓ Schlüssel aktiv  ", fg_color="#15261F", text_color=READY_GREEN)
            if self.gate is not None:
                self.gate.destroy()
                self.gate = None
            if not self.is_recording and self._status_raw in ("LOCKED", "READY"):
                self.update_status("READY", "ready")
            self.record_btn.configure(state="normal")
        else:
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
        self._toggle_calls = getattr(self, "_toggle_calls", 0) + 1
        if not self.is_recording and not keys_ready():
            self.refresh_key_state()
            return
        if not speech_client:
            if not init_google_speech():
                messagebox.showerror("Fehler", "Google Cloud Speech-to-Text konnte nicht initialisiert werden. Bitte prüfen Sie Ihre Credentials (JSON-Datei) und die Internetverbindung.")
                return

        if not self.is_recording:
            log("[RECORD] Aufnahme wird gestartet...")
            self.final_transcript = ""
            self.recorded_audio_chunks = []
            self.recorded_audio_chunks_all = []
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
            
            # Run wait and process in background thread
            def wait_and_process():
                log("[PROCESS] Warte auf Beendigung des Aufnahme-Threads...")
                if hasattr(self, 'record_thread') and self.record_thread:
                    self.record_thread.join(timeout=6.0) # Wait for generator to finish yielding and responses to drain
                log("[PROCESS] Aufnahme-Thread beendet oder Timeout erreicht.")
                
                # ═══ CHIRP 3 Volltranskription (v2.9.10) ═══
                # Das Streaming (7s-Chunks) dient nur der Live-Anzeige. Für die
                # finale Transkription wird die KOMPLETTE Aufnahme noch einmal
                # an chirp_3 (STT v2, WER 2,4% vs 16,7%) geschickt.
                try:
                    all_pcm = np.concatenate(self.recorded_audio_chunks_all, axis=0) \
                        if getattr(self, 'recorded_audio_chunks_all', None) else None
                    if all_pcm is not None and len(all_pcm) > 16000:
                        log(f"[CHIRP3] Volltranskription: {len(all_pcm)/16000:.0f}s Audio")
                        self.after(0, lambda: self.update_status("PROCESSING", "busy"))
                        token = _get_stt_access_token()
                        chirp_text = _chirp3_worker(all_pcm, 16000, 'eu', token) if token else None
                        if chirp_text and chirp_text.strip():
                            self.final_transcript = chirp_text.strip()
                            log(f"[CHIRP3] OK: {len(self.final_transcript)} Zeichen")
                            self.after(0, lambda: (
                                self.transcript_text.delete("1.0", "end"),
                                self.transcript_text.insert("1.0", self.final_transcript.strip())
                            ))
                        else:
                            log("[CHIRP3] Kein Ergebnis — nutze Streaming-Transkript weiter.")
                except Exception as e_chirp:
                    log_exception("[CHIRP3] Volltranskription fehlgeschlagen — Streaming-Transkript bleibt.")

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

                self.process_dictation()

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
                if not hasattr(self, 'recorded_audio_chunks_all'):
                    self.recorded_audio_chunks_all = []
                self.recorded_audio_chunks_all.append(indata.copy())
                rms = np.sqrt(np.mean(indata.astype(np.float64)**2))
                self.after(0, self.update_level_bar, rms)

        try:
            log(f"[RECORD] Versuche sounddevice InputStream zu öffnen. Device Index: {self.selected_device_index}")
            self.stream = sd.InputStream(device=self.selected_device_index, samplerate=self.samplerate, channels=1, dtype='int16', callback=callback)
            log("[RECORD] sounddevice InputStream erfolgreich erzeugt. Starte Stream...")
            with self.stream:
                log("[RECORD] Stream ist aktiv. Google STT wird ausgeführt.")
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

    def process_dictation(self):
        try:
            raw = apply_misheard(self.final_transcript.strip())  # v3.1: Fehlhör-Liste vor Bypass/LLM
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

            # v3.2: Diktat mit mehreren Regionen ("Schulter rechts … Ellbogen rechts …") → je Region ein eigener
            # Befund (eigenes Template, eigenes Ergebnis), parallel erzeugt und untereinander ausgegeben.
            segmente = br.split_regionen(raw)
            if len(segmente) > 1:
                print(f"[MULTI] {len(segmente)} Regionen: " + " | ".join(x[:40] for x in segmente))
                with ThreadPoolExecutor(max_workers=len(segmente)) as ex:
                    teile = list(ex.map(self._befund_fuer_segment, segmente))
                report = br.befunde_zusammenfuegen(teile) if all(_report_complete(t) for t in teile) else ""
            else:
                report = self._befund_fuer_segment(raw)

            if report:
                self.after(0, lambda r=report: (
                    self.result_text.delete("1.0", "end"),
                    self.result_text.insert("1.0", r)
                ))
            # v2.11.1 (Prüfbericht W4): leeren/unvollständigen Befund NIE ins Zielprogramm einfügen
            if not _report_complete(report):
                self.after(0, lambda: (
                    self.update_status("ERROR", "busy"),
                    self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE),
                    self.level_indicator.configure(fg_color=READY_GREEN, width=0)
                ))
                return
            self.after(0, lambda: (
                self.update_status("READY", "ready"),
                self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE),
                self.level_indicator.configure(fg_color=READY_GREEN, width=0),
                self.copy_formatted_report(),
                self.after(500, lambda: keyboard.press_and_release('ctrl+v'))
            ))
        except Exception as e:
            log_exception("Befund-Generierung")
            if "401" in str(e) or "Unauthorized" in str(e):
                msg = ("Gemini: HTTP 401 — der API-Key fehlt oder ist ungültig.\n\n"
                       f"Gesucht in: {BASE_DIR}\n"
                       "  - rakscribe-praxis-key.json (Drive-Ordner RaKScribe — EIN-Key-Setup)\n"
                       "  - vertex-key.b64 (Drive-Ordner RaKScribe)\n"
                       "  - vertex-key.txt\n"
                       "  - config.ini [API_KEY]\n\n"
                       "Bitte die Key-Dateien aus dem Drive-Ordner RaKScribe in diesen Ordner legen.")
            else:
                msg = f"Fehler bei der Befund-Generierung:\n{e}"
            self.after(0, lambda m=msg: (
                messagebox.showerror("Generierungs-Fehler", m),
                self.update_status("ERROR", "busy"),
                self.record_btn.configure(state="normal", text=" Aufnahme Starten (F10) ", fg_color=ACCENT_PURPLE),
                self.level_indicator.configure(fg_color=READY_GREEN, width=0)
            ))

    def _ist_normalbefund(self, raw, template_key):
        """Bypass ohne LLM nur bei REINEM Normalbefund (nur Untersuchung + Normal-Worte, v3.2 Peter 05.10.)
        UND erkannter Region — jedes weitere Wort ("sonst", Pathologie, Beschreibung) → LLM."""
        return _nb.is_pure_normal_finding(raw, DISPLAY_NAMES) and template_key != "allgemein"

    def _befund_fuer_segment(self, raw):
        """Ein Befund (## Titel / ## Befund / ## Ergebnis) für EIN Diktat-Segment = eine Region.
        Läuft im Worker-Thread (bei mehreren Regionen parallel) — KEINE UI-Zugriffe hier."""
        template_key = detect_template(raw)
        template_data = RADIOLOGY_TEMPLATES.get(template_key, ALLGEMEIN_FALLBACK)

        # RAG-Bypass-Shortcut für reine Normalbefunde (nur bei ERKANNTER Region —
        # bei 'allgemein' lieber LLM-Strukturierung, damit echte Normalbefund-Templates greifen)
        if self._ist_normalbefund(raw, template_key):
            print(f"[BYPASS] Normalbefund erkannt: '{raw}'. Generiere direkt aus Template '{template_key}'.")
            # v3.2 (Peter 05.10.): Ergebnis = Normal-Ergebnis der Untersuchung (+ Seite) — NIE das Diktat abschreiben
            ergebnis = br.ergebnis_mit_seite(template_data.get('ergebnis', ''), raw)
            tpl_lines = template_data['body'].split('\n')
            tpl_title = br.titel_mit_seite(derive_untersuchungs_titel(raw, tpl_lines[0].strip().rstrip(':')), raw)
            tpl_body = '\n'.join(tpl_lines[1:])
            return br.nachbearbeiten(f"## {tpl_title}\n\n## Befund\n{tpl_body}\n\n## Ergebnis\n{ergebnis}")  # v3.2.2: CSA-Platzhalter raus

        p_base = br.strip_prompt_marker(INITIAL_PROMPT_CONTENT)
        p_full = p_base.replace('{roh_text}', raw)
        p_full = p_full.replace('{template_body}', template_data['body'])
        p_full = p_full.replace('{region_name}', template_data['display_name'])
        # v2.10.13 (K3-Review Befund 2/3): Der LLM-Pfad bekommt die KANONISCHE
        # Bezeichnung (display_name, inkl. "(Allgemein)"), damit die
        # "(Allgemein)"-Ausnahme im Gen-Prompt ECHT feuern kann — bei
        # pathologischen (Allgemein)-Diktaten leitet das LLM die Überschrift
        # aus dem Diktat (ohne Befundworte), statt den Volltext als Titel zu
        # bekommen. Der Bypass-Pfad bleibt bei derive.
        p_full = p_full + "\n<untersuchung>" + template_data['display_name'] + "</untersuchung>\n"
        # v3.2 (Peter 05.10.): Normal-Ergebnis der Untersuchung — fürs Ergebnis, wenn das Diktat keine Pathologie nennt
        p_full = p_full + "<normal_ergebnis>" + (template_data.get('ergebnis') or "Unauffälliger Befund.") + "</normal_ergebnis>\n"
        if MISHEARD_HINTS:  # v3.1: kontextabhängige Verhörer (mode 'llm') als Hinweis für Gemini
            p_full = p_full + MISHEARD_HINTS + "\n"

        # RAG Few-Shot Beispiele (practice_reports.db) — v3.2: Standard AUS (RAG_BEISPIELE in config.ini)
        examples_str = ""
        if RAG_BEISPIELE > 0 and not _nb.is_pure_normal_finding(raw, DISPLAY_NAMES):
            db_path = os.path.join(BASE_DIR, "practice_reports.db")
            examples_str = get_few_shot_examples(raw, classify_report(raw), db_path, limit=RAG_BEISPIELE)
        if "{examples}" in p_full:
            p_full = p_full.replace("{examples}", examples_str)
        else:
            p_full = p_full + "\n\n" + examples_str

        report = ""
        if LLM_PROVIDER == 'gemini':
            # Vertex AI REST API Call (Auth via x-goog-api-key Header)
            key = _load_vertex_key() or API_KEY or os.environ.get("GEMINI_API_KEY", "")
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": key,
            }
            body = json.dumps({
                "contents": [{"role": "user", "parts": [{"text": p_full}]}],
                "systemInstruction": {"parts": [{"text": SYS_MSG}]},
                # v2.10.15: thinkingBudget 0 (Web-Parität seit v2.10.1) — ohne denkt
                # Gemini dynamisch mit: Befund 7 s → ~1,5 s, gleiche Qualität (90-Fall-A/B).
                "generationConfig": {"temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}},
            }).encode()
            # v2.11.1 HOTFIX: ALLE Text-parts zusammensetzen (Gemini 3.5 splittet Antworten, z.B. '## L' | 'endenwirbel…')
            # + Vollständigkeits-Check (## Befund + ## Ergebnis, finishReason STOP) + bis zu 3 Versuche bei Fehler/Unvollständigkeit.
            last_err = None
            for _attempt in range(3):
                try:
                    req = urllib.request.Request(VERTEX_ENDPOINT, data=body, headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        result = json.loads(resp.read())
                    if "error" in result:
                        raise Exception(result["error"].get("message", result["error"]))
                    cand = result["candidates"][0]
                    txt = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", [])
                                  if isinstance(p.get("text"), str) and not p.get("thought")).strip()
                    txt = re.sub(r'^```[a-zA-Z]*\s*\n?', '', txt)
                    txt = re.sub(r'\n?```\s*$', '', txt).strip()
                    if _report_complete(txt) and cand.get("finishReason", "STOP") == "STOP":
                        report = txt
                        break
                    last_err = Exception("Befund unvollständig (## Ergebnis fehlt)")
                    print(f"[GEN] Versuch {_attempt + 1}: Befund unvollständig — neuer Versuch")
                except Exception as _e:
                    last_err = _e
                    if "401" in str(_e) or "Unauthorized" in str(_e):
                        break
                    print(f"[GEN] Versuch {_attempt + 1} fehlgeschlagen: {_e}")
                    time.sleep(2 * (_attempt + 1))
            if not report:
                raise last_err or Exception("Gemini lieferte keinen Befund")
        else:
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

        # v3.2: '## Befund' sichern + Ergebnis deterministisch nummerieren (einzelner Normalbefund-Satz unnummeriert)
        return br.nachbearbeiten(report)

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
        keyboard.add_hotkey('f9', lambda: self.after(0, self.reset_dictation), suppress=True)

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = RaKScribeApp()
    app.mainloop()
