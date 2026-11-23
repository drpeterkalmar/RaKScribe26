# Kontrolle kaiscribe-frog-einsetzen-n1-kontrolle-f1 – erster auffälliger FROG im Betrieb (Mo 23.11.2026, ~16:20, Hetzner)

**Ergebnis: belegt, kein Fehler.** Heute gab es **3 echte auffällige FROG-Fälle** (`ablage=FROG:patho`). Alle 3 haben den
IB-Lab-Text im Befund: `urteil=OK`, FROG-Satz da, Schlusssatz da, je 3 Zeilen. Einer davon lief an **CASWS08**.
**0 auffällige Fälle ohne Text.** `rakscribe.log` schreibt (neuer Ort, siehe 4.). Kein Folgejob, keine Karte.

Ich habe nur gelesen (X: auf der Automaten-VM, Konto rakauto, über `tools/vm/x_lauf_hetzner.py`). Kein C-MOVE/C-STORE, keine
CAS-Datenbank, keine DICOM-Header. Die Ausgaben enthalten nur Zähler und Kategorien.

## 1. Stand
- 3.19.15 war seit 20.11. eingespielt. Danach kamen neuere Fassungen (3.20.x am 21.11., heute **3.22.4**). Den FROG-Fix aus
  3.19.15 enthalten sie weiter.
- **Neuer Datenordner:** Die Lauf-Dateien liegen jetzt in `X:\KaiScribe\Daten` (119 Läufe seit 20.11., der neueste heute
  14:26). Der alte Ordner `X:\RaKScribe\Daten` ist noch da, wird aber nicht mehr beschrieben. Mit dem alten Standardpfad
  meldete das Werkzeug `n=0`.
- FROG-Bausteine, die seit 20.11. 15:00 in der Ablage `X:\IBL-Vorbefunde` geschrieben wurden: 9.

## 2. `ibl_laeufe_pruefen.py --von 20261120 --module FROG --ordner X:\KaiScribe\Daten`
`IBL_LAEUFE n=12 ok=10 leer=0 normal=2`

| Zeit | PC | KaiScribe | Brücke | Module | Zeilen | FROG-Satz | Schluss | Ablage FROG | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| 20.11. 00:04–14:40 | (4 Läufe, am 20.11. bewertet) | 3.19.15 | | | | | | | 2× OK, 2× NORMAL |
| 21.11. 01:58–10:57 | CASWS14 | 3.20.1/3.20.5 | ?/2.5.27 | FROG (5 Läufe) | 3–4 | 4× ja | ja | ? | OK |
| **23.11. 10:09** | CASWS10 | 3.22.4 | 2.5.27 | FROG links | 3 | ja | ja | **patho** | **OK** |
| **23.11. 10:10** | CASWS10 | 3.22.4 | 2.5.27 | FROG links | 3 | ja | ja | **patho** | **OK** |
| **23.11. 14:22** | CASWS08 | 3.22.4 | 2.5.27 | FROG beidseits | 3 | ja | ja | **patho** | **OK** |

- 21.11. an CASWS14: Das ist der Test-/Abnahme-PC. Die Ablage war dort `?`, weil zu diesen Läufen kein Baustein mehr in
  der Ablage liegt (Testbausteine). Alle 5 Läufe haben `urteil=OK`. Sie zählen nicht als Betriebsfälle.
- 10:09 und 10:10 sind zwei Läufe kurz hintereinander am selben PC. Das kann derselbe Fall zweimal diktiert sein. Beide
  sind korrekt.
- CASWS08 hat inzwischen die Brücke 2.5.27, nicht mehr 2.5.15. Den Sonderweg für alte Brücken (Nachladen aus der Ablage)
  belegt dieser Fall also nicht. An CASWS08 wird er auch nicht mehr gebraucht. In den geprüften Läufen hatten CASWS08 und
  CASWS10 beide die Brücke 2.5.27.

## 3. Bewertung
Nach dem Brief gilt: `urteil=OK` + `frog_satz=ja` + `schluss=ja` bei `ablage=FROG:patho` → **Fall belegt**. Das trifft auf
alle 3 auffälligen Fälle zu. Es gibt keinen `LEER` mit Pathologie, darum keine Diagnose und kein `kaiscribe-frog-einsetzen-n2`.

## 4. rakscribe.log
- Das Log liegt jetzt in **`X:\KaiScribe\Programm\rakscribe.log`**: 414 917 Byte, zuletzt geändert **23.11. 16:16:23**. Es
  schreibt also.
- `X:\RaKScribe\rakscribe.log` (319 889 Byte, 21.11. 05:02) ist der alte Ort und steht seit dem Umzug still. Das ist so
  gewollt.
- Das alte 1-MB-Log vom 19.11. (`.1`) liegt jetzt als `X:\KaiScribe\_alt\rakscribe.log.1.20261121-084937`. Das Programm hat
  noch nicht rotiert (Log < 1 MB).

## 5. Werkzeug-Änderung (Repo)
- `tools/vm/ibl_laeufe_pruefen.py` (`--ordner`) und `tools/vm/ibl_frog_diag.py` zeigen jetzt standardmäßig auf
  `X:\KaiScribe\Daten` statt auf `X:\RaKScribe\Daten`.
- Lese-Hilfen dieser Kontrolle (`kf_stand.py`, `kf_log.py`: nur Anzahl, Größe, Zeit) liegen unter
  `~/cj/work/kaiscribe-frog-einsetzen-n1-kontrolle-f1/` (Hetzner) und in `C:\RaK\einrichtung\frogdiag\` auf der VM.

## 6. Weiter
Nichts. Die FROG-Kontrollkette ist abgeschlossen, kein `-f2`. Für Peter ist nichts zu tun.

Abschluss: FROG im echten Betrieb belegt: 3 auffällige Fuß-Befunde (2× CASWS10, 1× CASWS08) mit IB-Lab-Text, 0 leer.
`rakscribe.log` schreibt am neuen Ort `X:\KaiScribe\Programm`.
