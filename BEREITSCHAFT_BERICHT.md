# RaKScribe 3.11.0 – Bereitschaft: wartet minimiert auf das nächste CAS-Diktat (Bericht, 13.10.2026)

## Kurzfassung

- Peters Wunsch: RaKScribe soll nicht bei jedem Diktat erst ein paar Sekunden laden, sondern **als Symbol in der
  Taskleiste warten**. Das gibt es jetzt (nur EXE; die Web-App hat nur die neue Versionsnummer).
- **Menü ☰ „Mit Windows starten (wartet minimiert)“** (Standard aus): Nach der Windows-Anmeldung wartet ein kleiner,
  unsichtbarer **Starter auf dem eigenen PC**, bis die EXE erreichbar ist – X: kommt ja erst mit dem CAS-Login
  (Nachtrag 1). Dann startet er RaKScribe **nur als Taskleisten-Symbol**, ohne Fenster und ohne den Fokus zu stehlen.
- **„Digitales Diktat“ in CAS** holt das wartende RaKScribe sofort nach vorne (Annahme im Test 0,23–0,35 s statt
  Kaltstart), **nach EOL geht es nach ~1,5 s wieder in die Taskleiste** (Menü „Nach CAS-Befund minimieren“, Standard an).
  Das gilt auch, wenn die Brücke RaKScribe gestartet hat – es lädt also höchstens einmal am Tag.
- **Nur eine RaKScribe**: Ein zweiter Start (Doppelklick) holt die laufende nach vorne. **Schließen (X) beendet wie
  bisher.** Ohne CAS-Auftrag ändert sich am Arbeiten nichts.
- In der Taskleiste steht jetzt das **RaKScribe-Mikrofon** statt des allgemeinen CustomTkinter-Symbols.
- **Leerlauf minimiert: 0,8–1,4 % eines CPU-Kerns** (im Task-Manager meist 0 %), ~80 MB Arbeitsspeicher, kein Mikrofon
  offen. Windows-Test der echten EXE **69/69 bestanden** (14 neue Prüfungen Fall G), Offline-Tests 29/29 grün.
- Live: EXE-Release **3.11.0 (Latest)**, Web-App 3.11.0.

## Bedienhinweis für Peter (3 Zeilen)

1. Einmal RaKScribe von **X:\RaKScribe\rakscribe26.exe** starten → ☰ → **„Mit Windows starten (wartet minimiert)“** anhaken.
2. Ab der nächsten Anmeldung erscheint RaKScribe nach dem CAS-Login von selbst still als **Mikrofon-Symbol in der
   Taskleiste**; „Digitales Diktat“ holt es nach vorne, EOL schickt den Befund und legt es wieder ab.
3. Ausschalten: Haken wieder weg. Ganz beenden: Fenster mit **X** schließen (die Brücke startet es beim nächsten Diktat neu).

## Was genau passiert

### Autostart über den lokalen Starter (Nachtrag 1 hat Vorrang vor Punkt 1)

- Haken an → `RaKScribe.lnk` im **Benutzer-Autostart** (shell:startup, ohne Admin) →
  `wscript.exe //B //Nologo "%APPDATA%\RaKScribe\warte_auf_x.vbs"` (unsichtbar, kein Fenster).
- Der Starter prüft **alle 10 s**, ob die EXE unter ihrem Pfad erreichbar ist, und startet sie dann mit `--minimiert`.
  **Läuft RaKScribe schon** (z. B. von der Brücke gestartet; geprüft werden nur Prozesse des eigenen Benutzers): nichts
  tun. **Nach 4 h** gibt er still auf. Haken aus = Starter gelöscht → ein noch wartender Starter endet beim nächsten Takt.
- Er merkt sich die EXE, **aus der der Haken gesetzt wurde**. **Keine lokale Kopie** der EXE – Updates bleiben „eine
  Datei auf X: tauschen“. Das Menü zeigt darunter „wartet auf: X:\RaKScribe\rakscribe26.exe“.
- Protokoll des Starters: `%APPDATA%\RaKScribe\starter.log` (eine Zeile pro Anmeldung: gestartet / läuft schon /
  aufgegeben).

### Start mit `--minimiert`

- Nur Symbol in der Taskleiste, kein Fenster vorne, kein Fokus-Klau (z. B. mitten in die CAS-Anmeldung). Schlüssel,
  Vorlagen, Prompt werden wie sonst geladen.
- Ohne Praxis-Schlüssel wartet RaKScribe trotzdem; beim ersten CAS-Auftrag kommt es nach vorne mit Sperre und Hinweis
  „erst den Praxis-Schlüssel laden“.
- Der einmalige Hinweis auf eine alte Prompt-Datei erscheint erst, wenn das Fenster sichtbar und kein CAS-Diktat offen ist.

