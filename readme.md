# 🚀 RaKScribe26

**Intelligentes Reporting und strukturiertes radiologisches Befunden** – blitzschnell, hochpräzise und maßgeschneidert für den klinischen Alltag.

RaKScribe26 ist ein hocheffizienter radiologischer Befundungsassistent. Es kombiniert die unglaubliche Geschwindigkeit und Qualität moderner Online-KI-Modelle mit dem bewährten lokalen Workflow, um Diktate in Sekundenschnelle in strukturierte Berichte (mit *Befund* und *Beurteilung*) zu übersetzen und direkt in Ihr RIS oder Word einzufügen.

> **Neu in v2.8.0:** Erweiterte Nervensonographie-Templates (**N. radialis, N. ischiadicus, N. peroneus, N. tibialis, N. femoralis, N. femoralis cutaneus lateralis, N. pudendus, Nn. iliohypogastricus/ilioinguinalis, Plexus cervicalis**) sowie **Mammasonographie** und **Ultraschall-gezielte Blockade**. Befund-Prompt an die Qualitätsstandards der Web-App angeglichen (Anti-Pattern-Regeln, Konsistenz- und Konfliktregeln, CSA-Regel für Nerven, "Bild wie bei"-Regel).

---

## 💡 Architektur: Online-Only 💻

Um eine maximale Vereinfachung, Stabilität und einen minimalen Hardware-Bedarf zu garantieren, läuft RaKScribe26 als reine Online-Anwendung:

* **Spracherkennung (STT):** **Google Cloud Speech-to-Text** (sichere Übertragung via HTTPS, live-streaming, extrem präzise inkl. medizinischem Fachwortschatz-Boost).
* **Strukturierung (LLM):** **Google Gemini 1.5 Flash** (unter-Sekunden Antwortzeiten, zero-configuration) oder optional **OpenAI GPT-4o-mini**.
* **Hardware-Bedarf:** **Minimal** – läuft extrem flüssig auf jedem standardmäßigen Praxis- oder Büro-PC (keine dedizierte Grafikkarte nötig, da keine Berechnungen lokal stattfinden).
* **Programmgröße:** Durch den Wegfall schwerer Machine-Learning-Bibliotheken (PyTorch, onnxruntime, CUDA) wurde das Programm auf **~75 MB** verkleinert.

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
* **🔑 Ein Key für alles:** Eine einzige Datei (`rakscribe-praxis-key.json`) authentifiziert Spracherkennung (Speech-to-Text) **und** Gemini – keine manuelle API-Key-Eingabe, keine separate Konfiguration.
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

