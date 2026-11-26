# kaiscribe-kosten-je-befund-n1 – Warum KaiScribe ~6 ct statt ~1,5 ct je Befund kostet – 25.11.2026

**Kurz:** Der Zwischenspeicher (Prompt-Cache) war im Betrieb **nie aktiv**. Die EXE wird auf einem Windows-Rechner
gebaut. Dort bekommt `radiology_prompt.txt` Windows-Zeilenenden (CRLF). Dadurch fand `llm_anbieter.fester_anfang()`
die Grenze `<normalbefund_template>\n` nicht und gab "" zurück. Ohne `cache_control` gingen die ganzen Regeln
(heute 29.203 Token) bei jedem Befund zum vollen Preis hinaus. In allen Tests (Linux/Mac, LF) griff der Cache, deshalb
fiel es dort nicht auf. Behoben in diesem Job: Der Prompt wird beim Laden auf LF gestellt, `fester_anfang` findet die
Grenze auch mit CRLF, und `.gitattributes` hält die Datei auf LF. Ergebnis an denselben synthetischen Fällen:
**6,68 ct → 1,39 ct je Befund-Aufruf** (Cache-Treffer). Hochrechnung bei 3.000 Befunden im Monat: **≈ 200 $ → ≈ 50 $.**

## 1. Betrieb gemessen (X:\KaiScribe\Daten\nutzung, über die Automaten-VM, nur Zahlen)

| | Wert |
|---|---|
| Zeitraum | 16.–25.11.2026, alle PCs |
| Befunde (Rolle gen) / Claude-Aufrufe | 160 / 179 (die 19 zusätzlichen sind Call-0-Korrekturen, Rolle korr) |
| Anthropic laut Zähler | 9,57 $ → **5,34 ct je Aufruf**, ≈ 5,9 ct je Befund |
| Einzelne Befunde an ruhigen Tagen (kein Cache möglich) | 4,8–6,1 ct (CASWS08 17.11., CASWS14 18.11., RAKCLIENT04 19.11.) |
| Dichte Tage | 23.11. CASWS08: 57 Aufrufe 5,57 ct; 20.11. CASWS10: 61 Aufrufe 4,94 ct |
| Zweite Versuche / ohne KI | 0 / 0 (Rückfälle auf Gemini: 2, 18.11. und 23.11., damals noch KI_RUECKFALL = an) |

Wenn der Cache gearbeitet hätte, wären dichte Tage deutlich billiger als einzelne Befunde (Treffer ≈ 1,4 ct). Ein
Neuschreiben des Caches hätte ≈ 12,8 ct gekostet. Gemessen wurde aber an **allen** Tagen gleich viel, nämlich genau der
Preis „ganz ohne Cache“. Der Aufschlag des Prompts im Zeitraum (40,8k → 55,8k Zeichen, 16. → 24.11.) erklärt, warum der
Mittelwert (5,34 ct) unter dem heutigen Stand (6,68 ct) liegt.

**Beleg an der echten EXE** (`tools/vm/exe_prompt_zeilenenden.py`, liest das PyInstaller-Paket von
`X:\RaKScribe\rakscribe26.exe` = 3.28.2, gibt nur Zahlen aus):
`bytes=56016 crlf=226 lf_gesamt=226 marke_lf=False marke_crlf=True version=2026-11-24-ac-gelenk-artikel`.
Alle 226 Zeilenenden sind CRLF, die LF-Marke fehlt. Ursache: `.gitattributes` `* text=auto` + Runner `windows-latest`
(core.autocrlf = true) → Checkout mit CRLF → `--add-data "../radiology_prompt.txt;."`. `keys.read_text_robust()` behält CRLF.

## 2. Ursachen geprüft – Anteil an den 5,34 ct je Aufruf

Aufteilung nach der Token-Struktur der Live-Probe (unten). Im Mittel: Regel-Anfang 29.203 Token, Rest 1.838 Token,
Antwort 472 Token. Diese Anteile sind auf die 5,34 ct des Betriebs umgelegt.

