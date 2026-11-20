# kaiscribe-gws-seitlich-vorlage-n1 – Einspielen 3.19.18 (GWS mit Seitaufnahme → „Gesamte Wirbelsäule“), Abnahme 451898

Wurde von `kaiscribe-gws-seitlich-vorlage-n1` (Teil 1, Fr 20.11.2026 abends, Mac) eingereiht, und zwar als **Nachtrag an den
wartenden Einspiel-Auftrag** `kaiscribe-befundfeld-sicher-n1-einspielen-f1`: ein Tausch und eine Abnahme-Runde je Abend.
Repo RaKScribe26, Ordi-Werkzeuge liegen in ris-mods. Ressource: ordi, automaten-vm.

> **MELDUNGSRUHE (Peter 11.11.2026):** Nichts selbst an Telegram schicken. Was nur Peter kann, geht über `kanban.py peter …`
> und eine Zeile „👉 …“.

ZUERST LESEN: `BERICHT-GWS-SEITLICH-VORLAGE-N1.md` (Ursache, Änderung, Tests). Ablauf von Tausch und Abnahme wie in
`FOLGEJOB-KAISCRIBE-MEHRFACH-SEITENLOS-N1-EINSPIELEN.md` (Tore, `kaiscribe_x_tauschen.ps1 -Schritt exe`, Rückweg, Zeitfenster
Mo–Fr 20:10–06:30, kein Klick am Büro-PC Mo–Fr 06:30–17:20).

## Was eingespielt wird
- **KaiScribe 3.19.18** = RaKScribe26 `62d22f7` (Änderung `3d893a1`). Release-Tag `3.19.18` ist „latest“, Asset
  `rakscribe26.exe` mit 56 591 220 Byte, **sha256 `65606fdfc184c17e0e1674fd6d6208eb3e28c0568c56595cf60512793900be64`**.
  Tests 44801634004 und Build 44802409278 sind grün, Windows-UI-Test 44802658766. Tor: alle drei grün.
- 3.19.18 enthält 3.19.16 (Befundfeld) und 3.19.17 (SQUIRREL). Wer heute Abend tauscht, nimmt **3.19.18 statt 3.19.17**.
  Liegt schon ein neueres grünes Release vor, das `3d893a1` enthält, wird das genommen. Nie zurück auf eine ältere Version.
- ris-mods (Brücke, Formatierer, Abholer): **keine Änderung**. Die Brücke ordnet `gws` weiter der a.p.-Vorlage zu; KaiScribe
  macht daraus selbst „Gesamte Wirbelsäule“, wenn der Leistungstext „seitl“/„stl.“ enthält.

## Abnahme am Testpatienten 451898 (nie vidieren)
- Testeintrag 451898 mit **Leistung gws** („WS Ganzaufn. ap + stl. geteilt“), über die Teststrecke KS. Klappt das Anlegen
  nicht, KaiScribe eine cas_leistungen-Datei geben:
  `[{"kurz":"gws","text":"WS Ganzaufn. ap + stl. geteilt","modalitaet":"Röntgen","vorlage":"ganzaufnahme_der_wirbelsäule_a-p"}]`
  (ohne CAS-Schreiben) und das im Bericht klar sagen.
- **Diktat A (ohne Region):** „Flachbogige skoliotische Asymmetrie. Osteochondrose L5/S1, sonst unauffällig.“
  Erwartet: Titel „## Gesamte Wirbelsäule“ mit den Abschnitten HWS, BWS und LWS. Die Asymmetrie steht wörtlich am Anfang.
  Die Osteochondrose L5/S1 ersetzt im LWS-Abschnitt den passenden Normalsatz („Kein Nachweis von Discopathien“). Kein
  „Ganzaufnahme der Wirbelsäule a.-p.“, keine Zeile „laut CAS, nicht diktiert“.
- **Diktat B (nur Ganzaufnahme genannt):** „Ganzaufnahme der Wirbelsäule: unauffällig.“ Erwartet: „Gesamte Wirbelsäule“ mit
  dem Normaltext von HWS, BWS und LWS.
- **Gegenprobe ohne gws** (nur wenn die Teststrecke es ohne Aufwand kann, Leistung `lws`): Diktat „LWS: Osteochondrose L5/S1“
  ergibt wie bisher „Lendenwirbelsäule in 2 Ebenen“.
- Optional, nur wenn für 451898 ein SQUIRREL-Baustein (Cobb 44°) da ist: Diktat A bekommt dann nur den Cobb-Satz hinter dem
  Diktat-Satz. „Normaler Achsenverlauf“ (HWS) und „Annähernd achsengerechte Stellung“ (LWS) fallen weg, „Harmonische Kyphose“
  bleibt. Ist kein Baustein da, gilt das als offen (offline geprüft in `tests/offline/test_gws_seitlich.py`).
- EOL bzw. Beleg nur lesend: In der Lauf-Datei `X:\RaKScribe\Daten\laeufe\<Nr>_*.json` steht `vorlagen` = `["wirbelsäule_gesamt"]`.
  Danach stornieren wie in der Teststrecke üblich. Den Befundtext von A und B wörtlich in den Brief bzw. Bericht (keine
  Patientendaten).
- **Release nur nach echtem Lauf am 451898.** Weicht der Text ab: Rückweg mit `-Schritt zurueck` auf die vorherige Version,
  Grund in den Bericht.

## Lücke aus Teil 1 (ohne Büro-PC nicht prüfbar)
- Wie oft gws, gesws2, wsg2 und wsap in den letzten 3 Monaten gebucht wurden, war von hier aus nicht zu zählen. Bekannt aus
  Plaza (ris-mods `BERICHT_ibl_weiche_n2.md`, 21.10.–10.11.): 24 Ganz-WS-Untersuchungen, davon gws 23× und gesws2 1×; zu
  jeder gehören seitliche Bilder. Wer das am Büro-PC nur lesend nachzählen kann (CAS-Leistungsliste, nur Kürzel und Zahl):
  Zahl in den Bericht. Für den Tausch ist das kein Tor.

## Bericht und Meldung
`docs/einspielen/ergebnis_gws_seitlich_vorlage_n1_<datum>.md` (Tore, Stände vorher und nachher, Tausch, Wortlaut A/B, Rückweg).
Meldung nach außen nur über den Queue-Abschluss und nur, wenn live belegt. Vorschlag an Georg (Thread wie im Auftrag):
„KaiScribe 3.19.18: Bei einer GWS mit Seitaufnahmen (Leistung gws) kommt jetzt automatisch die Vorlage ‚Gesamte Wirbelsäule‘
mit HWS/BWS/LWS. Ihr diktiert nur das Auffällige, HWS/BWS/LWS muss man nicht mehr dazusagen. Ohne Leistung reicht ‚in 2 Ebenen‘
oder ‚seitlich‘ im Diktat. Aktiv seit <Datum Uhrzeit>.“
