# Bericht kaiscribe-befundfeld-sicher-n1 (Teil 1, Fr 20.11.2026 15:10–17:30, Hetzner): rechtes Befundfeld nie mehr still überschreiben

**Kurztext für Peter:** Ab KaiScribe 3.19.16 wird rechts nichts mehr gelöscht. Steht dort schon ein Befund, ist jedes Diktat eine
Ergänzung. Ohne Cursor im Feld kommt sie ans Ende des Befundteils, vor „Ergebnis“. Titel und Text bleiben, die Statuszeile sagt
beim Record „Ergänzung“ bzw. „Neuer Befund“. Einen neuen Befund gibt es nur bei leerem Feld (nach EOL, „Clear all“ oder F1).
Oben im BEFUND-Kopf gibt es drei neue Knöpfe: **Clear all** leert das Feld, der Fall bleibt offen. **Reset** holt den ersten
Befundvorschlag dieses Falls zurück. **Restructure** baut den Befund aus dem jetzigen Text neu auf. Was du dazudiktiert oder getippt
hast, hat dabei Vorrang: Widersprechende Normalsätze fliegen raus, das Ergebnis wird angepasst und der Titel bleibt. Fehlt danach
etwas, erscheint eine rote Prüfzeile. Nach jedem Schritt holt Strg+Z im Befundfeld den Stand davor zurück. Die SpeechMike-Tasten
sind unverändert. 3.19.16 ist gebaut und nach main gepusht. Eingespielt wird erst nach dem Abendauftrag mit Abnahme am
Testpatienten 451898; bis dahin läuft in der Ordi weiter 3.19.15.

## 1. Ursache (Code 41893b4, ohne Büro-PC; belegt am Code und in den Offline-Tests)
- `RaKScribe._einfuege_ziel_ermitteln` hat nur dann an der Cursor-Stelle eingefügt, wenn beim Record der Tastaturfokus im Befundfeld
  lag **und** KaiScribe das Vordergrundfenster war. Im IB-Lab-Gerüst hat es das nie getan. In allen anderen Fällen hat
  `_aufnahme_umschalten` das Feld beim Start geleert, und `process_dictation` hat einen kompletten Neubefund mit neuer Überschrift
  erstellt. Ein kurzer Klick in Plaza/CAS (Fokus weg) genügte dafür, deshalb wirkte es „zufällig“.
- Zwei weitere Wege führten zum selben Ergebnis:
  - **SpeechMike-Nachdiktat:** Record nach INS, dann wieder INS. Das baute den Befund aus dem Gesamtdiktat neu, Handänderungen gingen
    verloren und der Titel konnte wechseln.
  - **Zweites INS ohne neue Aufnahme:** Es lief `befund_aus_text` mit dem alten Diktat. Das Modell antwortet nicht immer gleich, also
    kam unter Umständen ein anderer Titel heraus.
- Die Web-App verhielt sich gleich (`startRecording` leerte das Feld ohne Cursor, `befundAusText` ebenso).
- **Lücke:** Peters konkreten Fall habe ich nicht im Ordi-Protokoll nachgesehen, weil der Büro-PC in diesem Lauf tabu war. Steht im
  Folgeauftrag: dort `[EINFÜGEN]`/`[RECORD]`-Zeilen in `X:\RaKScribe\rakscribe.log` lesen, ab 3.19.16 zusätzlich `[BEFUNDFELD]`.

## 2. Umsetzung (Release 3.19.16, EXE ≡ Web)
- **Neues Modul `source_code/befundfeld.py` ≡ `web_app/src/befundfeld.ts`:**
  - `modus()` legt fest, was ein Diktat tut: neu / Ergänzung / Cursor / Gerüst / Maske.
  - `ergaenzen()` hängt ans Ende des Befundteils des passenden Abschnitts an. Gewählt wird nach Region und Seite der Ergänzung, sonst
    der letzte Abschnitt. Text ohne Abschnitte (Nur Text) wird angehängt bzw. vor einer Zeile „Ergebnis“ eingefügt.
  - `vorrang()` liefert den Diff zum letzten KaiScribe-Stand, also Peters diktierte oder getippte Sätze.
  - Dazu kommen die Restructure-Bausteine `umbau_segment`, `umbau_block`, `titel_uebernehmen`, `streichen` sowie die Prüfungen
    `fehlende`, `ergebnis_fehlt` und `verneint_vorrang`.
