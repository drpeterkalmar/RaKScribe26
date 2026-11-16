# kaiscribe-mammo-vergleichsdatum-n1 – Mammo-Maske: altes Vergleichsdatum aus dem Vorbefund nie stehen lassen (KaiScribe @@VERSION@@)

Mo 16.11.2026 nachmittags, Hetzner, Teil 1 (Ursache, Code, Offline-Tests, Version). Am Büro-PC und an den Befund-PCs habe ich nichts gemacht.
Bau, Einspielen, Abnahme am 451898 und die Meldung an Georg macht der Folgejob **kaiscribe-mammo-vergleichsdatum-n1-einspielen**
(Brief `docs/benchmarks/mammo_vergleichsdatum_n1/folgejob_einspielen.md`, frühestens heute 20:15, Ressourcen ordi + automaten-vm).

Auftrag Georg 16.11. (Telegram Homepage): „bei ‚Im Vergleich zur Voruntersuchung‘ … Er übernimmt immer den Vorbefund. Da ist natürlich das falsche Datum drin.“

## Ursache (belegt)
- Beleg Ordi-Hermes (`ris-mods/ordi-hermes/ergebnis_georg_mammo_vergleichsdatum_20261116.md`), Fall 20261116124, KaiScribe 3.19.1:
  - KaiScribe hatte den richtigen Vorbefund: 20241018078, Untersuchung 18.10.2024 (Brief erst am 22.10.2024).
  - Dessen Feld Mammographie begann mit „Verglichen zur Voruntersuchung vom 14.11. 2019 …“. 14.11.2019 ist die Mammo davor.
  - Georg hat das alte Datum markiert und mit 10 Zeichen überdiktiert. Danach stand das Feld auf „getippt“.
- Im Code (3.19.1): `maske.vergleich()` ersetzt das Datum richtig (auch „14.11. 2019“ mit Leerzeichen). Aufgerufen wird es aber nur bei
  Übernehmen (F3/Play), beim Diktat „unverändert“ und beim Befund.
  - Den grauen Vorschlag zeigt `vorschau()` → `f.vorschlag`, und `_vorschlaege_setzen()` legt dort den Rohtext des Vorbefunds ab,
    mit dem alten Datum.
  - Wer hineinklickt, markiert, drüberdiktiert oder tippt (`_anwenden` art „ziel“ → GETIPPT, `tippen()`), arbeitet auf diesem Rohtext.
    Getippt bleibt seit 3.16.7 wie getippt, also griff `vergleich()` danach nie mehr.
- Das Datum selbst stimmt: Die Brücke liefert in `casdb` (`mammo_vb["datum"]`) das **Untersuchungsdatum** der letzten fertigen Mammo, nicht
  das Briefdatum. Im Fall: 18.10.2024 an KaiScribe, Brief 22.10.2024.

## Änderung (`source_code/maske.py`, `source_code/RaKScribe.py`)
1. `vorschlag_mit_datum(text, datum)`: Bei Vergleichs-Feldern (`vergleich: true`, also Mammographie und Sonographie) mit
   Vorbefund-Vorschlag wird das alte Vergleichsdatum im Kopf schon **im Vorschlag** zum Untersuchungsdatum des Vorbefunds. Es gelten
   dieselben Muster wie bei `vergleich()` (`_VERGLEICH_DATUM`/`_VERGLEICH_KOPF`, gemeinsam in `_kopf_datum_neu`):
   „Verglichen mit/zur/zu …“, „Im Vergleich zur Voruntersuchung vom …“, „(12.03.2022)“, „von 2022“, „vom März 2021“, zwei Daten.
   Es kommt **kein** „unverändert“ dazu. Ohne Vergleichskopf mit Datum bleibt der Text, wie er ist.
   Das gilt beim Öffnen und ebenso, wenn der Vorbefund nachkommt (`vorbefund_setzen()` → `_vorschlaege_setzen()`).
2. Datumsangaben **mitten im Text** („… seit 2019 größenkonstant“) ändert KaiScribe nicht. `weitere_daten()` findet sie, und
   `Maske.datum_hinweis()` gibt in der Hilfezeile aus: „Mammographie: Vorbefund nennt weiteres Datum (2019) – bitte prüfen“.
   Der Hinweis erscheint, solange das Feld den Vorbefund zeigt (Vorschlag oder übernommen). Ist das Feld heute getippt oder
   diktiert, verschwindet er. `RaKScribe._maske_warnung_text()` hängt ihn an.
3. Getippt und diktiert bleibt wie getippt (Regel 3.16.7). Markiert der Arzt das Datum und diktiert sein eigenes, gilt seines.
   Bei einem ganz neuen Diktat mit Datum gilt ebenfalls seines (`vergleich_diktat`, unverändert).
4. Übernehmen, „unverändert“ und Befund laufen wie bisher über `vergleich()`. Das ist idempotent auf dem schon korrigierten Vorschlag.
   An die KI geht der Vorbefund weiterhin nie.

## Tests (alle offline, Hetzner, venv mit tkinter)
- `tests/offline/maske_faelle.txt`, neuer Block `vorschlag_datum` mit 9 synthetischen Fällen: Georgs Fall „Verglichen zur Voruntersuchung vom
  14.11. 2019“, „Im Vergleich zur …“, Klammer, „von 2022“, zwei Daten, „Verglichen zu …“, Datum nur mitten im Text,
  Kopf plus weitere Daten, kein Kopf.
- `tests/offline/test_maske.py`, neue Prüfungen:
  - Vorschlag zeigt 18.10.2024 statt 14.11. 2019, ohne „unverändert“. Das Datum ist das **Untersuchungsdatum, nicht das Briefdatum**
    (Vorbefund mit `brief_datum`/`fertig` 22.10.2024 → 18.10.2024).
  - Inspektion (kein Vergleichs-Feld) bleibt, wie sie ist.
  - Übernehmen und Befund ergeben „Mammographie: Verglichen zur Voruntersuchung vom 18.10.2024 …“.
  - Vorbefund kommt nach („nachgekommen 4/4“): auch dann das neue Datum.
  - Markieren + Drüberdiktieren im Vorschlag: getippt mit 18.10.2024. Hineintippen ebenso.
  - Datum markiert und selbst „03.05.2023“ diktiert: seines bleibt, auch im Befund.
  - Weiteres Datum mitten im Text bleibt stehen. Hinweis „bitte prüfen“ bei Vorschlag und übernommen, weg nach Tippen.
- Ergebnis: `test_maske.py` 208/208 ✅. Alle 38 Gates aus `.github/workflows/test.yml` und die 6 übrigen `tests/offline/test_*.py` grün.

## Version
@@VERSION@@ (VERSION auf main, beim Zusammenführen vergeben).

## Offen → Folgejob `kaiscribe-mammo-vergleichsdatum-n1-einspielen`
- Bau + Release über `kaiscribe_bau.py --release` am Büro-PC (ab 20:10), UI-Test, Tausch auf X:.
- Abnahme am Testpatienten 451898 mit Mammo-Vorbefund (nie vidieren/melden), Ergebnis wörtlich.
- Lücke aus Teil 1: Ob 451898 überhaupt eine fertige Mammo mit Vergleichskopf samt Datum hat, habe ich nicht geprüft, weil das
  nur am Büro-PC geht. Der Folgejob klärt das in Schritt 3.
- Meldung an Georg schickt die Queue erst, wenn es an allen Befund-PCs belegt live ist.
