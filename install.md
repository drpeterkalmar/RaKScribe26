# ⚙️ RaKScribe26 - Installationsanleitung

Diese Anleitung führt Sie Schritt für Schritt durch die Einrichtung von **RaKScribe26** für den radiologischen Befundungsalltag.

---

## 1. Systemvoraussetzungen 💻

Je nachdem, welchen Modus Sie in der `config.ini` wählen, gelten unterschiedliche Anforderungen:

### A. Online-Modus (Empfohlen für Standard-PCs)
* **Betriebssystem:** Windows 10 / 11
* **Python:** Version 3.12 oder neuer
* **Hardware:** Minimal. Funktioniert auch auf alten Praxis-Arbeitsplätzen mit Onboard-Grafikkarte oder älteren Prozessoren, da die Berechnung auf Google-Servern erfolgt.
* **Internetverbindung:** Erforderlich für die Google Cloud Speech-to-Text und Gemini API-Anfragen.

### B. Offline-Modus (Für High-End-PCs mit Grafikkarte)
* **Betriebssystem:** Windows 10 / 11
* **Hardware:** **NVIDIA-Grafikkarte** mit mindestens **8 GB VRAM** (z. B. RTX 3060/4060 oder besser) für flüssiges, verzögerungsfreies Arbeiten.
* **Zusatzsoftware:** Lokaler Ollama-Server für die KI-Strukturierung.

---

## 2. Installationsschritte 🚀

### Schritt 1: Python installieren
1. Laden Sie Python 3.12 von der offiziellen Webseite herunter: [python.org/downloads](https://www.python.org/downloads/)
2. **Wichtig:** Aktivieren Sie bei der Installation das Kontrollkästchen **"Add Python.exe to PATH"**.

### Schritt 2: Repository herunterladen und entpacken
1. Laden Sie das ZIP-Archiv von GitHub herunter und entpacken Sie es in einen Ordner Ihrer Wahl (z. B. `C:\RaKScribe26`).

### Schritt 3: Google Service Account Key hinterlegen (Nur Online-Modus)
1. Platzieren Sie Ihre Google Cloud JSON-Schlüsseldatei (z. B. `rakscribe-0ff1ffd128a1.json`) direkt im Hauptverzeichnis des entpackten Ordners.
2. Das Programm liest diesen API-Schlüssel automatisch aus und verwendet ihn sowohl für die Spracherkennung (Speech-to-Text) als auch für das Sprachmodell (Gemini Flash).

### Schritt 4: Python-Abhängigkeiten installieren
1. Öffnen Sie die Eingabeaufforderung (cmd) oder PowerShell im Programmordner.
2. Führen Sie folgenden Befehl aus, um alle notwendigen Bibliotheken zu installieren:
   ```cmd
   pip install -r requirements.txt
   ```

---

## 3. Konfiguration anpassen (`config.ini`) 🛠️

Öffnen Sie die Datei `config.ini` im Hauptverzeichnis mit einem Texteditor (z. B. Notepad), um das Verhalten anzupassen:

```ini
[SETTINGS]
# LLM-Provider: 'gemini' (online), 'openai' (online) oder 'ollama' (lokal offline)
LLM_PROVIDER = gemini

# Modellname je nach Provider:
# - Für gemini: gemini-1.5-flash (empfohlen für blitzschnelle Befunde)
# - Für ollama: gemma2:9b (empfohlen) oder gemma4:12b
LLM_MODEL = gemini-1.5-flash

# API-Key für Online-Modelle (kann bei Gemini leer bleiben, wenn rakscribe-*.json vorhanden ist)
API_KEY = 

# Spracherkennung: 'google' (online, live streaming) oder 'whisper' (offline, batch)
STT_ENGINE = google

# Dateiname der Google Cloud JSON-Schlüsseldatei (muss im Hauptverzeichnis liegen)
GOOGLE_JSON_FILENAME = rakscribe-0ff1ffd128a1.json
```

---

## 4. Anwendung starten und bedienen 🎤

1. Starten Sie das Programm einfach per Doppelklick auf die Datei **`start rakscribe.bat`** im Hauptverzeichnis.
2. Drücken Sie **F10**, um das Diktat zu starten. Sprechen Sie Ihren Befund ein.
3. Drücken Sie **F10** erneut, um die Aufnahme zu stoppen.
4. Die Anwendung überträgt das Diktat, strukturiert es in *Befund* und *Beurteilung* anhand Ihrer Templates und fügt es **automatisch** per `Ctrl+V` in Ihre aktuell geöffnete Anwendung (z. B. Ihr RIS oder MS Word) ein.

---

## 🔍 Diagnose & Fehlerbehebung (Troubleshooting)

Alle Aktivitäten, Warnungen und Fehler werden in die Datei **`rakscribe.log`** im Hauptverzeichnis geschrieben. Sollte etwas nicht funktionieren:
* **Kein Ton erkannt:** Prüfen Sie im Log (`rakscribe.log`), ob Ihr Standard-Mikrofon korrekt erkannt und angesprochen wird.
* **Fehler bei der Google API:** Stellen Sie sicher, dass Ihre JSON-Schlüsseldatei im Hauptverzeichnis liegt und der Name in der `config.ini` exakt übereinstimmt.
* **Latenzprobleme:** Wenn Sie den Offline-Modus nutzen und die Antwort zu lange dauert, prüfen Sie, ob Ihre NVIDIA-Grafikkarte von CUDA angesprochen wird oder ob auf die langsame CPU ausgewichen wurde.

---
*(c) 2026 Dr. Peter Kalmar - Modernes Reporting für die radiologische Praxis.*