- **Ergänzung:**
  - Das neu Diktierte wird wie bei „Nur Text“ korrigiert (Fehlhör-Liste, Call 0, Satzbausteine) und eingebaut, ohne Befund-KI. Titel
    und übriger Text bleiben Zeichen für Zeichen.
  - Mit Cursor oder Markierung bleibt alles wie bisher (an der Stelle bzw. ersetzt).
  - Statuszeile: „Ergänzung · Aufnahme läuft“ bzw. „Neuer Befund · Aufnahme läuft“, „Neuer Befund (IB-Lab-Gerüst)“.
  - Protokollzeile `[BEFUNDFELD] Record: …` ohne Diktatinhalt.
- **IB-Lab-Gerüst:**
  - Das Gerüst bleibt beim Record sichtbar (früher war es sofort leer). Das Diktat baut es zum Befund aus, die IB-Lab-Texte setzt
    `ibl_anwenden` wie bisher wörtlich in den passenden Befund. Jedes weitere Diktat ergänzt.
  - Scheitert die KI, kommt das Gerüst zurück statt „… Befund wird geladen …“.
- **Neuer Befund** gibt es nur bei leerem Feld, nach Clear all, F1/F9 Neu oder EOL. Zwei Ausnahmen zählen wie EOL:
  - Ein unvollständiger Mehr-Regionen-Befund, unberührt: Er wird wie bisher neu diktiert.
  - **F10 ohne CAS-Band, Befund schon automatisch kopiert/eingefügt:** Das ist der nächste Patient. Ohne diese Regel wäre im
    F10-Ablauf der neue Patient in den alten Befund ergänzt worden. Strg+Z holt den alten zurück.
- **SpeechMike-INS ohne neue Aufnahme** baut einen stehenden Befund nicht mehr still neu:
  - nichts geändert → „Befund steht schon rechts – EOL schickt ihn weiter“;
  - rechts von Hand geändert → „Restructure baut ihn neu, F1 = Neu“;
  - nur links das Diktat geändert → wie bisher neu, aber mit Strg+Z.
- **Knöpfe im BEFUND-Kopf** (per Maus, SpeechMike-Belegung unverändert):
  - **Clear all:** rechts und das Diktat links leeren. Ohne das Diktat links würde Record es als Nachdiktat-Basis mitnehmen.
    Fall/Band/Diktatnummer bleiben, das nächste Diktat wird ein neuer Befund.
  - **Reset:** erster Befundvorschlag dieses Falls. Das ist der Stand nach dem ersten INS; vor dem ersten Diktat ist es das
    IB-Lab-Gerüst. Der Stand wird bei Fallwechsel, EOL und F1 verworfen. Clear all behält ihn, Reset funktioniert danach also noch.
  - **Restructure:** `pipeline.befund_umbauen` ≡ `pipeline.ts befundUmbauen`:
    1. Peters Sätze seit dem letzten KaiScribe-Stand (Diff) gehen als `<umbau>`-Vorrang an das Modell. Sie stehen an derselben
       Stelle wie `<widersprueche>` und laufen über dieselbe Kette wie der Befund (EXE: Sonnet maskiert, Rückfall wie gehabt; voller
       Regel-Prompt, alle Wächter).
    2. Widersprechende Normalsätze nach dem Widerspruchs-Katalog nimmt KaiScribe vorher heraus und lässt sie nicht wörtlich zurück.
    3. Die Überschriften bleiben. Abschnitte ohne Änderung bleiben bei Mehrfachbefunden Zeichen für Zeichen.
    4. Danach wird geprüft:
       - Fehlt eine Angabe von Peter, wird sie wörtlich nachgetragen und es kommt eine rote Prüfzeile.
       - Fehlt eine eigene Angabe des alten Textes, kommt eine Prüfzeile. Ausnahme: Peter hat das Gegenteil ergänzt (z. B. „Kein
         Hinweis auf eine Fraktur“ gegen eine ergänzte Fraktur).
       - Fehlt eine Pathologie von Peter im Ergebnis, kommt die Prüfzeile „… nicht im Ergebnis – bitte prüfen“.
    5. Das Ergebnis geht nur zur Kontrolle ins Feld und nie per Strg+V hinaus. Wurde während des Laufs getippt, wird nichts ersetzt.
- **Strg+Z** im Befundfeld (EXE: Tk-Bindung, Web: beide Ansichten): Stand vor dem letzten KaiScribe-Schritt (Diktat, Ergänzung,
  Clear all, Reset, Restructure). Noch einmal Strg+Z bringt den neueren Stand zurück, es geht also nichts verloren.
