# kaiscribe-nicht-diktiert-streichen-n1 – Bericht Teil 1 (Do 26.11.2026 vormittags, Hetzner), Karte #542

- **Version:** KaiScribe **3.30.0** (main `2b08a63`). Release gebaut, `KaiScribe.exe` sha256
  `4f48fe2fab5cae8b1c119eafab41c97a788bbf5c1d199248cd9a92a0ac4381c3` (56.795.398 B). GitHub: Tests (aa96e55), Build EXE und
  Windows-UI-Test (2b08a63) grün. Noch **nicht live**: X: steht auf 3.28.2.
- **Was geändert:** `cas_vorlagen.nicht_diktiert_ergaenzen` (nur EXE, das Web hat kein CAS). Werden von mehreren
  CAS-Untersuchungen nur einige diktiert, bekommen die übrigen keinen Titel, keinen Normaltext und keinen Befund mehr.
  Stattdessen gibt es GENAU EINE rote Prüfzeile im Befundfenster: „BWS, LWS bestellt, aber nicht diktiert – bitte prüfen“.
  Unverändert bleiben der reine IB-Lab-Teil (Baustein mit Inhalt zur Region, z. B. Ganzbein mit LAMA), Funktions-Kombis, GWS und DEXA.
  Regel-Register: neu `georg-nicht-diktiert-streichen` (26.11.); `georg-nicht-diktiert-normal` (20.11.) steht als **ersetzt** drin (neuer Status, Test prüft `ersetzt_durch`).
- **Tests:** neu `tests/offline/test_nicht_diktiert_streichen.py` mit 17 Prüfungen: HWS + BWS/LWS, RH 68, LAMA mit/ohne Baustein, Funktion, alle diktiert, GWS, DEXA, Register.
  2 alte Erwartungen (test_georg_2011 „16“, test_ursula_2011 „6“) auf die neue Regel umgestellt. Alle 71 Offline-Gates grün.
  Nebenbei behoben: `test_uebung` war Mo–Fr vor 17:00 rot (Uhrzeit-abhängig), jetzt mit fester Uhr.
- **Probe 451898 (Bild):** noch offen → Teil 2 heute ab 17:35 (`FOLGEJOB-KAISCRIBE-NICHT-DIKTIERT-STREICHEN-N1-EINSPIELEN.md`,
  Werkzeug `tools/buero/nicht_diktiert_abnahme.py`). Dort wird auch der 3.29.x-Rückstand (Cache, DEXA-doppelt) mit eingespielt.
- **Satz für Ursula:** kommt erst aus Teil 2, wenn 3.30.0 belegt live ist.

## Abschluss
Georgs Entscheidung „1b“ ist gebaut: KaiScribe 3.30.0. Wird nur ein Teil der bestellten Untersuchungen diktiert, schreibt
KaiScribe für die übrigen keine Überschrift und keinen Normaltext mehr. Im Befundfenster steht dann eine einzige rote
Zeile, z. B. „BWS, LWS bestellt, aber nicht diktiert – bitte prüfen“. Ganzbein mit IB-Lab-Werten und Funktionsaufnahmen
bleiben wie bisher. Alle Tests sind grün. Eingespielt wird heute Abend ab 17:35 nach Ordi-Schluss, mit Probe am
Testpatienten. Erst danach gilt es an den Befund-PCs.

## Teil 2 – live (Fr 27.11.2026 00:35, Job kaiscribe-nicht-diktiert-streichen-n1-einspielen)
- **Version:** X: seit 27.11.2026 00:35 auf **KaiScribe 3.31.0** (enthält 3.30.0, 3.29.2 Cache, 3.29.0 DEXA-doppelt); Release-SHA `b1262bd7…c4ba` geprüft, Windows-UI-Test 123/123 für 7468767. Sicherung `KaiScribe.exe.vor3.31.0-20261127-003552.alt`.
- **Geändert:** Nicht diktierte Leistungen eines Mehrfach-Auftrags bekommen keinen Titel/Normaltext/Befund, dafür eine rote Prüfzeile „… bestellt, aber nicht diktiert – bitte prüfen“.
- **Probe 451898 (Kopie 3.31.0, LWS + Becken bestellt):** N1 (nur LWS diktiert) `NDABN=ok BEFUNDE=1 PRUEFZEILE=ja` (Log „[CAS] Becken: nicht diktiert → gestrichen“, „Hinweis: Becken bestellt, aber nicht diktiert – bitte prüfen“); Gegenprobe A1 (beide diktiert) `NDABN=ok BEFUNDE=2`, keine Prüfzeile (Nr. 20261126150/151, beide storniert, nie vidiert).
- **Bild:** keins – `diktat_e2e` hat keine Screenshot-Option; die Prüfzeile ist über Logzeile und Prüfung `pruefzeile_im_fenster=ja` belegt. Seitenbild nur bei einem echten Fall zu holen.
- **Für Ursula:** gilt ab Fr 27.11.2026 mit dem ersten KaiScribe-Start an jedem PC (alle starten von X:).
