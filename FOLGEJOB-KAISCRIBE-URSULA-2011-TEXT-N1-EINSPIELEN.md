# Teil 2 zu kaiscribe-ursula-2011-text-n1 – Einspielen + Abnahme (Ordi-Zeit, Büro-PC/VM)

Gebündelt per Nachtrag in den wartenden KaiScribe-Einspielauftrag (ein Einspielen, eine Abnahme-Runde je Abend).
Version/Commit: siehe `BERICHT_kaiscribe-ursula-2011-text-n1.md` („Version“). Regeln aus dem Hauptauftrag gelten:
Ordi-Systeme nur Mo–Do ab 17:30 / Fr ab 13:30 / WE, nie Mo 06:30–09:30; CAS nur über die Oberfläche; Patientendaten
bleiben auf der VM (an Anthropic nur maskiert); 451898 nie vidieren; Meldungsruhe (nur Kanban-Notizen, Bericht).

## A. Belege nachholen (nur lesen, VM)
Teil 1 durfte nicht an VM/Büro-PC – die Ursachen sind am Code belegt, nicht am echten Lauf. Je RH (Diktat
`20261120<RH>`, sonst 19./23.11. mit derselben RH-Nr., Treffer über die Überschriften bestätigen) aus Lauf-JSON
(X:\RaKScribe\Daten\laeufe\ bzw. X:\KaiScribe\Daten\laeufe\) + rakscribe.log NUR Struktur ausgeben (Überschriften,
„## “-Zeilen, Leerzeilen, Treffer der Wörter unten), keinen Befundtext:
- RH 31, 119: steht im KaiScribe-Ergebnis ein „## …“ (Ergebnistext als Überschrift) bzw. „## Ergebnis: Text“? → sonst Formatierer.
- RH 37: Leerzeile nach „## Ergebnis“ in der KaiScribe-Ausgabe? → sonst Formatierer (ris-format-ursula-2011-n1).
- RH 47 („Becken“ lose), RH 68 (BWS/LWS/Hüfte-Überschriften), RH 120 (leere „Defileeaufnahme Patella einseitig“,
  Ganzbein ohne Seite): Überschriften der KaiScribe-Ausgabe + CAS-Leistungen (Seite) im Lauf.
- RH 44/92/106: „Im Übrigen“-Zahl je Befund, „-prozentig“, Titel „HWS beidseits“ – aus der KI oder aus dem Wächter
  ([WIDERSPRUCH]-Logzeile)?
- RH 41 („trochanter“), RH 55 („Verklakung“), RH 59 („TH“): im Diktat (STT) oder erst in der KI-Ausgabe?
- RH 49 (Rho-Überschrift), RH 89/82 (Dosis bei Nervensono): Version des Laufs (3.19.x?) notieren.
Abweichung vom Teil-1-Befund → Folgejob/Kanban-Karte (Spalte tun), nicht still nachbauen.

## B. Einspielen
EXE der Version aus dem Bericht bauen (Release vom Hetzner per API-Token), X:-Tausch
`kaiscribe_x_tauschen.ps1 -Schritt exe -Tag <Version>`; danach Fenster + SM-Wächter in der neuen Version, `[INIT] …`,
0 Fehlerzeilen (Autostart-Falle #541: alter Wächter → Fenster ggf. von Hand starten). Rückweg: `-Schritt zurueck`.

## C. Abnahme am Testpatienten 451898 (echter Lauf, Brieftext aktiv, sonst Rollback)
Mit echter Spracherkennung (WAV, Werkzeug wie `tools/buero/markierung_abnahme.py` / ris-mods diktat_e2e), EOL →
Brieftext im CAS ansehen, Einträge stornieren, nichts vidieren:
1. CAS „Ganzbein re.“ (oder Knie re. + Ganzbein re.), Diktat ohne Seite → Brief-Titel „Ganzbeinaufnahme im Stand rechts“.
2. CAS HWS, Diktat „HWS: 50-prozentige Höhenminderung C5/6, Unkovertebralarthrose beidseits.“ → Titel ohne „beidseits“,
   „50%ige“, im Brief keine Leerzeile zwischen „Ergebnis:“ und dem Ergebnistext, kein „Im Übrigen“ doppelt hintereinander.
3. Gegenprobe: Knie mit kurzem diktierten Text bleibt; ein IB-Lab-Teil (LAMA) bleibt mit Titel.
Grün → Bericht ergänzen (Abnahme-Zeilen), Kanban-Notiz. Rot → Rückweg + Karte.
