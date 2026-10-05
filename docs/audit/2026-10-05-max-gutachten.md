# Code-Gutachten RaKScribe26 — Stand 05.10.2026 (v3.2.2, Commit b85499e)

Fable-Burn-Gutachten (Fable 5.1, max). Reines Lesen und Messen — am Code wurde nichts geändert.
Leicht-Spur: keine Browser-, Gemini- oder Windows-Läufe; alle Belege stammen aus dem Quelltext und aus
kurzen Offline-Tests auf diesem Mac. Testdiktate im Text sind synthetische Fixtures, keine Patientendaten.

## Kurzurteil

1. Der Kern ist gesund: die geteilten Regelmodule (Regionen-Trenner, Nummerierung, Fehlhör-Liste, Normalbefund-Bypass) laufen in Python **und** TypeScript gegen dieselben Fixtures, alle vier Offline-Gates sind heute grün (58 + 37 + 31 Fixtures, alle Normalbefund-Gates), die Typprüfung ist sauber.
2. Die beiden Hauptdateien sind Monolithen: `RaKScribe.py` (1991 Zeilen, eine Klasse mit 848 Zeilen, 51 Anweisungen mit Seiteneffekt beim Import) und `App.tsx` (2361 Zeilen, eine Komponente mit 1837 Zeilen). Tests kommen nur per AST-/String-Extraktion an die Funktionen heran.
3. **Größtes Risiko (EXE):** keine Zustandssperre während „Befund wird erstellt“ — F10/F9 startet eine zweite Aufnahme in den laufenden Job hinein — und die automatische Strg+V-Einfügung läuft auch dann, wenn das Kopieren in die Zwischenablage still fehlschlug (alter Zwischenablage-Inhalt landet im RIS).
4. **Zweitgrößtes Risiko (beide Apps):** die Vorlagen-Erkennung existiert zweimal (275 Zeilen Python, 304 Zeilen TypeScript) ohne Paritätstest. Gemessen über 832 Testdiktate: 6 Abweichungen (Web ordnet „Ultraschall-gezielte Blockade“ der allgemeinen Sono-Vorlage zu), und 22 von 142 Vorlagen sind über kein Diktat erreichbar, nicht einmal über ihren eigenen Namen.
5. Zählung: **4 × P1, 15 × P2, 8 × P3.** Nichts davon ist ein Notfall für heute; P1-1 und P1-2 sollten aber vor dem nächsten Praxis-Update rein.

## Was geprüft wurde

| Prüfung | Ergebnis |
|---|---|
| `befund_regeln_test.py` (PY + TS, 58 Fixtures) | grün |
| `misheard_test.py` (PY + TS, 37 Fälle, Prompt-Block identisch) | grün |
| `normal_bypass_test.py` (PY + TS, 31 Fälle, 140/142 Normal-Ergebnisse) | grün |
| `test_normalbefunde.py` (Taught-Coverage, 53 Detector-Fälle EXE = Web, Bypass, Titelzeilen) | grün |
| `tsc -p tsconfig.app.json --noEmit` | 0 Fehler (1,3 s) |
| `eslint src` | **87 Fehler** (siehe P2-15) |
| Parität `detect_template` (EXE) ↔ `detectTemplate` (Web), 832 Diktate | **6 Abweichungen**, 22 unerreichbare Vorlagen (P1-3, P2-3) |
| Bypass-Whitelist (236 Wörter aus Vorlagennamen) gegen Implantat-/Pathologie-Wörter | unauffällig: „Knie rechts Prothese unauffällig“ geht korrekt zum LLM, „Hüftprothese rechts unauffällig“ korrekt zur Prothesen-Vorlage |
| Geheimnisse in getrackten Dateien und in der gesamten Git-Historie (PEM-/API-Key-Muster) | keine Treffer (die zwei Treffer sind ein Regex-Literal und der Dummy-Schlüssel des UI-Tests) |
| Phrasenlisten | `CHIRP_PHRASES` EXE = Web (68); `MEDICAL_PHRASES` EXE 292, Web 692 mit 123 Duplikaten |

Nicht geprüft (Leicht-Spur): Browser-Verhalten (iPhone, Clipboard, Audio), Gemini-Ketten, Windows-EXE-Lauf. Offene Punkte dazu am Ende.

---

## P1 — drohende Bugs

### P1-1 EXE: Strg+V wird auch ausgelöst, wenn das Kopieren fehlschlug

