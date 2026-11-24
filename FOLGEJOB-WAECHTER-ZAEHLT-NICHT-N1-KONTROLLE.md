# waechter-zaehlt-nicht-n1-kontrolle – Morgenkontrolle 25.11.2026 ab 07:35 (Kanban #541), NUR LESEN

Von `kaiscribe-schulter-ergebnis-n1-abnahme` (24./25.11. nachts). Stand: Brücke **2.5.35** auf X: (24.11. 21:01,
ris-mods e384203), KaiScribe **3.28.1** auf X: (24.11. 23:43, Release Latest, sha256 0707bbe5…f89d). Probe am Büro-PC
grün (nur Wächter → CAS-Diktat → „angenommen von RaKScribe 3.28.1 nach 8.0 s“, keine_antwort 0; Starter „gestartet
(minimiert)“). Bericht: `BERICHT-WAECHTER-ZAEHLT-NICHT-N1.md` Teil 2.

Regeln: nur lesen (Ordi-Zeit!), keine Klicks an Befund-PCs, CAS nur lesen, keine Patientendaten in Berichten
(nur Zeiten, Zählungen, PC-Namen, Versionen). Meldungsruhe (nur Kanban-Notiz, Bericht; die Queue meldet).

## Auftrag
1. Ab 07:35: alle `X:\KaiScribe\Daten\protokolle\bruecke_<PC>.log` (Rückfall `X:\RaKScribe\Daten\protokolle`) – je PC
   seit heute 06:00: Anzahl Zeilen mit „keine Antwort von RaKScribe“/`keine_antwort`, Anzahl „angenommen von RaKScribe
   <Version>“ (Version je PC), Anzahl „[rakscribe] gestartet“. CASWS10 besonders (Georg 24.11.).
2. Je PC die erste KaiScribe-Version des Tages (3.28.1 erwartet) und ob der Starter heute „gestartet (minimiert)“
   oder „KaiScribe läuft schon“ schrieb (soweit lesbar).
3. keine_antwort = 0 überall → Kanban #541 Notiz + **fertig**; Zeile im Bericht „Morgenkontrolle 25.11.: …“.
   Die Meldung an Georg („KaiScribe startet wieder von selbst, auch wenn nur der Wächter läuft“) schickt die Queue mit
   dem Abschluss – im Abschluss-Text eine Zeile dafür.
4. keine_antwort > 0: die Log-Zeilen (Zeit + Kurztext ohne Patientendaten) zitieren, Ursache eingrenzen (läuft dort
   noch eine alte Brücke < 2.5.35? alte EXE?), Folgejob bzw. Karte (Spalte tun); #541 bleibt offen.
5. Nebenbei (nur lesen, nur Zahlen), falls die Logs lesbar sind: in den rakscribe.log der kp-PCs seit 06:00 die Zeilen
   `[CHIRP3] Text links nach X s ab Stopp` (Median/Max – Messwert für BERICHT-KAISCRIBE-LIVE-ANZEIGE-AUS-KP-N1.md) und
   `[SM] … Pause erkannt`/`Sprachpegel nicht messbar` (Anzahl – Beleg für BERICHT-SM-SENF-DIKTATPAUSE-N1.md Teil 2).
