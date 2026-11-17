# kaiscribe-sonnet-n3-beleg – Beleg je Befund-PC (Claude Sonnet), Rückfälle, Chirp-Warnung als Kanban-Weg – 17.11.2026

**Ergebnis:** Alle echten KaiScribe-Befunde vom 16.11. hat **Claude Sonnet 5.5** geschrieben, es gab **0 Rückfälle** auf Gemini.
Das gilt für **CASWS10** (3.19.1, 8 Läufe) und den Büro-PC CASWS14. **CASWS08 und RAKCLIENT04 hatten keinen KaiScribe-Befund**:
Dort wurde seit 12.11. bzw. überhaupt noch nie für kp/rg diktiert. Es läuft dort auch keine alte Version.
Die Google-Spracherkennung wird **zu niedrig angezeigt**: Die Hochrechnung teilte durch den Tag des Monats, und die Live-Anzeige
(Streaming) wurde gar nicht gezählt. Beides ist behoben. Ein täglicher Weg legt bei mehr als 6 €/Monat eine Kanban-Karte an.

## 1. Beleg je PC (Lauf-Protokolle X:\RaKScribe\Daten\laeufe, nur Zähler)

Gelesen über die Automaten-VM (als rakauto, X: nur lesen, Leser `tools/vm/kaiscribe_nutzung_lesen.py`): Pro Rechner,
Modell und Version wurde nur gezählt, ohne Befundtext, Nr oder Benutzer.

| PC | Läufe 16.11. | Modell | KaiScribe | Claude-Befunde (Zähler) | Rückfälle | Chirp 16.11. | Stand |
|---|---|---|---|---|---|---|---|
| **CASWS10** | 8 (13:07–15:46, davon 1 Maske) | anthropic/claude-sonnet-5-5 (8/8) | 3.19.1 | 4 | 0 | 28,3 min | ✅ belegt |
| **CASWS14** (Büro-PC) | 3 (01:28–01:37 Probe sonnet-n2, 20:19 Maske) + 17.11. 13 Testläufe anderer Jobs (3.19.4) | anthropic/claude-sonnet-5-5 | 3.19.0 / 3.19.1 / 3.19.4 | 0 (16.11.) / 13 (17.11.) | 0 | 0,6 min | ✅ belegt |
| **CASWS08** | 0 | – | – | – | – | – | kein Befund |
| **RAKCLIENT04** | 0 | – | – | – | – | – | kein Befund |

Warum fehlen CASWS08 und RAKCLIENT04? Das ist keine alte KaiScribe:
- Die Brücke schickt nur Diktate der Benutzer **kp und rg** an KaiScribe (`X:\RaKScribe\Bruecke\benutzer.txt`).
- Für CASWS08 ist die letzte Brückenzeile vom **12.11. 11:50** (`bruecke_CASWS08.log`). RAKCLIENT04 ist seit 11.11. eingerichtet,
  hat aber **noch keine Brückenprotokoll-Datei**: Dort wurde noch nie ein kp/rg-Diktat an KaiScribe gegeben.
- Es gibt **keine einzige Lauf-Datei** von CASWS08/RAKCLIENT04 seit 12.11. Lauf-Dateien schreibt jede KaiScribe ab 3.18.5.
  Im gemeinsamen `X:\RaKScribe\rakscribe.log` gab es am 16.11. 8 Starts, alle auf CASWS10 (5×) oder CASWS14 (3×).
- Eine im Speicher hängende alte KaiScribe gibt es dort nicht: Die läuft nur, wenn die Brücke sie für ein kp/rg-Diktat startet.
  Beim nächsten Start nimmt sie die aktuelle EXE von X: (seit 16.11. 23:07: 3.19.4).

→ **Keine Kanban-Karte „neu starten“ nötig.** Ab jetzt prüft der tägliche Weg das selbst (Abschnitt 3): Schreibt ein Rechner noch
über Gemini (ohne Rückfall) oder mit einer Version unter 3.19.0, legt er einmal je Rechner die Karte „KaiScribe an <PC> einmal
schließen/neu starten“ an. Bis 17.11. 04:15 gab es keinen solchen Rechner.

