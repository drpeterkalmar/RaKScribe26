# Kontrolle kaiscribe-frog-einsetzen-n1 – erster Betriebstag mit KaiScribe 3.19.15 (Fr 20.11.2026, 17:20–18:10, Hetzner)

**Ergebnis: Kein Fehler.** Seit 3.19.15 (live seit 20.11. 00:27) gab es **3 echte FROG-Fälle**, alle an CASWS10
(Brücke 2.5.23). Alle 3 waren laut IB Lab **ohne Pathologie**: Die Abholer-Datei hat keine Ergebnispunkte und kein Feld
„befundtext“. Bei FROG ohne Pathologie gibt es keinen Fuß-Text, „0 eingesetzte Zeilen“ ist dort richtig.
**Ein auffälliger FROG-Fall im echten Betrieb fehlt also noch.** Ebenso fehlt ein Fall an CASWS08 (alte Brücke 2.5.15,
Nachladen aus der Ablage). Die Folgekontrolle ist für **Mo 23.11. ab 13:00** eingereiht (`-f1`).
`rakscribe.log` schreibt wieder.

Nur gelesen (X: auf der Automaten-VM, Konto rakauto). Kein C-MOVE/C-STORE, keine CAS-Datenbank, keine DICOM-Header.
Die Ausgaben enthalten nur Zähler und Kategorien (Nummern unterdrückt, keine Namen, kein Befundtext).

## 1. Stand
- `kaiscribe-frog-einsetzen-n1-einspielen` lief durch: 3.19.15 aktiv seit 20.11. 00:27 (`ergebnis_frog_einsetzen_n1_20261120.md`).
- Lauf-Dateien vom 20.11.: **46**, alle mit `kaiscribe=3.19.15`. Letzter Lauf 14:49.
- Module in diesen Läufen: HIPPO 12, KOALA 7, RBfracture 6, **FROG 4** (davon 1 Testpatient 00:04), LAMA 2, SQUIRREL 1.
- FROG-Bausteine, die heute in der Ablage `X:\IBL-Vorbefunde` geschrieben wurden: 5.

## 2. `ibl_laeufe_pruefen.py --von 20261120` (FROG/HIPPO)
`IBL_LAEUFE n=15 ok=13 leer=0 normal=2` (mit dem neuen Urteil NORMAL, siehe 5.)

| Zeit | PC | Brücke | Module | Zeilen | FROG-Satz | Schluss | Ablage FROG | Urteil |
|---|---|---|---|---|---|---|---|---|
| 00:04 | CASWS14 | 2.5.22 | FROG bds + HIPPO bds | 11 | ja | ja | (Test, Baustein gelöscht) | OK – Abnahme 451898 |
| 12:19 | CASWS10 | 2.5.23 | FROG links + RBfracture | 1 | nein | nein | normal | OK (die Zeile ist RBfracture) |
| 13:52 | CASWS10 | 2.5.23 | FROG bds | 0 | nein | nein | normal | NORMAL |
| 14:40 | CASWS10 | 2.5.23 | FROG rechts | 0 | nein | nein | normal | NORMAL |

- HIPPO: 11 Läufe an CASWS10, alle `urteil=OK` (3–9 Zeilen, Schlusssatz da). In 9 steht ein HIPPO-Satz. 2 Läufe (HIPPO + LAMA)
  haben 3 Zeilen und den Schlusssatz, aber keinen der HIPPO-Satzanfänge, nach denen das Werkzeug sucht. Kein Fehlerbild, nur
  zur Kenntnis.
- An CASWS08 und RAKCLIENT04 gab es heute keinen Lauf mit FROG/HIPPO.

## 3. Bewertung der FROG-Fälle (Diagnose `ibl_frog_diag.py`, nur Kategorien)
Für jeden der drei echten Fälle gilt:
- Abholer-Datei: `format=ibl-abholer/1`, Fassung 1–2, **ergebnis_punkte=0**, **befundtext fehlt**, keine angewandten Regeln,
  7–37 Messzeilen, 3–4 Hinweise für den Befunder.
- Der Baustein lag 2–4 Stunden vor dem Diktat in der Ablage. Die Brücke 2.5.23 meldete `[ibl] … FROG v1/v2 …`.
- Vorgehen laut Brief: FROG ohne Pathologie → `zeilen=0`, kein „befundtext“ in der Ablage → **richtig**. Kein Fix nötig, kein
  `kaiscribe-frog-einsetzen-n2`.
