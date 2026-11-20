# Bericht kaiscribe-squirrel-ergebnistext-n1-kaiscribe (Teil 1, Fr 20.11.2026, Mac, ohne Büro-PC)

**Für den Einspiel-Auftrag `kaiscribe-squirrel-ergebnistext-n1-einspielen`:** Version **3.19.17** = Commit **71c1e1f**
(Änderung 53c5415). Release 3.19.17 ist „latest“: `rakscribe26.exe`, 56 591 459 Byte, sha256
`b73a6238b8e0ce4fabc73abc05e420344d404f3bbb86a34c4e4cc337d8ec2042`. Enthält auch 3.19.16 (Befundfeld). Der Auftrag
`kaiscribe-befundfeld-sicher-n1-einspielen-f1` hat dazu einen Nachtrag bekommen (ein Tausch je Abend).

## Was KaiScribe jetzt mit SQUIRREL macht (`source_code/ibl_bausteine.py`)
- Liest `befundtext.squirrel` (Abholer ≥ 1.3.14, Brücke 1.8.0). Ist die Brücke am PC älter, holt KaiScribe den Text aus der
  Ablage (`TEXT_MODULE` mit „squirrel“) und zeigt „Brücke veraltet“.
- **Ohne Krümmung im Diktat:** Die Skoliose-Sätze stehen an der Stelle des Achsensatzes. Bei GWS a.p. ist das
  „Wirbelsäule: Normale Stellung, flachbogige rechts-konvexe Skoliose.“, die Beschriftung bleibt. Bei der Gesamten
  Wirbelsäule (HWS/BWS/LWS) stehen sie als erster Absatz. Der Skoliose-Punkt ist der erste Ergebnispunkt, „Regelrechte
  Darstellung der Wirbelsäule.“ entfällt, die Schlussanmerkung steht ohne Nummer darunter.
- **Krümmung diktiert (Punkt 20):** Das gilt auch verneint, Kyphose/Lordose zählen nicht; das Muster ist wörtlich wie in
  ris-mods. Die Wortwahl des Arztes bleibt, nur der Cobb-Satz kommt dahinter, kein Ergebnissatz und nie „Skoliose“
  zusätzlich. Der Gen-Prompt sagt der KI dasselbe.
- **Punkt 40b:** Kyphose-/Lordose-Sätze bleiben. „Normaler Achsenverlauf“ und „achsengerechte Stellung“ entfallen, außer
  der Arzt hat sie selbst so diktiert.
- Wenn der Text da ist, kommen keine Messzeilen „Cobb-Winkel … (IB Lab SQUIRREL).“ mehr. Bei Metall gibt es nur die rote
  Prüfzeile. Hinweise mit „prüfen“ bekommen ein ⚠, und die IB-Lab-Hinweiszeile wird dann rot (Prüfzeilen zuerst).
- Unter 10° liefert der Abholer keinen Text. Dann bleibt alles wie in 3.19.15, also nur die Messzeilen. Regel 3s hat dazu
  eine Notiz bekommen.

## Tests
- Neu: `tests/offline/test_ibl_squirrel_text.py` mit 43 Prüfungen und Snapshot, in CI eingetragen. Die Bausteine dafür
  erzeugt `tools/squirrel_bausteine_erzeugen.py` aus dem Code von ris-mods (Fixture SQUIRREL_SR plus die Fälle aus dem
  Brief), ohne Patientendaten.
- Regel-Register: `ibl-squirrel`, `ibl-squirrel-diktat` und `ibl-squirrel-achse` sind neu, `ibl-text-immer` ist angepasst.
- Am Mac sind 47 von 49 Offline-Tests grün. `test_cas_auftrag` und `test_maske_ablauf` sind auch auf dem unveränderten main
  rot (Mac-Umgebung).
- GitHub: Tests 44794426568, Build EXE 44794464433, Windows-UI-Test 44794821420 grün; Web 3.19.17 live auf Pages.

## Offen
- Einspielen und Abnahme am Büro-PC macht der Folgeauftrag (dort sind auch Brücke 1.8.0 und Abholer 1.3.14 zu prüfen).
- Die GWS-Vorlage selbst enthält „flachbogige rechts-konvexe Skoliose“. Das ist mit SQUIRREL abgefangen, ohne SQUIRREL
  bleibt es eine Frage an `kaiscribe-gws-seitlich-vorlage-n1` (pausiert, noch nichts committet).
