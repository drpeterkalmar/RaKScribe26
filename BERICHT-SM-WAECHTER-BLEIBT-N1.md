# Bericht kaiscribe-sm-waechter-bleibt-n1 – Teil 1 (Bau, ohne Büro-PC), Mo 23.11.2026

- **Ursache:** Der SpeechMagic-Wächter lief im KaiScribe-Fenster. „Fenster zu“ (`_schliessen` → `_sm_thread.stop()` + `destroy`)
  hat ihn beendet. Beispiel: Diktat 20261123004 wurde 08:13:47 erkannt, das Fenster ging 08:13:50 zu, der Senf kam 08:15 und wurde nie eingefügt.
- **Fix 3.22.5 (main 3efea36, Release 3.22.5, CI: Tests + Build + Windows-UI-Test grün):** Der Wächter ist jetzt ein eigener
  unsichtbarer Prozess `KaiScribe.exe --sm-waechter`. Er läuft einmal je Windows-Sitzung (Mutex), ohne Fenster und ohne Taskleisten-Eintrag.
  Jede KaiScribe startet ihn, falls keiner läuft (beim Start und jede Minute). Er legt seinen Autostart selbst an.
  „Fenster zu“ beendet ihn nie. Bei einer neuen EXE startet er einen Nachfolger, aber nie mitten in einem kp-Diktat.
  Den Merker liest er direkt vor dem Einfügen neu, daher wird auch über mehrere Prozesse nie doppelt eingefügt.
- **Senf-Feld:** Das Nachladen selbst funktioniert, es war nur zu langsam. RH 20 (020) ist nachgestellt: Mit 15 s war der Senf vor EOL
  verpasst, mit 5 s ist er da. Jetzt wird alle 5 s nachgeladen. Neu im Log: `[SENF] <Nr>: Auftrag zu, Senf noch nicht da`.
- **Tests:** neu `tests/offline/test_sm_waechter_bleibt.py` (36 Prüfungen, u. a. „KaiScribe ganz zu → SM-Diktat → [SENF] eingefügt“).
  `test_senf_anzeige` und `test_sm_einfuegen` sind ergänzt. Die ganze Offline-Reihe (58 Dateien) ist grün.
- **Verworfen:** Die Variante „Fenster verstecken statt schließen“ habe ich nach Peters Korrektur (09:25) wieder ausgebaut.
  Sie liegt nur als Diff in `~/cj/work/kaiscribe-sm-waechter-bleibt-n1/`.
- **Offen → Teil 2 `kaiscribe-sm-waechter-bleibt-n1-einspielen`** (`FOLGEJOB-KAISCRIBE-SM-WAECHTER-BLEIBT-N1-EINSPIELEN.md`):
  Einspielen, den Wächter sofort einmal starten, Abnahme an 451898 (W1: KaiScribe ganz zu), Brücken-Aufruf in ris-mods,
  erster echter kp-Fall.
