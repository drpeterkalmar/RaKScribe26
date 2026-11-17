# Bericht kaiscribe-webapp-schluessel-n1 – Web-App holt den Claude-Schlüssel selbst (Kanban #351)

Di 17.11.2026, 04:57–05:30, Coding-Queue. Ergebnis: **Web-App 3.19.5 schreibt mit Claude Sonnet (maskiert), ohne dass
Peter oder Georg etwas tun.** Kein Patient, kein Schlüssel in Chat/Logs/Repo.

## 1. Schlüsseldatei in Drive ersetzt

- Der Drive-Ordner „RaKScribe“ heißt heute **„Röntgen am Kai/Projekte/RIS-Mods/RaKScribe + Brücke“** (dort lag die
  `rakscribe-praxis-key.json` vom 03.09., 2460 B, nur `vertex_api_key` + `stt`).
- Kein Umweg über den Büro-PC nötig: Der Ordi-Hermes hat am Büro-PC (05:05, nur lesend) Prüfsummen der
  X:-Datei geliefert – `fa1bbf02b6840432` (2609 B, 16.11. 01:28), Felder `vertex_api_key, stt, anthropic_api_key`.
  Am Mac ergeben die alte Drive-Datei + `~/.hermes/secrets/anthropic-api-kaiformat` (Konto A, gleiche Prüfsumme
  `5cdf39ca…` wie das Feld auf X:) im Format des Helfers (indent 2, CRLF) **Byte für Byte dieselbe Datei**.
- Drive (rclone, Konto Peter): alte Fassung gesichert als `rakscribe-praxis-key.json.alt-20260903` (daneben, ohne
  „.json“-Endung, damit niemand sie versehentlich lädt), dann die Datei **an Ort und Stelle aktualisiert** (gleiche
  Datei-ID `17Wes4rC…`, Freigaben für Georg/roentgen.am.kai bleiben). Neue Änderungszeit **17.11. 05:03**,
  Prüfsumme in Drive = X:-Datei. Lokale Arbeitskopien gelöscht.
- X:\RaKScribe\rakscribe-praxis-key.json ist damit gleich der Drive-Datei; Nutzer, die die Datei neu laden, bekommen
  alles in einem.

## 2. Web-App lädt den Claude-Schlüssel beim Start selbst nach

Die meisten Browser haben noch die alte Schlüsseldatei geladen (ohne Claude). Damit niemand neu laden muss:

- **Dienstkonto statt Klick:** Die Datei ist zusätzlich **nur lesend** für das Spracherkennungs-Dienstkonto
  `rakscribe-stt@rakscribe.iam.gserviceaccount.com` freigegeben (keine Mail). Dessen Schlüssel liegt ohnehin in jedem
  Browser mit geladener praxis-key.json – wer ihn hat, hatte die Datei schon; es entsteht also kein neuer Zugang.
  Im Google-Projekt `rakscribe` ist dafür die **Drive-API eingeschaltet** (gratis).
- `web_app/src/llmAnbieter.ts`: `anthropicSchluesselNachladen()` – fehlt `anthropic_api_key` und ist Claude nicht
  per `llm_anbieter = gemini` abgeschaltet, holt die App ein Token (Bereich `drive.readonly`), sucht die neueste
  freigegebene `rakscribe-praxis-key.json` und speichert nur den Claude-Schlüssel. Scheitert es, bleibt Gemini und
  der nächste Start versucht es erneut.
- `stt.ts`: Token-Zwischenspeicher je Bereich (vorher nur je Konto – ein Drive-Token hätte sonst die Spracherkennung
  gestört).
- `App.tsx`: läuft beim Start bzw. sobald Schlüssel geladen werden; Konsole `[KEY] Claude-Schlüssel aus Drive nachgeladen`.
- **Gemini nur als gezählter Rückfall:** Ohne Claude-Schlüssel lief Gemini bisher ungezählt; jetzt zählt jeder
  solche Aufruf als `rueckfall` im Nutzungszähler (`ki_nutzung`).
- Tests: `llm_anbieter_test.mjs` 26/26 (neu: Nachladen, „schon da“, abgeschaltet, Datei ohne Schlüssel, nicht
  freigegeben, gezählter Rückfall) – jetzt auch in GitHub `test.yml`. Alle Web-Tests, `tsc`, `eslint`,
  `test_ki_maske_web.py`, `test_llm_anbieter.py` grün; GitHub Tests + Pages-Deploy für `622506f` grün.

## 3. Live-Beleg (05:18, https://drpeterkalmar.github.io/RaKScribe26/)

Frischer Test-Browser (stumm, headless), darin nur die **alte** Schlüsseldatei vom 03.09. (ohne Claude-Schlüssel):

| Schritt | Ergebnis |
|---|---|
| Seite | Badge **v3.19.5** |
| Nachladen | nach **1 s** Claude-Schlüssel da (Prüfsumme `5cdf39ca…` = Konto A), Drive-Liste + Datei je HTTP 200, `[KEY] Claude-Schlüssel aus Drive nachgeladen` |
| „Befund aus Text“ mit „Kniegelenk links. Mäßige Gonarthrose medial. Kleiner Gelenkerguss.“ | 2 × `api.anthropic.com/v1/messages` **HTTP 200** (Korrektur + Befund), Zähler `{"anthropic":2}`, **kein Rückfall**; Befund „Kniegelenk links in 2 Ebenen … Mäßige degenerative Veränderungen des medialen Kompartiments …“ |

(Die zwei Gemini-Aufrufe im Netzprotokoll sind die übliche Schlüsselprüfung beim Start, kein Befund.)

## Entscheidungen (ohne Rückfrage, empfohlene Option)

- Schlüsselinhalt vom Mac statt Büro-PC: lag nachweislich identisch vor (Prüfsummen), spart das Büro-PC-Fenster.
- Drive-Freigabe für das STT-Dienstkonto statt Google-Login im Browser oder Secret Manager: keine neue Anmeldung,
  eine einzige Quelle (die Drive-Datei), Rückweg = Freigabe entfernen.
- VERSION 3.19.5 nur für die Web-App (EXE unverändert, kein EXE-Release nötig; die nächste EXE trägt die Nummer mit).

## Rückweg

Freigabe von `rakscribe-stt@…` an der Drive-Datei entfernen (dann wieder Gemini, gezählt) oder im Browser
`localStorage.llm_anbieter = 'gemini'`. Alte Drive-Fassung: `rakscribe-praxis-key.json.alt-20260903`.

## Offen

- Nichts für Peter. Ein Browser, der gerade offen ist, holt den Schlüssel beim nächsten Neuladen der Seite.