Nebenbefund CASWS10: Zwischen 13:06 und 13:54 gab es 5 Starts, zwei davon ohne Diktat dazwischen (13:24:12/13:24:52). Im Log
stehen dazu 0 Traceback- und 0 WinError-Zeilen. Wahrscheinlich wurde KaiScribe geschlossen und wieder geöffnet; es sieht nicht
nach Abstürzen aus. CASWS10 läuft noch mit 3.19.1 und bekommt 3.19.4 beim nächsten Start (wie im Bericht humeruskopf-n1).

**Tagesbericht `X:\RaKScribe\Daten\nutzung\tagesbericht_2026-11-16.txt` wörtlich:**

```
KaiScribe Tagesbericht 2026-11-16 (alle PCs, ohne Patientendaten)
Befund-KI heute: 4 Befunde, Aufrufe Claude 5, Rückfälle auf Gemini 0, nur Gemini 0
Befund-KI Monat 2026-11: Aufrufe Claude 5, Rückfälle auf Gemini 0, Anthropic 0.22 $ (heute 0.22 $)
Spracherkennung Chirp: heute 28.9 min, Monat 28.9 min ≈ 0.40 € (× 0.016 $/min), hochgerechnet 0.75 €/Monat
  CASWS10: heute Befunde 4, Claude 4, Rückfall 0, Gemini 0, Chirp 28.3 min
  CASWS14: heute Befunde 0, Claude 1, Rückfall 0, Gemini 0, Chirp 0.6 min
```

Monatsdateien `2026-11_CASWS10.json` und `2026-11_CASWS14.json` enthalten keine Rückfälle und keine Gründe.
`2026-11_CASWS08.json` und `2026-11_RAKCLIENT04.json` gibt es nicht, weil diese PCs nicht gezählt haben.
Es gibt keine `warnung_2026-11.txt`.

## 2. Rückfälle

**0 von 18** Claude-Aufrufen (16.11.: 5, 17.11. bis 02:55: 13), also 0 %. Kein Grund kommt gehäuft vor, deshalb ist im Code
nichts zu ändern. Die Datenmenge ist klein, weil nur kp/rg über KaiScribe laufen und am 16.11. erst ab 13 Uhr an CASWS10.

## 3. Google-Spracherkennung: zwei Zählfehler behoben + Kanban-Weg

**a) Hochrechnung (EXE, `source_code/nutzung.py`):** Die Formel war „Monat bisher / Tag des Monats × Monatstage“. Der Zähler
gibt es aber erst seit 16.11., deshalb wurde ein Ordi-Tag durch 16 geteilt. Ergebnis im Tagesbericht: **0,75 €/Monat**, real
liegt der Wert eher bei ≈ 8 € (siehe unten). Neu wird ab dem ersten Tag mit Zählerdaten im Monat gerechnet. Die Warnung kommt
erst ab 3 gezählten Tagen, weil ein einzelner Tag zu zufällig ist. Der Tagesbericht zeigt dazu „(aus N Tagen)“.

**b) Live-Anzeige wurde nicht gezählt:** Während jeder Aufnahme schickt KaiScribe das Audio zusätzlich an den Google-Streaming-
Dienst (Speech v1 `latest_long`, die Live-Anzeige). Am 16.11. lief er bei jeder CASWS10-Aufnahme mit (`[GOOGLE] Streaming-Request
beendet`). Das kostet etwa so viel wie Chirp (Listenpreis ≈ 0,024 $/min), wurde aber nicht gezählt. Neu: `aufnahme.ZAEHLER`
→ `stt_s.streaming`. Tagesbericht und Warnung rechnen Chirp + Live zusammen.