- **Wo:** `source_code/RaKScribe.py:1963-1982` (`copy_formatted_report`, endet mit `except: pass`) und `:1828-1833` (`copy_formatted_report()` → 500 ms später `keyboard.press_and_release('ctrl+v')`).
- **Beleg:** `win32clipboard.OpenClipboard()` schlägt unter Windows regelmäßig fehl, wenn ein anderes Programm die Zwischenablage gerade hält (RIS, Teams, Zwischenablage-Manager). Die Ausnahme wird verschluckt, die Funktion gibt nichts zurück, der Aufrufer prüft nichts und drückt trotzdem Strg+V.
- **Folge:** Der vorherige Zwischenablage-Inhalt — im Praxisalltag der letzte Befund — wird in das aktive RIS-Feld eingefügt. Status zeigt „Kopiert & eingefügt“ nicht, aber der Arzt sieht das Einfügen und hält es für den neuen Befund.
- **Vorschlag:** `copy_formatted_report()` gibt `True/False` zurück; `OpenClipboard` bis zu fünfmal mit 100 ms Pause versuchen; bei Fehlschlag Status ERROR + Hinweisfenster, **kein** Strg+V. Zusätzlich nach dem Setzen `GetClipboardData` gegenlesen.
- **Aufwand:** S. **Risiko des Umbaus:** gering. **Test:** Unit-Test mit gemocktem `win32clipboard` (erster Versuch wirft → Retry greift; dauerhaft wirft → kein Paste, Status ERROR).

### P1-2 EXE: F10/F9 während der Verarbeitung — zwei Jobs teilen sich denselben Zustand

- **Wo:** `source_code/RaKScribe.py:1585-1614` (`toggle_recording` prüft nur `is_recording` und `keys_ready()`, nicht `_status_raw == "PROCESSING"`), `:1572-1583` (`reset_dictation`), `:1984-1986` (globale Hotkeys), Worker `:1646-1690`.
- **Beleg:** Während „Befund wird erstellt…“ ist nur der Button deaktiviert; der globale F10-Hotkey ruft `toggle_recording` weiter auf. Der Start-Zweig setzt `final_transcript = ""` und `recorded_audio_chunks_all = []`. Der noch laufende Worker liest danach die geleerte Liste (`np.concatenate([])` wirft, wird in `:1673` verschluckt), rettet sich den Text aus der Textbox (= Zwischenstand der **neuen** Aufnahme), ruft `process_dictation`, setzt Status READY und Button „Aufnahme Starten“, obwohl das Mikrofon läuft, und fügt per Strg+V ein. Das Web hat den Schutz (`App.tsx:2112-2118`, `statusRef`).
- **Folge:** Vermischte oder leere Befunde, Oberfläche zeigt „Bereit“ bei laufender Aufnahme; Mehrfachdruck auf F10 bei Ungeduld ist der Normalfall in der Praxis.
- **Vorschlag:** Guard in `toggle_recording` und `reset_dictation` (`PROCESSING` → ignorieren bzw. Abbruch-Flag setzen); Generationszähler `self._job_id`, den der Worker beim Start merkt und vor jedem UI-Schreibzugriff und vor dem Einfügen vergleicht. Deckt auch P2-5 mit ab.
- **Aufwand:** S. **Risiko:** gering. **Test:** Zustandsautomat als reine Funktion herausziehen (Status × Ereignis → Aktion) und mit Unit-Tests belegen; EXE-UI-Test Fall B um „F10 während PROCESSING“ erweitern (Selbsttest-Modus kann PROCESSING simulieren).

### P1-3 Web: Vorlagen-Erkennung weicht von der EXE ab — „Ultraschall-gezielte Blockade“ bekommt die falsche Vorlage

- **Wo:** `web_app/src/App.tsx:852-925` (Sono-Zweig ohne `blockade`/`injektion`-Regel), EXE hat sie in `source_code/RaKScribe.py:678-679`; umgekehrt kennt nur das Web `ganzaufnahme_der_wirbelsäule_a-p` (`App.tsx:825-827`), die EXE nicht.
- **Beleg (gemessen):** 832 Testdiktate (alle Fixtures, alle 142 Vorlagennamen, Diktate aus den Verify-Skripten) durch beide Erkenner: 6 Abweichungen.
  - „Ultraschall-gezielte Blockade [rechts] unauffällig“, „ultraschall gezielte blockade o.B.“ → EXE `ultraschall_gezielte_blockade`, **Web `sonografie_allgemein`**.
  - „Ganzaufnahme der Wirbelsäule a.-p. [rechts] unauffällig“ → **EXE `wirbelsäule_gesamt`**, Web `ganzaufnahme_der_wirbelsäule_a-p`.
- **Folge:** Im Web entsteht für eine Blockade der generische Sono-Standardtext statt des Blockade-Textes (Skill-Regel 3ae, erst am 05.10. eingebaut); in der EXE bekommt die Ganzaufnahme den Gesamt-Wirbelsäulen-Text statt der eigenen Vorlage. Der bestehende Detector-Test (53 Fälle) enthält beide Diktate nicht.
- **Vorschlag:** Kurzfristig beide Regeln angleichen (Blockade-Regel in den Web-Sono-Zweig, Ganzaufnahme-Regel in die EXE) und den Paritätstest als Fixture-Datei (`detect_fixtures.json`: alle 142 Vorlagennamen + Fixtures) in `test_normalbefunde.py` aufnehmen. Mittelfristig P2-2/P2-3: Erkennung als Regeltabelle (Daten) mit zwei dünnen Interpretern.
- **Aufwand:** S (Angleichen + Fixture), M (Regeltabelle). **Risiko:** gering, Verhalten ändert sich nur für die 6 Fälle.

### P1-4 EXE: Streaming-Fehler bricht die Aufnahme ab und verwirft das Diktat