| Ursache (Auftrag) | Befund | Anteil an 5,34 ct | Beleg |
|---|---|---|---|
| **a) fester_anfang() = "" im EXE-Weg** | **ja, bei jedem Befund-Aufruf** (CRLF im gebündelten Prompt) | **≈ 4,2 ct (79 %)** Mehrkosten. Die Regeln liefen zu 2 $/Mio statt 0,20 $/Mio | EXE-Prüfung oben; Probe „vorher“: 8/8 Aufrufe `cache_control` fehlt, `cache_read=0`, `cache_write=0` |
| a) je Weg/PC/Version verschieden? | nein. Ein einziger Anfang für 26 Vorlagen + Hinweis-, Widerspruch-, CAS- und IB-Lab-Block (alle stehen hinter der Grenze). Rho (Auslöser wird vor gen_prompt entfernt), Mehrfachdiktat (je Abschnitt derselbe Prompt) und Bausteine (KI-Hinweis über `hinweise`) ändern ihn nicht. Ein lokaler `radiology_prompt(_v4).txt` neben der EXE wird jetzt genauso normalisiert. | 0 | `tests/offline/test_kosten_cache.py` |
| b) Denken trotz `between_tools` | **nein.** Die Antwort enthält nur `text`-Blöcke. 290–700 Output-Token passen zur Textlänge. | 0 | Probe: `typen=['text']` in 16/16 |
| c) ungecachter Rest (Vorlage, Beispiele, Blöcke, Diktat) | 1.400–2.230 Token (Mittel 1.838) | ≈ 0,29 ct (5 %). Gleich viel wie im Test, nicht die Ursache | Probe `input_tokens` nachher |
| Antwortlänge | 290–700 Token (Mittel 472) | ≈ 0,37 ct (7 %). Gleich viel wie im Test | Probe `output_tokens` |
| Regel-Anfang, der auch mit Cache bleibt (Lesen 0,1 ×) | – | ≈ 0,46 ct (9 %) | Rechnung |
| d) neue Version/Prompt → Cache neu | im Betrieb **0 ×**, weil es gar keinen Cache gab. Prompt-Stände im Zeitraum: 5 (16., 18., 20., 23., 24.11.), EXE-Stände ~25 | 0. Nach dem Fix kostet jeder neue Stand höchstens ein Neuschreiben (≈ +11 ct) je Stunde mit Pause | LAUF-Zeilen der VM; Prompt-Marker in git |
| e) zweite Versuche / Rückfälle | 0 zweite Versuche. 2 Rückfälle auf Gemini (deren verworfene Claude-Antwort war bisher **nicht** in den 9,57 $, also ≈ +0,12 $ zusätzlich) | 0 | Zähler `zweitversuch=0`. Neu: `verworfen` zählt mit |
| Korrektur-Aufrufe (Call 0, 19 ×) | eigener kurzer Prompt aus dem Code (LF) → gecacht | < 0,1 ct | – |

## 3. Behoben (Prompt-Wortlaut und Regel-Register unverändert)

- `befund_regeln.prompt_normalisieren()`: `waehle_prompt()` (eingebaut + lokale Dateien) liefert immer LF. Auch der
  Prompt-Editor normalisiert. Danach ist der feste Anfang der EXE **bytegleich** zu dem der Tests (in denen Qualität
  und Regeln seit sonnet-n2 abgenommen wurden).
- `llm_anbieter.fester_anfang()` findet die Grenze auch mit CRLF (zweite Sicherung). `web_app/src/llmAnbieter.ts` ist
  gleich gezogen; das Web baute schon immer mit LF und ändert sich im Verhalten nicht.
