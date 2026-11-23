# kaiscribe-schulter-ergebnis-n1 – Georgs Punkte 48–70 (22./23.11.2026)

**Für Georg (Stand 23.11. nachts: 3.23.0 gebaut, getestet, Web live; EXE noch NICHT auf X: – erst nach dem Testlauf an 451898):**
1. Schulter: Gelenk → AC → „Ansonsten die Gelenkflächen …“ → Enthesiopathie; „Enthesiopathie <Ort>“ wird im Befund „(Grad) kortikale Unregelmäßigkeiten und vermehrte Sklerosierung am <Ort>“; Ergebnis Omarthrose → AC → Enthesiopathie.
2. Sono: diktierte Bursitis/Bursaflüssigkeit/Step-sign streicht den Bursa-Normalsatz (Satz steht an seiner Stelle). Röntgen: Fraktur an die Kortikalis-Stelle, danach „Im Übrigen glatte …“; „Im Übrigen“ nur nach einer Pathologie.
3. Hüfte/Becken: TEP, Coxarthrose oder auffälliger LCE/AI → Hüftkopf-/Gelenkspalt-Normalsatz nur noch für die andere Seite; Beckenschiefstand ab 10 mm ins Ergebnis; „Regelrechte Darstellung“ trotz Pathologie → rote Prüfzeile; „Beckenübersicht und Hüfte …“ in einem Titel = ein Kombibefund; doppelte Teile werden zusammengelegt.
4. K&L: Grad immer aus dem Adjektiv derselben Diagnose (gering = 2, RH 94 gibt jetzt Grad 2), fehlende Klammer + Standardsatz je Seite (RH 88: 2 Punkte Grad 4/2). KOALA beim Knie ganz aus (Peter #514).
5. Ergebnis: Verlauf („unverändert zur Voruntersuchung …“) immer 1. Punkt; „zweitens …“ fügt Punkt 2 ein, die anderen rücken nach; Nerv unauffällig → „Unauffälliger Befund am N. … rechts.“ zuerst.
6. Nachdiktat ändert nur die diktierte Region: Ganzbein/LAMA- und GWS-Teile bleiben (RH 120/130), Funktionsaufnahmen kommen dazu, Skoliose bleibt im GWS-Teil.
7. Spracherkennung: Enkapsulation, Tuberculum Gerdy, periprothetische Fraktur, Dunn-Aufnahme, „unverändert zur Voruntersuchung“; Überschriften auch bei „Nur Text“ fett (KaiScribe-Anzeige/Zwischenablage).
8. Offen: Dunn aus dem Bildkopf (nur Diktat), Hüft-OP-Seite aus Bild (nur Prüfzeile), Fettdruck im Word-Brief bei Nur Text = Formatierer (ris-mods) – wird beim Testlauf geprüft.

---
## Technik (für den Einspiel-Job)
- **3.23.0** = main 9876a85; GitHub-Tests grün, Web live (Deploy 2× GitHub-Artefakt-Störung, 3. Lauf grün, Bundle belegt); EXE nur
  Vorabversion `test-45277048366` (sha256 9b41b309…ab53a), Latest bleibt 3.22.6 bis zur Abnahme. Tests: alle Gates
  aus test.yml grün mit /usr/bin/python3 außer den schon auf main roten `test_cas_auftrag` (ris-mods-Import, Py 3.9) und
  `test_maske_ablauf` (Umgebung); Node pipeline/speechmike/audio/llm_anbieter, `tsc`, `eslint` grün. Neu:
  `tests/offline/test_schulter_ergebnis.py` (26 Prüfungen, in CI), Fixtures `georg_2311` (30 + 4 Teile + 4 Nur-Text, EXE = Web, je zweimal gleich),
  6 befundfeld-Fälle (Punkt 62), 8 Fehlhör-Fälle, 22 Register-Einträge (`georg-*`), sichtbar geändert: `kl-koala` (AUS),
  `ergebnis-format` + Regel `9` (Verlauf = 1. Punkt). Prompt-Marker `2026-11-23-georg-schulter-ergebnis`.
- Ursachen aus den Lauf-Dateien (nur gelesen, Werkzeug `tools/vm/rh_ursache_bauen.py`, Ausgabe nur Vorlagensatz-Anfänge/Stichwörter):
  RH 30 (13:33) Hüft-Teil = Diktat oben + „Im Übrigen …“-Normalsätze, Becken-Teil = volle Normalvorlage + HIPPO, Ergebnis
  „Regelrechte Darstellung“ – kein Fallback/Timeout; Beckenschiefstand kommt vom Abholer nie als Ergebnispunkt (Punkt 6 war
  damit nicht wirksam). RH 59: Beckenübersicht doppelt, HIPPO-Sätze im LWS-Ergebnis. RH 88/94: K&L-Regel stand im Prompt, der
  Wächter prüfte nur vorhandene Klammern bzw. ließ bei mehreren Adjektiven den KI-Grad stehen. RH 120: KOALA-Modul im Lauf,
  Ganzbein von der KI neu geschrieben (Gerüst nicht protokolliert). RH 124: Unterarm-Vorlage + KI-Zusatzteil Handgelenk.
  RH 130: Diktat 6/2 Wörter → Befund im Gerüst-Modus ganz neu (1 Teil Funktionsaufnahmen + SQUIRREL). RH 92: 4 Teile richtig
  (Regression `georg_2311.teile` „RH 92 Positiv-Referenz“).
- Neue Wege: `befund_regeln.georg_2311` (am Ende von grundregeln), `teile_zusammenlegen`, `pruefzeilen_2311`,
  `nur_text_ueberschriften`; `befundfeld.ergebnis_einfuegen`/`geruest_erhalten` (Gerüst nur EXE); `pipeline._becken_huefte_kombi`
  (KOMBI_LISTE, Prothesen-Kombi-Titel), `_seite_hinweise`, `_pruefen`; `ibl_bausteine.KOALA_KNIE_AUTOMATIK = False`.
- Nicht gemacht: Bildkopf (Dunn/Seite Hüft-OP) – kein Header-Zugriff erlaubt, RH 47 nicht gelesen; Punkt 5 „Nur Text bleibt an“
  nicht neu nachgestellt (Auto-Aus beim neuen CAS-Auftrag ist seit 3.20 drin – beim Testlauf belegen); kein Live-KI-Lauf.
- Einspielen + Pflicht-Abnahme 451898 = Folgeauftrag `FOLGEJOB-KAISCRIBE-SCHULTER-ERGEBNIS-N1-EINSPIELEN.md`.
