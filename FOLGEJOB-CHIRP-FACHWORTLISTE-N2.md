# chirp-fachwortliste-n2 – Nachmessung der SpeechMagic-Fachwortliste für Chirp (ab Mi 09.12.2026, VM) – Kanban #557

Vorlauf: BERICHT-CHIRP-FACHWORTLISTE-N1.md (24.11.2026). Die Liste `phrases.json` → `chirp_sm` (316 Einträge) und der
Schalter `CHIRP_SM` (Standard aus) sind auf main. Gemessen am 24.11.: rg Fachwort-Fehlhörer 55 → 44 (je Fall 12 besser /
5 schlechter, p ≈ 0,14), kp nur 6 Fälle, schlechter (8 → 11) → Schalter aus gelassen. Peter 24.11.: „1 ok, 2 ich vertraue dir,
3+4 ok, wenn gut bitte auch rg“.

## A. Messung (unabhängig, nur neue Fälle)
- Nur KaiScribe-Fälle mit Diktatnummer ab **20261125** (nicht für die Auswahl benutzt). `tools/vm/chirp_fachwort/cfw_messen.py`
  bekommt dafür einen Parameter „ab Nummer“ (Standard wie bisher). Bisherige `mess_*.jsonl` auf der VM nicht überschreiben:
  neuen Dateinamen-Zusatz `_n2`.
- Varianten `ohne,sm5` (sm5 = die gespeicherte Liste mit 316 Einträgen, Boost 5). Aufruf: `/usr/bin/python3 tools/chirp_sm/messen_mac.py …`
  (google-auth nur im System-Python 3.9), KAISCRIBE_TEST_JOB=chirp-fachwortliste-n2. Vorher die Minuten zählen,
  **Deckel 2 €** (0,022 €/min). Peter hat die Messung im Projekt rakscribe-test am 24.11. freigegeben. Die allgemeine
  Google-Testsperre nicht ändern.
- Datenschutz wie n1: Alles läuft auf der VM, zurück kommen nur Summen, Audio geht nur an Google EU, nichts an Anthropic.

## B. Entscheidung (Regel aus dem Auftrag)
- **kp:** Bedingung: ≥ 10 kp-Fälle, FH gesamt nicht schlechter und FH selten/Liste messbar besser (mehr Fälle besser als
  schlechter). Dann: CHIRP_SM = kp in die config.ini der kp-PCs (oder den Standard in config.py auf ["kp"], mit Version beim
  Zusammenführen). Release nach den Regeln aus n1: nur Mo–Do ab 17:30 / Fr ab 13:30 / WE, echter Lauf am Testpatienten
  451898 (nie vidieren), Logzeile „[CHIRP3] Fachwortliste SpeechMagic an (kp, 316 Phrasen, Boost 5)“, sonst Rückweg.
- **rg** erst nach kp live + 2–3 Ordi-Tage ohne neue Fehlhörer (Folgeauftrag). Info-Mail an Georg nur als Entwurf, Versand erst nach
  Peters Ok (Kanban grund freigabe).
- Zu wenige kp-Fälle oder nicht besser → Schalter aus lassen, Ergebnis-Notiz auf die Karte, fertig.

Meldungsruhe: keine eigenen Telegram-Meldungen.
