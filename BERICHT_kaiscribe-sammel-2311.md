# BERICHT kaiscribe-sammel-2311 – Markierung ersetzen (Nachtrag Peter 23.11.) + Karten #377, #344, #401, #202

Mo 23.11. 20:40 – Di 24.11. ~03:30, Hetzner + Büro-PC (außerhalb der Ordi-Zeit). Ein Paket: **KaiScribe 3.24.1**
(main d504f42, Release Latest = die abgenommene Vorabversion test-45304526742, sha256 `807131fc…0109452`).
Montagskontrollen gelesen (befundfeld-sicher ok + Lücke #518, frog ok, senf/georg/umzug ok) – nichts davon im Konflikt.

## Nachtrag (Vorrang): markierter Text im rechten Befundfeld wird ersetzt – erledigt
- Ursache (Log CASWS10 23.11., VM-Lesung): RH 156 – Markierung beim RECORD erkannt (33–615), in der Pause PLAY → Tk-„sel“
  weg, `_fortsetzen` las die neue Lage (Cursor am Markierungsende 615) als „in der Pause geklickt“ → eingefügt statt ersetzt.
  RH 165 – in der Pause markiert (216–251), danach wurde der markierte Text verändert (kein neuer Klick im Log), die Marken
  umfassten nur noch 2 Zeichen → 11 Zeichen dort eingefügt. Grund in beiden Fällen: KaiScribe kannte nur die flüchtige
  Auswahl „sel“ und nicht den markierten Text.
- Änderung (`source_code/RaKScribe.py`): jede Auswahl im Befund wird als eigener Tag `ks_markierung` festgehalten
  (sichtbar, `<<Selection>>`). Er geht nur weg durch einen echten Einzelklick ohne Auswahl im Befund (dann gilt der Cursor)
  oder durch eine neue Auswahl (die gilt dann). Beim Start und beim Weiter-Diktieren wird Stelle + Text festgehalten; ersetzt
  wird genau dieser Text (`markierung_stelle`: an den Marken, sonst das nächste wörtliche Vorkommen, sonst die Stelle der
  Marken + Hinweis „bitte prüfen (Strg+Z = zurück)“). Gilt mit SpeechMike-RECORD, Weiter-Diktieren und F10, auch ohne Fokus
  im Feld und im IB-Lab-Gerüst (dort wird nur die Markierung ersetzt, kein neuer Befund). IB-Lab-Neuschreiben des Felds
  (Gerüst aktualisiert, Werte nachgekommen) hält die Markierung. Status: „Ersetzt markierten Text (N Zeichen) · …“, Hinweis
  danach „Markierten Text ersetzt (N Zeichen)“, Log `[EINFÜGEN] Markierung ersetzt (gleich|wiedergefunden|veraendert)`.
  Ohne Markierung alles wie bisher (Ergänzung bzw. Cursor nur mit Fokus).
- Tests: neu `tests/offline/test_markierung.py` (25 Prüfungen: RH 156, RH 165, Klick, neue Markierung, veränderter Text,
  Gerüst, Neuschreiben) in der CI; Windows-UI-Test der EXE um beide Abläufe erweitert (grün, Lauf 45304736055).
- **Echter Lauf 451898** (Büro-PC 02:43–02:54, Werkzeug `tools/buero/markierung_abnahme.py` + ris-mods diktat_e2e 1.2.0,
  echte Spracherkennung aus WAV, Claude Sonnet 5.5, EOL → Brieftext abgelegt): **M156** (Ablauf Video RH 156) und **M165**
  (Ablauf Video RH 165) je 7/7 + `MARKABN=ok` – „Beginnende Gonarthrose“ (22 Zeichen) ersetzt durch „Mäßige Gonarthrose“, Rest
  Zeichen für Zeichen gleich, Status „Ersetzt markierten Text (22 Zeichen)“, `Weiter diktieren: Markierung (22 Zeichen) bleibt`.
  Einträge 20261124004/005/006 storniert, nichts vidiert, kein Gemini im Log. Abweichung: Ordi hat in einer KOPIE von
  diktat_e2e Zeile 998 um M156/M165 ergänzt (Ablage-Vergleich gegen den korrigierten Befund wie bei E4b); Original unverändert.

## #377 gehaltene Aufnahmen Sprunggelenk – erledigt (Karte fertig)
`cas_vorlagen.erweitert_von` + `abgleich`: CAS-Vorlage „<Grund-Vorlage> mit …“ gilt, wenn die Grund-Untersuchung diktiert
wird (allgemein: gehaltene Aufnahmen, „mit Fuß“, Patella axial). Titel z. B. „Sprunggelenk links in 2 Ebenen mit gehaltenen
Aufnahmen“, beidseits bei sgbg. Tests in `test_cas_leistungen.py` (+11). Kein echter sg*g-Fall seit 17.11. → Kontrolle.

## #344 Knie + Patella axial – erledigt (Karte fertig)
Echter Fall 20.11. (Diktat …20092, 3.19.15, kniepatr): Titel „Kniegelenk rechts in 2 Ebenen mit Patella axial“ (VM-Lesung).

## #401 AC-Gelenk-Satz – gebaut, Wortlaut bei Georg (Karte → Georg, Frist 27.11.)
Schulter-Normalbefund: „Das AC-Gelenk ist altersentsprechend, keine Luxation.“ (templates, taught_blocks, Prompt-Marker
`2026-11-24-ac-gelenk-artikel`); alte Form und Georgs Handform „Der AC-Gelenk …“ bleiben erkannt (`VORLAGEN_ALTFORMEN`
PY ≡ TS, Fixtures, test_pipeline_exe EXE + Web). Anderer Wortlaut = eine Zeile.

## #202 Mikrofon-Wache – erledigt (Karte fertig)
Wache scharf wie entschieden (a): seit 18.11. 20 J-Funde (7 Diktate), 0 Rücksetzungen, alle wegen offener Sitzung des Arztes
(kp@CASWS10 19×, rg@RAKCLIENT04 1×) – kein hängendes J aus KaiScribe; jetzt 1 J (RH 60, bekannt). Nebenbefund: 10× DB nicht
lesbar (Zeitüberschreitung/keine Verbindung), nichts zurückgesetzt.

## Einspielen / Rückweg
- Offline-Suite wie CI (63 Python-Dateien + 4 Node) grün, GitHub „Tests“ + Windows-UI-Test grün.
- X:-Tausch 3.22.5 → 3.24.1 per `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.24.1`: ok 03:15 (Sicherung
  `KaiScribe.exe.vor3.24.1-20261124-031504.alt`), Fenster + SM-Wächter 3.24.1, `[INIT] … Rückfall: aus`, 0 Fehlerzeilen.
  Der Autostart nach dem Tausch hielt den alten Wächter für „KaiScribe läuft schon“ → Fenster von Hand gestartet, Karte #541.
  Rückweg: `-Schritt zurueck` (.alt-Sicherung). 3.24.1 enthält auch 3.22.6/3.23.x/3.24.0 (kein Gemini-Rückfall).
- Wartender Job `sm-senf-laenge-n1-einspielen` (wollte 3.22.6/3.24.0 tauschen) hat einen Nachtrag: bei 3.24.1 live nicht
  zurücktauschen, nur belegen.
- Folgejob `kaiscribe-sammel-2311-kontrolle` (ab 24.11. 17:45, nur lesen): echte Ersetzungen im Log, #377/#401-Belege.
- Arbeitsdateien: `~/cj/work/kaiscribe-sammel-2311/` (Aufträge r1/r2, Antworten, tests.sh, gate.sh, version_hoch.sh).

👉 Georg: AC-Satz „Das AC-Gelenk ist altersentsprechend, keine Luxation.“ ok? (Karte #401), bis Fr 27.11.

## Kontrolle 24.11. (Job kaiscribe-sammel-2311-kontrolle, 25.11. 01:00–01:30, nur gelesen über Büro-PC + VM)
- Nicht rot, aber kein Beleg: an den Befund-PCs lief am 24.11. KEIN Befund über das KaiScribe-Fenster (142 Diktate rg/kp nur über SpeechMagic/Wächter; Läufe nur CASWS14-Testpatient 21:04–23:49). Geteiltes rakscribe.log: 0 `[EINFÜGEN]`-Zeilen, 0 Traceback/EXCEPTION.
- Versionen 24.11.: 3.25.0 ab 05:57 (CASWS08 2 Annahmen 09:34), 3.26.1 ab 12:42, 3.28.1 ab 23:43; Fenster + SM-Wächter jetzt 3.28.1 (alle ⊇ 3.24.1). CASWS10 ohne KaiScribe-Start (Brücke zuletzt 08:09) → #541.
- #377: 0 Läufe mit sglg/sgrg/sgbg. #401: 5 Schulter-Läufe (alle Test): 2× neuer AC-Satz (3.26.2), 0× alte Form, 3× ohne (Abnahmefälle mit AC-Befund).
- Wiederholung am ersten echten Tag: `FOLGEJOB-KAISCRIBE-SAMMEL-2311-KONTROLLE-F1.md` (ab 25.11. 17:45). Arbeitsdateien `~/cj/work/kaiscribe-sammel-2311-kontrolle/`.


## Kontrolle 25.11. (Job kaiscribe-sammel-2311-kontrolle-f1, 25.11. 18:05–18:15, nur gelesen über VM)
- Wieder kein Beleg, nicht rot: 06:00–18:04 an KEINEM Befund-PC ein KaiScribe-Fenster-Start (`[INIT]` 0), nur Wächter 3.28.2 (07:25/07:27, Abmeldung 16:53/18:04); 0 `[EINFÜGEN]`, 0 Traceback/EXCEPTION, 0 echte Läufe (nur 2 WAV-Tests 451898 01:42/01:47).
- Live ist 3.28.2 (Wächter-Nachfolger seit 25.11. 01:36). CASWS10 weiter ohne Fenster-Start → Notiz #541 (Starter, Job waechter-zaehlt-nicht-n2).
- #377: 0 sg*g-Läufe. #401: 0 Schulter-Läufe. Notizen auf #377/#401/#541.
- Letzter Versuch: `FOLGEJOB-KAISCRIBE-SAMMEL-2311-KONTROLLE-F2.md` (ab Do 26.11. 17:45), danach Karte „wartet auf ersten echten Fall“. Arbeitsdateien `~/cj/work/kaiscribe-sammel-2311-kontrolle-f1/`.
