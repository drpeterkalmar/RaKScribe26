# kaiscribe-georg-2011-kontrolle – erste echte Fälle mit KaiScribe 3.20.5 lesend prüfen (Mo 23.11.2026)

Von `kaiscribe-georg-2011-abnahme` (Sa 21.11.2026). Brief Punkt 6: „Montag 23.11. früh: erste echte Fälle (FROG, Mehrfach,
Knie, Rho) lesend prüfen und melden.“ Deutsch, betrieblich. **Nur lesen** – keine Klicks an Befund-PCs, kein CAS, keine
CAS-DB, kein C-MOVE/C-GET/C-STORE, keine DICOM-Header, keine Patientendaten in Bericht/Log (nur Zähler, Kategorien, Uhrzeiten,
Versionen; Befundtext höchstens anonymisiert ohne Nummer/Name). MELDUNGSRUHE: nichts selbst an Telegram; Peter nur über
`kanban.py peter …` bei Handlungsbedarf.

## Stand (eingespielt 21.11.2026)
- KaiScribe **3.20.5** auf `X:\RaKScribe\rakscribe26.exe` seit 04:42 (Rückweg: `kaiscribe_x_tauschen.ps1 -Schritt zurueck`
  = 3.19.15, Sicherung `rakscribe26.exe.vor3.20.5-20261121-044243.alt`). Brücke 2.5.26 (XQ + Büro-PC), VM-Formatierer 2.5.26,
  Abholer 1.3.15 auf der VM. Bericht: `BERICHT-GEORG-2011-ABNAHME.md`.
- Andere Befund-PCs starten 3.20.5 beim nächsten KaiScribe-Start von X: (Brücke dort ggf. älter → KaiScribe holt FROG/HIPPO-Text
  selbst aus der Ablage).

## Prüfen (VM als rakauto, Weg wie `tools/vm/ibl_laeufe_pruefen.py` / ris-mods `automaten_vm/mac/abholer_vm.py beleg`)
1. Lauf-Dateien `X:\RaKScribe\Daten\laeufe\*_20261123-*.json` mit `kaiscribe` = 3.20.5: Anzahl je PC; Fehler-/Traceback-Zeilen in
   `X:\RaKScribe\rakscribe.log` seit Mo 07:00 (Zähler + erste 120 Zeichen ohne Patientenbezug); WinError 10013/Token-Fehler
   (ESET „Anwendung geändert“ – am Büro-PC stand am 21.11. so ein Dialog für eine Testkopie)?
2. Je Kategorie die ersten echten Fälle (nur Zähler/Ja-Nein):
   - FROG: `ibl_zeilen` > 0, Messwerte bzw. Begriffe im Befund, „Anmerkung:“-Block, bei „ohne Diagnose“ Prüfzeile rot (Log
     `[IBL] Hinweise: … rot (Prüfzeile): n`).
   - Mehrfach (≥ 2 Vorlagen): Titel je Teil, nicht diktierte CAS-Teile mit eigenem Befund; LAMA-Anmerkung „/Traglinie des
     Ganzbeines“; Rho (diktiert) als letzter Block „Opportunistisches Knochendichtescreening (KI)“.
   - Knie beidseits: Befund beginnt mit der Stellung (nicht „Im Übrigen …“), Ergebnis rechts vor links, kein „KI:“-Punkt.
   - GWS a.p.: „Wirbelsäule: Normale Stellung. …“ ohne Skoliose, bzw. diktierte/SQUIRREL-Skoliose.
3. Brücke: `bruecke_*.log` – Versionen je PC, `[ablage] … zurückgestellt` (Punkt 3) vorgekommen? ok=True?
4. Ergebnis ≤ 15 Zeilen in `docs/einspielen/kontrolle_georg_2011_20261123.md`, commit + `claude_job.py zusammenfuehren --keine-tests`.
   Auffälligkeit → Kanban-Karte (Spalte tun) bzw. Folgeauftrag; bei echtem Fehler im Brief: `kanban.py peter …` mit 👉-Zeile.
   Kein echter Fall einer Kategorie: als „noch kein Fall“ vermerken (nicht raten), nächster Werktag als Folgeprüfung einreihen.
