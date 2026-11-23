# kaiscribe-schulter-ergebnis-n1-einspielen – KaiScribe 3.23.0 (Georg Punkte 48–70) einspielen + PFLICHT-Abnahme 451898

Von `kaiscribe-schulter-ergebnis-n1` (Mo 23.11.2026 nachts, Bau am Mac, Bericht `BERICHT-KAISCRIBE-SCHULTER-ERGEBNIS-N1.md`).
Release-Regel (Georg; Nachtrag Peter 23.11. 20:2x zu Punkt 61): **Release auf X: erst nach echtem Lauf an 451898**, sonst
Rollback. 451898 NIE vidieren, alles stornieren. CAS nur lesen. VERBOTEN: C-MOVE/C-GET/C-STORE, Header, dcm4chee, CAS-DB
schreiben. Ordi-Zeit (Mo–Do vor 17:30, Fr vor 13:30): erst danach; Tausch-Sperre Mo–Fr 06:30–20:10. Ordi/Büro-PC exklusiv
(nie zwei Peer-Läufe). Keine Patiententexte in Commits/Berichten.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.

## Was eingespielt wird
main **9876a85 = 3.23.0** (Web live seit 23.11. ~23:20, Bundle mit Prompt-Marker `2026-11-23-georg-schulter-ergebnis` belegt).
EXE bisher nur als **Vorabversion `test-45277048366`** (Build aus main, VERSION 3.23.0; Asset `KaiScribe.exe`, sha256
`9b41b3097f4f336eb2c7232a14eb1172ef93bbc4bf31c0ec195c57afa0aab53a`) – bewusst NICHT „Latest“ (Release erst nach 451898).
Nach grüner Abnahme: `gh workflow run build-exe.yml --ref main -f release=true` → Release 3.23.0 Latest, dann X:-Tausch mit
dessen sha256. Inhalt siehe Bericht Punkte 1–8.
KOALA-Knie-Automatik ist AUS (`ibl_bausteine.KOALA_KNIE_AUTOMATIK = False`, Kanban #514 erledigt).

## Ablauf
1. Testkopie am Büro-PC wie bei FROG 3.19.15 (eigener Ordner, nie die EXE im selben Ordner austauschen – ESET, Kanban #461);
   Werkzeuge: Peer `hermes peer run ordi`, Ton `ton.sh sprechen <ID> <datei> o`, Arbeitsdateien wie
   `~/cj/work/kaiscribe-georg-2011-abnahme` (lauf.py, warte.sh), CAS-Kürzel `ris-mods katalog/kuerzel_vorlage.tsv`.
2. Abnahme-Matrix an 451898 (je Lauf Brieftext belegen, Fettdruck im Word-Brief prüfen – `tools/vm/rho_titel_kontrolle.py`-Weg
   liest Format aus dem RTF):

| Fall | Diktat (gesprochen) | erwartet |
|---|---|---|
| A Schulter re | „Schulter rechts in zwei Ebenen. Omarthrose Kellgren Lawrence 2. Enthesiopathiezeichen Tuberculum majus. AC-Gelenksarthrose.“ | Befund: Gelenksätze → AC → „Ansonsten die Gelenkflächen regelrecht konturiert.“ → „Kortikale Unregelmäßigkeiten und vermehrte Sklerosierung am Tuberculum majus.“; Ergebnis 1. Omarthrose (Grad 2) 2. AC 3. Enthesiopathie |
| B Schulter re, 2. Lauf | „… Kalkdepot mit Enkapsulation … Ergebnis Doppelpunkt …“ | „Enkapsulation“ (nie „Einkapselung“), „Ergebnis:“ als Abschnitt, im Brief fett |
| C Sono Schulter | „Geringgradige Bursitiszeichen perifokal im Bereich der Supraspinatussehne“ | Bursa-Normalsatz weg, Satz an seiner Stelle, kein Widerspruch |
| D Fuß + Malleolus | Fuß mit „knöcherner Bandausriss am Malleolus lateralis, 9 mm Fragment“ | Fraktur vor Gelenk-/Weichteilsätzen, danach „Im Übrigen glatte …“; kein eigener Absatz am Ende, keine rote „KEIN eigener Befund“-Warnung |
| E Nur Text AN | Sono Weichteile mit Titel + „Ergebnis Doppelpunkt“ | Überschriften fett in KaiScribe UND im Word-Brief (sonst ris-mods-Folgejob Formatierer) |
| F Becken + Hüfte | Variante 1 „Beckenübersicht und Hüfte rechts …“ / Variante 2 getrennt | V1 ein Kombibefund, V2 zwei Teile |
| G Knie mit KOALA-Baustein | „Knie links unauffällig“ | kein KOALA-Text/Grad |

3. Alles grün → EXE auf X: (`kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.23.0 -Sha <sha>`, `.alt` bleibt), Kontrolle am
   nächsten Ordi-Tag mit `tools/vm/georg_kontrolle_pruefen.py` + `tools/vm/rh_ursache_bauen.py`. Rot → nicht einspielen,
   Fehler beheben (eigener Commit, Version beim Zusammenführen).
4. Bericht ≤ 8 Zeilen als Nachtrag in `BERICHT-KAISCRIBE-SCHULTER-ERGEBNIS-N1.md`.

## Lücken aus dem Bau
- Fettdruck im Word-Brief bei „Nur Text“ setzt der Formatierer (ris-mods `bruecke/ki_format`), nicht KaiScribe – nur Beleg.
- Dunn-Aufnahme / Hüft-OP-Seite aus dem Bildkopf nicht angebunden (nur Diktat bzw. Prüfzeile).
- Gerüst-Erhalt (Punkte 63/67) nur offline getestet (Gerüst wird nicht in der Lauf-Datei protokolliert).
