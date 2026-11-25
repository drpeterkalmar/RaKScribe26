# BERICHT waechter-zaehlt-nicht-n1 – Teil 1 (Bau), Kanban #541

Auslöser: Georg 24.11.2026 08:08 CASWS10 „Ich kann nichts mit KaiScribe diktieren“. Belegt (VM run_60d95c84…): rg 07:55
(RH 60) und 08:08 (20261124008) Brücke 2.5.27 `keine_antwort` → SpeechExec-Original. Nach der Anmeldung lief nur
`KaiScribe.exe --sm-waechter` (3.25.0, 07:25), kein KaiScribe-Fenster.

## Ursache (zwei Stellen, beide zählten den Wächter als „KaiScribe läuft“)

1. **Starter beim Anmelden** (`source_code/bereitschaft.py`, `starter_vbs` → `KaiScribeLaeuft()`): Der Wächter startet
   eigenständig aus seinem Autostart. Der KaiScribe-Starter sah per WMI „KaiScribe.exe läuft (eigener Benutzer)“ und
   meinte: „KaiScribe läuft schon – nichts zu tun“. Deshalb kam das Fenster gar nicht erst.
2. **Brücke beim CAS-Diktat** (ris-mods `bruecke/windows.py kaiscribe_prozesse()`, nur Prozessnamen per tasklist):
   `laeuft=True` → KaiScribe nicht gestartet, nur `annahme_s` 15 s gewartet → `keine_antwort` → Original.

## Behoben

| Teil | Version / Commit | Was |
|---|---|---|
| Brücke (RaK-Befund) | **2.5.35**, ris-mods `ce26f4a`, `706ef74`, `e384203` | `kaiscribe_prozesse()` zählt nur die Fenster-Instanz: Befehlszeile mit `--sm-waechter` zählt nie (NtQueryInformationProcess, ohne Adminrechte, ohne PowerShell); **maßgeblich** ist der Einzelinstanz-Mutex `Local\RaKScribe26-Einzelinstanz` (fehlt er → kein Fenster → Brücke startet KaiScribe; ist er da → läuft). **Sicherheitsnetz**: `keine_antwort` trotz „läuft“ → EXE einmal starten (Einzelinstanz holt eine laufende KaiScribe nach vorne bzw. startet das Fenster), neuer Auftrag (schon geschickte Leistungen/IB-Lab/Kontext übernommen), `annahme_start_s` (120 s) warten, erst dann Original. |
| Tausch-Skript | `ordi-hermes/kaiscribe_x_tauschen.ps1` **2.1** (ris-mods `706ef74`) | `Get-Ks` ohne Wächter: `neu_gestartet` nicht mehr fälschlich True, `Close-Ks` wartet nicht 30 s auf einen fensterlosen Wächter (sonst „belegt“). `-Schritt lage` zeigt Wächter-PIDs extra. |
| KaiScribe-Starter | **3.25.1**, RaKScribe26 `4ddde4d`, `4a16950` | `KaiScribeLaeuft()` nimmt Prozesse mit `--sm-waechter` in der Befehlszeile aus (`InStr(LCase(p.CommandLine & ""))`, vor `GetOwner`). Der Starter auf den PCs wird beim nächsten Start des KaiScribe-Fensters per `nachziehen` neu geschrieben (Text weicht ab). |

EXE 3.25.1: GitHub-Release `3.25.1`, Build-Lauf 45348971927 grün, SHA256
`8cf954c36ebfc5f946bc34421381e22ae6f9860d69512340683bee58560f9202` (KaiScribe.exe = rakscribe26.exe). Windows-UI-Test-Lauf
45349230126 **grün** (08:49).

## Tests (offline, Hetzner)

- ris-mods `python3 -m unittest discover -s bruecke/tests`: **1305 OK** (7 übersprungen), neu
  `bruecke/tests/test_waechter_zaehlt_nicht.py` (15): Wächter allein → startet KaiScribe; Fenster läuft → kein Start;
  Sicherheitsnetz startet einmal, zweiter Auftrag, Diktat fertig ohne Original; Netz danach Original; kein Netz, wenn
  frisch gestartet; Befehlszeile unlesbar + Mutex fehlt → kein Fenster; Leistungen/Kontext ziehen um; Tausch-Skript 2.1.
