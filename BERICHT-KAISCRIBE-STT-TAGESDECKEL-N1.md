# kaiscribe-stt-tagesdeckel-n1: harter Tagesdeckel für die Google-Spracherkennung (Di 24.11.2026), Teil 1

## Kurzbericht
1. **Fertig in KaiScribe 3.28.0 (origin/main 99dcd35), noch nicht eingespielt.** Einspielen und der echte Lauf an 451898 kommen im Folgeauftrag
   `kaiscribe-stt-tagesdeckel-n1-einspielen` (`FOLGEJOB-KAISCRIBE-STT-TAGESDECKEL-N1-EINSPIELEN.md`), außerhalb der
   Ordi-Zeit. Bis dahin ist am PC nichts aktiv.
2. **Zähler:** KaiScribe zählt jede Audiosekunde, die an Google geht. Das umfasst chirp_3, die Live-Anzeige, Fehlversuche
   und Wiederholungen. Gezählt wird je PC und Tag, zusätzlich je Kürzel. Der Tag wechselt um 00:00 Wiener Zeit.
3. **Wo der Zähler liegt:** `%APPDATA%\KaiScribe\stt_tagesdeckel_<PC>.json`, lokal am PC (nicht X:). So zählt er auch,
   wenn das Netzlaufwerk fehlt. Die Datei wird atomar geschrieben und enthält nur Zahlen.
