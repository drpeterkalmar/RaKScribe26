# Bericht kaiscribe-lektor-einbau-n1-einspielen (Teil 2): Abnahme bestanden, Tausch auf 3.32.0 NICHT erfolgt

Stand Fr 27.11.2026 01:15. Live in der Ordi läuft weiter **3.31.0**. Der Lektor-Schalter ist nicht angelegt (fehlt = aus).

## A. Vorbedingung
CI für 3.32.0 grün (laut Folgeauftrag); Asset 56.867.985 B, SHA256 `a3aeeece…70f206` auf dem Büro-PC bestätigt.

## B. Abnahme an 451898 (Kopie 3.32.0 als Gast, Befunder kp, Quelle 42ba193) – alle drei `LKABN=ok`
- **L0** (Schalter aus, Nr 20261127005): `GESTARTET=nein`, Brief = Feld bei INS, `[KI] gen: … Cache treffer`.
- **L1** (Schalter an, Diktat 1, Nr 20261127006): `GESTARTET=ja FERTIG=ja UEBERNOMMEN=0 PRUEFZEILEN=4`; die vier Prüfzeilen stehen rot in der Hinweiszeile („… (Lektor) – bitte prüfen“), nicht im Brief; Brief = Feld nach dem Lektor. Der Lektor meldete u. a. den Seitenwiderspruch rechts/links im Diktat.
- **LS** (EOL sofort, Nr 20261127007): `GESTARTET=ja FERTIG=nein`, „bei EOL noch nicht fertig … Befund unverändert“, Brief = Feld bei INS.
- Anmerkung: `E2E_EXIT=1` bei L1/LS kommt von der Prüfung „Befund rechts nach INS“ des E2E-Werkzeugs: Diktat 1 widerspricht sich (rechts/links), die Befund-KI hat darum zusätzlich einen Abschnitt „links“ gebaut. Das ist nicht der Lektor-Einbau.
- `[INIT] Lektor: claude-opus-5-5 (lektor-2) … nur kp/rg, 52 Register-Wortlaute, 2017 Vorlagensätze`.
- Seitenbild: keins (diktat_e2e hat keine Screenshot-Option; Hinweiszeile ist per Prüfung `pruefzeile_rot_im_fenster=ja` belegt).
- Aufgeräumt: alle drei Einträge storniert, nichts vidiert (`VIDIERT=0`), Kopie-config.ini `LEKTOR_DATEI = aus`, `X:\KaiScribe\Daten\lektor.json` nicht angefasst/nicht vorhanden. Letzte Ablage 00:50.

## C. Tausch: gescheitert an „nicht umbenennbar“ (belegt), nichts geändert
`kaiscribe_x_tauschen.ps1` 2.1, 01:12: `KS_TAUSCH=belegt SCHRITT=exe X:\KaiScribe\Programm\KaiScribe.exe nicht umbenennbar (an einem anderen PC offen?)`.
Halter laut Restart Manager: nur der SM-Wächter **3.31.0** am Büro-PC (PID 28828/37636, `--sm-waechter --nachfolger`, seit 00:37). Beim 3.31.0-Tausch (00:35) war der Halter noch der Wächter 3.28.2, der die EXE nicht blockierte; der 3.31.0-Wächter blockiert sie (Ursache offen). Der Wächter endet nur bei neuer EXE (setzt die Umbenennung voraus), bei SM_SENF/SM_IBL aus (Live-config.ini, nicht erlaubt) oder bei Windows-Abmeldung. Nichts erzwungen, nichts beendet. X: unverändert (beide EXE noch SHA `b1262bd7b655`, keine .neu/.alt), RL ohne neue Fehler, kein Rollback nötig. Lektor-Schalterdatei nicht angelegt (nur nach erfolgreichem Tausch vorgesehen).

## Offen / Folgejob
`FOLGEJOB-KAISCRIBE-LEKTOR-EINSPIELEN-TAUSCH-N2.md`: Tausch lösen (Wächter-Halter klären, z. B. Umbenennen mit anderem Weg, Wächter bekommt einen Stopp-Weg per Datei, oder die Büro-PC-Sitzung wird in der Nachtzeit abgemeldet), dann Tausch + Schalter-Datei AUS. Danach `kaiscribe-lektor-scharf-n1`.

## Abschluss
KaiScribe 3.32.0 mit lektor wurde an 451898 abgenommen: ohne Schalter wie bisher (L0), mit Schalter fand der Lektor 4 Prüfstellen und zeigte sie rot nur in der Hinweiszeile (L1), bei sofortigem Fertig bleibt der Befund unverändert (LS). Eingespielt ist 3.32.0 aber noch nicht: Der Austausch der Programmdatei auf X: scheitert, weil der unsichtbare SpeechMagic-Wächter 3.31.0 am Büro-PC sie festhält. Nichts wurde verändert, in der Ordi läuft weiter 3.31.0, der Lektor ist aus. Ein Folgeauftrag löst den Tausch.
