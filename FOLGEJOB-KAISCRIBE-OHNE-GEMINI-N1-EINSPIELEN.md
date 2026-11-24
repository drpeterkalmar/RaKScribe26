# kaiscribe-ohne-gemini-n1-einspielen – KaiScribe @@VERSION@@ (kein Gemini-Rückfall) einspielen + Abnahme 451898

Von `kaiscribe-ohne-gemini-n1` (Teil 1 Di 24.11.2026 nachts am Hetzner, ohne Büro-PC; Bericht `BERICHT_kaiscribe-ohne-gemini-n1.md`).
Peter 23.11. ~22:30: „no gemini please derzeit“. Release-Regel (Georg): **erst echter Lauf am Testpatienten 451898 mit
Brieftext aktiv** – Log zeigt `Rückfall: aus` und einen Befund über `anthropic/claude-sonnet-5-5`, sonst Rollback.
451898 NIE vidieren. CAS nur über die Oberfläche. Ordi-Systeme nur Mo–Do ab 17:30, Fr ab 13:30, Wochenende, nachts bis
06:00; NIE Mo 06:30–09:30; Tausch-Sperre des Skripts Mo–Fr 06:30–20:10. Patientendaten nur auf der VM.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram/Mail. Was nur Peter kann → `kanban.py peter …` + „👉 …“.

## Was eingespielt wird
main **@@VERSION@@** (Versions-Commit „v@@VERSION@@: Kein Gemini-Rückfall …“) (Web ist mit dem Push schon live – im Bundle `ki_rueckfall`/„ohne KI (kein Rückfall)“
belegen). EXE: Vorabversion aus Teil 1 (siehe Bericht, Abschnitt Teil 2) bzw. `build-exe.yml` mit `release=true` erst
nach grüner Abnahme → Release @@VERSION@@ Latest, dann X:-Tausch mit dessen sha256
(`kaiscribe_x_tauschen.ps1 -Schritt exe -Tag @@VERSION@@ -Sha <sha>`, `.alt` bleibt = Rollback `-Schritt zurueck`).
Enthält alles bis @@VERSION@@ (auch 3.22.6 SM-Senf-Länge, 3.23.0 Georg 48–70, 3.23.1 Senf-Abgleich), falls die noch nicht auf X: sind.

## 1. Messung zuerst (VM/X:, nur lesen) – Lücke aus Teil 1
`X:\KaiScribe\Daten\nutzung\2026-11_*.json` (bzw. `X:\RaKScribe\Daten\nutzung`) + `tagesbericht_*` seit 16.11.:
Rückfälle je Grund (Frist/HTTP/Platzhalter/Maske/unvollständig), je PC und Tag; Dauer-p90/max der Claude-Aufrufe aus
`rakscribe.log` (`[KI] …maskiert (x.x s`) bzw. den Lauf-Dateien. Nur Zahlen/Kategorien als Nachtrag in den Bericht.
Teil-1-Beleg (Log 23.11.): 27 Claude-Aufrufe p90 4,6 s / max 7,3 s, 1 Rückfall (Korrektur unvollständig), 0 × Frist.
Liegt max auch über alle Tage deutlich unter 45 s, bleibt 45 (Begründung im Bericht); gibt es Frist-Fälle > 45 s → melden
als Karte (tun), nicht still ändern.

## 2. Abnahme 451898 (Testkopie am Büro-PC wie bei den letzten Abnahmen, eigener Ordner)
- `[INIT] Befund-KI: anthropic/claude-sonnet-5-5, Korrektur: … — maskiert, Rückfall: aus, Frist 45 s` im Log.
- Ein Diktat an 451898 mit Brieftext aktiv → `[KI] gen: Anbieter=anthropic claude-sonnet-5-5 maskiert (…)`, Befund im Brief.
- Kein `→ Gemini (Rückfall)` mehr im Log. Ausfall-Weg nur offline belegt (test_ohne_ki_ui.py) – nicht am PC provozieren.
- Nicht vidieren, alles stornieren.

## 3. Danach
Grün → Release + X:-Tausch, Kontrolle am nächsten Ordi-Tag: `tagesbericht_<Tag>.txt` hat die Zeile
„Ohne KI (kein Rückfall) …“, Rückfälle auf Gemini 0. Rot → nicht einspielen, beheben (eigener Commit, Version beim
Zusammenführen), Rollback falls schon getauscht. Bericht ≤ 6 Zeilen als Nachtrag in `BERICHT_kaiscribe-ohne-gemini-n1.md`
(Rückfall-Statistik, Beleg 451898, Version, Rückweg `KI_RUECKFALL = an`). Kanban-Notiz statt Meldung.
