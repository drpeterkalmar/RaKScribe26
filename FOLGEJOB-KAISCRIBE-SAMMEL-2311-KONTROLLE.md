# kaiscribe-sammel-2311-kontrolle – erster Ordi-Tag mit KaiScribe 3.24.1 (Markierung ersetzen, OSG gehalten, AC-Satz)

Von `kaiscribe-sammel-2311` (Bericht `BERICHT_kaiscribe-sammel-2311.md`). Nur LESEN (VM/Ordi nach 17:30, nie Mo 06:30–09:30),
Patientendaten bleiben auf der VM, Antwort nur Zähler/Logzeilen ohne Diktattext. MELDUNGSRUHE: Ergebnis als Kanban-Notiz.

1. `X:\KaiScribe\Programm\rakscribe.log` des Tages: alle Zeilen `[EINFÜGEN]` (Ersetzt markierten Text / Weiter diktieren:
   Markierung … bleibt / In der Pause neu markiert / In der Pause in den Befund geklickt / Markierung ersetzt (gleich|
   wiedergefunden|veraendert) / Cursor-Stelle nicht lesbar) mit Zeit; Traceback/EXCEPTION. Zählen: Ersetzungen gesamt,
   davon „veraendert“ (= Text der Markierung wurde in der Pause verändert → Hinweis „bitte prüfen“).
   Rot, wenn: ein „[EINFÜGEN] In der Pause in den Befund geklickt“ direkt nach einer Markierung OHNE Klick-Anlass auftritt
   (wie RH 156 vorher), ein Traceback in den neuen Pfaden, oder Peter meldet erneut „funzt ned“.
2. Live-Version an allen Befund-PCs = 3.24.1 (`bruecke_<PC>.log`/Fenstertitel), SM-Wächter 3.24.1.
3. #377: Lauf-Dateien mit CAS sglg/sgrg/sgbg seit 24.11. → Titelzeile muss „… in 2 Ebenen mit gehaltenen Aufnahmen“ heißen.
4. #401: Schulter-Befunde des Tages: „Das AC-Gelenk ist altersentsprechend, keine Luxation.“ statt alter Form (Zähler).
Grün → Notiz auf Karte #377/#401, Bericht ≤ 6 Zeilen als Nachtrag in BERICHT_kaiscribe-sammel-2311.md. Rot → beheben
(eigener Commit, Version beim Zusammenführen) oder Rollback `kaiscribe_x_tauschen.ps1 -Schritt zurueck` + Karte (tun).
