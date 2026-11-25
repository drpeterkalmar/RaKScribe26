# kaiscribe-sammel-2311-kontrolle-f1 – Markierung ersetzen / OSG gehalten / AC-Satz am ersten ECHTEN Ordi-Tag (ab Mi 25.11. 17:45)

Von `kaiscribe-sammel-2311-kontrolle` (Nachtrag in `BERICHT_kaiscribe-sammel-2311.md`). Am 24.11. gab es an den Befund-PCs
KEINEN Befund über das KaiScribe-Fenster (Diktate liefen nur über SpeechMagic/Wächter) → nichts zu belegen, nicht rot.
Live seit 24.11. 23:43: **KaiScribe 3.28.1** (enthält 3.24.1). Nur LESEN (nach 17:30, nie Mo 06:30–09:30), Patientendaten
bleiben auf der VM/dem Büro-PC, Antwort nur Zähler/Logzeilen. MELDUNGSRUHE: Ergebnis als Kanban-Notiz.

Lesewege (gelernt 25.11.): Lesen über **peer vm** (rakauto) – sieht dasselbe X: wie der Büro-PC. Das Log
`X:\KaiScribe\Programm\rakscribe.log` ist EINE geteilte Datei aller PCs (bisher nie rotiert, sonst .1–.4 mitlesen);
PC-Zuordnung über `[INIT] Nutzungszähler … (<PC>)` im Startblock + SpeechMike-Gerätenummer (0c1d = CASWS14, 0c1c = CASWS08).
Lauf-Dateien `X:\KaiScribe\Daten\laeufe\*.json` (Feld `rechner`) entstehen nur bei Befunden im KaiScribe-Fenster; die
CAS-Kürzel stehen nicht in der Datei → per DB-SELECT über die Nr. CASWS14-Läufe am Testpatienten (451898) nicht mitzählen.

1. Tag 25.11.: alle `[EINFÜGEN]`-Zeilen je PC mit Zeit (Ersetzt markierten Text / Weiter diktieren: Markierung … bleibt /
   In der Pause neu markiert / In der Pause in den Befund geklickt / Markierung ersetzt (gleich|wiedergefunden|veraendert) /
   Cursor-Stelle nicht lesbar), Traceback/EXCEPTION. Zähler: Ersetzungen, davon „veraendert“. Rot wie im Erstauftrag
   (Klick-Zeile direkt nach Markierung ohne Klick-Anlass, Traceback in den neuen Pfaden, Peter „funzt ned“).
2. Je Befund-PC: KaiScribe-Starts (Version aus `[SM] Wächter-Prozess <Version>`), Anzahl Läufe. Startet an einem PC das
   Fenster gar nicht (24.11.: CASWS10 ohne Startblock, #541) → nur Notiz auf #541, nicht hier beheben.
3. #377: Läufe mit sglg/sgrg/sgbg → Titelzeile „… in 2 Ebenen mit gehaltenen Aufnahmen“.
4. #401: Schulter-Röntgen (sch*) je Version: neuer Satz „Das AC-Gelenk ist altersentsprechend, keine Luxation.“ / alte Form /
   keiner (bei „keiner“: AC pathologisch diktiert? nur ja/nein).
Grün → Notiz #377/#401, ≤ 6 Zeilen Nachtrag. Wieder 0 echte Fälle → Notiz, EIN weiterer Versuch am nächsten Ordi-Tag
(f2), danach Belegpflicht auf Karte #345-Art „wartet auf ersten echten Fall“ umstellen. Rot → beheben (eigener Commit,
Version beim Zusammenführen) oder Rollback `kaiscribe_x_tauschen.ps1 -Schritt zurueck` + Karte (tun).
