# ⚙️ KaiScribe (vormals RaKScribe) – Installationsanleitung

> **Name:** Seit Version 3.17.0 (Oktober 2026) heißt das Programm **KaiScribe** (Familie: KaiScribe = Diktat/Befund, KaiView = Viewer, KaiRad = Dachname). Seit dem Umzug im November 2026 heißt es auch technisch so: Programmdatei `KaiScribe.exe`, Benutzer-Ordner `%APPDATA%\KaiScribe`, Schlüsseldatei `kaiscribe-praxis-key.json`, Ordner auf dem Praxis-Laufwerk `X:\KaiScribe`.
> **Übergang:** Das Release enthält zusätzlich `rakscribe26.exe` (dieselbe Datei), damit alte Update-Wege und Links weiter gehen. KaiScribe liest den alten Schlüsselnamen `rakscribe-praxis-key.json` weiter, kopiert `%APPDATA%\RaKScribe` beim ersten Start einmal nach `%APPDATA%\KaiScribe` (der alte Ordner bleibt) und nimmt `X:\RaKScribe`, solange es `X:\KaiScribe` noch nicht gibt. Unverändert bleiben Repo `RaKScribe26` und der Pages-Pfad `/RaKScribe26/`.

Diese Anleitung führt Sie Schritt für Schritt durch die Einrichtung von **KaiScribe** für den radiologischen Befundungsalltag.

---

## 1. Systemvoraussetzungen 💻

* **Betriebssystem:** Windows 10 / 11 (64-Bit)
* **Hardware:** Minimal – läuft auch auf älteren Praxis-PCs, da die Berechnung auf Google-Servern erfolgt
* **Internetverbindung:** Erforderlich für Google Cloud Speech-to-Text und Gemini API
* **Python:** ❌ Nicht erforderlich – die EXE-Datei ist vollständig eigenständig

---

## 2. Installation 🚀

### Schritt 1: EXE bekommen
Die Befund-PCs bekommen die EXE automatisch über das Praxis-Update (RaK-Befund-Paket → Praxis-Laufwerk `X:`).
Seit KaiScribe privat ist (kaiscribe-privat-n1, 11/2026) gibt es keinen öffentlichen Download mehr; am Mac liegt das
Release im privaten Repo (`gh release download -R drpeterkalmar/RaKScribe26 -p KaiScribe.exe`). Vorlagen, Prompt und
Fehlhör-Liste sind in der EXE eingebaut, `config.ini` legt sie beim ersten Start selbst an.

### Schritt 2: Praxis-Key hinterlegen (EIN Key für alles)
1. Kopieren Sie die Datei `kaiscribe-praxis-key.json` (im Praxis-Drive, bis 11/2026 `rakscribe-praxis-key.json` – beide Namen gehen) **in denselben Ordner** wie die EXE.
2. Das ist alles – keine config.ini-Änderung nötig. Diese **eine Datei** authentifiziert automatisch sowohl die Spracherkennung (Speech-to-Text) als auch das Sprachmodell (Gemini Flash).

> **Hinweis:** Ältere Setups mit getrennten Schlüsseldateien (`vertex-key.b64`, `rakscribe-stt-key.json`) funktionieren weiterhin, sind aber nicht mehr nötig.

### Schritt 3: Starten
Doppelklick auf **`KaiScribe.exe`** – fertig. ✅

---

## 3. Konfiguration anpassen (`config.ini`) 🛠️

Normalerweise ist nichts zu tun. `config.ini` liegt neben der EXE und enthält nur:

```ini
[SETTINGS]
# Befund-KI: gemini = Gemini 3.5 Flash über Vertex AI am EU-Endpoint (Modell und Endpoint sind fest eingebaut).
# Der Schlüssel kommt ausschließlich aus kaiscribe-praxis-key.json (Rückfall rakscribe-praxis-key.json) — nicht hier eintragen.
LLM_PROVIDER = gemini
LLM_MODEL = gemini-3.5-flash

# Optional (Standard 0 = aus): Anzahl Praxis-Beispiele aus practice_reports.db im Prompt
# RAG_BEISPIELE = 0
```

Fehlt die Datei, legt die EXE sie beim Start mit diesen Werten an. Fehlt eine Zeile oder ist ein Wert unbrauchbar,
gilt der Standardwert (Hinweis in `rakscribe.log`). Nur eine nicht lesbare Datei (z. B. ohne `[SETTINGS]`-Kopf)
führt zu einer Fehlermeldung beim Start — dann Datei korrigieren oder löschen.
Frühere Einträge `API_KEY` (für Gemini), `CHUNK_DURATION`, `GOOGLE_JSON_FILENAME` und `STT_ENGINE` werden nicht mehr
ausgewertet und dürfen gelöscht werden.

---

## 4. Bedienung 🎤

1. Doppelklick auf **`KaiScribe.exe`**
2. **F10** drücken → Diktat starten
3. Befund einsprechen
4. **F10** erneut drücken → Aufnahme stoppen
5. Die KI strukturiert den Befund in *Befund* und *Beurteilung* und fügt ihn per **Ctrl+V** direkt in Ihr RIS, Word oder KIS ein

**F9** – Alle Felder zurücksetzen (z. B. bei falsch gestarteten Diktaten)

---

## 🔍 Diagnose & Fehlerbehebung

Alle Aktivitäten, Warnungen und Fehler werden in die Datei **`rakscribe.log`** geschrieben:

* **Kein Ton erkannt:** Prüfen Sie im Log, ob Ihr Standard-Mikrofon korrekt erkannt wird.
* **Fehler bei der Google API:** Stellen Sie sicher, dass `kaiscribe-praxis-key.json` (oder der alte Name `rakscribe-praxis-key.json`) im selben Ordner wie die EXE liegt (Ein-Key-Setup). Ältere Setups: Dateiname in `config.ini` unter `GOOGLE_JSON_FILENAME` prüfen.
* **Windows Defender / Antivirus:** Da die EXE selbst kompiliert ist, kann ein Hinweis erscheinen. Klicken Sie auf „Weitere Informationen" → „Trotzdem ausführen".

---
*(c) 2026 Dr. Peter Kalmar - Modernes Reporting für die radiologische Praxis.*
