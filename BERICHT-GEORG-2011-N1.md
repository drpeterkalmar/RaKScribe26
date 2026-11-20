# BERICHT kaiscribe-georg-2011-n1 – Georgs Diktiertag 20.11.2026 (gebündelter Bau EXE + Web)

Stand 20.11.2026 abends · Branch `job/kaiscribe-georg-2011-n1` (von `main` 41893b4) · **nicht auf main, kein Release.**
Merge, Versionsnummer und Release macht der Abnahme-Job `kaiscribe-georg-2011-abnahme` (ab 20:15).
**Vorschlag Version: 3.20.0** (VERSION steht unverändert auf 3.19.15).

Commits: 22e9442 (Grundregeln) · 82d6b83 (IB Lab) · 15c166f (Bedienung) · 847fdf9 (Mehrfach/Titel) · 4548851 (Becken+Hüfte,
Zehe) · 6bc6d09 (test_import) · dieser Bericht.

## Tests
- Alle 49 Offline-Gates aus `.github/workflows/test.yml` grün mit `/usr/bin/python3`, dazu `befund_regeln_test` (PY 303 + TS
  Fälle), Node `pipeline_test`/`speechmike_test`/`audio_test`/`llm_anbieter_test`, `tsc --noEmit`, `eslint` grün.
- Neu: `tests/offline/test_georg_2011.py` (EXE-Kette, 25 Prüfungen), `tests/offline/test_georg_2011_ui.py` (Bedienung, 18),
  Fixtures `georg_2011` (23 Fälle, je zweimal angewandt gleich) + `rho.ans_ende` + `rho.einfuegen` (Score 6/7) in
  `befund_regeln_fixtures.json`, 4 neue Fälle in `detect_fixtures.json`. Beide neuen Tests stehen in der CI.
- Regel-Register `tests/regel_register/regeln.json`: **27 neue Einträge** (alle mit Wortlaut, Quelle, Datum), Test grün.
  Keine bestehende Regel entfernt; geänderte Wortlaute nur ergänzt (Prompt-Beispiel Knie Z. 19, Pleuraerguss, K&L-Gelenkliste).
- Schon vorher rot, nicht durch diesen Job (am Basis-Stand 41893b4 gleich geprüft): `test_cas_auftrag` Teil 3 (importiert
  ris-mods `bruecke/roboter.py`, das unter Python 3.9 einen f-String-Syntaxfehler hat – Teil 1+2 grün), `test_maske_ablauf`
  (31 rot auch auf 41893b4, Umgebung). `test_audiodatei` „100-ms-Blöcke“ ist zeitabhängig (bei Last einmal rot, wiederholt grün).
- EXE = Web: `radiology_prompt.txt` und `templates.json` sind EINE Datei für beide (Web lädt sie per `?raw`/Import);
  `befund_regeln.py` ≡ `befundRegeln.ts` über dieselben Fixtures. Prompt-Marker neu: `2026-11-20-georg-diktiertag`.
- Kein Google-Geld, keine Live-KI-Aufrufe, kein Browser (LEICHT-SPUR).

## Punkte der Sammelliste