- **Regeln:**
  - Kein Prompt-Satz entfernt. `radiology_prompt.txt` ist unverändert, der Umbau-Hinweis kommt nur beim Restructure dazu.
  - Im Widerspruchs-Katalog (`vorlagen_vorrang.json`, Merkmal „struktur“) ist „unauffällige/regelrechte/normale/homogene …
    Spongiosa“ als Normalsatz dazugekommen (Peters Beispiel). Das Regel-Register und die Widerspruchs-Matrix sind grün.

## 3. Tests
- **`tests/offline/test_befundfeld.py`** (neues GitHub-Gate):
  - 26 gemeinsame Fälle `snapshots/befundfeld_faelle.txt`, darunter 11 Restructure-Fälle mit fester KI-Antwort über die ganze Kette.
    Web `pipeline_test.mjs` liefert genau dasselbe (91/91).
  - EXE-Abläufe:
    - Ergänzung ohne Fokus: Titel und Text bleiben, keine KI. Mit F10 ebenso.
    - F10-Befund schon kopiert → neuer Befund.
    - Mit Cursor, mit Markierung.
    - Leeres Feld → „Neuer Befund“.
    - Zwei Ergänzungen, dann Reset → erster Vorschlag, Strg+Z.
    - Restructure-Knopf (Vorrang im Prompt, Titel bleibt, Kontrolle statt Einfügen, ohne Änderung kein KI-Aufruf).
    - Clear all → nächstes Diktat neu; F1 Neu.
    - Doppel-INS und INS nach Handänderung.
    - IB-Lab-Gerüst + Diktat (Gerüst beim Record sichtbar, KOALA-Text bleibt, danach Ergänzung).
    - KI-Fehler → Gerüst zurück.
  - Restructure-Fälle:
    - Enostose ↔ „Unauffällige Spongiosa“;
    - Erguss ändert das Ergebnis;
    - Ergebnis bleibt normal → Prüfzeile;
    - verlorene Angabe → Nachtrag + Prüfzeile;
    - Mehrfachbefund mit K&L-Tabelle unberührt;
    - K&L-Befund + Ergänzung;
    - Kinder-Befund (Wachstumsfugen);
    - ergänzte Fraktur.
- Angepasst wurden zwei alte Prüfungen, die das alte Verhalten festschrieben („ohne Cursor: neuer Befund ersetzt den alten“,
  „Nachdiktat: INS baut aus dem Gesamtdiktat neu“): `test_einfuegen.py`, `test_speechmike_ablauf.py` 6.
- **Alle Offline-Gates sind grün:** 55 Python-Dateien aus `test.yml`, 4 Web-Suiten, tsc und eslint. Für tsc/eslint liegen die
  `node_modules` hier unter `~/cj/work/kaiscribe-befundfeld-sicher-n1/web_deps`. Lauf unter der Push-Sperre vor e004365.
- **Live, echte anonymisierte Diktate** (RH 38, RH 99, Erhalt-Knie aus den Ordi-Fällen + 3 kurze), Claude Sonnet 5.5 maskiert wie in
  der Produktion (`KAISCRIBE_TEST_ROUTE=alle=claude-sonnet-5-5`, Testkonto B):
  - `tools/verify_restructure.py 2` ergibt **12/12 PASS**.
  - Kosten des Jobs: 0,41 $ von 5 $.
  - Vorher/Nachher vollständig in `docs/benchmarks/restructure_live_20261120.md` (+ .json). Lauf 1 kurz:

| Fall (Ergänzung von Peter) | weg | neu |
|---|---|---|
| Knie unauffällig + „Enostose im distalen Femur von 6 mm.“ | „Mineralgehalt und Knochenstruktur sind regelrecht.“, Ergebnis „Regelrechte Darstellung …“ | „Mineralgehalt regelrecht, im Übrigen regelrechte Knochenstruktur, abgesehen von einer Enostose …“; Ergebnis „Enostose im distalen Femur links von 6 mm.“ |
| RH 38 (mediale Spaltverschmälerung) + „Kleiner Gelenkerguss im Recessus suprapatellaris.“ | „Unauffällige Weichteile.“ | Erguss im Befund; Ergebnis 1. Spaltverschmälerung, 2. Erguss links |
| Erhalt-Knie (Gonarthrose Grad 3) + „Zusätzlich Chondrokalzinose des Außenmeniskus.“ | „Keine … Verkalkungen.“ | K&L-Tabellensatz Grad 3, Chondrokalzinose im Befund; Ergebnis 1. Gonarthrose (Grad 3 …), 2. Chondrokalzinose rechts |
| RH 99 (Becken) + „Alte, knöchern konsolidierte Fraktur des oberen Schambeinasts rechts.“ | „Kein Hinweis auf eine Fraktur.“, Form/Kontur-Normalsätze | „Im Übrigen kein Hinweis auf eine Fraktur.“; Fraktur im Befund und Ergebnis |
| Schulter unauffällig + „Kalkdepot im Verlauf der Supraspinatussehne von 8 mm.“ | „Keine Kalzifikationen im Bereich der Rotatorenmanschette.“, Normal-Ergebnis | Ergebnis „Kalkdepot … von 8 mm rechts.“ |
| Knie + Hand (Mehrfach) + „Hand links: Rhizarthrose.“ | Gelenkflächen/-spalten-Normalsätze der Hand | Knie-Abschnitt Zeichen für Zeichen gleich; Hand: „Rhizarthrose links.“ in Befund und Ergebnis |

