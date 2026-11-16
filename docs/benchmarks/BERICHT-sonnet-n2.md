# kaiscribe-sonnet-n2 – Befund-KI auf Claude Sonnet 5.5 (maskiert), Gemini nur Rückfall – 16.11.2026

**Kurz:** KaiScribe 3.19.0 schreibt den Befundtext standardmäßig über **Claude Sonnet 5.5** (Text vorher maskiert),
Gemini springt nur noch bei einem Anthropic-Problem ein. Die zwei Satzverluste aus dem 13.11. sind mit Sonnet weg
(Kurzsätze 5/5, Georg 6/6). In 1049 Test-Aufrufen gab es **0 Rückfälle** auf Gemini und 0 $ Google-Kosten.
Einspielen: siehe Abschnitt „Einspielen“.

## Vorher/nachher je Prüfskript (Sonnet 5.5 maskiert, Testschlüssel Konto B)

„Vorher“ = `BERICHT-haiku-ab-n1.md` (13.11., Stand 3.18.5). „Nachher“ = dieser Job auf 3.19.0, alle Aufrufe über
`KAISCRIBE_TEST_ROUTE=alle=claude-sonnet-5-5` (Call 0, Befund, Prüfung) durch die Produktionsfunktion
`source_code/llm_anbieter.py`. **Gemini wurde nicht gemessen** (Google-Testgrenze 0 $ seit 520cef7); der Gemini-Weg
ist unverändert (Prompt-Snapshots wortgleich, nur die Anthropic-Seite und die Standards sind neu).

