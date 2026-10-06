# Umbau-Bericht RaKScribe26 nach dem Gutachten vom 05.10.2026

Stand 06.10.2026, Ausgangspunkt v3.2.3 (Commit `1f53068`), Ende `4338870`, alles auf `main` und gepusht.
Grundlage: `docs/audit/2026-10-05-max-gutachten.md` (Befundnummern P1-x/P2-x/P3-x) und der 24-Schritte-Auftrag.

## In Kürze (für Peter)

- **Alle 24 Schritte sind umgesetzt.** Jeder Schritt hat einen eigenen Commit mit grünen Tests, jeder Push lief
  auf GitHub grün durch, und die Web-App ist live (Titel und Badge zeigen „3.2.3“).
- **Windows-App:** Sie fügt nur noch ein, wenn das Kopieren nachweislich geklappt hat. F10 während „Befund wird
  erstellt“ wird ignoriert, F9 bricht ab. Bricht die Live-Anzeige ab, läuft die Aufnahme weiter und das Diktat geht
  nicht mehr verloren. Scheitert bei mehreren Regionen eine Region, steht das im Befund-Feld und es kommt eine
  Meldung. Das Protokoll ist auf 5 × 1 MB begrenzt und enthält keine Diktattexte mehr.
- **Web-App:** „Neu“/F9 bricht eine laufende Verarbeitung wirklich ab. Spracherkennungsfehler kommen als echte
  Google-Meldung an statt „Failed to fetch“. Das Mikrofon startet ohne Verzögerung. Beim Diktieren braucht die App
  rund sechsmal weniger Speicher, und der Bildschirm bleibt während der Aufnahme an.
- **Befundtexte, Prompts, Vorlagen, Fehlhör-Liste und Regeln sind inhaltlich unverändert.** Die Prompts sind gegen
  eine Sicherungskopie von vor dem Umbau zeichengleich geprüft.
- **Noch offen, nur von dir prüfbar:** der Windows-Test mit dem nächsten EXE-Build (siehe „Offene Punkte“) und die
  Prüfungen auf dem iPhone.

## Was v3.2.3 (heute früh) schon erledigt hatte

Den Commit `1f53068` von 11:19 Uhr gab es beim Schreiben des Auftrags noch nicht. Er hatte P1-1 (Zwischenablage),
P1-2/P2-5 (F10/F9, Lauf-Nummer), P1-3 (Blockade/Ganzaufnahme über `vorlagen_vorrang.json`), die **22 unerreichbaren
Vorlagen** (seitdem 142/142 erreichbar) und den umgedrehten Deploy-Schutz (P2-11) schon behoben. Diese Schritte habe
ich deshalb auf das umgestellt, was noch fehlte: Module, Tests und die Restfälle (Details in der Tabelle).

## Je Schritt: Commit, Tests

Alle Offline-Gates laufen in CI (`.github/workflows/test.yml`, Node 24 + Python 3.12). Lokal liefen sie nach jedem
Schritt mit `/usr/bin/python3` (3.9) und Node 24. Ab Schritt 24 liegen sie in `tests/offline/`.