Beide Änderungen kommen in der EXE erst mit dem **nächsten Release** an (hier nicht gebaut; Versionsnummer und Einspielen
gehören zum Release-Weg). Der Mac-Weg rechnet die korrigierte Hochrechnung schon **heute** selbst, aus den Monatszählern.

**Zahlen bisher (Monatszähler, nur Chirp):** 16.11.–17.11. 03:00 = 39,7 min ≈ 0,55 €. Hochgerechnet aus 2 Tagen ergibt das
**8,29 €/Monat** (alte Formel: 0,98 €). Davon sind 10,8 min Testläufe anderer Jobs in der Nacht am Büro-PC.
Ein Ordi-Nachmittag an CASWS10 kostete 28,3 min ≈ 0,39 € Chirp, die Live-Anzeige kommt etwa gleich viel dazu. Bei rund
21 Ordi-Tagen im Monat landet das deutlich über der 6-€-Grenze (Google-Gutschrift ~9 €). Die **Karte kommt deshalb
voraussichtlich ab Mi 18.11. 20:30 von selbst**, sobald 3 Tage gezählt sind.

**Kanban-Weg (Aufgabe 3):**
- `tools/mac/kaiscribe_chirp_warnung.py` (RaKScribe26): Er lädt den Leser auf die Automaten-VM und startet ihn als rakauto
  (`C:\RaK\tmp\n10_interaktiv.ps1`, wie `ks_kontrolle.ps1`). Zurück kommen nur Zähler.
- Warnung, wenn eine dieser Bedingungen gilt: Die EXE hat die Zeile `WARNUNG` im Tagesbericht, `warnung_<JJJJ-MM>.txt` ist da,
  oder die eigene Hochrechnung liegt über 6 € (mindestens 3 Tage).
- Dann **genau eine** Karte je Monat, Spalte peter: „KaiScribe: Google-Spracherkennung hochgerechnet X €/Monat (JJJJ-MM, > 6 €)“
  mit a) so lassen, b) Budget/Gutschrift prüfen, c) billiger machen (Folgejob). Doppelte Karten verhindern zwei Dinge: der
  Zustand `~/.hermes/work/kaiscribe-chirp/zustand.json` und eine Titelsuche in der Kartei.
- Dazu je Rechner der letzte Lauf (Modell/Version) im Zustand und die Karte „neu starten“ (Abschnitt 1).
- Keine Google-Quota-Änderung, keine Meldung, still bei Erfolg, Fehler mit Exit 1 an den Cron-Doktor.
- **Cron:** Server-Job `668f3092f79c` „KaiScribe Chirp-Warnung → Kanban (täglich)“, `30 20 * * *`, no_agent, Zustellung local.
  Er läuft über den Werkbank-Stummel `werkbank/mac__kaiscribe_chirp_warnung.sh` mit dem Mac-Skript
  `~/.hermes/scripts/kaiscribe_chirp_warnung.py`. Das Skript holt den Code aus origin/main von RaKScribe26 und ris-mods
  (`vmssh.py`); freigegeben ist es in `fleet/werkbank/lauf_erlaubt.txt`. Der Mac hat keinen eigenen Scheduler mehr.
  Erster Lauf ist heute 20:30.
- Ganze Kette vom Server aus geprüft (17.11. 04:15): 17 s, Exit 0, still. Probe ohne Karte:
  `KCW_TROCKEN=1 python3 ~/.hermes/scripts/kaiscribe_chirp_warnung.py`.

## Tests

`tests/offline/test_chirp_warnung.py` (neu, auch in `test.yml`), `test_nutzung.py` (Zählstart Mitte Monat, Mindesttage,
Live-Sekunden), `test_capture.py` (Streaming-Sekunden), dazu `test_exe_ablauf`, `test_import`, `test_pipeline_exe`,
`test_toter_code`, `test_llm_anbieter`, `test_buero_anthropic`, `test_config`: alle grün.

## Kosten

Anthropic 0 $, Google 0 $. Es gab nur Lesezugriffe über die Automaten-VM, nichts in CAS und nichts am Büro-PC.