### Nur eine RaKScribe (Einzelinstanz)

- Zwei RaKScribe würden um denselben CAS-Auftrag konkurrieren. Ein zweiter Start holt die laufende nach vorne und
  beendet sich (Test: 3,9–5,7 s inkl. Entpacken). Der Starter bzw. ein zweiter Start mit `--minimiert` endet still.
- Startet man eine **andere** EXE (z. B. eine Kopie in Downloads), kommt die laufende nach vorne mit dem Hinweis
  „für die andere EXE erst dieses Fenster schließen“.

### Nach EOL im CAS-Modus

- Befund geht wie in 3.10.0 an die Brücke; ~1,5 s später geht RaKScribe in die Taskleiste – **nur, wenn bis dahin nichts
  Neues begonnen hat** (neuer Auftrag, Aufnahme, Text links). Menü „Nach CAS-Befund minimieren“ schaltet das ab.

### Unverändert

- Ohne CAS-Auftrag: F10/F9, SpeechMike, Einfügen, Web-App – alles wie bisher. Schließen (X) = Beenden. Kein Symbol im
  Infobereich (nur Taskleiste, wie gewünscht).

## Messung: Leerlauf minimiert

Echte EXE auf dem GitHub-Windows-Rechner (Windows Server 2025, ohne Mikrofon und SpeechMike), 5 s nach dem Laden,
dann **30 s gemessen** (psutil), drei Läufe (2 Test-Builds + Release):

| Lauf | CPU (alle RaKScribe-Prozesse) | Arbeitssatz | privater Arbeitssatz (Task-Manager „Arbeitsspeicher“) | zugesichert | Threads |
|---|---|---|---|---|---|
| Test-Build 1 | 0,78 % eines Kerns | 100,3 MB | 80,7 MB | 168,0 MB | 20 |
| Test-Build 2 | 0,94 % eines Kerns | 104,4 MB | 80,7 MB | 169,8 MB | 20 |
| Release 3.11.0 | 1,41 % eines Kerns | 104,0 MB | 80,4 MB | 169,5 MB | 20 |

Dazu der kleine Startprozess der EXE (PyInstaller): 8 MB Arbeitssatz, ~1 MB privat, keine messbare CPU.
Der Task-Manager rechnet in Prozent **aller** Kerne – bei 4 Kernen sind 1 % eines Kerns 0,25 %, angezeigt meist 0 %.
Im Leerlauf laufen nur die zwei 0,5-s-Takte (CAS-Auftrag/zweiter Start, letztes Fremdfenster), die Bildlaufleisten-
Prüfung der Textfelder und die SpeechMike-Suche alle 2 s. **Kein Aufnahme-Strom offen** (geprüft); das Mikrofon öffnet
erst bei Record/F10.

Weitere Zeiten aus dem Windows-Test: Kaltstart bis zum Taskleisten-Symbol 4,5–9,5 s · CAS-Auftrag angenommen nach
0,23–0,35 s, Fenster vorne · nach EOL wieder minimiert · Starter: EXE erscheint → Symbol nach 13–14 s (Takt ≤ 10 s +
Laden) · Starter bei laufender RaKScribe beendet nach 3,0 s · Frist-Test (12 s statt 4 h) beendet nach 12,0–12,1 s.

## Tests

- **Offline** `tests/offline/test_bereitschaft.py` (65 Prüfungen, läuft in CI): Starter-Skript (Pfad, Takt, Frist,
  „läuft schon“, Ende bei gelöschtem Skript, Umlaute/Leerzeichen/UNC/Apostroph, VBScript-Blöcke), Verknüpfung
  anlegen/entfernen mit einer Attrappe statt Windows Script Host (auch: gesperrt, hängt), Nachziehen (bleibt bei X:,
  X: nicht verbunden, umgezogen, alte Vorlage, Starter fehlt), Signal „nach vorne“, echter EXE-Ablauf mit Attrappen
  (EOL → nach 1,5 s minimiert; Option aus; Neues dazwischen; ohne Auftrag nichts; zweiter Start; ohne Schlüssel;
  Menü-Haken; Prompt-Hinweis), `main()` (Einzelinstanz, `--minimiert`).
- **Windows-UI-Test Fall G** (echte EXE, nach jedem Build): Start mit `--minimiert` → nur Symbol, nicht vorne, eigenes
  Symbol; Leerlauf; zweiter Start ohne/mit `--minimiert`; CAS-Auftrag wie die Brücke → vorne, Annahme < 1 s → Testbefund
  → EOL → wieder minimiert; Menü-Haken → Verknüpfung im echten Autostart-Ordner → wscript → Starter;
  **„Anmeldung“ mit fehlender EXE → Starter wartet unsichtbar; EXE erscheint nach 30 s → Start minimiert, Starter
  endet**; Starter bei laufender RaKScribe; Haken aus; Starter-Frist. Ergebnis 69/69 (Release-Notizen 3.11.0).
