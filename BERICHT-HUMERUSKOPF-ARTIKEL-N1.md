# kaiscribe-humeruskopf-artikel-n1 – Schulter-Normalsatz mit Artikel (KaiScribe 3.19.2), Teil 1

Mo 16.11.2026 nachmittags, Hetzner. Auftrag Georg 16.11. (Foto Schulter-Normalbefund): „Der Humeruskopf. Bitte ändern“.
Ist „Humeruskopf in regelrechter Artikulation.“ → Soll „Der Humeruskopf steht in regelrechter Artikulation.“

## Ursache
Der Satz stammt wörtlich aus der Vorlage „Schultergelenk in 2 Ebenen“ (`templates.json`). Der Normalbefund-Bypass schreibt diese
Vorlage ohne KI. Dieselbe Fassung steht in `taught_blocks.json` und in einem ❌/✅-Beispiel des Prompts.

## Änderung (RaKScribe26 8d29db2, Version e84b617 = 3.19.2)
- `templates.json` (Röntgen-Schulter), `taught_blocks.json`, `radiology_prompt.txt` (beide Beispielsätze, Marker
  `2026-11-16-humeruskopf-artikel`, damit keine alte Prompt-Datei neben der EXE gewinnt). Scapula („Humeruskopf, Clavicula und
  Rippen: …“) und MR-Schulter („Humeruskopf: normal konfiguriert …“) unverändert.
- Erkennung tolerant: Die Abschnittsprüfung (fremder Vorlagensatz im falschen Abschnitt, z. B. Humeruskopf-Satz im Hüftbefund)
  kennt neben der neuen auch die alte Form ohne Artikel: `VORLAGEN_ALTFORMEN` in `befund_regeln.py` ≡ `befundRegeln.ts`.
  Die Tossy-Regel und das Merkmal „regelrechte … Artikulation“ greifen für beide Formen (Muster unabhängig von „steht“).
- `RULES_SYNC.md`: eine neue Zeile.

## Tests
- Fixtures (`befund_regeln_fixtures.json`): Tossy ×2 auf die neue Form, `abschnitte` mit alter Form (Hüfte → weg, Schulter → bleibt,
  diktiert → bleibt) und 2 neue mit der neuen Form. PY + TS 213/213.
- Neuer Regressionsfall `tests/offline/test_pipeline_exe.py`: Schulter-Normalbefund (EXE und Web-Kette) enthält „Der Humeruskopf
  steht in regelrechter Artikulation.“ und keinen Satz ohne Artikel.
- `tools/verify_georg_schulter_ellbogen.py`: erwarteter Vorlagensatz angepasst (Live-Test, nicht ausgeführt – kostet Geld, die
  Änderung ist deterministisch).
- Alle 38 Offline-Gates der CI grün (Server, venv mit tkinter), GitHub „Tests“ grün, Build 3.19.2, Windows-UI-Test 115/115
  (Lauf 43901994474). EXE sha256 `a45bbefef05153736c03c427e00d668b7ae243ede671756cea74384885b89aed`.
- `docs/benchmarks` nicht angefasst.

## Teil 2 (Folgejob)
`kaiscribe-humeruskopf-artikel-n1-einspielen`, Brief `FOLGEJOB-HUMERUSKOPF-ARTIKEL-N1-EINSPIELEN.md`: Einspielen nach 20:10,
Abnahme am Testpatienten 451898, danach Meldung an Georg (2 Zeilen, Gruppe Homepage). Hinweis: Auf main liegt schon 3.19.3
(Mammo-Vergleichsdatum, eigener Einspiel-Job) – eingespielt wird das neueste grüne Release mit diesem Commit, kein Doppel-Tausch.
Lücke: Kein Beleg vom Büro-PC, dass Georgs Foto aus dieser Vorlage stammt; das prüft die Abnahme.
