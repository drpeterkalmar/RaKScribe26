# kaiscribe-release-1118-einspielen – KaiScribe 3.19.13 + Abholer 1.3.11 + Brücke/Formatierer einspielen, Abnahme 451898 (Georg-Go 18.11.)

Eingereiht von `kaiscribe-release-1118` (Teil 1, Do 19.11.2026 ~02:35, Hetzner). Repo RaKScribe26, Ordi-Werkzeuge und Abholer in ris-mods.
Ressourcen: ordi + automaten-vm. Georg 18.11. ~20:00: „Geh live. Morgen sollte alles, was wir hier geübt haben, verfügbar sein.“

**Zeitfenster:** Der EXE-Tausch ist nur Mo–Fr 20:10–06:30 (Sperre im Skript) bzw. am Wochenende erlaubt. Ziel laut Auftrag: **live bis Do 19.11. 06:30**.
Startet dieser Job an einem Werktag nach 05:30, dann nichts halb einspielen. Stattdessen denselben Brief als `kaiscribe-release-1118-einspielen-f1`
mit not-before 20:15 desselben Tages einreihen. Klicks am Büro-PC Mo–Fr 06:30–17:20 nie.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.

ZUERST LESEN: `BERICHT-KAISCRIBE-RELEASE-1118.md` (Teil 1), ris-mods `BERICHT_kaiscribe_hippo_ergebnistext_n1.md` (Prüftexte HIPPO),
`BERICHT-PANDA-KNOCHENALTER-N1.md`, `BERICHT-KL-TABELLE-ZURUECK-N1.md`. Ablauf-Vorlage für Tausch/Abnahme: `FOLGEJOB-KNIEPAT-TITEL-N1-EINSPIELEN.md`.

## Was eingespielt wird
1. **KaiScribe 3.19.13** (RaKScribe26 `34bf5ea`). Release-Tag `3.19.13` (latest). Asset `rakscribe26.exe`, 56 853 396 Byte,
   **sha256 `704549ed1c3aeb692ca7817240a74e7783c5da9aa10bb6a732230e14a1e85469`**. Build-Run 44434784025 und Windows-UI-Test 44435064425 sind grün.
   Enthalten sind 3.19.11 (K&L-Tabelle zurück, KOALA → Kniebefund, Regel-Register), 3.19.12 (PANDA-Knochenalter) und 3.19.13 (HIPPO-Becken-/Hüfttext).
   Stand Teil 1: **3.19.12 liegt schon auf X:** (Sicherung `rakscribe26.exe.vor3.19.12-20261119-010351.alt` = 3.19.10). Also 3.19.12 → 3.19.13 tauschen.
   Nie eine ältere Version (3.19.11) auf X: legen.
2. **Abholer 1.3.11 auf die Automaten-VM** (ris-mods `43a9268`/`1973a50`: `ibl/hippo_ergebnis.py`, `ibl/dicomweb.py` `zusatz_nachladen` lädt das
   private IB-Lab-JSON per BulkDataURI nach). Ohne das kommen Beckenschiefstand und BLD ohne Seite. Weg wie beim Abholer 1.3.10 im Job
   kaiscribe-panda-knochenalter-n1: `--pruefen` grün, Selbsttest. Ist 1.3.11 schon aktiv, dann nur belegen.
3. **RaK-Befund-Version mit Brücke `ibl_bausteine`** (reicht `befundtext.hippo` durch) auf X:/Büro-PC, dazu **VM-Formatierer `ibl_einfuegen` 1.7.0**.
   Weg wie bei den bisherigen ris-mods-Einspielungen (Windows-Prüfung des jeweiligen Werkzeugs).
- Keine Fälle neu aufbauen. Vidierte Befunde bleiben unberührt, die Änderung wirkt ab jetzt.

## Schritt 0 – Tore (nur lesen)
1. Release 3.19.13 + Digest per API (Helfer `~/cj/work/kaiscribe-release-1118/gh.py release 3.19.13`).
2. Live-Stand: SHA/Version von `X:\RaKScribe\rakscribe26.exe`, letzte `[INIT]`-Zeilen in `X:\RaKScribe\rakscribe.log`, Abholer-Version auf der VM.
3. Niemand arbeitet am Büro-PC (die eigene RDP-Sitzung des Macs zählt nicht).

## Schritt 1 – Tausch
- ris-mods `ordi-hermes/kaiscribe_x_tauschen.ps1`: Die EXE direkt von github.com nach `%LOCALAPPDATA%\hermes\work\ks_tausch\v3.19.13\rakscribe26.exe`
  holen, SHA prüfen, dann `-Schritt exe -Tag 3.19.13 -Sha 704549ed…5469`. **NICHT** `-Schritt holen`.
- Beleg: `KS_TAUSCH=ok neu=… alt=…`, Sicherung `rakscribe26.exe.vor3.19.13-….alt`, Fenstertitel „KaiScribe 3.19.13 – Röntgen am Kai“.
- Rückweg: `-Schritt zurueck` (nimmt die jüngste .alt = 3.19.12). Bei Rot: alte Version bleibt bzw. zurück, Grund in den Bericht.

## Schritt 2 – Live prüfen
- Version je PC belegen: `X:\RaKScribe\Daten\protokolle\bruecke_<PC>.log` bzw. `[INIT]` in `rakscribe.log` für **CASWS08, CASWS10, RAKCLIENT04**.
  Ein PC, der seit dem Tausch nicht neu gestartet ist, zählt als „startet beim nächsten Mal mit 3.19.13 von X:“. Das als solches im Bericht nennen.
- **Testlauf am Testpatienten 451898 (nie vidieren)** mit der **Knie-KOALA-Fixture Nr. 34** (`tests/offline/test_ibl_koala_text.py`, Georgs Fixtures Nr. 34/50).
  Der Wortlaut im KaiScribe-Ergebnis muss **exakt** dem Erwartungstext der Fixture Nr. 34 entsprechen (Offline in Teil 1 grün). Teststrecke KS
  (ris-mods `ordi-hermes/teststrecke/ks.py` bzw. `buero/kaiscribe.py diktat`).
- **Lücke aus Teil 1:** Am Server war nicht zu belegen, wie die Teststrecke einen KOALA-Baustein (Fixture Nr. 34) für 451898 einspeist.
  Weg wählen wie bei bisherigen IB-Lab-Abnahmen (ibl-Baustein-Datei für den Testauftrag). Geht es nicht ohne echten KOALA-Fall: im Bericht als offen nennen.
- Optional, wenn ein echter HIPPO-Fall nach dem Einspielen kommt: einen Prüftext aus dem HIPPO-Bericht gegen KaiScribe abgleichen (nur lesen).

## Schritt 3 – Bericht
Bericht `BERICHT-KAISCRIBE-RELEASE-1118-EINSPIELEN.md` (RaKScribe26). Inhalt: Version, was drin ist, Tausch-Belege, Abholer/Brücke/Formatierer-Stand,
Ergebnis von Testlauf 451898/Nr. 34 (Wortlaut-Vergleich), Regel-Audit-Liste aus Teil 1 übernehmen. Meldungen nach außen nur, wenn alles belegt live ist (über die Queue).
