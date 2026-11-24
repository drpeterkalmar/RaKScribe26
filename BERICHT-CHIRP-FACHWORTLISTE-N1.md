# chirp-fachwortliste-n1 – SpeechMagic-Fachwortliste für Chirp (Di 24.11.2026)

Auftrag Peter 24.11.: „1 ok, 2 ich vertraue dir, 3+4 ok, wenn gut bitte auch rg“. Grundlage: BERICHT_speechmagic-daten-inventur-n1
(ris-mods, Kanban #526).

**Kanban #557.** **Kurz:** Die Liste ist gebaut (316 Einträge), maschinell auf Namen gefiltert und als Schalter je Kürzel eingebaut. Der
Schalter steht für alle auf **aus**. Gemessen habe ich im Testprojekt, Kosten unter dem Deckel von 5 €. Bei rg werden die Fehler
weniger, aber noch nicht sicher belegt. Bei kp gibt es nur 6 Fälle mit Audio, und die werden mit Liste eher schlechter. Nach der
Regel im Auftrag („wenn nicht besser: Schalter aus lassen“) ist deshalb nichts eingeschaltet: kein kp-Release, kein rg, keine
Mail an Georg. Ein Folgeauftrag misst ab 09.12. mit neuen Fällen nach.

## 1. Liste (Schritt 1 + 6)
- Alles Auswählen und Filtern lief auf der VM als rakauto (`tools/vm/chirp_fachwort/cfw_liste.py`). Aus der VM kamen nur Zähler
  und die fertig gefilterte Liste.
- Kandidaten: 2.013 Wörter. Jedes davon wurde in mindestens 5 verschiedenen Briefen diktiert (im SpeechMagic-Rohtext) und steht
  auch in der Endfassung. Grundlage sind 2.367 Briefpaare.
- Namensfilter, „im Zweifel streichen“:
  - (a) Alle Namen, Orte und Straßen aus CAS. Gelesen nur per SELECT, READ ONLY, alle 17 Felder ohne Fehler: PRIVADRESS
    Name/Vorname/Geburtsname/Zweitname/Ort/Straße, WARTEROW Patient und Zuweiser, ALLARZTE Name/Vorname/Ort/Straße, USERS. Dazu
    alle Briefkopf-Felder und unbekannten großgeschriebenen Wörter im Kopf der 2.367 Briefe, außerdem jedes Wort nach Dr./Prof./
    Prim./OA/Frau/Herr/Pat./Kollege/Klinik … → 103 Wörter gestrichen.
  - (b) Großgeschriebene oder unbekannte Wörter, die weder im Wörterbuch noch in einer Phrasenliste stehen, sich nicht in
    Wörterbuch-Teile zerlegen lassen und keine lat./med. Endung haben → 371 gestrichen. Als Wörterbuch dienten die öffentliche
    Häufigkeitsliste de_50k und die Listen medical_web, medical_exe, chirp und misheard.
  - (c) Ortsendungen → 4 gestrichen.
  - Die CAS-Namen liegen nur auf der VM (`%LOCALAPPDATA%\chirp_fw\namen_cache.json`, rakauto).
- Auswahl: zuerst Wörter mit Beleg, dann seltene Fachwörter nach Häufigkeit. Als Beleg zählten:
  - Chirp hat das Wort nachweislich falsch gehört. Geprüft per Wortausrichtung KaiScribe-STT ↔ vidierte Endfassung (52 Fälle,
    lernen.db), nur ähnlich klingende Ersetzungen. Eingefügter Vorlagentext zählt nicht.
  - Vidier-Änderungen aus lernen.db.
  - Ziele der Fehlhör-Liste.
- Je Beugeform blieb höchstens ein Eintrag. 18 Mehrwortphrasen sind dabei, jede in mindestens 20 Briefen im selben Satzteil.
- Selbst gesichtet: keine Personen-, Orts- oder Praxisnamen gefunden. 109 Allgemeinwörter von Hand gestrichen, z. B.
  „Nachweis“, „zentral“, „weitgehend“ (`tools/chirp_sm/kuratieren.py`).
- Endfassung: Variante „smr“ mit 316 Einträgen. Sie enthält nur Wörter, die nicht in der Alltags-Häufigkeitsliste stehen. Bei
  der Messung war sie die beste Variante.
- **Ablage:** `phrases.json` → `chirp_sm`. Dieselbe Datei liest die EXE. Den Mistral-Vergleich (Voxtral context biasing) habe ich
  nicht gebaut; er kann später dieselbe Liste nehmen.
- **Google-Grenzen** (live geprüft am 24.11.):
  - chirp_3 nimmt bis 1.000 Phrasen. Google rät: „so wenige wie möglich, sonst leiden Nicht-Listenwörter“.
  - Boost höchstens 20. Je PhraseSet bis 1.200 Phrasen, je Phrase bis 100 Zeichen, je Anfrage bis 100.000 Zeichen und bis 20
    PhraseSets.
  - Mit Liste sind es 85 + 316 = 401 Phrasen, die längste hat 30 Zeichen.

## 2. Einbau (Schritt 2)
- `stt.py`:
  - `chirp_sm_phrases()` liefert die neue Liste (ohne die schon kuratierten Wörter). `chirp_phrase_sets(sm)` liefert die
    PhraseSets.
  - Mit `sm=True` kommt ein **zweites** PhraseSet dazu, mit eigenem Boost `CHIRP_SM_BOOST = 5`. Die 85 kuratierten bleiben
    unverändert bei Boost 10.
  - `chirp3_worker` fragt den Schalter `SM_AKTIV` ab. Ist er aus, fehlt oder wirft er einen Fehler, ist die Anfrage bit-gleich wie
    bisher.
- `config.py`: neuer Eintrag `CHIRP_SM = kp | kp, rg | aus`. **Standard: aus** (niemand).
- `RaKScribe.py`: `_chirp_sm_an()` schaltet die Liste nur ein, wenn das offene CAS-Diktat einem Kürzel aus CHIRP_SM gehört. Ohne
  CAS-Auftrag bleibt sie aus. Wenn an, steht im Log „[CHIRP3] Fachwortliste SpeechMagic an (kp, 316 Phrasen, Boost 5)“.
- Keine Regel entfernt. Die Web-App ist unverändert (nur die 85).
- Tests: `tests/offline/test_stt.py` hat 10 neue Prüfungen, alle grün:
  - Google-Grenzen und Namensschutz (keine Titel, Anreden oder Ziffern in der Liste)
  - ohne Schalter genau wie bisher; mit Schalter das zweite PhraseSet
  - alte Test-Attrappen bleiben gültig
  - die Werte für config.ini
  - EXE-Verdrahtung
- `test_bereitschaft` und `test_testkosten` waren nach meiner Änderung rot und sind jetzt grün:
  - test_bereitschaft: FakeApp → `getattr`.
  - test_testkosten: Das Mess-Skript enthielt die Produktions-Projekt-URL, jetzt steht dort ein Muster.
- Weiter rot, aber auf unverändertem origin/main genauso (Mac-Python 3.9): test_cas_auftrag (f-string), test_maske_ablauf
  (31 → 28), test_buero_anthropic (2), test_ibl_nur_auffaellig (1). Das ist nicht von diesem Job.

## 3. Messung (Schritt 3)
- Werkzeug: `tools/chirp_sm/messen_mac.py` → `tools/vm/chirp_fachwort/cfw_messen.py`, läuft auf der VM.
  - Benutzt wird die echte Produktionsfunktion `stt.chirp3_worker`. Nur das Projekt ist auf **rakscribe-test** umgebogen, mit
    einem 1-h-Token, der danach gelöscht wird.
  - Das Audio ging nur an Google EU. Zurück kamen nur Summen. Die Texte liegen auf der VM (`chirp_fw\mess_*.jsonl`).
- **Daten:** alle KaiScribe-PCM-WAVs von kp und rg seit 02.11. in M:\Diktate mit Referenz, ohne Testpatient-Fälle. Die
  Philips-WAVs habe ich nicht angefasst.
  - kp: 6 Fälle, 2,9 min. Die übrigen 146 kp-WAVs sind Testpatient-Läufe und haben keine Referenz.
  - rg: 61 Fälle, 32,5 min.
  - Referenz: die vidierte Endfassung (39 Fälle) bzw. der Befundteil der Brief-Datei (28 noch offene Fälle).
- **Rauschen:** Ein zweiter Lauf ohne Liste war in allen 61 vergleichbaren Fällen wortgleich. Chirp ist also deterministisch, und
  jede Änderung kommt von der Liste.
- **Maß:**
  - Die Endfassung enthält viel Vorlagentext. Die Wortfehlerquote gegen die Endfassung liegt deshalb bei allen Varianten gleich
    bei ca. 88 % und sagt nichts aus.
  - Belastbar ist **FH = Fehlhörer**: Wortausrichtung Chirp → Endfassung, gezählt werden nur kurze, ähnlich geschriebene
    Ersetzungen, also in der Endfassung korrigierte Hörfehler. Angegeben je Wortklasse: Fehlhörer / Endwörter.
  - Wortklassen: gesamt, Listenwort, selten (≥ 6 Buchstaben, nicht unter den 20.000 häufigsten deutschen Wörtern), Seite, Zahl.

| Kürzel / Variante | FH gesamt | FH Listenwort | FH selten (Fachwort) | Seite | Zahl | je Fall Fachwort besser / gleich / schlechter |
|---|---|---|---|---|---|---|
| **alle 67** ohne (85 × B10, = Produktion) | 85/1436 (5,9 %) | 17/245 (6,9 %) | 63/533 (11,8 %) | 4/82 | 4/155 | – |
| alle + Liste 334, Boost 5 | 79/1424 (5,5 %) | 15/237 (6,3 %) | 60/524 (11,5 %) | 3/83 | 4/156 | 10 / 46 / 11 |
| alle + Liste 334, Boost 10 | 82/1444 (5,7 %) | 13/244 (5,3 %) | 62/538 (11,5 %) | 4/84 | 3/155 | 11 / 44 / 12 |
| alle + **Liste 316 („smr“), Boost 5** | **77/1453 (5,3 %)** | **13/249 (5,2 %)** | **55/543 (10,1 %)** | 4/85 | 4/155 | 13 / 45 / 9 |
| **kp 6** ohne | 11/165 (6,7 %) | 3/40 | 8/59 (13,6 %) | 0/7 | 2/25 | – |
| kp + Liste 316 B5 | 15/166 (9,0 %) | 3/39 | 11/59 (18,6 %) | 0/7 | 2/25 | **1 / 1 / 4** |
| kp + Liste 334 B5 | 12/164 (7,3 %) | 3/39 | 10/57 (17,5 %) | 0/7 | 1/25 | 1 / 2 / 3 |
| **rg 61** ohne | 74/1271 (5,8 %) | 14/205 (6,8 %) | 55/474 (11,6 %) | 4/75 | 2/130 | – |
| rg + Liste 316 B5 | **62/1287 (4,8 %)** | **10/210 (4,8 %)** | **44/484 (9,1 %)** | 4/78 | 2/130 | **12 / 44 / 5** |
| rg + Liste 334 B5 | 67/1260 (5,3 %) | 12/198 | 50/467 (10,7 %) | 3/76 | 3/131 | 9 / 44 / 8 |

- Nach der Fehlhör-Liste (`misheard`, wie in der EXE) bleibt das Bild gleich: alle ohne 84 → mit Liste 77 Fehlhörer.
- Mit Liste landen etwas mehr Listenwörter im Text, die in der Endfassung fehlen: 46 → 53–59.
- **Bewertung:**
  - rg: Fachwort-Fehlhörer −20 % (55 → 44), je Fall 12 besser zu 5 schlechter. Ein Vorzeichentest ergibt p ≈ 0,14, das ist noch
    nicht sicher.
  - Vorsicht: Ein Teil der Belege für die Auswahl stammt aus denselben KaiScribe-Fällen (lernen.db). Das Ergebnis ist also eher zu
    gut.
  - kp: 6 Fälle, Fachwort 8 → 11, in 4 von 6 Fällen schlechter. Damit ist kp **nicht besser**. Für einen Beleg sind es zu wenige
    Fälle: kp diktiert fast alles über SpeechMagic, und dessen Audio ist ohne Philips-Codec nicht lesbar.
- **Kosten:**
  - 191,7 min gesendet, inkl. Wiederholungen nach 429-Fehlern (Ratenbegrenzung).
  - 3,07 $ zum Listenpreis (≈ 2,64 €), gebucht im Testkosten-Buch (Job chirp-fachwortliste-n1). Mit Peters 0,022 €/min
    höchstens 4,22 €. Unter dem Deckel von 5 €.
  - Die allgemeine Google-Testsperre (14.11.) ist unverändert. `messen_mac.py` prüft nur den Job-Deckel dieser einen freigegebenen
    Messung.

## 4.–5. Release / rg
- Nicht gemacht, weil die Messung bei kp nicht besser ist (Regel aus dem Auftrag). CHIRP_SM ist aus, also gibt es kein Einspielen,
  keinen Testpatient-Lauf und kein rg.
- Der Code ist auf main und kommt mit dem nächsten KaiScribe-Release mit, ohne dass sich etwas ändert.
- Die Info-Mail an Georg habe ich nicht vorbereitet, weil rg nicht eingeschaltet ist.
- **Folgeauftrag `chirp-fachwortliste-n2` (ab Mi 09.12., VM):** eine neue, unabhängige Messung an den KaiScribe-Fällen vom 25.11.
  bis 08.12. Diese Fälle wurden nicht für die Auswahl benutzt.
  - Varianten: ohne und Liste 316 mit Boost 5. Kosten ≤ 2 €.
  - Regel wie hier: Ist kp besser (≥ 10 Fälle, Fachwort messbar besser, gesamt nicht schlechter), folgt ein kp-Release nach den
    Release-Regeln aus Schritt 4. Bei rg mit klarer Verbesserung: Bericht mit Vorschlag.
- M:\Diktate hält nur ca. 4 Wochen. Die heutigen Fälle sind am 09.12. teils weg. Ihre Ergebnisse liegen als Text auf der VM.

## Dateien
- `phrases.json` (chirp_sm, _doc), `source_code/stt.py`, `config.py`, `RaKScribe.py`, `tests/offline/test_stt.py`, `tools/testkosten.py`
  (chirp3_test: sm durchreichen)
- `tools/vm/chirp_fachwort/` (cfw_erkunden*, cfw_vorprobe, cfw_liste, cfw_messen), `tools/mac/chirp_vm.py` (Skript als rakauto auf
  der VM), `tools/chirp_sm/` (kuratieren, messen_mac)
- Nur auf der VM: `%LOCALAPPDATA%\chirp_fw\` (chirp_sm_liste.json mit Kennzahlen, namen_cache.json, mess_*.jsonl)

👉 nichts für Peter.