### 2. Praxis-Key hinterlegen (EIN Key für alles)
Legen Sie `rakscribe-praxis-key.json` (aus dem Drive-Ordner „RaKScribe") in denselben Ordner wie die EXE. Fertig – diese eine Datei versorgt Spracherkennung **und** Gemini.

### 3. Starten
Doppelklick auf **`rakscribe26.exe`** – fertig. Kein Python, keine Installation nötig.

---

## ⚙️ Konfiguration (`config.ini`, optional)

```ini
[SETTINGS]
# Befund-KI: gemini = Gemini 3.5 Flash über Vertex AI am EU-Endpoint (Modell und Endpoint sind fest eingebaut).
# Der Schlüssel kommt ausschließlich aus rakscribe-praxis-key.json — nicht hier eintragen.
LLM_PROVIDER = gemini
LLM_MODEL = gemini-3.5-flash

# Optional (Standard 0 = aus): Anzahl Praxis-Beispiele aus practice_reports.db im Prompt
# RAG_BEISPIELE = 0

# Optional (ab v3.15.0): SpeechMike-Tasten der Mammo-Maske (Standard aus masken.json). Mehrere Tasten mit Leerzeichen.
# Erlaubt: FF, REW, F3, F4, PLAY, INSTR, COMMAND — Record, INS, EOL, Stop, F1, F2 bleiben immer, wie sie sind.
# [MASKE]
# NAECHSTES_FELD = FF
# VORIGES_FELD = REW
# UEBERNEHMEN = F3
# MASKE_UMSCHALTEN = F4
```

Fehlt die Datei, legt die EXE sie beim Start mit diesen Werten an. Fehlt eine Zeile oder ist ein Wert unbrauchbar,
gilt der Standardwert (Hinweis in `rakscribe.log`). Nur eine nicht lesbare Datei (z. B. ohne `[SETTINGS]`-Kopf)
führt zu einer Fehlermeldung beim Start — dann Datei korrigieren oder löschen.
Frühere Einträge `API_KEY` (für Gemini), `CHUNK_DURATION`, `GOOGLE_JSON_FILENAME` und `STT_ENGINE` werden nicht mehr
ausgewertet und dürfen gelöscht werden.

---

## 🛠️ Build und Version (für Entwickler)

- **EXE nur per GitHub-Workflow** „Build Windows EXE“ (`.github/workflows/build-exe.yml`): Paketliste `requirements.txt`
  (feste Versionen), Vorlagen/Prompt/Fehlhör-Liste/Phrasen/VERSION werden in die EXE gebündelt. Ein lokales `build.bat`
  gibt es nicht mehr (es bündelte die Daten nicht — die EXE fiel dann auf „allgemein“ zurück).
  Manueller Lauf: mit Tag → Release; ohne Tag → Vorabversion `test-<Lauf-Nr.>`; „release“ angehakt → Release mit der
  Version aus `VERSION`.
- **Versionsnummer nur in `VERSION`** (Repo-Root): EXE-Titel und -Badge, Web-Badge und Seitentitel lesen sie
  (`tests/offline/test_version_sync.py`).
- **Protokoll** `rakscribe.log` neben der EXE: höchstens 5 Dateien à 1 MB, ohne Diktatinhalt. Zur Fehlersuche
  mit Diktattext: Umgebungsvariable `RAKSCRIBE_DEBUG=1` (Web-Konsole: `localStorage.rakscribe_debug = '1'`).
- **Tests** laufen bei jedem Push (`.github/workflows/test.yml`); der Web-Deploy startet erst, wenn sie grün sind.

## ⏱️ Bereitschaft: RaKScribe wartet minimiert (EXE, ab v3.11.0)

- **Menü ☰ „Mit Windows starten (wartet minimiert)“**: Nach der Windows-Anmeldung wartet ein kleiner, unsichtbarer
  Starter (`%APPDATA%\RaKScribe\warte_auf_x.vbs`), bis die EXE erreichbar ist (X: kommt erst mit dem CAS-Login, höchstens
  4 h), und startet sie dann nur als Symbol in der Taskleiste. Keine lokale Kopie — Updates bleiben „eine Datei tauschen“.
- **Nach EOL im CAS-Modus** geht RaKScribe nach ~1,5 s wieder in die Taskleiste (Menü „Nach CAS-Befund minimieren“).
- **Nur eine RaKScribe**: Ein zweiter Start holt die laufende nach vorne. Schließen (X) beendet RaKScribe wie bisher.
- Bericht: [`BEREITSCHAFT_BERICHT.md`](BEREITSCHAFT_BERICHT.md).

## 🧭 CAS-Leistungen als Vorrang-Hinweis (EXE, ab v3.12.0)

- Die RaKScribe-Brücke (ab 1.1.0) reicht zum CAS-Diktat die Leistungen des Eintrags nach
  (`cas_leistungen_<id>.json`, Sekunden nach dem Auftrag). Das blaue Band zeigt sie: „CAS-Diktat <Nr> (<Kürzel>) · HWS ·
  Schulter re. (Sono)“. Ohne diese Datei arbeitet RaKScribe wie bisher.
- **Vorlagenwahl:** Die Erkennung aus dem Diktat läuft immer, die CAS-Liste ist ein Vorrang-Hinweis, kein Zwang
  (`source_code/cas_vorlagen.py`). Bestätigt das Diktat eine CAS-Region, gilt deren Vorlage. Nennt es nur die Region,
  während CAS eine andere Modalität kennt („Knie“ und „Sono Knie“), gilt die CAS-Vorlage. „Unauffällig.“ bekommt die
  einzige CAS-Vorlage. Nennt das Diktat eine Region außerhalb der CAS-Liste, gewinnt das Diktat, mit einem Hinweis.
- **Gemischte Diktate:** Bei mehreren CAS-Untersuchungen wird zusätzlich an Satzanfängen geteilt, die eine andere
  CAS-Untersuchung nennen („Fuß links: … LWS: …“). So entsteht je Untersuchung ein eigener Befund in Diktat-Reihenfolge.
- **Hinweise im Band:** „LWS laut CAS, nicht diktiert“, „… nicht in den CAS-Leistungen“ und „Seite: diktiert rechts,
  laut CAS links“. Ergänzt wird dabei nichts.
- **Nach EOL im CAS-Modus** steht 4,5 s ein grünes Band „✓ An CAS übergeben: <Nr> · <Titel>“, erst danach geht RaKScribe
  in die Taskleiste. In der Kopfzeile überdeckt „Bereit“ den Hinweis „SpeechMike verbunden“ nicht mehr.
- Ohne CAS-Leistungen bleiben Einzelbefunde bit-gleich (`tools/cas_bitgleich.py`, 726 Diktate). Tests:
  `tests/offline/test_cas_leistungen.py`, live `tools/test_all_regions.py --cas`. Die Zuordnung Leistungskürzel → Vorlage
  liegt in der Praxis (privat), nicht in diesem Repo.

## 📐 IB-Lab-Messwerte im CAS-Diktat (EXE, ab v3.13.0)

- Die RaKScribe-Brücke (ab 1.2.0) reicht zum CAS-Diktat die vorhandenen IB-Lab-Vorbefund-Bausteine nach
  (`cas_ibl_<id>.json`, beim Start oder später, eine neue Fassung ersetzt die alte). Das blaue Band zeigt eine eigene Zeile,
  z. B. „IB Lab: FROG rechts ✓“. Kommt etwas nach, wird die Zeile kurz grün hervorgehoben. Ohne Datei bleibt alles wie in
  3.12.0.
- **Messwerte 1:1, nie von der KI umformuliert:** Die KI erfährt nur, welche Messgrößen ergänzt werden (keine Zahlen) und
  welche widersprechenden Vorlagensätze sie weglassen soll. Nach der KI setzt `source_code/ibl_bausteine.py` die
  Befundzeilen ans Ende des Befundtexts der passenden Untersuchung und die Ergebnispunkte an deren Ergebnisliste.
  Zugeordnet wird über die Leistung im CAS-Eintrag, sonst über Modul und Region (FROG → Fuß, LAMA → Ganzbein, HIPPO →
  Becken/Hüfte, …), bei zwei Füßen über die Seite. Ist das nicht eindeutig, kommen die Werte als eigener Absatz ans Ende,
  mit Hinweis. Ein Messwert-Gate prüft, dass jede eingesetzte Zeile wörtlich im Befund steht.
- **Nichts doppelt, nichts still geändert:** Nennt das Diktat die Messgröße mit demselben Wert oder dieselbe Diagnose
  schon, wird sie nicht doppelt angefügt. Bei einem Widerspruch (andere Zahl, „kein Plattfuß“, unauffälliges Ergebnis,
  Vorlagensatz „Fußgewölbe regulär“) erscheint ein gelber Hinweis in der IB-Lab-Zeile, am Text ändert sich nichts. Die
  Hinweise des Bausteins (Bildqualität, Fraktur-Verdacht, Entwürfe) erscheinen nur dort, nie im Befund. Ein Klick auf die
  Zeile zeigt alle Werte und Hinweise.
- **Werte nach dem Befund:** RaKScribe ändert einen schon erstellten Befund nicht still. Stattdessen erscheint der Knopf
  „＋ IB Lab einfügen“, eine ältere Fassung wird dabei wörtlich ersetzt.
- Menü ☰ **„IB-Lab-Bausteine übernehmen“** (Standard an). Ohne Bausteine bzw. bei „aus“ sind Prompt und Befund bit-gleich
  mit 3.12.0 (726 Diktate). Tests: `tests/offline/test_ibl_bausteine.py`, live `tools/test_all_regions.py --ibl`.

## 🗂️ Kontext aus dem RIS und IB-Lab-Gerüst vor dem Diktat (EXE, ab v3.14.0)

- Die RaKScribe-Brücke (ab 2.0.0, Paket „RaK-Befund“) kann zum CAS-Diktat Angaben aus der Datenbank des RIS nachreichen
  (`cas_kontext_<id>.json`): **Zuweiser** und **Info** erscheinen als Kopfzeile im blauen Band, der **letzte Vorbefund
  derselben Untersuchung** öffnet sich über den Knopf „Vorbefund TT.MM.JJJJ“ in einem eigenen Fenster (nur lesen).
  Diese Angaben sind **nur Anzeige**: Sie gehen nie an die KI, nie in den Befund und nie ins Protokoll (dort nur Längen).
  Ein Test prüft, dass kein Prompt sie enthält (`tests/offline/test_cas_kontext.py`).
- Kommen die Leistungen aus der Datenbank, trägt jede ihre **Ziffer** (Accession = Diktatnummer + Ziffer) — die
  IB-Lab-Bausteine werden dann exakt der richtigen Untersuchung zugeordnet.
- **IB-Lab-Gerüst vor dem ersten Wort:** Liegen beim Öffnen schon IB-Lab-Werte vor, steht im Befund-Feld das Gerüst des
  strukturierten Befunds (Titel der Untersuchung, Messwerte wörtlich, Ergebnispunkte). **Auffällige Werte sind farbig
  hervorgehoben** — nur, wenn eine Regel des IB-Lab-Abholers (Schwellen mit Quelle) daraus einen Ergebnispunkt gemacht hat;
  sonst wird nichts gewertet. Diktiert wird wie gewohnt; der Befund aus dem Diktat ersetzt das Gerüst, die Messwerte
  setzt RaKScribe danach wieder wörtlich ein (wie seit 3.13.0). Ohne Werte gibt es kein Gerüst.
- **Werte, die erst später kommen**, setzt RaKScribe jetzt bis EOL selbst sichtbar in den Befund ein (Hinweis +
  Hervorhebung). Kamen sie weniger als 3 s vor EOL, muss EOL ein zweites Mal gedrückt werden — nie etwas Ungesehenes.

## 🩻 Mammo-Maske: Felder per SpeechMike-Taste, Vorbefund schon eingetragen (EXE, ab v3.15.0)

Hat ein CAS-Diktat eine **Mammographie-Leistung** (Screening oder kurativ), zeigt RaKScribe links statt des Diktat-Felds
die **Mammo-Maske** mit vier Feldern: **Inspektion und Palpation · Mammographie · Sonographie · Ergebnis** (mit ACR und
BI-RADS). Ohne Mamma-Sono-Leistung ist die Sonographie eingeklappt (Diktat oder Klick „＋ zuschalten“ holt sie dazu).

| Taste | SpeechMike III / Premium | SpeechMike Ambient (ab v3.15.4) | Tastatur |
|---|---|---|---|
| nächstes / voriges Feld (feste Reihenfolge: 3× = Ergebnis), auch während der Aufnahme | Vorspulen / Rückspulen | Vorspulen / Rückspulen | Bild↓ / Bild↑ |
| diktiert ins aktive Feld (Pause/Weiter wie gewohnt); das Diktat **ersetzt** den Vorschlag | Record | Record | F10 |
| Vorbefund dieses Felds **bewusst übernehmen** (noch einmal = zurück); bei heutigem Text: 2× = verwerfen | F3 | **Play** | F3 (ab v3.15.4) |
| Maske aus = freies Diktat wie bisher (noch einmal = wieder an) | F4 | **Command** | F4 (ab v3.15.4) |
| Befund aus den Feldern zur Kontrolle / an CAS | INS / EOL | INS / EOL | F11 / F12 |

- **Belegung je erkanntem Gerät (v3.15.4):** Das SpeechMike Ambient (PSM5000, ohne F1–F4) meldet sich wie ein
  Premium Air als „SpeechMike III“ (0911:0C1D) und wird an seiner Seriennummer „PSM5…“ erkannt. Nur dann gelten Play und
  Command; SpeechMike III/Premium bleiben bei F3/F4. Die Hilfezeile über den Feldern zeigt die Tasten des erkannten
  Geräts (ohne SpeechMike: die Tastatur). Play zählt beim Loslassen und nie als Schieberstellung. Eigene Belegung:
  `config.ini` `[MASKE]` (`UEBERNEHMEN = …`, für das Ambient `AMBIENT_UEBERNEHMEN = …`).
- **Text markieren und drüberdiktieren (v3.15.4):** Text im aktiven Feld markieren → Record → das Diktat ersetzt genau die
  Markierung; Cursor in ein Feld mit heutigem Text gesetzt → an dieser Stelle eingefügt; ohne Markierung/Cursor wie
  bisher (ein grauer Vorschlag wird durch einen bloßen Klick nicht übernommen). Steht danach Vorbefund-Text mit im Feld,
  gilt es als getippt (ohne KI — die KI bekommt nur Peters Diktat). Strg+A markiert den ganzen Feldtext.
- **Selbst löschen/korrigieren (v3.15.4):** Tippen, Markieren, Entf und die Knöpfe „✓ übernehmen“/„✕ verwerfen“ gehen auch
  in der **Pause** (gesperrt nur bei laufender Aufnahme, während der Befund entsteht und solange das Feld noch erkannt
  wird). Ganz gelöscht → das Feld ist leer und kommt nicht in den Befund; „✕ verwerfen“ holt den Vorschlag zurück.
- **Am Ambient ohne F1/F2:** „Neu“ (F1) = F9 bzw. Knopf „↺ Neu (F9)“, „Nur Text“ (F2) = Schalter oben rechts im Befund.

- **Vorbefund:** Die Brücke (ab 2.1.0) liefert den letzten fertigen Mammographie-Befund mit Datum und ACR/BI-RADS der
  Doppelbefundung. RaKScribe zerlegt ihn an den Labels und trägt ihn **grau** als Vorschlag ein („Vorbefund TT.MM.JJJJ“).
  Ein Vorschlag wird **nie still** zum heutigen Befund: INS warnt, solange ein Feld noch Vorschlag ist; ein zweites INS
  ohne Änderung baut den Befund **ohne** diese Felder.
- **„unverändert“** diktiert (oder F3) → der Vorbefund dieses Felds mit Vergleichsdatum, z. B. „Verglichen mit 05.06.2024
  beidseits unverändert …“, „Verglichen mit 05.06.2024 weiterhin keine …“ — deterministisch, ohne KI. Eine alte
  Datumsangabe im Vergleichssatz des Vorbefunds („Voruntersuchung (12.03.2022)“, „von 2022“) wird ersetzt, nie
  ergänzt (ab v3.15.3).
- Kein Vorbefund → Felder leer, im Mammographie-Feld der Normalbaustein „Mammo 1“ als Vorschlag.
- **INS** baut den Befund aus den Feldern: Titel (Screening: „Mammographie beidseits – Screening“), Labels, Ergebnis mit
  „ACR:“/„BIRADS:“; beim Screening mit BI-RADS 1/2 der Screening-Text der Praxis (BI-RADS 0/3/4/5: Hinweis, der Text mit
  Namen/Kontrollintervall bleibt in CAS). Ändert sich die Maske nach INS, schickt EOL erst nach einem neuen INS.
- **Datenschutz:** Der Vorbefund wird nur angezeigt und wörtlich eingesetzt — an die KI geht nur Peters Diktat eines
  Felds (Korrektur der Spracherkennung), ins Protokoll nur Zustände und Zählungen.
- Menü ☰ „Mammo-Maske bei Mammographie (CAS)“ schaltet sie ab. Definition: `masken.json`; Tests:
  `tests/offline/test_maske.py`, `test_maske_ablauf.py`, Windows-UI-Test Fall M. Die Web-App hat keinen CAS-Auftrag und
  damit keine Maske.

## 🔧 v3.15.4 außerdem (Peter 15.10.2026, Ordi-Probelauf)

- **Genaue Spracherkennung (chirp_3) in der EXE repariert:** Die Schlüssel für chirp_3 wurden ohne Scope angelegt — jede
  Token-Erneuerung scheiterte mit „invalid_scope“ (Ordi-Protokoll 15.10.: 18 von 18 Volltranskriptionen), RaKScribe nahm
  dann still das schwächere Live-Transkript. Jetzt mit Scope `cloud-platform` (wie alle Werkzeuge am Mac).
- **Beidseitige CAS-Leistung → beidseitiger Befund:** Ist die CAS-Leistung einer paarigen Region beidseits („bds.“,
  „beidseits“, „bilateral“), heißt die Überschrift immer „… beidseits …“ (auch wenn nur eine Seite diktiert wurde), der
  Gen-Prompt bekommt die Regel für den beidseitigen Befundtext, das Band einen Hinweis. Wirbelsäule/Becken nie.
- **Drüberdiktieren rechts nach einer Pause:** Record → Pause → in den Befund klicken bzw. Text markieren → Record
  (weiter) → INS setzt das Diktat an diese Stelle (wie seit v3.5.0 beim Start; bisher wurde die Stelle in der Pause nicht
  gelesen und INS baute einen neuen Befund bzw. ersetzte ihn bei „Nur Text“). Gilt auch im CAS-Band.
- **Häkchen im ☰-Menü weiß** statt schwarz auf dunkelblau; Schalter „Nur Text“ mit hellem Knopf und Rahmen.

## 🦴 Umschriebene Skelettbefunde ohne Widerspruch (EXE + Web, ab v3.15.5)

Peter 15.10.2026: „Fersensporn diktiert, aber ‚Normale Form des Calcaneus …‘ steht noch da.“ Ein umschriebener Befund an
EINER Stelle darf dem Normaltext der Vorlage nicht widersprechen — das gilt jetzt für alle Skelett-Vorlagen (Röntgen,
CT/MR, Prothesen, Ordi-Bausteine mit Skelett-Normaltext).

- **Katalog als Daten** (`vorlagen_vorrang.json` → `widersprueche`): 20 Befund-Kategorien (Fibroostose/Enthesiopathie/
  Sporn, Exostose, Osteophyt, Arthrose inkl. AC/ISG/Finger/Zehen/Kiefergelenk, Spondylose, Spondylarthrose,
  Osteochondrose, Unkovertebralarthrose, Baastrup, DISH, Verkalkung, Chondrokalzinose, Os accessorium/Sesambein,
  Enostose, Zyste, alte Fraktur, Fehlstellung, Osteopenie, Skoliose, Sklerose) mit Deskriptoren, 21 Normalsatz-Merkmale
  (Form, Kontur, Kortikalis, Gelenkspalt, „keine Verkalkungen“ …) und 25 Strukturgruppen (Trochanter ≠ Hüftgelenk,
  ISG ≠ Hüftgelenke, Unkovertebral- ≠ Facettengelenke …). Verneinte Befunde („kein Fersensporn“) zählen nicht.
- **Vor der KI:** Widerspricht ein Satz der Vorlage einem diktierten Befund, bekommt der Gen-Prompt den Block
  `<widersprueche>` mit genau diesen Sätzen (an der Stelle `{examples}`, EXE = Web); dazu die Konflikt-Regel im Prompt
  (Marker `2026-10-15-v3155-umschriebene-befunde`) und eine Zeile im Web-Prüfer (Call 2).
- **Nach der KI (deterministisch, EXE = Web):** übrig gebliebene widersprechende Normalsätze → „Im Übrigen …“ (nur der
  betroffene Satz, der übrige Normaltext bleibt Zeichen für Zeichen), der Befundsatz steht davor; fehlt der Befund im
  Befundtext, kommt der diktierte Teilsatz dorthin; das Ergebnis nennt den Befund (mit Seite) statt „Regelrechte
  Darstellung …“. Ohne diktierten Befund bleibt alles unverändert.
- **Tests:** `tests/offline/widerspruch_matrix_test.py` baut die Matrix aller Skelett-Vorlagen × Kategorien
  (98 Vorlagen/Bausteine, 1062 Kombinationen, 0 Fehler, 200 Gegenproben unverändert, EXE = Web) →
  [`docs/widerspruch_matrix.md`](docs/widerspruch_matrix.md); Fixtures `widerspruch` in `befund_regeln_fixtures.json`
  (PY + TS); Live-Check mit Gemini `tools/verify_widerspruch.py` (EXE 8/8, Web 8/8).

---
*(c) 2025-2026 Dr. Peter Kalmar - Modernes Reporting für die radiologische Praxis.*