| # | Commit | Inhalt | Tests |
|---|---|---|---|
| 1 | `1f61e30` | `test.yml` mit allen Offline-Gates; `deploy.yml` startet erst nach grünen Tests (workflow_run, baut den getesteten Commit); Doku-Commits lösen keinen Deploy aus | YAML geprüft, CI-Lauf grün, Deploy danach grün |
| 2 | `678f427` | `detect_fixtures.json` (663 Diktate, später 670) + TEIL 2c PARITÄT in `test_normalbefunde.py`; Liste `unerreichbar` (leer seit v3.2.3) mit Gate | EXE = Web = Erwartung 663/663; Gegenprobe mit verfälschtem Erwartungswert schlägt an |
| 3 | `61b38fc` | `clipboard_win.py` (`clipboard_set(md_text) -> bool`, 5 Versuche à 100 ms, Gegenlesen, ohne Windows importierbar); auch der Knopf „Befund kopieren“ meldet einen Fehlschlag | `tests/offline/test_clipboard.py` (Mock: Retry, dauerhaft belegt, Gegenlesen falsch, CF_HTML-Offsets, Verdrahtung) |
| 4 | `a3a0a21` | `jobstate.py` (Zustände READY/RECORDING/PROCESSING/ERROR/LOCKED, Ereignisse mit Generationsnummer); Streaming-Text nur noch in `stream_transcript`; Fall D im Windows-UI-Test (`simulate_processing`) | `test_jobstate.py`, neuer `test_exe_ablauf.py`: echter EXE-Ablauf mit Attrappen (normal, F10/F9 während der Verarbeitung, verspätetes Streaming, Zwischenablage gesperrt, chirp_3-Ausfall) |
| 5 | `59ed14a` | Mehr-Regionen: fertige Regionen bleiben sichtbar, die fehlende steht als „Befund für Region X konnte nicht erstellt werden — bitte erneut diktieren“ im Feld, Dialog, kein Strg+V | `test_regionen.py` + Ablauftest Fall 6 |
| 6 | `fc167bf` | `aufnahme.py`: Capture-Thread und Streaming-Thread getrennt; Streaming-Fehler → „Aufnahme läuft · Live-Anzeige ausgefallen“; Neustart des Streams nach 240 s | `test_capture.py` (Stub-Mikrofon, Streaming wirft nach 2 Antworten → Puffer vollständig, Neustart, Mikrofonfehler) + Ablauftest Fall 7 (chirp_3 bekommt alle Samples) |
| 7 | `de4da50` | Web: Blockade/Injektion im Sono-Zweig; EXE: Ganzaufnahme-Regel vor `wirbelsäule_gesamt` — betraf noch längere Diktate hinter den Vorrang-Regeln | 7 neue Paritätsfälle (vorher abweichend, jetzt EXE = Web) |
| 8 | `583500d` | Web: `lauf.ts` (Lauf-Nummer + AbortController, „Neu“ bricht ab, Drop/Upload während Verarbeitung ignoriert), `net.ts` (Abbruch von außen), `stt.ts` (Whisper nur auf localhost oder mit `localStorage.whisper_fallback = '1'`), Schlüsselprüfung einmal nach dem Laden | `web_app/pipeline_test.mjs` (gemocktes fetch: abgebrochener Lauf schreibt nichts, Google-403 kommt an, kein localhost-Aufruf auf Pages) |
| 9 | `4388a55` | Web: `audio.ts`: 16 kHz Int16 schon im Callback, ein wachsender Puffer, WAV per Ausschnitt; chirp_3 > 59 s ohne AudioContext; Pegel per requestAnimationFrame; Wake Lock | `web_app/audio_test.mjs`: Sinus 440 Hz 48 kHz → n/3, WAV-Header, **Voll-WAV und `sliceWav` Byte für Byte gleich dem alten Weg** (alter Encoder als Referenz im Test), 44,1/96/22,05 kHz |
| 10 | `072db9d` | `config.py`: Standardwerte, nur Syntaxfehler fatal (Klartext-Dialog); CHUNK_DURATION/STT_ENGINE entfernt; readme/install/config.ini auf echten Stand | `test_config.py` |
| 11 | `0e0b5e5` | `keys.py`; Token-Ablauf als UTC (P3-6), Schlüsselwechsel leert den Token-Cache | `test_keys.py` (Tempdir, Altdateien ignoriert, UTF-16/BOM, 3 Zeitzonen) |
| 12 | `0c598f1` | `detect.py`; Tests, prod_pipeline und Harness importieren direkt (kein AST-Extrakt, kein Titel-Klon) | Paritäts-Fixture + TEIL 4b grün |
| 13 | `4f36621` | `stt.py`; `sync_fixtures.json` (Stitch, EXE = Web) | `test_stt.py` (Segmente 50/50/28 s ab 0/46/92 s, Request-Inhalt), `sync_test.mjs` |
| 14 | `9181a31` | `gemini.py` (`generate`, parts-Join, Vollständigkeit, 3 Versuche, 401-Abbruch) | `test_parts_join.py` 28/28, `test_gemini.py` |
| 15 | `2cbffb4` | `pipeline.py` `befund_aus_diktat(diktat, ctx)`; EXE und `prod_pipeline.exe_kette` rufen dieselbe Funktion | `test_pipeline_exe.py`: 18 Bypass-Fälle = `prod_pipeline.bypass_report`, 12 LLM-Fälle mit zeichengleichem Gen-Prompt |
| 16 | `48f1e37` | `RaKScribe.py` = Oberfläche + `main()`, Start in `init_runtime()`, Import ohne Seiteneffekte; alle Module als `--hidden-import` | `test_import.py` (Kopie im leeren Ordner: Import schreibt nichts; Prüfung der hidden-imports) |
| 17 | `b711bb1` | Web `detect.ts` (`detectTemplate`, `deriveUntersuchungsTitel`); `detect_test.mjs` importiert direkt | Parität grün; Titel-Fixtures jetzt auch gegen die Web-Funktion |
| 18 | `ab84a40` | Web `gemini.ts` (Call 0/1/2, `validationPrompt` als Export), `pipeline.ts`; prod_pipeline/call0_prompt lesen die Prompts dort | **Prompt-Snapshots von vor dem Umbau** (`tests/offline/snapshots/`) in TS und Python gleich; Web = EXE für 23 Normalbefund-Diktate |
| 19 | `9f57cbe` | `useLatest`, Typen statt `any`, Startwerte per useState-Initialisierer, Listener-Cleanup, Prompt immer aus der Datei | `npx eslint src --max-warnings=0` → 0 (vorher 87), in CI |
| 20 | `62b45dd` | eine `templates.json`; `phrases.json` (`chirp`, `medical_exe`, `medical_web`); `sync_fixtures.json` + report_complete | Sync-Checks in `befund_regeln_test.py`; Phrasen in den Requests (pipeline_test) |
| 21 | `5b95837` | `VERSION` (3.2.3), `requirements.txt` mit den Versionen des v3.2.3-Builds, `build.bat` gelöscht, Test-Builds als Vorabversion `test-<Lauf>` | `test_version_sync.py`; live: Seitentitel „RaKScribe 3.2.3“, Badge v3.2.3 |
| 22 | `f7390c8` | Deploy-Schutz erkennt jetzt auch PEM-Dateien mit echten Zeilenumbrüchen; lokal `web_app/dist/` gelöscht | `test_deploy_guard.py` (Schritt wörtlich aus deploy.yml gegen Dummy-Bundles); Live-Bundle gegengeprüft: sauber |
| 23 | `c1c7e7b` | `protokoll.py`: RotatingFileHandler 5 × 1 MB, Diktatinhalt nur mit `RAKSCRIBE_DEBUG=1`; Web-Konsole nur Längen | `test_logging.py` (kein Diktattext ohne Debug, Rotation nach > 6 MB) |
| 24a | `6c2799c` | toter Code (transcribe_full_chirp3, numpy_to_wav_bytes, pyperclip, get_close_matches, engine_label, prompt_toggle, ALLGEMEIN_FALLBACK beider Apps, leere download.html); Prompt-Hinweis nur einmal je Datei | `test_toter_code.py` |
| 24b | `4338870` | Gates → `tests/offline/`, Live-Harness → `tools/`, Messergebnisse → `docs/benchmarks/`; alle Pfade angepasst | alle Gates aus den neuen Pfaden grün; `git grep` ohne alte Pfade (außer Historie: Gutachten, BERICHT_v3.2) |

