# Teil 2 zu kaiscribe-stt-tagesdeckel-n1: Einspielen + echter Lauf an 451898

Code: **KaiScribe 3.28.0 = origin/main 99dcd35** (Code-Commit 45bfd37). Den Inhalt beschreibt `BERICHT-KAISCRIBE-STT-TAGESDECKEL-N1.md`. Die Version enthält
alles, was vorher auf main war (3.27.1 = Live-Anzeige aus für kp + K&L-Fix). Läuft `kaiscribe-schulter-ergebnis-n1-abnahme`
bzw. `kaiscribe-rho-regel-becken-n1-einspielen` noch mit einer älteren Version: erst danach tauschen, nicht dazwischen.

Regeln:
- Ordi-Systeme nur Mo–Do ab 17:30, Fr ab 13:30 oder am WE. Selbst einspielen nur bis 06:30.
- 451898 nie vidieren.
- Keine Patientendaten auf Mac/Server.
- Meldungsruhe.
- Google-Kosten: nur der eine Abnahmelauf über den Praxisweg (ein paar Sekunden Audio). Die Grenze selbst NICHT mit
  echtem Google-Audio ausreizen, sondern mit einem kleinen Deckel (s. B3).

## A. Einspielen
1. Windows-UI-Test (test-exe-windows.yml) muss grün sein. Danach EXE bauen. Neu im Bau ist `--hidden-import=stt_deckel`,
   das steht schon in build-exe.yml.
2. Tausch wie gehabt: `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.28.0`.
3. Nach dem Start im `[INIT]`-Block muss stehen:
   `[INIT] Tagesdeckel Spracherkennung: 240 min/Tag (…\KaiScribe\stt_tagesdeckel_<PC>.json), heute X min`.
4. Die config.ini neben der EXE nicht ändern, der Standard 240 ist eingebaut.

## B. Abnahme an 451898 (außerhalb der Ordi-Zeit)
1. **Normaler Lauf, als kp.** Diktat 451898 → Record → kurz sprechen → INS.
   - Befund kommt wie bisher.
   - `%APPDATA%\KaiScribe\stt_tagesdeckel_<PC>.json` hat heute `s` > 0, `kuerzel.kp` > 0 und `art.chirp` > 0.
   - Im Log steht keine Zeile `[STT-DECKEL]`.
2. **Tageswechsel.** Wird nur gelesen: Am nächsten Morgen (oder nach 00:00) zeigt `[INIT]` „heute 0.0 min“, bzw. die
   Datei hat das neue `tag`. Dafür ist kein eigener Lauf nötig, das ist offline belegt.
3. **Grenze, ohne Google-Kosten.**
   - In der config.ini neben der EXE **vorübergehend** `STT_TAGESDECKEL_MIN = 1` eintragen und KaiScribe neu starten.
     Alternativ geht der WAV-Modus mit eigener config.ini, falls der Weg verfügbar ist.
   - Liegt der Zähler heute schon ≥ 60 s (nach B1 meist ja), wird kein weiterer Google-Aufruf gemacht. Sonst einmal
     WAV-Modus/„Audio laden“ mit einer > 60-s-Testdatei (rakscribe-test, keine Patientenstimme). Das kostet ≤ 0,02 $.
   - Dann 451898 als kp: Record → sprechen → INS. Erwartet:
     - Rote Zeile „⚠ Tagesgrenze Spracherkennung erreicht – Aufnahme gesichert, bitte Hermes melden“.
     - WAV `%APPDATA%\KaiScribe\nicht_erkannt\<Zeit>_<Nr>.wav`.
     - Kein Befund, keine Zeile `[CHIRP3] OK`.
     - Log `[STT-DECKEL] Tagesgrenze erreicht …`, KEINE Zeile „chirp_3 wird einmal wiederholt“.
     - Ab dem ersten Überschreiten zusätzlich `[STT-DECKEL] WARNUNG: … (80 %, <PC>)`.
     - `X:\KaiScribe\Daten\nutzung\tagesbericht_<heute>.txt` enthält eine Zeile `STT-DECKEL <PC>: …`.
   - Danach **`STT_TAGESDECKEL_MIN`-Zeile wieder entfernen**, KaiScribe neu starten und prüfen, dass `[INIT]` 240 min
     zeigt. Die gesicherte WAV löschen (Testaudio).
   - Die Brücke meldet das Diktat „abgebrochen“, also stornieren und NICHT vidieren.
4. **Meldeweg trocken.** Am Mac `tools/mac/kaiscribe_chirp_warnung.py --vmssh … --trocken` muss
   `DECKEL <heute> <PC>` zeigen. Nicht scharf laufen lassen, sonst entsteht eine Test-Karte. Läuft der Cron 20:30 vorher
   scharf, entsteht eine Karte „KaiScribe: Tagesdeckel Spracherkennung <PC> <Tag>“ (Spalte tun). Diese mit Notiz
   „Abnahme-Test“ auf fertig setzen.
5. **rg.** Nur lesen: rg-Logs zeigen weiter `Streaming-Request beendet`, `[INIT]` hat dort ebenfalls die Deckel-Zeile.
   Kein eigener rg-Lauf.

**Rot → Rückweg:** `-Schritt zurueck` auf die vorige EXE. Einen Schalter zum Abschalten gibt es bewusst nicht: ohne
Deckel hätte chirp_3 keine Tagesgrenze. Höchstens `STT_TAGESDECKEL_MIN` größer setzen. Dazu eine Karte in Spalte tun.

## C. Bericht
`BERICHT-KAISCRIBE-STT-TAGESDECKEL-N1.md` ergänzen: Log-Zeilen aus B1/B3, Pfad der Zählerdatei am PC, Ergebnis aus B4.
