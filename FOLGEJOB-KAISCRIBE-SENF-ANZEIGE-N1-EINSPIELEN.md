# kaiscribe-senf-anzeige-n1-einspielen – Senf-Feld für kp auf X: bringen, Abnahme am Testpatienten 451898

Von `kaiscribe-senf-anzeige-n1` (Sa 21.11.2026, Mac, Leicht-Spur ohne Büro-PC). Brief:
`~/.hermes/claude-jobs/briefs/kaiscribe-senf-anzeige-n1.md` (Teil 2, Regeln gelten vollständig).

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.

## Was eingespielt wird
KaiScribe **≥ 3.21.0** (main, Commits `kaiscribe-senf-anzeige-n1`): eigene Zeile „Senf – nur Hinweis“ unter dem CAS-Band,
nur für Kürzel aus `SENF_ANZEIGE` (Standard `kp`). Liest `X:\RaKScribe\Daten\senf\<Diktatnummer>.json` (ris-mods
opus_senf 1.7.0, seit 20.11. 19:55 live) nur lesend, im Hintergrund, Frist 1 s. Anzeige: „Senf läuft…“ (alle 15 s nachladen,
max. 10 min) · „Senf: unauffällig“ · Zeile(n) · „Senf: kein Ergebnis“. Markier-/kopierbar (Strg+A/Strg+C, Knopf
„⧉ Kopieren“), sonst nie in Befund/EOL/Lauf-Datei/Zwischenablage. Keine Ablage → Zeile aus.

## Tore
- **EXE-Release 3.21.0 ist noch NICHT gebaut** (main `bb88ae7`, GitHub `Tests` + Pages-Deploy grün; der Bau läuft nur per
  Hand, damit „Latest“ erst mit der Abnahme kommt): `gh workflow run build-exe.yml -f version=3.21.0` (bzw. auf dem dann
  aktuellen main-Stand mit dessen VERSION), danach `Windows UI-Test (EXE)` abwarten.
- Tests (GitHub `Tests` grün auf dem eingespielten Commit, enthält `tests/offline/test_senf_anzeige.py`), Build EXE,
  Windows-UI-Test zur Version grün.
- Einspielen nur nach Ordi-Schluss (Mo–Do ab 20:15, Fr ab 13:30, Wochenende). Kein Klick am Büro-PC während der Ordi.
- Einspielweg wie 3.20.5 (`BERICHT-GEORG-2011-ABNAHME.md`): `X:\KaiScribe\KaiScribe.exe`, Rückweg `.alt` = 3.20.5.
  Testkopie-EXE nie im selben Ordner austauschen (ESET, Kanban #461).

## Abnahme am Testpatienten 451898 (nie vidieren; Release-Regel Georg)
451898 läuft im Senf nie mit → Ergebnis von Hand in die Ablage legen, danach wieder entfernen.
1. Diktatnummer `<Nr>` des 451898-Testeintrags bestimmen (Brücke-Log `nr=` beim Öffnen).
2. **Kürzel:** Das Feld erscheint nur, wenn die Brücke `benutzer=kp` meldet. Ist am Büro-PC ein anderes Kürzel angemeldet,
   für die Dauer der Abnahme (Wochenende/abends) in der `config.ini` neben der EXE auf X: `SENF_ANZEIGE = kp, <kürzel>`
   setzen und danach wieder entfernen (gilt für alle PCs!). Keine Regel/kein Register sonst anfassen.
3. VM (als rakauto-Aufgabe, sonst kein X:): `vm_senf.py ablage --nr <Nr> --status laeuft` → Diktat öffnen → Zeile
   „Senf läuft…“ (Screenshot/Log `[SENF] <Nr>: laeuft`).
4. `vm_senf.py ablage --nr <Nr> --status fertig --befund auffaellig --zeile "RH 0 · Probe · TESTSENF bitte ignorieren"` →
   innerhalb von 15 s steht die Zeile im Feld (Screenshot; Log `[SENF] <Nr>: fertig`).
5. Knopf „⧉ Kopieren“ → Zwischenablage = die TESTSENF-Zeile (Log `[SENF] kopiert … Knopf`). Danach Testbefund bzw.
   kurzes Diktat, **EOL** → CAS-Brief (Textauszug) enthält **kein** „TESTSENF“/„RH 0“; Lauf-Datei
   `X:\…\Daten\laeufe\<Nr>_*.json` ebenso nicht (nur lesend prüfen).
6. Gegenprobe Kürzel: ein Auftrag mit anderem Kürzel (rg o. ä.) → keine Zeile, kein `[SENF]`-Log.
7. Aufräumen: `vm_senf.py ablage --nr <Nr> --weg`, `config.ini` zurück, Testeintrag stornieren wie üblich.
Belege (Screenshot oder Log + Briefauszug) in den Bericht, keine Patientendaten. Weicht etwas ab: Rückweg `.alt`, Grund in
den Bericht, nichts „live“ melden.

## Danach
- Am nächsten Ordi-Morgen (Mo 23.11.) den ersten echten kp-Fall prüfen: KaiScribe-Log `[SENF] <Nr>: fertig|laeuft|kein`,
  CAS-Brief ohne Senf-Zeile; VM `ablage_takt n ≥ 1` (siehe ris-mods `BERICHT_opus_senf_n8.md`). Als Einmal-Kontrolljob
  einreihen (Zustellung local).
- Bericht ≤ 10 Zeilen nach `BERICHT-SENF-ANZEIGE-N1.md` (Abschnitt „Einspielen“) ergänzen.