Zahlen: 23 Python-Testdateien in `tests/offline/` (plus Stub-Hilfe und Prompt-Snapshots) und 7 Node-Tests in
`web_app/`. Der Lint läuft ohne Warnung. `RaKScribe.py` hat jetzt 1333 statt 1994 Zeilen (Logik in 13 Modulen),
`App.tsx` 1016 statt 2365 (Logik in 12 Modulen unter `web_app/src/`).

## Abweichungen vom Auftrag (bewusst)

1. **F9 während der Verarbeitung bricht ab.** Laut Auftrag sollte er ignoriert werden. Seit v3.2.3 (Peter, 06.10.)
   bricht F9 aber ab. Diese neuere Entscheidung habe ich übernommen, also `reset` → „abbrechen“ in `jobstate.py`.
2. **CI nutzt Node 24 statt Node 20.** Die `.mjs`-Tests importieren TypeScript direkt, und Node 20 kann das nicht.
3. **VERSION enthält 3.2.3.** Der Auftrag nannte 3.2.2, das war der Stand vor dem heutigen Release.
4. **Deploy-Schutz.** Das einfache Muster `private_key|AQ\.…` aus dem Auftrag hätte jeden Deploy abgebrochen, weil
   der App-Code selbst `.private_key` enthält. Ich habe deshalb das genauere Muster aus v3.2.3 behalten und um
   mehrzeilige PEM-Schlüssel erweitert.
5. **Streaming-Generator.** Er liegt in `aufnahme.py` (Schritt 6), nicht in `stt.py`.
6. **Etwas früher erledigt als geplant.** Den Prompt aus localStorage und das Listener-Cleanup (eigentlich P3-2,
   Schritt 24) habe ich schon in Schritt 19 gemacht, den doppelten Chunk-Block schon in Schritt 8. Sie hingen
   jeweils direkt am Lint- bzw. Abbruch-Umbau.
7. **Fixture-JSONs bleiben im Root.** Der Auftrag nannte sie nicht. Mehrere Web-Tests und Apps lesen sie per
   relativem Pfad.