- `.gitattributes`: `radiology_prompt.txt text eol=lf` → auch der Windows-Checkout bündelt LF.
- Nebenwirkung des Fehlers, jetzt weg: Im CRLF-Weg ging auch der Regeltext durch die Maske (ein Datum der Regeln
  wurde ⟦D…⟧). Jetzt gehen die Regeln wie geplant unmaskiert und gecacht hinaus (sie enthalten nie Patientendaten).
  Vorlage, Blöcke und Diktat sind weiter maskiert, die Maskierung selbst ist unverändert.
- Modell (claude-sonnet-5-5), Denken aus, 1-h-Cache, Frist und Regeln sind unverändert.

**Messen (Auftrag 1):** `nutzung.Zaehler.ki()` speichert je Tag `token` = {input, cache_lesen, cache_schreiben_5m,
cache_schreiben_1h, output} und `cache` = {treffer, neu, ohne}. Verworfene, aber bezahlte Antworten zählen als
`ki.verworfen` in $ und Token mit, nicht als Befund. Der Tagesbericht hat eine neue Zeile „Claude-Token heute … Cache-Treffer a,
neu b, ohne c, verworfen d, ≈ x ct je Aufruf; Monat: …“. `tools/vm/kaiscribe_nutzung_lesen.py` gibt dazu je PC/Tag
`tok_in … cache_treffer cache_neu cache_ohne verworfen zweitversuch ohne_ki` aus. Nur Zahlen, nie Text, Nr oder Benutzer.
**`cache_ohne` > 0 bei Befund-Aufrufen ist ab jetzt das Warnzeichen.**

## 4. Vorher/nachher an denselben synthetischen Fällen (Live, Testkonto B, 0,72 $)

`tools/kosten_probe.py --laeufe 2 --faelle 4`: EXE-Kette (`pipeline.befund_aus_diktat`) mit Sonnet 5.5 maskiert,
4 Fälle (HWS, LWS, BWS aus `test_all_regions`, Thorax mit Vergleichsdatum) × 2 Läufe. „vorher“ = CRLF-Prompt mit dem
alten `fester_anfang` (= EXE bis 3.29.0), „nachher“ = nach dem Fix. Rohdaten: `~/cj/work/kaiscribe-kosten-je-befund-n1/probe.json`.

| | Aufrufe | Input ungecacht | Cache lesen | Cache schreiben 1h | Output | $ je Aufruf |
|---|---|---|---|---|---|---|
| vorher | 8 | 31.041 | 0 | 0 | 472 | **6,68 ct** (6,41–6,93) |
| nachher, Cache-Treffer | 7 | 1.838 | 29.203 | 0 | 478 | **1,39 ct** (1,17–1,65) |
| nachher, erster Aufruf (Neuschreiben) | 1 | 2.234 | 0 | 29.203 | 699 | 12,83 ct |

**Text:** Nicht bytegleich. Sonnet 5.5 nimmt keine Temperatur an, und schon zwei Läufe *derselben* Variante weichen
voneinander ab (vorher0 ≠ vorher1 in 4/4 Fällen). Die Unterschiede zwischen vorher und nachher sind von derselben Art
und Größe: Wortwahl wie „Keilwirbel“ / „Keilförmige Deformierung“, Satzreihenfolge, „Im Übrigen“ / „Die übrigen“, beim
Thorax ein oder zwei Ergebnispunkte. Inhalt: **alle erwarteten Pathologien und das Vergleichsdatum in 16/16 Läufen da**,
keine Platzhalter-Reste. Die Qualitätsabnahmen seit sonnet-n2 (1049 Aufrufe, alle Verify-Skripte) liefen schon immer
mit dem LF-/Cache-Weg. Der Fix bringt die EXE also auf genau den Stand, der geprüft wurde.

## 5. Neue Hochrechnung (3.000 Befunde/Monat, API-Guthaben Konto A 200 $)