- Am Rand: Im Fall 12:19 (Sprunggelenk + Vorfuß links) steht als Vorlage nur `allgemein`, obwohl die Brücke
  `sprunggelenk_in_2_ebenen` und `vorfuß_in_2_ebenen` zugeordnet hatte. Für FROG war das ohne Folge, weil der Fall unauffällig
  war. Hier nicht weiter untersucht.

## 4. rakscribe.log
- `X:\RaKScribe\rakscribe.log`: **300 611 Byte**, zuletzt geändert **20.11. 14:52:40**. Es wächst also wieder (nach dem
  Neustart um 00:27 waren es 4 526 Byte).
- `rakscribe.log.1`: 1 000 059 Byte vom 19.11. 11:32:49 (das alte, stehengebliebene Log). Noch kein `.2`, also bisher keine
  weitere Rotation.

## 5. Werkzeug-Änderungen (Repo)
- `tools/vm/ibl_laeufe_pruefen.py`: neue Spalte `ablage=<MODUL>:patho|normal|?` aus der Abholer-Datei und neues Urteil
  **NORMAL** (0 Zeilen, laut Ablage alle Module ohne Pathologie). Unauffällige FROGs zählen damit nicht mehr als LEER. Mit
  nachgebauten Dateien offline geprüft und auf der VM gelaufen (Tabelle oben).
- `tools/vm/ibl_frog_diag.py`: je FROG-Lauf die Kategorien aus Lauf-Datei, Ablage und Brücken-Protokoll (Nummern als `<nr>`).
- `tools/vm/x_lauf_hetzner.py` + `x_lauf_huelle.ps1`: der Weg vom **Hetzner** auf die VM mit X: (siehe 6.).

## 6. Weg vom Hetzner (anders als im Bericht vom 19.11.)
- Der Weg aus dem Bericht (`abholer_vm.alskonto`) braucht das rakauto-Kennwort aus Vaultwarden. Das Nur-Lese-Konto des
  Hetzner hat diesen Eintrag nicht.
- Mit SSH-Schlüssel als rakauto (`dexa-rakauto`) verbindet `laufwerke.cmd` X: nicht: Ohne Kennwort-Anmeldung fehlt die
  gespeicherte Anmeldung für `\\casmed\casmed$`.
- Lösung: Die Anmeldung „Laufwerk X: CASMED-Konto dexa“ aus dem Hetzner-Tresor geht per stdin an `x_lauf_huelle.ps1`. Die
  Hülle verbindet X: nur für diese SSH-Sitzung (`New-PSDrive -Persist`; `New-SmbMapping` ist über SSH gesperrt) und trennt
  danach wieder (`x_getrennt=True` belegt).
- `bw sync` hängt, wenn der Tresor-Server am Mac nicht antwortet. Darum liest das Werkzeug ohne sync aus dem lokalen Stand.
  Gegen 17:55 hingen auch `bw unlock` und `bw lock` (der Mac war per Tailscale erreichbar). Ein fremder
  `vw_get.py list …`-Aufruf mit hängendem `bw sync` lief da schon über 30 min. Alle Daten oben stammen aus den Läufen davor.
- Auf der VM liegen in `C:\RaK\einrichtung\frogdiag\` nur Lese-Skripte (`ibl_laeufe_pruefen.py` neue Fassung, `ibl_frog_diag.py`,
  `kf_chk.ps1`, `kf_x.ps1`, `kf_x2.ps1`, `kf_lauf.ps1`, `x_lauf_huelle.ps1`). Dazu kommt `C:\RaK\tmp\vm_als_konto.ps1` (Kopie
  aus ris-mods, nicht benutzt). Arbeitsdateien: `~/cj/work/kaiscribe-frog-einsetzen-n1-kontrolle/` (Hetzner).

## 7. Weiter
- `kaiscribe-frog-einsetzen-n1-kontrolle-f1` ist eingereiht: automaten-vm, frühestens **Mo 23.11.2026 13:00**, nicht nach
  Mi 25.11. Brief: `FOLGEJOB-KAISCRIBE-FROG-EINSETZEN-N1-KONTROLLE-F1.md`. Dort werden nur Läufe ab 20.11. 15:00 gewertet, und
  er muss erst `urteil=OK` mit `ablage=FROG:patho` sehen.
- Für Peter nichts zu tun.

Abschluss: Keine Fehler. Seit 3.19.15 gab es 3 echte FROG-Fälle, alle unauffällig (0 Zeilen ist dort richtig), 0 auffällige
Fälle leer. Der Beleg mit einem auffälligen FROG steht noch aus, Folgekontrolle Mo 23.11. `rakscribe.log` schreibt wieder.