| Nr | Inhalt | Stand | Wo / Test |
|---|---|---|---|
| 3 | zurückgestellter Befund | ✅ KaiScribe-Teil: Feld `zurueckgestellt` im Auftrag → Band „zurückgestellt – EOL ersetzt den Befundteil“. Ablage macht die Brücke (Nachtrag ris-mods). | `cas_auftrag.Auftrag.zurueckgestellt`; test_georg_2011_ui „3: …“ |
| 5 | „Nur Text“ bei neuem CAS-Auftrag aus + Anzeige | ✅ Schalter zeigt „⚠ NUR TEXT AN – kein Befund“ (Bernstein); neuer Auftrag schaltet aus + Hinweis | `RaKScribe._cas_neu`, `_nur_text_anzeige`; test_georg_2011_ui „5: …“ |
| 7/14b/21a/32 (+RH 22, 80) | Befund beginnt nie mit „Im Übrigen/Ansonsten“ | ✅ an der Quelle (Prompt-Beispiel Z. 19 war die Quelle für Knie) + deterministisch nach allen Wächtern, alle Regionen: „Ansonsten …“ wandert hinter die erste Pathologie, „Im Übrigen …“ nur hinter pathologische Stellung, sonst entfällt das Wort (Verb-vorn-Sätze → Vorlagensatz) | `br.grundregeln`/`befund_anfang` ≡ TS; Fixtures georg_2011 (Knie, Schulter, LWS, Finger-Fraktur, Luxation, Normalbefund); test_georg_2011 „32: …“ |
| 8 | Fibroostose/Erguss wörtlich | ✅ Prompt „DIKTAT WÖRTLICH“ + chirp_3-PhraseSet „Fibroostose“, „Recessus suprapatellaris“. Ob RH 51 Chirp oder KI war, nicht per VM geprüft (kein VM-Lauf in der Leicht-Spur) | Register georg-diktat-woertlich, georg-stt-vokabular |
| 9 (+25, 26d) | Winkel-Erläuterung als „Anmerkung: …“ mit Leerzeile | ✅ LAMA/FROG/HIPPO-Schlussanmerkung am Ende des Ergebnisses als eigener Block (EXE-Kette, IB-Lab-Knopf, Gerüst, Maske) | `ibl_bausteine.anmerkung_absetzen`; test_georg_2011 „9: …“ |
| 10 | Pleuraerguss | ✅ Sinus-Satz der betroffenen Seite raus, „Ansonsten das Zwerchfell beidseits glatt begrenzt.“ hinter dem Erguss-Satz | grundregeln/_pleura; Fixtures (rechts, „Sinus links frei“ bleibt, ohne Erguss unverändert) |
| 12 | Mammo + Sono getrennt | ❌ offen – Mammographie läuft über die Mammo-Maske, die den ganzen Diktat-Text in ihre Felder nimmt; Trennung braucht einen Umbau in `maske.py`/`_maske_aktiv` (Maske nur für den Mammo-Teil). Nicht in diesem Lauf. | Folgeauftrag |
| 13 | [WIDERSPRUCH]-Nachprüfung | ✅ Schreibvarianten c/k/z, femoropatellar↔patellofemoral/tibiofemoral, schon dastehender Satz nie doppelt | `schreibvarianten`, `phrase_vorhanden` ≡ TS; Fixture „RH 78 …“ (der genaue RH-78-Text lag nicht vor – Fix ist allgemein) |
| 14a/18/37b/40a/40b | Widerspruchsregel | ✅ Humeruskopfhochstand, DD infiltrativ, Beckenschiefstand (beide Sätze, auch aus HIPPO-Text), SQUIRREL-Skoliose/Cobb (Achsen-Sätze raus, Kyphose BWS + Lordose LWS bleiben) | `GEORG_STREICHEN` ≡ TS; Fixtures je Fall |
| 16/17 | Jones/MT V → Vorfuß; 2. CAS-Leistung mit Normalsätzen; Titel robust | ✅ detect (EXE = Web) + Region Fuß; nicht diktierte CAS-Untersuchung bekommt eigenen Befund + Prüfzeile; Zeile vor „## Befund“ ohne „## “ wird vor EOL zur Überschrift | `detect`, `cv.nicht_diktiert_ergaenzen`, `_cas.titel_sichern`; test_georg_2011 „16: …“, test_georg_2011_ui „17: …“ |
| 19/40c/31 | Rho eigener Einzelbefund am Schluss | ✅ „## Opportunistisches Knochendichtescreening (KI)“ mit eigenem Text + Ergebnis, immer zuletzt (auch Mehrfach); Score 6 → kein Text, 7 → Text | `rho_einfuegen`, `rho_ans_ende` ≡ TS; test_georg_2011 „19/40c“, „31“ |
| 20/25 | Abstufung/Etage wörtlich | ✅ Prompt; deterministisch: „skoliotische Asymmetrie“ ohne diktierte Skoliose bleibt im Ergebnis so | Fixture „20 …“ |
| 21b + RH 69 | KI-Hinweise nie im Ergebnis | ✅ RBfracture nur noch als Hinweis (Abholer-Text in die Anzeige), „KI: …“-Punkte der KI werden gestrichen | `NUR_HINWEIS`, `_KI_PUNKT`; test_ibl_bausteine m), test_georg_2011 „21b“ |
| RH 69 bündeln | zusammengehörige Befunde = ein Punkt | ⚠ nur Prompt-Regel (Fraktur + Dislokation/Gelenkbeteiligung derselben Struktur = 1 Punkt), **ohne Log abgeleitet** (kein VM-Lauf) – Georg bestätigen | Register georg-zusammengehoerig |
| 22 | Zehennummer nie raten | ✅ CAS Zehe/Finger ohne diktierte Nummer → rote Prüfzeile; Prompt: nie raten | `_strahl_hinweise`; test_georg_2011 „22: …“ |
| 23 | Warnung „bereits diktiert“ | ✅ Lauf-Datei `<Nr>_<heute>-*.json` → Dialog „Bereits diktiert“, „Nein“ gibt den Auftrag zurück (abgelehnt, Grund) | `_cas.heute_diktiert`; test_georg_2011_ui „23: …“. Der Teil „Status sofort nach EOL“ (Plaza/Roboter) ist nicht KaiScribe. |
| 26/37a/36/40d | Titel je Mehrfach-Teil, reine KI-Teile, Becken+Hüfte | ✅ reiner KI-Teil (Ganzbein/LAMA) bekommt eigenen Befund mit Titel; RH 49: Becken + Hüfte = EIN Befund mit Kombi v3.18.7, Titel „Becken sowie Hüftgelenk in 2 Ebenen rechts“, Seite aus CAS | `nicht_diktiert_ergaenzen`, `_becken_huefte_kombi`, `KOMBI_TITEL`; test_georg_2011 „36/37a“, „26“ |
| 27 | Ergebnis nach F10 neu abgleichen | ❌ offen – braucht einen zweiten KI-Aufruf (Ergebnis aus geändertem Befundteil) bzw. eine Abgleich-Regel; nicht ohne Live-Test baubar | Folgeauftrag (mit 451898) |
| 28 | Seite im Befundsatz; Daumen vor CAS-„Finger“ | ✅ Prompt (Seite bleibt im Satz, genauere Bezeichnung vor CAS-Kürzel) + deterministisch Daumen in Überschrift/Ergebnis | Fixture „RH 79 …“ |
| 29 | Daumen-Normalsatz | ✅ „Normale Form der Phalangen, achsengerechte Stellung.“ (deterministisch + Prompt) | Fixture „RH 79 …“ |
| 30/42 | K&L an allen peripheren Gelenken, Wirbelsäule nie | ✅ Prompt (Gelenkliste inkl. Daumensattelgelenk, Beispiel Rhizarthrose → Ergebnis „Geringe Rhizarthrose beidseits.“); deterministisch: an der Wirbelsäule fällt „(Arthrose Grad X nach K&L)“ weg | Fixture „RH 81 …“ |
| 33 | Knie beidseits rechts zuerst | ✅ Prompt-Regel (keine deterministische Umsortierung) | Register georg-knie-rechts-zuerst |
| 34 | FROG im Fuß-Ergebnis bei Mehrfach | ✅ war schon richtig, jetzt mit Test Hand + Fuß belegt | test_georg_2011 „34: …“ |
| 35 | LAMA „Varisierung“ | ✅ bei regelrechter LAMA-Achse fällt der KI-Zusatz „mit Varisierung“ o. ä. weg (Werte bleiben); Grenzen prüft der Abholer | `lama_achsworte`; test_georg_2011 „35“ |
| 36 (lama.toml) | Mikulicz-Linie/Traglinie | – ris-mods (Nachtrag: dort umgesetzt); KaiScribe erkennt den Anfang „HKA = …“ unverändert | |
| 37c | erste Zeile = Stellung (LCE) | ⚠ Prompt-Regel; HIPPO-Sätze setzt der Abholer-Text – keine eigene Umsortierung in KaiScribe | |
| 38 | „SI-Gelenksarthrose“ | ✅ Prompt + deterministisch (ISG-/Iliosakralgelenksarthrose → SI-Gelenksarthrose) | Fixture „38 …“ |
| 39 | Aufnahme starten löscht nie ohne Rückfrage | ✅ Rückfrage bei nicht übergebenem Text, Knopf „↶ Rückgängig“ (auch nach F9), Lauf-Datei jetzt auch im Nur-Text-Weg (RH 7: genau dort fehlte sie) | test_georg_2011_ui „39: …“ |
| 41a | FROG ohne Diagnose (Nachtrag) | ✅ `ohne_diagnose` + `messwerte` (Abholer 1.3.14): Sätze ans Ende der Fuß-Beschreibung, Vorlagensätze bleiben, kein Ergebnispunkt, Schluss als Anmerkung; Vorfuß nur d.p.; a) „Uneinheitliche Winkel …“ statt Gewölbesatz geht | test_georg_2011 „41a …“ |
| 41b | akzessorische Knochen | ✅ Prompt (nie Ausriss/Fraktur) + chirp_3 (+6 Os …) + Region Fuß (Os naviculare cornutum nicht mehr „Hand“) | test_georg_2011 „41b“, test_stt |

