# BERICHT kaiscribe-ohne-gemini-n1 – kein Gemini-Rückfall mehr in KaiScribe (Version @@VERSION@@)

Anlass: Peter 23.11.2026 ~22:30 „Dauert die Antwort länger als 20 s, übernimmt Gemini — das kannst abstellen. no gemini
please derzeit.“ Teil 1 (Bau, Hetzner, Di 24.11. nachts) ohne Büro-PC; Einspielen + Abnahme 451898 = Teil 2 (siehe unten).
Keine Patientendaten in diesem Bericht.

## Abschluss (≤ 6 Zeilen)
1. EXE + Web: kein automatischer Gemini-Aufruf mehr (Korrektur, Befund, Prüfung); neuer Schalter `KI_RUECKFALL = aus` (Standard).
2. Statt Rückfall: Frist 45 s, bei Frist/Netz/HTTP 429/5xx/overloaded/Platzhalter/Maske EIN zweiter Claude-Versuch (2 s Pause).
3. Geht auch der schief: Call 0 → Rohtext; Befund → Diktat unverändert ins Befundfeld + rote Prüfzeile, nichts eingefügt; Prüfung entfällt.
4. Zähler/Tagesbericht: „ohne KI“ je Rolle + Grund, zweite Versuche; Log `… → ohne KI (kein Rückfall)`, `[INIT] … Rückfall: aus, Frist 45 s`.
5. Version @@VERSION@@ auf main, alle Offline-Gates grün (63 Python + 4 Web + tsc + eslint); Web geht mit dem Push live, EXE erst nach 451898.
6. Rückweg: `KI_RUECKFALL = an` (config.ini) bzw. im Browser `localStorage.ki_rueckfall = 'an'`; Notschalter `LLM_ANBIETER = gemini` bleibt.

## Rückfall-Statistik seit 16.11. (Messung)
- **Teil 1 ohne Büro-PC/X:** die Nutzungszähler `X:\…\Daten\nutzung\2026-11_*.json` und `tagesbericht_*` liegen nur auf X:
  → Auszählung je Grund ist Aufgabe von Teil 2 (nur lesen, Ergebnis als Nachtrag hier).
- Vorhandener Beleg im Repo-Umfeld: Auszug `rakscribe.log` des Büro-/Befund-Betriebs 21.–23.11. (Job
  kaiscribe-befundfeld-sicher-n1-kontrolle, `~/cj/work/kaiscribe-befundfeld-sicher-n1-kontrolle/aus3.txt`, nur Statuszeilen):
  28 `[KI]`-Aufrufe (23 Befund, 5 Korrektur), davon **27 über Claude** und **1 Rückfall** (Korrektur, „Antwort unvollständig“
  = Call-0-Antwort nicht plausibel), **0 × Frist, 0 × HTTP, 0 × Maske**.
- Dauer der Claude-Aufrufe (27): **p50 3,1 s, p90 4,6 s, max 7,3 s**.
- Älterer Beleg: `docs/benchmarks/BERICHT-sonnet-n3-beleg.md` (17.11.): CASWS10 4 Befunde/4 Claude/0 Rückfall, CASWS14 0/1/0.

## Gewählte Frist: 45 s
Gemessen max 7,3 s (p90 4,6 s) – die alte 20-s-Grenze wurde im Beleg nie erreicht. Trotzdem 45 s statt kleiner: die
Stichprobe ist klein (ein Tag), lange Mehr-Regionen-Befunde (bis 4000 Ausgabe-Token) brauchen bei Sonnet deutlich länger
als ein Knie-Befund, und ohne Gemini dahinter kostet eine zu knappe Frist einen ganzen Befund (zweiter Versuch scheitert
dann genauso). Live wird im Hintergrund diktiert, der Roboter wartet. Schlimmster Fall 45 + 2 + 45 s ≈ 1,5 min, dann
Diktat roh. Die PCs haben in ihrer config.ini noch `ANTHROPIC_FRIST = 20` (alter Standard) → wird als 45 gelesen;
jeder andere Wert gilt wie eingetragen. Teil 2 prüft die Frist gegen die Zähler seit 16.11. (Frist-Rückfälle > 0?).

## Verhalten bei Ausfall (Soll 1–4 umgesetzt)
| Rolle | 1. Versuch scheitert | 2. Versuch scheitert |
|---|---|---|
| Call 0 Korrektur (EXE Nur Text / Web) | Pause 2 s, neu | unkorrigierter Diktattext weiter in die Kette, Log `[KORREKTUR] ohne KI` |
| Befund (EXE + Web) | Pause 2 s, neu | Diktattext (nach Fehlhör-Liste/Satz-Bausteinen) unverändert ins Befundfeld + rote Prüfzeile **„KI nicht verfügbar – Diktat unformatiert übernommen, bitte prüfen.“**; EXE: nichts in CAS eingefügt (wie unvollständiger Befund, Status Fehler, Kurzhinweis 20 s), stand vorher etwas im Feld (Gerüst), bleibt es oben stehen; kein KaiScribe-Stand → Restructure baut ihn später neu. Web: Statuszeile mit der Prüfzeile, nicht kopiert. |
| Prüfung (Call 2, nur Web) | Pause 2 s, neu | Befund aus Call 1 bleibt, Prüfung entfällt, Log `[VALIDATE] ohne KI` |
| Restructure | – | Text bleibt unverändert, Dialog „KI nicht verfügbar … bitte später erneut“ |