- Alle bisherigen Gates grün (29 Offline-Tests, Web-Tests, Typprüfung, Lint).

## Auslieferung

- Commits `93fc393` (Bereitschaft) und `25e2741` (Taskleisten-Symbol) auf main; Tests + Pages-Deploy grün.
- Release **3.11.0, Latest**, nur `rakscribe26.exe` (54 991 127 Bytes). Download geprüft:
  SHA256 `d8a3cbca0814b8b4d6d836994f1d340481e96e34cf408f45b551705a371f8394` = Prüfsumme von GitHub.
- Web-App live: Seitentitel „RaKScribe 3.11.0 – Befundungsassistent“.
- Zwei Test-Vorabversionen (`test-…`) wurden nach dem Prüfen wieder gelöscht.

## Lesart & Entscheidungen (Peter kann umsteuern)

- **„Nachziehen“ (Punkt 1) vs. „merkt sich den Pfad“ (Nachtrag 1):** Der Starter bleibt bei der EXE, aus der der Haken
  gesetzt wurde. Automatisch nachgezogen wird nur bei einem **echten Umzug** (alte Datei weg, ihr Ordner aber
  erreichbar). So wird eine einmal aus Downloads gestartete Test-EXE nicht still zum täglichen RaKScribe, und ein noch
  nicht verbundenes X: ändert nichts. Für alles andere gibt es im Menü „→ auf diese EXE umstellen“.
- **„An“ heißt: die Verknüpfung liegt im Autostart-Ordner** (was dort liegt, startet Windows). Zusätzlich steht die
  Wahl in `%APPDATA%\RaKScribe\einstellungen.json` (`autostart`, `cas_minimieren`).
- Fenstersymbol: zusätzlich zur Aufgabe, weil das minimiert wartende RaKScribe sonst mit dem CustomTkinter-Logo in der
  Taskleiste stand. Schlägt das Symbol fehl, bleibt es beim alten.

## Offene Punkte / Hinweise

- **Am Praxis-PC einmal echt durchspielen** (GitHub hat kein CAS und kein X:): Haken setzen, abmelden/anmelden,
  CAS-Login → nach ≤ 10 s Mikrofon-Symbol; „Digitales Diktat“ → vorne; EOL → zurück in die Taskleiste.
  Bei Problemen hilft `%APPDATA%\RaKScribe\starter.log`.
- **VBScript**: Microsoft baut VBScript schrittweise ab (heute noch vorinstalliert, später standardmäßig aus). Sperrt
  die Praxis-IT den Windows Script Host, meldet RaKScribe beim Anhaken „Autostart konnte nicht eingerichtet werden“.
  Ersatz bei Bedarf: derselbe Starter als PowerShell-Skript.
- **F10/F9 bleiben globale Tasten**, solange RaKScribe läuft – mit Autostart also ab der Anmeldung (wie bisher, wenn
  RaKScribe offen war). F10 in einem anderen Programm startet eine Aufnahme im minimierten RaKScribe.
- **Brücke (ris-mods, hier nicht geändert):** Sie bevorzugt laut `bruecke.ini` die Kopie in Downloads vor X:. Läuft
  RaKScribe (aus X:), nimmt sie natürlich die laufende. Nur wenn RaKScribe beendet wurde, startet sie kalt die
  Downloads-Kopie – alte Kopien dort am besten löschen. Außerdem erkennt sie „läuft schon“ per `tasklist` über alle
  Sitzungen; auf einem PC mit mehreren gleichzeitig angemeldeten Benutzern könnte sie eine fremde RaKScribe für
  „läuft“ halten (Starter und Einzelinstanz von RaKScribe prüfen dagegen nur den eigenen Benutzer bzw. die Sitzung).

## Dateien

- `source_code/bereitschaft.py` (neu): Starter- und Verknüpfungs-Skript, Autostart an/aus/nachziehen, Einzelinstanz,
  Signal „nach vorne“ – ohne Windows testbar.
- `source_code/RaKScribe.py`: Menü (Autostart, „wartet auf …“, umstellen, „Nach CAS-Befund minimieren“), `--minimiert`,
  Einzelinstanz in `main()`, Minimieren nach CAS-EOL, zweiter Start, Hinweis ohne Schlüssel, Prompt-Hinweis, Symbol,
  Selbsttest-Felder/-Phasen.
- Tests: `tests/offline/test_bereitschaft.py`, `tests/windows/exe_ui_test.py` (Fall G), `tests/offline/test_import.py`.
- Workflows: `build-exe.yml` (`--hidden-import=bereitschaft`), `test.yml` (neuer Schritt), `test-exe-windows.yml` (psutil).
