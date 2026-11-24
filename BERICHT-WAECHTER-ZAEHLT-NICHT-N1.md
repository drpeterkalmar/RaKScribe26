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
