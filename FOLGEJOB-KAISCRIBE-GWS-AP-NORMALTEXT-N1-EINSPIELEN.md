# kaiscribe-gws-ap-normaltext-n1 – Einspielen ab 3.19.20 (GWS a.p.-Normaltext ohne Skoliose), Abnahme 451898

Von `kaiscribe-gws-ap-normaltext-n1` (Fr 20.11.2026 abends, Mac) als **Nachtrag** an die wartenden Einspiel-Aufträge
gegeben. Ein eigener Tausch ist nicht nötig: Die Änderung reist mit jeder Version **ab 3.19.20** (enthält Commit `5012b9d`).

> **MELDUNGSRUHE (Peter 11.11.2026):** nichts selbst an Telegram. Was nur Peter kann → `kanban.py peter …` + Zeile „👉 …“.

## Was sich ändert
Vorlage „Ganzaufnahme der Wirbelsäule a.-p.“ (templates.json, EXE und Web):
- vorher: „Wirbelsäule: Normale Stellung, flachbogige rechts-konvexe Skoliose. Alignementlinien regelrecht.“
- jetzt: „Wirbelsäule: Normale Stellung. Alignementlinien regelrecht.“

Quelle: Peter 20.11.2026, Kanban #459 Antwort „a“. Regel-Register `gws-ap-normaltext`. Sonst ändert sich nichts; der
SQUIRREL-Ersatz greift auf „Normale Stellung.“ wie bisher (offline geprüft: `tests/offline/test_gws_ap_normaltext.py`,
`tests/offline/test_ibl_squirrel_text.py`).

## Welche Version, wer spielt ein
- **3.19.20 enthält 3.19.19 (Umzug KaiScribe.exe, `%APPDATA%\KaiScribe`, `X:\KaiScribe`).** Laut
  `BERICHT-KAISCRIBE-UMZUG-N1-EXE.md` spielt den Umzug nur Teil 2 (`kaiscribe-umzug-n2-ordi`) ein, mit einem Rückweg.
  Darum: Wer heute 3.19.18 tauscht (`kaiscribe-befundfeld-sicher-n1-einspielen-f1`), bleibt bei 3.19.18. Die GWS-Abnahme
  unten macht der Auftrag, der die erste Version ≥ 3.19.20 auf X: bringt (`kaiscribe-umzug-n2-ordi` oder
  `kaiscribe-georg-2011-abnahme` mit 3.20.x, falls die auf main nach `5012b9d` gebaut ist).
- Tore wie immer: Tests, Build EXE und Windows-UI-Test zur eingespielten Version grün; Zeitfenster Mo–Fr 20:10–06:30 bzw.
  Wochenende; kein Klick am Büro-PC während der Ordi.

## Abnahme am Testpatienten 451898 (nie vidieren)
Testeintrag 451898 mit einer GWS-a.p.-Leistung (z. B. `gwsap`/„WS Ganzaufnahme a.p.“; **nicht** gws/gesws2/wsg2 – die
gehen seit 3.19.18 auf „Gesamte Wirbelsäule“). Gibt es keine reine a.p.-Leistung, ohne Leistung diktieren.
- **Diktat A (ohne Stellung, ohne SQUIRREL):** „Ganzaufnahme der Wirbelsäule a.p.: unauffällig.“
  Erwartet: „## Ganzaufnahme der Wirbelsäule a.-p.“, Befund beginnt mit „Wirbelsäule: Normale Stellung. Alignementlinien
  regelrecht.“, **kein „Skoliose“** im Brief.
- **Diktat B (Skoliose diktiert):** „Ganzaufnahme der Wirbelsäule a.p.: flachbogige linkskonvexe Skoliose, sonst unauffällig.“
  Erwartet: die diktierte Skoliose steht wörtlich im Befund und im Ergebnis, keine „rechts-konvexe“.
- **Diktat C (mit IB-Lab-Baustein SQUIRREL, Release-Regel Georg):** SQUIRREL-Baustein zu 451898 aus `X:\IBL-Vorbefunde`
  bzw. die anonymisierte Fixture `tests/offline/squirrel_bausteine.json` Fall „einzeln“ (Cobb 44°, Th5–Th12), Diktat
  „Ganzaufnahme der Wirbelsäule a.p.: Wirbelsäule unauffällig.“ Erwartet wie 3.19.17: „Wirbelsäule: Rechtskonvexe
  skoliotische Krümmung der BWS (Th5–Th12) mit einem Cobb-Winkel von 44°. Alignementlinien regelrecht.“, Ergebnis
  beginnt mit „Hochgradige rechtskonvexe Skoliose der BWS.“, Schluss „Weitere Winkelmessungen …“. Text muss **im Brief**
  stehen (Textauszug), nicht nur im Skripttest.
- Lauf-Datei `X:\…\Daten\laeufe\<Nr>_*.json` nur lesend: `vorlagen` = `["ganzaufnahme_der_wirbelsäule_a-p"]`. Danach
  stornieren wie in der Teststrecke üblich. Befundtext A/B/C wörtlich in den Bericht, keine Patientendaten.
- Weicht ein Text ab: Rückweg auf die vorherige Version, Grund in den Bericht, nichts „live“ melden.

## Abschluss
Nur nach belegter Abnahme A–C:
`python3 ~/.hermes/scripts/kanban.py fertig 459 --notiz "KaiScribe <Version> eingespielt <Datum Uhrzeit>, GWS a.p. 451898 A/B/C belegt (<Bericht>)"`.
Still – Peter nur bei Problem.