## Bewusst NICHT gemacht (Entscheidung Peter)

- **22 unerreichbare Vorlagen:** keine neuen Erkennungsregeln von mir. Seit v3.2.3 sind ohnehin alle 142 erreichbar.
  Die Liste `unerreichbar` in `detect_fixtures.json` ist leer, und das Gate schlägt an, sobald eine Vorlage wieder
  unerreichbar wird.
- **Vereinigung der Phrasenlisten:** `medical_exe` (292) und `medical_web` (565, das sind die 692 Einträge ohne 127
  Doppelte) bleiben getrennt. Eine größere EXE-Liste würde den Boost ändern.
- **iPhone-Browser-Prüfungen:** nicht gemacht (keine Browser-Läufe), siehe „Offene Punkte“.
- **Windows-EXE-Lauf:** nicht gemacht. Der Test ist erweitert (Fall D, Phrasen-Check) und läuft mit dem nächsten
  Build.

## Neu gefundene Punkte (nicht geändert, zur Entscheidung)

1. **CF_HTML-Offsets in Zeichen statt Bytes** (`clipboard_win.html_format_bytes`, unverändert übernommen). Bei
   Umlauten sind `EndHTML`/`EndFragment` zu klein. Programme, die die HTML-Variante nutzen (z. B. Word), könnten
   das Ende des Befunds abschneiden. Der reine Text (CF_UNICODETEXT) ist korrekt. Vorschlag: Offsets über
   `len(...encode("utf-8"))` berechnen. Das ist ein Einzeiler mit Test, ändert aber das Einfüge-Ergebnis.
2. **Zusammenfügen langer Diktate (> 50 s):** `stitch_overlaps`/`stitchOverlaps` werten eine Überlappung von
   1 Wort immer als Treffer. Ohne echte Überlappung fällt so das erste Wort des nächsten Segments weg (EXE und Web
   gleich). Bei leerem erstem Segment weichen EXE und Web zusätzlich voneinander ab. Beides ist in
   `sync_fixtures.json` dokumentiert. Vorschlag: Schwelle `max(1, int(L*0.8))`.
3. **Tools waren seit Schritt 8/18 kurz defekt** (`meddictate_bench`, `stt_ab`, `stt_ab_g35t`, `verify_k2k3` lasen
   Listen bzw. den Validator aus App.tsx). Sie sind repariert und lesen jetzt aus `phrases.json` bzw. über
   `prod_pipeline`.

## Schlüssel (Schritt 22)

`web_app/public/stt-key.txt` und `vertex-key.txt` lagen nicht mehr im public-Ordner; sie waren schon vorher entfernt.
Den lokalen Build-Ordner `web_app/dist/` vom 06.10. 11:19 habe ich gelöscht. Er enthielt kein Schlüsselmaterial.
**Der Praxis-Schlüssel liegt weiterhin nur im Drive-Ordner „RaKScribe“.** Die Empfehlung aus dem Gutachten bleibt
offen: den API-Key in der Google Cloud auf den Referrer `drpeterkalmar.github.io` beschränken und das
Service-Konto nur mit Speech-Rechten ausstatten.

## Offene Punkte (brauchen Windows bzw. iPhone)

**Windows (nächster EXE-Build):** Workflow „Build Windows EXE“ manuell ohne Tag starten. Das erzeugt eine
Vorabversion `test-<Lauf>`, die danach automatisch vom Windows-UI-Test geprüft wird. Neu prüft er F10 während der
Verarbeitung (Fall D) und die gebündelte `phrases.json`. Für das echte Release den Haken „release“ setzen
(Tag = VERSION) oder einen Tag angeben. Am Praxis-PC zusätzlich:
- Zwischenablage gesperrt halten (z. B. ein Zwischenablage-Programm) → Meldung, kein Einfügen.
- Langes Diktat über 4 Minuten (Neustart der Live-Anzeige).
- Netzwerk kurz trennen während der Aufnahme → „Live-Anzeige ausgefallen“, Befund kommt trotzdem.
- Zwei Regionen diktieren.

**iPhone (Web):**
- 5-Minuten-Diktat: Speicherverlauf und ob der Tab neu lädt.
- Diktat über 59 s: kommt chirp_3 richtig an? (Kein AudioContext mehr in diesem Pfad.)
- Bildschirm bleibt während der Aufnahme an (Wake Lock).
- „Neu“ während der Verarbeitung: es darf nichts mehr eingefügt werden.
- Ohne Netz: es soll eine verständliche Google-Meldung kommen.
