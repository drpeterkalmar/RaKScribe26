# kaiscribe-haiku-ab-n1 – Befund-KI: Gemini 3.5 Flash (EU) gegen Claude Haiku 5.5 / Sonnet 5.5 (maskiert) – 13.11.2026

**Kurz:** Haiku 5.5 ist ~10× billiger als Gemini und gleich schnell, **erfindet aber Befunde und lässt Diktiertes weg**
(6 von 12 Prüfskripten rot, Konfabulation 67/90) → **nicht umschalten**. Sonnet 5.5 maskiert verliert in 100 Ordi-Befunden
keine Pathologie, ist ~0,8 s langsamer und kostet mit Cache etwa die Hälfte von Gemini heute (ohne Cache);
in den Prüfskripten erfindet Sonnet weniger als alle anderen (Konfabulation 89/90), verliert aber zweimal einen einzelnen Satz (10/12 grün) → **Sonnet ist fast gleichauf, noch nicht ganz**. Umschalten ist jetzt eine Einstellung (Standard bleibt Gemini), nichts eingespielt, kein Release.

## Tabelle Modell × Kennzahl

20 synthetische Harness-Diktate (`test_all_regions.TEST_CASES`) × **5 Läufe** je Modell = 100 Befunde je Zeile, echte
Produktionsketten (`tools/modellvergleich.py`): **EXE** = was im Ordi läuft (nur Befund-Aufruf), **Web** = Call 0 Korrektur →
Befund → Prüfaufruf. Claude immer über `source_code/llm_anbieter.py` (maskiert, Rückfall Gemini), Testschlüssel Konto B.

| Kennzahl | Gemini 3.5 Flash eu (heute) | Haiku 5.5 maskiert | Sonnet 5.5 maskiert | Hybrid Web (nur Call 0 Haiku) |
|---|---|---|---|---|
| Prüfskripte (testlauf, 12 Skripte) | alle grün (am 13.11. im modellvergleich-n1 auf demselben Prompt-Stand)¹ | **6/12 rot** (Knie, Sprunggelenk, K2/K3, Peter-Ergebnis, Georg, Konfabulation) | **10/12 grün**; rot: Kurzsätze (Fall 5 EXE „ZVK-Spitze in der V. cava superior“ 2/3), Georg 7/8 (Web-Lauf 3: ein Schulter-Vorlagensatz weg) | – |
| Konfabulation (18 Fälle × 5) | rh99_koxa 20/20, rh99_degen2 0 erfunden¹ | **67/90 PASS**: erfindet Osteophyt/Sklerose (erhalt_ohne_adj 4/5), Arthrose (rh99_degen2 2/5), K&L-Grad fehlt (rh99_koxa 0/5) | **89/90 PASS**: nichts erfunden, alle K&L-Grade da; sogar ibl_kl1 4/5 (alle anderen 0/5) | – |
| Pathologie fehlt im Befund – EXE | **0**/100 | **8**/100 (SLAC wrist 5/5, Kellgren 3/5) | **0**/100 | – |
| Pathologie fehlt – Web | 5/100 (Kahnbein 5/5) | 12/100 | – | 6/100 |
| Normalbefund-Treue EXE · Web | 83,1 % · 81,9 % | 84,1 % · 81,2 % | 82,4 % · – | – · 83,1 % |
| Seitenangabe (Checker, 17 Fälle mit Seite) EXE | 65/85 | 61/85 (Schädel 4/5 ohne Seite im Titel) | 60/85 | 60/85 |
| Wortfehler | – | „Maßgradige“ statt „Mäßiggradige“ (Knie K&L), Feld-Labels bleiben stehen | – | – |
| Latenz je Befund EXE p50 / p90 (max) | 2,24 / 3,38 s (36 s Ausreißer) | **2,00 / 2,69 s** (3,8) | 3,05 / 4,46 s (6,7) | – |
| Latenz je Befund Web p50 / p90 | 5,85 / 8,35 s | 5,70 / 7,53 s | – | 5,89 / 7,41 s |
| Latenz je Aufruf p50/p90: Call 0 · Befund · Prüfung | 1,42/1,81 · 2,11/3,06 · 2,01/2,61 | 1,40/1,64 · 1,84/2,47 · 1,81/2,51 | – · 2,72/4,00 · – | 1,43/1,72 (Haiku) |
| $ je Befund EXE, gemessen (Cache) / ohne Cache | 0,0056 / **0,0232** (Produktion hat heute keinen Cache) | **0,0006** / 0,0027 | 0,0116 / 0,0497 | – |
| $ je Befund Web (Cache) / ohne Cache | 0,0171 / 0,0346 | 0,0010 / 0,0037 | – | 0,0114 / 0,0294 |
| Rückfälle auf Gemini (Harness, 300 Haiku-Aufrufe Web + 100 EXE) | – | 2 × „unvollständig“ (0,5 %), 0 × Frist (20 s), 0 × Ausfall | 0 | 0 |
| Maskierung: Werte wieder im Befund (Diktat + 1 erfundener Personendaten-Satz) | 11/20 (Gemini lässt Zuweiser/Befundnr. selbst weg) | Datum 10/10, Termin 10/10, Zuweiser → Gemini 10/10, Befundnr. → Gemini 10/10 | wie Haiku (5/5, 5/5, Rückfall, Rückfall) | – |
| Platzhalter-Reste „⟦…⟧“ im Befund | – | **0** in 100 maskierten Befunden | 0 | – |

