# kaiscribe-mammo-vergleichsdatum-n1-einspielen – Mammo-Maske: neues Vergleichsdatum im Vorschlag bauen, einspielen, abnehmen (ab Mo 16.11.2026 20:15)

Eingereiht von `kaiscribe-mammo-vergleichsdatum-n1` (Teil 1, Mo 16.11. nachmittags, Hetzner). Repo RaKScribe26.
Ressourcen: ordi + automaten-vm. Alles, was am Büro-PC oder an den Befund-PCs etwas ändert (Bau, Tausch, Klicks, Testdiktat), läuft nur
werktags ab 20:10 bzw. am Wochenende. Nie in der Ordi-Zeit, nie Mo 06:30–09:30.
Startet der Job an einem Werktag nach 04:00: nichts halb einspielen. Dann denselben Brief als
`kaiscribe-mammo-vergleichsdatum-n1-einspielen-f1` für den nächsten Abend ab 20:15 einreihen.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram schicken (kein `hermes send`, kein Bot-API-Aufruf, kein Peer-Auftrag „schick …“).
> Was nur Peter kann → `python3 ~/.hermes/scripts/kanban.py peter …` und eine Zeile „👉 <was>, bis <wann>“. Ist etwas rot: selbst beheben oder Folgejob/Kanban-Karte.

ZUERST LESEN: `docs/benchmarks/BERICHT-mammo-vergleichsdatum-n1.md` (Ursache, Änderung, Tests, Version) und den Beleg
`ris-mods/ordi-hermes/ergebnis_georg_mammo_vergleichsdatum_20261116.md` (Fall 20261116124).

## Schritt 0 – Tore (nur lesen)
1. main enthält die Änderung: `source_code/maske.py` hat `vorschlag_mit_datum`, `weitere_daten` und `Maske.datum_hinweis`. In
   `VERSION` steht die Version aus Teil 1 (3.19.2 bzw. die Nummer im Bericht). Für diese Version gibt es noch kein Release.
   Hat inzwischen ein anderer Job eine höhere Version mit dieser Änderung gebaut, nimmst du die.
2. Offline-Gates grün (alle Dateien aus `.github/workflows/test.yml`, am Hetzner mit dem tkinter-venv, siehe Memory „Release vom Hetzner“).
3. Live-Stand lesen: welche KaiScribe-Version auf X: liegt (Titel bzw. `[INIT]`-Zeile in `X:\RaKScribe\rakscribe.log`) und
   ob am Büro-PC jemand verbunden ist (eigener Mac-RDP-Client = kein Hindernis, siehe BERICHT-mammo-lauf-n1).

## Schritt 1 – Bau + Release
- `~/.hermes/scripts/kaiscribe_bau.py --release` (Büro-PC baut, Windows-UI-Test, GitHub-Release), nur im erlaubten Fenster.
  Ist das Repo noch öffentlich und läuft der Bau sonst über GitHub Actions: Weg aus der Memory „Release vom Hetzner“
  (`build-exe.yml` per API dispatchen, danach auf den „Windows UI-Test (EXE)“ warten).
- UI-Test muss grün sein, sonst nicht einspielen. Rot → selbst beheben oder Folgejob.

## Schritt 2 – Einspielen (X:)
- Weg wie bei 3.19.1 (`docs/benchmarks/BERICHT-mammo-lauf-n1.md`, Abschnitt Einspielen): Ordi-Hermes lädt das Release-Asset direkt von
  GitHub nach `%LOCALAPPDATA%\hermes\work\ks_tausch\v<Tag>\rakscribe26.exe` und prüft die SHA. Danach
  `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag <Tag> -Sha <sha>`. Nicht `-Schritt holen` verwenden.
- Beleg: `KS_TAUSCH=ok`, Titel „KaiScribe <Version> - Röntgen am Kai“, `[INIT]`-Zeile, keine Fehlerzeilen. Die Befund-PCs bekommen die Version
  beim nächsten Start von X:. Beleg je PC: `X:\RaKScribe\Daten\protokolle\bruecke_<PC>.log` bzw. `[INIT]` im Log.
- Rückweg: `kaiscribe_x_tauschen.ps1 -Schritt zurueck`, nur außerhalb 06:30–20:10.

## Schritt 3 – Abnahme am Testpatienten 451898 (nie vidieren, nie melden)
- Die Mammo-Maske mit einem Mammo-Vorbefund öffnen. Weg wie beim Echttest `kaiscribe-mammo-lauf-n2-echttest` (Teststrecke KS, Ton vom Mac,
  CAS-Auftrag mit Mammo-Leistung). Vorher prüfen, ob 451898 eine fertige Mammo als Vorbefund hat und ob deren Text im
  Feld Mammographie mit einem Vergleichskopf samt Datum beginnt („Verglichen … vom <älteres Datum>“).
  - Hat er keinen solchen Vorbefund, nicht an echten Patienten testen. Dann reicht der Beleg im Log: Vorschlag (`_mk.vorschau`) bzw.
    Lauf-Datei `ergebnis_vorschlag` nach Übernehmen. Die Lücke kommt in den Bericht.
- Erwartet:
  1. Der graue Vorschlag im Feld Mammographie zeigt schon das Untersuchungsdatum des Vorbefunds (nicht das Briefdatum) und
     nicht mehr das ältere Datum. Ein „unverändert“ kommt dabei nicht dazu.
  2. Übernehmen (F3/Play) ergibt „Verglichen … vom <Datum des Vorbefunds> …“. So steht es im Befund und in der Lauf-Datei
     (`X:\RaKScribe\Daten\laeufe\<Nr>_*.json`, `ergebnis_vorschlag`).
  3. Nennt der Vorbefund mitten im Text ein weiteres Datum: Die Hilfezeile zeigt „Mammographie: Vorbefund nennt weiteres Datum (…) –
     bitte prüfen“, und der Text bleibt dabei unverändert.
- Ergebnis wörtlich in den Bericht, ohne Patientendaten (nur Feldtext, Datum, Version).
- Danach aufräumen wie im Echttest: Befund nicht vidieren, Testeintrag nicht melden. VM-Schalter wieder in den Ausgangszustand.
- Testeinträge am Testpatienten sehen auch die Schreibkräfte. Eine Ankündigung „nicht schreiben“ läuft über Kanban/Queue, nicht selbst.

## Grenzen
- CAS-DB nur lesen. Keine Patientendaten nach außen. Team nicht anschreiben, keine ESET-Ausnahmen.
- Fall 20261116124 nicht anfassen (Georg hat ihn selbst korrigiert).

## Abschluss
- Bericht `docs/benchmarks/BERICHT-mammo-vergleichsdatum-n1-einspielen.md` mit Toren, Release (Tag, SHA, UI-Test), Tausch, Belegen je PC,
  Abnahme wörtlich und Rückweg.
- Erst wenn es an allen Befund-PCs belegt live ist, schickt die Queue eine Zeile an Georg (Telegram-Gruppe Homepage, -5216773962), z. B.:
  „Mammo-Maske: Bei ‚Verglichen zur Voruntersuchung‘ steht jetzt gleich das Datum der letzten Mammographie, nicht mehr das alte Datum aus dem Vorbefund.“