- **Wo:** `source_code/RaKScribe.py:1749-1773` (`record`: Audio-Stream und Google-Antwortschleife im selben `with`-Block) und `:1693-1705` (`cancel_recording_due_to_error`).
- **Beleg:** Jede Ausnahme in der Antwortschleife (`for response in responses`) — Netzwerk-Hänger, gRPC-Abbruch, und spätestens das 5-Minuten-Limit eines Google-Streaming-Requests — verlässt den `with`-Block, schließt den Mikrofon-Stream und ruft `cancel_recording_due_to_error`. Die bis dahin aufgenommenen Daten liegen in `recorded_audio_chunks_all`, werden aber nie an chirp_3 geschickt. Dabei ist chirp_3 der eigentliche Textlieferant (`:1652-1675`); das Streaming dient laut Kommentar nur der Live-Anzeige.
- **Folge:** Ein Wackler in der Verbindung oder ein langes Diktat kostet das komplette Diktat; der Arzt muss neu diktieren.
- **Vorschlag:** Aufnahme (sounddevice) und Streaming-Anzeige trennen: eigener Capture-Thread, der nur sammelt; Streaming in eigenem Thread, dessen Fehler nur geloggt werden („Live-Anzeige ausgefallen“); beim Stopp läuft chirp_3 immer über den gesammelten Puffer. Für > 5 min das Streaming alle 4 min neu aufsetzen.
- **Aufwand:** M. **Risiko:** mittel (Thread-Struktur ändert sich; mit Capture-Mock testbar). **Test:** Unit-Test mit simuliertem Streaming-Fehler → Puffer vollständig, chirp_3-Worker wird aufgerufen.

---

## P2 — Wartbarkeit und Robustheit

### P2-1 Monolithen ohne importierbare Schnittstellen

- **Wo:** `source_code/RaKScribe.py` 1991 Zeilen: Klasse `RaKScribeApp` 848 Zeilen (`:1139-1986`), `detect_template` 275 Zeilen (`:535-809`), `toggle_recording` 107, `create_widgets` 104, `_befund_fuer_segment` 103; 51 Anweisungen auf Modulebene mit Seiteneffekt beim Import (Config lesen `:152-193`, Schlüssel laden `:276`, `SpeechClient` bauen `:353`, `messagebox` `:181/:383`, Vorlagen `:488`). `web_app/src/App.tsx` 2361 Zeilen: `App()` 1837 Zeilen (`:525-2361`), `detectTemplate` 304 Zeilen **innerhalb** der Komponente (`:766-1069`, wird bei jedem Render neu erzeugt).
- **Beleg:** Alle Tests, die an echte Funktionen wollen, extrahieren sie aus dem Quelltext: `prod_pipeline.py:33-44` (AST-Exec), `test_normalbefunde.py` (AST), `web_app/detect_test.mjs:6-10` (String-Suche + `new Function`). Importieren kann man `RaKScribe.py` nicht, ohne Tk, Windows-Module und Google-Clients zu starten.
- **Vorschlag:** Modul-Schnitt wie im Umbauplan (config / keys / detect / stt / gemini / pipeline / ui). Reine Funktionen zuerst herausziehen, UI zuletzt.
- **Aufwand:** L (in kleinen Schritten S–M). **Risiko:** gering, wenn jeder Schritt die bestehenden Gates und den Windows-UI-Test durchläuft.

### P2-2 Doppelte Logik EXE ↔ Web ohne Sync-Test

- **Wo:** Vorlagen-Erkennung (P1-3); `MEDICAL_PHRASES` `RaKScribe.py:95-145` (292) vs. `App.tsx:70-251` (692, davon 123 Duplikate — der Block „Allgemein radiologische Begriffe … Mamma“ steht wörtlich zweimal, `:138-175` und `:213-250`); `CHIRP_PHRASES` `:944-1013` vs. `:1190-1259` (heute identisch, aber ungeprüft); `derive_untersuchungs_titel` `:497-532` vs. `deriveUntersuchungsTitel` `:263-284` (plus Klon in `titel_fixtures.py`); `_stitch_overlaps` `:1068-1077` vs. `stitchOverlaps` `:1283-1293`; `_report_complete` `:1016-1023` vs. `isCompleteReport` `:59-65`; WAV-Encoder zweimal im Web (`:335-380` und `:1330-1345`).
- **Beleg:** Nur `SYS_MSG` und die drei Regelmodule haben Sync-Tests (`befund_regeln_test.py:70-86`). Die Phrasenliste ist bereits auseinandergelaufen.
- **Vorschlag:** Listen als Daten im Repo-Root (`phrases.json` mit `medical` und `chirp`), beide Apps importieren sie wie heute `misheard_words.json` (`App.tsx:8`); für jede doppelte Funktion ein gemeinsames Fixture (Muster: `befund_regeln_fixtures.json`).
- **Aufwand:** M. **Risiko:** gering.

### P2-3 22 von 142 Vorlagen sind unerreichbar

