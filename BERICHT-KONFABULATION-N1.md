# KaiScribe erfindet Befundinhalte (RH 38) – Bericht kaiscribe-konfabulation-n1 (12.11.2026)

**Kurz:** Ursache gefunden und behoben. Release **3.18.4** ist veröffentlicht (Latest, Windows-UI-Test 114/114), die
Web-App ist live. An die Befund-PCs kommt die EXE über das RaK-Befund-Paket. Das macht der Eiljob
`kaiscribe-nachvollzug-paket-n1` nach der Ordi-Zeit; er erweitert dabei auch die Brücke für die .rakscribe.json.

## Ursache
1. `radiology_prompt.txt`, Abschnitt „K&L-Graduierung (PFLICHT)“: Der Grad wurde **aus dem Adjektiv** abgeleitet
   (mäßig = 3), dazu kam der feste Deskriptor „… mit multiplen Osteophyten und subchondraler Sklerosierung“. Mit dem
   alten Prompt erfand die EXE-Kette das in 4 von 4 Läufen genau wie im Fall RH 38.
2. Web-Validator Regel 5: „Fehlt die Graduierung, ergänze sie aus dem Adjektiv“.
   Die Vorlage `kniegelenk_in_2_ebenen` enthält keine Pathologie, und es gibt keinen eigenen Ergebnis-Aufruf.

## Fix (EXE + Web)
- Prompt-Abschnitt „NUR DIKTIERTES – nichts erfinden, nichts weglassen“: Einzelbefunde, Diagnosen, Grade/Scores und
  Messwerte stehen nur, wenn sie diktiert sind oder aus dem IB-Lab-Block kommen. Dazu die gepaarte Erhalt-Regel: alles
  Diktierte steht in Befund **und** Ergebnis, Verhörer werden weiter zum Fachbegriff korrigiert. ❌/✅-Beispiel mit dem
  RH-38-Wortlaut.
- K&L nur aus dem Diktat oder aus IB Lab (KOALA, Seite beachten). Ein diktierter Grad geht vor, der IB-Lab-Grad wird
  dann nicht zusätzlich genannt. Ohne diktierte Merkmale steht im Befundtext „[Adjektiv] degenerative Veränderungen …“.
- Feste Prüfung nach der KI: `kl_bereinigen` (py ≡ ts). Ein nicht gedeckter Grad wird entfernt bzw. auf den einzigen
  erlaubten Grad gesetzt.
- Nachvollziehbarkeit: Die EXE schickt bei EOL `nachvollzug` mit (STT-Rohtext, Modell, Prompt-/Vorlagen-Stand,
  IB Lab ja/nein). In der .rakscribe.json landet das erst mit der neuen Brücke (Folgejob).

## Tests
Zahlen und Fälle: `docs/benchmarks/konfabulation_2026-11-12.md`. RH 38 ohne IB Lab: 0 Erfindungen in 3 × 20 Läufen
(EXE mit CAS, EXE, Web). Mit KL 1: 20/20 nur Grad 1. Diktat-Grad: 20/20. Erhalt-Fälle: 3 × 20 ohne verschluckten
Inhalt. Die bestehende Regression hat keine neuen FAIL, alle Offline-Gates sind grün.

## Bewusste Verhaltensänderung
„mäßiggradige Omarthrose“ ohne diktierten Grad ergibt jetzt „Mäßiggradige Omarthrose rechts.“, **ohne** „(Arthrose
Grad 3 nach Kellgren & Lawrence)“. Georgs Referenzfall vom 05.10. hatte den Grad noch so verlangt. Peters Regel vom
12.11. („nie aus dem Wortlaut ableiten“) geht vor. Ein Grad steht also nur, wenn er diktiert ist oder aus IB Lab kommt.

## Offen
- Brücke + Paket + Einspielen + Echttest am Testeintrag: Folgejob `kaiscribe-nachvollzug-paket-n1` (Prio −10, rush,
  Ordi). Er trägt auch die Kurznotiz in den Skill ein; der Skill ist am Hetzner nur ein Lese-Spiegel.
- Kein Browser-Check der Web-App (Hetzner). Das Bundle ist per curl geprüft: Version 3.18.4, neue Prompt-Texte drin.
