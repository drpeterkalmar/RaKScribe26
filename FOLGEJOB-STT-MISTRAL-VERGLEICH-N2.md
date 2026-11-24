# stt-mistral-vergleich-n2 – Voxtral gegen chirp_3 messen (sobald Kanban #561 erledigt ist)

Vorlauf: BERICHT-STT-MISTRAL-VERGLEICH-N1.md (24.11.2026). Start erst, wenn Peter Karte #561 erledigt hat: Vaultwarden-Eintrag
„Mistral API KaiScribe“ existiert (`python3 ~/.hermes/scripts/vw_get.py list mistral`), bezahlter Tarif, Training aus, DPA/AVV
akzeptiert (Datum von Peter auf der Karte). Fehlt etwas: nichts messen, Notiz auf #561, fertig.

## A. Ohne Patientenbezug (gleich nach dem Schlüssel)
1. `python3 tools/stt_mistral/voxtral_ab.py --modelle` → aktuelles Batch-Transkriptionsmodell wählen (Standard
   `voxtral-mini-latest`; gibt es ein neueres „Transcribe“-Modell, per `MISTRAL_STT_MODEL=…`).
2. `python3 tools/stt_mistral/voxtral_ab.py --laeufe 3` → 6 Sprachnachricht-Oggs + 9 Synthetik-Texte × 3 Listen-Varianten
   (ohne / chirp85 / chirp+sm, `context_bias` ≤ 100) × 3 Läufe ≈ 37 Audio-min ≈ 0,14 €. Deckel 5 € im Skript (Kostenbuch
   `docs/benchmarks/stt_mistral/kostenbuch.jsonl`). Lehnt die API `context_bias` ab (HTTP 400/422), wird die Variante
   ausgelassen – Fehlermeldung lesen und Format anpassen (z. B. nur Einzelwörter, andere Höchstzahl), dann nachmessen.
3. Opcodes ansehen, wenn WER > 20 % (Skill stt-quality-testing.md, Pitfall). chirp_3-Vergleich = Altwerte 04.10.
   (`chirp3_basis_20261004.json`); **keine neuen Google-Aufrufe**.

## B. Echte Praxisdiktate (nur mit AVV-Datum)
- Auf der VM liegen die chirp_3-Texte von 67 kp/rg-Fällen samt Referenz (`chirp_fw\mess_*.jsonl`, Variante „ohne“,
  chirp-fachwortliste-n1) = Google-Vergleich ohne neue Kosten. Voxtral auf dieselben WAVs (VM, `--echt <ordner>`
  mit `<name>.ref.txt`, `MISTRAL_AVV_BESTAETIGT=<Datum>`), zurück an den Mac nur Summen (WER, Fachwort-Fehlhörer, Seite,
  Zahlen, Verneinung). ~35 Audio-min × 3 Varianten ≈ 0,40 €.
- Optional Realtime (Live-Anzeige): Latenz bis erstes Wort an 2–3 Oggs, nur wenn A gut ist.

## C. Entscheidung (Bericht ≤10 Zeilen, Notiz auf #561)
- **wechseln** nur, wenn Voxtral auf B: WER nicht schlechter als chirp_3, Seitenfehler 0, Verneinungen/Zahlen nicht
  schlechter, Fachwort-Fehlhörer höchstens gleich. Dann Umbau als eigener Auftrag (Peter-Go, grund go).
- **erst mit Fachwortliste**: nur die Variante mit `context_bias` erreicht chirp_3.
- **nicht wechseln**: sonst; Gründe nennen.
Kein Umbau von KaiScribe in diesem Job. Meldungsruhe: keine eigenen Telegram-Meldungen.