- Formatierer G10 (Versionstupel) grün.
- RaKScribe26 `test_bereitschaft.py` FEHLER 0 (neuer Check Wächter-Ausnahme), `test_sm_waechter_bleibt.py`,
  `test_import.py`, `test_produktname.py` grün (venv mit tkinter `~/cj/work/kaiscribe-konfabulation-n1/venv`).
- Nicht prüfbar am Hetzner: `windows.befehlszeile`/`mutex_da` (ctypes, nur Windows) und das PowerShell-Skript 2.1 laufen
  erst bei der Abnahme echt – ist im Folgeauftrag ausdrücklich dabei (`-Schritt lage` zeigt die Wächter-PID).

## Teil 2 (Einspielen + Abnahme) – gebündelt

Nach Queue-Regel kein eigener Folgeauftrag: Nachtrag an `kaiscribe-schulter-ergebnis-n1-abnahme` (ab 20:15):
Brücke 2.5.35 auf X: (Quellpaket), EXE 3.25.1 per `kaiscribe_x_tauschen.ps1` 2.1, Probe am 451898 (Wächter läuft allein →
CAS-Diktat → KaiScribe nimmt an, `bruecke.log` ohne `keine_antwort`), morgen 07:30 alle Befund-PCs `keine_antwort` = 0.
Kanban #541 erst danach fertig.

Offene Lücke ohne Büro-PC: ob auf CASWS10 außer dem Wächter wirklich kein Fenster-Mutex existierte, ist nur aus dem
Prozessbild (VM-Lauf) geschlossen; die Abnahme belegt es mit `-Schritt lage` (Wächter-PID) + Brücken-Log
(`[rakscribe] gestartet:` statt 15 s Warten).

## Teil 2 – Einspielen + Probe (kaiscribe-schulter-ergebnis-n1-abnahme, 24.11.2026 21:01–23:57)
- **Brücke 2.5.35** (ris-mods e384203) auf X: und Büro-PC: `kaiscribe_x_tauschen.ps1 2.1 -Schritt py` 21:01 → `KS_TAUSCH=ok XQ=2.5.35 DQ=2.5.35 vorher=2.5.27`.
  Nachzuholen: Für e384203 gab es vor dem Einspielen keinen grünen `windows_pruefung.py`-Lauf. Am 25.11. 00:13 nachgeholt: ris-mods main b9fd0764 **grün** (70 Tests, Brücke/Formatierer/IBL; enthält den Code von 2.5.35 + den späteren Roboter-Stand). Für e384203 allein zählt das nicht als „gleicher Code“, siehe Karte #565.
- **EXE 3.28.1** (enthält den 3.25.1-Starter-Fix) 23:43 per Skript 2.1. Das Fenster kam von selbst: starter.log „gestartet (minimiert) … 17 s nach dem Start“, Wächter 3.28.1 als Nachfolger.
- **Probe 451898:** Fenster sanft zu, es liefen nur die Wächter (Mutex `Local\RaKScribe26-Einzelinstanz` fehlte). Dann CAS-Diktat (kp, gesprochen). bruecke.log: `[rakscribe] gestartet: X:\KaiScribe\Programm\KaiScribe.exe` → `angenommen von RaKScribe 3.28.1 (pid 11460) nach 8.0 s` → Ablage + JobFinished. 0× keine Antwort/Original. Brief richtig.
- **Starter von Hand** (nur Wächter lief): `gestartet (minimiert)` statt „KaiScribe läuft schon“.
- Offen: Morgenkontrolle 25.11. ab 07:35 an allen Befund-PCs (`keine_antwort` seit 06:00 = 0), Folgejob `waechter-zaehlt-nicht-n1-kontrolle`. Erst danach #541 fertig.

## Teil 3 – Morgenkontrolle 25.11. (waechter-zaehlt-nicht-n1-kontrolle, gelesen 07:35–09:45, nur lesen)
**Morgenkontrolle 25.11.: keine_antwort 0, aber nicht belegt.** Bis 09:38 kein einziges CAS-Diktat über die Brücke. Ein Fenster-Start nach der Anmeldung kam ebenfalls nicht → #541 bleibt offen.

