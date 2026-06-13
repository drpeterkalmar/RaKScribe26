# 🚀 RaKScribe26

**Intelligentes Reporting und strukturiertes radiologisches Befunden** – blitzschnell, hochpräzise und maßgeschneidert für den klinischen Alltag.

RaKScribe26 ist die Weiterentwicklung des offline-basierten radiologischen Befundungsassistenten. Es kombiniert die unglaubliche Geschwindigkeit und Qualität moderner Online-KI-Modelle mit dem bewährten lokalen Workflow, um Diktate in Sekundenschnelle in strukturierte Berichte (mit *Befund* und *Beurteilung*) zu übersetzen und direkt in Ihr RIS oder Word einzufügen.

---

## 💡 Architektur: Hybrid Online & Offline

RaKScribe26 unterstützt zwei hocheffiziente Betriebsmodi, um sich perfekt an Ihre Praxis-Infrastruktur anzupassen:

| Komponente | Online-Modus (Empfohlen für Standard-Arbeitsplätze) | Offline-Modus (Für High-End-Workstations mit GPU) |
| :--- | :--- | :--- |
| **Spracherkennung (STT)** | **Google Cloud Speech-to-Text** (Übertragung via HTTPS, extrem präzise, inkl. Fachbegriff-Boost) | **Faster-Whisper** (Lokal auf dem Rechner via GPU/CPU) |
| **Strukturierung (LLM)** | **Google Gemini 1.5 Flash** (Unter-Sekunden-Antwortzeiten, zero-configuration) | **MedGemma / Gemma2** (Betrieben über lokales Ollama) |
| **API-Kosten** | **Praktisch 0 €** (Erste 60 Min. STT/Monat gratis, Gemini im Free Tier kostenlos) | **0 €** (Komplett kostenfrei) |
| **Hardware-Bedarf** | **Minimal** (Läuft flüssig auf alten Praxis-PCs mit Onboard-GPU) | **Hoch** (NVIDIA-GPU mit mind. 8GB VRAM benötigt) |

---

## ⭐ Hauptmerkmale

* **⚡ Sub-Sekunden-Latenz:** Befunde werden online via Gemini Flash in unter 2 Sekunden fertig strukturiert und formatiert zurückgeliefert.
* **🔑 Zero-Configuration:** Keine manuelle API-Key-Eingabe nötig! Die Anwendung verwendet automatisch Ihre Google Speech-to-Text-Schlüsseldatei (`rakscribe-0ff1ffd128a1.json`) zur sicheren Authentifizierung bei Gemini.
* **📋 Auto-Paste & Hotkey (F10):** Ein einziger Tastendruck auf **F10** startet und stoppt das Diktat. Nach Beendigung wird der fertige Befund automatisch in die Zwischenablage kopiert und per `Ctrl+V` direkt in Ihr aktives RIS, Word oder KIS eingefügt.
* **🩺 Medizinisches Vokabular:** Ein integrierter Wortschatz-Boost sorgt dafür, dass komplexe radiologische Fachbegriffe (z. B. *Spondylarthrose*, *Rotatorenmanschettenruptur*, *Rhizarthrose*) fehlerfrei erkannt werden.
* **🪵 Diagnose-Protokollierung:** Automatisches Schreiben von Log-Ausgaben und Mikrofon-Pegeldaten (RMS) in eine lokale `rakscribe.log`, um Treiber- oder Datenschutzprobleme auf einzelnen PCs sofort aufzuspüren.

---

## 🚀 Schnellstart & Installation

Eine ausführliche Anleitung zur Einrichtung aller Komponenten finden Sie in der **[INSTALL.md](INSTALL.md)**.

### 1. Repository klonen & vorbereiten
Stellen Sie sicher, dass sich folgende Dateien im Projektverzeichnis befinden:
* `config.ini` – Ihre Einstellungen (Standardmäßig auf Online-Modus konfiguriert)
* `templates.json` – Ihre Normalbefunde und radiologischen Templates
* `radiology_prompt.txt` – Der System-Prompt für die KI-Strukturierung
* `practice_reports.db` – Die lokale SQLite-Datenbank für Praxis-Referenzen
* `rakscribe-0ff1ffd128a1.json` – Ihre Google Cloud Service-Account-Schlüsseldatei

### 2. Abhängigkeiten installieren
```bash
pip install -r source_code/requirements.txt
```

### 3. Anwendung starten
Starten Sie das Programm einfach per Doppelklick auf die Batch-Datei im Hauptverzeichnis:
```bash
start rakscribe.bat
```

---

## ⚙️ Konfigurations-Beispiel (`config.ini`)

```ini
[SETTINGS]
# LLM-Provider: 'gemini' (online), 'openai' (online) oder 'ollama' (lokal)
LLM_PROVIDER = gemini
LLM_MODEL = gemini-1.5-flash

# API-Key (kann für Gemini leer bleiben, da die STT-Schlüsseldatei wiederverwendet wird)
API_KEY = 

# Spracherkennung: 'google' (online, live streaming) oder 'whisper' (offline)
STT_ENGINE = google
GOOGLE_JSON_FILENAME = rakscribe-0ff1ffd128a1.json
```

---
*(c) 2025-2026 Dr. Peter Kalmar - Modernes Reporting für die radiologische Praxis.*
