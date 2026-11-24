# Teil 2 zu kaiscribe-rho-regel-becken-n1 – Einspielen 3.26.0 + Abnahme (Ordi-Zeit, Büro-PC/VM) – Kanban #533

Georg 24.11.2026: „Bitte alles heute Abend erledigen.“ Teil 1 (Code, Offline-Tests, Version) ist fertig:
**KaiScribe 3.26.0 = origin/main 2a51626** (Code-Commit 00b3d3a), Bericht `BERICHT-KAISCRIBE-RHO-REGEL-BECKEN-N1.md`.
3.26.0 enthält auch 3.25.1 (SM-Wächter zählt nicht, Kanban #541) und Ursulas 3.25.0.
Regeln wie immer: Ordi-Systeme nur Mo–Do ab 17:30 / Fr ab 13:30 / WE, nie Mo 06:30–09:30; CAS nur über die Oberfläche;
Patientendaten bleiben auf der VM (an Anthropic nur maskiert); 451898 nie vidieren; Meldungsruhe (nur Kanban-Notizen,
Bericht). Der Brief sagte „die EXE spielt kaiscribe-schulter-ergebnis-n1-abnahme ein“ – diesen Job gab es am 24.11.
08:40 nicht in der Queue (kein wartender RaKScribe26-Einspielauftrag) → dieser Auftrag spielt selbst ein.

## A. Voraussetzung (nur lesen, VM)
- Abholer-Version auf der VM: HIPPO-Punkte ≥ 10 mm kommen nur mit **Abholer ≥ 1.3.18** (ris-mods cce497c, Feld
  `befundtext.ergebnis_becken`). Das Einspielen dort macht `ibl-rho-sc-ab7-weiche-bue-n1-einspielen` (gleicher Abend,
  Ordi exklusiv). Ist der Abholer noch älter: KaiScribe-Teil trotzdem einspielen (ohne die Liste ändert sich nichts,
  die alte Becken-Regel georg-hippo-10mm bleibt Rückfall), HIPPO-Abnahme mit der Testkopie (C.H1) und Lücke notieren.
- Belege RH 101 (13 mm re tiefer / 20 mm BLD) und RH 30 (12 mm): neueste HIPPO-Ablage-Datei je Accession auf der VM
  ansehen – steht `ergebnis_becken` drin (nur Struktur + die zwei Sätze ausgeben, keinen Befundtext)?

## B. Einspielen
Wie FOLGEJOB-KAISCRIBE-URSULA-2011-TEXT-N1-EINSPIELEN.md Teil B: EXE 3.26.0 bauen (Release vom Hetzner per API-Token),
X:-Tausch `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.26.0`; danach Fenster + SM-Wächter in 3.26.0, `[INIT] …`,
0 Fehlerzeilen (Autostart-Falle #541 ist mit 3.25.1 behoben – prüfen). Web: GitHub Pages zeigt 3.26.0 (Deploy prüfen).
Rückweg: `-Schritt zurueck`.

## C. Abnahme am Testpatienten 451898 (echter Lauf, Brieftext aktiv, sonst Rollback)
Mit echter Spracherkennung (WAV, Werkzeug wie `tools/buero/ursula_abnahme.py`), EOL → Brieftext im CAS ansehen,
Einträge stornieren, nichts vidieren. Je Fall `[RHO] …`-Logzeile und Anzeige-Hinweis notieren.
- **R1 (RH 124)**: CAS Handgelenk li., Diktat „Handgelenk links unauffällig. Rho 9.“ → KEIN Rho-Teil, kein
  „Osteopenischer Knochenaspekt“, Hinweis „Rho: kein Rho-Text – Rho-Region nicht LWS …“.
- **R2**: CAS LWS, Diktat „LWS: geringe Osteochondrose L5/S1. Rho 8.“ → Rho-Teil „Opportunistisches
  Knochendichtescreening (KI)“ am Schluss (Score 8, Ergebnis ohne Nummer) + „Osteopenischer Knochenaspekt.“ im LWS-Teil.
- **R3**: CAS LWS, Diktat „… Rho 6.“ → nichts von Rho, Mineralisations-Normalsatz bleibt.
- **H1 (HIPPO)**: CAS Beckenübersicht (bü). Gibt es an 451898 kein echtes HIPPO-Ergebnis: erfundenen HIPPO-Baustein
  (Format 1, `ergebnis_becken` = „Beckenschiefstand von 13 mm, rechts tieferstehend.“, „Beinlängendifferenz von 20 mm.“,
  Sätze wie in tests/offline/test_ibl_hippo_text.py „RH 101“) als Testkopie in die Ablage für die Abnahme-Nummer legen
  (wie FROG 3.19.15), danach wieder entfernen. Erwartet im Brief: Ergebnis 1. Beckenschiefstand von 13 mm, rechts
  tieferstehend. 2. Beinlängendifferenz von 20 mm., „Anmerkung: …“ darunter, kein „Regelrechte Darstellung des Beckens“.
  Gegenprobe 9 mm (nur Beschreibung, Normal-Ergebnis bleibt).
- Ist die Ursula-Abnahme 3.25.0 (BERICHT_kaiscribe-ursula-2011-text-n1.md, „Abnahme 451898 offen“) noch offen: in
  derselben Runde mit abnehmen (G1/H1/K1 aus `tools/buero/ursula_abnahme.py`) – eine Abnahme-Runde je Abend.
Grün → Bericht ergänzen (Abnahme-Zeilen), Kanban #533 Notiz + fertig. Rot → Rückweg + Karte (Spalte tun).

## D. Querverweis ris-mods (nur Doku)
`ibl/RHO_REGEL.md` (ris-mods): Zeile „KaiScribe (RaKScribe26) … Erzeugt KaiScribe selbst Rho-Text, muss es dieselbe
Regel nutzen“ ergänzen um „seit 3.26.0 umgesetzt: befund_regeln.rho_regel/rho_regel_anwenden (+ befundRegeln.ts),
Register RaKScribe26 tests/regel_register/regeln.json „rho-eine-regel“; Ausgänge: diktierter Schlussbefund, Osteopen,
Anzeige des IB-Lab-Rho-Bausteins“. Nur Doku – über die Arbeitskopie/zusammenfuehren von ris-mods, `--keine-tests`.

## E. Meldungen
Nur aus diesem Teil, wenn belegt live: Kanban #533 Notiz („3.26.0 live, R1–R3/H1 grün“) und auf fertig. Keine eigenen
Telegram-Meldungen (Meldungsruhe), die Abschlussmeldung schickt die Queue.
