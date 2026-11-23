# sm-senf-laenge-n1 – Teil 1 (Mo 23.11.2026)
- Ursache: `sm_einfuegen.senf_zeilen` schnitt jede Senf-Zeile hart bei 300 Zeichen ab („… stationär. (V“, RH 146).
- Fix 3.22.6 (main 74167d6, Release 3.22.6 Latest, sha256 e1f02503…af39): bis 1200 Zeichen ganz, länger → Schnitt am letzten „. “/„; “ + „ …“, nie mitten im Wort; `senf_anzeige.py` kürzt nicht je Zeile (unverändert).
- Tests: neue Prüfungen (>300 ganz, >1200 am Satzende, kein doppeltes Einfügen); CI grün (Tests, Build, Windows-UI-Test). Thread-Test misst jetzt die Mac-Timergenauigkeit.
- Wächter: Der Selbst-Neustart bei neuer EXE ist seit 3.22.5 eingebaut (Nachfolger, nie im offenen Diktat) → pid 12452 an CASWS10 sollte sich nach dem Tausch selbst ersetzen.
- Einspielen + Abnahme 451898 = Folgeauftrag `sm-senf-laenge-n1-einspielen` (FOLGEJOB-SM-SENF-LAENGE-N1-EINSPIELEN.md).
