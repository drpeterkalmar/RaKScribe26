# Bericht kaiscribe-gws-seitlich-vorlage-n1 (Teil 1, Fr 20.11.2026, Mac, ohne Büro-PC)

**Für den Einspiel-Auftrag:** Version **3.19.18** = Commit **62d22f7** (Änderung 3d893a1). Release 3.19.18 ist „latest“:
`rakscribe26.exe`, 56 591 220 Byte, sha256 `65606fdfc184c17e0e1674fd6d6208eb3e28c0568c56595cf60512793900be64`. Enthält 3.19.16
und 3.19.17. Der Abend-Auftrag `kaiscribe-befundfeld-sicher-n1-einspielen-f1` hat dazu einen Nachtrag bekommen (ein Tausch je
Abend). Die Anleitung steht in `FOLGEJOB-KAISCRIBE-GWS-SEITLICH-VORLAGE-N1-EINSPIELEN.md`.

## Ursache (nur lesend geklärt, aus den Unterlagen im Repo)
- Leistungskatalog der Praxis (ris-mods `auditor/regeln/pflicht_ebenen.toml`, nur Kürzel und Kurztext):
  `gws` „WS Ganzaufn. ap + stl. geteilt“, `gesws2` „WS Ganzaufn.im Stehen ap+seitl“, `wsg2` „WS Ganzaufn.steh.ap u.seitl.“,
  `gws1` „Gesamte Wirbelsäule stehend“, `gws2` „Ges.Wirbelsäule steh.ap+stl.“, `wsap` „Wirbelsäule ap.“.
- Die Brücke (ris-mods `katalog/kuerzel_vorlage.tsv`) ordnet **gws, gesws2 und wsg2 der Vorlage „Ganzaufnahme der Wirbelsäule
  a.-p.“** zu, obwohl der Leistungstext „seitlich“ nennt. Nur gws1/gws2 gehen auf „Gesamte Wirbelsäule“, wsap hat „?“.
- Häufigkeit: Die Plaza-Auswertung (ris-mods `BERICHT_ibl_weiche_n2.md`, 21.10.–10.11.) fand 24 Ganz-WS-Untersuchungen,
  **gws 23×, gesws2 1×**. Zu fast jeder gehören einzelne Seitbilder von HWS, BWS und LWS. Eine reine a.p.-Ganzaufnahme kam
  dort nicht vor. Eine Zählung der CAS-Leistungsliste über 3 Monate ging ohne Büro-PC nicht; sie steht als Lücke im Folgeauftrag.
- Darum bekam fast jede GWS die a.p.-Vorlage ohne HWS/BWS/LWS-Abschnitte. Das Diktat allein half nicht, denn „Ganzaufnahme“
  ohne HWS führte immer zu a.p.

## Was KaiScribe 3.19.18 jetzt macht
- **CAS-Leistung (Ziel a):** Nennt der Leistungstext Ganzaufnahme **und** seitlich („seitl“, „stl.“, „lateral“), gilt
  „Gesamte Wirbelsäule“. Das gilt auch, wenn das Diktat keine Region nennt oder nur „Ganzaufnahme …“, „LWS: …“ oder „HWS … LWS …“
  sagt. Der Arzt diktiert nur das Auffällige, die KI ersetzt den passenden Normalsatz im Abschnitt
  (`cas_vorlagen.gws_vorlage`, `abgleich` mit `WS_TEILE`).
- **Nur a.p. gebucht** (oder „Gesamte Wirbelsäule stehend“ ohne „seitlich“): wie bisher, das Diktat entscheidet.
- **Rückfall (b) ohne oder mit unklarer Leistung:** „Ganzaufnahme“ zusammen mit „in 2 Ebenen“, „a.p. und seitlich“ oder
  „seitlich“ im Diktat ergibt „Gesamte Wirbelsäule“; „ohne seitliche Aufnahme“ nicht. Die Regel steht in `vorlagen_vorrang.json`
  und gilt damit gleich für EXE und Web.
- **IB-Lab-Gerüst:** nimmt die Vorlage so, wie die Vorlagenwahl sie bestimmt (Titel „Gesamte Wirbelsäule“ bei gws).
- **SQUIRREL (3.19.17):** funktioniert auf der Gesamt-Vorlage unverändert. Mit Diktat „flachbogige skoliotische Asymmetrie“
  bleibt die Wortwahl, dahinter steht nur der Cobb-Satz 44°. „Normaler Achsenverlauf“ und „Annähernd achsengerechte Stellung“
  entfallen, „Harmonische Kyphose“ bleibt.
- Unverändert: Mehrfachdiktat GWS + Becken ergibt zwei Befunde, hws_und_lws ohne CAS bleibt, gws + flws behält die
  Funktions-Vorlage. Das Regel-Register hat die neue Regel `gws-seitlich-vorlage` bekommen, keine Regel wurde entfernt.

## Tests
- Neu: `tests/offline/test_gws_seitlich.py` mit 40 Prüfungen, in CI eingetragen. Geprüft werden die GWS-a.p.-Leistung,
  die GWS+seitlich-Leistung ohne Region, der Stichwort-Rückfall, SQUIRREL mit Cobb 44° und dem Diktat „flachbogige
  skoliotische Asymmetrie“, GWS + Becken in der ganzen EXE-Kette mit KI-Attrappe und die Kette ohne CAS.
- Fixtures: 5 Fälle in `detect_fixtures.json` (Parität EXE = Web), 3 in `vorlagen_vorrang_tests.json`.
- Am Mac sind alle Offline-Tests grün außer `test_cas_auftrag` und `test_maske_ablauf`. Die sind auf dem unveränderten main genauso
  rot (Mac-Umgebung: Python 3.9 bzw. fehlendes Tk). Die Web-Tests (pipeline, speechmike, audio, llm_anbieter) sind grün.
- GitHub: Tests 44801634004, Build EXE 44802409278 und Windows-UI-Test 44802658766 sind grün. Web 3.19.18 ist live auf Pages.

## Offen
- Einspielen und Abnahme am 451898 macht der Abend-Auftrag (Nachtrag an `kaiscribe-befundfeld-sicher-n1-einspielen-f1`).
- Die Vorlage „Ganzaufnahme der Wirbelsäule a.-p.“ enthält im Normaltext „flachbogige rechts-konvexe Skoliose“. Mit SQUIRREL
  wird das ersetzt, ohne SQUIRREL bleibt es stehen. Seit 3.19.18 betrifft das nur noch reine a.p.-Aufnahmen. Ob der Satz
  „Normale Stellung.“ heißen soll, entscheidet Peter (Kanban-Karte).
- Langfristig wäre es sauberer, auch in ris-mods `katalog/kuerzel_vorlage.tsv` gws/gesws2/wsg2 auf `wirbelsäule_gesamt` zu
  stellen. Nötig ist das nicht, weil KaiScribe es selbst erkennt; eine Brücken-Änderung bräuchte den Windows-Test.
