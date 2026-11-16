# kaiscribe-humeruskopf-artikel-n1-einspielen – Schulter-Normalsatz „Der Humeruskopf steht …“ einspielen, Abnahme 451898, Meldung an Georg (ab Mo 16.11.2026 20:15)

Eingereiht von `kaiscribe-humeruskopf-artikel-n1` (Mo 16.11. nachmittags, Hetzner, Teil 1). Repo RaKScribe26 (Ordi-Werkzeuge in ris-mods).
Ressourcen: ordi + automaten-vm. Peer-Aufträge, die etwas ändern, nur werktags 20:10–06:00 bzw. am Wochenende, nie Mo 06:30–09:30.
Startet der Job an einem Werktag nach 04:00: nichts halb einspielen, denselben Brief als `…-einspielen-f1` für den nächsten Abend ab 20:15 einreihen.

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Die Meldung an Georg schickt die Queue aus dem Abschluss dieses Jobs
> (siehe unten), und nur, wenn es belegt live ist. Was nur Peter kann → `python3 ~/.hermes/scripts/kanban.py peter …` + Zeile „👉 …“.

ZUERST LESEN: `BERICHT-HUMERUSKOPF-ARTIKEL-N1.md` (Teil 1: Änderung, Tests, Release).

## Was eingespielt wird
- Georg 16.11.2026 („Der Humeruskopf. Bitte ändern“): im Röntgen-Schulter-Normalbefund steht jetzt
  „Der Humeruskopf steht in regelrechter Artikulation.“ statt „Humeruskopf in regelrechter Artikulation.“
- Code auf main: RaKScribe26 8d29db2, **Release 3.19.2** (e84b617), `rakscribe26.exe` 56.808.628 B,
  sha256 `a45bbefef05153736c03c427e00d668b7ae243ede671756cea74384885b89aed`, Windows-UI-Test 115/115 (Lauf 43901994474).
- Auf main liegt schon **3.19.3** (810b3ec, kaiscribe-mammo-vergleichsdatum-n1) darüber; dieser Job hat einen eigenen
  `…-einspielen`-Folgejob. Einspielen: das **neueste grüne Release, das e84b617 enthält** (`git merge-base --is-ancestor e84b617 <tag>`,
  Build + Windows-UI-Test grün). Läuft auf X: schon ein solches Release (z. B. weil der Mammo-Job vorher getauscht hat), NICHT
  nochmals tauschen, nur Schritt 2 (Abnahme). Nie auf ein älteres Release zurücktauschen.

## Schritt 0 – Tore (nur lesen)
1. Release vorhanden, Asset-SHA aus der API (`digest`), Build + UI-Test für den Commit grün (Helfer `~/cj/work/kaiscribe-cursor-record-n1/gh.py`).
2. Live-Stand lesen: SHA/Version von `X:\RaKScribe\rakscribe26.exe`, letzte `[INIT]`-Zeilen im `X:\RaKScribe\rakscribe.log`.
3. Niemand arbeitet am Büro-PC (Sitzung des eigenen Mac-RDP-Clients zählt nicht, siehe BERICHT-mammo-lauf-n1 A1/A1b).

## Schritt 1 – Tausch (wie 3.19.1, docs/benchmarks/BERICHT-mammo-lauf-n1.md)
- ris-mods `ordi-hermes/kaiscribe_x_tauschen.ps1`: EXE direkt von github.com nach
  `%LOCALAPPDATA%\hermes\work\ks_tausch\v<Tag>\rakscribe26.exe`, SHA prüfen, dann `-Schritt exe -Tag <Tag> -Sha <sha>`
  (Mo–Fr 06:30–20:10 gesperrt). NICHT `-Schritt holen`.
- Beleg: `KS_TAUSCH=ok neu=… alt=…`, Sicherung `rakscribe26.exe.vor<Tag>-….alt`, Titel „KaiScribe <Tag> - Röntgen am Kai“,
  `[INIT] Befund-Prompt 2026-11-16-humeruskopf-artikel …` (oder jünger), keine Netz-/Fehlerzeilen, kein Dialog der Sicherheitssoftware.
- Rückweg: `kaiscribe_x_tauschen.ps1 -Schritt zurueck` (nur außerhalb 06:30–20:10).

## Schritt 2 – Abnahme am Testpatienten 451898 (nie vidieren, nie melden)
- Ein neuer Testeintrag von 451898, Teststrecke KS (ris-mods `ordi-hermes/teststrecke/ks.py` / `buero/kaiscribe.py diktat`,
  Ablauf und Fallen: `ordi-hermes/ergebnis_hermi_ks_k0_20261111.md`, `ordi-hermes/folgejob_kaiscribe_3187_echttest_20261113.md`).
- Diktat „Schulter rechts unauffällig.“ (Normalbefund-Bypass, ohne KI). Erwartet im Befund wörtlich:
  „Normale Form der am Schultergelenk beteiligten Skelettabschnitte. **Der Humeruskopf steht in regelrechter Artikulation.** …“,
  kein „Humeruskopf in regelrechter Artikulation“ ohne Artikel; Ergebnis „Regelrechte Darstellung des Schultergelenkes rechts.“
- Optional zweites Diktat mit KI: „Schulter rechts. Mäßiggradige Omarthrose.“ → Humeruskopf-Satz, falls vorhanden, mit Artikel.
- Belegen (nur lesend): Lauf-Datei `X:\RaKScribe\Daten\laeufe\<Nr>_*.json` (`ergebnis_vorschlag` enthält „Der Humeruskopf steht“),
  `prompt_version` und `kaiscribe`-Version. Danach stornieren wie in der Teststrecke üblich.
- Testeinträge sehen die Schreibkräfte: Ankündigung „nicht schreiben“ nur über Kanban/Queue, nicht selbst.
- Geht die Teststrecke nicht (kein Ton, kein Fernzugang): ersatzweise in KaiScribe am Büro-PC getippt, ohne CAS-Schreiben, und das
  im Bericht klar sagen. Dann keine Meldung an Georg, sondern Kontroll-Job am nächsten Werktag (nur lesen: Lauf-Dateien echter
  Schulter-Normalbefunde enthalten „Der Humeruskopf steht“).

## Lücke aus Teil 1
Teil 1 lief ohne Büro-PC: kein Beleg, dass Georgs Foto aus genau dieser Vorlage stammt (andere Quelle wie ein Ordi-Textbaustein
oder lokal gespeicherter Block wäre denkbar). Gefunden wurde der Satz im Repo nur in `templates.json` (Röntgen-Schulter),
`taught_blocks.json` und dem Prompt. Zeigt die Abnahme den alten Satz trotz neuer EXE: Herkunft suchen (CAS-Textbaustein,
X:-Dateien), in RaKScribe26 beheben oder Kanban-Karte.

## Abschluss
- Bericht `docs/einspielen/ergebnis_humeruskopf_artikel_n1_<datum>.md` (Tore, Stände vorher/nachher, Tausch, Belege, Rückweg),
  Ordi-Aufträge/Antworten daneben.
- Nur wenn live belegt, zwei Zeilen an Georg (TG-Gruppe Homepage, -5216773962) – über den Queue-Abschluss, keine Patientendaten, z. B.:
  „Schulter-Normalbefund in KaiScribe geändert: jetzt ‚Der Humeruskopf steht in regelrechter Artikulation.‘
  Aktiv seit <Datum Uhrzeit> (Version <Tag>), an allen Befund-PCs ab dem nächsten Start von KaiScribe.“
