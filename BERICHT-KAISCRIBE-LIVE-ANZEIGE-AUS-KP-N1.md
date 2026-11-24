# kaiscribe-live-anzeige-aus-kp-n1: Live-Anzeige für kp abschaltbar (Di 24.11.2026), Teil 1

## Kurzbericht (≤10 Zeilen)
1. **Fertig in KaiScribe 3.27.0** (origin/main 55c5411), noch nicht eingespielt. Das Einspielen ist an
   `kaiscribe-rho-regel-becken-n1-einspielen` angehängt (heute Abend, gleiche Runde).
2. Für kp gibt es keine Live-Anzeige mehr: kein Google-Streaming und keine Reparatur je SpeechMike-Pause. Links steht
   nur das bisherige Diktat mit „● Aufnahme läuft“ und dem Pegel. Der Text kommt nach Stopp/INS aus chirp_3.
   rg und Diktate ohne CAS-Auftrag bleiben unverändert.
3. Rechts einfügen (Cursor, Markierung übersprechen, Nachdiktat) und die Mammo-Maske laufen offline grün mit kp.
4. **Rückfall:** chirp_3 wird einmal wiederholt. Bleibt es leer, wird das Audio als WAV behalten und links erscheint
   die rote Zeile „Spracherkennung nicht verfügbar – bitte erneut diktieren/prüfen“. Offline getestet.
5. **Messwert:** Statt Pause→Anzeige (entfällt laut Nachtrag) wird jetzt Stopp→Text links gemessen (Logzeile `Text
   links nach X s`). Die Zahl kommt aus der Abnahme.
6. **Ersparnis:** etwa 125 Live-Minuten pro Woche ≈ 7,70–11,40 €/Monat (Listenpreis mit/ohne Datenprotokoll). Dazu
   kommen die Abschnitts-Reparaturen, ihre genaue Zahl wird aus den Logs 17.–23.11. in Teil 2 gerechnet.
7. **Rollback-Schalter:** `LIVE_ANZEIGE_AUS = aus` in der config.ini neben der EXE, wirkt beim nächsten Start.

## Details
- **Code:**
  - `config.py`: `LIVE_ANZEIGE_AUS`, eine Kürzel-Liste. Standard kp, `aus` = niemand.
  - `aufnahme.py`: `live=False` heißt kein Streaming-Thread. Puffer, Pegel und Pausen bleiben gleich.
  - `RaKScribe.py`:
    - `_live_anzeige_an` (Kürzel aus dem CAS-Auftrag)
    - `_pausieren` ohne Reparatur
    - `_repariert_anzeigen` (Statuszeile)
    - `_warten_und_verarbeiten`: Wiederholung, Ausfall, Messzeile
    - `_maske_abschnitt_thread`: Wiederholung statt Live-Text-Rettung
    - `_chirp_neuversuch`, `_stt_ausfall_merken`
  - Unter 1 s Audio kommt wie bisher „Kein Text diktiert“.
- **Tests:**
  - Neu ist `tests/offline/test_live_anzeige_aus.py` (37 Prüfungen, in test.yml).
  - `test_audiodatei.py`: WAV-Modus als kp, ohne Streaming und mit Ausfall. Die alten Fälle laufen jetzt als rg.
  - `test_maske_ablauf.py`: der Live-Text-Fall 2b läuft mit Live-Anzeige an, alles andere als kp ohne Live.
  - Alle Python-Gates aus test.yml sind grün. Lokal liefen sie mit der tkinter-venv, das Skript liegt unter
    `~/cj/work/kaiscribe-live-anzeige-aus-kp-n1/`. Google wurde nicht aufgerufen (0 $).
- **Kosten-Grundlage:** BERICHT-STT-MISTRAL-VERGLEICH-N1 (544 Live-Minuten/Monat = Woche × 4,35) und nutzung.py
  (0,024 $/min Live). Die Logs der Woche (`X:\…\Daten\nutzung`, `rakscribe.log`) liegen am Büro-PC, der in Teil 1
  tabu ist → Teil 2, Abschnitt C.
- **Offen (Teil 2, `FOLGEJOB-KAISCRIBE-LIVE-ANZEIGE-AUS-KP-N1-EINSPIELEN.md`):**
  - Windows-UI-Test vor dem Bau
  - Einspielen
  - Abnahme an 451898 mit den Log-Zeilen „kein Streaming gestartet“, „chirp_3 OK“ und „Einfügen rechts OK“
  - Messwert Stopp→Text
  - genaue Kostenrechnung

## Teil 2 – Abnahme (in kaiscribe-schulter-ergebnis-n1-abnahme, 24.11.2026, KaiScribe 3.27.1/3.28.1, live 3.28.1 seit 23:43)
- Echter Praxisweg (CAS-Diktat 451898 als kp, gesprochen, 36 s): `[GOOGLE] Live-Anzeige aus – kein Streaming gestartet (nur Aufnahme, Text nach Stopp aus chirp_3).`, `[CHIRP3] OK: 155 Zeichen`, **`[CHIRP3] Text links nach 2.8 s ab Stopp (Live-Anzeige aus)`**. In allen Läufen gab es 0 Zeilen „Streaming-Request beendet“.
- WAV-Modus als kp: E1 2,9 s, E4b 2,4 s/0,8 s, J 1,7 s, K 1,8 s (Stopp → Text). Nachdiktat ohne Cursor → `[BEFUNDFELD] Ergänzung: … eingebaut (Titel und Text unverändert)`. Markierung → `[EINFÜGEN] Markierung ersetzt (gleich)`.
- Rückfall E5 (simulierter chirp-Ausfall): einmal wiederholt, dann `Spracherkennung nicht verfügbar – bitte erneut diktieren/prüfen – Audio behalten`, WAV `%APPDATA%\KaiScribe\nicht_erkannt\…` (444 844 B), kein Befund, Brücke „abgebrochen“.
- Nicht gemacht: Cursor-Einfügen (Klick an eine Stelle), rg-Log lesen (B4), Kostenrechnung C (Logs 17.–23.11.). Das ist an `kaiscribe-stt-tagesdeckel-n1-einspielen` weitergegeben, die Messwerte aus dem Praxisbetrieb an die Morgenkontrolle.
