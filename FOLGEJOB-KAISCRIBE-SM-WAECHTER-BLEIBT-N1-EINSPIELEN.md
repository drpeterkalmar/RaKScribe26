# kaiscribe-sm-waechter-bleibt-n1-einspielen – KaiScribe 3.22.5 (eigener SpeechMagic-Wächter) einspielen, Abnahme 451898, erster kp-Fall

Von `kaiscribe-sm-waechter-bleibt-n1` (Mo 23.11.2026, Teil 1 auf dem Hetzner ohne Büro-PC). EILT: Peter 23.11. 09:21/09:25:
„Einspielen SOFORT nach Abnahme 451898, nicht abends“, Ordi-Zeit ausdrücklich erlaubt. Release-Regel (Georg): erst ein echter
Lauf am Testpatienten 451898, sonst Rollback. 451898 NIE vidieren. CAS nur lesen. Patientendaten nur VM, Logs nur Status-/Nummernzeilen.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.

## Was eingespielt wird
GitHub-Release **3.22.5** (main 3efea36), Asset `KaiScribe.exe` / `rakscribe26.exe`,
sha256 `03c2bd13854c625771ffa4ba91845e1a3c792af867e2cf7188e5bed096ecc0bf`. CI grün: Tests, Build Windows EXE, Windows UI-Test (EXE).
- **Neu: `KaiScribe.exe --sm-waechter`** = unsichtbarer SpeechMagic-Wächter als EIGENER Prozess (kein Fenster, keine Taskleiste,
  Mutex `Local\KaiScribe-SM-Waechter` je Windows-Sitzung, ein zweiter endet sofort). Fenster zu beendet ihn nie.
  - Startet sich: (a) jede KaiScribe-Fenster-Instanz (EXE) startet ihn beim Start + prüft jede Minute (falls keiner läuft);
    (b) er legt selbst den Autostart an: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KaiScribe SM-Waechter.lnk`
    → wscript → `%APPDATA%\KaiScribe\sm_waechter_start.vbs` (wartet auf die EXE auf X:, dann `--sm-waechter`).
  - Neue EXE an derselben Stelle → startet sie als Nachfolger (`--sm-waechter --nachfolger`) und endet, nie während eines
    offenen kp-SpeechMagic-Diktats. Merker bleibt `%LOCALAPPDATA%\RaKScribe\speechmagic` + `X:\KaiScribe\Daten\speechmagic`,
    wird jetzt direkt vor dem Einfügen neu gelesen (nie doppelt, auch prozessübergreifend).
  - Log (rakscribe.log neben der EXE): `[SM] Wächter-Prozess 3.22.5 gestartet (pid …)`, `[SM] Autostart Wächter: …`,
    `[SM] <Nr>: SpeechMagic-Diktat (kp) erkannt`, `[SM] <Nr>: n Zeile(n) (…) eingefügt`, `[SM] Wächter-Prozess endet: …`.
- Senf-Feld im KaiScribe-Fenster lädt alle **5 s** statt 15 s nach; neu im Log: `[SENF] <Nr>: Auftrag zu, Senf noch nicht da (…)`.
- Selbsttest/CI-Weg unverändert (dort Wächter weiter im Fenster-Thread, `sm_einfuegen: ok thread=ja`).

## Ablauf
1. Einspielen wie gewohnt (Memory „Release vom Hetzner“): Ordi-Hermes lädt das Asset direkt von GitHub, SHA prüfen,
   `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.22.5 -Sha <sha>`; alte EXE als `.alt` daneben. Laufende KaiScribe-Fenster
   an den Befund-PCs NICHT abschießen. Achtung: Die Sperre des Skripts (Mo–Fr 06:30–20:10) gilt. Peters Go für die
   Ordi-Zeit liegt vor (09:21/09:25). Falls das Skript keinen Override hat: den Tausch von Hand gleichwertig machen
   (Kopie → `.alt`, neue EXE, SHA prüfen), Belege ablegen.
2. **Wächter sofort aktiv machen (ohne Neustart)** an CASWS10 (Peter, kp) und am Testplatz: einmal `X:\KaiScribe\Programm\KaiScribe.exe
   --sm-waechter` in Peters Sitzung starten (z. B. geplante Aufgabe „einmal, interaktiv, Benutzer = angemeldeter“ oder wie
   sm_probe.ps1). Danach in rakscribe.log `Wächter-Prozess 3.22.5 gestartet` und `Autostart Wächter: … angelegt` belegen,
   Prozess mit Befehlszeile `--sm-waechter` genau 1× je Sitzung (Get-CimInstance Win32_Process).
3. **Abnahme 451898** (Werkzeuge/Ablauf aus `senf-ibl-speechmagic-paste-n1`, Belege damals `~/cj/work/senf-ibl-speechmagic-paste-n1/`
   l1–l3, `tools/sm_probe.ps1`). Pflichtfall **W1**: KaiScribe-Fenster KOMPLETT zu (kein KaiScribe-Fensterprozess, nur der
   Wächter) → SM-Diktat 451898 öffnen → `[SENF]` (bzw. „[SENF] unauffällig“) wird eingefügt; danach Fenster zu, erneut
   öffnen → nichts doppelt. **W2**: KaiScribe-Fenster offen → schließen → danach SM-Diktat → eingefügt (der Fall von heute
   08:13). **W3**: zweiter Wächter-Start → endet sofort (Log, nur 1 Prozess). Alles stornieren, nie vidieren. Rot → Rollback auf `.alt`.
4. **Brücken-Teil (ris-mods, Peter 09:25 Punkt b):** Die Brücke soll bei JEDEM Aufruf für ein Kürzel aus SM_SENF/SM_IBL
   (kp) vor dem SpeechMagic-Start bzw. vor der Übergabe an KaiScribe einmal `"<KaiScribe.exe>" --sm-waechter` starten
   (unsichtbar, nicht warten; läuft schon einer, endet der neue sofort per Mutex). KaiScribe 3.22.5 deckt das schon über
   den Fenster-Start + Autostart ab; der Brücken-Aufruf ist die zusätzliche Sicherung für Diktate, bei denen KaiScribe
   nie startet. In ris-mods `bruecke/` umsetzen + testen + einspielen, wenn die Brücke ohnehin angefasst werden darf;
   sonst als eigene Karte (Spalte tun) und im Bericht nennen.
5. **Erster echter kp-Fall** heute: rakscribe.log zeigt `Wächter-Prozess` überlebt das `fenster_zu`, dann
   `[SM] <Nr>: … eingefügt`. Nur Diktatnummern im Bericht.
6. Bericht ≤ 10 Zeilen (keine Patiententexte), Bericht-Datei ins Repo `BERICHT-SM-WAECHTER-BLEIBT-N1.md`.

## Lücken aus Teil 1 (ohne Büro-PC nicht belegbar)
- Der Start eines PyInstaller-onefile-Kinds aus dem Fenster (`PYINSTALLER_RESET_ENVIRONMENT=1`, `_PYI*`/`_MEIPASS2` entfernt)
  ist nur offline getestet: belegen, dass der Wächter nach dem Schließen des Fensters weiterläuft (Prozess + Log), und dass
  das Fenster-Temp `_MEI…` des geschlossenen Fensters nicht vom Wächter benutzt wird.
- Autostart-Verknüpfung über wscript am echten PC (ESET!) nicht belegt → Log `[SM] Autostart Wächter: … angelegt` prüfen;
  bei „NICHT angelegt“ die Verknüpfung per Ordi-Hermes anlegen und Karte.
- Ob `WM_SAVE_YOURSELF` bei der Windows-Abmeldung ankommt, ist offen (Windows beendet den Prozess bei der Abmeldung ohnehin).
- Senf-Feld: heute kein einziges `[SENF] … fertig` im Log. Das passt zu „Senf kommt 2–4 min, Peter diktiert schneller“
  (VM spiegelt jede Minute nach X:). Mit 3.22.5 steht beim Auftragsende `[SENF] <Nr>: Auftrag zu, Senf noch nicht da`
  → am ersten Tag zählen, wie oft der Senf nur knapp verpasst wird.
