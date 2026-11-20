# kaiscribe-befundfeld-sicher-n1-einspielen – KaiScribe 3.19.16 einspielen NUR nach Pflicht-Abnahme am Testpatienten 451898

Eingereiht von `kaiscribe-befundfeld-sicher-n1` (Teil 1, Fr 20.11.2026 ~17:30, Hetzner). Repo RaKScribe26, Ordi-Werkzeuge in ris-mods.
Ressource: ordi, automaten-vm. Peter 20.11.: „Wenn schon was rechts steht und ich dazudiktieren möchte, wird manchmal alles
gelöscht oder der Titel ändert sich … Dann mache ich panikartig zu und verwende SpeechMagic.“

**Zeitfenster:** EXE-Tausch nur nach Ordi-Schluss (Mo–Do ab 17:30, Fr ab 13:30, Wochenende). Die Sperre im Tauschskript gilt
zusätzlich (Mo–Fr 06:30–20:10 gesperrt). Klicks am Büro-PC nie während der Ordi. Startet der Job an einem Werktag nach 05:30: nichts
halb einspielen. Dann denselben Brief als `…-f1` mit not-before 20:15 desselben Tages einreihen.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.
> **VERBOTEN:** C-MOVE/C-STORE von Patientenbildern, CAS-Datenbank (auch kein SELECT von hier aus), DICOM-Header.

ZUERST LESEN: `BERICHT-BEFUNDFELD-SICHER-N1.md` (Ursache, Verhalten, Tests, Kurztext für Peter). Ablauf-Vorlage für Tausch und Abnahme:
`FOLGEJOB-KAISCRIBE-FROG-EINSETZEN-N1-EINSPIELEN.md`, `BERICHT-KAISCRIBE-RELEASE-1118-EINSPIELEN.md`.

**Mit SQUIRREL abstimmen:** `kaiscribe-squirrel-ergebnistext-n1-einspielen` (ris-mods + KaiScribe) wartet auf seinen KaiScribe-Bau
(war am 20.11. 17:00 wegen eines Login-Problems am Mac pausiert). Laufen beide am selben Abend, wird nur die neueste KaiScribe-Version
getauscht. Ein squirrel-Release ≥ 3.19.17 enthält 3.19.16, dann gibt es eine Abnahme-Runde mit beiden Prüfungen. Nie auf eine ältere
Version zurück.

## Was eingespielt wird
- **KaiScribe 3.19.16** (RaKScribe26 `e004365`, Änderung `1366f72`), Release-Tag `3.19.16`, Asset `rakscribe26.exe`, 56 584 815 Byte,
  **sha256 `1f7dc090bbfdb6ea706360bd355686db39ce1c953b8af24227527618505ba8a0`**. Enthält 3.19.15.
  - Tests 44768754202 grün, Build 44768796212 grün, Windows-UI-Test 44769262757 (Stand im Bericht von Teil 1).
  - Tor: alle drei grün (API `actions/runs/<id>`). Die Web-App 3.19.16 ist seit 20.11. ~17:04 auf Pages.
- ris-mods (Brücke, Formatierer, Abholer): **keine Änderung**. `radiology_prompt.txt` ist unverändert. Im Widerspruchs-Katalog
  (`vorlagen_vorrang.json`, eingebaut) ist „unauffällige … Spongiosa“ dazugekommen.

## Schritt 0 – Tore (nur lesen)
1. Release, Digest und die drei Läufe grün.
2. Live-Stand: SHA/Version von `X:\RaKScribe\rakscribe26.exe` (erwartet 3.19.15).
3. Niemand arbeitet am Büro-PC.
4. **Lücke aus Teil 1 schließen:** In `X:\RaKScribe\rakscribe.log` (+ `.1`…`.5`) Peters Fälle der letzten Tage suchen. Das Muster ist
   Befund steht, dann `[RECORD] Aufnahme wird gestartet` OHNE `[EINFÜGEN] … an Stelle`, danach ein neuer Befund, oft zweimal `INS`
   hintereinander. Nur Zeit, PC und Zeilenart notieren, kein Inhalt. Damit ist die Ursache am echten Protokoll bestätigt (oder nicht).