4. **Grenze:** `STT_TAGESDECKEL_MIN`, Standard 240 min Audio/Tag/PC. Normal sind 15–30 min, der Deckel greift also im
   Alltag nie. Bei Erreichen gibt es bis Mitternacht keinen Google-Aufruf mehr. Das Audio wird als WAV in
   `%APPDATA%\KaiScribe\nicht_erkannt\` gesichert, links steht rot „Tagesgrenze Spracherkennung erreicht – Aufnahme
   gesichert, bitte Hermes melden“. Ein zweiter Versuch wird dann nicht gemacht.
5. **Schleifenbremse:** Geht dieselbe Aufnahme mehr als 3× in 10 min an Google, gibt es für sie keine weiteren Aufrufe
   (bis KaiScribe neu startet). Ausfall-WAV und rote Zeile kommen wie bei der Grenze.
6. **Meldung ab 80 %:** Im `rakscribe.log` steht dann `[STT-DECKEL] WARNUNG …`. Außerdem kommt eine Zeile
   `STT-DECKEL <PC>: …` in den Tagesbericht `X:\KaiScribe\Daten\nutzung`. Die bestehende Chirp-Warnung (Cron 20:30) liest
   sie mit und legt **eine Karte je Tag und PC für Hermes** an (Spalte tun, nicht Peter).
7. **Grenze ändern:** In der `config.ini` neben der EXE `STT_TAGESDECKEL_MIN = 360` eintragen (Minuten). Das wirkt beim
   nächsten KaiScribe-Start. Ein `aus` gibt es bewusst nicht: 0 oder keine Zahl ergibt 240 mit Warnung im `[INIT]`.
8. **Test:** `tests/offline/test_stt_tagesdeckel.py` hat 54 Prüfungen und ist grün. Alle Python-Gates aus test.yml sind
   grün. Google wurde nicht aufgerufen (Attrappen), Kosten 0 $.

## Details
- **Neu: `source_code/stt_deckel.py` (Klasse `Deckel`):**
  - `vorher(pcm)` prüft vor dem Google-Aufruf die Tagesgrenze und die Schleifenbremse (SHA-1 der Samples, nur im
    Speicher).
  - `buchen(s, art)` zählt die gesendeten Sekunden.
  - Die 80-%-Meldung und die Grenze-Meldung kommen je einmal pro Tag.
  - Kaputte oder fehlende Datei: Der Deckel zählt im Speicher weiter und greift trotzdem.
  - Ohne tzdata (Windows-EXE) gilt die Ortszeit des PCs, also Wien.
- **`stt.py`:**
  - `chirp3_worker` prüft vor dem Diktat und vor jedem weiteren 50-s-Stück. Ist gesperrt, kommt None zurück und kein
    Request geht raus.
  - `letzte_sperre()` meldet im selben Thread „grenze“ oder „schleife“.
  - Gebucht wird jetzt auch, wenn der Request eine Ausnahme wirft. Das gilt auch für den Nutzungszähler.
- **`aufnahme.py`:** Ist die Grenze erreicht, startet keine Live-Sitzung. Eine laufende Sitzung schickt nichts mehr
  (höchstens 1 Prüfung pro Sekunde). Das Mikrofon und der Puffer laufen weiter, nichts geht verloren. Die gesendeten
  Live-Sekunden werden gebucht.
- **`RaKScribe.py`:**
  - `_deckel_einrichten` läuft in `init_runtime` immer, auch ohne Nutzungszähler. `[INIT]` zeigt Grenze, Datei und
    Stand.
  - Das Kürzel kommt aus dem CAS-Auftrag.
  - `_chirp_neuversuch` macht bei Sperre keinen zweiten Versuch.
  - `_stt_ausfall_merken` nimmt den Deckel-Text. Mit Live-Anzeige (rg) und in der Maske wird bei Sperre ebenfalls Audio
    gesichert und rot angezeigt, ein schon sichtbarer Live-Text wird wie bisher gerettet.
  - „Audio laden“ ist ebenfalls abgedeckt.
- **`config.py` / `config.ini`:** `STT_TAGESDECKEL_MIN`, in der config.ini auskommentiert dokumentiert.
- **`nutzung.py`:** `Zaehler.stt_deckel()` und die Tagesbericht-Zeilen `STT-DECKEL …`.
- **`tools/mac/kaiscribe_chirp_warnung.py`:** `deckel_karten()` liest heute und gestern, damit nach 20:30 nichts verloren
  geht.
- **Build und Tests:** build-exe.yml hat `--hidden-import=stt_deckel`, test.yml hat den neuen Test.
- **Unverändert:** Erkennung, Fachwortliste, Einfügen/Drüberdiktieren, Mammo-Maske. Die bestehenden Gates dafür
  (test_live_anzeige_aus, test_maske_ablauf, test_audiodatei, test_stt, …) sind grün.
- **Was der Test prüft:**
  - Zähler, Datei und Kürzel, Neustart am selben Tag, anderer PC
  - Tageswechsel (23:59 / 23:00 UTC = 00:00 Wien)
  - kaputte Datei, fehlender Ordner
  - 80 % und Grenze
  - Schleifenbremse (3× ok, 4. gestoppt, gleitendes Fenster)
  - chirp3_worker: Grenze mitten im langen Diktat, Fehlversuch zählt, Sperre nur im eigenen Thread
  - Live-Anzeige gesperrt
  - config
  - Meldeweg über den VM-Leser bis zur Karte (Attrappe kanban, `--tun`, nicht `--peter`)
  - EXE-Ablauf kp **und** rg an der Grenze: 0 Google-Aufrufe, WAV, rote Zeile, kein Befund
- **Offen (Teil 2):**
  - Windows-UI-Test, EXE bauen, Einspielen
  - echter Lauf an 451898 (normal, dann Grenze mit vorübergehend `STT_TAGESDECKEL_MIN = 1`, ohne Google-Kosten)
  - Meldeweg trocken am Mac
  - Grenze-Zeile wieder entfernen

## Teil 2 teilweise (in kaiscribe-schulter-ergebnis-n1-abnahme, 24.11.2026)
- 3.28.1 (enthält 3.28.0) ist seit 23:43 auf X: (Release Latest). Damit ist A erledigt, nur nicht mit 3.28.0 selbst.
- `[INIT] Tagesdeckel Spracherkennung: 240 min/Tag (C:\Users\cas\AppData\Roaming\KaiScribe\stt_tagesdeckel_CASWS14.json), heute 0.0 min`
  (Testkopie), live nach dem Tausch „heute 0.8 min“. Testkopie und Live-Instanz teilen sich die Zählerdatei.
- **B1 grün:** Nach einem kp-Lauf hat die Datei `tag 2026-11-24, s 30.0, kuerzel.kp 30.0, art.chirp 30.0`, 0 Zeilen `[STT-DECKEL]`.
- Offen für `kaiscribe-stt-tagesdeckel-n1-einspielen`: B3 (Grenze mit `STT_TAGESDECKEL_MIN = 1`), B4 (Meldeweg trocken), B5 (rg) sowie 3.28.2 (eu-speech) bauen und tauschen.