| | je Befund | Monat |
|---|---|---|
| bisher, Betrieb 16.–25.11. (kleinerer Prompt) | ≈ 6,0 ct | ≈ 180 $ |
| bisher mit heutigem Prompt (55,8k Zeichen) | 6,7 ct | **≈ 200 $ (= ganzes Guthaben)** |
| **nach dem Fix**: 1,39 ct + ~3 Neuschreibungen je Ordi-Tag (≈ 7,5 $/Monat) + Call 0 (≈ 1–2 $) | ≈ 1,7 ct | **≈ 50 $** (45–60 $ je nach Pausen > 1 h) |

## Offene Punkte

- **Gebaut:** Release 3.29.1 (Fix + Zähler) und **3.29.2** (zusätzlich zeigt die Logzeile `[KI] gen: … maskiert (… s,
  n Platzhalter, Cache treffer|neu|ohne)` den Cache-Status). Asset `KaiScribe.exe`/`rakscribe26.exe` 56.795.191 B,
  sha256 `a32c0f731bd33760975209aa041cece75a390de762d3a27d5c9b6abc1bf6543c`. CI grün: Tests, Build Windows EXE,
  Windows UI-Test (EXE) für 3.29.1 und 3.29.2 (Lauf 45703744315). Pages-Deploy für a36474d ist grün (das Web ändert
  sich im Verhalten nicht).
- **Noch nicht eingespielt:** Einspielen und Abnahme an 451898 (echter Lauf, nie vidieren; zwei Diktate, das zweite muss
  `Cache treffer` zeigen) macht der Folgeauftrag `kaiscribe-kosten-je-befund-n1-einspielen`
  (`FOLGEJOB-KAISCRIBE-KOSTEN-JE-BEFUND-N1-EINSPIELEN.md`). Er läuft nach dem DEXA-Tausch, sodass nur einmal mit der
  neuesten Version getauscht wird. Beleg am Tag danach: Tagesbericht-Zeile „Claude-Token“ mit `Cache-Treffer` ≫ `neu`
  und `ohne 0`.
- Schon auf main rot, nicht durch diesen Job: `test_testkosten` (Übungs-E2E) und `test_ibl_nur_auffaellig` (PANDA-Snapshot)
  → Karte #578 (tun). `test_buero_anthropic` (Frist 20 → 45 s veraltet) ist hier behoben.
- Testkonto B steht diesen Monat bei ≈ 149 von 150 $ (fast alles aus anderen Jobs). Weitere Live-Tests im November
  sind kaum möglich.

## Einspielen 3.29.2 – Stand 26.11. (Nacht auf Do, 02:37)

Nicht ausgeführt: Ordi-Systeme sind Mo–Do erst ab 17:30 frei (Fr ab 13:30, Wochenende); der Lauf startete Do 02:37, also
vor dem Fenster. Weder Abnahme an 451898 noch Tausch noch Beleg im Betrieb wurden gemacht, nichts an Ordi angefasst.
Offen bleibt: A (Tausch 3.29.2 nach 20 min Ruhe, Rollback `.alt`), B (zwei Diktate, 2. muss `Cache treffer` zeigen,
stornieren), C (Betriebsbeleg am Folgetag). Hinweis: Der letzte Tausch (3.29.0) scheiterte an belegter X:-EXE.

## Einspielen 3.31.0 – Stand Fr 27.11.2026 00:35 (enthält 3.29.2)
Abnahme 451898 (Kopie 3.31.0, Konto A): Diktat N1 `Cache neu` (23:47:47), Diktat A1 33 s später **`Cache treffer`** (23:48:17), kein `Cache ohne`. X: seit 00:35 auf 3.31.0 live (EXE-Prüfung am Asset: crlf=0).
Offen: Betriebsbeleg (Teil C) am nächsten Ordi-Tag ab 17:30 bzw. Fr ab 13:30 – eigener Kontroll-Folgejob `FOLGEJOB-KAISCRIBE-KOSTEN-KONTROLLE-N1.md`; dort Nachtrag „Betrieb nach dem Fix“ inkl. Hochrechnung 3.000 Befunde/Monat.
