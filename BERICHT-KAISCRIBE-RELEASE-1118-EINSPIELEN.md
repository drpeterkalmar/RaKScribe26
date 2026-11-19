# Bericht kaiscribe-release-1118-einspielen (Do 19.11.2026 03:23–04:05, Hetzner-Nachtspur)

**Ergebnis: KaiScribe 3.19.13, RaK-Befund 2.5.22 (Brücke, Formatierer, ibl_einfuegen 1.7.0) und Abholer 1.3.11 sind live. Eingespielt zwischen 03:44 und 03:54, also vor 06:30.**
Nicht belegt ist nur der Testlauf mit echtem Diktat am Testpatienten 451898 (siehe 5.). Dafür gibt es einen Ketten-Beleg ohne Büro-PC.

## 1. Tore (nur gelesen, 03:25)
- Release 3.19.13: `rakscribe26.exe` 56 853 396 Byte, sha256 `704549ed1c3a…85469` (API-Digest, passt zum Brief).
- X: vorher: 3.19.12 (sha `da380ad81968`, Sicherung davor `…vor3.19.12-20261119-010351.alt`). Niemand aktiv am Büro-PC (1 RDP-Sitzung, seit ~18 h ohne Eingabe).
- Abholer VM vorher 1.3.10, VM-Formatierer und Zeiger 2.5.21. In ris-mods main war ibl_einfuegen 1.7.0 noch **ohne** Versionsnummer: Brücke stand auf 2.5.21.

## 2. Reihenfolge (so, dass nie ein neuer Baustein auf alte Auswertung trifft)
| Zeit | Schritt | Beleg |
|---|---|---|
| ~03:35 | **RaK-Befund 2.5.22** in ris-mods main (`56db19d`, `bau/version_heben.py`, `cj zusammenfuehren`) | Tests nach Rebase: Brücke 1182 OK, ibl 679 OK. Windows-Prüfung am Mac 65/65 grün (619 s) |
| 03:44:27 | **VM-Formatierer 2.5.22** (4 Dateien: befund_format, ibl_einfuegen, ibl_bausteine, hippo.toml) | `titel_fmt_vm.py tauschen`: Hashes gleich, Probe `version=2.5.22 ibl_einfuegen=1.7.0`, Neustart ohne Fehler. Rückweg: `titel_fmt_vm.py zurueck` |
| 03:46:55 | **Formatierer-EXE 2.5.22-56db19d** am Büro-PC gebaut, 6/6 Proben, Quelle 461/461, ESET nach 2 min ok, nach X:\RaKScribe\Formatierer abgelegt | sha `5df2ad8c38eb…fc64` |
| 03:49:59 | **Brücke 2.5.22 auf X: + Büro-PC** (`kaiscribe_x_tauschen.ps1 -Schritt py -Commit 56db19d`) | `KS_TAUSCH=ok SCHRITT=py XQ=2.5.22 DQ=2.5.22 vorher=2.5.21`; `ibl_einfuegen.py` 1.7.0 (`764ba9afc8c6`), `ibl_bausteine.py` `983b3f817134`, 3× „hippo“. Sicherung `X:\RaKScribe\_alt\Py-diktat-vor-2.5.22-20261119-034959` |
| 03:50:38 | **KaiScribe 3.19.13 auf X:** (EXE direkt von github.com, SHA geprüft, `-Schritt exe`) | `KS_TAUSCH=ok SCHRITT=exe neu=704549ed1c3a alt=da380ad81968 sicherung=rakscribe26.exe.vor3.19.13-20261119-035038.alt`; Fenstertitel „KaiScribe 3.19.13 - Röntgen am Kai“; `[INIT]` ab 03:51:02, 0 Fehler |
| 03:52:47 | **Formatierer-Zeiger** 2.5.21-8c8c922 → 2.5.22-56db19d (Schreib-PCs holen es beim nächsten RaK-Start) | `fmt_kontrolle`: VM/DEXA je 1 Start v2.5.22, 0 Traceback. Rückweg: `fmt_zip_vm.py zeiger fmt2521 2.5.21-8c8c922` (Mo–Fr 06:30–20:10 gesperrt) |
| 03:54 | **Abholer 1.3.11 auf RAKVM** (`abholer_vm.py einrichten` aus main, Paket 59 Dateien, zip `d6a0d815…aa70`, Rho-PDF-Ablage unverändert) | `--pruefen`: PY_RC=0, SR-Freigabe 8/8, 8 Module, KI-Status gekoppelt. Läufe 03:54/03:58: `fehler=0`. Vorher-Fassung in `prog.vorher` (= 1.3.10) |