- **Wo:** `source_code/RaKScribe.py:751-807` (Mapping + Key-Fallback), `web_app/src/App.tsx:1016-1066`.
- **Beleg (gemessen):** Für jede Vorlage wurde „<display_name> unauffällig“, „<display_name> rechts unauffällig“ und der Key ohne Unterstriche diktiert. 22 Keys erreicht keiner der beiden Erkenner: `axialaufnahme_des_ellbogens`, `beckenübersicht_mit_beidseitiger_hüftprothese`, `funktionsaufnahmen_der_halswirbelsäule`, `funktionsaufnahmen_der_lendenwirbelsäule`, `mittelfuß_in_2_ebenen` (das Stichwort „mittelfuß“ liegt unter `fuß_in_2_ebenen`, `:791`), `vorfuß_in_2_ebenen`, `skaphoidaufnahme` (→ `naviculareserie`), `schrägaufnahme_der_halswirbelsäule`, `schultergelenk_tangential_bizepssehnenkanal`, `schultergelenke_a-p_unter_belastung`, `sonografie_abdomen_komplett`, `sonografie_nerven` und 10 MR-Vorlagen, deren Key mit Doppelpunkt endet (`mr_der_brustwirbelsäule:` …) — der Fallback `key.replace('_', ' ')` behält den Doppelpunkt und matcht nie.
- **Folge:** Diese Vorlagen (teils Peters beigebrachte Normalbefunde) kommen nie zum Einsatz; das Diktat bekommt eine Nachbar-Vorlage.
- **Vorschlag:** Gate „jeder display_name erreicht seinen Key“ als Test; Erkennungsregeln datengetrieben (Reihenfolge, Stichwörter, Ausschlüsse je Key in einer JSON-Tabelle, Interpreter in PY und TS je ~40 Zeilen). Welche der 22 Vorlagen wirklich erreichbar sein sollen, entscheidet Peter — Erkennungsregeln dafür sind neues Verhalten.
- **Aufwand:** M. **Risiko:** mittel (jede neue Regel kann bestehende Zuordnungen verschieben → nur mit dem Paritäts-Fixture aus P1-3).

### P2-4 EXE: `config.ini`-Verarbeitung ist spröde, Werte werden nicht benutzt

- **Wo:** `source_code/RaKScribe.py:152-193`, `:359-363` (Endpoint fest verdrahtet).
- **Beleg:** `config['SETTINGS']['LLM_MODEL']` ohne Default → fehlt die Zeile, gilt die Datei als „fehlerhaft“ und die EXE beendet sich (`:180-184`), obwohl `LLM_MODEL` für Gemini gar nicht benutzt wird. `int(CHUNK_DURATION)` (`:162`) und `configparser.Error` (z. B. fehlender `[SETTINGS]`-Kopf, doppelte Schlüssel) stehen nicht im `except` → Absturz beim Start, bei `--noconsole` nur der PyInstaller-Dialog. `CHUNK_DURATION`, `STT_ENGINE` (`:162-164`) werden nirgends verwendet; `GOOGLE_JSON_FILENAME` ist Legacy.
- **Vorschlag:** Alle Werte per `.get()` mit Default; nur `configparser.Error` fatal (mit Klartext-Dialog); ungenutzte Schlüssel aus Datei und Code entfernen; Dokumentation (`readme.md:94-111`, `install.md:41-63`) auf den tatsächlichen Stand bringen (dort steht noch `gemini-1.5-flash`).
- **Aufwand:** S. **Risiko:** gering.

### P2-5 EXE: Wettlauf zwischen Streaming-Anzeige und chirp_3-Endtext

- **Wo:** `source_code/RaKScribe.py:1646-1650` (`join(timeout=6.0)`), `:1725-1733` (`update_interim_text` hängt an `final_transcript` an), `:1766` (Aufruf per `after` aus dem Record-Thread), `:1664-1670` (chirp_3 setzt `final_transcript`).
- **Beleg:** Läuft die Google-Antwortschleife länger als 6 s nach dem Stopp (letzte `is_final`-Antworten kommen verzögert), feuert `update_interim_text` nach dem chirp_3-Ergebnis: `final_transcript += transcript` hängt Streaming-Text an den fertigen Text an (Diktat doppelt → doppelte Regionen und Ergebnis-Punkte) oder ein Zwischenergebnis überschreibt die Anzeige.
- **Vorschlag:** Streaming-Text in eigener Variable führen, nie in `final_transcript` mischen; Callbacks nach dem Stopp über den Generationszähler aus P1-2 verwerfen.
- **Aufwand:** S. **Risiko:** gering.

### P2-6 EXE: Mehr-Regionen-Befund scheitert stumm

- **Wo:** `source_code/RaKScribe.py:1806-1827`.
- **Beleg:** Fällt bei zwei Regionen ein Segment durch `_report_complete`, wird `report = ""`; der Code setzt Status ERROR, zeigt aber keine Meldung, und die Befund-Box behält „... Befund wird geladen ...“. Der Ein-Regionen-Pfad wirft dagegen eine Ausnahme mit Dialog (`:1943-1944`).
- **Vorschlag:** Fehlertext in die Box und Dialog wie im Ein-Regionen-Pfad; fertige Segmente anzeigen und das fehlende markieren.
- **Aufwand:** S. **Risiko:** gering.

