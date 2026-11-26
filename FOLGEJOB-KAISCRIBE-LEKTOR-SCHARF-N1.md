# kaiscribe-lektor-scharf-n1: Kosten belegen, dann Lektor für kp + rg scharf schalten (oder aus lassen)

Grundlage: Peter 26.11.2026 „Go: a“ (Kanban #531). Lektor ist ab KaiScribe 3.32.0 eingebaut, Schalter AUS
(`X:\KaiScribe\Daten\lektor.json`). Bericht `BERICHT-KAISCRIBE-LEKTOR-EINBAU-N1.md`, Teil 2
`FOLGEJOB-KAISCRIBE-LEKTOR-EINBAU-N1-EINSPIELEN.md` (muss fertig und grün sein, Tausch auf 3.32.0 erledigt).
Start frühestens am Abend des ersten vollen Ordi-Tags NACH dem Tausch (Mo–Do ab 17:30, Fr ab 13:30).

Regeln wie immer: Ordi-Systeme nur außerhalb der Ordi-Zeit, keine Patientendaten nach außen (nur Zahlen), Meldungsruhe.

## 1. KaiScribe-Kosten im echten Betrieb (Nachtrag „Betrieb nach dem Fix“ in `docs/benchmarks/BERICHT-kosten-n1.md`)
`tools/vm/kaiscribe_nutzung_lesen.py` (neue Fassung mit LEKTOR-Zeilen) per scp auf die VM und
`python3 tools/vm/x_lauf_hetzner.py 'C:\RaK\einrichtung\frogdiag\kaiscribe_nutzung_lesen.py' --tage <Ordi-Tage seit Tausch>`.
Nur Tage/PCs mit `LAUF … kaiscribe=3.29.2` oder neuer zählen. Bedingung (a): **`cache_ohne=0`** und
**`usd / anthropic ≤ 2 ct`** je KaiScribe-Aufruf (ohne die LEKTOR-Zeile). Stand 26.11.2026: im Betrieb lief noch 3.28.2,
Token-Zähler alle 0 → noch kein Beleg.

## 2. Konto-A-Rechnung (Bedingung b)
Hochgerechnet auf 3.000 Befunde/Monat, aus echten Nutzungsdaten:
- KaiScribe: ct je Befund aus 1. × 3.000
- Lektor: 1,31 ct je Aufruf, nur Nicht-Normalbefunde (≈ 84 %) ≈ **33 $/Monat** (Probe 26.11., 54 Aufrufe, Konto B);
  nach dem Scharf-Schalten aus den LEKTOR-Zeilen ersetzen
- übrige Konto-A-API-Dienste: KaiFormat (ris-mods `bruecke`, ki_maske-Weg), Ordimail, Überweisungen, Senf-API falls
  vorhanden — je Dienst aus seinen Zählern/Logs oder der Anthropic-Abrechnung je Schlüssel (nur Summen), Monat bisher
  hochgerechnet
- Summe **≤ 170 $** (30 $ Reserve unter 200 $)? Rechnung offen in den Bericht.

## 3. Entscheidung
- **(a) und (b) erfüllt:** nach Ordi-Schluss `X:\KaiScribe\Daten\lektor.json` = `{"befunder": {"kp": true, "rg": true},
  "monatsdeckel_usd": 40}` (wird alle 30 s gelesen, kein Neustart nötig). Am nächsten Ordi-Tag ab 17:30 Live-Beleg nur
  über Zähler: LEKTOR-Zeilen (aufrufe, uebernommen, pruefzeilen, ausfall, zu_spaet, deckel, usd) und `[LEKTOR]`-Zeilen im
  Log (nur Zahlen). Kanban #531 fertig setzen.
- **sonst:** Schalter bleibt aus. Kanban #531 bekommt die Zahlen (ct je Aufruf, cache_ohne, Konto-A-Summe) und was fehlt.
- Notaus jederzeit: `"kp": false` bzw. Datei löschen.

## Abschluss (≤ 6 Zeilen)
Version, Schalter-Stand (an/aus und warum), erste Live-Zahlen.