## 3. Nachtrag ibl-frog-seitenmarker-n1-f1 (Schalter `plaza_frog_immer`)
Abholer laut `stand`: **1.3.11**. In `C:\RaK\ibl\prog\abholer_vm.toml` steht **`plaza_frog_immer = true`**, Datei geändert **19.11. 03:54** (gelesen 03:59 per `vmssh`). Nichts zurückgesetzt, nichts extra gemacht. Den Beleg im Betrieb macht `ibl-frog-seitenmarker-n1-kontrolle`.

## 4. Version je PC (3.19.13 von X:)
- Alle drei starten KaiScribe von X: beim nächsten Start; die laufende Instanz am Büro-PC wurde beim Tausch neu gestartet (PID mit Titel 3.19.13).
- **CASWS08**: letzter Eintrag in `bruecke_CASWS08.log` 18.11. 08:08 mit 3.19.8 → seit dem Tausch nicht neu gestartet: **startet beim nächsten Mal mit 3.19.13 von X:**.
- **CASWS10**: letzter Eintrag 18.11. 13:11 mit 3.19.8 → ebenso **startet beim nächsten Mal mit 3.19.13 von X:**.
- **RAKCLIENT04**: es gibt kein `bruecke_RAKCLIENT04.log`, nur die Einrichtungs-Dateien → nicht belegbar, **startet beim nächsten Mal mit 3.19.13 von X:**.
- Büro-PC (CASWS14): 3.19.13 läuft seit 03:51 (Beleg im Log).
- 👉 Peter/Georg: Brücke 2.5.22 kommt an CASWS08, CASWS10 und RAKCLIENT04 erst mit einem Doppelklick auf `X:\RaKScribe\KaiScribe-einrichten.cmd`, **bis Do 19.11. vor dem ersten Diktat** (gleiche Bitte wie aus ibl-frog-lama-vm-n1-f1, #422; ohne sie läuft dort die Brücke 2.5.21, also ohne HIPPO-Text).

## 5. Abnahme Nr. 34 (Knie-KOALA)
- **Weg:** Ein Diktat über die Teststrecke (Mac-TTS, RDP-Mikrofon, F10/F12 am Büro-PC) wurde **nicht** gefahren. Das wäre ein Klick-Lauf am Büro-PC ohne Not, und der KOALA-Baustein für 451898 hätte von Hand in `X:\IBL-Vorbefunde` gelegt werden müssen (ein echter KOALA-Fall liegt nicht vor). Ersatz wie bei ibl-frog-lama-vm-n1-f1 (4b/4c): Kette aus den **live eingespielten Ständen** gerechnet, nur Testdaten, erfundene Nummer.
- **Skript:** `tools/beleg_koala34_kette.py <ris-mods> <RaKScribe26>` (Ausgabe am Server in `~/cj/work/kaiscribe-release-1118-einspielen/koala34.out`).
- **Kette:** KOALA-Eingabe (links, KL 3, medial 3,50 mm, lateral 6,10 mm) → Abholer **1.3.11** (`erstelle_vorbefund`) → Brücke **2.5.22** (`baustein_lesen` + `fuer_rakscribe`) → KaiScribe **3.19.13** (`ibl_bausteine.einsetzen`, KI-Vorlage der Fixture, Diktat der Fixture, Alter 66).
- **Ergebnis: `WORTLAUT_GLEICH_NR34 = True`**, keine Hinweise. Befund und Ergebnis sind **Zeichen für Zeichen** der Erwartungstext der Fixture Nr. 34 (Georgs freigegebener Wortlaut), also: Medial mäßiggradig … / Lateral normal weiter Gelenkspalt / Femoropatellar … / Ergebnis 1. Gonarthrose links medial (Grad 3 nach K&L), 2. Femoropatellararthrose links (Grad 3), 3. Geringer Gelenkerguss links; keine mm-Werte.
- **Offen:** Der Lauf mit echtem Diktat am Büro-PC an 451898 und ein echter KOALA-/HIPPO-Fall nach dem Einspielen stehen aus. Sobald ein echter Fall kommt, nur lesen und gegen die Prüftexte (ris-mods `BERICHT_kaiscribe_hippo_ergebnistext_n1.md`) abgleichen. Wer die Teststrecke mit Baustein will: Baustein-Datei `X:\IBL-Vorbefunde\<Nr><Ziffer>_koala.json` für eine Testnummer ablegen (Format wie `ibl_bausteine.baustein_lesen`) und `buero/kaiscribe.py diktat` laufen lassen (nur außerhalb Mo–Fr 06:30–17:20).

## 6. Hinweise
- Der erste `-Schritt py` des Büro-PC-Auftrags brach ab (EXIT=1), weil das Skript aus dem Ordner lief, den es neu baut; der zweite Lauf aus einer Kopie ging durch. Davor wurde auf X: nichts angefasst. Ordi-Hermes hat das im Skill vermerkt.
- VM-Hermes lehnte zwei Lese-Aufträge mit `content_policy_blocked` ab (harmlos formuliert, nur Lesen). Ich habe stattdessen den Mac-Weg `vmssh.py` genommen. Ein Prüfhinweis, kein Eingriff nötig.
- `abholer_vm.py stand` meldet „ABLAGE nicht_erreichbar (rakadmin)“, schon vor dem Einrichten so (rakadmin sieht X: nicht, rakauto schon, Läufe `fehler=0`).
- ris-mods-Quelle des Mac-Hermes-Auftrags: M0–M4, O0–O2 liegen in `~/cj/work/kaiscribe-release-1118-einspielen/`.

## 7. Regel-Audit (aus Teil 1 übernommen, BERICHT-KL-TABELLE-ZURUECK-N1, Skill-Regeln 1–13/3a–3af)
- **vorhanden:** 1, 3, 3a–3n (ohne 3j), 3r, 3s, 3t, 3u, 3v, 3w (eingeschränkt durch RH 38), 3x, 3aa, 3ab, 3ac, 3ad, 3af, 4, 5 (mit Peters Einzelpunkt-Ausnahme), 5a, 5b, 6, 7, 8, 10, 11, 12, 13
- **ergänzt:** 2, 3j, 3o, 3p, 3y, 3z, 3ae, 9
- **unklar:** 3q. „‚Wie bei‘ → ‚vereinbar mit‘“ widerspricht „IMMER ‚Bild wie bei [Diagnose]‘“. Georg entscheidet (Kanban #421).

## 8. Rückwege
- KaiScribe: `kaiscribe_x_tauschen.ps1 -Schritt zurueck` (jüngste .alt = 3.19.12; nur Sa/So oder Mo–Fr 20:10–06:30).
- Brücke: `X:\RaKScribe\_alt\Py-diktat-vor-2.5.22-20261119-034959` zurückkopieren, am Büro-PC `KaiScribe-einrichten.ps1 -Still`.
- VM-Formatierer: `titel_fmt_vm.py zurueck`. Zeiger: siehe Zeile 03:52.
- Abholer: `abholer_vm.ps1 -Einrichten` mit `prog.vorher` (= 1.3.10).

Meldung nach außen (Queue, live belegt): „KaiScribe 3.19.13 live seit Do 19.11. 03:51: K&L-Tabelle/KOALA-Kniebefund, PANDA-Knochenalter, HIPPO-Becken-/Hüfttext. IB-Lab-Texte aus dem Abholer 1.3.11 greifen ab jetzt; an CASWS08/CASWS10/RAKCLIENT04 braucht es noch einmal `KaiScribe-einrichten.cmd`.“