### P2-7 Web: Keine Abbruch-/Generationslogik für laufende Pipelines

- **Wo:** `web_app/src/App.tsx:2083-2098` (`handleReset`), `:727-738` (Drag&Drop ohne Statusprüfung), `:1882-2026` (`stopRecording`), `:2035-2080` (`handleAudioUpload`).
- **Beleg:** „Neu“/F9 setzt Status auf `ready`, die laufende Kette (bis zu vier Google-Aufrufe à 120 s Timeout × 3 Versuche) schreibt später `setStructuredReport` und kopiert in die Zwischenablage. Eine während der Verarbeitung fallengelassene Audiodatei startet eine zweite Kette parallel; beide schreiben `transcript`/`structuredReport`. Es gibt keinen Abbrechen-Knopf.
- **Vorschlag:** `runIdRef` + `AbortController` pro Lauf; jede `set…`-Schreibung und das Kopieren prüfen `runId`; Reset bricht ab; Drop während `processing` ignorieren oder nachfragen.
- **Aufwand:** M. **Risiko:** gering.

### P2-8 Web: Performance- und Speicherfallen auf dem iPhone

- **Wo:** `web_app/src/App.tsx:1850-1863` (ScriptProcessorNode + `setMicLevel` pro Puffer), `:1858` (alle Float32-Chunks in nativer Rate), `:1764-1768`/`:1907-1911` (neuer AudioContext je 6-s-Chunk), `:1966-1977` (Kopien beim Stopp), `:1297` (Base64-String), `:1314-1324` (Volltranskription > 59 s).
- **Beleg:** (a) `setMicLevel` löst ~10 Re-Renders/s der 1837-Zeilen-Komponente aus — auf demselben Hauptthread, auf dem der (veraltete) `ScriptProcessorNode` das Audio liefert → Aussetzer auf schwachen Geräten. (b) Bei 48 kHz entstehen 192 KB/s; ein 5-Minuten-Diktat hält ~57 MB Rohdaten, beim Stopp kommen Merge-Kopie, Downsample, AudioBuffer, WAV und Base64-String dazu (~230 MB Spitze) — iOS Safari lädt den Tab dann neu, das Diktat ist weg. (c) Der Pfad > 59 s dekodiert das selbst erzeugte 16-kHz-WAV per `decodeAudioData` in einem AudioContext mit `sampleRate: 16000` und nimmt danach 16 kHz an, ohne `audioBuf.sampleRate` zu prüfen; ignoriert ein Gerät die Option, wird dreifach verlangsamtes Audio segmentiert (nur über Browser-Test verifizierbar, s. offene Punkte). (d) Kein Wake Lock: Bildschirmsperre beendet die Aufnahme. (e) Mikrofonberechtigung wird sofort beim Laden angefragt (`:678-679`), noch vor dem Schlüssel.
- **Vorschlag:** Im Audio-Callback sofort auf 16 kHz Int16 reduzieren (6× weniger Speicher, ein zusammenhängender Puffer); Pegel über `ref` + `requestAnimationFrame` statt State; Chunk- und Voll-WAV durch Byte-Slicing aus dem Int16-Puffer bauen (kein AudioContext, kein `decodeAudioData`); `navigator.wakeLock.request('screen')` während der Aufnahme; AudioWorklet optional später.
- **Aufwand:** M. **Risiko:** mittel (Audio-Pfad; mit `test-audio*.ogg`-Dateien aus `public/` offline gegen die alte WAV-Ausgabe vergleichbar).

### P2-9 Web: Jede Aufnahme beginnt mit einem Gemini-Testaufruf vor dem Mikrofon

- **Wo:** `web_app/src/App.tsx:1805-1816` (`testGeminiAPI`), Mikrofon erst `:1832`.
- **Beleg:** Nach F10 vergehen bei langsamer Verbindung ein bis zwei Sekunden, bevor `getUserMedia` läuft; die ersten Silben fehlen. Dazu ein kostenpflichtiger Aufruf pro Aufnahme.
- **Vorschlag:** Schlüssel einmal beim Laden prüfen (oder im Hintergrund nach dem Start der Aufnahme), Mikrofon sofort öffnen.
- **Aufwand:** S. **Risiko:** gering.

### P2-10 Web: Whisper-Fallback maskiert echte STT-Fehler

- **Wo:** `web_app/src/App.tsx:1356-1363` (`transcribeAudio`), `:1397-1414`, `:2044-2051`.
- **Beleg:** Jeder Google-Fehler (401/403/429/Quota) landet im Fallback auf `http://localhost:8765`. Auf GitHub Pages (https) ist das Mixed Content und auf dem iPhone gibt es keinen Server; der Nutzer sieht „Failed to fetch“ statt der eigentlichen Ursache. Die Google-Meldung steht nur in der Konsole.
- **Vorschlag:** Fallback nur, wenn `location.hostname === 'localhost'` oder ein localStorage-Flag gesetzt ist; sonst den Google-Fehler durchreichen.
- **Aufwand:** S. **Risiko:** gering.

### P2-11 Schlüssel-Hygiene rund um den Web-Build

