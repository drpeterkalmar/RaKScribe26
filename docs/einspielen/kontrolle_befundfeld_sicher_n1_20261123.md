# Kontrolle Befundfeld-sicher – erste echte Fälle (Mo 23.11.2026, nur lesen)

Ich habe nur gelesen: das Protokoll über den Ordi-Hermes (Skript, nichts angeklickt, nichts verändert). Nummern stehen hier nur als A1, A2 …,
es gibt keine Namen und keinen Befundtext. kp = Peter, rg = zweites Kürzel.

**Ergebnis: Das Befundfeld macht, was es soll. Keine Fehler, kein „Restructure verworfen“, keine Ergänzung beim falschen Patienten.**
**Eine echte Lücke gibt es aber:** Drückt man **F1 während einer Ergänzung (Aufnahme läuft oder steht auf Pause)**, wird der vorhandene
Befund rechts gelöscht, und **„Rückgängig“ holt ihn nicht zurück**. Peter ist das heute zweimal passiert (siehe Punkt 4). Dafür gibt es die Karte (tun) unten.

## 1 Welche Logs (Schritt 0.4 aus Teil 1)
- `X:\KaiScribe\Programm\rakscribe.log`: 4894 Zeilen, **21.11. 08:50 → 23.11. 16:16**, keine `.1`-Dateien (noch keine Rotation).
- `X:\RaKScribe\rakscribe.log` (alter Ort): 3750 Zeilen, 20.11. 00:05 → 21.11. 05:02, Stand vor 3.19.16 (keine `[BEFUNDFELD]`-Zeilen).
- Für den Wechsel gibt es eine Lücke von 21.11. 05:02 bis 08:50, in der nichts protokolliert ist (Samstagmorgen, kein Fall).
  Der Brief nennt `X:\RaKScribe\rakscribe.log`, seit dem Umzug am 21.11. schreibt KaiScribe aber nach `X:\KaiScribe\Programm`.
- Lauf-Dateien ab 19.11.: 120 (451898 nicht darin). Versionen: 23.11. **3.22.4** (CASWS08 35, CASWS10 5, CASWS14 3), am 21.11. auf CASWS14
  3.20.1–3.21.1. Live war also nicht 3.20.5, sondern schon 3.22.x. Alle diese Versionen enthalten 3.19.16.

## 2 Befundfeld-Zeilen seit 21.11. 08:50 (alle Kürzel)
| Zeilenart | Anzahl |
|---|---|
| `[BEFUNDFELD] Record:` gesamt | 71 |
| … Neuer Befund / Neuer Befund (IB-Lab-Gerüst) | 35 / 26 |
| … Ergänzung (an Cursor-Stelle, `[EINFÜGEN]`) | 7 (kp 2, rg 5) |
| … Ergänzung (an das Ende angebaut) | 2 (beide rg) |
| … Maske | 1 |
| `[BEFUNDFELD] Ergänzung: … eingebaut` | 2 |
| `[EINFÜGEN] … eingefügt` | 5 (rg 5 von 5; kp 0 von 2, siehe Punkt 4) |
| Restructure gestartet / fertig / „keine Änderung“ / verworfen / Fehler | 1 / 0 / 1 / **0** / **0** |
| Strg+Z / Clear all / Reset (Knopf) | 0 / 0 / 0 |
| Traceback / EXCEPTION / FEHLER / ERROR im Log | **0** (seit 19.11.) |

- **Restructure** wurde einmal benutzt (rg, 13:33, „mit KaiScribe-Stand“). Ergebnis: „keine Änderung seit dem letzten KaiScribe-Stand“, also nichts umgebaut.
  Das ist richtig so, denn gleich nach dem Befund war nichts geändert worden. Einen Umbau mit geändertem Text gab es noch nicht.
- **Neuer Befund bei Text rechts:** In keinem Fall wurde ein stehender Befund durch Record ersetzt. Jeder „Neuer Befund“ kam von einem leeren
  Feld (direkt nach Auftrag oder EOL) oder kam gleich nach F1 (Zurücksetzen). Das ist so gewollt.

## 3 Ergänzung beim richtigen Patienten? (Reihenfolge Record → EOL je Diktatnummer)
- Alle **5 Cursor-Einfügungen von rg** kamen nach einem Befund desselben Auftrags (A66, A71, A87, A97, einmal ohne CAS) und gingen mit
  dem EOL **desselben** Auftrags hinaus (10:20, 11:15, 13:45, 14:19). Dazwischen war kein anderer Auftrag offen. ✔
- **A80 (rg, 12:57):** zuerst Gerüst-Befund, dann eine Ergänzung (21 Zeichen) zum eigenen Befund. ✔ 3 s später wurde das Fenster geschlossen
  (`abgebrochen (fenster_zu)`), dann derselbe Auftrag neu geöffnet („heute schon diktiert“) und mit EOL „ohne Aufnahme“ (667 Zeichen) abgeschlossen.
  Kein fremder Patient betroffen. Was der Arzt nach dem Neustart geschickt hat, lässt sich ohne Inhalt nicht sagen.
