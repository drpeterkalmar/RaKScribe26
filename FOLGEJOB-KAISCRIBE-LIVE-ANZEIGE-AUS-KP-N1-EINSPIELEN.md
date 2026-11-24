# Teil 2 zu kaiscribe-live-anzeige-aus-kp-n1: Einspielen 3.27.0 + Abnahme + Kostenrechnung

Gebündelt per Nachtrag in `kaiscribe-rho-regel-becken-n1-einspielen` (ein Einspielen und eine Abnahme-Runde je Abend).
Code: **KaiScribe 3.27.0 = origin/main 55c5411** (Code-Commit ca9c177), Bericht `BERICHT-KAISCRIBE-LIVE-ANZEIGE-AUS-KP-N1.md`.
3.27.0 enthält alles bis 3.26.2. Es reicht also, statt 3.26.x gleich 3.27.0 zu bauen und einzuspielen.
Regeln: Ordi-Systeme nur Mo–Do ab 17:30 / Fr ab 13:30 / WE, selbst einspielen nur bis 06:30. 451898 nie vidieren.
Google-Testkosten 0 $, einzige Ausnahme ist der eine Abnahmelauf über den Praxisweg. Meldungsruhe.

## A. Einspielen
- EXE 3.27.0 bauen. Vorher muss der Windows-UI-Test (test-exe-windows.yml) grün sein. Die Fälle F/M laufen mit CAS-Kürzel
  kp, also jetzt ohne Live-Anzeige. Mit Chirp-Attrappe sollte das grün bleiben, offline ließ es sich hier nicht laufen
  (kein Windows). Ist ein Live-Text-Check rot, die Erwartung für kp anpassen (links leer bis Stopp) und nicht den Code.
- Tausch wie gehabt: `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.27.0`. Danach `[INIT]` ohne Fehlerzeilen.
- config.ini neben der EXE auf X: nicht ändern, der Standard `LIVE_ANZEIGE_AUS = kp` ist eingebaut.

## B. Abnahme an 451898 (als kp, Praxisweg, EIN echter Lauf)
1. CAS-Diktat 451898 als kp öffnen → Record → kurz sprechen → Pause → weiter → INS. Erwartet:
   - Während der Aufnahme links nur „● Aufnahme läuft“ (Pause: „● Aufnahme pausiert – Text kommt nach Stopp/INS“),
     kein Diktattext, Pegelbalken läuft.
   - Log `rakscribe.log`: `[GOOGLE] Live-Anzeige aus für kp (LIVE_ANZEIGE_AUS)` und `… kein Streaming gestartet`.
     KEINE Zeile `[GOOGLE] Streaming-Request beendet` und KEIN `[SPEECHMIKE] Abschnitt … repariert`.
   - `[CHIRP3] OK: … Zeichen` und `[CHIRP3] Text links nach X s ab Stopp (Live-Anzeige aus)`. **X = Messwert
     Stopp→Text links für den Bericht.**
2. Im selben Fall rechts: Cursor in den Befund setzen → Record → „zusätzlich …“ → INS ⇒ `[EINFÜGEN] Ergänzung an
   Cursor-Stelle …`, Text an der Stelle. Danach ein Wort markieren → Record → INS ⇒ Markierung ersetzt.
   Nachdiktat (Record nach INS ohne Cursor) ⇒ „Ergänzung eingebaut“. Belegen per Logzeilen und Brieftext. Danach EOL
   → Brief in CAS ansehen → stornieren, NICHT vidieren.
3. Rückfall ohne Google-Kosten: WAV-Modus als kp mit `{"fehler": "stt"}` (wie tests/offline/test_audiodatei.py 6b).
   Erwartet: rote Zeile „⚠ Spracherkennung nicht verfügbar – bitte erneut diktieren/prüfen“, WAV in
   `%APPDATA%\KaiScribe\nicht_erkannt\`, kein Befund, Brücke „abgebrochen“.
4. rg unverändert: im Log eines rg-Diktats (CASWS14, falls vorhanden) weiter `Streaming-Request beendet`. Nur lesen,
   kein eigener rg-Lauf.
5. Mammo-Maske: offline belegt (test_maske_ablauf.py läuft jetzt als kp ohne Live-Anzeige, Feldtext aus chirp_3 je
   Feld; test_live_anzeige_aus.py Fall 5 deckt Wiederholung und Ausfall ab). Gibt es an 451898 keine Mammo-Leistung,
   keinen eigenen Lauf machen und das so im Bericht vermerken.
Rot → Rückweg: entweder config.ini neben der EXE `LIVE_ANZEIGE_AUS = aus` (wirkt beim nächsten KaiScribe-Start) oder
`-Schritt zurueck`. Dazu eine Karte (Spalte tun).

## C. Kostenrechnung (Nachtrag Peter 24.11. 18:57) aus den Logs 17.–23.11.
Hetzner hatte keinen Zugriff, deshalb hier nachholen (nur Zahlen, keine Patientendaten):
- `X:\KaiScribe\Daten\nutzung\2026-11_<PC>.json` (Rückfall `X:\RaKScribe\…`), Tage 17.–23.11.:
  `stt_s.streaming` (Live) und `stt_s.chirp` je PC. Peters PC(s) = CASWS10 u. a., Zuordnung über `bruecke_*.log`.
- Abschnitts-Reparaturen: in den `rakscribe.log` der kp-PCs die Zeilen `[SPEECHMIKE] Pause nach Abschnitt k (x s)`
  mit x ≥ 0,5 s summieren. Diese Sekunden stecken in `stt_s.chirp` mit drin (chirp_3 je Pause).
- Ersparnis/Woche = Live-min × 0,024 $ + Abschnitts-min × 0,016 $ (Listenpreise nutzung.py), × 4,35 = Monat, in € × 0,87.
  In den Bericht schreiben: Woche, Monat, getrennt nach Live und Abschnitten.

## D. Meldungen
Nur wenn belegt live: Bericht ergänzen (Messwert Stopp→Text, Log-Zeilen, Kosten). Keine eigenen Telegram-Meldungen,
die Abschlussmeldung schickt die Queue.