- **Wo:** `web_app/public/stt-key.txt` (Service-Account-Private-Key, 2,3 KB), `web_app/public/vertex-key.txt`; `web_app/dist/stt-key.txt` (vom Build am 05.10. kopiert); `.github/workflows/deploy.yml:48-53`; `web_app/src/App.tsx:470-494` (localStorage).
- **Beleg:** Beide Dateien werden seit v3.0 nicht mehr gelesen (`App.tsx:650`), liegen aber im `public/`-Ordner und wandern bei jedem `vite build` nach `dist/`. Gitignore schützt sie (geprüft: nichts im Repo, nichts in der Historie), aber `vite preview`, ein Upload des dist-Ordners oder ein Wechsel des Deploy-Wegs würde den Private Key veröffentlichen. Der Deploy-Guard löscht die falschen Namen (`*.b64` statt `*.txt`). Im Browser liegen Service-Account-Key und API-Key im Klartext im localStorage einer öffentlichen Origin — jedes XSS oder jeder Zugriff auf den Praxis-Browser liest sie (bewusste Designentscheidung, trotzdem festhalten).
- **Vorschlag:** Dateien aus `public/` entfernen; Deploy-Guard umdrehen: Build abbrechen, wenn `dist/` eine Datei mit `private_key`/`AQ.` enthält; im GCP den API-Key auf HTTP-Referrer `drpeterkalmar.github.io` beschränken und das Service-Konto auf Speech-Rechte begrenzen; Rotationsplan über den vorhandenen `KEY_VERSION`-Mechanismus.
- **Aufwand:** S. **Risiko:** gering.

### P2-12 Build, Deploy, Versionierung

- **Wo:** `requirements.txt` (`ttkbootstrap`, kein `customtkinter`/`google-cloud-speech`) vs. `.github/workflows/build-exe.yml:32`; `source_code/build.bat:5-84` (ohne `--add-data` für Vorlagen/Prompt/Fehlhör-Liste, ohne `hidden-import` für `befund_regeln`/`misheard`/`normalbypass`); `build-exe.yml:60` (manueller Lauf ohne Version veröffentlicht auf das feste Tag „3.2.2“, `prerelease: false`); Versionsstring an fünf Stellen (`RaKScribe.py:1143` „3.2.2“, `:1217` Badge „v3.0“, `App.tsx:2155` „v3.2.2“, `index.html:12` „3.0“, `build-exe.yml:60`); keine CI für die Offline-Gates (`deploy.yml` baut und veröffentlicht bei jedem Push, auch bei reinen Doku-Commits).
- **Beleg:** Eine lokal mit `build.bat` gebaute EXE hat keine Vorlagen im Bundle und fällt für jedes Diktat auf `allgemein` zurück. Fixture-Regressionen fallen erst in der Praxis auf, weil nur `tsc` im Deploy läuft.
- **Vorschlag:** `test.yml` (Node 20 + Python: die vier Offline-Gates, `test_parts_join.py`, `tsc`) als Pflicht vor `deploy`; `paths-ignore: docs/**`; eine `VERSION`-Datei, aus der EXE-Titel, Web-Badge und Release-Tag lesen; `build.bat` löschen oder aus dem Workflow generieren; `requirements.txt` = Workflow-Liste; manueller Build ohne Version → Prerelease-Tag.
- **Aufwand:** S–M. **Risiko:** gering.

### P2-13 `templates.json` doppelt gepflegt

- **Wo:** `templates.json` (Root) und `web_app/src/templates.json` (109 KB, identisch; `normal_bypass_test.py:13` prüft Gleichheit).
- **Beleg:** `misheard_words.json` und `radiology_prompt.txt` importiert das Web bereits aus dem Root (`App.tsx:8`, `:12`) — die Vorlagen nicht.
- **Vorschlag:** `import templatesData from '../../templates.json'`, Kopie löschen, Test-Assert entfernen.
- **Aufwand:** S. **Risiko:** gering (Vite bündelt Root-JSON bereits).

### P2-14 Diktattexte in Logs ohne Begrenzung

- **Wo:** `source_code/RaKScribe.py:464` (Fehlhör-Korrektur), `:1687` (Rettung), `:1730` (jeder Zwischenabschnitt), `:1808` (Regionen), `:1868` (Bypass) → `rakscribe.log` ohne Rotation (`:50-65`); Web-Konsole `App.tsx:1412`, `:1422`, `:1476-1477`, `:2064`.
- **Beleg:** Diktate können Patientennamen enthalten; die Logdatei wächst unbegrenzt neben der EXE auf dem Praxis-PC.
- **Vorschlag:** Diktatinhalt nur bei `RAKSCRIBE_DEBUG=1` loggen, sonst Längen/Hashes; `RotatingFileHandler` (5 × 1 MB); Konsolenausgaben im Web auf Längen reduzieren.
- **Aufwand:** S. **Risiko:** gering.

### P2-15 Web: Lint-Gate rot und unbenutzt