## Schritt 1 – PFLICHT-Abnahme am Testpatienten 451898 (VOR dem Tausch auf X:, nie vidieren)
Ohne diesen Beleg wird **nicht** eingespielt, 3.19.15 bleibt. Grund in den Bericht, Folgejob `…-f1` ab 20:15 am nächsten Werktag.
1. 3.19.16 nur für den Testlauf starten: die geprüfte EXE aus `%LOCALAPPDATA%\hermes\work\ks_tausch\v3.19.16\` direkt. X: noch nicht anfassen.
2. Testeintrag 451898 mit **einer Knie-Leistung** über die Teststrecke (ris-mods `ordi-hermes/teststrecke/ks.py` bzw.
   `buero/kaiscribe.py diktat`). Dazu einen **IB-Lab-Baustein (KOALA)** für die AccNo in die Ablage
   (`python3 tools/ibl_abnahme_bausteine.py X:\IBL-Vorbefunde …`, Vorgehen wie bei FROG/HIPPO am 19.11.). Band zeigt
   „IB Lab: KOALA … ✓“, rechts steht das **IB-Lab-Gerüst** (Titel notieren).
3. Ablauf mit Audio (Teststrecke/WAV-Modus bzw. „Audio laden“, kein Mikrofon nötig), Statuszeile und rechtes Feld nach jedem Schritt
   per Screenshot belegen:
   a. Record (Statuszeile **„Neuer Befund (IB-Lab-Gerüst) · Aufnahme läuft“**, das Gerüst bleibt sichtbar), Diktat „Knie links
      kleiner Gelenkerguss“, INS → Befund mit dem **KOALA-Text wörtlich**, Titel wie im Gerüst.
   b. **Ohne ins Befundfeld zu klicken** (Fokus in CAS/Plaza lassen): Record → Statuszeile **„Ergänzung · Aufnahme läuft“**, Diktat
      „Enostose im distalen Femur von 6 mm“, INS → der Satz steht am Ende des Befundteils vor „Ergebnis“. **Titel und übriger Text
      sind Zeichen für Zeichen gleich** (vorher/nachher vergleichen).
   c. **Restructure** klicken → Enostose im Befund und im Ergebnis, „Mineralgehalt und Knochenstruktur sind regelrecht.“ nicht mehr so
      da (weg oder „im Übrigen …“), KOALA-Text weiter da, Titel gleich, keine rote Prüfzeile. Strg+Z im Befundfeld → Stand von b,
      nochmal Strg+Z → Stand von c.
   d. Kurz **Reset** (→ Befund von a) und **Strg+Z** (→ c), dann **EOL**.
   Protokoll-Beleg (ohne Inhalt): `[BEFUNDFELD] Record: Neuer Befund (IB-Lab-Gerüst)`, `[BEFUNDFELD] Record: Ergänzung`,
   `[BEFUNDFELD] Ergänzung: … eingebaut`, `[BEFUNDFELD] Restructure fertig: 0 Prüfzeile(n)`.
4. **Brief belegen** (nur lesen): Brief bzw. `X:\RaKScribe\Daten\laeufe\<Nr>_*.json` enthält KOALA-Text + Enostose + Erguss im Ergebnis.
   Screenshot + Textauszug in den Bericht (ohne Patientendaten).
5. Kurzprobe **Clear all** (Feld leer, Band/Diktatnummer bleiben), dann Testeintrag stornieren wie in der Teststrecke üblich und die
   Testbausteine aus `X:\IBL-Vorbefunde` entfernen.

## Schritt 2 – Tausch (nur wenn Schritt 1 belegt)
- ris-mods `ordi-hermes/kaiscribe_x_tauschen.ps1`: EXE direkt von github.com nach `%LOCALAPPDATA%\hermes\work\ks_tausch\v3.19.16\rakscribe26.exe`,
  SHA prüfen, dann `-Schritt exe -Tag 3.19.16 -Sha 1f7dc090…ba8a0`. **NICHT** `-Schritt holen`.
- Beleg: `KS_TAUSCH=ok neu=1f7dc090bbfd alt=…`, Sicherung `rakscribe26.exe.vor3.19.16-….alt`, Titel „KaiScribe 3.19.16 – Röntgen am Kai“.
- Rückweg: `-Schritt zurueck`. Bei Rot bleibt die alte Version bzw. es geht zurück, Grund in den Bericht, nie „live“ melden.

## Schritt 3 – erster echter Fall
Einen Kontroll-Auftrag `kaiscribe-befundfeld-sicher-n1-kontrolle` mit not-before am **nächsten Ordi-Morgen, 12:30** (Mo 23.11.) und
Ressource keine einreihen (nur lesen über die Automaten-VM bzw. das Log). Er prüft:
- `[BEFUNDFELD]`-Zeilen der ersten echten Fälle (Ergänzung statt Neubefund, Restructure benutzt?);
- keine `Restructure verworfen`/Fehler;
- kein Ergänzungs-Satz in einem Befund eines anderen Patienten (Zeitfolge `[BEFUNDFELD] Record` → EOL je Diktatnummer).

## Schritt 4 – Bericht + Meldung
`docs/einspielen/ergebnis_befundfeld_sicher_n1_<datum>.md` (Tore, Log-Befund aus Schritt 0.4, Abnahme mit Screenshots/Brief-Auszug,
Tausch, Rückweg), keine Patientendaten. Meldung nach außen nur über den Queue-Abschluss und nur, wenn live belegt, mit dem
„Kurztext für Peter“ aus `BERICHT-BEFUNDFELD-SICHER-N1.md` und „aktiv seit <Datum Uhrzeit>“ (an Peter, Thread KaiScribe wie bei den
letzten Releases).
