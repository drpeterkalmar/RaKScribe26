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

---
## Nachtrag Abnahme + Einspielen (kaiscribe-schulter-ergebnis-n1-abnahme, 24./25.11.2026 20:42–00:15)

**Kurzbericht für Georg (≤ 8 Zeilen):**
1. Seit 24.11. 23:43 ist **KaiScribe 3.28.1** auf X: (Release „Latest“). Es enthält deine Punkte 48–70, Ursulas Punkte, die Rho-Regel/HIPPO ≥ 10 mm und den Wächter-Fix.
2. Vorher geprüft am Testpatienten 451898 (echte KI, Brief in CAS-Form, Fettdruck im Word-Brief): **alle Fälle grün** – Schulter (Reihenfolge, Enkapsulation, „Ergebnis:“ fett), Sono Bursitis, Bandausriss, Nur Text, Becken+Hüfte als ein Befund, Knie ohne KOALA, K&L 4/2 und MTP-I Grad 2, „zweitens …“ als Punkt 2, Rho nur LWS ≥ 7, HIPPO 13 mm + BLD 20 mm.
3. Zwei Fehler habe ich dabei gefunden und behoben: K&L-Grad fehlte bei „Coxarthrose links hochgradig, rechts gering“ (3.27.1), und die Beinlängendifferenz ≥ 10 mm kam nicht ins Ergebnis (3.28.1).
4. Startet nach der Anmeldung nur der SpeechMagic-Wächter, öffnet KaiScribe jetzt trotzdem von selbst. Am Büro-PC ist das mit Brücke 2.5.35 belegt („angenommen nach 8 s“, keine „keine Antwort“). Die Kontrolle an allen PCs folgt morgen ab 07:35.
5. Die Spracherkennung zeigt bei kp während der Aufnahme keinen Live-Text mehr (spart Kosten). Der Text kommt 1–3 s nach Stopp/INS.
6. Noch nicht testbar: „Ganzbein re.“ (der Testpatient hat kein Ganzbein-Kürzel mit Seite) und das Nachdiktat nach dem GWS-Gerüst (RH 130), dieses nur offline.

**Abnahme-Matrix (451898, Büro-PC, Testkopie als Gast, getipptes Diktat bzw. gesprochene WAV, echte KI, EOL → `<Nr>.rakscribe.txt`, Formatierer-Kopie → RTF):**