- **Wo:** `npm run lint` → 87 Fehler: 39 × `no-explicit-any`, 38 × `no-useless-escape`, 6 × `react-hooks/refs` (Ref-Zuweisung im Render, `App.tsx:538-539`, `:549-550`, `:2101-2108`), 2 × `set-state-in-effect`, 1 × `immutability`, 1 × `prefer-const`.
- **Beleg:** Der Build (`tsc -b && vite build`) ruft ESLint nicht; die Regeln sind seit dem Plugin-Update (react-hooks 7) rot.
- **Vorschlag:** `useLatest`-Hook für die Ref-Spiegel (ersetzt sechs Stellen), Typen statt `any` für Gemini-/STT-Antworten, Escapes bereinigen; Lint in `test.yml`.
- **Aufwand:** M. **Risiko:** gering.

---

## P3 — Kosmetik

### P3-1 Toter Code EXE
`transcribe_full_chirp3` (`RaKScribe.py:931-941`, nie aufgerufen, enthält `len(x) if False else len(x)`), `numpy_to_wav_bytes` (`:914-922`), `import pyperclip` (`:19`), `get_close_matches` (`:25`), `engine_label` (`:1237`), `prompt_toggle`-Alias (`:1300`), `openai`-Import immer geladen (`:31`, EXE-Größe), `classify_report`/`get_few_shot_examples` (`:811-912`) nur bei `RAG_BEISPIELE > 0`, `ALLGEMEIN_FALLBACK` (`:491-495`, `App.tsx:34-38`) unerreichbar, weil `templates.json` den Key `allgemein` mit gleichem Inhalt enthält (doppelt gepflegt).

### P3-2 Toter Code Web
`systemPrompt` + localStorage-Prompt (`App.tsx:540`, `:614-662`, `:1510`): es gibt keinen Editor mehr, der Inhalt ist immer `GEN_PROMPT`; Event-Listener ohne Cleanup (`:630`, `:647`); zwei leere `download.html` (`web_app/` und `web_app/src/`); der Chunk-Block in `stopRecording` (`:1895-1936`) ist eine Kopie von `processNextAudioChunk` (`:1750-1793`); `(window as any).__praxisSttKey` als globaler Kanal statt State; `alert()` für Fehler.

### P3-3 Repo-Hygiene
85 Einträge im Root: 20 Ergebnis-Dumps (`test_results_v*.txt`, `test_diff_v*.txt`), 11 Messdaten-JSONs (`ab_*.json`, `*_results.json`, `parts_stress_raw.json`), rund 25 Einmal- und Live-Skripte (`verify_*`, `stt_ab*`, `model_ab`, `chirp_adapt_ab2`, `call0_*`, `meddictate_bench`, `migrate_normalbefunde`, `add_normal_ergebnis`, `test_diff`, `test_pipeline`). Vorschlag: `tools/` (Live-Harness), `tests/offline/` (die Gates), `docs/benchmarks/` (Ergebnisse) — Dumps aus Git.

### P3-4 UX-Kleinigkeiten
Prompt-Hinweis erscheint bei **jedem** Start, solange die alte Prompt-Datei liegt (`RaKScribe.py:1194-1197`; der Bericht verspricht „einmal“); Strg+V pastet in das fokussierte Fenster — ist das RaKScribe selbst, landet der Befund doppelt in der Box; der Web-Dialog „Schlüssel einfügen“ liegt über dem Gate, aber Esc schließt nur das Menü.

### P3-5 Versionsmarker-Vergleich lexikografisch
`befund_regeln.py:51` (`lv < bv`): Konvention „Datum zuerst, dann Buchstabe“ dokumentieren — am selben Tag gewänne „…-v4“ gegen „…-v32“.

### P3-6 STT-Token-Cache und Zeitzone
`RaKScribe.py:1062`: die naive UTC-Expiry von google-auth wird als Lokalzeit interpretiert; in Österreich harmlos (Token wird früher erneuert), westlich von UTC würde ein abgelaufener Token aus dem Cache kommen.

### P3-7 Kein Manifest, kein Service Worker
`web_app/index.html` setzt `apple-mobile-web-app-capable`, hat aber kein `manifest.webmanifest` und keinen Service Worker: kein Offline-Cache, daher auch kein Stale-Cache-Risiko beim Update. Als Home-Screen-App hat Safari einen eigenen localStorage (Schlüssel dort erneut laden). GitHub Pages cached `index.html` zehn Minuten: direkt nach einem Deploy kann ein alter Index auf gelöschte Assets zeigen (weißer Bildschirm bis zum Neuladen).

### P3-8 Teilschlüssel-Reste im localStorage
`App.tsx:622-626`, `:636`: ein `KEY_VERSION`-Bump löscht `praxis_stt_key` nur, wenn auch `vertex_api_key` gespeichert war; ein alleiniger STT-Schlüssel alter Generation bleibt liegen (wird nicht geladen, aber nicht entfernt).

---

## Umbauplan — Reihenfolge in kleinen, einzeln testbaren Schritten

Jeder Schritt: eigener Commit, Offline-Gates grün (`/usr/bin/python3 befund_regeln_test.py`, `misheard_test.py`, `normal_bypass_test.py`, `test_normalbefunde.py`, `test_parts_join.py`), `tsc` grün. Kein neues Verhalten außer den benannten Bugfixes.

