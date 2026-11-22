# Bericht kaiscribe-rho-osteopen-n1 – Rho ≥ 7 → „Osteopenischer Knochenaspekt.“ statt Mineralisations-Normalsatz (So 22.11.2026)

## Für Georg
- **Live seit So 22.11. 18:24: KaiScribe 3.22.4 (EXE auf X: und Web).** Setzt KaiScribe den Rho-Schlussbefund („Rho 7/8…“ diktiert),
  steht in der Beschreibung **jeder** Röntgen-Untersuchung des Auftrags „Osteopenischer Knochenaspekt.“ statt „Mineralgehalt und
  Knochenstruktur … regelrecht“ (alle Formen aus den Vorlagen). „Im Übrigen …“ bleibt davor. Das Ergebnis bleibt, wie es war.
- Bei Score < 7 oder ohne Rho-Text bleibt der Normalsatz. Hast du Mineralisation, Osteopenie oder Osteoporose selbst diktiert, gilt dein Diktat. Der Satz steht nie doppelt.
- **Am Testpatienten belegt (Brieftext, echte KI):** Rho 8 LWS → ersetzt. Rho 6 → Normalsatz bleibt. LWS + Becken mit Rho 8 → in beiden Teilen ersetzt.
- **Noch offen:** Kommt Rho nur von IB Lab (nicht diktiert), setzt der Formatierer den Screening-Text. Dort fehlt der Ersatz noch.
  Er hängt an den gleichen Bedingungen (LWS, keine DEXA < 2 J). Der Folgeauftrag `rho-osteopen-formatierer-n1` ist eingereiht
  (Bau, Einspielen, Abnahme mit echtem Rho-Baustein). Bis dahin steht in diesen Briefen weiter der Normalsatz neben dem Screening-Text.
- Mo 23.11. ab 11:30 prüft `kaiscribe-rho-osteopen-kontrolle` die ersten echten Fälle, nur lesend.

## Technik
- Regel: `source_code/befund_regeln.py` `osteopen_ersetzen` = `web_app/src/befundRegeln.ts` `osteopenErsetzen`, ganz am Schluss
  der Kette (`pipeline._osteopen` nach Wächtern und IB Lab; auch Restructure, dort zählen Peters eigene Sätze als Diktat).
  Gemeinsame Fixtures `befund_regeln_fixtures.json` → `rho.osteopen` (10 Fälle, je zweimal angewandt gleich), Kettentest
  `tests/offline/test_rho_osteopen.py` (Score 6/7, Mehrfach LWS + Becken 8, Diktat Osteopenie/Mineralgehalt/Osteoporose,
  IB-Lab-Rho ohne Rho-Text = DEXA < 2 J, alle Röntgen-Vorlagen erkannt), Regel-Register `rho-osteopen` (111 Regeln, keine entfernt).
- Tests: ganze Offline-Reihe aus `test.yml` grün (Hetzner, vor jedem Push), `tsc`/`eslint` grün; GitHub `Tests` grün,
  Windows-UI-Test 45043679230 grün. Release 3.22.4: `KaiScribe.exe` = `rakscribe26.exe`, 56 671 754 Byte, sha256
  `b261f5ca92697a90efdb4feac85b5a0f885d74076d805e8c2c8ca3caea844778`. Pages: Lauf 45044976448 grün, live = 3.22.4. Zwei
  automatische Läufe davor scheiterten an GitHub („github-pages“-Artefakt doppelt bzw. nicht gefunden).
  Grep „BEGIN PRIVATE KEY“ in den Änderungen = 0.
- Abnahme (Büro-PC, 17:57–17:59): `tools/buero/rho_osteopen_abnahme.py` nutzt ris-mods `e2e/diktat_e2e.py`. Dabei läuft eine KaiScribe-Kopie 3.22.4
  als Gast mit echtem CAS-Auftrag. Der Diktattext wird getippt (keine Spracherkennung), die KI ist Claude Sonnet 5.5 wie im Betrieb. Danach EOL und Ablage
  `<Nr>.rakscribe.txt` mit JobFinished. 20261122001 (R8) OSTEOPEN=1/Normalsatz 0, 20261122002 (R6) 0/1 ohne Rho-Text, 20261122004 (M8,
  lws + bü) 2/0. Je 6/6 E2E-Prüfungen. Alle Einträge (001–004) storniert, nichts vidiert, LETTERS 0.
- Tausch X: 18:24 per `kaiscribe_x_tauschen.ps1 -Schritt exe` (Rückweg `-Schritt zurueck`, Sicherung
  `KaiScribe.exe.vor3.22.4-20261122-182410.alt`), Live-Titel 3.22.4, keine Fehlerzeilen. Belege: `~/cj/work/kaiscribe-rho-osteopen-n1/`.
- Hinweis Teststrecke: `strecke.py storno` wartet bei einer RDP-Sitzung von hermes-standby (Hetzner). Diese Sitzung ist unsere eigene. Die Wache kennt sie nicht, darum hat der Ordi-Hermes direkt mit `storno.ps1` storniert (PatNr-Prüfung 451898). Karte #493.
