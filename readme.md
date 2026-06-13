# 🚀 RaKScribe26

**Intelligentes Reporting und strukturiertes radiologisches Befunden** – blitzschnell, hochpräzise und maßgeschneidert für den klinischen Alltag.

RaKScribe26 ist die Weiterentwicklung des offline-basierten radiologischen Befundungsassistenten. Es kombiniert die unglaubliche Geschwindigkeit und Qualität moderner Online-KI-Modelle mit dem bewährten lokalen Workflow, um Diktate in Sekundenschnelle in strukturierte Berichte (mit *Befund* und *Beurteilung*) zu übersetzen und direkt in Ihr RIS oder Word einzufügen.

> **Neu in v2.6.0:** Klarer Fokus auf **modalitätsspezifische Befundvorlagen** – RaKScribe26 erkennt automatisch die Bildgebungsmodalität und wählt die passende Vorlage. Unterstützte Modalitäten: Röntgen (Skelett, Thorax, HWS/BWS/LWS, Schädel, Fernröntgen), Sonographie (Abdomen, Weichteile, Gelenke, Schilddrüse, Gefäße), Mammographie, Durchleuchtung, DEXA-Knochendichtemessung, Zahnröntgen (OPG) und Digitale Volumentomographie (DVT).

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

## 💰 API-Kosten-Kalkulation (Online-Modus)

Für den Online-Modus fallen bei Google folgende minimale Gebühren an:

* **Spracherkennung (Google Cloud Speech-to-Text):**
  * Tarif: **$0,024 pro Minute** (aufgerundet auf 15-Sekunden-Schritte).
  * **10-Sekunden-Diktat:** Kostet ca. **$0,006** (~0,6 Cent).
  * **Gratis-Kontingent:** Die ersten **60 Minuten** pro Monat sind **komplett kostenlos** (entspricht ca. 360 Diktaten à 10s).
* **Strukturierung (Google Gemini 1.5 Flash):**
  * Tarif: **$0,075 / 1 Mio. Input-Tokens** und **$0,30 / 1 Mio. Output-Tokens**.
  * **Kosten pro Befund:** Bei einem Prompt mit ca. 1.500 Tokens (inkl. Vorlagen) und 200 Tokens Antwort entspricht das ca. **$0,00017** (~0,017 Cent).
  * **Gratis-Kontingent:** Komplett **kostenfrei** im AI Studio Free Tier (bis zu 15 Anfragen/Minute).

**Gesamtkosten pro 10-Sekunden-Befund:** Weniger als **1 Cent** (ca. **0,6 Cent** im regulären Tarif bzw. **0,0 Cent** im Rahmen der monatlichen Freibeträge). Bei ca. 100 Befunden am Tag entspricht dies Betriebskosten von ca. **60 Cent**.

---


## ⭐ Hauptmerkmale

* **🏥 Modalitätsspezifische Befundvorlagen:** RaKScribe26 erkennt automatisch die Bildgebungsmodalität des diktierten Befunds und wählt die passende strukturierte Vorlage. Jede Modalität hat eigene, klinisch präzise Templates – keine Verwechslung mehr zwischen Röntgen, Sonographie und Nervenschall.
* **⚡ Sub-Sekunden-Latenz:** Befunde werden online via Gemini Flash in unter 2 Sekunden fertig strukturiert und formatiert zurückgeliefert.
* **🔑 Zero-Configuration:** Keine manuelle API-Key-Eingabe nötig! Die Anwendung verwendet automatisch Ihre Google Speech-to-Text-Schlüsseldatei (`google-service-account.json`) zur sicheren Authentifizierung bei Gemini.
* **📋 Auto-Paste & Hotkey (F10):** Ein einziger Tastendruck auf **F10** startet und stoppt das Diktat. Nach Beendigung wird der fertige Befund automatisch in die Zwischenablage kopiert und per `Ctrl+V` direkt in Ihr aktives RIS, Word oder KIS eingefügt.
* **🔄 Reset-Hotkey (F9):** Schnelles Zurücksetzen aller Felder mit **F9** – ideal wenn ein Diktat falsch gestartet wurde oder die Vorlage neu gewählt werden soll.
* **🩺 Medizinisches Vokabular:** Ein integrierter Wortschatz-Boost sorgt dafür, dass komplexe radiologische Fachbegriffe (z. B. *Spondylarthrose*, *Rotatorenmanschettenruptur*, *Rhizarthrose*) fehlerfrei erkannt werden.
* **🪵 Diagnose-Protokollierung:** Automatisches Schreiben von Log-Ausgaben und Mikrofon-Pegeldaten (RMS) in eine lokale `rakscribe.log`, um Treiber- oder Datenschutzprobleme auf einzelnen PCs sofort aufzuspüren.

---

## 🏥 Unterstützte Modalitäten & Befundvorlagen

Jede Modalität verfügt über eigene, klinisch präzise Befundvorlagen. Die automatische Erkennung erfolgt auf Basis von Schlüsselwörtern im Diktat:

| Modalität | Beispiele / Templates |
| :--- | :--- |
| **Röntgen – Skelett & Gelenke** | Hand, Handgelenk, Finger, Daumen, Schulter, Ellbogen, Knie, Sprunggelenk, Fuß, Zehengelenke, Becken, Hüfte |
| **Röntgen – Wirbelsäule** | HWS, BWS, LWS (je ap + seitlich) |
| **Röntgen – Thorax** | Thorax pa, Thorax ap liegend |
| **Röntgen – Schädel** | Schädel standard, Schädelfernröntgen (lateral/pa, unauffällig) |
| **Sonographie – Abdomen** | Oberbauch, Ganzes Abdomen, Nieren |
| **Sonographie – Weichteile** | Weichteilsonographie, Nervenschall (Leitbahnen, Gelenke sonographisch) |
| **Sonographie – Schilddrüse** | Schilddrüse, Halsweichteile |
| **Mammographie** | Standard-Mammographie bilateral, Befund & BIRADS-Kategorie |
| **Durchleuchtung** | Ösophagus, Magen, Darm, Kontrastmittel-Untersuchungen |
| **DEXA** | Knochendichtemessung LWS + Femur, T-Score, Z-Score, Osteoporose-Einschätzung |
| **Zahnröntgen (OPG)** | Orthopantomogramm, Einzelzahnaufnahmen |
| **DVT** | Digitale Volumentomographie Oberkiefer, Unterkiefer |

---

## 🚀 Schnellstart & Installation

Eine ausführliche Anleitung zur Einrichtung finden Sie in der **[INSTALL.md](INSTALL.md)**.

### 1. Release herunterladen
Laden Sie die neueste Version vom [Releases-Tab](https://github.com/drpeterkalmar/RaKScribe26/releases) herunter. Sie benötigen:
* `rakscribe26.exe` – die fertige Anwendung (kein Python erforderlich)
* `config.ini` – Konfigurationsdatei
* `templates.json` – Befundvorlagen
* `radiology_prompt.txt` – System-Prompt für die KI

Alle Dateien in **denselben Ordner** legen.

### 2. Google Service Account hinterlegen
Platzieren Sie Ihre Google Cloud JSON-Schlüsseldatei im selben Ordner und tragen Sie den Dateinamen in der `config.ini` unter `GOOGLE_JSON_FILENAME` ein.

### 3. Starten
Doppelklick auf **`rakscribe26.exe`** – fertig. Kein Python, keine Installation nötig.

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
GOOGLE_JSON_FILENAME = google-service-account.json
```

---
*(c) 2025-2026 Dr. Peter Kalmar - Modernes Reporting für die radiologische Praxis.*