Nicht gebaut laut Auftrag: 1, 2, 4/43, 6, 11, 15-nach-EOL, 24, 44, 45.

## Für den Abnahme-Job / ris-mods (bitte beim Merge beachten)
1. **„Anmerkung: “-Präfix (Punkt 9):** KaiScribe schreibt die Schlussanmerkung jetzt als `Anmerkung: HKA = …` bzw.
   `Anmerkung: Weitere Winkelmessungen …`. ris-mods `bruecke/ibl_einfuegen.ist_schluss` erkennt nur Zeilen, die mit
   `HKA = `/`Weitere Winkelmessungen`/`LCE = …` **beginnen** – falls der Formatierer KaiScribe-Text nachbearbeitet, muss
   er das Präfix `Anmerkung:` tolerieren (sonst Gefahr doppelter Anmerkung). Bitte im Abnahme-Lauf an 451898 prüfen.
2. **Rho-Einzelbefund:** neuer letzter Block `## Opportunistisches Knochendichtescreening (KI)` – der Formatierer muss einen
   Block ohne eigene CAS-Leistung annehmen (Titel kommt nicht aus CAS). Rho von IB Lab setzt weiter nur der Formatierer.
3. **zurückgestellt:** KaiScribe liest das Feld `zurueckgestellt` (bool) aus `cas_auftrag.json` nur für die Anzeige; schickt
   die Brücke es nicht, passiert nichts.
4. FROG `ohne_diagnose` greift erst mit Abholer 1.3.14 + Brücke 2.5.25 (dort noch ohne Versionsnummer).

## Offen / Folgeaufträge
- 12 Mammo + Oberbauch-Sono trennen (Umbau Maske) · 27 Ergebnis-Abgleich nach F10 (zweiter KI-Aufruf, Live-Test 451898).
- Georg bestätigen: RH-69-Bündelregel (ohne Log abgeleitet), Rhizarthrose-Ergebnis ohne K&L-Klammer (so von Georg vorgegeben,
  weicht von der allgemeinen K&L-Ergebnisform ab), Normalbefund für nicht diktierte CAS-Untersuchung (ersetzt den bisherigen
  Hinweis „laut CAS, nicht diktiert“; Funktions-Kombis bleiben wie bisher).
- Satztrenner: „Dig. V.“ am Satzende wird nicht als Satzende erkannt („V“ ist Abkürzung „V.“) – betrifft nur das Verschieben
  von „Ansonsten …“ hinter so einen Satz; unverändert gelassen.
- Ein Live-Durchlauf mit Claude maskiert (Georgs RH-Fälle anonymisiert) wurde nicht gemacht (Leicht-Spur) – gehört in die Abnahme.
