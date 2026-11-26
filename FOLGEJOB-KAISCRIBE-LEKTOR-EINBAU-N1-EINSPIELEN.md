# Teil 2 zu kaiscribe-lektor-einbau-n1: KaiScribe 3.32.0 einspielen + Abnahme an 451898 (Lektor, Schalter bleibt AUS)

Code: GitHub-Release **3.32.0** (main, enthält 3.31.0 und alles davor). Bericht Teil 1: `BERICHT-KAISCRIBE-LEKTOR-EINBAU-N1.md`.
Neu: KaiScribe-Lektor (Opus 5.5, Konto A) nach dem fertigen Befund, nur kp/rg, **Schalter Standard AUS**
(`X:\KaiScribe\Daten\lektor.json`, fehlt = aus). Ohne Schalter-Datei verhält sich 3.32.0 wie 3.31.0.

Regeln: Ordi-Systeme nur Mo–Do ab 17:30, Fr ab 13:30 oder am Wochenende, nie Mo 06:30–09:30. 451898 nie vidieren, alle
Testeinträge sofort stornieren. Nie in die CAS-DB schreiben. Keine Patientendaten nach außen, nur Nr. und Zahlen.
Meldungsruhe (nur jobnote/Kanban). Kein Gemini, kein anderes Modell.
**Nur einmal tauschen:** Läuft `kaiscribe-nicht-diktiert-streichen-n1-einspielen` (3.31.0) noch nicht oder ist der Tausch
dort noch offen, dann direkt auf 3.32.0 tauschen (enthält 3.31.0) und das dort vermerken. Nie auf eine ältere Version
zurück, außer als Rollback.

## A. Vorbedingung
GitHub: „Tests“, „Build Windows EXE“ und „Windows UI-Test (EXE)“ für 3.32.0 grün (SHA aus dem API-`digest`). Ist etwas
rot: nicht tauschen, Ursache beheben (Folgejob), nichts melden.

## B. Abnahme an 451898 mit der KaiScribe-KOPIE 3.32.0 als Gast, VOR dem Tausch
Werkzeug `tools/buero/lektor_abnahme.py` über ris-mods `e2e/diktat_e2e.py` (Muster `nicht_diktiert_abnahme.py`, Befunder
kp). Es legt eine EIGENE Schalter-Datei in `--arbeit` an und trägt `LEKTOR_DATEI` nur in die config.ini der Kopie ein
(danach `aus`). Den Schalter der Ordi auf X: NICHT anfassen. Je Fall ein frischer Eintrag; `--log` = rakscribe.log der Kopie.
1. **L0** Schalter aus → `LKABN=ok`: kein `[LEKTOR] gestartet`, Brief = Feld bei INS (Verhalten unverändert).
2. **L1** Schalter an (nur für diesen Lauf) → `LKABN=ok`: `[LEKTOR] fertig …` mit ≥ 1 übernommener Korrektur oder
   ≥ 1 Prüfzeile, Prüfzeile rot in der Hinweiszeile („… (Lektor) – bitte prüfen“) und NICHT im Brief, Brief = Feld nach
   dem Lektor. Findet der Lektor bei Diktat 1 nichts: `--diktat 2` bzw. `3` (das ist kein Fehler des Einbaus).
3. **LS** Schalter an, EOL sofort → `LKABN=ok`: `[LEKTOR] bei EOL noch nicht fertig … Befund unverändert`, Brief = Feld bei
   INS (Ausfall-Fall). HTTP-/Netzausfall ist offline geprüft (`tests/offline/test_lektor.py`).
4. Seitenbild L1 ohne Patientendaten: nur Befundbereich + rote Hinweiszeile.
5. Danach: Kopie-config.ini `LEKTOR_DATEI = aus` (macht das Werkzeug), alle drei Einträge stornieren.
Ist B rot: nicht tauschen bzw. Rollback (`-Schritt zurueck`), Ursache als Folgejob.

## C. Tausch + Schalter-Datei
1. Tausch wie bisher (Erinnerung release-vom-hetzner): Ordi-Hermes lädt das Asset von GitHub, prüft die SHA, dann
   `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.32.0 -Sha <sha>` (20 min Ruhe nach der letzten Ablage).
2. Schalter-Datei ausdrücklich AUS anlegen: `X:\KaiScribe\Daten\lektor.json` =
   `{"befunder": {"kp": false, "rg": false}, "monatsdeckel_usd": 40}` (UTF-8). Beleg: Dateiinhalt + `[INIT] Lektor:`-Zeile
   im Log nach dem nächsten Start (nur diese Zeile lesen).

## Abschluss
Version, Abnahme L0/L1/LS (Zahlen aus den LKABN-Zeilen), Schalter-Stand (aus), Tausch ja/nein.
Der Scharf-Entscheid ist NICHT Teil dieses Jobs → `kaiscribe-lektor-scharf-n1`.