- Kein zweiter Versuch bei fehlendem Anthropic-Schlüssel und HTTP 400/401/403/404 (dieselbe Anfrage scheitert wieder).
- Normalbefund-Bypass und wörtliche Bausteine brauchen keine KI → unverändert.
- Spracherkennung (Chirp/Google STT) unverändert.
- Logzeilen nur Kategorie: `[KI] gen: Anthropic nicht verwendet — Frist → ohne KI (kein Rückfall)`; Kategorien Frist, Netz,
  HTTP <n>, overloaded, Platzhalter, abgebrochen, unvollständig, Maske unsicher, Schlüssel.
- Zähler (`nutzung.py`): `ki.ohne_ki`, `ohne_ki_rolle` {gen, korr}, `ohne_ki_grund` {Kategorie}, `ki.zweitversuch`,
  `ki.zweitversuch_ok`; alter Zähler `rueckfall` bleibt für `KI_RUECKFALL = an`. Tagesbericht neue Zeile
  „Ohne KI (kein Rückfall) heute n (Grund: n) je Rolle (…), zweite Claude-Versuche n (davon geklappt n)“.
- Web-Zähler `localStorage.ki_nutzung`: zusätzlich ohne_ki, zweitversuch, zweitversuch_ok.
- Regel-Register: neue Pflicht-Regel `ohne-ki-pruefzeile` (Wortlaut in llm_anbieter.py, llmAnbieter.ts, pipeline.py, config.py).

## Code
`source_code/llm_anbieter.py` (Weiche: `rueckfall`, Zweitversuch, `OhneKi`, `HttpFehler`, `kategorie`, Frist 45),
`config.py`/`config.ini` (`KI_RUECKFALL`, Frist 45, Altwert 20 → 45), `pipeline.py` (`_ohne_ki`), `korrektur.py`,
`RaKScribe.py` (Weiche aus config, `[INIT]`, Befund/Restructure ohne KI), `nutzung.py`; Web `llmAnbieter.ts`, `gemini.ts`,
`pipeline.ts`, `App.tsx`; `tools/testkosten.py` (Live-Tests wie die EXE ohne Rückfall, `KAISCRIBE_TEST_KI_RUECKFALL=an`).
Tests: `test_llm_anbieter.py` (+ aus-Fälle mit Gemini-Spion, Handschalter gemini, HTTP 529/429/400, Maske, Pipeline),
`test_nutzung.py`, neu `test_ohne_ki_ui.py` (EXE-Ablauf), `web_app/llm_anbieter_test.mjs`; alte Rückfall-Tests laufen mit
`KI_RUECKFALL = an` weiter (Rückweg belegt), `exe_stubs.py` lädt die UI-Tests wie bisher mit Rückfall an (ihre Attrappen
ersetzen den Gemini-Weg). Neu in test.yml: test_llm_anbieter, test_ohne_ki_ui, test_nutzung.
Live-Test (KaiTest-Schlüssel) in Teil 1 nicht nötig: der Erfolgsweg ist unverändert, neu ist nur der Fehlerweg (offline belegt).

## Beleg 451898
Offen → Teil 2 (Release-Regel Georg: Log zeigt „Rückfall: aus“ + einen Befund über anthropic/claude-sonnet-5-5, sonst Rollback).

## Teil 2
Einspielen + Abnahme 451898 + Messung auf X: (nur lesen) laufen gebündelt als Nachtrag am schon wartenden
KaiScribe-Einspiel-Auftrag `sm-senf-laenge-n1-einspielen` (ein Einspielen und eine Abnahme-Runde je Programm und Abend);
lehnt die Queue den Nachtrag ab, als eigener Folgeauftrag `kaiscribe-ohne-gemini-n1-einspielen` (`--ressource
ordi,automaten-vm`). Inhalt: `FOLGEJOB-KAISCRIBE-OHNE-GEMINI-N1-EINSPIELEN.md`. EXE: Vorabversion `test-<Lauf>` aus
`build-exe.yml` (main, VERSION @@VERSION@@), Release Latest erst nach grüner Abnahme.
Arbeitsdateien Teil 1: `~/cj/work/kaiscribe-ohne-gemini-n1/` (Testliste, Versions-Skript).