- **A83 (rg, 13:20):** Das **erste** Diktat nach frischem Programmstart und angenommenem Auftrag (Gerüst ins Feld eingesetzt) lief als
  **„Ergänzung“** statt als „Neuer Befund (IB-Lab-Gerüst)“. Die 364 Zeichen Diktat wurden also wörtlich an das Gerüst angehängt, statt einen Befund zu bauen.
  Ein fremder Patient ist ausgeschlossen, denn das Programm war gerade erst gestartet und im Feld konnte nur das Gerüst von A83 stehen.
  Die Ursache steht nicht im Log. Am wahrscheinlichsten wurde das Gerüst vor dem Diktat von Hand geändert (Tippen wird nicht protokolliert).
  Dann gilt es nicht mehr als „unberührt“, und so ist es auch gebaut. rg hat danach F1 gedrückt (diesmal mit „Stand gemerkt – Rückgängig möglich“),
  den Auftrag abgebrochen und ihn 13:31 neu diktiert. Dabei kamen korrekt „Neuer Befund (IB-Lab-Gerüst)“ und danach ein Restructure ohne Änderung.
  → Kein Fehler im Befundfeld, aber eine Falle bei der Bedienung. Kommt das öfter vor, sollte ein angefasstes Gerüst beim ersten Diktat trotzdem als Gerüst-Befund gelten (Notiz auf der Karte).

## 4 Peters Fälle (kp): „Record ohne [EINFÜGEN] … an Stelle, dann neuer Befund“
- Peters Fälle in den letzten Tagen: **21.11.** CASWS14, 17 Aufnahmen. Jede war das erste Diktat nach dem Auftrag (N/G), keine kam nach einem stehenden Befund.
  **23.11.** CASWS10, 5 Aufnahmen (08:10 G, 08:12 Cursor, 08:40 Maske, 08:47 N, 10:10 Cursor). Am 20.11. gibt es keine kp-Fälle im Log (nur rg/CASWS10).
- **Das gesuchte Muster kommt nicht vor.** Es gibt bei kp keinen Record ohne `[EINFÜGEN]`, auf den ein neuer Befund folgt, wenn schon Text dastand.
  Beide Cursor-Aufnahmen hatten die Zeile `[EINFÜGEN] Ergänzung an Cursor-Stelle … wird an Stelle … eingefügt`.
- **Stattdessen zweimal dieselbe Folge (08:12–08:13 A58, 10:10–10:12 A64; beide „Nur Text“ an):**
  RECORD, nach 1–2 s RECORD (= Pause), **kein INS**. Rund 1 min später EOL → „Erst INS, Befund prüfen, dann EOL“ (abgewiesen).
  Dann **F1** → `[UI] Zurücksetzen …`, das Gerüst kommt neu, und es gibt **keine** Zeile „Stand gemerkt“. Danach wurde das Fenster geschlossen und der Auftrag abgebrochen (`fenster_zu`).
  Beide Fälle gingen nicht über KaiScribe zu CAS und tauchen später nicht wieder auf.
- **Ursache im Code** (`reset_dictation`, `source_code/RaKScribe.py:2182`): Bei F1/F9 während Aufnahme oder Pause wird `_stand_merken()`
  absichtlich übersprungen, damit „nicht das halbe Diktat“ gemerkt wird. Seit 3.19.16 bleibt bei einer Ergänzung aber der fertige Befund rechts
  stehen, und genau den löscht F1 dann ohne Rückgängig-Stand. Das ist Peters Sorge „alles gelöscht“.
  (Bei rg A83 stand die Aufnahme schon auf „bereit“, deshalb wurde dort der Stand gemerkt.)
- Bei rg kommt „EOL vor INS → abgewiesen → F1 → neu diktieren“ öfter vor (12:46–12:53 sechsmal). Das passiert dort jeweils vor bzw. gleich nach
  dem eigenen Befund und kostet keinen fremden Text.

## Offen / weiter
- **Karte (tun) #518:** „F1/F9 während Ergänzung: Befund-Stand merken (Rückgängig)“. Gemeint ist: Im Zweig `stop_und_reset` bei `_einbau` ∈ {Ergänzung, Cursor}
  den Befund rechts (ohne halbes Diktat) als Rückgängig-Stand merken. Dazu vielleicht den Hinweis bei EOL in der Pause einer Ergänzung
  klarer machen („INS fügt die Ergänzung ein, dann EOL“). Neue Fälle in test_befundfeld.py.
- Ein Restructure mit wirklich geändertem Text gab es noch nicht. Das zeigt sich erst bei einer späteren Kontrolle.
- Werkzeug: `tools/vm/befundfeld_kontrolle_pruefen.py` (`--kompakt` = Zeitleiste, `--fenster TTHHMMSS-TTHHMMSS,…` = maskierte Zeilen).
  Es lief über den Ordi-Hermes (`hermes peer run ordi`, das Skript wird als gzip/Base64 im Auftrag mitgegeben), denn vom Hetzner gibt es keinen Weg zur VM per scp.
  Rohauszüge (nur Aliase) liegen in `~/cj/work/kaiscribe-befundfeld-sicher-n1-kontrolle/` (aus2.txt = Zeitleiste, aus3.txt = Fenster, nicht im Repo).

Meldung nach außen: keine. Für Peter: nichts zu tun (kein 👉).
