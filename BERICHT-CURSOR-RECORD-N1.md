# kaiscribe-cursor-record-n1 – Ergänzung per Record wörtlich an der Cursor-Stelle (13.11.2026)

**Für Peter:** Ergänzungen ins rechte Fenster gehen jetzt direkt: In den fertigen Befund klicken (oder etwas markieren),
Record drücken, diktieren, INS. Der Text kommt wörtlich an diese Stelle bzw. ersetzt die Markierung, „Nur Text“ brauchst
du dafür nicht. Technisch ging das schon seit 3.5.0, man hat es nur nicht gesehen. Im Protokoll vom 12.11. sieht man,
dass du vorher „Nur Text“ eingeschaltet und danach wieder ausgeschaltet hast. Deshalb zeigt die Statuszeile ab 3.18.9 in
jedem Schritt „Ergänzung an Cursor-Stelle“ (Aufnahme, Pause, Einfügen) und danach „Ergänzung an Cursor-Stelle eingefügt“.
Ohne Cursor im Befund bleibt alles wie bisher, und EOL schickt wie immer den sichtbaren Befund weiter. 3.18.9 liegt seit
13.11. 02:32 auf X:, und der Büro-PC läuft damit. CASWS08 und CASWS10 holen es beim nächsten KaiScribe-Start. Der Beleg
dort und der kurze Echttest am Testpatienten stehen noch aus (Karte #252).

## Befund vor der Änderung
- Ordi-Protokoll (`X:\RaKScribe\rakscribe.log`, 12.11.): 09:36:32 „Nur Text an“ → 09:36:35 Record mit
  `[EINFÜGEN] … an Stelle (415, 415)` → weitere Ergänzung mit Markierung (09:38) und Klick in der Pause (09:39) → EOL an CAS.
  Danach, beim nächsten Auftrag, lieferte das noch eingeschaltete „Nur Text“ (09:44) keinen Befund. Erst ausschalten (09:45:07)
  und dann „Befund aus Text“ halfen.
- Code: `_einfuege_ziel_ermitteln` und der Einfüge-Zweig in `process_dictation` hängen nicht von „Nur Text“ ab. Gefehlt hat
  nur eine sichtbare Rückmeldung. Die alte Meldung „Diktat wird an der Cursor-Stelle eingefügt“ stand nur während der
  Aufnahme da, und die Pause- bzw. Verarbeitungs-Anzeige hat sie überschrieben.

## Umsetzung (RaKScribe26, Release 3.18.9)
- `RaKScribe.py`: `ERGAENZUNG`/`ERGAENZUNG_STATUS`. `update_status` zeigt bei gemerktem Einfüge-Ziel
  „Ergänzung an Cursor-Stelle · Aufnahme läuft“, „· Pause – Record: weiter · INS: einfügen“ bzw. „wird eingefügt…“.
  Nach dem Einfügen erscheint der Hinweis „Ergänzung an Cursor-Stelle eingefügt“. Das Ziel wird danach verbraucht (auch
  bei „kein Text“ oder Fehler), damit später keine falsche Anzeige stehen bleibt. Das Protokoll nennt den Nur-Text-Stand
  und die Zahl der eingefügten Zeichen (ohne Inhalt). Im Menü gibt es eine neue Hilfezeile.
- Web-App (`App.tsx`): Statustexte und Hilfezeile sind gleich. Die Einfüge-Regeln sind unverändert (`einfuegen.py` ≡ `einfuegen.ts`).
- Unverändert: Fensterziel/EOL, F10-Ablauf, Mammo-Maske, „Nur Text“-Knopf (gleiches Ergebnis beim Einfügen).

## Tests
- `tests/offline/test_einfuegen.py`: Record direkt (ohne Pause) mit Cursor im Befund bei „Nur Text“ aus, mit und ohne
  CAS-Band. Geprüft wird: wörtlich eingefügt, keine Befund-KI, Statuszeile in beiden Schritten, Hinweis danach, Nur Text
  bleibt aus, Cursor steht hinter der Ergänzung. Dazu Markierung ersetzen und ohne Cursor: normaler Befund ohne Ergänzungs-Anzeige.
- `tests/offline/test_speechmike_ablauf.py` 6c: echte Cursor-Ermittlung, Record → Pause → weiter → INS. Danach EOL: genau der
  sichtbare Befund, SpeechMagic-Fenster aktiviert, genau einmal Strg+V. Danach normales Diktat.
- `tests/offline/snapshots/einfuegen_faelle.txt`: 4 neue gemeinsame Fälle (Zeilenende vor dem Ergebnis, Abkürzung, markierter
  Messwert, leere Zeile am Ende). Python und Web (`pipeline_test.mjs` 65/65) sind grün.
- Alle Offline-Gates sind grün (Python-Dateien + 7 Web-Suiten), ebenso GitHub Tests, Build und Windows-UI-Test (fcf3f62).

## Verteilung
- Release 3.18.9: `rakscribe26.exe`, 56766990 Bytes, sha256 00610bc681ab…
- Büro-PC (CASWS14): A1 (02:23) hat die EXE geholt und den SHA geprüft, A2 (02:32) lief `kaiscribe_x_tauschen.ps1 -Schritt exe -Tag 3.18.9`
  mit KS_TAUSCH=ok. Titel „KaiScribe 3.18.9 - Röntgen am Kai“, keine Netzfehler. Die Sicherung liegt als
  `rakscribe26.exe.vor3.18.9-20261113-023244.alt` daneben (Rückweg: `-Schritt zurueck`).
- CASWS08 (zuletzt 12.11. 11:05) und CASWS10 (12.11. 17:37) liefen zuletzt mit 3.18.0. Sie bekommen 3.18.9 beim nächsten Start.
  Den Beleg liefert `X:\RaKScribe\Daten\protokolle\bruecke_<PC>.log`.
- Ordi-Aufträge: `~/cj/work/kaiscribe-cursor-record-n1/ordi/` (Hetzner).

## Offen
- Echttest am Testpatienten 451898 (nie vidieren) mit SpeechMike → Karte #252 für Peter. Nachts geht das nicht ohne Mensch am Mikrofon.
- Beleg „3.18.9 an CASWS08/CASWS10“ nach dem nächsten Start dort.
