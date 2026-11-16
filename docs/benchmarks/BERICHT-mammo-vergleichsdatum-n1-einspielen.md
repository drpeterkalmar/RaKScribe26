# Bericht kaiscribe-mammo-vergleichsdatum-n1-einspielen (Mo 16.11.2026, Hetzner + Büro-PC)

Ziel: Mammo-Maske „Vergleichsdatum im Vorschlag“ (3.19.3) bauen, auf X: einspielen, abnehmen.

## Kurz
1. **Eingespielt:** KaiScribe **3.19.4** läuft seit 23:07 auf X: (Büro-PC CASWS14). 3.19.4 enthält 3.19.3 (Mammo-Vergleichsdatum), 3.19.2 (Schulter) und die Knie-/Patella-Änderung.
2. **Abnahme am Testpatienten 451898: nicht möglich, Lücke.** Er hat laut Echttest `kaiscribe-mammo-lauf-n2-echttest` heute keinen Mammo-Vorbefund („Vorbefund keiner“). Nach Brief nicht an echten Patienten testen. Ein Log-Beleg aus dem Live-Betrieb gibt es noch nicht, weil seit dem Tausch keine Mammo-Maske mit Vorbefund lief.
3. **Georg:** noch nicht melden. Erst wenn alle Befund-PCs die Version laufen haben und eine Mammo mit Vorbefund den Beleg liefert (siehe offene Punkte).

## Schritt 0 – Tore
- main: `vorschlag_mit_datum`, `weitere_daten`, `Maske.datum_hinweis` vorhanden; `VERSION` = 3.19.4 (höher als 3.19.3, enthält die Änderung).
- Offline-Gates komplett grün (alle `tests/offline/*test*.py` + 7 Web-Tests, tkinter-venv, Hetzner). `test_maske.py`: MASKE PASS, mit Fällen zu Vergleichsdatum, weiterem Datum im Text, „heute selbst getippt“.
- Live-Stand vorher: KaiScribe 3.19.1 auf X:; niemand außer dem eigenen Mac-Client verbunden; letzte Aufnahme 20:18:56 (geschlossen); Word, Brücke, MammoDoppel aus.

## Schritt 1 – Bau + Release
- Den Bau 3.19.4 (Commit 1a3512d) hatte der Job kaiscribe-kniepat-titel-n1 schon über GitHub Actions gestartet. Ich habe keinen zweiten Bau ausgelöst (keine Doppelbauten).
- Release **3.19.4**, Asset `rakscribe26.exe`, 56.811.184 Bytes, SHA256 `5e1308dc46a5a7640f7217876b6f82d4a20fc471264da894df7b721cc8a4b2d0`.
- Windows UI-Test (EXE), Lauf 43963359467: **success**.

## Schritt 2 – Einspielen (Ordi-Hermes, 23:05–23:09)
- Auftrag/Antwort: `docs/benchmarks/mammo_vergleichsdatum_einspielen/a1.txt`, `a1_antwort.txt`.
- Download von GitHub, Größe und SHA stimmen. Skript `kaiscribe_x_tauschen.ps1` (SHA256 9e4d1188b0e6…).
- `KS_TAUSCH=ok SCHRITT=exe neu=5e1308dc46a5 alt=3dd3f3a04ef2 sicherung=rakscribe26.exe.vor3.19.4-20261116-230725.alt neu_gestartet=True`.
- 23:08: Titel „KaiScribe 3.19.4 - Röntgen am Kai“ (minimiert), `[INIT]` ohne Fehler (Speech-Bibliotheken geladen, SpeechClient und Gemini-Client [OK]), 0 Zeilen mit WinError/10013/Firewall/Netz/Fehler, kein neuer Dialog der Sicherheitssoftware.
- **Abweichung:** Der Ordi-Hermes hat vor dem Tausch nur Word, Brücke, MammoDoppel und KaiScribe geprüft, nicht CAS. CasMed („CAS - Med“, seit 20:15 offen) war an. In CAS wurde nichts angeklickt, KaiScribe lief minimiert ohne Aufnahme; ein Rückweg war nicht nötig. Die Prüfung auf CAS wird in künftige Einspiel-Aufträge aufgenommen, soweit nötig.

## Belege je PC
| PC | Stand |
|---|---|
| CASWS14 (Büro-PC) | 3.19.4 läuft seit 23:07:26 (Titel + INIT belegt) |
| CASWS10 | letzte Brückenzeile 16.11. 15:46:55, läuft noch die alte Version, bekommt 3.19.4 beim nächsten Start von X: |
| CASWS08 | letzte Brückenzeile 12.11. 11:50:42, bekommt 3.19.4 beim nächsten Start von X: |

Damit ist es **nicht** an allen Befund-PCs belegt live.

## Schritt 3 – Abnahme
- Kein Mammo-Vorbefund am 451898 → kein Test am Testpatienten, nichts angelegt, nichts vidiert/gemeldet, VM-Schalter unverändert.
- Ersatzbeleg: Offline-Tests grün (siehe oben). Der Live-Beleg (grauer Vorschlag mit Datum des Vorbefunds, Übernehmen → „Verglichen … vom <Datum>“, Hilfezeile bei weiterem Datum) steht aus.

## Rückweg
`kaiscribe_x_tauschen.ps1 -Schritt zurueck` (Sicherung `…vor3.19.4-20261116-230725.alt`), nur außerhalb 06:30–20:10.

## Offene Punkte
- Live-Beleg: sobald Georg/jemand eine Mammo mit Vorbefund im Maskenweg macht, im `rakscribe.log` bzw. in `X:\RaKScribe\Daten\laeufe\<Nr>_*.json` (`ergebnis_vorschlag`) das Datum prüfen. Alternativ ein Folgetest am 451898, sobald dort ein Mammo-Vorbefund angelegt ist (nur Peter/Queue).
- Meldung an Georg erst nach diesem Beleg und nach dem Neustart auf CASWS08/CASWS10.
