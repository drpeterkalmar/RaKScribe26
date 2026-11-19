# kaiscribe-frog-einsetzen-n1-einspielen – KaiScribe 3.19.15 einspielen NUR nach Pflicht-Abnahme FROG + HIPPO am Testpatienten 451898

Eingereiht von `kaiscribe-frog-einsetzen-n1` (Teil 1, Do 19.11.2026 ~19:30, Mac). Repo RaKScribe26, Ordi-Werkzeuge in ris-mods.
Ressource: ordi. Läuft NACH `kaiscribe-mehrfach-seitenlos-n1-einspielen` (3.19.14, Nachtrag: nimmt NICHT 3.19.15).
Georg 19.11. (RH 127 „keine Werte“): „Teste das immer ob es funktioniert.“ **Live bis Fr 20.11. 06:30.**

**Zeitfenster:** EXE-Tausch nur Mo–Fr 20:10–06:30 (Sperre im Skript). Klicks am Büro-PC Mo–Fr 06:30–17:20 nie. Startet dieser Job an
einem Werktag nach 05:30: nichts halb einspielen, denselben Brief als `kaiscribe-frog-einsetzen-n1-einspielen-f1` mit not-before 20:15
desselben Tages einreihen.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.
> **VERBOTEN:** C-MOVE/C-STORE von Patientenbildern, CAS-Datenbank (auch kein SELECT von hier aus), DICOM-Header.

ZUERST LESEN: `BERICHT-FROG-EINSETZEN-N1.md` (Ursache, Fix, Tests, Prüftext). Ablauf-Vorlage für Tausch/Abnahme:
`FOLGEJOB-KAISCRIBE-MEHRFACH-SEITENLOS-N1-EINSPIELEN.md` und `BERICHT-KAISCRIBE-RELEASE-1118-EINSPIELEN.md`.

## Was eingespielt wird
- **KaiScribe 3.19.15** (RaKScribe26 `fa2dcc4`), Release-Tag `3.19.15` (latest), Asset `rakscribe26.exe`, 56 560 416 Byte,
  **sha256 `9c7a91f8ec2e1105d0b7c05dfb17d4609d6854c3dfbf40ba117b78f29dea71de`**. Enthält 3.19.14 (bd8a4a1). Tests 44585270898,
  Build 44585294862, Windows-UI-Test 44585570908 – Tor: alle drei grün (`gh run view <id>`).
- Auf X: liegt danach 3.19.14 (vom Job davor) oder noch 3.19.13. Tausch → 3.19.15. Nie zurück auf ein älteres.
- ris-mods (Brücke, Formatierer, Abholer): **keine Änderung**. Neu in KaiScribe: `IBL_ABLAGE` (config.ini, Standard `X:\IBL-Vorbefunde`) –
  nichts eintragen, der Standard stimmt.

## Schritt 0 – Tore (nur lesen)
1. Release + Digest per API, die drei Läufe grün.
2. Live-Stand: SHA/Version von `X:\RaKScribe\rakscribe26.exe`, Größe/Änderungszeit von `X:\RaKScribe\rakscribe.log` (stand 19.11. seit 11:32
   still bei 1 000 059 Byte – 3.19.15 schreibt wieder, siehe Schritt 3).
3. Niemand arbeitet am Büro-PC (die eigene RDP-Sitzung des Macs zählt nicht).

