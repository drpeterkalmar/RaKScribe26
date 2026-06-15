# ⚙️ RaKScribe26 - Installationsanleitung

Diese Anleitung führt Sie Schritt für Schritt durch die Einrichtung von **RaKScribe26** für den radiologischen Befundungsalltag.

---

## 1. Systemvoraussetzungen 💻

* **Betriebssystem:** Windows 10 / 11 (64-Bit)
* **Hardware:** Minimal – läuft auch auf älteren Praxis-PCs, da die Berechnung auf Google-Servern erfolgt
* **Internetverbindung:** Erforderlich für Google Cloud Speech-to-Text und Gemini API
* **Python:** ❌ Nicht erforderlich – die EXE-Datei ist vollständig eigenständig

---

## 2. Installation 🚀

### Schritt 1: Release herunterladen
Öffnen Sie den [Releases-Tab auf GitHub](https://github.com/drpeterkalmar/RaKScribe26/releases) und laden Sie die folgenden Dateien herunter:

| Datei | Beschreibung |
| :--- | :--- |
| `rakscribe26.exe` | Die fertige Anwendung – kein Python nötig |
| `config.ini` | Konfigurationsdatei (LLM-Provider, STT-Engine, etc.) |
| `templates.json` | Modalitätsspezifische Befundvorlagen |
| `radiology_prompt.txt` | System-Prompt für die KI-Strukturierung |

Legen Sie **alle Dateien in denselben Ordner** (z. B. `C:\RaKScribe26\`).

### Schritt 2: Google Service Account Key hinterlegen
1. Platzieren Sie Ihre Google Cloud JSON-Schlüsseldatei (z. B. `google-service-account.json`) **in denselben Ordner** wie die EXE.
2. Öffnen Sie `config.ini` mit einem Texteditor und tragen Sie den genauen Dateinamen ein:
   ```ini
   GOOGLE_JSON_FILENAME = google-service-account.json
   ```
   Das Programm verwendet diese Datei automatisch für Spracherkennung (Speech-to-Text) und das Sprachmodell (Gemini Flash).

### Schritt 3: Starten
Doppelklick auf **`rakscribe26.exe`** – fertig. ✅

---

## 3. Konfiguration anpassen (`config.ini`) 🛠️

Öffnen Sie die Datei `config.ini` im Texteditor, um das Verhalten anzupassen:

```ini
[SETTINGS]
# LLM-Provider: 'gemini' (Google AI Studio) oder 'openai' (OpenAI)
LLM_PROVIDER = gemini

# Modellname je nach Provider:
# - Für gemini: gemini-1.5-flash (empfohlen), gemini-1.5-pro
# - Für openai: gpt-4o-mini (empfohlen), gpt-4o
LLM_MODEL = gemini-1.5-flash

# API-Key (kann bei Gemini leer bleiben, wenn die JSON-Schlüsseldatei vorhanden ist)
API_KEY = 

# Chunk-Dauer in Sekunden für das Google Streaming (empfohlen: 7)
CHUNK_DURATION = 7

# Dateiname der Google Cloud JSON-Schlüsseldatei (muss im Hauptverzeichnis liegen)
GOOGLE_JSON_FILENAME = google-service-account.json
```

---

## 4. Bedienung 🎤

1. Doppelklick auf **`rakscribe26.exe`**
2. **F10** drücken → Diktat starten
3. Befund einsprechen
4. **F10** erneut drücken → Aufnahme stoppen
5. Die KI strukturiert den Befund in *Befund* und *Beurteilung* und fügt ihn per **Ctrl+V** direkt in Ihr RIS, Word oder KIS ein

**F9** – Alle Felder zurücksetzen (z. B. bei falsch gestarteten Diktaten)

---

## 🔍 Diagnose & Fehlerbehebung

Alle Aktivitäten, Warnungen und Fehler werden in die Datei **`rakscribe.log`** geschrieben:

* **Kein Ton erkannt:** Prüfen Sie im Log, ob Ihr Standard-Mikrofon korrekt erkannt wird.
* **Fehler bei der Google API:** Stellen Sie sicher, dass die JSON-Schlüsseldatei im selben Ordner wie die EXE liegt und der Name in `config.ini` exakt übereinstimmt.
* **Windows Defender / Antivirus:** Da die EXE selbst kompiliert ist, kann ein Hinweis erscheinen. Klicken Sie auf „Weitere Informationen" → „Trotzdem ausführen".

---
*(c) 2026 Dr. Peter Kalmar - Modernes Reporting für die radiologische Praxis.*
