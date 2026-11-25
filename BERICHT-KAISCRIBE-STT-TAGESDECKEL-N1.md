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

## Teil 2: Einspielen 3.28.2 + Abnahme (kaiscribe-stt-tagesdeckel-n1-einspielen, 25.11.2026 01:30–02:00)
Bündelt den Nachtrag `kaiscribe-live-anzeige-eu-n1` (EU-Endpunkt). Alle Läufe am Büro-PC CASWS14 über den Ordi-Hermes, Testpatient 451898 als kp, nie vidiert, alle Test-Diktate storniert (…002/003/004).

**A. Einspielen: grün.**
- Build Windows EXE + Windows UI-Test (EXE) für 3.28.2 grün (Build 00:16 UTC, Release Latest 3.28.2, 56 789 194 Bytes).
- Tausch 01:34 per `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.28.2` = ok. SHA256 der X:-EXE `b9294f9a…f692e` = Release-Asset. Rückweg: `-Schritt zurueck` (3.28.1 gesichert als `…vor3.28.2-20261125-013448.alt`).
- `[INIT]` nach dem Start, ohne Fehlerzeilen: `Tagesdeckel Spracherkennung: 240 min/Tag (C:\Users\cas\AppData\Roaming\KaiScribe\stt_tagesdeckel_CASWS14.json), heute 0.0 min` und `Live-Anzeige (Speech v1) über eu-speech.googleapis.com (EU)`.
- Zählerdatei am PC: `C:\Users\cas\AppData\Roaming\KaiScribe\stt_tagesdeckel_CASWS14.json`.

**EU-Abnahme (Punkte 1–3): grün.** Mit vorübergehend `LIVE_ANZEIGE_AUS = aus` (WAV-Modus-Gast-Instanz, `e1_lws.wav` 23,9 s, ein Google-Lauf):
```
[01:41:28] [INIT] Live-Anzeige (Speech v1) über eu-speech.googleapis.com (EU)
[01:41:32] [CAS] Auftrag 20261125002 (kp) angenommen
[01:41:58] [GOOGLE] Streaming-Request beendet (238 Pakete).
[01:41:59] [GOOGLE] Finaler Zwischenabschnitt erkannt: 296 Zeichen
[01:42:02] [CHIRP3] OK: 310 Zeichen
[01:42:02] [CHIRP3] Text links nach 3.7 s ab Stopp
```
Kein PERMISSION_DENIED/RESOURCE_EXHAUSTED/Quota. Netz: nach `ipconfig /flushdns` zeigt `displaydns` 8× `eu-speech.googleapis.com`, kein reines `speech.googleapis.com`. Port-443-Verbindung der KaiScribe-Instanz 01:41:40 → 172.217.115.4 (DNS-Cache: eu-speech.googleapis.com); weitere Ziele oauth2.googleapis.com (142.251.127.95) und 160.79.104.10 (vermutlich Befund-KI, nicht belegt). Danach Zeile entfernt, config.ini wieder bitgleich (SHA256 `356d49dd…cd3df`), Neustart zeigt wieder Deckel 240 min + eu-speech.
Einschränkung: dass links der Text mitläuft, ist nur über das Log belegt (238 Pakete, Zwischenabschnitt 296 Zeichen), die Gast-Instanz lief ohne Mensch.

**B1 (normaler Lauf): grün.** Zählerdatei direkt danach: `{"art": {"chirp": 23.9, "streaming": 23.9}, "kuerzel": {"kp": 47.8}, "pc": "CASWS14", "s": 47.8, "tag": "2026-11-25"}`, keine Zeile `[STT-DECKEL]`. Später am 24.11. (3.28.1) schon grün belegt.

**B2 (Tageswechsel):** `heute 0.0 min` am 25.11. nach Mitternacht (Neustart 01:35, Datei hatte `tag 2026-11-24` → neuer Tag 2026-11-25 mit 0.0 min). Belegt.