## Schritt 1 – PFLICHT-Abnahme am Testpatienten 451898 (VOR dem Tausch auf X:, nie vidieren)
Ohne diesen Beleg wird **nicht** eingespielt, die Vorversion bleibt (Grund in den Bericht, Folgejob `…-f1` ab 20:15 am nächsten Werktag).
1. 3.19.15 nur für den Testlauf starten (wie `kaiscribe_x_tauschen.ps1 -Schritt holen` es lokal ablegt bzw. die geprüfte EXE aus
   `%LOCALAPPDATA%\hermes\work\ks_tausch\v3.19.15\` direkt starten) – X: noch nicht anfassen.
2. Testeintrag 451898 mit **zwei Leistungen: fuss2 (Fuß bds.) + bü (Becken)** über die Teststrecke (ris-mods `ordi-hermes/teststrecke/ks.py`
   bzw. `buero/kaiscribe.py diktat`). Geht das nicht: eine Leistung je Lauf (zuerst fuss2, dann bü) und das im Bericht sagen.
3. **Echte Bausteine** (anonyme echte Fälle, nur Winkel) für die AccNo des Testeintrags in die Ablage legen:
   `python3 tools/ibl_abnahme_bausteine.py X:\IBL-Vorbefunde --frog <Nr>1 --hippo <Nr>2` (Nr = 11-stellige Diktatnummer des Testeintrags,
   Ziffer = Stelle der Leistung). Das Skript gibt den erwarteten Text aus. FROG = Fall vom 19.11. (Digitus quintus varus beidseits),
   HIPPO = Fall 52 vom 18.11. Brücke liest sie (am Büro-PC Brücke 2.5.22, Band „IB Lab: FROG beidseits ✓ · HIPPO beidseits ✓“).
4. Diktat (F10/F12 über die Teststrecke): „Fuß beidseits unauffällig. Beckenübersicht unauffällig.“ → INS.
   **Erwartet im Befundfenster** (Wortlaut der Sätze, KI-Text drumherum darf abweichen):
   - „## Fuß beidseits in 2 Ebenen“: **„Varusstellung der Kleinzehe beidseits mit einem Metatarsophalangealwinkel V von rechts 17° und links
     13°.“** an der Stelle von „Das Fußskelett ist (beidseits) nach Form … normal.“; „Das Fußgewölbe ist regulär ausgebildet.“;
     Ergebnis erster Punkt **„Digitus quintus varus beidseits.“**, kein „Regelrechte Darstellung des Fußskeletts …“, ganz unten ohne Nummer
     „Weitere Winkelmessungen sind den KI-Auswertungsbildern im PACS zu entnehmen.“
   - Becken: HIPPO-Sätze (Beckenschiefstand 7 mm rechts tieferstehend, BLD 1 mm links kürzer, LCE/AI/CCD) am Anfang der Beschreibung,
     Ergebnis „Grenzwertige Überdachung … Coxa valga beidseits.“, Schlussanmerkung „LCE = … Weitere Winkelmessungen …“ ohne Nummer.
   - Keine Normbereiche, keine Messzeilen „… (IB Lab FROG).“, keine rote Zeile.
5. EOL → **Brief belegen** (nur lesen): der fertige Brief (RTF/Word des Testeintrags bzw. `X:\RaKScribe\Daten\laeufe\<Nr>_*.json`
   `ergebnis_vorschlag` + `ibl_zeilen` > 0) enthält die Sätze aus 4. Screenshot des Befundfensters + Textauszug in den Bericht.
6. Zusatz (empfohlen, 5 min): derselbe Lauf mit einer Brücken-Datei OHNE „befundtext“ geht am Büro-PC nicht (Brücke 2.5.22). Dafür prüft
   der Kontroll-Job morgen CASWS08 (dort lief zuletzt Brücke 2.5.15). Nichts nachbauen.
7. Bausteine aus `X:\IBL-Vorbefunde` wieder entfernen (nur die zwei Testdateien), Testeintrag stornieren wie in der Teststrecke üblich.

## Schritt 2 – Tausch (nur wenn Schritt 1 belegt)
- ris-mods `ordi-hermes/kaiscribe_x_tauschen.ps1`: EXE direkt von github.com nach `%LOCALAPPDATA%\hermes\work\ks_tausch\v3.19.15\rakscribe26.exe`,
  SHA prüfen, dann `-Schritt exe -Tag 3.19.15 -Sha 9c7a91f8…71de`. **NICHT** `-Schritt holen` auf X:.
- Beleg: `KS_TAUSCH=ok neu=9c7a91f8ec2e alt=…`, Sicherung `rakscribe26.exe.vor3.19.15-….alt`, Titel „KaiScribe 3.19.15 – Röntgen am Kai“.
- Rückweg: `-Schritt zurueck`. Bei Rot: alte Version bleibt bzw. zurück, Grund in den Bericht.

## Schritt 3 – Log läuft wieder
Nach dem ersten Start von 3.19.15 von X:: `X:\RaKScribe\rakscribe.log` wird rotiert (`rakscribe.log.1` neu) bzw. wächst wieder; `[INIT]`-
Zeile mit 3.19.15 steht drin. Scheitert das Rotieren (Datei an anderem PC mit alter Version offen), hängt 3.19.15 trotzdem an – die alten
Instanzen (3.19.13/14) schreiben erst nach ihrem Neustart wieder.

## Schritt 4 – Bericht
`docs/einspielen/ergebnis_frog_einsetzen_n1_<datum>.md` (Tore, Stände vorher/nachher, Abnahme-Wortlaut FROG + HIPPO, Brief-Auszug,
Tausch, Log, Rückweg), keine Patientendaten. Meldung nach außen nur über den Queue-Abschluss und nur, wenn live belegt, z. B.:
„KaiScribe 3.19.15: IB-Lab-FROG-Text kommt wieder in den Befund (auch an PCs mit älterer Brücke), abgenommen am Testpatienten mit echtem
FROG- und HIPPO-Baustein; aktiv seit <Datum Uhrzeit>.“