| Fall | Stand | Ergebnis |
|---|---|---|
| A Schulter re (K&L 2, Enthesiopathie, AC) | 3.26.2 / 3.27.1 / 3.28.1 + gesprochen live 3.28.1 | grün: Gelenk → AC → „Ansonsten …“ → „Kortikale Unregelmäßigkeiten … Tuberculum majus“; Ergebnis Omarthrose (Grad 2) → AC → Enthesiopathie; Titel + „Ergebnis:“ fett |
| B Kalkdepot Enkapsulation, „Ergebnis Doppelpunkt“ | 3.26.2 | grün (Enkapsulation, kein „Doppelpunkt“-Wort, Ergebnis fett) |
| C Sono Schulter Bursitis | 3.26.2 (usschul) | grün: Bursa-Normalsatz ersetzt durch den Bursitis-Satz an seiner Stelle (Step-sign-Normalsatz bleibt, richtig) |
| D Fuß + Bandausriss 9 mm | 3.26.2 (fussr) | grün: Fraktur an der Kortikalis-Stelle, danach „Im Übrigen glatte …“, keine Warnung |
| E Nur Text Sono Weichteile | 3.26.2 (usweich) | grün (mehrzeilig diktiert): Titel + „Ergebnis“ als Überschrift, im Word-Brief fett. Einzeilig („… Ergebnis: …“ mitten im Satz) bleibt es Fließtext – so gebaut |
| F1 „Beckenübersicht und Hüfte rechts …“ | 3.26.2 ×2, 3.27.1 ×2, 3.28.1 | 4/5 ein Kombibefund. 1× (3.26.2) lieferte die KI trotz Kombi-Abschnitt zwei Titel → Karte #566 |
| F2 getrennt diktiert | 3.26.2 | grün, zwei Teile |
| G Knie li unauffällig | 3.26.2 (kniel) | grün, kein KOALA/Grad |
| H Coxarthrose li hochgradig / re gering | 3.26.2 **rot** → 3.27.1/3.28.1 grün | Fix 3.27.1 (Seite vor dem Adjektiv): Grad 4 / Grad 2 |
| I MTP-I gering | 3.26.2 (vofur) | grün, Grad 2 |
| J „zweitens …“ (gesprochenes Nachdiktat) | 3.27.1 / 3.28.1 | grün: Punkt 2 eingefügt, Rest rückt nach („Ergänzung eingebaut“) |
| K GWS + Nachdiktat Funktionsaufnahmen | 3.27.1 | Nachdiktat als Satz in den LWS-Abschnitt eingebaut, Titel bleibt. Die 4 Teile aus RH 130 (Gerüst) ließen sich so nicht nachstellen, nur offline belegt (test_schulter_ergebnis 67) |
| G1 Ursula Ganzbein | 3.27.1 (uex1) | nicht prüfbar: im Katalog PRIVAT gibt es kein „Ganzbein re.“, uex1 hat keine Seite |
| H1 Ursula HWS 50 % | 3.27.1 / 3.28.1 | grün: „50%ige Höhenminderung“ bzw. „um 50 %“, Titel ohne „beidseits“, keine Leerzeile, „Im Übrigen“ nie doppelt |
| K1 Ursula Knie | 3.27.1 | grün |
| R1 / R2 / R3 Rho | 3.27.1 / 3.28.1 | grün: Hand Rho 9 → nichts; LWS 8 → Screening-Teil + „Osteopenischer Knochenaspekt“; LWS 6 → nichts |
| M13 / M9 HIPPO | 3.27.1 M13 **rot** → 3.28.1 grün | Brücke 2.5.35 reicht `ergebnis_becken` nicht durch → 3.28.1 lädt es aus der Ablage (Log „nachgeladen … Becken ≥ 10 mm“); 13 mm + BLD 20 mm als Punkte 1/2; 9 mm nur Beschreibung. Brücken-Fix: Karte #565 |
| E1 / E4b / E5 (diktat_e2e, gesprochen, kp) | 3.27.1 / 3.28.1 | grün: kein Streaming, chirp_3 „Text links nach 2,4–2,9 s“, Markierung ersetzt, STT-Ausfall → WAV behalten, kein Befund. Nebenbefund E4b: alter K&L-Grad bleibt nach dem Überdiktieren → Karte #567 |

- Einspielen: Brücke **2.5.35** (ris-mods e384203) per `kaiscribe_x_tauschen.ps1 2.1 -Schritt py` (21:01, Sicherung
  `X:\KaiScribe\_alt\Py-diktat-vor-2.5.35-20261124-210105`). EXE **3.28.1** per `-Schritt exe -Tag 3.28.1` (23:43, Sicherungen
  `*.vor3.28.1-20261124-23435x.alt` = 3.26.1, Rückweg `-Schritt zurueck`). Fenster + Wächter 3.28.1 (Nachfolger), 0 Fehlerzeilen.
  Release 3.28.1 ist genau die abgenommene Datei: sha256 `0707bbe506f57ac49f824e46598af4bde1c9a7609b0de574daa337ba4d07f89d`
  (Test-Build 45496757707 zum Release befördert, nicht neu gebaut); Windows-UI-Test grün; Web live 3.28.1.
- Alle 47 Testeinträge (20261124177–223) storniert, nichts vidiert, 0 Briefe. 20261124176 (DEXA-Sperre, nicht von diesem Job) nicht angefasst.
- Versehen: Die Versionsnummer 3.26.3 lag kurz unter dem parallel gepushten 3.27.0. Ich habe sie sofort auf 3.27.1 korrigiert;
  aus 3.26.3 wurde nichts gebaut (Lauf abgebrochen).
- Belege: `~/cj/work/kaiscribe-schulter-ergebnis-n1-abnahme/` (a1–a7 Aufträge + Antworten), Büro-PC `A\ergebnis_abend_a2…a7.md`.