**Phase 0 — Sicherheitsnetz**
1. `test.yml`: Offline-Gates + `tsc` auf jedem Push; `deploy.yml` wartet darauf und ignoriert `docs/**` (P2-12e).
2. `detect_fixtures.json` + Paritätstest EXE ↔ Web über alle 142 Vorlagennamen und Fixtures; die 6 Abweichungen als erwartete Werte **nach** Entscheidung (Blockade → Blockade-Vorlage, Ganzaufnahme → eigene Vorlage), die 22 unerreichbaren Vorlagen als dokumentierte Liste (P1-3, P2-3).

**Phase 1 — P1-Fixes EXE (jeweils S)**
3. `copy_formatted_report` mit Rückgabewert und Retry; Paste nur bei Erfolg (P1-1).
4. Zustandsschutz: PROCESSING-Guard in `toggle_recording`/`reset_dictation`, Generationszähler im Worker, Streaming-Callbacks nach Stopp verwerfen (P1-2, P2-5).
5. Mehr-Regionen-Fehler sichtbar machen (P2-6).
6. Aufnahme von Streaming trennen; chirp_3 läuft immer über den Puffer (P1-4).

**Phase 2 — Web-Korrekturen (S–M)**
7. Blockade-Regel im Web-Sono-Zweig, Ganzaufnahme-Regel in der EXE (P1-3) — Paritätstest grün.
8. `runId`/`AbortController` (P2-7); Whisper-Fallback nur lokal (P2-10); Schlüsselprüfung nicht pro Aufnahme (P2-9).
9. Audio-Pfad: Int16@16 kHz im Callback, Pegel per rAF, WAV-Slicing ohne AudioContext, `sampleRate`-Prüfung, Wake Lock (P2-8).

**Phase 3 — Modul-Schnitt EXE (Modul für Modul, UI zuletzt)**
10. `source_code/config.py` — robustes Laden mit Defaults (P2-4).
11. `source_code/keys.py` — Praxis-Key, Vertex-Key, STT-Credentials, Token-Cache.
12. `source_code/detect.py` — `detect_template`, `derive_untersuchungs_titel` (Tests importieren direkt statt AST).
13. `source_code/stt.py` — Streaming-Generator, chirp_3-Worker, Stitching.
14. `source_code/gemini.py` — Request, parts-Join, Vollständigkeit, Retry.
15. `source_code/pipeline.py` — `process_dictation` ohne UI (raw → report), UI nur über Callbacks.
16. `RaKScribe.py` = UI und Verdrahtung in `main()`, kein Seiteneffekt beim Import (P2-1).

**Phase 4 — Modul-Schnitt Web**
17. `src/detect.ts` (reine Funktion; `detect_test.mjs` importiert sie direkt).
18. `src/audio.ts` (WAV, Downsample, Capture), `src/stt.ts` (JWT, Token, chirp_3, Chunks), `src/gemini.ts` (fetchWithRetry, joinGeminiText, Call 0/1/2, Prompts), `src/pipeline.ts` (`befundAusDiktat`).
19. `App.tsx` = UI; `useLatest`-Hook für die Refs; Lint grün (P2-15).

**Phase 5 — Daten-Einheit**
20. `templates.json` nur im Root (P2-13); `phrases.json` für `MEDICAL_PHRASES`/`CHIRP_PHRASES` mit Sync-Test (P2-2); Erkennung als Regeltabelle mit Gate „jeder display_name erreicht seinen Key“ — welche der 22 Vorlagen erreichbar werden, entscheidet Peter (P2-3).

**Phase 6 — Hygiene**
21. `requirements.txt` = Workflow, `build.bat` weg, `VERSION`-Datei, Prerelease bei manuellem Build (P2-12); Schlüsseldateien aus `public/`, Deploy-Guard umdrehen (P2-11); Logging mit Rotation und ohne Diktatinhalt (P2-14); toter Code und Root-Aufräumen (P3-1 bis P3-3).

## Offene Punkte (brauchen Browser, Gemini oder Windows — hier nicht ausgeführt)

- **iPhone, Diktat > 59 s:** prüfen, ob `new AudioContext({ sampleRate: 16000 })` auf iOS Safari die Rate tatsächlich setzt (`audioBuf.sampleRate` in der Konsole ausgeben) — sonst greift P2-8c.
- **iPhone, 5-Minuten-Diktat:** Speicherverlauf (Safari Web Inspector → Timelines) und ob der Tab neu lädt.
- **Windows:** F10 während „Befund wird erstellt“ (P1-2) und Zwischenablage gesperrt (P1-1, z. B. mit einem Clipboard-Viewer, der die Zwischenablage hält) auf dem Praxis-PC nachstellen — beides lässt sich nach dem Umbau als Selbsttest-Phase in `tests/windows/exe_ui_test.py` ergänzen.
- **Gemini:** keine Änderung an Prompts in diesem Gutachten; die Live-Harnesse (`verify_*.py`, `test_all_regions.py`) bleiben die Referenz nach Phase 3/4 (Ketten dürfen sich nicht ändern — `prod_pipeline.py` liest sie weiterhin aus dem Code).
