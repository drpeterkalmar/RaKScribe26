# kaiscribe-kniepat-titel-n1-einspielen – Knie + Patella axial: KaiScribe __VERSION__ einspielen, Abnahme 451898, Kanban #344 (ab Mo 16.11.2026 abends)

Eingereiht von `kaiscribe-kniepat-titel-n1` (Teil 1, Mo 16.11. ~22:45, Mac). Repo RaKScribe26 (Ordi-Werkzeuge in ris-mods).
Ressourcen: ordi + automaten-vm. Büro-PC-Regeln: Mo–Fr 06:30–17:20 nichts klicken, Mo 06:30–09:30 nichts einspielen, EXE-Tausch
nur werktags 20:10–06:30 bzw. am Wochenende. Startet der Job an einem Werktag nach 04:00: nichts halb einspielen, denselben Brief als
`…-einspielen-f1` für den nächsten Abend ab 20:15 einreihen (Mo ab 17:20 gilt für Klicks).

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.

ZUERST LESEN: `BERICHT-KNIEPAT-TITEL-N1.md` (Teil 1: Ursache, Änderung, Tests). Ablauf-Vorlage für Tausch/Abnahme:
`FOLGEJOB-HUMERUSKOPF-ARTIKEL-N1-EINSPIELEN.md` und `docs/benchmarks/BERICHT-mammo-lauf-n1.md`.

## Was eingespielt wird
- Leistungen kniepatl/kniepatr/kniepat2 → KaiScribe-Titel „Kniegelenk links/rechts/beidseits in 2 Ebenen mit Patella axial“
  (neue Vorlage `kniegelenk_in_2_ebenen_mit_patella_axial`, `cas_vorlagen.zusatz_vorlage`). Commit/Release: **__VERSION__** auf main
  (`git log --oneline --grep kniepat-titel-n1`).
- Einspielen: das **neueste grüne Release, das den Commit von __VERSION__ enthält** (`git merge-base --is-ancestor <commit> <tag>`,
  Build + Windows-UI-Test grün). Läuft auf X: schon ein solches Release: NICHT nochmals tauschen, nur Abnahme. Nie zurück auf ein älteres.
- ris-mods/Formatierer: keine Änderung (Bericht Abschnitt 2) → keine Windows-Prüfung nötig. Ist bis zum Start doch etwas aus ris-mods
  mit einzuspielen (anderer Job), gilt dessen eigene Windows-Prüfung.

## Schritt 0 – Tore (nur lesen)
1. Release vorhanden, Asset-SHA aus der API (`digest`), Build + UI-Test für den Commit grün (Helfer `~/cj/work/kaiscribe-cursor-record-n1/gh.py`).
2. Live-Stand: SHA/Version von `X:\RaKScribe\rakscribe26.exe`, letzte `[INIT]`-Zeilen in `X:\RaKScribe\rakscribe.log`.
3. Niemand arbeitet am Büro-PC (die Sitzung des eigenen Mac-RDP-Clients zählt nicht).

## Schritt 1 – Tausch
- ris-mods `ordi-hermes/kaiscribe_x_tauschen.ps1`: EXE direkt von github.com nach `%LOCALAPPDATA%\hermes\work\ks_tausch\v<Tag>\rakscribe26.exe`,
  SHA prüfen, dann `-Schritt exe -Tag <Tag> -Sha <sha>`. NICHT `-Schritt holen`.
- Beleg: `KS_TAUSCH=ok neu=… alt=…`, Sicherung `rakscribe26.exe.vor<Tag>-….alt`, Titel „KaiScribe <Tag> – Röntgen am Kai“, keine Netz-/Fehlerzeilen.
- **Rückweg:** `kaiscribe_x_tauschen.ps1 -Schritt zurueck` (jüngste .alt, nur außerhalb Mo–Fr 06:30–20:10). Im Bericht dokumentieren.

## Schritt 2 – Abnahme am Testpatienten 451898 (nie vidieren)
- Neuer Testeintrag 451898 mit der Leistung **kniepatl** („Knie li mit Patella axial“), Teststrecke KS (ris-mods `ordi-hermes/teststrecke/ks.py`
  bzw. `buero/kaiscribe.py diktat`, Fallen: `ordi-hermes/ergebnis_hermi_ks_k0_20261111.md`). **Lücke aus Teil 1:** nicht geprüft, ob die
  Teststrecke kniepatl als Leistung anlegen kann (bisher nur Einzelleistungen wie bü). Wenn nicht: Eintrag mit kniepatl so anlegen,
  wie die Strecke sonst Leistungen anlegt (cas_w), oder ersatzweise in KaiScribe am Büro-PC mit einer cas_leistungen-Datei
  `[{"kurz":"kniepatl","text":"Knie li mit Patella axial","vorlage":"kniegelenk_in_2_ebenen","seite":"links"}]` (ohne CAS-Schreiben)
  und das im Bericht klar sagen.
- Realistisches Testdiktat (KI-Weg), z. B.: „Kniegelenk links. Mäßiger Gelenkerguss im Recessus suprapatellaris. Beginnende
  Gonarthrose mit kleinen Osteophyten am medialen Tibiaplateau. Patella axial zentriert. Keine Fraktur.“
- Erwartet: Titel **„Kniegelenk links in 2 Ebenen mit Patella axial“** in KaiScribe und, nach dem Formatierer, fett + unterstrichen im
  CAS-Befund, genau ein Titel, keine CAS-Zeile daneben. Kein „Unauffällige Weichteile“ neben dem Erguss (3.18.13 bleibt).
- Optional Normalbefund ohne KI: „Knie links unauffällig.“ → derselbe Titel, Ergebnis „Regelrechte Darstellung des Kniegelenkes links.“
- Belegen (nur lesend): Lauf-Datei `X:\RaKScribe\Daten\laeufe\<Nr>_*.json` (`vorlagen` enthält `kniegelenk_in_2_ebenen_mit_patella_axial`,
  `ergebnis_vorschlag` beginnt mit dem Titel), Formatierer-Log ohne „bitte Titel prüfen“. Danach stornieren wie in der Teststrecke üblich.

## Abschluss
- Bericht `docs/einspielen/ergebnis_kniepat_titel_n1_<datum>.md` (Tore, Stände vorher/nachher, Tausch, Belege, Rückweg), keine Patientendaten.
- Nur wenn live belegt: `python3 ~/.hermes/scripts/kanban.py fertig 344 --notiz "Beleg: RaKScribe26 <commit> (Release <Tag>), Testpatient
  451898: Titel „Kniegelenk links in 2 Ebenen mit Patella axial“"`. Sonst #344 offen lassen, Notiz mit dem Grund.
- Meldung nach außen nur über den Queue-Abschluss und nur, wenn es live belegt ist, z. B. eine Zeile: „KaiScribe <Tag>: Knie mit Patella
  axial (kniepatl/r/2) hat jetzt den Titel ‚Kniegelenk links in 2 Ebenen mit Patella axial‘, aktiv seit <Datum Uhrzeit>.“
