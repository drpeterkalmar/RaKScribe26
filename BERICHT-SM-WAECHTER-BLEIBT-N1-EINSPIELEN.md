# Bericht kaiscribe-sm-waechter-bleibt-n1-einspielen – KaiScribe 3.22.5 NICHT eingespielt (Mo 23.11.2026)

- **Stand: 3.22.5 ist noch nicht auf X:.** Büro-PC/X: unverändert (KaiScribe 3.22.4), nichts zurückgerollt, nichts abgeschossen.
- **Grund:** `kaiscribe_x_tauschen.ps1 -Schritt exe -Trotzdem` (Peters Wort 09:21/09:25 gegen die Mo–Fr-Zeitsperre) meldete 10:18–14:28
  ca. 120× `KS_TAUSCH=belegt … jüngste Ablage vor 0–9 min`. Die zweite Sperre des Skripts (mind. 20 min ohne neue Ablage, schützt laufende
  Diktate) blieb zu: an den anderen PCs wird montags durchgehend diktiert, längste Pause 13 min. Diese Ruhe-Prüfung wurde nicht umgangen.
- Release geprüft: `KaiScribe.exe`/`rakscribe26.exe` 56 692 284 B, sha256 03c2bd13…c0bf = GitHub-Digest; auf dem Büro-PC liegt die geprüfte
  Datei in `W\v3.22.5\` (SHA ok). Keine Netz-/ESET-Fehler. Auftrag an den Ordi-Hermes: `docs/einspielen/sm_waechter_n1/a1b_auftrag_ordi.txt`.
- **Nicht gemacht (hängt am Einspielen):** Wächter-Start/Autostart-Beleg, Abnahme 451898 W1–W3, Temp-/_MEI-Probe, erster echter kp-Fall.
- **Brücke (`--sm-waechter` bei jedem kp-Aufruf):** nicht gebaut, eigene Karte #510 (Spalte tun). KaiScribe 3.22.5 deckt es über Fenster-Start + Autostart ab.
- **Weiter:** Folgejob `kaiscribe-sm-waechter-bleibt-n1-einspielen-n2` heute ab 20:15 (Ordi-Schluss, Ruhe-Prüfung meist erfüllt): Tausch, W1–W3, Wächter am Büro-PC.
  CASWS10/Peters Sitzung: dort startet der Wächter erst mit dem nächsten KaiScribe-Start von X: (3.22.5) bzw. der Autostart-Verknüpfung; per Ordi-Hermes nicht erreichbar.
- 👉 Peter: Soll der Tausch früher als 20:15 gehen, muss die 20-min-Ruhe-Prüfung ausgesetzt werden (ein laufendes Diktat startet dann ggf. mit der neuen EXE). Sonst nichts zu tun.

## Nachtrag n2 (Mo 23.11.2026 ~16:20): 3.22.5 EINGESPIELT, Abnahme teilweise
- **Tausch ok 16:05** (auf Peters Wort 15:32, Ruhe-Prüfung nur dafür ausgesetzt, per temporärer Skriptkopie; Original unverändert): `KS_TAUSCH=ok`, neu 03c2bd13854c, Sicherungen `*.vor3.22.5-20261123-160517/160520.alt` (= 3.22.4, Rollback `-Schritt zurueck`). Titel „KaiScribe 3.22.5“, 0 Netz-/Fehlerzeilen, kein ESET-Dialog.
- **Wächter ok:** `[SM] Wächter-Prozess 3.22.5 gestartet (pid 8828)`, `Autostart Wächter: … Verknüpfung angelegt` (KaiScribe SM-Waechter.lnk + sm_waechter_start.vbs da). Eigene `_MEI`-Temp des Wächters, anders als die des Fensters.
- **W3 ok** (zweiter Start endet sofort, Exit 0). **Fenster zu → Wächter lebt weiter: ja.** Nie doppelt (DOPPELT=0).
- **W1 / W2-Diktatteil NICHT getestet:** tagsüber ist die Automaten-VM die CAS-Seite, am Büro-PC gibt es kein CasMed (nur ab 20:10 per `cas_anmelden -Test`). Nichts angelegt, 451898 unberührt, nichts vidiert.
- **Neuer Fehler:** Autostart-Starter (`warte_auf_x.vbs`, bereitschaft.py) hält den Wächter für das Fenster („läuft schon – nichts zu tun“) → Fenster kommt per Verknüpfung nicht wieder. Fenster wurde von Hand neu gestartet (3.22.5 läuft). Karte #517 (tun).
- Erster echter kp-Fall mit `[SENF]`: noch nicht belegt (offen, in #517 mitgeführt).
- Belege: ~/cj/work/kaiscribe-sm-waechter-bleibt-n1-einspielen-n2/ (warte2.txt, Aufträge).
