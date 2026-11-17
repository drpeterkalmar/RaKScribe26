# Bericht kaiscribe-kniepat-titel-n1-einspielen-f1 (Di 17.11.2026, Hetzner + Büro-PC)

## Kurz
1. **Eingespielt: KaiScribe 3.19.8** auf X: am 17.11. 23:46:47 (ein Tausch für Knie + Patella axial [3.19.4] und Funktionsaufnahmen [3.19.6, Commit 1c10a4c]; 3.19.7 und 3.19.8 enthalten außerdem LAMA-Ergebnistext und FROG-Fußtext).
2. **Abnahme am Testpatienten 451898: nicht gemacht** (weder Knie noch Funktion). Die Teststrecke KS braucht den Mac (Sprachausgabe + RDP-Mikrofon), vom Hetzner gibt es das nicht; getippte Ersatzdiktate nachts am offenen CAS wurden wie im Vorjob nicht riskiert.
3. Deshalb **kein "OK"-Ergebnisfile** `ris-mods/ordi-hermes/ergebnis_kaiscribe_funktion_20261117.md` und **Kanban #344 bleibt offen** (nicht live belegt). Keine Meldung nach außen.

## Tore
- Zeitfenster: Start 23:39, im Fenster 20:10–06:30, kein `-f2` nötig.
- Release 3.19.8 (Tag Commit 795f865): `git merge-base --is-ancestor` ja für 1a3512d (3.19.4 Knie) und 1c10a4c (Funktion). Build 44190573020 grün, Windows-UI-Test 44190925239 grün (abgewartet). SHA256 aus der API `efd31f9ac8fde8eb58ac4261526afd79cb571436e40c09f7db5bb5cbe46ab96f`, 56.826.917 B.
- Älter grün wäre 3.19.7 (UI-Test grün) gewesen; es wurde das neueste grüne genommen.
- Lage vorher (Ordi-Lesejob KF1, `docs/einspielen/kniepat_funktion_einspielen/b1*.txt`): X: = 3.19.4 (sha 5e1308dc46a5), keine Aufnahme (letztes [RECORD] 17:09, letztes Diktat vor 396 min). Wer am Büro-PC verbunden ist, hat Ordi-Hermes nicht geprüft (dort verboten); Tageszeit und fehlende Aktivität sprechen für niemand.

## Tausch (Job KF2, `b2*.txt`)
- EXE direkt von github.com nach `%LOCALAPPDATA%\hermes\work\ks_tausch\v3.19.8\`, SHA exakt gleich, dann `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.19.8 -Sha …` (ris-mods main b93bba0), Exit 0.
- `KS_TAUSCH=ok SCHRITT=exe neu=efd31f9ac8fd alt=5e1308dc46a5 sicherung=rakscribe26.exe.vor3.19.8-20261117-234647.alt neu_gestartet=True`
- Nachher: Titel „KaiScribe 3.19.8 - Röntgen am Kai“, 17 [INIT]-Zeilen ohne Fehler, Speech/Gemini [OK], Prompt-Marker 2026-11-16-humeruskopf-artikel. Andere PCs (CASWS08/10): beim nächsten Start von X:.
- **Rückweg:** `kaiscribe_x_tauschen.ps1 -Schritt zurueck` (jüngste .alt = 3.19.4-Stand), nur außerhalb Mo–Fr 06:30–20:10.

## Offen (Abnahme, nur vom Mac aus)
- Testpatient 451898 (nie vidieren):
  1. Knie: Leistung kniepatl, Diktat wie im Brief → Titel „Kniegelenk links in 2 Ebenen mit Patella axial“.
  2. Funktion: Leistungen hwsmf + kp („Schultergelenk rechts“), Diktat wie RH 97 → drei Titel (Schultergelenk rechts in 2 Ebenen / Halswirbelsäule in 2 Ebenen / Funktionsaufnahmen der Halswirbelsäule), Logzeile „[CAS] Funktionsaufnahmen der Halswirbelsäule: laut CAS (hwsmf) …“.
  3. Ersatzweise ohne Mikrofon: Lauf-Dateien echter Fälle mit hwsmf/kniepat* ab 17.11. 23:47 lesend prüfen (`vorlagen`, `kaiscribe` = 3.19.8).
- Lücke aus Teil 1 unverändert: nicht geprüft, ob die Teststrecke hwsmf/kniepatl als Leistung anlegen kann; sonst cas_leistungen-Datei aus dem Brief.
- Danach: `ergebnis_kaiscribe_funktion_20261117.md` (OK, 1c10a4c, 3.19.8) in ris-mods, `kanban.py fertig 344`.