## 4. Verteilung / Stand
- main: 1366f72 (Änderung) + **e004365 v3.19.16**.
- GitHub für e004365, alle **grün**: Tests 44768754202, Build Windows EXE 44768796212 (per API mit Tag 3.19.16 angestoßen),
  Windows-UI-Test 44769262757, Pages-Deploy 44769450198. Die Web-App 3.19.16 ist damit seit ~17:04 auf Pages, wie bei jedem Release.
- Release **3.19.16**: `rakscribe26.exe`, 56 584 815 Byte, sha256 `1f7dc090bbfdb6ea706360bd355686db39ce1c953b8af24227527618505ba8a0`.
- Eingespielt ist **noch nichts**: Die Befund-PCs laufen mit 3.19.15. Einspielen und Abnahme stehen im Abendauftrag (Abschnitt 6),
  erst danach „live“.

## 5. Offen / Hinweise
- **Abnahme am Testpatienten 451898** mit IB-Lab-Baustein, Text im Brief belegt: Abendauftrag. Ohne Beleg wird zurückgerollt und
  nichts als live gemeldet. Danach den **ersten echten Fall am nächsten Ordi-Morgen** prüfen (`[BEFUNDFELD]`-Zeilen im
  rakscribe.log, kein Diktatinhalt).
- Browser-Sichtprüfung der Web-Knöpfe ist hier nicht möglich (kein Browser am Server). Dafür sind tsc, eslint und die Web-Logik
  (91/91) grün.
- **Vorschlag für SpeechMike-Tasten** (nicht umgesetzt, Belegung bleibt): INSTR (heute unbelegt) = Restructure. F3 außerhalb der
  Mammo-Maske = Strg+Z (Schritt zurück). „Clear all“ bewusst nur per Maus, weil man es nicht versehentlich drücken soll.
- **Auslegung, bitte bei Bedarf korrigieren:**
  - „Reset“ vor dem ersten Diktat = IB-Lab-Gerüst, danach der erste Befund.
  - „Clear all“ leert auch das Diktat links.
  - F10-Befund, der schon automatisch kopiert wurde, zählt wie EOL.

## 6. Folgeauftrag
- **`kaiscribe-befundfeld-sicher-n1-einspielen`** eingereiht (Brief `FOLGEJOB-KAISCRIBE-BEFUNDFELD-SICHER-N1-EINSPIELEN.md`),
  Ressource ordi + automaten-vm. Kein not-before, weil Freitag nach 13:35; die Tauschsperre des Skripts gilt Mo–Fr bis 20:10.
  Er macht die Abnahme an 451898 mit KOALA-Baustein, belegt den Text im Brief, tauscht und schließt die Log-Lücke aus Abschnitt 1. Den
  Kontroll-Auftrag für den ersten echten Fall (Mo 23.11.) reiht er selbst ein, die Meldung an Peter kommt erst nach „belegt live“.
- **Abweichung von der Bündel-Regel:** In der Queue wartet `kaiscribe-squirrel-ergebnistext-n1-einspielen`. Er gehört zum Repo
  ris-mods und startet laut seinem Bericht erst nach `kaiscribe-squirrel-ergebnistext-n1-kaiscribe`. Dieser KaiScribe-Bau war um
  17:00 wegen eines Login-Problems am Mac pausiert und hatte noch nicht angefangen. Ein Nachtrag dort hätte 3.19.16 auf unbestimmte
  Zeit blockiert. Der eigene Folgeauftrag hat den Hinweis, sich abzustimmen: Laufen beide am selben Abend, wird nur die neueste Version
  getauscht, mit einer gemeinsamen Abnahme.
- Arbeitsdateien: `~/cj/work/kaiscribe-befundfeld-sicher-n1/` (gates.sh = alle Offline-Gates, version.sh, web_deps = node_modules für tsc/eslint).