**B3 (Grenze mit `STT_TAGESDECKEL_MIN = 1`): Verhalten grün, ein Beleg offen.**
```
[01:45:18] [INIT] Tagesdeckel Spracherkennung: 1 min/Tag (…), heute 0.8 min
[01:46:58] [STT-DECKEL] WARNUNG: 1.2 von 1 min Google-Spracherkennung heute (80 %, CASWS14) – bitte Hermes prüfen
  Zählerdatei: {"art": {"chirp": 47.8, "streaming": 23.9}, "kuerzel": {"kp": 71.7}, "pc": "CASWS14", "s": 71.7, "tag": "2026-11-25", "warn80": 1}
[01:48:30] [INIT] Tagesdeckel Spracherkennung: 1 min/Tag (…), heute 1.2 min
[01:49:00] [CHIRP3] Volltranskription: 24s Audio
[01:49:00] [STT-DECKEL] Tagesgrenze erreicht: 1.2 von 1 min Audio heute (CASWS14) – keine Google-Spracherkennung mehr bis Mitternacht
[01:49:00] [CHIRP3] Tagesgrenze Spracherkennung erreicht – Aufnahme gesichert, bitte Hermes melden – Audio behalten: 20261125-014900_20261125004.wav
[01:49:00] [HINWEIS] ⚠ Tagesgrenze Spracherkennung erreicht – Aufnahme gesichert, bitte Hermes melden
```
- Grenzlauf: kein Befund, keine Zeile `[CHIRP3] OK`, keine Streaming-Zeile, keine Zeile „wiederholt“, Zähler unverändert (71.7 s, `grenze: 1`). WAV `nicht_erkannt\20261125-014900_20261125004.wav` (764 844 Bytes) lag da und wurde danach gelöscht. Die Brücke meldete „abgebrochen“.
- Danach `STT_TAGESDECKEL_MIN` entfernt (config.ini bitgleich zum Original), Neustart: `[INIT] … 240 min/Tag …, heute 1.2 min`.
- **Offen:** Die Tagesbericht-Zeile `STT-DECKEL CASWS14: …` in `X:\KaiScribe\Daten\nutzung\tagesbericht_2026-11-25.txt` ist **nicht belegt**. Der WAV-Modus/Selbsttest hat laut Quelle keinen Nutzungszähler und schreibt deshalb keinen Tagesbericht (die Datei existiert heute noch nicht). Das ist offline im Test geprüft, am echten Fenster müsste es ein Mensch mit Mikrofon auslösen (oder sich beim ersten echten Diktat zeigen, dann im Tagesbericht nach `STT-DECKEL` suchen, normale Läufe erzeugen nur den Zähler).
- Der Zähler zählte im 2. Lauf nur chirp (Live-Anzeige für kp wieder aus), daher 71.7 s statt ~95 s, ohne Folgen.

**B4 (Meldeweg trocken): nicht ausgeführt.** Vom Hetzner-Server scheitert `kaiscribe_chirp_warnung.py --vmssh … --trocken` beim Hochladen auf die VM (`scp: Connection closed`, kein SSH-Zugang hier). Muss am Mac laufen (`DECKEL <heute> <PC>` erwartet; nicht scharf). Wegen der Tagesbericht-Lücke oben zeigt der Trockenlauf heute noch nichts.

**B5 / EU Punkt 4 (rg-Logs, Neuaufsetzen nach 240 s): offen.** Nur lesen, am nächsten Tag: rg-Log mit `[INIT]` eu-speech + Deckel-Zeile, `Streaming-Request beendet`, nach Diktaten > 4 min `Live-Anzeige nach 240s neu aufgesetzt` ohne Fehler. rg läuft erst mit 3.28.2, wenn der Wächter dort neu startet.

**Arbeitsdateien am Büro-PC:** `%LOCALAPPDATA%\hermes\work\ks3282_abn\` (b1_treiber.py, netz.txt, rl_lauf.txt, rl_b3a/b.txt, b3a/b_deckel.json). Meldung für Hermes: KaiScribe 3.28.2 live: Live-Anzeige über eu-speech.googleapis.com (Beleg INIT + DNS), Tagesdeckel 240 min/PC/Tag aktiv und an der Grenze belegt; Quota 14400 s/Tag gilt gemeinsam; Rollback = vorherige EXE / `LIVE_ANZEIGE_AUS = kp, rg`.
👉 Offen für Folgetag: B4 am Mac, B5/EU-4 rg-Log lesen, Tagesbericht-Zeile `STT-DECKEL` beim ersten echten Lauf prüfen.