¹ Gemini-Prüfskripte nicht noch einmal gefahren: der Gemini-Anteil dieses Jobs war nach den 5×-Kettenläufen bei 4,36 $ von 5 $
(Web-Kette ohne Cache auf Call 0/2 ist teuer). Referenz = `BERICHT-MODELLVERGLEICH-N1.md` und
`docs/benchmarks/konfabulation_rh99_2026-11-12.md` (gleicher Prompt-Stand; mein Code ändert den Gemini-Weg nicht, die
Snapshot-Tests sind wortgleich). ibl_kl1 ist bei allen Modellen rot (#261) und zählt hier nicht als Modellthema.

**Was die Zahlen heißen**
- **Haiku:** Tempo und Preis top, aber genau die Fehlerklasse, die Peter am meisten stört (Konfabulation): erfundene
  Osteophyten/Sklerose, erfundene Arthrose, fehlende diktierte Grade, „SLAC wrist“ verschwindet aus dem Ergebnis.
  Zusätzlich hält Haiku den Call-0-Prompt (Gemini-Stil „Roh: … Korrigiert:“) für ein Beispiel und fragt zurück („Bitte gib
  mir den Text …“, 15/20) – auf dem Anthropic-Weg steht das Diktat deshalb in `<diktat>`-Tags (danach 20/20), und eine
  Rückfrage statt Korrektur geht über eine Wortüberlappungs-Prüfung auf Gemini.
- **Sonnet:** inhaltlich deutlich näher an Gemini (0 fehlende Pathologien EXE), aber ~0,8 s (p50) bzw. ~1,1 s (p90)
  langsamer und doppelt so teuer wie Gemini MIT Cache. In den Prüfskripten ist Sonnet bei der Konfabulation besser als Gemini (89/90, ibl_kl1 4/5), verliert aber zweimal einen einzelnen Satz bzw. Vorlagensatz (Kurzsätze 2/3 in einem Fall, Georg 7/8) – Gemini war dort am 13.11. 5×/8×8 grün.
- **Maskierung:** funktioniert in der Kette (kein Platzhalter-Rest, Daten kommen zurück). Die strenge Regel „fehlt ein
  Platzhalter des Diktats → Gemini“ schlägt bei Zuweiser-Namen und Befundnummern immer an – die lässt aber auch Gemini im
  Befund weg (0/5 bzw. 1/5). Folge: solche Befunde laufen erst Anthropic, dann Gemini (≈ +2–3 s, doppelte Kosten).

## Hochrechnung Betrieb (36.000 Befunde/Jahr = 3.000/Monat, Listenpreis netto, ohne 20 % USt)

Obergrenze: Die Harness-Diktate sind alle pathologisch; reine Normalbefunde (Bypass ohne KI) kosten 0. EXE-Zahlen, weil die
Befund-PCs die EXE nutzen. Spracherkennung (Chirp 3, ~0,74 €/Monat) bleibt bei Google und ist nicht enthalten.

| Variante | $/Befund | $/Monat | vom 200-$-Guthaben bleibt (Konto A, schon ~40–50 $ verplant) |
|---|---|---|---|
| (a) Gemini brutto heute (kein Cache) | 0,0232 | **≈ 70 $** (Web-Kette ≈ 104 $) | – (läuft über Google) |
| Gemini mit Kontext-Cache (#263, Release nötig) | 0,0056 | ≈ 17 $ | – |
| (b) Haiku 5.5 mit Prompt-Cache | 0,0006–0,0027² | **≈ 2–8 $** | ≈ 142–158 $ |
| Sonnet 5.5 mit Prompt-Cache | 0,0116–0,026² | **≈ 35–78 $** | ≈ 72–125 $ |

² Spanne = alle Aufrufe treffen den 5-Minuten-Cache … nur ~70 % treffen (Ordi-Pausen > 5 min, dann Cache-Schreiben 1,25×).
Mit 1-Stunden-Cache (Schreiben 2×) läge Sonnet bei ≈ 45–50 $. Rückfälle auf Gemini kommen obendrauf (Harness 0,5 %;
bei Diktaten mit Zuweiser/Befundnummer deutlich mehr, siehe oben).

**Konto-Vorschlag:** Betrieb auf **Konto A** (KaiFormat-Schlüssel) – das ist die geltende Regel „Betrieb = A, Tests = B“, und
selbst Sonnet passt mit Rest ≥ 70 $ hinein. Konto B bleibt für Tests (150-$-Deckel; dieser Job hat dort 5,20 $
verbraucht). Alternative: ein eigener Schlüssel „KaiScribe“ auf Konto A, damit die Kosten getrennt sichtbar sind.

## Empfehlung (ehrlich)

1. **Haiku: nein.** Billig und schnell, aber Konfabulation und Befundverlust sind schlechter als Gemini – Peters Bedingung
   „mindestens gleichauf in Qualität“ ist klar nicht erfüllt. Auch kein Hybrid für die EXE (die EXE nutzt Call 0 nur im
   Nur-Text-Modus); für die Web-Kette spart „Haiku nur Call 0“ ≈ 1/3 der Kosten bei gleicher Qualität (6 vs. 5 fehlende
   Pathologien), lohnt aber den neuen Datenweg allein nicht.
2. **Sonnet: ja als Ziel (Peters Nachtrag: Anthropic konstanter), aber noch nicht sofort.** Qualität fast gleichauf (weniger Erfundenes, zwei Einzelverluste), Latenz +0,8 s p50 / +1,1 s p90 (EXE 3,0/4,5 s statt 2,2/3,4 s – im Live-Diktat merkbar, aber ohne Gemini-Ausreißer bis 36 s), Kosten etwa wie Gemini heute brutto. Weg dorthin: (1) Nachbesserungs-Job für die zwei Satzverluste (Erhalt-Regel/Kurzsatz-Wächter mit Sonnet, Messung 5×), (2) Release mit Schalter, Standard noch gemini, (3) 20×-Release-Suite mit `KAISCRIBE_TEST_ROUTE=alle=claude-sonnet-5-5` grün, (4) Pilot an Peters Befund-PC eine Woche (`LLM_ANBIETER = anthropic`), Gemini bleibt Rückfall, (5) dann alle PCs.
3. **Gemini bleibt vorerst Standard.** Der größte sichere Hebel bleibt der Kontext-Cache für Gemini (#263: ≈ 70 → 17 $/Monat).

## Was beim Umschalten zu tun ist (erst nach Peters Go)

- **EXE:** `config.ini` am X:-Laufwerk: `LLM_ANBIETER = anthropic`, `ANTHROPIC_MODELL = claude-sonnet-5-5` (bzw. Haiku),
  optional `ANTHROPIC_FRIST = 20`, `LLM_ANBIETER_KORREKTUR` (leer = wie oben). In `rakscribe-praxis-key.json` (Drive „RaKScribe“)
  das Feld `"anthropic_api_key": "sk-ant-…"` ergänzen (Schlüssel von Konto A, nie KaiTest). Die EXE braucht dafür ein
  Release mit diesem Stand (llm_anbieter.py/ki_maske.py sind als hidden-import im Build); ohne Schlüssel oder bei jedem
  Problem läuft alles über Gemini weiter, Protokollzeile `[KI] gen: Anthropic nicht verwendet — <Grund> → Gemini`.
- **Web:** Schlüssel kommt mit derselben Praxis-Schlüsseldatei (`anthropic_api_key`), Umschalten im Browser per
  `localStorage.llm_anbieter = 'anthropic'` (+ optional `anthropic_modell`, `llm_anbieter_korrektur`). Offen: ein Live-Test im
  Browser (CORS mit `anthropic-dangerous-direct-browser-access`) – hier nicht gefahren (Leicht-Spur, kein Browser); eine
  Schalterfläche in den Einstellungen gibt es noch nicht.
- **Vorher erledigen:** (1) Zuweiser/Befunder aus dem CAS-Auftrag als bekannte Namen an die Maske geben (`Weiche.namen`
  ist vorbereitet, in RaKScribe.py noch nicht verdrahtet); (2) Regel für Platzhalter entscheiden (siehe unten);
  (3) Datenschutz: USA-Transfer/AVV mit Anthropic (Konto A hat KaiFormat schon so laufen) – Peters Entscheid 03.11. gilt
  für maskierten Text; (4) Release + Büro-PC-Test (Windows-Prüfung) wie üblich.
- **Lokales Modell (VM) später:** dritter Anbieter = eigener Zweig in `Weiche` (`ANBIETER`-Liste in `config.py` und
  `llm_anbieter.py`), Maskierung/Rückfall/Protokoll bleiben; bei lokal kann die Maske entfallen.

## Entscheidungen für Peter

- a) Sonnet maskiert als Befund-KI vorbereiten (Release mit Schalter auf Sonnet, Gemini nur Rückfall) – b) Haiku trotzdem
  (billig, aber schlechter) – c) bei Gemini bleiben, zuerst Gemini-Cache (#263).
- Platzhalter-Regel: streng lassen (jeder maskierte Wert des Diktats muss zurückkommen, sonst Gemini) oder nur Daten
  (⟦D⟧) verlangen und Zuweiser/Nummern fehlen lassen dürfen wie bei Gemini.
- Konto für den Betrieb: A (Vorschlag) oder B.

👉 Peter: Bericht lesen und a/b/c + Konto + Platzhalter-Regel entscheiden, bis 20.11. (Kanban #288).

## Was gebaut wurde (Standard unverändert Gemini, nichts eingespielt)

- `source_code/llm_anbieter.py` – Weiche gemini|anthropic: fester Prompt-Anfang unmaskiert als Cache-Breakpoint, Rest mit
  `ki_maske.Maske` (wortgleiche Kopie von `ris-mods/bruecke/ki_maske.py`, Gleichheit im Test geprüft) maskiert +
  Restprüfung, Antwort zurücksetzen; Rückfall auf Gemini bei Maske unsicher, fehlendem/erfundenem Platzhalter,
  unvollständiger/abgeschnittener Antwort, Ausfall, Frist 20 s; Nachdenken aus (Haiku `disabled`, Sonnet `between_tools`),
  kein `temperature` (beide Modelle lehnen es ab).
- EXE: `config.py` (`LLM_ANBIETER`, `LLM_ANBIETER_KORREKTUR`, `ANTHROPIC_MODELL`, `ANTHROPIC_FRIST`), `keys.py`
  (`anthropic_api_key`), `korrektur.korrigieren_ki`, `RaKScribe.py` (`KI_GEN`/`KI_KORR`), Build-Zeile (hidden-imports).
- Web: `kiMaske.ts` (TS-Port, 172/172 Fälle gleich zu Python), `llmAnbieter.ts`, Einbau in Call 0/1/2 in `gemini.ts`,
  Schlüssel aus der Praxis-Schlüsseldatei in `App.tsx`; ohne Einstellung bit-gleich wie bisher.
- Tests: `tests/offline/test_llm_anbieter.py`, `tests/offline/test_ki_maske_web.py`, `web_app/llm_anbieter_test.mjs` (im
  testlauf); Messwerkzeuge `tools/haiku_maske_probe.py`, `tools/haiku_ab_auswertung.py`; `tools/testkosten.py`: Claude-Weiche
  jetzt maskiert über die Produktionsfunktion (`KAISCRIBE_TEST_MASKE=0` = alt), Grenze je Konto
  (`KAISCRIBE_TEST_LIMIT_KONTO`), Lauf-Kennung im Kostenbuch, Haiku-Preis.

## Kosten dieses Jobs

Google (Testprojekt) 4,36 $ von 5 $, Anthropic Konto B 5,20 $ von 10 $. Tagesgrenze bewusst auf 18 $ gesetzt
(heute schon 2,16 $ von anderen Jobs). Rohdaten: `~/cj/work/kaiscribe-haiku-ab-n1/` (Logs, JSON je Runde, Suite-Ausgaben),
Kostenbuch `~/cj/work/testkosten/kaiscribe-haiku-ab-n1.jsonl` + `.weiche.jsonl`.

Offline-Gates: alle grün bis auf `test_cas_auftrag.py` und `test_maske_ablauf.py` – beide auch auf dem unveränderten main-Stand
rot, weil auf diesem Mac kein Python mit Tk ≥ 3.10 liegt (Umgebung, nicht Code).