| Prüfskript | Läufe | vorher Sonnet (13.11.) | nachher Sonnet (16.11.) |
|---|---|---|---|
| verify_kurzsaetze | 5 | rot: Fall 5 EXE „ZVK-Spitze in der V. cava superior“ 2/3 | **grün**, alle 12 Fälle × EXE/Web 5/5 |
| verify_georg_schulter_ellbogen | 2 × 3 | rot 7/8 (Web-Lauf 3: ein Schulter-Vorlagensatz weg) | **grün** 8/8 und 8/8 |
| test_all_regions (+ --cas, --ibl) | 1 | grün | grün |
| verify_widerspruch | 1 | grün | grün |
| verify_knie | 3 | grün | grün |
| verify_sprunggelenk | 3 | grün | grün |
| verify_flachprofil | 3 | grün | grün |
| verify_k2k3 | 5 | grün | grün |
| verify_peter_ergebnis | 5 | grün | grün |
| verify_konfabulation | 3 (18 Fälle) | 89/90 (5 Läufe) | **51/54**: nur `ibl_kl1` 0/3 (IB-Lab-Grad 1 fehlt im Ergebnis – bei allen Modellen rot, #261, kein erfundener Inhalt). Alle rh38/rh99/erhalt-Fälle 3/3: **nichts erfunden** |

**Nicht wie verlangt gefahren:** 20 Wiederholungen der Konfabulation. 20 × 18 Fälle × bis zu 3 Aufrufe passen nicht in die
10-$-Grenze des Jobs. Der erste 20er-Lauf brach nach 408 Aufrufen an der Tagesgrenze ab (15 $ über alle Jobs am Mac,
ohne Auswertung). Danach: 3 Läufe komplett, ein weiterer 5er-Lauf brach wieder an der Tagesgrenze ab (18 $, bewusst
angehoben wie im haiku-ab-n1-Job). Kurzsätze, K2/K3 und Peter-Ergebnis liefen mit der Release-Zahl (5).
Satzverluste (Aufgabe 1) sind damit **ohne Code-Änderung an Erhalt-Regel/Kurzsatz-Wächter grün**. Zwischen 13.11. und
heute kamen 3.18.6–3.18.13 dazu (Abschnittsprüfung, Arthrose-Wächter, Chirp-Marken), und die strengere
Platzhalter-Regel ist weg (unten). Gemini als Rückfall ist unverändert.

## Latenz (Sonnet 5.5, je Aufruf, 1049 Aufrufe)

| Aufruf | Anzahl | p50 | p90 | max | $ je Aufruf (Test, Cache warm) |
|---|---|---|---|---|---|
| Call 0 Korrektur | 189 | 2,07 s | 2,50 s | 2,8 s | 0,0020 |
| Befund (Gen) | 647 | 2,83 s | 3,46 s | 5,3 s | 0,0112 |
| Prüfung (Web) | 213 | 2,84 s | 3,70 s | 5,0 s | 0,0061 |

Zum Vergleich Gemini (13.11.): Befund 2,11/3,06 s. Sonnet ist also ≈ +0,7 s (p50) / +0,4 s (p90) langsamer, aber ohne
Gemini-Ausreißer (bis 36 s). EXE = nur der Befund-Aufruf; Web = Call 0 + Befund + Prüfung.

## Prompt-Cache 1 Stunde (Aufgabe 2)

- Fester Befund-Prompt-Anfang = **21.443 Token** (gemessen, Sonnet-Tokenizer), Call 0 4.955, Prüfung 4.729.
- Preise Sonnet 5.5 je 1 Mio Token: Input 2,00 $, Cache lesen 0,20 $, Schreiben 5 min 2,50 $, **Schreiben 1 h 4,00 $**.
- Rechnung je Befund-Aufruf (Anfang): Treffer 0,0043 $, Neuschreiben 5 min 0,054 $, 1 h 0,086 $, ganz ohne Cache 0,043 $.
- Ordi-Takt ≈ 150 Befunde an ~10 Stunden → im Mittel alle 4 min einer (alle PCs teilen den Cache, gleicher Schlüssel).
  Abstände > 5 min kommen dann bei ≈ 29 % der Befunde vor (Pausen, Ultraschall, Mittag). 5 min: ≈ 2,9 $/Tag nur für den
  Anfang; **1 h: ≈ 1,5 $/Tag** (≈ 11 Neuschreibungen am Tag). Ab ≈ 12 % Fehltreffern ist 1 h billiger → **1 h ist eingebaut**
  (`llm_anbieter.CACHE`, Web `ttl: '1h'`). Die API nimmt `ttl: 1h` an (alle 1049 Testaufrufe ohne Fehler).
- Gemessen im Test: 5 Neuschreibungen in 647 Befund-Aufrufen, Rest Cache-Treffer.

## Kosten je Befund + Hochrechnung

| | $ je Befund (EXE, nur Befund-Aufruf) | $/Monat bei 3.000 Befunden |
|---|---|---|
| Test (Cache fast immer warm) | 0,0112 | 34 $ |
| Betrieb geschätzt (1-h-Cache, ~11 Neuschreibungen/Tag, Output ~350 Token) | ≈ 0,016 | **≈ 47 $** |
| Web-Kette (Call 0 + Befund + Prüfung) | ≈ 0,019 (Test) | – (Web nur Peter/Georg) |

Obergrenze, weil Normalbefund-Bypässe nichts kosten. Läuft über **Konto A** (KaiFormat-Schlüssel, 200 $/Monat, laut
haiku-ab-n1 ≥ 70 $ frei). Google zahlt nur noch Chirp (Spracherkennung) und die seltenen Rückfälle.

## Was gebaut wurde (3.19.0)

- **Standard anthropic** in `config.py` (Datenklasse, `STANDARD_INHALT` einer neu angelegten config.ini, Lesen ohne Zeile),
  mitgelieferter `config.ini`, Web `llmAnbieter.ts` (anthropic, sobald der Anthropic-Schlüssel aus der Praxis-Schlüsseldatei
  geladen ist; `localStorage.llm_anbieter = 'gemini'` schaltet zurück). Modell `claude-sonnet-5-5`, Frist 20 s.
- **Rückfall auf Gemini** wie gehabt bei Ausfall, Frist 20 s, Maske unsicher, unvollständiger/abgeschnittener Antwort,
  unbekanntem Platzhalter – **und** wenn ein **Datum** des Diktats in der Antwort fehlt.
- **Platzhalter-Regel gelockert** (offene Peter-Frage aus haiku-ab-n1, hier entschieden wegen „ich will nicht noch extra
  google zahlen“): Pflicht sind nur Daten ⟦D⟧. Namen/Nummern/Adressen darf der Befund weglassen – Gemini lässt sie selbst
  weg; mit der strengen Regel ging jeder Befund mit Zuweiser im Diktat doppelt (Claude, dann Gemini auf Google-Kosten).
- **Zähler + Tagesbericht** (`source_code/nutzung.py`, ohne Patientendaten): je PC und Monat
  `X:\RaKScribe\Daten\nutzung\<JJJJ-MM>_<PC>.json` mit Befunden, Claude-Aufrufen, Rückfällen (nur Kategorie),
  Anthropic-$, **an Chirp geschickten Audiosekunden**; nach jedem Ereignis `tagesbericht_<JJJJ-MM-TT>.txt` (alle PCs:
  Rückfälle heute/Monat mit Grund, Chirp-Minuten × 0,016 $/min, Hochrechnung Monat in €). Hochrechnung > 6 € →
  Zeile `WARNUNG` + `warnung_<JJJJ-MM>.txt`. Web zählt Claude/Rückfall je Tag im Browser (`localStorage.ki_nutzung`).
- **Logzeile je Claude-Befund** `[KI] gen: Anbieter=anthropic claude-sonnet-5-5 maskiert (2.9 s, 3 Platzhalter)`; im
  Lauf-Protokoll (`X:\RaKScribe\Daten\laeufe`) steht unter `modell`, wer den Befund wirklich schrieb
  (`anthropic/claude-sonnet-5-5` bzw. `gemini/gemini-3.5-flash (Rückfall)`).
- **Büro-PC-Helfer** `tools/buero/kaiscribe_anthropic.py`: Schlüssel Konto A aus der Windows-Anmeldeinformation
  `RaK-Anthropic-KaiFormat` in `X:\RaKScribe\rakscribe-praxis-key.json` (Sicherung, nie ausgegeben), config.ini umstellen
  (`config --anbieter gemini` = Notschalter zurück), Probe einer EXE-Kopie im WAV-Modus.
- Tests: `test_nutzung.py`, `test_buero_anthropic.py`, `test_llm_anbieter.py`, `llm_anbieter_test.mjs`;
  `testkosten`: Rückfall in Tests ohne Google (Ersatztext statt Exit 7).
- Web-CORS geprüft: `api.anthropic.com` erlaubt den Browser-Aufruf von `drpeterkalmar.github.io` (Preflight 200).

## Einspielen

(wird nach dem Ordi-Lauf ergänzt)

## Kosten dieses Jobs

Anthropic Konto B 8,92 $ von 10 $ (1049 Aufrufe), Google 0 $. Rohdaten `~/cj/work/kaiscribe-sonnet-n2/`, Kostenbuch
`~/cj/work/testkosten/kaiscribe-sonnet-n2.jsonl` + `.weiche.jsonl`.
