# Teil 2 zu kaiscribe-ergaenzung-ohne-ins-n1: KaiScribe 3.31.0 einspielen + Abnahme an 451898 (kp und rg)

Gebündelt mit `kaiscribe-nicht-diktiert-streichen-n1-einspielen` (Nachtrag dort): **nur EINMAL tauschen, direkt auf 3.31.0**
(main `7468767`). Es enthält 3.30.0 und alles davor. Bericht Teil 1: `BERICHT-KAISCRIBE-ERGAENZUNG-OHNE-INS-N1.md`.

Neu in 3.31.0 (Peter 26.11.2026, Diktat 20261126060): Ist rechts ein Cursor gesetzt oder eine Stelle markiert, geht es so:
Record → sprechen → Pause. Der Text steht dann sofort wörtlich an der Stelle bzw. ersetzt die Markierung. Links wird
nichts angehängt, ein INS ist nicht nötig, und EOL in der Pause schließt direkt ab. EOL während der Aufnahme fügt erst
ein, danach kommt „EOL nochmals“. „Erst INS“ gibt es nur, wenn rechts noch kein Befund steht. Fenster zu / CAS abbrechen
fragen bei offener Ergänzung nach, und „Befund kopieren“ fügt dann erst ein.

Regeln wie im Hauptauftrag: Ordi-Systeme nur Mo–Do ab 17:30, Fr ab 13:30 oder am Wochenende. 451898 nie vidieren, alles
stornieren. Nie in die CAS-DB schreiben. Keine Patientendaten nach außen, nur Nr./Abschnittsnamen. Meldungsruhe.

## A. Vorbedingung
GitHub: „Build Windows EXE“ und „Windows UI-Test (EXE)“ für `7468767` müssen grün sein (Release 3.31.0, SHA aus dem
API-`digest`). Im UI-Test muss der neue Fall „k“ grün sein („markiert → Record → Pause ⇒ steht SOFORT rechts …“, „… EOL
direkt danach schließt ab“). Ist etwas rot: nicht tauschen, Ursache beheben (Folgejob), nichts melden.

## B. Abnahme an 451898 mit der KaiScribe-KOPIE 3.31.0, VOR dem Tausch
Werkzeug `tools/buero/ergaenzung_abnahme.py` über ris-mods `e2e/diktat_e2e.py`, Muster wie `markierung_abnahme.py`:
Kopie als Gast, echter CAS-Auftrag, echte Spracherkennung aus den WAV-Dateien der Teststrecke, echte KI über Konto A.
Je Fall einen **frischen** Eintrag nehmen, denn eine benutzte Nr. wird abgelehnt.
1. **K1** (markieren → RECORD → sprechen → Pause → EOL, **kein INS**): erwartet `ERGABN=ok`, dazu `PAUSE_RECHTS=ja`,
   `LINKS_GLEICH=ja`, `STATUS=ja`, `EOL_DIREKT=ja`, `ABLAGE=ja`.
2. **K2** (Cursor ans Befund-Ende, ohne Markierung): ebenso `ERGABN=ok`.
3. Laut Auftrag **mit Befunder kp (Live-Anzeige aus) und rg (Live-Anzeige an)**. Ein Lauf je Befunder genügt, z. B. K1 mit
   kp und K2 mit rg. Im Log der Kopie muss stehen: `[EINFÜGEN] … (ohne INS)`, kein `[HINWEIS] Erst INS`, kein
   `[BEFUNDFELD] Restructure`.
4. Seitenbild ohne Patientendaten: nur den Befundbereich nach der Pause zuschneiden, mit Statuszeile „… steht rechts“.
   Ablage `docs/einspielen/ergaenzung_ohne_ins_451898.png`.
5. Alle Läufe stornieren, nie vidieren.
Bei Rot: nicht tauschen bzw. Rollback (`-Schritt zurueck`), Ursache beheben (Folgejob/Karte „tun“), nichts melden.
(`markierung_abnahme.py` M156/M165 prüft noch die alte Bedeutung „Markierung bis INS gehalten“ und ist ab 3.31.0 nicht
mehr maßgeblich.)

## C. Tausch
Wie im Hauptauftrag (`kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.31.0 -Sha <sha>`, Asset direkt von GitHub, `.alt`
bleibt). Wichtig ist der Hinweis zum X:-EXE-Halter (SM-Wächter). Beleg je PC über `bruecke_<PC>.log` bzw. den
Fenstertitel.

## D. Belege nachholen (Lücken aus Teil 1, Büro-PC-Log `X:\KaiScribe\Daten\…\rakscribe.log` + Lauf-Datei 20261126060)
1. 26.11. um 10:53:26: Steht dort `[GOOGLE] Live-Anzeige aus für …`, und für wen? Das erklärt, ob Peter links Live-Text
   angehängt sah oder erst das Nachdiktat-Bild.
2. Nach 10:56: `[CAS] … abgebrochen (fenster_zu)` bzw. `knopf`. War die Aufnahme da noch offen (RECORDING/PAUSED), wurde
   sie also verworfen? Nur Zeitstempel und Strukturzeilen, keine Inhalte.
3. Lauf-Datei 20261126060 (X:, Lauf-Ordner): (a) Welche CAS-Leistung bzw. Vorlage hat die orange Zeile „im Diktat genannt,
   aber KEIN eigener Befund“ ausgelöst (`cas_hinweise`, Vorlagenwahl)? (b) Steht „6 mm“ oder „0,6 mm“ im `stt_roh`, im
   korrigierten Text (Call 0) bzw. im Befund? Wer hat geändert? Kommt die Änderung von Call 0 oder vom Formulierer: Karte
   „Messwert-Wächter (diktierte Zahl ≠ Befundzahl → rote Prüfzeile)“ in „tun“ anlegen, keine Regel still ändern.
   Ergebnisse nur als Strukturangaben in den Bericht, ohne Patiententext.

## E. Bericht + Meldung (erst wenn belegt live)
Nachtrag in `BERICHT-KAISCRIBE-ERGAENZUNG-OHNE-INS-N1.md` (≤ 8 Zeilen): Version live seit, K1/K2 kp/rg, Bild, Belege D.
Der `## Abschluss` des Einspiel-Auftrags nennt zusätzlich in einfachen Sätzen, wie man ab jetzt dazudiktiert: „Stelle
rechts markieren oder Cursor setzen → Record → sprechen → Pause: steht sofort rechts, links bleibt alles; danach EOL, kein
INS, kein ‚Nur Text‘ nötig.“ Keine Meldung, solange nicht live.
