# Bericht kaiscribe-lektor-scharf-n1: noch kein Kostenbeleg, Schalter bleibt aus

Stand Fr 27.11.2026 14:05 (nach Ordi-Schluss 13:30). Nur gelesen, nichts geschaltet.

## 1. Kosten im Betrieb – kein Beleg möglich
`tools/vm/kaiscribe_nutzung_lesen.py` (Fassung mit LEKTOR-Zeilen) per scp auf die VM,
`x_lauf_hetzner.py … --tage 2026-11-26,2026-11-27`:
- LAUF-Zeilen 27.11. nur CASWS14 (Büro-PC 451898) 00:03–00:14 (3.31.0, 4 Läufe) und 00:48–00:50 (3.32.0, 3 Läufe) =
  die Nachttests/Abnahme. **Kein einziger Tageslauf in der Ordi** am 27.11.; keine NUTZUNG-Zeile für den 27.11.,
  `TAGESBERICHT 2026-11-27 fehlt`, keine LEKTOR-Zeilen.
- Letzter Betriebswert: 26.11. CASWS10, 3.28.2, 3 Aufrufe 0,2004 $ = 6,7 ct/Aufruf (ohne Cache, Token-Zähler 0).
- Alle Token-Zähler (`tok_*`, `cache_*`) im Monat 0 → Bedingung (a) `cache_ohne=0`, ≤ 2 ct je Aufruf **nicht belegbar**.
- Monat 11/2026 bisher: 182 Claude-Aufrufe, 9,77 $ Anthropic (KaiScribe, meist 3.28.2 ohne Cache).

## 2. Konto-A-Rechnung (b) – offen
Ohne Betriebszahlen mit Cache keine Hochrechnung; Schätzung aus dem Einbau-Bericht unverändert (KaiScribe ≈ 42 $,
Lektor ≈ 33 $, übrige Dienste ohne Zahlen). Wird im Folgelauf mit echten Zahlen gerechnet.

## 3. Entscheidung: aus lassen
- (a) nicht belegt, (b) offen → `X:\KaiScribe\Daten\lektor.json` nicht angelegt (fehlt = aus). Live läuft ohnehin
  3.31.0, die die Datei gar nicht liest; 3.32.0 ist nicht auf X: (Tausch 27.11. 01:12 an der Wächter-Sperre gescheitert).
- Der Tausch-Folgejob `FOLGEJOB-KAISCRIBE-LEKTOR-EINSPIELEN-TAUSCH-N2.md` war **nicht eingereiht** → jetzt eingereiht
  als `kaiscribe-lektor-einspielen-tausch-n2` (not-before Fr 27.11. 20:00, Ressourcen ordi + automaten-vm).
- Dieser Auftrag neu eingereiht als `kaiscribe-lektor-scharf-n2` (not-before Mo 30.11. 17:30, nach dem Tausch-Job).
- Kanban #531: Notiz mit den Zahlen (bleibt „wartet“, Frist 02.12.).

## Abschluss
Der Lektor bleibt aus. Heute (Fr 27.11.) wurde KaiScribe in der Ordi nicht benutzt – es gibt nur die Nachttests am Büro-PC, also noch keine echten Kostenzahlen mit dem neuen Spar-Speicher (letzter Wert: 6,7 ct je Befund mit der alten Version 3.28.2).
In der Ordi läuft weiter 3.31.0; 3.32.0 mit Lektor ist noch nicht eingespielt.
Der Austausch auf 3.32.0 ist für heute ab 20:00 eingeplant, die Kostenprüfung mit Entscheid für Mo 30.11. ab 17:30.
