# stt-mistral-vergleich-n1 – Mistral Voxtral gegen Google chirp_3 (Di 24.11.2026) – Kanban #561

## Kurzbericht an Peter (≤10 Zeilen)
1. Für Mistral gibt es noch keinen Schlüssel (nicht im Tresor). Ich habe deshalb nichts registriert, nichts bezahlt und
   Mistral noch nicht gemessen.
2. Fertig ist das Messwerkzeug. Es vergleicht deine 6 Sprachnachricht-Diktate und 9 nachgesprochene Musterbefunde, jeweils
   ohne Liste, mit der Chirp-Liste und mit der Fachwortliste. Gemessen werden Fehlerrate, Fachwörter, Seite, Zahlen und
   Verneinungen. Der Testdeckel liegt bei 5 €, real kostet die Messung etwa 0,14 €.
3. Google-Vergleich aus den Altwerten (0 $): chirp_3 hat 5,5 % Wortfehler und 0 Seitenfehler. Bei 6 von 18 Zahlen und
   Höhen stimmt die Schreibweise nicht („DH4“ statt Th4, „Scaphoid Taille“). Das bügelt bisher Call 0 aus.
4. Kosten pro Monat bei deinen Minuten (444 min Endtext, 544 min Live): Mistral kostet etwa 1,80 $ für den Endtext und
   4,40 $ für Live, zusammen rund 6 $. Google kostet etwa 10 € für den Endtext und etwa 18 € mit Live, davon gehen rund 9 €
   Gutschrift ab.
5. **Empfehlung: noch nicht wechseln, erst messen.** Billiger und EU ist Mistral. Ob es Fachwörter und Seiten so
   zuverlässig erkennt wie chirp_3, ist offen. Voraussichtlich gilt dann: „erst mit Fachwortliste“.
6. 👉 Mistral-Konto anlegen: bezahlter Tarif, Training aus, AVV akzeptieren, Schlüssel in den Tresor (Schritte auf Karte
   #561), bis 05.12. Danach misst der Folgeauftrag zuerst ohne Patientendaten und erst nach der AVV echte Diktate.

## Details
- **Zugang:** `vw_get.py list mistral` → kein Eintrag. In `~/.hermes/.env` steht nur ein Kommentar und kein Schlüssel.
  Kanban #561 (Grund geld, Frist 05.12.) enthält die Schritte: Konto, bezahlter Tarif mit Limit 10 €/Monat, Training aus,
  DPA/AVV, Region EU und Schlüssel als Vaultwarden „Mistral API KaiScribe“.
- **Werkzeug:** `tools/stt_mistral/voxtral_ab.py` (Gate `tests/offline/test_voxtral_ab.py`, 16 Prüfungen grün).
  - Batch über `/v1/audio/transcriptions`, Modell `voxtral-mini-latest` (umstellbar).
  - Listen-Varianten über `context_bias`: ohne / chirp85 / chirp+sm, gekappt auf 100.
  - Kostenbuch mit Deckel 5 €.
  - `--echt` ist nur mit `MISTRAL_AVV_BESTAETIGT` erlaubt.
  - Ruft Google nicht auf.
  - Referenzen, Termini und Seiten kommen aus `stt_ab_g35t.py`. Die Synthetik besteht aus 4 Texten aus `chirp_adapt_ab2.py`
    und 5 neuen Texten mit Seiten, Maßen und Verneinungen. Alle Synthetik-Texte sind frei formuliert, ohne Patientenbezug,
    gesprochen von macOS Anna.
  - Trockenlauf (Erkenner = Referenz) ergibt überall 0 % und volle Treffer, die Auswertung arbeitet also richtig.
- **chirp_3-Basis:** `docs/benchmarks/stt_mistral/chirp3_basis_20261004.json`. Das ist der chirp_3-Teil von
  `stt_ab_g35t_results.json` vom 04.10.: 6 Oggs × 3 Läufe, damals mit der 85er-Liste. Die Werte sind deterministisch, alle
  3 Läufe sind wortgleich.

  | | WER Ø | Termini | Zahlen | Verneinung | Seite falsch | s je Audio-min |
  |---|---|---|---|---|---|---|
  | chirp_3 +85 | 5,5 % | 126/135 | 12/18 | 3/3 | 0/18 | 5,6 |

  Für die Synthetik gibt es keine chirp-Altwerte. Dort wird Voxtral absolut bewertet, für den Vergleich zählen die Oggs und
  der VM-Teil B.
- **Kosten:** Monat = Woche × 4,35.
  - Mistral (Listenpreise laut Skill, Nov. 2026): Batch 0,004 $/min, Realtime 0,008 $/min.
  - Google: chirp_3 ca. 0,022 €/min (chirp-fachwortliste-n2). Live macht etwa 45 % der Sprachkosten aus (testkosten.md).
    Die Euro-Beträge aus der Konsole sind nicht nachgelesen, die Google-Zahl ist daher eine Schätzung nach Listenpreis.
  - Websuche war in diesem Lauf nicht freigegeben. Die Mistral-Preise und die Regeln zu DPA und Training sollte Peter beim
    Anlegen des Kontos auf der Mistral-Seite gegenprüfen.
- **Offen:**
  - Realtime-Modell (Live-Anzeige) ist nicht gebaut, kommt nur bei gutem Batch-Ergebnis (Folgeauftrag).
  - Das genaue Format von `context_bias` (Höchstzahl, Mehrwortphrasen) muss mit dem echten Schlüssel geprüft werden.
    Lehnt die API ab, lässt das Skript die Variante mit Meldung aus.
- **Folgeauftrag:** `FOLGEJOB-STT-MISTRAL-VERGLEICH-N2.md` (A: ohne Patientenbezug, B: 67 VM-Fälle gegen die vorhandenen
  chirp-Texte, C: Entscheidungsregel).
- Kein Umbau von KaiScribe.
