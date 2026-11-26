# BERICHT kaiscribe-lektor-einbau-n1: Lektor in KaiScribe eingebaut, Schalter AUS (Do 26.11.2026)

Peter hat am 26.11.2026 „Go: a“ gegeben (Kanban #531). Der Lektor ist jetzt in **KaiScribe 3.32.0** eingebaut.
Scharf geschaltet ist er **nicht**: Der Schalter ist standardmäßig aus, und die Kostenbedingung ist noch nicht belegt
(siehe 4). Gebaut und getestet wurde am Hetzner-Server; an Ordi, CAS und Büro-PC wurde nichts verändert. Der Bericht
enthält keine Patientendaten.

## Kurz
- **Einbau:** nach „Hermi formt“ (KaiScribe-Befund-KI), vor EOL/CAS; nur kp + rg; im Hintergrund; nur über den Wächter;
  Arzt-Stellen bleiben unberührt; Prüfzeilen als rote Prüfzeile wie bisher, nie im Befund (also nie in CAS/marc/ELGA).
- **Modell/Prompt:** Opus 5.5 medium, Prompt `lektor-2`, Arzt-Filter im Code, nur Nicht-Normal-/Nicht-Bausteinbefunde.
  Das ist die Empfehlung aus Messlauf n2 §5 (lektor-3 macht Opus zu leise). Bezahlt über den KaiScribe-Schlüssel
  (Konto A), maskiert wie der KaiScribe-Weg.
- **Probe am eingebauten Weg** (64 maskierte Paare aus n1, Testschlüssel Konto B, **0,78 $**): 54 Aufrufe, 0 Ausfälle,
  **1,31 ct je Aufruf → ≈ 33 $/Monat** bei 3.000 Befunden. 15 Korrekturen übernommen (6 davon hat der Arzt genauso
  gemacht), 4 vom Wächter verworfen (darunter „Zelle“ → „Galle“), 4 auf Arzt-Stellen nicht angewandt; 10 Prüfzeilen
  nach Filter, p50 4,9 s / p90 10,2 s.
- **Schalter-Stand: AUS.** Im Betrieb lief am 26.11. noch KaiScribe 3.28.2 (ohne Kosten-Fix, Token-Zähler alle 0).
  Den Beleg „`cache_ohne = 0` und ≤ 2 ct je Aufruf“ gibt es also noch nicht, und die Konto-A-Summe ist offen.
- **Release:** 3.32.0 ist gebaut. In die Ordi kommt es erst nach dem echten Lauf an 451898 (Folgejob, sonst Rollback).

## 1. Was eingebaut ist
| Teil | Datei |
|---|---|
| Lektor: Prompt lektor-2 (wortgleich ris-mods SYSTEM_2), Aufruf, Antwort-Leser, Schalter, Deckel, Normal-/Bausteinprüfung, Einarbeiten | `source_code/lektor.py` |
| Wächter (Pflicht), wortgleich zu ris-mods `kaiscribe_lektor/waechter.py` (Test prüft die Gleichheit) | `source_code/lektor_waechter.py` |
| Start nach dem Befund, Einarbeiten im Fenster, EOL-Regel, Abbruch | `source_code/RaKScribe.py` (`_lektor_*`) |
| Kostenzählung Rolle `lektor` | `source_code/nutzung.py`, `tools/vm/kaiscribe_nutzung_lesen.py` |
| Schalter-Pfad `LEKTOR_DATEI` | `source_code/config.py` |
| Regel-Register-Eintrag `lektor-schalter-aus` (Pflicht) | `tests/regel_register/regeln.json` |

**Ablauf im Betrieb (nur mit Schalter):**
1. Steht ein vollständiger Befund rechts und gibt es einen CAS-Auftrag mit Befunder kp oder rg (Schalter dort an),
   startet EIN Aufruf im Hintergrund. Ausnahmen ohne Aufruf: reine Normal-/Bausteinbefunde (Zähler `normal`) oder
   Monatsdeckel erreicht (Zähler `deckel`).
2. Die Antwort wird erst eingearbeitet, wenn gerade nichts aufgenommen, verarbeitet oder eingefügt wird. Sie wird auf
   den **jetzigen** Feldtext angewandt: Zeichen-Diff Lektor-Eingabe ↔ jetzt. Eine Korrektur kommt nur dort hinein, wo
   der Text samt Nachbarzeichen noch genau so steht. Was der Arzt geändert hat, bleibt unberührt.
3. Jede Korrektur geht durch den Wächter: Seite, Zahl, Verneinung, Normal-Aussage, Graduierung, Platzhalter, Überschrift,
   neue Inhaltswörter, Regel-Register-Wortlaute (gebündelte `regeln.json`) und Vorlagensätze sind tabu. Neu dazu
   (n2 §5): Ein Wortwechsel mit anderem Anfangsbuchstaben gilt nicht als Hörfehler („Zelle“ → „Galle“ wird verworfen).
4. Prüfzeilen werden in die bestehende Hinweiszeile übernommen, rot, im bisherigen Format
   `„<Zitat>“: <Hinweis> (Lektor) – bitte prüfen`, höchstens 5. Sie fallen weg, wenn das Zitat nicht mehr unverändert
   dasteht (Arzt-Filter aus n2). Ebenso fallen „nicht diktiert“-Zeilen auf einem K&L-Grad oder einem Register-Wortlaut weg
   (Hausregel, n2-Fehlalarm P52).
5. Kurzhinweis „Lektor: n Korrektur(en) übernommen · m Prüfzeile(n) – Strg+Z = zurück“. Strg+Z holt den Stand vor dem
   Lektor zurück.
6. **EOL:** Hat der Lektor vor weniger als 3 s korrigiert, braucht es ein zweites EOL (wie bei IB Lab: nie Ungesehenes
   senden). Läuft er noch, wird er abgebrochen und der Befund geht unverändert. Eine spätere Antwort wird verworfen
   (Zähler `zu_spaet`).
7. **Ausfall** (Netz, HTTP, Frist 90 s, Maske unsicher, unlesbare oder abgebrochene Antwort): Der Befund bleibt
   unverändert. Es gibt keinen zweiten Versuch, kein anderes Modell und kein Gemini (Zähler `ausfall`).
8. Im Protokoll stehen nur Zahlen: gestartet, fertig nach x s, Korrekturen/übernommen/Wächter/Arzt-Stelle, Prüfzeilen.

**Schalter:** `X:\KaiScribe\Daten\lektor.json`, z. B. `{"befunder": {"kp": false, "rg": false}, "monatsdeckel_usd": 40}`.
- Fehlt die Datei, ist sie kaputt oder fehlt X:, ist der Lektor aus. Es gelten nur kp und rg (im Code festgelegt).
- Die Datei wird alle 30 s gelesen. Notaus = `false` setzen, ohne Neustart.
- Monatsdeckel: die Lektor-$ des Monats über alle PCs. Standard 40 $.
- Für den Testlauf kann eine Gast-Kopie per `LEKTOR_DATEI` in ihrer config.ini auf eine eigene Datei zeigen. Der
  Schalter der Ordi bleibt dabei unberührt.

**Kosten:** Der Lektor wird getrennt gezählt (`td["lektor"]`). Die KaiScribe-Zahlen (Aufrufe, $, Cache, ct je Aufruf)
bleiben damit unverfälscht, das ist wichtig für die Kostenbedingung.
- Tagesbericht: neue Zeile „Lektor heute: Aufrufe …, Korrekturen übernommen … (in … Befunden), Prüfzeilen …, ausgefallen
  …, zu spät …, Deckel …, x $ (≈ y ct je Aufruf); Monat: …“.
- `kaiscribe_nutzung_lesen.py`: neue Zeile `LEKTOR <monat> <PC> <tag> aufrufe= usd= uebernommen= …`. Die
  `NUTZUNG`-Zeile ist unverändert.
- Opus-Preis in `llm_anbieter.PREISE` (4 / 0,40 / 20 $ je Mio Token, Cache-Schreiben 1 h = 2 × Input).

## 2. Tests
- Neu: `tests/offline/test_lektor.py`, 64 Prüfungen grün. Geprüft werden:
  - Schalter: fehlt = aus, nur kp/rg, Neulesen, Deckel
  - Body: Opus, medium, Cache, kein temperature
  - Maske: Datum geht als Platzhalter hinaus
  - Ausfall: HTTP 529 ohne zweiten Versuch, abgebrochene Antwort
  - Wächter: Rechtschreibung ja; Verneinung, Seite, Überschrift, Register- und Vorlagensatz, Zelle → Galle nein
  - Arzt-Stellen bei Korrekturen und Prüfzeilen
  - Positionen nach einem Arzt-Einschub, Hausregel-Filter, Normal-/Bausteinbefund
  - Lauf im Hintergrund, EOL vorher, Ausfall
  - Zähler getrennt, Tagesbericht, Leser-Zeile
  - Einbau-Stellen in der EXE und im Build (gebündelte Dateien)
- Alle 73 Python-Gates aus `test.yml` und `pipeline_test.mjs` sind am Hetzner grün. Das gilt auch für den
  **Regel-Register-Test**: 390 Prüfwörter, keine Regel entfernt, neue Pflicht-Regel `lektor-schalter-aus`.
- GitHub für 3.32.0: siehe Nachtrag CI.
- Werkzeug-Probe: `tools/lektor_probe.py` (Konto B, eingebauter Weg, maskierte Paare). Ergebnis oben.
- Abnahme-Werkzeug für den Büro-PC: `tools/buero/lektor_abnahme.py`. Fälle:
  - L0: Schalter aus = unverändert
  - L1: Schalter an = Korrektur/rote Zeile, nie im Brief
  - LS: EOL vor dem Lektor = Befund unverändert

  Es schreibt eine eigene Schalter-Datei und setzt die Kopie danach wieder auf `aus`. Gelaufen ist es noch nicht, das
  macht Teil 2.

## 3. Abweichungen vom Brief (bewusst)
- **Prompt lektor-2 statt lektor-3:** So empfiehlt es n2 §5 ausdrücklich. Die Arzt-Markierung im Prompt ist im Einbau
  ohnehin leer: Der Lektor bekommt die KaiScribe-Fassung, bevor der Arzt etwas ändert. Der Arzt-Filter sitzt deshalb im
  Code beim Einarbeiten.
- **Abnahme an 451898 nicht in diesem Lauf:** Sie folgt als Teil 2 (`FOLGEJOB-KAISCRIBE-LEKTOR-EINBAU-N1-EINSPIELEN.md`)
  nach dem schon wartenden 3.31.0-Einspielen, damit nur einmal getauscht wird. Bis dahin ist 3.32.0 nur gebaut und nicht
  in der Ordi. Fällt die Abnahme rot aus, wird nicht getauscht bzw. zurückgerollt.
- **Ausfall-Fall an 451898 = „EOL vor der Antwort“ (LS).** Einen echten HTTP-Ausfall kann man an der Kopie ohne Eingriff
  nicht erzwingen. Er ist offline geprüft.

## 4. Scharf schalten – Stand der beiden Bedingungen
| Bedingung | Stand 26.11.2026 | erfüllt? |
|---|---|---|
| (a) Betrieb nach dem Kosten-Fix: `cache_ohne = 0`, ≤ 2 ct je KaiScribe-Aufruf | Lauf-Dateien bis 26.11. zeigen im Betrieb **3.28.2** (CASWS10, 10:52); Token-/Cache-Zähler alle 0. 3.29.2+ ist noch nicht in der Ordi, also gibt es keinen Beleg. Nachtrag „Betrieb nach dem Fix“ fehlt. Nov. bisher: 179 Claude-Aufrufe, ≈ 5,3–6,7 ct je Aufruf (vor dem Fix) | **nein (offen)** |
| (b) KaiScribe + Lektor + übrige Konto-A-API ≤ 170 $ bei 3.000 Befunden | KaiScribe nach Fix ≈ 1,4 ct → ≈ 42 $ (Probe 25.11., kein Betriebswert), Lektor ≈ 33 $ (Probe heute), KaiFormat/Ordimail/Überweisungen/Senf-API: keine Nutzungsdaten gefunden | **offen** |

→ **Schalter bleibt aus.** Die Prüfung macht `FOLGEJOB-KAISCRIBE-LEKTOR-SCHARF-N1.md` am ersten Ordi-Tag nach dem Tausch.
Ab 3.29.2 gibt es dafür die Token-Zähler, ab 3.32.0 die LEKTOR-Zeilen. Kanban #531 hat eine Notiz mit diesen Zahlen
bekommen.

## 5. Dateien
- Repo: siehe 1. Dazu kommen `tools/lektor_probe.py`, `tools/buero/lektor_abnahme.py`, die beiden FOLGEJOB-Dateien und
  der Build (`--hidden-import=lektor/lektor_waechter`, `--add-data regeln.json`).
- Hetzner `~/cj/work/kaiscribe-lektor-einbau-n1/`:
  - `probe_lauf.jsonl`: Rohantworten der Probe, maskiert
  - `nutzung_2611.txt`: Zählerauszug X:, nur Zahlen
  - `tests.sh`, `version.sh`
- Kostenbuch: `~/cj/work/testkosten/kaiscribe-lektor-einbau-n1.jsonl` (0,84 $ inkl. Probeaufrufe, Konto B).

## Offen
- Teil 2: Abnahme an 451898 (L0/L1/LS), dann Tausch auf 3.32.0 und Schalter-Datei ausdrücklich `false` anlegen.
- Scharf-Entscheid: Beleg (a) aus dem Betrieb und Konto-A-Summe (b), vor allem die Zahlen der übrigen Konto-A-Dienste.
- Die 451898-Abnahme zeigt nur, dass der Weg funktioniert. Ob die Prüfzeilen im Alltag nützen, zeigen erst die Live-Zähler.

## Abschluss
Version 3.32.0: Der Lektor ist eingebaut, aber **ausgeschaltet**. In der Ordi ist er noch nicht, das kommt nach dem Test an 451898.
Warum aus: In der Ordi läuft noch die alte KaiScribe-Version ohne Kosten-Fix. Darum gibt es noch keinen echten Beleg für ≤ 2 ct je Befund, und die Summe für Konto A ist offen.
Probe heute: 1,3 ct je Lektor-Aufruf, also etwa 33 $ im Monat bei 3.000 Befunden. Kein Ausfall, falsche Wörter wie „Zelle → Galle“ blockt der Wächter.
Live-Zahlen gibt es noch keine. Das Scharfschalten prüft ein eigener Auftrag am ersten Ordi-Tag nach dem Tausch.