- Brücken-Spiegel `X:\KaiScribe\Daten\protokolle\bruecke_<PC>.log` (Rückfall `X:\RaKScribe\…`: keine Dateien), Zeilen seit 06:00:
  CASWS08 0 (zuletzt 24.11. 10:07) · CASWS10 0 (zuletzt 24.11. 08:09) · CASWS14 0 (zuletzt 25.11. 01:48, Nachttest) ·
  RAKCLIENT04 0 (zuletzt 19.11.). Also: keine_antwort 0, angenommen 0, `[rakscribe] gestartet` 0 an allen PCs, weil es keine Diktate gab.
  Aktiv waren heute nur die Formatierer-Logs von CASWS03 (bis 09:35) und CASWS15 (bis 09:30), also SpeechMagic-Befundung.
- Geteiltes `X:\KaiScribe\Programm\rakscribe.log` seit 06:00: 80 Zeilen, alle `[SM]` (Wächter). Wächter **3.28.2** startete
  07:25:47 und 07:27:27, beide frisch (also Anmeldungen, kein Nachfolger). Das passt zu Georgs Anmeldezeit vom 24.11. (07:25:57).
  **Kein einziger Fenster-Start (`[INIT] Nutzungszähler`) seit 06:00.** Letzter Fenster-Start je PC: CASWS10 23.11. 17:33,
  CASWS08 24.11. 10:11, CASWS14 25.11. 01:56. Die erste KaiScribe-Version des Tages ist damit an keinem Befund-PC belegbar
  (Wächter 3.28.2 ist auf X: aktuell, nicht 3.28.1).
- Starter (`%APPDATA%\KaiScribe\starter.log`) ist vom Büro-PC aus nicht lesbar (Admin-Freigabe `\\<PC>\c$` an allen
  fünf PCs zu). Ob dort „gestartet (minimiert)“ oder „KaiScribe läuft schon“ steht, bleibt offen.
- **Ursache (aus dem Code, sehr wahrscheinlich):** Der neue Starter (seit 3.25.1) kommt erst auf einen PC, wenn dort das
  **KaiScribe-Fenster** einmal startet (`Bereitschaft.nachziehen` in `_autostart_nachziehen`, RaKScribe.py:1233). Der Wächter
  (`sm_waechter_main`) sichert nur seinen eigenen Autostart und zieht den Fenster-Starter nicht nach. An CASWS10 lief das Fenster
  seit 23.11. nicht mehr. Dort liegt also noch der alte `warte_auf_x.vbs`, der den Wächter als „läuft schon“ zählt. Ergebnis:
  wieder nur der Wächter, wie am 24.11. Das ist ein Henne-Ei-Problem.
- Folge für Georg heute: Das Sicherheitsnetz Brücke 2.5.35 greift beim ersten CAS-Diktat (startet KaiScribe, ca. 8 s, siehe
  Probe 451898). Danach schreibt das Fenster den Starter neu, und ab der nächsten Anmeldung kommt das Fenster von selbst. Die Meldung
  „KaiScribe startet wieder von selbst“ stimmt daher **heute noch nicht** und geht nicht raus.
- Nebenwerte (Punkt 5): `[CHIRP3] Text links nach … s ab Stopp` seit 06:00: **n = 0** (kein Fenster-Diktat, kein Messwert).
  `[SM] … Pause erkannt`: **14** · `Sprachpegel nicht messbar`: **0** (Beleg für BERICHT-SM-SENF-DIKTATPAUSE-N1 Teil 2).
- Folgeauftrag: `FOLGEJOB-WAECHTER-ZAEHLT-NICHT-N2.md`. Der Wächter zieht den Fenster-Starter beim Start nach, danach
  Morgenkontrolle mit echten Brücken-Diktaten. Arbeitsdateien (Leseskripte): `~/cj/work/waechter-zaehlt-nicht-n1-kontrolle/`.
- Lesewege: Ordi-Hermes `peer run ordi` und VM `peer run vm` (sieht dasselbe X:). Die Zeilen im rakscribe.log haben das Format
  `[YYYY-MM-DD HH:MM:SS]`, die Brücken-Logs `YYYY-MM-DD HH:MM:SS`.
