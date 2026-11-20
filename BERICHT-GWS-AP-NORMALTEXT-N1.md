# Bericht kaiscribe-gws-ap-normaltext-n1 (Fr 20.11.2026, Mac, ohne Büro-PC)

**Version 3.19.20** = Commit **7b317b8** (Änderung 5012b9d). Release 3.19.20 ist „latest“: `KaiScribe.exe` und
`rakscribe26.exe` sind dieselbe Datei, 56 597 829 Byte, sha256 `e282492c2ea60a4ab7017a6bb807bc4dc240a72f867323871d9539dc43b88f4b`.
**Auf X: ist 3.19.20 noch nicht eingespielt, also nicht live in der EXE.** Die Web-App ist live.

## Änderung (Peter 20.11., Kanban #459 „a“)
- `templates.json`, Vorlage „Ganzaufnahme der Wirbelsäule a.-p.“ (EXE und Web lesen dieselbe Datei):
  „Wirbelsäule: Normale Stellung, flachbogige rechts-konvexe Skoliose. Alignementlinien regelrecht.“ →
  „Wirbelsäule: Normale Stellung. Alignementlinien regelrecht.“
- Nach weiteren Kopien gesucht (`git grep` in RaKScribe26, ris-mods und den Hermes-Skills): Der Satz steht nur in
  `templates.json`, in Snapshots und in Berichten.
- Regel-Register: neuer Eintrag `gws-ap-normaltext` (Pflicht-Regel). Keine Regel wurde entfernt.
- Der SQUIRREL-Ersatz (`_SQ_GWS`) erkennt „Normale Stellung.“ weiterhin. Dafür musste der Code nicht geändert werden.

## Tests
- Neues Gate `tests/offline/test_gws_ap_normaltext.py`, 11 Prüfungen, in CI eingetragen:
  - ohne SQUIRREL und ohne Stellungs-Diktat kein „Skoliose“, sowohl beim Normalbefund als auch über die KI;
  - die KI bekommt die Skoliose nicht mehr in der Vorlage vorgelegt;
  - eine diktierte Skoliose bleibt in Befund und Ergebnis;
  - mit SQUIRREL (Cobb 44°) entsteht derselbe Text wie bisher.
- SQUIRREL-Snapshot nachgezogen. Geändert haben sich nur die zwei Fälle mit Vorlagentext („alle < 10°“, „Metall“).
  Den Kommentar in `test_ibl_squirrel_text.py` habe ich angepasst.
- Am Mac sind alle Offline-Tests grün, mit drei Ausnahmen, die schon vorher rot waren:
  - `test_cas_auftrag` (Python 3.9) und `test_maske_ablauf` (Tk) scheitern an der Mac-Umgebung.
  - `test_ibl_nur_auffaellig` („bit-gleich panda“) ist auf dem unveränderten Stand genauso rot und läuft nicht in CI.
- Die Web-Tests sind grün.
- GitHub: Tests 44825348605, Build EXE 44825365985, Windows-UI-Test 44825647648 und Pages 44825948376 sind grün. Im
  Live-Bundle stehen 3.19.20 und der neue Satz, die alte Formulierung kommt nicht mehr vor.

## Einspielen (offen)
3.19.20 enthält auch 3.19.19, also den Umzug auf KaiScribe.exe, `%APPDATA%\KaiScribe` und `X:\KaiScribe`. Diesen Umzug
spielt laut `BERICHT-KAISCRIBE-UMZUG-N1-EXE.md` nur Teil 2 ein. Deshalb gibt es keinen eigenen Tausch, sondern Nachträge:
- an `kaiscribe-umzug-n2-ordi` (Server-Queue) und an `kaiscribe-georg-2011-abnahme` (Mac): Wer die erste Version ab 3.19.20
  einspielt, macht auch die GWS-a.p.-Abnahme am 451898. Sie hat drei Teile: A ohne Stellung, B mit diktierter Skoliose,
  C mit SQUIRREL-Baustein. Der Text muss im Brief stehen. Erst danach folgt `kanban.py fertig 459`.
- an `kaiscribe-befundfeld-sicher-n1-einspielen-f1` und `kaiscribe-squirrel-ergebnistext-n1-einspielen`: gezielt 3.19.18
  tauschen, nicht „latest“, weil sonst der Umzug ohne Teil 2 auf X: käme.
- Die Anleitung steht in `FOLGEJOB-KAISCRIBE-GWS-AP-NORMALTEXT-N1-EINSPIELEN.md`.
- Kanban #459 hat eine Notiz bekommen und ist **nicht** auf „fertig“ gesetzt.
