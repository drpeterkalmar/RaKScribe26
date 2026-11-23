# Kontrolle Senf-Anzeige – erste echte kp-Fälle (Mo 23.11.2026, 07:00–~16:20, VM als rakauto, nur lesen)

**Ergebnis: kein Fehler, Senf-Anzeige läuft.** 41 echte Läufe, alle KaiScribe **3.22.4** (CASWS08 36, CASWS10 5); 451898 nicht mitgezählt.
- **Log** (`X:\KaiScribe\Programm\rakscribe.log`): seit 07:00 0 Fehler, 0 Traceback, 0 WinError 10013, 0 ESET.
- **kp: 6 Aufträge mit `[SENF] … Anzeige an (kp)`**, erste 08:10. Zustände: 2× sofort „fertig“ (Senf lag schon da), 4× „laeuft“ – davon im
  KaiScribe-Log kein „fertig“ mehr. Ablage zu den 4: 3× später `fertig` (auffällig 2, unauffällig 1; einmal 2 min nach Anzeige, zweimal erst 16:12
  als Nachlauf), 1× keine Datei. Das passt zu 3.22.4 (Verfolgung endet mit dem Auftrag; Senf nach Schließen erst mit 3.22.5, dort auch
  „Auftrag zu, Senf noch nicht da“ im Log) – kein neuer Fehler, aber **nicht live belegt, dass „laeuft“ → „fertig“ im offenen Fenster kommt**.
- **Anderes Kürzel:** `rg` 36 Aufträge – gewollt: Peter 23.11. 11:50 `SENF_ANZEIGE = kp, rg` / `SM_SENF = kp, rg` in config.ini. Kein drittes Kürzel;
  `[SENF]`-Zeilen ohne vorheriges „Anzeige an“: 0. Rg: 33× fertig, 3× laeuft; Zeit Anzeige→fertig 0–1 s.
- **Senf im Brief:** in den Lauf-Dateien 0× im Ergebnis; 2 Treffer (kp, Zeile „RH 45 · …“) nur in `stt_roh` = SpeechMagic-Senf-Einfügung (SM_SENF),
  kein Brieftext. `<Nr>.rakscribe.txt` ist unter X: nicht mehr greifbar → Brief-Text direkt nicht prüfbar (Ja/Nein: Lauf-Ergebnis sauber).
- **VM:** `senf_202611.log` heute 210 `ablage_takt`-Zeilen, davon n ≥ 1: 169 (max 22), `ablage_fehler` 0; `takt_letzt.txt` 16:16.
  Ablage `senf\`: KaiScribe 135 / RaKScribe 143 Dateien (je 20 `fehler`, Rest `fertig`) – Zwilling hat mehr (Altbestand), kein Rückstand.
- **Offen → Folgeprüfung Di 24.11.:** nach Einspielen 3.22.5 (heute 20:15) kp-Fälle auf „laeuft → fertig“ im offenen Fenster und „Auftrag zu“-Zeilen ansehen.
- Werkzeuge: `tools/vm/senf_kontrolle_pruefen.py`, `senf_kontrolle_nach.py` (Zähler/Ja-Nein, keine Nr/Namen/Text) über `tools/vm/x_lauf_mac.py`.
