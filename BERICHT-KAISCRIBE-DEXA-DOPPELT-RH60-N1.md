# Bericht kaiscribe-dexa-doppelt-rh60-n1 (Teil 1, Mi 25.11.2026, Mac, ohne Büro-PC)

- **Ursache (belegt, Nachbau im Test):** Es war nicht die GWS-Regel. Die Ursache ist `nicht_diktiert_ergaenzen` aus `kaiscribe-georg-2011-n1`
  (3.19.20, live mit 3.20.5 seit Sa 21.11. 04:42). Jede nicht diktierte CAS-Leistung mit Vorlage bekommt dort einen Normalbefund aus der Vorlage.
  Die Brücke ordnet dexa/dexaneu/dxf/od/odh der Vorlage `knochendichtemessung_dexa` zu (ris-mods `katalog/kuerzel_vorlage.tsv`).
  Darum stand in jeder Kombi Rö/US + DEXA die leere DEXA-Vorlage mit `[Wert_LWS]` … und „Unauffälliger Befund.“, darüber die Prüfzeile
  „Osteodensitometrie laut CAS, nicht diktiert – Normalbefund …“. Zweiter Weg: Stand irgendwo im Rö-Diktat „Knochendichte“,
  griff die Erkennung schon deshalb zur DEXA-Vorlage (die DEXA-Regel kam vor allen Regionen).
- **Betroffene Briefe seit 20.11.:** am Mac nicht zählbar (keine VM-Logs). Theoretisch ist jede Kombi mit DEXA seit Mo 23.11. betroffen. Belegt ist bisher nur RH 60.
  Die Zählung (nur Anzahl + RH-Nr.) macht Teil 2 auf der VM.
- **Fix **3.28.3** (EXE = Web):** DEXA-Leistungen zählen nicht mehr zur Vorlagenwahl. Sie bekommen keinen Abschnitt, keinen Normalbefund
  und keinen Hinweis und bleiben nur Auskunft für die Rho-Regel. Die Erkennung wählt die DEXA-Vorlage nie mehr: Bei DEXA-Wörtern entscheidet
  der übrige Text, sonst gilt „allgemein“. Neu ist ein Platzhalter-Wächter: Ein unbefülltes `[…]` wird im Brief zu „…“ und erscheint als rote Prüfzeile.
  Die GWS-Seitlich-Logik ist unverändert. Ordi-Bausteine (osteokal, A1 … C3) sind nicht betroffen.
- **Tests:** neu `tests/offline/test_dexa_doppelt.py` mit 34 Prüfungen (Kombi DEXA+Rö, DEXA+US, reine DEXA, GWS a.p.+seitlich, reiner Rö, Wächter
  EXE = Web), steht in der CI. Fixtures angepasst: DEXA-Namen führen zu „allgemein“, und es gibt 5 neue Paritätsfälle. Regel-Register +2.
  Alle Offline-Gates sind grün. Ausnahme sind die bekannten Mac-Umgebungsfehler (cas_auftrag, maske_ablauf, live_anzeige_aus, deploy_guard),
  die auf main genauso rot sind. Web: pipeline/speechmike/audio/llm-Tests, tsc und eslint sind grün.
- **Probe 451898:** offen, kommt in Teil 2 (`kaiscribe-dexa-doppelt-rh60-n1-einspielen`, ab 17:35).
- **Satz für Ursula:** „KaiScribe fügt ab dem Einspielen heute Abend (ab Do 26.11. früh) bei DEXA in Kombination mit Röntgen/Ultraschall keine DEXA-Vorlage
  mehr ein. Den DEXA-Teil fügen wie früher Sie ein, bei reiner DEXA der Roboter. Neu war das seit 21.11., es war ein Fehler.“

## Teil 2 (Mi 25.11.2026 abends, Hetzner): Einspielen NICHT gelungen, Stand ROT/offen
- **Gebaut/geprüft:** main war inzwischen 3.29.0 (enthält 3.28.3). Pages-Deploy 3.29.0 grün, Live-Seite zeigt 3.29.0 (Pages-Hänger ist weg). Build Windows EXE (Lauf 45693720929) und Windows-UI-Test (45694137423) grün. Release-SHA256 `dd7f71e345949e87739d5fd28ec4bbdb01c795e7be2087683befc1c01f58649b`, auf dem Büro-PC unter `ks_tausch\v3.29.0` geholt und geprüft.
- **Tausch:** `-Schritt exe -Tag 3.29.0` lief 21:41–23:28, 50 Versuche, immer „belegt: X:\KaiScribe\Programm\KaiScribe.exe nicht umbenennbar“. X: steht unverändert auf 3.28.2 (b9294f9aaa75). Kein `-Trotzdem`, nichts beendet.
  Ursache offen: entweder KaiScribe an einem anderen PC (CASWS03/CASWS15 hatten heute Aktivität) oder die zwei SM-Wächter am Büro-PC, die direkt von der X:-EXE laufen.
- **Folge:** Abnahme 451898 (B), Zählung betroffener Briefe und RH 60 (C) und der Satz für Ursula (D) sind **nicht** gemacht, weil nichts live ist. Es gibt keine Uhrzeit für Ursula. Keine Meldung nach außen.
- **Nächster Versuch:** Kanban-Karte in Spalte tun (Folgejob). Dort zuerst klären, wer die X:-EXE hält (Lesezugriff auf Dateiserver/andere PCs, Wächter-Prozesse am Büro-PC prüfen), dann Tausch mit 3.29.0 oder neuer wiederholen.
